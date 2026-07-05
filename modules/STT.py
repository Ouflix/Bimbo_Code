import os
import pyaudio
import queue
import threading
import time
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.cloud import speech
from modules.audio import speaking

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CREDENTIALS_PATH = BASE_DIR / "config" / "speech_to_text_credentials.json"

def transcribe_ro():
    client_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(DEFAULT_CREDENTIALS_PATH))
    credentials = service_account.Credentials.from_service_account_file(client_file)
    RATE = 16000
    CHUNK = int(RATE / 10)
    
    client = speech.SpeechClient(credentials=credentials)
    streaming_config = speech.StreamingRecognitionConfig(
        config=speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code="ro-RO",
        ),
        interim_results=True,
        single_utterance=True,
    )
    

    q = queue.Queue()
    stop_recording = threading.Event()
    
    def record_audio():
        audio_interface = pyaudio.PyAudio()
        stream = audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        print("Vorbește...")
        
        try:
            while not stop_recording.is_set() and not speaking():
                data = stream.read(CHUNK, exception_on_overflow=False)
                q.put(data)
        finally:
            stream.stop_stream()
            stream.close()
            audio_interface.terminate()
            q.put(None)  
    
    def generator():
        while True:
            chunk = q.get()
            if chunk is None:
                return
            yield speech.StreamingRecognizeRequest(audio_content=chunk)
    
   
    audio_thread = threading.Thread(target=record_audio)
    audio_thread.daemon = True
    audio_thread.start()
    
    recognized_text = None
    
    try:
        responses = client.streaming_recognize(streaming_config, generator())
        
        for response in responses:
            
            if speaking():
          
                break
                
            for result in response.results:
                if result.is_final:
                    recognized_text = result.alternatives[0].transcript
                    print("Ai spus:", recognized_text)
                    stop_recording.set()  
                    return recognized_text
    
    except Exception as e:
        print("Eroare:", e)
    
    finally:
        stop_recording.set()
        
    return recognized_text
