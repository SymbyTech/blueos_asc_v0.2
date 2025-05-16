import serial
import socketio
import threading
import queue

# Serial port configuration
NANO2_SERIAL_PORT = '/dev/MOT1'  # Left motor
NANO1_SERIAL_PORT = '/dev/MOT2'  # Right motor
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
        self.current_command = None
        self.previous_command = None
        self.speed = 0
        self.direction_one = "STOP"
        self.direction_two = "STOP"

    def update(self, speed, direction_one, direction_two):
        if (self.speed != speed or self.direction_one != direction_one or self.direction_two != direction_two):
            self.speed = speed
            self.direction_one = direction_one
            self.direction_two = direction_two
            return True
        return False

state_manager = StateManager()

# Serial communication thread
def serial_worker():
    try:
        nano1_serial = serial.Serial(NANO1_SERIAL_PORT, BAUD_RATE, timeout=1)
        nano2_serial = serial.Serial(NANO2_SERIAL_PORT, BAUD_RATE, timeout=1)
        print("Serial ports initialized.")

        while True:
            command = command_queue.get()
            if command is None:
                break

            try:
                # Write commands to the correct motors
                nano1_serial.write(command["motor1"].encode())  # Right motor
                nano2_serial.write(command["motor2"].encode())  # Left motor

                if nano1_serial.in_waiting:
                    response1 = nano1_serial.readline().decode().strip()
                    print(f"Right motor response: {response1}")
                if nano2_serial.in_waiting:
                    response2 = nano2_serial.readline().decode().strip()
                    print(f"Left motor response: {response2}")

            except Exception as e:
                print(f"Serial communication error: {e}")

        nano1_serial.close()
        nano2_serial.close()
    except Exception as e:
        print(f"Error initializing serial ports: {e}")

def send_command_to_motors(speed, direction_one, direction_two):
    # Map directions: motor1 = right motor, motor2 = left motor
    motor1_command = f"DIR:{direction_two},SPEED:{speed}\n"  # Right motor
    motor2_command = f"DIR:{direction_one},SPEED:{speed}\n"  # Left motor
    command_queue.put({"motor1": motor1_command, "motor2": motor2_command})

# Safe axis parser
def parse_axis(data, target_index):
    for axis in data.get('axes', []):
        if axis.get('index') == target_index:
            try:
                return float(axis.get('value', 0.0))
            except (ValueError, TypeError):
                return 0.0
    return 0.0

# Joystick event handlers
@sio.event
def connect():
    print("Connected to the server!")

@sio.event
def disconnect():
    print("Disconnected from the server.")

@sio.on('joystick_response')
def on_joystick_data(data):
    try:
        y_axis = parse_axis(data, 1)
        x_axis = parse_axis(data, 2)

        speed = int(abs(y_axis) * MAX_SPEED) if abs(y_axis) > 0.1 else 0

        if y_axis < -0.5:  # Forward
            if x_axis < -0.5:
                if state_manager.update(speed, "FORWARD", "BACKWARD"):
                    send_command_to_motors(speed // 2, "FORWARD", "BACKWARD")
            elif x_axis > 0.5:
                if state_manager.update(speed, "BACKWARD", "FORWARD"):
                    send_command_to_motors(speed // 2, "BACKWARD", "FORWARD")
            else:
                if state_manager.update(speed, "FORWARD", "FORWARD"):
                    send_command_to_motors(speed, "FORWARD", "FORWARD")
        elif y_axis > 0.5:  # Backward
            if x_axis < -0.5:
                if state_manager.update(speed, "FORWARD", "BACKWARD"):
                    send_command_to_motors(speed // 2, "FORWARD", "BACKWARD")
            elif x_axis > 0.5:
                if state_manager.update(speed, "BACKWARD", "FORWARD"):
                    send_command_to_motors(speed // 2, "BACKWARD", "FORWARD")
            else:
                if state_manager.update(speed, "BACKWARD", "BACKWARD"):
                    send_command_to_motors(speed, "BACKWARD", "BACKWARD")
        elif x_axis < -0.5:
            if state_manager.update(MAX_SPEED, "FORWARD", "BACKWARD"):
                send_command_to_motors(MAX_SPEED, "FORWARD", "BACKWARD")
        elif x_axis > 0.5:
            if state_manager.update(MAX_SPEED, "BACKWARD", "FORWARD"):
                send_command_to_motors(MAX_SPEED, "BACKWARD", "FORWARD")
        else:
            if state_manager.update(0, "STOP", "STOP"):
                send_command_to_motors(0, "STOP", "STOP")

    except Exception as e:
        print(f"Error processing joystick data: {e}")

# Start serial thread
serial_thread = threading.Thread(target=serial_worker, daemon=True)
serial_thread.start()

# Connect to joystick server
try:
    sio.connect('http://192.168.1.44:9009')
    sio.wait()
except Exception as e:
    print(f"Socket.IO connection error: {e}")

# Stop serial worker thread
command_queue.put(None)
serial_thread.join()
