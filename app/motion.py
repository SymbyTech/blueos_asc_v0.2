import serial
import threading
import queue

# Serial port configuration
NANO2_SERIAL_PORT = '/dev/MOT2'  # Left motor
NANO1_SERIAL_PORT = '/dev/MOT1'  # Right motor
BAUD_RATE = 9600

# Max speed
MAX_SPEED = 20

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

# Serial connections
nano1_serial = None
nano2_serial = None

def initialize_motion_controller():
    """Initialize the serial connections for motors"""
    global nano1_serial, nano2_serial
    try:
        nano1_serial = serial.Serial(NANO1_SERIAL_PORT, BAUD_RATE, timeout=1)
        nano2_serial = serial.Serial(NANO2_SERIAL_PORT, BAUD_RATE, timeout=1)
        print("Serial ports initialized.")
        # Send stop command to ensure motors are stopped
        send_command_to_motors(0, "STOP", "STOP")
        return True
    except Exception as e:
        print(f"Error initializing serial ports: {e}")
        return False

def cleanup_motion_controller():
    """Close serial connections"""
    global nano1_serial, nano2_serial
    try:
        if nano1_serial:
            nano1_serial.close()
        if nano2_serial:
            nano2_serial.close()
    except Exception as e:
        print(f"Error closing serial ports: {e}")

def send_command_to_motors(speed, direction_one, direction_two):
    """Send command directly to motors via serial"""
    global nano1_serial, nano2_serial
    
    if not nano1_serial or not nano2_serial:
        # Try to initialize if not already done
        if not initialize_motion_controller():
            return
    
    try:
        # Map directions: motor1 = right motor, motor2 = left motor
        motor1_command = f"DIR:{direction_two},SPEED:{speed}\n"  # Right motor
        motor2_command = f"DIR:{direction_one},SPEED:{speed}\n"  # Left motor
        
        # Write commands to the correct motors
        nano1_serial.write(motor1_command.encode())  # Right motor
        nano2_serial.write(motor2_command.encode())  # Left motor

        if nano1_serial.in_waiting:
            response1 = nano1_serial.readline().decode().strip()
            print(f"Right motor response: {response1}")
        if nano2_serial.in_waiting:
            response2 = nano2_serial.readline().decode().strip()
            print(f"Left motor response: {response2}")
            
    except Exception as e:
        print(f"Serial communication error: {e}")
        # Try to reinitialize on error
        initialize_motion_controller()

# Safe axis parser
def parse_axis(data, target_index):
    for axis in data.get('axes', []):
        if axis.get('index') == target_index:
            try:
                return float(axis.get('value', 0.0))
            except (ValueError, TypeError):
                return 0.0
    return 0.0

# Process joystick data from WebSocket
def process_joystick_data(data):
    try:
        y_axis = parse_axis(data, 1)
        x_axis = parse_axis(data, 2)

        speed = int(abs(y_axis) * MAX_SPEED) if abs(y_axis) > 0.1 else 0

        if y_axis < -0.5:  # Forward
            if x_axis < -0.5:
                # Turn left while moving forward (left track slows/reverses)
                if state_manager.update(speed // 2, "FORWARD", "BACKWARD"):
                    command_queue.put({"speed": speed // 2, "direction_one": "FORWARD", "direction_two": "BACKWARD"})
            elif x_axis > 0.5:
                # Turn right while moving forward (right track slows/reverses)
                if state_manager.update(speed // 2, "BACKWARD", "FORWARD"):
                    command_queue.put({"speed": speed // 2, "direction_one": "BACKWARD", "direction_two": "FORWARD"})
            else:
                # Move straight forward
                if state_manager.update(speed, "FORWARD", "FORWARD"):
                    command_queue.put({"speed": speed, "direction_one": "FORWARD", "direction_two": "FORWARD"})
        elif y_axis > 0.5:  # Backward
            if x_axis < -0.5:
                # Turn left while moving backward
                if state_manager.update(speed // 2, "FORWARD", "BACKWARD"):
                    command_queue.put({"speed": speed // 2, "direction_one": "FORWARD", "direction_two": "BACKWARD"})
            elif x_axis > 0.5:
                # Turn right while moving backward
                if state_manager.update(speed // 2, "BACKWARD", "FORWARD"):
                    command_queue.put({"speed": speed // 2, "direction_one": "BACKWARD", "direction_two": "FORWARD"})
            else:
                # Move straight backward
                if state_manager.update(speed, "BACKWARD", "BACKWARD"):
                    command_queue.put({"speed": speed, "direction_one": "BACKWARD", "direction_two": "BACKWARD"})
        elif x_axis < -0.5:
            # Turn left in place
            if state_manager.update(MAX_SPEED, "FORWARD", "BACKWARD"):
                command_queue.put({"speed": MAX_SPEED, "direction_one": "FORWARD", "direction_two": "BACKWARD"})
        elif x_axis > 0.5:
            # Turn right in place
            if state_manager.update(MAX_SPEED, "BACKWARD", "FORWARD"):
                command_queue.put({"speed": MAX_SPEED, "direction_one": "BACKWARD", "direction_two": "FORWARD"})
        else:
            # Stop
            if state_manager.update(0, "STOP", "STOP"):
                command_queue.put({"speed": 0, "direction_one": "STOP", "direction_two": "STOP"})
    except Exception as e:
        print(f"Error processing joystick data: {e}")
