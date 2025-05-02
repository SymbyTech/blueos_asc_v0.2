import serial
import socketio
import time
import threading
import queue

# Serial port configuration
NANO1_SERIAL_PORT = '/dev/MOT1'  # Left motor
NANO2_SERIAL_PORT = '/dev/MOT2'  # Right motor
BAUD_RATE = 9600

# Max speed
MAX_SPEED = 20

# Socket.IO Client
sio = socketio.Client()

# Thread-safe command queue
command_queue = queue.Queue()

# Track joystick state
class StateManager:
    def __init__(self):
        self.current_command = None  # Current command active ("FORWARD", "SPIN", etc.)
        self.previous_command = None  # To manage transitions
        self.speed = 0
        self.direction_one = "STOP"
        self.direction_two = "STOP"

    def update(self, speed, direction_one, direction_two):
        """Update motor state if there is a change."""
        if (self.speed != speed or self.direction_one != direction_one or self.direction_two != direction_two):
            self.speed = speed
            self.direction_one = direction_one
            self.direction_two = direction_two
            return True  # State changed
        return False  # No change

# Initialize state manager
state_manager = StateManager()

# Serial communication thread
def serial_worker():
    """Background thread to handle serial communication."""
    try:
        # Open serial connections
        nano1_serial = serial.Serial(NANO1_SERIAL_PORT, BAUD_RATE, timeout=1)
        nano2_serial = serial.Serial(NANO2_SERIAL_PORT, BAUD_RATE, timeout=1)
        print("Serial ports initialized.")

        while True:
            # Process commands from the queue
            command = command_queue.get()
            if command is None:  # Exit signal
                break

            # Send commands to both motors
            try:
                nano1_serial.write(command["motor1"].encode())
                nano2_serial.write(command["motor2"].encode())

                # Optional: Read responses
                if nano1_serial.in_waiting:
                    response1 = nano1_serial.readline().decode().strip()
                    print(f"Left motor response: {response1}")
                if nano2_serial.in_waiting:
                    response2 = nano2_serial.readline().decode().strip()
                    print(f"Right motor response: {response2}")

            except Exception as e:
                print(f"Serial communication error: {e}")

        # Close serial connections
        nano1_serial.close()
        nano2_serial.close()
    except Exception as e:
        print(f"Error initializing serial ports: {e}")

# Function to add commands to the queue
def send_command_to_motors(speed, direction_one, direction_two):
    """Format and enqueue motor commands."""
    motor1_command = f"DIR:{direction_one},SPEED:{speed}\n"
    motor2_command = f"DIR:{direction_two},SPEED:{speed}\n"
    command_queue.put({"motor1": motor1_command, "motor2": motor2_command})

# Joystick event handler
@sio.event
def connect():
    print("Connected to the server!")

@sio.event
def disconnect():
    print("Disconnected from the server.")

@sio.on('joystick_response')
def on_joystick_data(data):
    try:
        # Extract and convert axis values safely
        y_axis = next((float(axis['value']) for axis in data.get('axes', []) if axis['index'] == 1), 0.0)
        x_axis = next((float(axis['value']) for axis in data.get('axes', []) if axis['index'] == 2), 0.0)

        speed = int(abs(y_axis) * MAX_SPEED) if abs(y_axis) > 0.1 else 0

        if y_axis < -0.5:  # Forward
            if x_axis < -0.5:  # Forward Left
                if state_manager.update(speed, "FORWARD", "BACKWARD"):
                    send_command_to_motors(speed // 2, "FORWARD", "BACKWARD")
            elif x_axis > 0.5:  # Forward Right
                if state_manager.update(speed, "BACKWARD", "FORWARD"):
                    send_command_to_motors(speed // 2, "BACKWARD", "FORWARD")
            else:
                if state_manager.update(speed, "FORWARD", "FORWARD"):
                    send_command_to_motors(speed, "FORWARD", "FORWARD")
        elif y_axis > 0.5:  # Backward
            if x_axis < -0.5:  # Backward Left
                if state_manager.update(speed, "BACKWARD", "FORWARD"):
                    send_command_to_motors(speed // 2, "BACKWARD", "FORWARD")
            elif x_axis > 0.5:  # Backward Right
                if state_manager.update(speed, "FORWARD", "BACKWARD"):
                    send_command_to_motors(speed // 2, "FORWARD", "BACKWARD")
            else:
                if state_manager.update(speed, "BACKWARD", "BACKWARD"):
                    send_command_to_motors(speed, "BACKWARD", "BACKWARD")
        elif x_axis < -0.5:  # Spin Left
            if state_manager.update(MAX_SPEED, "BACKWARD", "FORWARD"):
                send_command_to_motors(MAX_SPEED, "BACKWARD", "FORWARD")
        elif x_axis > 0.5:  # Spin Right
            if state_manager.update(MAX_SPEED, "FORWARD", "BACKWARD"):
                send_command_to_motors(MAX_SPEED, "FORWARD", "BACKWARD")
        else:
            if state_manager.update(0, "STOP", "STOP"):
                send_command_to_motors(0, "STOP", "STOP")

    except Exception as e:
        print(f"Error processing joystick data: {e}")

# Start the serial worker thread
serial_thread = threading.Thread(target=serial_worker, daemon=True)
serial_thread.start()

# Connect to the joystick server
try:
    sio.connect('http://192.168.1.44:9009')
    sio.wait()
except Exception as e:
    print(f"Socket.IO connection error: {e}")

# Stop the serial worker thread
command_queue.put(None)
serial_thread.join()
