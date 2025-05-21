#! /usr/bin/env python3
from pathlib import Path
import uvicorn
import threading
import json
import time
from fastapi import FastAPI, status, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi_versioning import VersionedFastAPI, version
from loguru import logger
from pydantic import BaseModel
from Stack import Stack
import subprocess
import os
import socket

# Import LED Controller
from led import led_controller

# Service name for logging
SERVICE_NAME = "RealTimeSensorDisplay"

# Initialize logger
logger.info(f"Starting {SERVICE_NAME}!")

# Initialize FastAPI app
app = FastAPI(
    title="Argonot Smart Control",
    description="Smart Control API for Real-time Data and Control Management.",
)

# Global variables
motion_controller_enabled = False
websocket_connections = set()

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        websocket_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# Motion controller thread
def run_motion_controller():
    import json
    from motion import command_queue, send_command_to_motors, state_manager
    
    while True:
        if not motion_controller_enabled:
            time.sleep(0.1)
            continue
            
        # Process any commands in the queue
        try:
            if not command_queue.empty():
                command = command_queue.get(block=False)
                if command is not None:
                    send_command_to_motors(command["speed"], command["direction_one"], command["direction_two"])
        except Exception as e:
            logger.error(f"Error in motion controller: {e}")
        
        time.sleep(0.01)

# Start motion controller thread
motion_thread = threading.Thread(target=run_motion_controller, daemon=True)
motion_thread.start()

# Data Models
class LEDToggle(BaseModel):
    led_num: int
    state: int

class LEDVALToggle(BaseModel):
    led_num: int
    val: int

class MOTORToggle(BaseModel):
    motor_num: int
    state: int

class CAMToggle(BaseModel):
    cam_num: int
    state: int

# Sensor Thread
def sensor_data():
    global stack
    while True:
        retv = json.dumps({'current': stack.get_current_sensor_data()})
        time.sleep(1)
        # logger.info(f"Sensor data: {retv}")

stack = Stack()
sensor_thread = threading.Thread(target=sensor_data)
sensor_thread.daemon = True
sensor_thread.start()

# API Endpoints
@app.post("/start_joystick")
@version(1, 0)
async def start_joystick():
    # Instead of starting a process, return a redirect to the joystick page
    return {"status": "success", "message": "Please navigate to /joystick to use the joystick interface"}

@app.post("/stop_joystick")
@version(1, 0)
async def stop_joystick():
    # No need to stop a process, but we can close existing WebSocket connections
    return {"status": "success", "message": "Please close the joystick browser tab to stop the joystick"}

