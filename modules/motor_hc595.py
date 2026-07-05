from gpiozero import OutputDevice
import threading
from modules.ultrasonicsensor import mesure_distance_low, mesure_distance_high
import time

DS = 16
CLOCK = 21
LATCH = 20
data_pin = OutputDevice(DS)
clock_pin = OutputDevice(CLOCK)
latch_pin = OutputDevice(LATCH)


def shift_out(byte1, byte2):
    for byte_value in [byte2, byte1]:
        for i in range(7, -1, -1):
            clock_pin.off()
            data_pin.value = (byte_value >> i) & 1
            clock_pin.on()
            
    latch_pin.off()
    
    time.sleep(0.001)
    latch_pin.on()

FORWARDS = 0b10011010
BACKWARDS = 0b01100101
RIGHT = 0b01010110
LEFT = 0b10101001
STOP = 0b00000000
UNRESERVED = 0b00000000
LINEAR_SPEED_MM_PER_SEC = 100

def move(mm):
    duration = mm / LINEAR_SPEED_MM_PER_SEC
    shift_out(FORWARDS, UNRESERVED)
    
    time.sleep(duration)
    shift_out(STOP, UNRESERVED)
    
def moveUntilStopped():
    time.sleep(3)
    shift_out(FORWARDS, UNRESERVED)
    
    a = mesure_distance_low()
    b = mesure_distance_high()
    
    
    while True:
        print(a, b)
        a = mesure_distance_low()    
        b = mesure_distance_high()
        if (a < 15 or b < 15):
            break
        
    shift_out(STOP, UNRESERVED)
    return True
    
def turn(degrees, duration):
    if degrees > 0:
        shift_out(RIGHT, UNRESERVED)
    elif degrees < 0:
        shift_out(LEFT, UNRESERVED)
    
    time.sleep(duration)
    shift_out(STOP, UNRESERVED)

if __name__ == "__main__":
    #moveUntilStopped()
    turn(1, 1)
