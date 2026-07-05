from gpiozero import DistanceSensor

sensor1 = DistanceSensor(24, 23)
sensor2 = DistanceSensor(26, 25)

def mesure_distance_low():
	return sensor1.distance * 100


def mesure_distance_high():
	return sensor2.distance * 100