@app.post("/start_motion")
@version(1, 0)
async def start_motion():
    global motion_controller_enabled
    if motion_controller_enabled:
        return {"status": "error", "message": "Motion controller is already running."}
    try:
        # Initialize motion controller
        from motion import initialize_motion_controller
        initialize_motion_controller()
        
        # Enable motion processing
        motion_controller_enabled = True
        return {"status": "success", "message": "Motion controller started."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/stop_motion")
@version(1, 0)
async def stop_motion():
    global motion_controller_enabled
    if not motion_controller_enabled:
        return {"status": "error", "message": "Motion controller is not running."}
    
    # Disable motion processing
    motion_controller_enabled = False
    
    # Stop motors
    from motion import send_command_to_motors
    send_command_to_motors(0, "STOP", "STOP")
    
    return {"status": "success", "message": "Motion controller stopped."}

@app.post("/led_toggle", status_code=status.HTTP_200_OK)
@version(1, 0)
async def handle_led_toggle(data: LEDToggle):
    led_num = data.led_num
    state = data.state
    
    # Store the switch state
    led_controller.set_switch_state(led_num, state)
    
    # If switch is turned off, force brightness to 0
    # If switch is turned on, use the stored brightness value (or default to 100%)
    if state:
        # Get current brightness, if it's 0 set it to 100
        current_brightness = led_controller.get_brightness(led_num)
        if current_brightness == 0:
            current_brightness = 100
        led_controller.set_brightness(led_num, current_brightness)
    else:
        # Force brightness to 0 when switch is off
        led_controller.set_brightness(led_num, 0)
    
    return {"success": True, "message": f"LED Channel {led_num} toggled to {state}"}

@app.post("/led_brightness", status_code=status.HTTP_200_OK)
@version(1, 0)
async def handle_led_brightness(data: LEDVALToggle):
    led_num = data.led_num
    val = data.val
    
    # Store the brightness value regardless of switch state
    led_controller.brightness_values[led_num] = val
    
    # Only apply brightness if switch is ON
    if led_controller.get_switch_state(led_num):
        led_controller.set_brightness(led_num, val)
    
    return {"success": True, "message": f"LED Channel {led_num} brightness set to {val}"}

@app.post("/motor_toggle", status_code=status.HTTP_200_OK)
@version(1, 0)
async def handle_motor_toggle(data: MOTORToggle):
    motor_num = data.motor_num
    state = data.state
    MOTOR_BOARD = 2
    stack.switch(MOTOR_BOARD, motor_num + 1, state)
    return {"success": True, "message": f"Motor Channel {motor_num} toggled to {state}"}

@app.post("/cam_toggle", status_code=status.HTTP_200_OK)
@version(1, 0)
async def handle_cam_toggle(data: CAMToggle):
    cam_num = data.cam_num
    state = data.state
    CAM_BOARD = 0
    stack.switch(CAM_BOARD, cam_num + 1, state)
    return {"success": True, "message": f"CAMERA Channel {cam_num} toggled to {state}"}

@app.get("/sensor_data", status_code=status.HTTP_200_OK)
@version(1, 0)
async def get_sensor_data():
    global stack
    retv = json.dumps({'current': stack.get_current_sensor_data()})
    return {"success": True, 'sensordata': retv}

@app.get("/bme_data", status_code=status.HTTP_200_OK)
@version(1, 0)
async def get_bme_data():
    global stack
    retv = json.dumps({'bme': stack.get_bme_data()})
    return {"success": True, 'bmedata': retv}

# Versioning and Static Files
app = VersionedFastAPI(app, version="1.0.0", prefix_format="/v{major}.{minor}", enable_latest=True)

# WebSocket endpoint for joystick data - MUST be AFTER versioning
@app.websocket("/ws/joystick")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive joystick data
            data = await websocket.receive_json()
            
            # Process joystick data if motion is enabled
            if motion_controller_enabled and "axes" in data:
                from motion import process_joystick_data
                process_joystick_data(data)
                
            # Broadcast to all clients
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Mount static files AFTER adding the websocket route
app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/", response_class=FileResponse)
async def root():
    return "index.html"

# Joystick page - serve directly with inline HTML
@app.get("/joystick", response_class=HTMLResponse)
async def joystick_page():
    # Define the joystick HTML directly in the code
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Joystick Control</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            color: white;
            background-color: #333;
            padding: 20px;
        }
        .controller-data {
            margin: 20px auto;
            text-align: left;
            display: block;
            background-color: #444;
            padding: 15px;
            border-radius: 5px;
            max-width: 800px;
        }
        .axis-data, .button-data {
            margin: 10px 0;
            font-size: 14px;
        }
        h1 {
            color: #4CAF50;
        }
        h2 {
            display: inline-block;
            font-size: 14px;
            margin: 0 10px 0 0;
            color: #4CAF50;
        }
        .data-line {
            margin: 5px 0;
        }
        .status {
            margin: 10px auto;
            padding: 5px;
            background-color: #444;
            border-radius: 5px;
            max-width: 400px;
        }
        .connected {
            color: #4CAF50;
        }
        .disconnected {
            color: #F44336;
        }
        .visual-display {
            margin: 20px auto;
            width: 300px;
            height: 300px;
            border: 2px solid #4CAF50;
            border-radius: 50%;
            position: relative;
            background-color: #222;
        }
        .joystick-dot {
            width: 20px;
            height: 20px;
            background-color: #F44336;
            border-radius: 50%;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            transition: all 0.1s ease;
        }
    </style>
