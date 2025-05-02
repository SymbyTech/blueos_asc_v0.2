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

    def set_brightness(self, index, brightness):
        brightness = max(0, min(100, brightness))
        command = f"BRIGHTNESS:{index}:{brightness}\n"
        command_queue.put(command)

# Global instance
led_controller = LEDController()