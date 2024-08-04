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

# Service name for logging
SERVICE_NAME = "RealTimeSensorDisplay"

# Initialize logger
logger.info(f"Starting {SERVICE_NAME}!")

# Initialize FastAPI app
app = FastAPI(
    title="Real Time Smart Control and Sensor Display API",
    description="API for managing real-time sensor data and controls.",
)


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

@app.get("/", response_class=FileResponse)
async def root():
    return "static/index.html"

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

# Versioned API
app = VersionedFastAPI(app, version="1.0.0", prefix_format="/v{major}.{minor}", enable_latest=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80, log_config=None)
