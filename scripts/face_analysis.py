from deepface import DeepFace
from picamera2 import Picamera2
import cv2
import time

picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()
time.sleep(2)

image_path = "capture.png"
picam2.capture_file(image_path)

img = cv2.imread(image_path)

analysis = DeepFace.analyze(img, actions = ["emotion"])

dominant_emotion = analysis[0]["dominant_emotion"]
print(dominant_emotion)
