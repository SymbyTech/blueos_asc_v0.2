#! /usr/bin/env python3
from pathlib import Path
import uvicorn
import threading
import json
import time
from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi_versioning import VersionedFastAPI, version
from loguru import logger
from pydantic import BaseModel
from Stack import Stack
import subprocess
import os
# Service name for logging
SERVICE_NAME = "RealTimeSensorDisplay"

# Initialize logger
logger.info(f"Starting {SERVICE_NAME}!")

# Initialize FastAPI app
app = FastAPI(
    title="Argonot Smart Control",
    description="Smart Control API for Real-time Data and Control Management.",
)

# Global variable to store the subprocess
joystick_process = None
motion_process = None
# Initialize Stack instance
stack = Stack()

# Configure CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Define data models
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

# Sensor data handling in a separate thread
def sensor_data():
    global stack
    while True:
        retv = json.dumps({'current': stack.get_current_sensor_data()})
        time.sleep(1)
        logger.info(f"Sensor data: {retv}")

sensor_thread = threading.Thread(target=sensor_data)
sensor_thread.daemon = True
sensor_thread.start()


# Post Request to handle joystick start script and stop script
@app.post("/start_joystick")
@version(1, 0)
async def start_joystick():
    global joystick_process
    if joystick_process and joystick_process.poll() is None:
        return {"status": "error", "message": "Joystick server is already running."}
    try:
        joystick_process = subprocess.Popen(["python3", "joystick/joystick.py"], cwd=os.path.dirname(__file__))
        return {"status": "success", "message": "Joystick server started."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    

@app.post("/stop_joystick")
@version(1, 0)
async def stop_joystick():
    global joystick_process
    if joystick_process and joystick_process.poll() is None:
        joystick_process.terminate()
        joystick_process = None
        return {"status": "success", "message": "Joystick server stopped."}
    return {"status": "error", "message": "Joystick server is not running."}

# Post Request to handle motion start script and stop script
@app.post("/start_motion")
@version(1, 0)
async def start_motion():
    global motion_process
    if motion_process and motion_process.poll() is None:
        return {"status": "error", "message": "Motion script is already running."}
    try:
        motion_process = subprocess.Popen(["python3", "motion.py"], cwd=os.path.dirname(__file__))
        return {"status": "success", "message": "Motion script started."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/stop_motion")
@version(1, 0)
async def stop_motion():
    global motion_process
    if motion_process and motion_process.poll() is None:
        motion_process.terminate()
        motion_process = None
        return {"status": "success", "message": "Motion script stopped."}
    return {"status": "error", "message": "Motion script is not running."}

@app.post("/led_toggle", status_code=status.HTTP_200_OK)
@version(1, 0)
async def handle_led_toggle(data: LEDToggle):
    led_num = data.led_num
    state = data.state
    LED_BOARD = 1
    stack.switch(LED_BOARD, led_num + 1, state)
    return {"success": True, "message": f"LED Channel {led_num} toggled to {state}"}

@app.post("/led_brightness", status_code=status.HTTP_200_OK)
@version(1, 0)
async def handle_led_brightness(data: LEDVALToggle):
    led_num = data.led_num
    val = data.val
    LED_PIN = 0
    stack.set_pwm_out(led_num + LED_PIN, val)
    return {"success": True, "message": f"LED Channel increased to {val}"}

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
# Versioned API
app = VersionedFastAPI(app, version="1.0.0", prefix_format="/v{major}.{minor}", enable_latest=True)

# Mount static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/", response_class=FileResponse)
async def root():
    return "index.html"

if __name__ == "__main__":
    # Running uvicorn with log disabled so loguru can handle it
    uvicorn.run(app, host="0.0.0.0", port=80, log_config=None)
