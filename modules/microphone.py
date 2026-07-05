import json
import os
import sys
from pathlib import Path
import pyaudio
from vosk import Model, KaldiRecognizer
from modules.audio import speaking

BASE_DIR = Path(__file__).resolve().parent.parent


def transcribe_en():
	model_path = os.getenv("VOSK_MODEL_PATH", str(BASE_DIR / "models" / "english-model"))

	if not os.path.exists(model_path):
		print("Modelul nu a fost gasit")
		sys.exit(1)

	model = Model(model_path)
	recognizer = KaldiRecognizer(model, 16000)

	p = pyaudio.PyAudio()
	stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
	stream.start_stream()
	
	
	print("Listening...")
	try:
		while True:
			if speaking():
				stream.stop_stream()
				stream.close()
				p.terminate()
				break
			print(speaking())
			data = stream.read(4096, exception_on_overflow=False)
			if data == 0:
				break 
			if recognizer.AcceptWaveform(data):
				result = json.loads(recognizer.Result())
				if result.get("text"):
					print("Ai zis:", result["text"])
					return result["text"]
	except KeyboardInterrupt:
		print("Oprire")
		stream.stop_stream()
		stream.close()
		p.terminate()
		
