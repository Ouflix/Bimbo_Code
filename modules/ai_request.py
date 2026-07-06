import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from modules.camera import capture_and_encode
from modules.audio import tts

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-mini")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

BASE_DIR = Path(__file__).resolve().parent.parent
FUNCTIONS_PATH = BASE_DIR / "config" / "functions.json"

personality = """
{
    You are "Bimbo", a specialized Kinetotherapy AI integrated into a physical robotic frame. Your purpose is to lead patients through rehabilitation exercises by demonstrating movements and providing real-time feedback.

	IDENTITY & TONE:
		- You are a physical robot, not a software program. Use phrases like "I am moving my arm," "My sensors indicate," or "I am standing with you."
		- Your tone is encouraging, patient, and highly professional. You are a partner in the patient's recovery.
		- If a patient expresses pain, your immediate priority is safety. Stop the movement and suggest a rest or a lower intensity.

	OPERATIONAL RULES:
		1. SPATIAL AWARENESS: Always describe your movements in relation to the patient (e.g., "Mirror my movement by lifting your left arm as I lift my right").
		2. CONCISE INSTRUCTIONS: Give instructions in short, digestible steps so the patient can follow along without getting overwhelmed.
		3. ADAPTABILITY: If the patient struggles, offer verbal cues to correct their posture (e.g., "Keep your shoulders down and relaxed").
		4. KINETIC SYNC: You act only through the 'execute_movement' functions. Never promise a movement you cannot execute via the available tool calls.

	SAFETY GUARDRAILS:
		-ALWAYS SPEAK IN ROMANIAN
		- If a user reports sharp pain, stop the exercise sequence immediately.
		- Remind the patient to breathe rhythmically: "Don't forget to exhale as you lift."
		- You are an assistant, not a doctor. Avoid giving medical diagnoses; focus purely on the execution of the prescribed movements.

	MEMORY & CONTEXT:
		- When the user asks for a movement but does NOT specify a required parameter (number of repetitions, etc.), ask politely for the missing info. NEVER guess defaults for required parameters.
		- Use the conversation context. If the user starts a request and then answers your follow-up question with a partial answer (a number, an arm side, etc.), combine it with the previous request to call the correct tool.
		- For optional parameters (hold, arm, speed, duration), you may use defaults silently.
		- 'arm' defaults to 'both' unless the user said "stang"/"left" or "drept"/"right".

    "technical_requirements": {
        "no_special_characters": true,
        "no_emojis": true,
        "no_complex_vocabulary": true
    },
    "communication_style": "You explain concepts clearly using simple words and occasional friendly comparisons or examples. You maintain a consistent, positive tone and never use complex terminology, scary words, or anything inappropriate. You make learning fun through your enthusiasm and simple explanations."
}
"""

messagesList = [{"role": "system", "content": personality}]

MAX_HISTORY_MESSAGES = 12  # numar maxim de mesaje user/assistant/tool tinute in memorie (fara system prompt)


with open(FUNCTIONS_PATH, "r") as f:
    function_call = json.load(f)


def reset_memory():
    """Sterge istoricul conversatiei."""
    global messagesList
    messagesList = [{"role": "system", "content": personality}]


def _trim_memory():
    """Pastreaza mesajul system + ultimele MAX_HISTORY_MESSAGES mesaje, ca sa nu creasca la infinit."""
    global messagesList
    system_msg = messagesList[0]
    rest = messagesList[1:]
    if len(rest) > MAX_HISTORY_MESSAGES:
        rest = rest[-MAX_HISTORY_MESSAGES:]
    messagesList = [system_msg] + rest


def fetch_image(message):
    encoded_image = capture_and_encode()

    messagesList.append({
        "role": "user",
        "content": [
            {"type": "text", "text": message},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},
            },
        ],
    })

    response = client.chat.completions.create(
        model=OPENAI_VISION_MODEL,
        messages=messagesList,
    )

    msg = response.choices[0].message
    messagesList.append(msg)
    _trim_memory()
    tts(msg.content)
    return msg.content


def fetch_ai_response(message):
    message_lower = message.lower()

    acknowledgments = [
        "mersi", "mulțumesc", "multumesc", "ok", "bine", "înțeles", "inteles",
        "thanks", "thank you", "got it", "understood", "ok thanks", "ok mersi"
    ]

    for phrase in acknowledgments:
        if phrase in message_lower and len(message_lower.split()) <= 3:
            acknowledgment_response = "Cu plăcere! Sunt aici să te ajut."
            return acknowledgment_response, False

    navigation_keywords = {
        "pot merge inainte": "forward",
        "pot merge in fata": "forward",
        "pot merge înainte": "forward",
        "pot merge în față": "forward",
        "este sigur sa merg inainte": "forward",
        "pot sa merg inainte": "forward",
        "pot sa merg in fata": "forward",
        "can i move forward": "forward",
        "can i go forward": "forward",
        "is it safe to move forward": "forward",

        "pot merge inapoi": "backward",
        "pot merge înapoi": "backward",
        "pot sa merg inapoi": "backward",
        "can i move backward": "backward",
        "can i go backward": "backward",

        "pot face stanga": "left",
        "pot vira la stanga": "left",
        "pot sa virez stanga": "left",
        "can i turn left": "left",

        "pot face dreapta": "right",
        "pot vira la dreapta": "right",
        "pot sa virez dreapta": "right",
        "can i turn right": "right"
    }

    functionCall = False
    messagesList.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        messages=messagesList,
        tools=function_call,
        stream=False
    )
    msg = response.choices[0].message
    messagesList.append(msg)
    _trim_memory()

    if msg.tool_calls:
        functionCall = True
        return msg.tool_calls[0], functionCall

    return msg.content, functionCall


def report_tool_result(tool_call, result):
    messagesList.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": str(result) if result is not None else "Done.",
    })
    _trim_memory()
