## README: Assigning Persistent Device IDs on Raspberry Pi with udev

This guide describes how to create stable, human-friendly device names (e.g., `/dev/LEDS`, `/dev/MOT1`, `/dev/MOT2`) for multiple Arduino Nano boards connected via USB serial on a Raspberry Pi. By using udev rules that match each board’s unique USB attributes, the OS will automatically generate the symlinks every time the device is plugged in—regardless of which USB port or `ttyUSB` number is assigned.

---

### Prerequisites

* A Raspberry Pi (or other Linux system) with `udev` installed.
* Arduino Nano boards (or similar devices) using unique USB-Serial converters (e.g., FTDI FT232R).
* sudo privileges to create and reload udev rules.

---

### 1. Identify the device attributes

1. Plug in the Nano board to any USB port.
2. Determine which `/dev/ttyUSB*` entry was created (e.g., `/dev/ttyUSB0`, `/dev/ttyUSB1`, etc.).
3. Run the following command, replacing the device name if necessary:

   ```bash
   udevadm info -q property -n /dev/ttyUSB0
   ```
4. Note the following properties for that device:

   * `ID_VENDOR_ID` (e.g., `0403`)
   * `ID_MODEL_ID`  (e.g., `6001`)
   * `ID_SERIAL_SHORT` (e.g., `A5069RR4`)

Repeat for each Nano board, recording its unique `ID_SERIAL_SHORT`.

---

### 2. Create udev rules file

1. Open (or create) the udev rules file with sudo:

   ```bash
   sudo nano /etc/udev/rules.d/99-nanos.rules
   ```
2. Paste rules for each board, substituting your recorded serials:

   ```bash
   # LED Nano
   SUBSYSTEM=="tty", \
   ENV{ID_VENDOR_ID}=="0403", \
   ENV{ID_MODEL_ID}=="6001", \
   ENV{ID_SERIAL_SHORT}=="A5069RR4", \
   SYMLINK+="LEDS"

   # Motor Nano 1
   SUBSYSTEM=="tty", \
   ENV{ID_VENDOR_ID}=="0403", \
   ENV{ID_MODEL_ID}=="6001", \
   ENV{ID_SERIAL_SHORT}=="A906QTBJ", \
   SYMLINK+="MOT1"

   # Motor Nano 2
   SUBSYSTEM=="tty", \
   ENV{ID_VENDOR_ID}=="0403", \
   ENV{ID_MODEL_ID}=="6001", \
   ENV{ID_SERIAL_SHORT}=="A50285BI", \
   SYMLINK+="MOT2"
   ```
3. Save (`Ctrl+O`) and exit (`Ctrl+X`).

---

### 3. Reload udev rules and trigger

Run the following commands to apply and test your new rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Alternatively, unplug and re-plug each Nano board.

---

### 4. Verify the symlinks

After reloading, check that each friendly name points to the correct serial device:

```bash
ls -l /dev/LEDS   # should point to /dev/ttyUSBx for LED Nano
ls -l /dev/MOT1   # should point to /dev/ttyUSBy for Motor Nano 1
ls -l /dev/MOT2   # should point to /dev/ttyUSBz for Motor Nano 2
```

If everything is correct, you can now use `/dev/LEDS`, `/dev/MOT1`, and `/dev/MOT2` in your scripts and applications without worrying about changing device numbers.

---

### 5. Using friendly names in your code

In Python (with `pyserial`):

```python
import serial

# Example: open LED Nano:
ser_led = serial.Serial('/dev/LEDS', 115200)

# Motor 1:
ser_mot1 = serial.Serial('/dev/MOT1', 115200)

# Motor 2:
ser_mot2 = serial.Serial('/dev/MOT2', 115200)
```

Or in Bash scripts:

```bash
echo -n I > /dev/LEDS
```

Now your applications can reference devices by their logical names, making your setup robust and maintainable.
