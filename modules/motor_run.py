import os
import serial
import time
from dotenv import load_dotenv

load_dotenv()

SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
BAUD_RATE = int(os.getenv("SERIAL_BAUD_RATE", "115200"))

print(f"Connecting to ESP32 on {SERIAL_PORT}...")
try:
    ser = serial.Serial(SERIAL_PORT, baudrate=BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Connected and ready!")
except serial.SerialException as e:
    print(f"WARNING: nu m-am putut conecta la ESP32 pe {SERIAL_PORT}: {e}")
    print("Comenzile de motor vor fi ignorate (fara crash).")
    ser = None


def set_motor_speed(speed_value):
    if ser and ser.is_open:
        speed_value = max(0, min(int(speed_value), 210))
        print(f"Sending speed command: {speed_value}")
        command = f"{speed_value}\n"
        ser.write(command.encode('utf-8'))


def close_serial():
    if 'ser' in globals() and ser and ser.is_open:
        ser.close()


if __name__ == "__main__":
    try:
        set_motor_speed(200)
        time.sleep(3)

        print("Test complete.")

    except KeyboardInterrupt:
        print("\nExecution interrupted! Stopping motors safely...")
        set_motor_speed(0)
    finally:
        ser.close()
        print("Serial port closed.")
