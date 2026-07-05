import os
from pathlib import Path
import pyaudio
import numpy as np
from openwakeword.model import Model

MODEL_PATH = os.getenv(
    "WAKEWORD_MODEL_PATH",
    str(Path(__file__).resolve().parent.parent / "assets" / "hey_bimbo.onnx"),
)

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

try:
    while True:
        raw_data = mic_stream.read(CHUNK_SIZE, exception_on_overflow=False)
        audio_frame = np.frombuffer(raw_data, dtype=np.int16)
        
        prediction = oww_model.predict(audio_frame)
        score = oww_model.prediction_buffer[model_key][-1]
        
        if score > 0.5:
            print(f"Detected! (Score: {score:.2f})")

except KeyboardInterrupt:
    pass
finally:
    mic_stream.stop_stream()
    mic_stream.close()
    audio.terminate()
