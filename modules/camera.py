import cv2
import time
from pathlib import Path
from modules.base64encoding import encode_image
from picamera2 import Picamera2 
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_IMAGE_PATH = BASE_DIR / "assets" / "temp" / "temp.jpg"

def capture():
	try:
		picam2 = Picamera2()
		picam2.start()
		time.sleep(1)

		frame = picam2.capture_array()
		picam2.stop()
		picam2.close()

		TEMP_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
		cv2.imwrite(str(TEMP_IMAGE_PATH), frame)
		print("Image captured")
		return True
	except Exception as e:
		print(f"Camera capture failed: {e}")
		return False
	
def capture_and_encode():
	status = capture()
	if status == True:
		return encode_image(str(TEMP_IMAGE_PATH))
		
		

