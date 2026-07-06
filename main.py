import os
from pathlib import Path
from dotenv import load_dotenv
from modules.ai_request import fetch_ai_response
from modules.ai_request import report_tool_result
from modules.pose_detection import pose_detect
from modules.arm_controller import shoulder_flexion, shoulder_abduction, elbow_flexion, forearm_rotation, physio_routine, wave_hello, home, release
from modules.movement_sequence import movement_sequence, moveUntilStopped
from modules.STT import transcribe_ro
from modules.audio import tts 
from modules.motor_run import close_serial, set_motor_speed
from modules.display import star_eye
import pyaudio
import numpy as np
import json
import requests
import time
import pygame
from openwakeword.model import Model

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

star_eye()
MODEL_PATH = os.getenv("WAKEWORD_MODEL_PATH", str(ASSETS_DIR / "hey_bimbo.onnx"))
BEEP_SOUND_PATH = os.getenv("BEEP_SOUND_PATH", str(ASSETS_DIR / "sounds" / "beep.mp3"))
ROBOT_SPEECH_PATH = os.getenv("ROBOT_SPEECH_PATH", str(ASSETS_DIR / "sounds" / "bimbo_speech_oncs.mp3"))

oww_model = Model(
    wakeword_models=[MODEL_PATH],
    inference_framework="onnx",
    vad_threshold=0.5 
)

model_key = list(oww_model.models.keys())[0]

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_SIZE = 1280

audio = pyaudio.PyAudio()
mic_stream = audio.open(
    format=FORMAT, 
    channels=CHANNELS, 
    rate=RATE, 
    input=True, 
    frames_per_buffer=CHUNK_SIZE
)


canProcess = True

FUNCTION_MAP = {
    "physio_routine":     physio_routine,
    "shoulder_flexion":   shoulder_flexion,
    "shoulder_abduction": shoulder_abduction,
    "elbow_flexion":      elbow_flexion,
    "forearm_rotation":   forearm_rotation,
    "wave_hello":         wave_hello,
    "home":               home,
    "release":            release,
    "set_motor_speed" : set_motor_speed,
    "pose_detect":        pose_detect
}


pygame.mixer.init()
try:
	while True:
			raw_data = mic_stream.read(CHUNK_SIZE, exception_on_overflow=False)
			audio_frame = np.frombuffer(raw_data, dtype=np.int16)
				
			prediction = oww_model.predict(audio_frame)
			score = oww_model.prediction_buffer[model_key][-1]
				
			if score > 0.5:
				pygame.mixer.music.load(BEEP_SOUND_PATH)
				pygame.mixer.music.play()

				while pygame.mixer.music.get_busy():
					pygame.time.Clock().tick(10)

				# FIX: transcrierea si procesarea se fac O SINGURA DATA, DUPA ce beep-ul s-a terminat
				# (inainte erau indentate in interiorul while-ului de mai sus si rulau in bucla)
				message = str(transcribe_ro())
				if message.lower() == "exit":
					canProcess = False
				elif message.lower() == "start":
					canProcess = True
				elif "robot" in message.lower() or "robotul" in message.lower():
					pygame.mixer.music.load(ROBOT_SPEECH_PATH)
					pygame.mixer.music.play()
					while pygame.mixer.music.get_busy():
						pygame.time.Clock().tick(10)

				if canProcess == True and message.lower() != "start":
					response, functionCall = fetch_ai_response(message)
					if functionCall == False:
						print("Answear:", response)
						tts(response)
					else:
						print(response)
						func_name = response.function.name
						func_args = json.loads(response.function.arguments)

						if func_name in FUNCTION_MAP:
							tts("Desigur")
							result = FUNCTION_MAP[func_name](**func_args)
							report_tool_result(response, result)
							print("Answear:", result)
						else:
							print(f"Functie necunoscuta: {func_name}")

				while mic_stream.get_read_available() > CHUNK_SIZE:
					mic_stream.read(CHUNK_SIZE, exception_on_overflow=False)
				oww_model.reset()

								
								
					
except KeyboardInterrupt:
	pass
finally:
	mic_stream.stop_stream()
	mic_stream.close()
	audio.terminate()
	close_serial()
