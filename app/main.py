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
    # We don't need to start a separate process now, just return success
    return {"status": "success", "message": "Joystick interface is ready. The joystick panel has been opened."}

@app.post("/stop_joystick")
@version(1, 0)
async def stop_joystick():
    # We don't need to stop a process, just return success
    return {"status": "success", "message": "Joystick interface stopped. You can close the joystick panel."}

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80, log_config=None)