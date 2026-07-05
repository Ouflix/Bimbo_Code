import cv2
import base64

def encode_image(path):
	img = cv2.imread(path)
	jpg_img = cv2.imencode('.jpg', img)
	b64_string = base64.b64encode(jpg_img[1]).decode('utf-8')
	return b64_string
	
	
