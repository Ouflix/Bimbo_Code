import os
import threading
import time
import serial
from dotenv import load_dotenv

from arm_controller import request_stop, clear_stop, home, release

ready_event = threading.Event()

load_dotenv()

SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
BAUD_RATE = int(os.getenv("SERIAL_BAUD_RATE", "115200"))

try:
    ser = serial.Serial(SERIAL_PORT, baudrate=BAUD_RATE, timeout=1)
except serial.SerialException as e:
    print(f"esp32_listener: nu m-am putut conecta la ESP32 pe {SERIAL_PORT}: {e}")
    ser = None


def _listen_loop():
    if ser is None:
        print("esp32_listener: serial indisponibil, ascultarea STALL/RECOVERED e dezactivata.")
        return

    while True:
        if not (ser and ser.is_open):
            print("esp32_listener: conexiunea seriala nu mai e deschisa, opresc ascultarea.")
            return

        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
        except Exception as e:
            print(f"esp32_listener: eroare citire serial: {e}")
            time.sleep(1)
            continue

        if not line:
            continue

        if line == "READY":
            print("esp32_listener: senzor calibrat -- ancorez bratele la home (lent)")
            #home(duration=5.0)
            ready_event.set()
        elif line == "STALL":
            print("esp32_listener: STALL primit de la ESP32 -- opresc rutina si eliberez PWM-ul")
            request_stop()
            release()
        elif line == "RECOVERED":
            print("esp32_listener: RECOVERED primit - alimentare restaurata (rutina ramane oprita)")


def reset_cutoff():
    from arm_controller import write, JOINTS
    import time as _time

    clear_stop()

    for name, j in JOINTS.items():
        write(name, j['home'])

    if ser and ser.is_open:
        ser.write(b"RESET\n")
        print("esp32_listener: RESET trimis catre ESP32 - realimentez servourile la home")

    _time.sleep(2.0)


def wait_for_ready(timeout=15.0, ping_interval=1.0):
    import time as _time
    deadline = _time.time() + timeout
    while _time.time() < deadline:
        if ser and ser.is_open:
            ser.write(b"PING\n")
        if ready_event.wait(timeout=ping_interval):
            return True
    return False


def start_listener():
    thread = threading.Thread(target=_listen_loop, daemon=True, name="ESP32Listener")
    thread.start()
    return thread


def close_listener():
    if ser and ser.is_open:
        ser.close()
