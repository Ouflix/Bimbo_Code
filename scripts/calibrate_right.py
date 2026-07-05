"""
import time
from adafruit_servokit import ServoKit
from adafruit_pca9685 import PCA9685
import threading
import board, busio

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50

def pulse(channel, us):
    pca.channels[channel].duty_cycle = int(0xFFFF * us / 20000)


#channel 6: shoulder_right_updown: home: 70, min = 0, max = 180, pulse(360, 2600), actuaion = 180
        #4: shoulder_right_inout: home: 0, min = 0, max = 80, pulse(360, 2600), actuaion = 180
        #5: elbow_right_inout: home: 170, min = 130, max = 180 same pulse,actuation
        #7: elbow_right_updown: home: 30-, min = 10, max = 90, same pulse, actuation

kit = ServoKit(channels=16)
kit.servo[4].actuation_range = 180
kit.servo[4].set_pulse_width_range(360, 2600)
kit.servo[4].angle = None
"""

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from modules.arm_controller import move_to, home, release


# ===== SHOULDER FLEXION =====
def test_left_shoulder_flexion(reps=1, hold=1.0):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({
            'left_shoulder_updown': 30,
            'left_elbow_updown':    70,
        }, duration=1.5)
        time.sleep(hold)
        move_to({
            'left_shoulder_updown': 135,
            'left_elbow_updown':    0,
        }, duration=1.5)
        time.sleep(hold)
    home(duration=2.0)


def test_right_shoulder_flexion(reps=1, hold=1.0):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({
            'right_shoulder_updown': 160,
            'right_elbow_updown':    90,
        }, duration=1.5)
        time.sleep(hold)
        move_to({
            'right_shoulder_updown': 60,
            'right_elbow_updown':    50,
        }, duration=1.5)
        time.sleep(hold)
    home(duration=2.0)


# ===== SHOULDER ABDUCTION =====
def test_left_shoulder_abduction(reps=1, hold=1.0):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({'left_shoulder_inout': 20}, duration=1.5)
        time.sleep(hold)
        move_to({'left_shoulder_inout': 100}, duration=1.5)
        time.sleep(hold)
    home(duration=2.0)


def test_right_shoulder_abduction(reps=1, hold=1.0):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({'right_shoulder_inout': 80}, duration=1.5)
        time.sleep(hold)
        move_to({'right_shoulder_inout': 0}, duration=1.5)
        time.sleep(hold)
    home(duration=2.0)


# ===== ELBOW FLEXION =====
def test_left_elbow_flexion(reps=1, hold=0.5):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({'left_elbow_updown': 60}, duration=1.5)
        time.sleep(hold)
        move_to({'left_elbow_updown': 0}, duration=1.5)
        time.sleep(hold)
    home(duration=2.0)


def test_right_elbow_flexion(reps=1, hold=0.5):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({'right_elbow_updown': 90}, duration=1.5)
        time.sleep(hold)
        move_to({'right_elbow_updown': 50}, duration=1.5)
        time.sleep(hold)
    home(duration=2.0)


# ===== FOREARM ROTATION =====
def test_left_forearm_rotation(reps=1, hold=0.5):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({'left_elbow_inout': 60}, duration=2.0)
        time.sleep(hold)
        move_to({'left_elbow_inout': 180}, duration=2.0)
        time.sleep(hold)
    move_to({'left_elbow_inout': 145}, duration=1.5)
    home(duration=2.0)


def test_right_forearm_rotation(reps=1, hold=0.5):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({'right_elbow_inout': 180}, duration=2.0)
        time.sleep(hold)
        move_to({'right_elbow_inout': 130}, duration=2.0)
        time.sleep(hold)
    move_to({'right_elbow_inout': 170}, duration=1.5)
    home(duration=2.0)


TESTS = {
    '1': ('Left  shoulder flexion',   test_left_shoulder_flexion),
    '2': ('Right shoulder flexion',   test_right_shoulder_flexion),
    '3': ('Left  shoulder abduction', test_left_shoulder_abduction),
    '4': ('Right shoulder abduction', test_right_shoulder_abduction),
    '5': ('Left  elbow flexion',      test_left_elbow_flexion),
    '6': ('Right elbow flexion',      test_right_elbow_flexion),
    '7': ('Left  forearm rotation',   test_left_forearm_rotation),
    '8': ('Right forearm rotation',   test_right_forearm_rotation),
}


if __name__ == "__main__":
    while True:
        print("\n=== Physio movement tests ===")
        for k, (name, _) in TESTS.items():
            print(f"  {k}: {name}")
        print("  r: release all servos")
        print("  q: quit")

        try:
            choice = input("\nWhich? ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == 'q':
            break
        if choice == 'r':
            release()
            print("Released.")
            continue
        if choice in TESTS:
            name, func = TESTS[choice]
            print(f"\nRunning: {name}  (Ctrl+C to stop and release)")
            try:
                func()
                print("Done.")
            except KeyboardInterrupt:
                release()
                print("\n!!! Interrupted. All servos released. !!!")
        else:
            print("Invalid choice.")
