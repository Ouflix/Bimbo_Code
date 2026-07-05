from gpiozero import Motor
import time
import math


# Puntea A motors
motor_a1 = Motor(forward=17, backward=27, enable=22)
motor_a2 = Motor(forward=23, backward=24, enable=25)

# Puntea B motors
motor_b1 = Motor(forward=16, backward=20, enable=13)
motor_b2 = Motor(forward=5, backward=6, enable=12)

WHEEL_DIAMETER = 63
WHEEL_CIRCUMFERENCE = math.pi * WHEEL_DIAMETER

AXEL_LENGHT = 130
ROBO_ROT_CIRCUMFERENCE = math.pi * AXEL_LENGHT

LINEAR_SPEED_MM_PER_SEC = 100
ROTATIONAL_DEG_PER_SEC = 50



def move(mm):
    duration = mm/ LINEAR_SPEED_MM_PER_SEC
    
    
    motor_a1.forward(1)
    motor_a2.forward(1)
    motor_b1.forward(1)
    
    motor_b2.backward(1)
    
    time.sleep(duration)

    motor_a1.stop()
    motor_a2.stop()
    motor_b1.stop()
    motor_b2.stop()
    
def moveUntilStopped(duration):
    motor_a1.forward(1)
    motor_a2.forward(1)
    motor_b1.forward(1)
    
    motor_b2.backward(1)
    
    time.sleep(duration)

    motor_a1.stop()
    motor_a2.stop()
    motor_b1.stop()
    motor_b2.stop()
    

def turn(degress, duration):
	
	if degress > 0:
		motor_a1.forward(1)
		motor_a2.backward(1)
		motor_b1.forward(1)
		motor_b2.forward(1)
	elif degress < 0:
		motor_a1.backward(1)
		motor_a2.forward(1)
		motor_b1.backward(1)
		motor_b2.backward(1)

	time.sleep(duration)
    

	motor_a1.stop()
	motor_a2.stop()
	motor_b1.stop()
	motor_b2.stop()


if __name__ == "__main__":
	turn(-1, 3)
