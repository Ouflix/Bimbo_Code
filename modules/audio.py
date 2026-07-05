import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import time

load_dotenv()

LISTENING = False 

client = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_API_KEY"),
)
def tts(message):
	
	global LISTENING
	LISTENING = True
	
	audio = client.text_to_speech.convert(
		text=message,
		voice_id="mKd8xk6RaHtL3G1oKomo",
		model_id="eleven_multilingual_v2",
		output_format="mp3_44100_128",
	)

	play(audio)
	time.sleep(0.2)
	LISTENING = False
	
def speaking():
	return LISTENING
