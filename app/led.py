import serial
import threading
import queue

# Configuration
LED_NANO_PORT = '/dev/LEDS'   # Update to your actual port
BAUD_RATE = 9600

# Thread-safe command queue
command_queue = queue.Queue()

class LEDController:
    def __init__(self):
        self.serial_thread = threading.Thread(target=self.serial_worker, daemon=True)
        self.serial_thread.start()
        # Track switch states and brightness values
        self.switch_states = {0: False, 1: False, 2: False, 3: False}
        self.brightness_values = {0: 0, 1: 0, 2: 0, 3: 0}
    
    def serial_worker(self):
        try:
            with serial.Serial(LED_NANO_PORT, BAUD_RATE, timeout=1) as led_serial:
                print("LED Nano serial port initialized.")
                while True:
                    command = command_queue.get()
                    if command is None:
                        break
                    try:
                        led_serial.write(command.encode())
                    except Exception as e:
                        print(f"Serial communication error: {e}")
        except Exception as e:
            print(f"Error initializing serial port: {e}")

    def set_switch_state(self, index, state):
        # Store the switch state (True for ON, False for OFF)
        self.switch_states[index] = bool(state)
        return self.switch_states[index]
    
    def get_switch_state(self, index):
        # Return switch state (default to False if not found)
        return self.switch_states.get(index, False)
    
    def get_brightness(self, index):
        # Return current brightness (default to 0 if not found)
        return self.brightness_values.get(index, 0)

    def set_brightness(self, index, brightness):
        # Clamp brightness to 0-100 range
        brightness = max(0, min(100, brightness))
        # Store the brightness value
        self.brightness_values[index] = brightness
        # Generate command and send to Arduino
        command = f"BRIGHTNESS:{index}:{brightness}\n"
        command_queue.put(command)

# Global instance
led_controller = LEDController()