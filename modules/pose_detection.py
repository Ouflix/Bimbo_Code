from picamera2 import Picamera2
import cv2
import mediapipe as mp
import math
from collections import deque
from modules.audio import tts 

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"}))
def pose_detect(index):
	mp_pose = mp.solutions.pose
	mp_draw = mp.solutions.drawing_utils
	pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)

	picam2.start()

	buffer = deque(maxlen=8)
	
	def angle(a, b, c):
		rad = math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x)
		deg = abs(math.degrees(rad))
		return deg if deg <= 180 else 360 - deg

	def detect_pose(lm):
		L = mp_pose.PoseLandmark

		indices = [L.LEFT_SHOULDER, L.RIGHT_SHOULDER, L.LEFT_ELBOW,
				   L.RIGHT_ELBOW, L.LEFT_WRIST, L.RIGHT_WRIST,
				   L.LEFT_HIP, L.RIGHT_HIP]
		if not all(lm[i.value].visibility > 0.7 for i in indices):
			return "LOW_VISIBILITY"

		l_shoulder = lm[L.LEFT_SHOULDER.value]
		r_shoulder = lm[L.RIGHT_SHOULDER.value]
		l_elbow = lm[L.LEFT_ELBOW.value]
		r_elbow = lm[L.RIGHT_ELBOW.value]
		l_wrist = lm[L.LEFT_WRIST.value]
		r_wrist = lm[L.RIGHT_WRIST.value]
		l_hip = lm[L.LEFT_HIP.value]
		r_hip = lm[L.RIGHT_HIP.value]

		l_shoulder_angle = angle(l_hip, l_shoulder, l_elbow)
		r_shoulder_angle = angle(r_hip, r_shoulder, r_elbow)
		l_elbow_angle = angle(l_shoulder, l_elbow, l_wrist)
		r_elbow_angle = angle(r_shoulder, r_elbow, r_wrist)
	 
		# POSE 1: Arms raised forward ~90°, elbows straight
		if (150 < l_shoulder_angle < 180 and
			150 < r_shoulder_angle < 180 and
			l_elbow_angle > 140 and
			r_elbow_angle > 140):
			return "ARMS_FORWARD_90"

		# POSE 2: Arms raised ~90°, elbows flexed inward
		if (5 < l_shoulder_angle < 25 and
			5 < r_shoulder_angle < 25 and
			45 < l_elbow_angle < 80 and
			45 < r_elbow_angle < 80):
			return "ELBOWS_FLEXED"

		return "NEUTRAL"
	
	while True:
		frame = picam2.capture_array()
		results = pose.process(frame)

		bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

		if results.pose_landmarks:
			mp_draw.draw_landmarks(bgr, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
			lm = results.pose_landmarks.landmark

			raw_pose = detect_pose(lm)
			buffer.append(raw_pose)
			stable_pose = max(set(buffer), key=buffer.count)
			if (index == 0 and stable_pose == "ARMS_FORWARD_90"):
			 print("ARMS FLEXED POSE DETECTED")
			 tts("Bravo! Ai flexat corect bratele")
			 break
			elif (index  == 1 and stable_pose == "ELBOWS_FLEXED"):
			 tts("Felicitari! Te descurci de minune. Ai flexat foarte bine coatele, tine-o tot asa!")
			 break
			 
			# Debug angles
			L = mp_pose.PoseLandmark
			ls = angle(lm[L.LEFT_HIP.value], lm[L.LEFT_SHOULDER.value], lm[L.LEFT_ELBOW.value])
			le = angle(lm[L.LEFT_SHOULDER.value], lm[L.LEFT_ELBOW.value], lm[L.LEFT_WRIST.value])

			color = (0, 255, 0) if stable_pose != "NEUTRAL" else (255, 255, 255)
			cv2.putText(bgr, stable_pose, (10, 40),
						cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
			cv2.putText(bgr, f"Shoulder: {ls:.0f}  Elbow: {le:.0f}", (10, 80),
						cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

		cv2.imshow('Pose Detection', bgr)
		if cv2.waitKey(1) & 0xFF == ord('q'):
			break

	picam2.stop()
	cv2.destroyAllWindows()

if __name__ == "__main__":
	pose_detect(0)