</head>
<body>
    <h1>BlueOS Joystick Control</h1>
    
    <div id="connection-status" class="status disconnected">
        WebSocket: Disconnected
    </div>
    
    <div id="controller-status" class="status disconnected">
        Controller: Disconnected
    </div>

    <div class="visual-display">
        <div id="joystick-dot" class="joystick-dot"></div>
    </div>

    <div class="controller-data">
        <div class="data-line">
            <h2>Axis Data:</h2>
            <span id="axis-data" class="axis-data"></span>
        </div>
        <div class="data-line">
            <h2>Button Data:</h2>
            <span id="button-data" class="button-data"></span>
        </div>
    </div>

    <script>
        // Create WebSocket connection
        const socket = new WebSocket(`ws://${window.location.host}/ws/joystick`);
        const connectionStatus = document.getElementById('connection-status');
        const controllerStatus = document.getElementById('controller-status');
        const joystickDot = document.getElementById('joystick-dot');
        
        // Connection opened
        socket.addEventListener('open', (event) => {
            connectionStatus.textContent = 'WebSocket: Connected';
            connectionStatus.className = 'status connected';
            console.log('WebSocket connected');
        });
        
        // Connection closed
        socket.addEventListener('close', (event) => {
            connectionStatus.textContent = 'WebSocket: Disconnected';
            connectionStatus.className = 'status disconnected';
            console.log('WebSocket disconnected');
        });
        
        // Listen for messages
        socket.addEventListener('message', (event) => {
            const data = JSON.parse(event.data);
            console.log('Server response:', data);
        });
        
        // Handle errors
        socket.addEventListener('error', (event) => {
            connectionStatus.textContent = 'WebSocket: Error';
            connectionStatus.className = 'status disconnected';
            console.error('WebSocket error:', event);
        });

        let controllerConnected = false;

        window.addEventListener("gamepadconnected", (event) => {
            controllerConnected = true;
            controllerStatus.textContent = 'Controller: Connected';
            controllerStatus.className = 'status connected';
            console.log("Gamepad connected!");
            updateControllerData();
        });

        window.addEventListener("gamepaddisconnected", (event) => {
            controllerConnected = false;
            controllerStatus.textContent = 'Controller: Disconnected';
            controllerStatus.className = 'status disconnected';
            console.log("Gamepad disconnected!");
        });

        function updateControllerData() {
            if (controllerConnected && socket.readyState === WebSocket.OPEN) {
                const gamepads = navigator.getGamepads();
                const gp = gamepads[0];

                // Display axis data horizontally
                let axisDataHtml = "";
                gp.axes.forEach((axis, index) => {
                    axisDataHtml += `Axis ${index}: ${axis.toFixed(2)} `;
                });
                document.getElementById('axis-data').innerText = axisDataHtml;

                // Display button data horizontally
                let buttonDataHtml = "";
                gp.buttons.forEach((button, index) => {
                    let valueDisplay = button.value !== undefined ? button.value.toFixed(2) : button.pressed;
                    buttonDataHtml += `Button ${index}: ${valueDisplay} `;
                });
                document.getElementById('button-data').innerText = buttonDataHtml;

                // Update visual joystick position (assuming axis 0 is horizontal, 1 is vertical)
                if (gp.axes.length >= 2) {
                    const xAxis = gp.axes[0];
                    const yAxis = gp.axes[1];
                    
                    // Calculate position (150 = center, 140 = radius)
                    const dotX = 150 + (xAxis * 140);
                    const dotY = 150 + (yAxis * 140);
                    
                    joystickDot.style.left = `${dotX}px`;
                    joystickDot.style.top = `${dotY}px`;
                }

                // Send data to the server via WebSocket
                socket.send(JSON.stringify({
                    axes: gp.axes.map((axis, index) => ({ index, value: axis.toFixed(2) })),
                    buttons: gp.buttons.map((button, index) => ({
                        index,
                        value: button.value !== undefined ? button.value.toFixed(2) : button.pressed
                    }))
                }));

                // Request next frame update
                requestAnimationFrame(updateControllerData);
            } else if (controllerConnected) {
                // If WebSocket is closed but controller is connected, try again later
                setTimeout(updateControllerData, 1000);
            }
        }
    </script>

</body>
</html>
    """
    return html_content

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80, log_config=None)