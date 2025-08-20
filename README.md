# Argonot Smart Control (ASC) - BlueOS Extension

<div align="center">

![Version](https://img.shields.io/badge/version-0.0.3-blue.svg)
![BlueOS](https://img.shields.io/badge/BlueOS-Compatible-green.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)

**Advanced underwater robotics control system for the Argonot ROV**

</div>

## 📖 Project Description

The Argonot Smart Control (ASC) is a sophisticated BlueOS extension designed to provide comprehensive control and monitoring capabilities for the Argonot robot. This system integrates multiple hardware components through a unified web-based interface, enabling real-time control of motors, lighting, sensors, and servo systems.

**Key Features:**
- **Real-time Motor Control**: Dual motor control with differential steering via joystick
- **Advanced Sensor Monitoring**: Current, voltage, power monitoring and environmental sensors (temperature, humidity, pressure)
- **LED Lighting Control**: Multi-channel brightness control with individual switching
- **Servo/PWM Control**: 16-channel PWM control for servos and actuators  
- **Camera Control**: Multi-camera switching capabilities
- **WebSocket Interface**: Real-time bidirectional communication for responsive control
- **Modern Web UI**: Vue.js-based responsive interface optimized for underwater operations

## 🔧 Hardware Architecture

### Core Components

#### **Primary Controller**
- **Raspberry Pi 4** (ARM64/ARMv7l architecture)
  - Runs BlueOS and the ASC extension
  - I2C communication hub
  - Serial communication controller

#### **Motor Control System**
- **2x Arduino Nano** (Motor Controllers)
  - **Left Motor**: Connected via `/dev/MOT1`
  - **Right Motor**: Connected via `/dev/MOT2`
  - Serial communication at 9600 baud
  - Variable speed control (0-20 range)
  - Forward/Backward/Stop commands

#### **Lighting System**
- **1x Arduino Nano** (LED Controller)
  - Connected via `/dev/LEDS`
  - 4-channel LED control
  - Individual brightness control (0-100%)
  - Per-channel on/off switching

#### **Sensor Stack**
- **I2C Multiplexer System** (Dual TCA9548A multiplexers)
  - Primary multiplexer: Address `0x77`
  - Secondary multiplexer: Address `0x71`
  - Enables connection of multiple I2C devices
  
- **Current/Power Monitoring** (up to 16 sensors)
  - Individual current, voltage, and power monitoring per channel
  - Real-time power consumption tracking

- **Environmental Sensors** (BME280)
  - Temperature, humidity, and pressure monitoring
  - Multiple sensor support via multiplexer system

#### **Servo Control**
- **PCA9685 PWM Controller**
  - 16-channel servo/PWM control
  - 50Hz default frequency (configurable)
  - Precise servo positioning for robotic arms, grippers, etc.

### System Integration Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raspberry Pi  │    │  Arduino Nano   │    │  Arduino Nano   │
│     (Main)      │◄──►│  (Left Motor)   │    │  (Right Motor)  │
│                 │    │   /dev/MOT1     │    │   /dev/MOT2     │
└─────────┬───────┘    └─────────────────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  I2C Multiplx   │    │  Arduino Nano   │    │   PCA9685 PWM   │
│   TCA9548A      │◄──►│  (LED Control)  │    │   Controller    │
│                 │    │   /dev/LEDS     │    │                 │
└─────────┬───────┘    └─────────────────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐
│  Current        │    │  Environmental  │
│  Sensors        │    │  Sensors BME280 │
│                 │    │                 │
└─────────────────┘    └─────────────────┘
```

## 💻 Software Architecture

### **Backend Stack**
- **FastAPI** (v0.92.0) - High-performance async web framework
- **Uvicorn** (v0.20.0) - ASGI web server
- **WebSockets** (v10.4) - Real-time communication
- **FastAPI-Versioning** (v0.9.1) - API versioning support

### **Hardware Interface Libraries**
- **RPi.GPIO** - Raspberry Pi GPIO control
- **SMBus** (v1.1.post2) - I2C communication
- **Adafruit-PCA9685** (v1.0.1) - PWM controller interface
- **BME280** (v0.6) - Environmental sensor interface
- **PySerial** (v3.5) - Serial communication with Arduino controllers

### **Frontend Stack**
- **Vue.js 2** - Reactive web interface
- **Vuetify** - Material Design component framework
- **Axios** - HTTP client for API communication

### **Code Architecture**

#### **Main Application** (`main.py`)
- FastAPI application setup and routing
- WebSocket connection management
- Multi-threaded sensor data collection
- Motion controller thread management
- API endpoints for all system controls

#### **Hardware Control Modules**

**Stack Controller** (`Stack.py`)
```python
# Key responsibilities:
- I2C multiplexer management
- Current sensor data collection
- Environmental sensor (BME280) interface  
- PWM servo control via PCA9685
- Multi-process sensor monitoring
```

**Motor Control** (`motion.py`)
```python
# Key responsibilities:
- Serial communication with motor controllers
- Joystick input processing and translation
- Differential steering calculations
- Thread-safe command queuing
```

**LED Control** (`led.py`)
```python
# Key responsibilities:
- LED brightness control via serial communication
- Multi-channel switching and dimming
- Thread-safe command processing
```

## 🚀 Usage Instructions

### **Installation via BlueOS**

1. **Access BlueOS Interface**
   ```
   http://your-vehicle-ip:8080
   ```

2. **Navigate to Extensions**
   - Go to "Extensions" in the BlueOS menu
   - Search for "Argonot Smart Control" 
   - Click "Install"

3. **Access ASC Interface**
   - Once installed, click "Open" on the ASC extension
   - The control interface will load in a new tab

### **Control Interface**

#### **Motor Control**
- **Start Motion Controller**: Initialize motor communication
- **Joystick Panel**: Real-time joystick control with WebSocket
  - Forward/Backward: Y-axis movement
  - Left/Right Turning: X-axis movement  
  - Differential steering for precise maneuvering

#### **LED Control**
- **4-Channel LED Control**
  - Individual on/off switches per channel
  - Brightness sliders (0-100%)
  - Real-time brightness adjustment

#### **Camera Control**
- **Multi-Camera Switching**
  - Switch between available camera feeds
  - Individual camera power control

#### **Motor Switching**
- **Direct Motor Control**
  - Manual motor enable/disable
  - Individual motor control override

#### **Sensor Monitoring**
- **Real-time Data Display**
  - Current, voltage, power consumption
  - Temperature, humidity, pressure readings
  - Auto-refreshing sensor dashboard

### **WebSocket Joystick Interface**

Connect to the WebSocket endpoint for real-time control:
```javascript
const ws = new WebSocket('ws://vehicle-ip/ws/joystick');
ws.send(JSON.stringify({
  axes: [
    {index: 1, value: y_axis},  // Forward/Backward
    {index: 2, value: x_axis}   // Left/Right
  ]
}));
```

## 🛠️ Developer Setup

### **Prerequisites**
- **Hardware Requirements**
  - Raspberry Pi 4 with BlueOS installed
  - Arduino Nano controllers for motors and LEDs
  - I2C multiplexer boards (TCA9548A)
  - Current sensors, BME280 sensors, PCA9685 PWM controller

- **Software Requirements**
  - Docker (for BlueOS extension development)
  - Python 3.11+
  - Git

### **Development Environment Setup**

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/blueos_asc_v0.2.git
   cd blueos_asc_v0.2
   ```

2. **Install Python Dependencies**
   ```bash
   cd app
   pip install -r requirements.txt
   ```

3. **Hardware Connection Setup**
   ```bash
   # Ensure device nodes exist for serial communication
   ls -la /dev/MOT*  # Motor controllers
   ls -la /dev/LEDS  # LED controller
   
   # I2C bus availability
   ls -la /dev/i2c-*
   ```

4. **Local Development**
   ```bash
   # Run locally for development
   cd app
   python main.py
   
   # Access at http://localhost:80
   ```

### **Docker Development**

1. **Build Extension Image**
   ```bash
   docker build -t argonot-asc:dev .
   ```

2. **Run with Hardware Access**
   ```bash
   docker run --privileged \
     -v /dev:/dev \
     -v /root/.config:/root/.config \
     -p 80:80 \
     argonot-asc:dev
   ```

3. **Development with Volume Mounting**
   ```bash
   docker run --privileged \
     -v /dev:/dev \
     -v $(pwd)/app:/app \
     -p 80:80 \
     argonot-asc:dev
   ```

### **Arduino Controller Setup**

#### **Motor Controller Code**
```cpp
// Upload to each motor control Arduino Nano
// Expects serial commands: "DIR:FORWARD,SPEED:15\n"
// Responds with motor status
```

#### **LED Controller Code** 
```cpp
// Upload to LED control Arduino Nano  
// Expects serial commands: "BRIGHTNESS:0:75\n"
// Controls 4-channel LED output
```

### **Hardware Configuration**

#### **I2C Device Addresses**
```python
# Multiplexer addresses
PRIMARY_MUX = 0x77    # TCA9548A
SECONDARY_MUX = 0x71  # TCA9548A

# Sensor addresses  
CURRENT_SENSORS = [0b1110000, 0b1110011, 0b1111100, 0b1111111]
BME280_ADDRESS = 0x76
PCA9685_ADDRESS = 0x40  # Default PWM controller
MOTOR_BOARD_ADDRESS = 0b1000001
```

#### **GPIO Pin Configuration**
```python
# PWM output pins (Raspberry Pi)
PWM_PINS = [12, 19]  # GPIO pins for servo control backup
```

### **API Endpoints**

#### **Motion Control**
- `POST /v1.0/start_motion` - Initialize motor controllers
- `POST /v1.0/stop_motion` - Stop motors and disable controller
- `WebSocket /ws/joystick` - Real-time joystick input

#### **Hardware Control**
- `POST /v1.0/led_toggle` - Toggle LED channel on/off
- `POST /v1.0/led_brightness` - Set LED brightness (0-100%)
- `POST /v1.0/motor_toggle` - Toggle motor power
- `POST /v1.0/cam_toggle` - Switch camera feeds

#### **Sensor Data**
- `GET /v1.0/sensor_data` - Get current/power sensor readings
- `GET /v1.0/bme_data` - Get environmental sensor data

### **GitHub Actions Deployment**

The project includes automated deployment via GitHub Actions:

```yaml
# .github/workflows/main.yml
# Automatically builds and deploys BlueOS extension
# Requires Docker Hub credentials and GitHub secrets
```

**Required Secrets:**
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password  
- `GITHUB_TOKEN` - GitHub access token

**Required Variables:**
- `IMAGE_NAME` - Docker image name
- `MY_NAME` - Author name
- `MY_EMAIL` - Author email
- `ORG_NAME` - Organization name
- `ORG_EMAIL` - Organization email

### **Testing and Debugging**

1. **Serial Communication Testing**
   ```bash
   # Test motor communication
   echo "DIR:FORWARD,SPEED:10" > /dev/MOT1
   
   # Test LED communication  
   echo "BRIGHTNESS:0:50" > /dev/LEDS
   ```

2. **I2C Device Detection**
   ```bash
   # Scan for I2C devices
   i2cdetect -y 1
   ```

3. **Log Monitoring**
   ```bash
   # Monitor application logs
   docker logs -f container_name
   ```

### **Contributing**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-control`)
3. Commit changes (`git commit -am 'Add new control feature'`)
4. Push to branch (`git push origin feature/new-control`) 
5. Create Pull Request

### **Hardware Integration Notes**

- **Motor Controllers**: Ensure proper serial port permissions and baud rate configuration
- **I2C Multiplexers**: Verify addressing and channel selection logic
- **Sensor Calibration**: BME280 and current sensors may require calibration
- **PWM Timing**: Servo control requires precise timing - verify PCA9685 frequency settings
- **Power Management**: Monitor power consumption via current sensors to prevent overload

### **Troubleshooting**

**Common Issues:**
- **Serial Port Access**: Verify `/dev/MOT*` and `/dev/LEDS` permissions
- **I2C Communication**: Check `i2cdetect -y 1` output for device presence
- **Docker Permissions**: Ensure `--privileged` flag and volume mounts for hardware access
- **WebSocket Connection**: Verify network connectivity and firewall settings

---

## 📄 License

This project is developed by SymbyTech for underwater robotics applications.

## 🤝 Support

For technical support and questions:
- **Company**: SymbyTech
- **Project**: Argonot Smart Control
- **Version**: 0.0.1
- **Author**: Daniel Ikekwem

