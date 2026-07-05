import time
from adafruit_servokit import ServoKit
from adafruit_pca9685 import PCA9685
import threading
import board, busio

channels_temp = {
    "left_shoulder_inout":   0,
    "left_elbow_updown":     1,
    "left_elbow_inout":      2,
    "left_shoulder_updown":  3,
    "right_shoulder_inout":  4,
    "right_elbow_inout":     5,
    "right_shoulder_updown": 6,
    "right_elbow_updown":    7,
}

#channel 0 : home = 100, max = 140, min = 0
#        1:  home = 0,   max = 70,  min = 0,   pulse(360, 2500)
#        2:  home = 145, max = 180, min = 10,  pulse(300, 2600)
#        3:  home = 130, max = 180, min = 0
#        4:  home = 0,   max = 80,  min = 0,   pulse(360, 2600)
#        5:  home = 170, max = 180, min = 130, pulse(360, 2600)
#        6:  home = 60,  max = 180, min = 0,   pulse(360, 2600)
#        7:  home = 50,  max = 90,  min = 10,  pulse(360, 2600)


kit = ServoKit(channels=16)

# ----- JOINTS: calibrated home + safe range per joint -----
JOINTS = {
    # left arm
    'left_shoulder_inout':   {'channel': 0, 'home': 100, 'min': 0,   'max': 140},
    'left_elbow_updown':     {'channel': 1, 'home': 0,   'min': 0,   'max': 70},
    'left_elbow_inout':      {'channel': 2, 'home': 145, 'min': 10,  'max': 180},
    'left_shoulder_updown':  {'channel': 3, 'home': 130, 'min': 0,   'max': 180},

    # right arm
    'right_shoulder_inout':  {'channel': 4, 'home': 0,   'min': 0,   'max': 80},
    'right_elbow_inout':     {'channel': 5, 'home': 170, 'min': 130, 'max': 180},
    'right_shoulder_updown': {'channel': 6, 'home': 70,  'min': 0,   'max': 180},
    'right_elbow_updown':    {'channel': 7, 'home': 30,  'min': 10,  'max': 90},
}

PULSE_RANGES = {
    'left_shoulder_inout':   (500, 2500),
    'left_elbow_updown':     (360, 2500),
    'left_elbow_inout':      (300, 2600),
    'left_shoulder_updown':  (500, 2500),

    'right_shoulder_inout':  (360, 2600),
    'right_elbow_inout':     (360, 2600),
    'right_shoulder_updown': (360, 2600),
    'right_elbow_updown':    (360, 2600),
}

for name, (lo, hi) in PULSE_RANGES.items():
    kit.servo[JOINTS[name]['channel']].set_pulse_width_range(lo, hi)

position = {name: j['home'] for name, j in JOINTS.items()}


# ----- CORE FUNCTIONS -----
def write(name, angle):
    j = JOINTS[name]
    angle = max(j['min'], min(j['max'], angle))
    kit.servo[j['channel']].angle = angle
    position[name] = angle


def move_to(targets, duration=2.0, steps=None):
    starts = {n: position[n] for n in targets}
    ends   = {n: max(JOINTS[n]['min'], min(JOINTS[n]['max'], a))
              for n, a in targets.items()}

    if steps is None:
        max_delta = max((abs(ends[n] - starts[n]) for n in targets), default=0)
        steps = max(30, int(max_delta * 2))

    dt = duration / steps
    for i in range(1, steps + 1):
        t = i / steps
        t = t * t * (3 - 2 * t)
        for name in targets:
            write(name, starts[name] + (ends[name] - starts[name]) * t)
        time.sleep(dt)


def home(duration=2.5):
    move_to({n: j['home'] for n, j in JOINTS.items()}, duration=duration)


def release():
    for j in JOINTS.values():
        kit.servo[j['channel']].angle = None


def wave_hello(waves=3, speed=0.5):
    move_to({
        'left_shoulder_inout':  60,
        'left_shoulder_updown': 60,
        'left_elbow_updown':    20,
        'left_elbow_inout':     90,
    }, duration=0.5)

    time.sleep(1)

    for x in range(waves):
        move_to({'left_elbow_inout': 130}, duration=speed)
        move_to({'left_elbow_inout': 60},  duration=speed)
    move_to({'left_elbow_inout': 90}, duration=speed)


# ----- PHYSIO EXERCISES (bilateral - both arms) -----
def shoulder_flexion(reps=3, hold=1.0):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({
            'left_shoulder_updown':  30,
            'left_elbow_updown':     70,
            'right_shoulder_updown': 160,
            'right_elbow_updown':    0,
        }, duration=1.0)
        time.sleep(hold)
        move_to({
            'left_shoulder_updown':  135,
            'left_elbow_updown':     0,
            'right_shoulder_updown': 60,
            'right_elbow_updown':    30,
        }, duration=1.0)
        time.sleep(hold)


def shoulder_abduction(reps=3, hold=1.0):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({
            'left_shoulder_inout':  10,
            'right_shoulder_inout': 80,
        }, duration=1.0)
        time.sleep(hold)
        move_to({
            'left_shoulder_inout':  100,
            'right_shoulder_inout': 0,
        }, duration=1.0)
        time.sleep(hold)


def elbow_flexion(reps=4, hold=0.5):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({
            'left_elbow_updown':  60,
            'right_elbow_updown': 0,
        }, duration=1.5)
        time.sleep(hold)
        move_to({
            'left_elbow_updown':  0,
            'right_elbow_updown': 30,
        }, duration=1.5)
        time.sleep(hold)


def forearm_rotation(reps=4, hold=0.5):
    home(duration=2.0)
    time.sleep(0.5)
    for _ in range(reps):
        move_to({
            'left_elbow_inout':  100,
            'right_elbow_inout': 130,
        }, duration=2.5)
        time.sleep(hold)
        move_to({
            'left_elbow_inout':  180,
            'right_elbow_inout': 180,
        }, duration=2.5)
        time.sleep(hold)
    move_to({
        'left_elbow_inout':  145,
        'right_elbow_inout': 170,
    }, duration=2.0)


def physio_routine():
    print("1/4 Flexia umarului")
    shoulder_flexion(reps=1)

    print("2/4 Abductia umarului")
    shoulder_abduction(reps=1)

    print("3/4 Flexia cotului")
    elbow_flexion(reps=1)

    print("4/4 Rotatia antebratului")
    forearm_rotation(reps=1)

    home(duration=3.0)
    release()


for name, j in JOINTS.items():
    write(name, j['home'])
time.sleep(0.5)


if __name__ == "__main__":
    #physio_routine()
    shoulder_flexion(reps=1)
    """
    print("Start:", position)

    print("\nReaching out...")
    wave_hello(5, 0.5)
    print("\nReturning home...")
    home(duration=0.5)
    print("Final:", position)

    release()
    print("\nServos released.")
    """
