# Bimbo = Robot Umanoid Asistiv pentru Kinetoterapie

Bimbo este un robot umanoid asistiv conceput pentru a ghida pacienți prin exerciții
de kinetoterapie: demonstrează mișcările fizic, ascultă și înțelege comenzi vocale
în limba română, oferă feedback în timp real și urmărește vizual pacientul pentru
a verifica dacă exercițiile sunt executate corect. Proiectul este dezvoltat de mine
ca parte a pregătirii pentru **InfoEducație**.

## Ce face Bimbo

- **Ascultă în permanență** un cuvânt de trezire ("hey Bimbo") folosind un model
  local `openWakeWord`, fără a trimite audio în cloud până nu e nevoie.
- **Transcrie vorbirea în română** în timp real prin Google Cloud Speech-to-Text.
- **Conversează natural**, prin OpenAI, cu o personalitate dedicată de asistent de
  kinetoterapie: instrucțiuni scurte, ton încurajator, întreabă când îi lipsesc
  detalii (câte repetări, ce braț) și se oprește imediat dacă pacientul semnalează
  durere.
- **Vede și analizează pacientul**: verifică cu MediaPipe Pose dacă mișcarea (ex.
  ridicarea umerilor sau a coatelor) este executată corect, și poate urmări o
  persoană cu YOLOv8 pentru a se deplasa spre ea.
- **Execută mișcări fizice reale**: brațele sunt controlate prin servomotoare
  (PCA9685 + MG996R) cu rutine predefinite (flexie umăr, abducție, flexie cot,
  rotație antebraț, salut), iar baza mobilă e acționată de motoare DC comandate
  printr-un ESP32 conectat prin serial.
- **Vorbește** răspunsurile generate, folosind ElevenLabs pentru sinteza vocală.
- **Are o față expresivă**: un display TFT care randează un ochi animat (clipește,
  își mișcă privirea) pentru a da robotului un aspect mai viu.

## Arhitectură software

```
main.py                  → punctul de intrare: wake word → STT → AI → acțiune/TTS
modules/                 → toată logica robotului
  ai_request.py          → conversația cu OpenAI + apelurile de funcții (tool calls)
  STT.py                 → transcriere vocală RO (Google Cloud Speech)
  microphone.py          → variantă de transcriere EN (Vosk, offline)
  audio.py               → sinteză vocală (ElevenLabs)
  camera.py, base64encoding.py → captură + encodare imagini pentru viziune
  pose_detection.py      → verificare corectitudine exerciții (MediaPipe)
  movement_sequence.py   → urmărire persoană cu YOLOv8 + navigație
  arm_controller.py      → mișcările brațelor (servo, PCA9685)
  motor.py, motor_hc595.py, ultrasonicsensor.py → baza mobilă + senzori distanță
  motor_run.py           → legătura serială cu ESP32-ul care controlează motoarele
  display.py             → animația ochiului pe display-ul TFT
scripts/                 → scripturi separate de test/calibrare, rulate manual
  arm_controller_test.py → meniu interactiv pentru testarea fiecărei mișcări
  calibrate_right.py     → calibrare unghiuri servo braț drept
  face_analysis.py       → analiză emoție facială (DeepFace), experimental
  openWakeWordBimbo.py   → test izolat pentru wake word, fără restul pipeline-ului
config/                  → functions.json (tool-urile expuse către OpenAI) + template credențiale
models/                  → yolov8n.pt (model YOLO pentru detecție/urmărire persoane)
assets/                  → sunete, imagini pentru display, poze temporare capturate
docs/                    → roadmap și note de dezvoltare
```

## Hardware

- Raspberry Pi 5 — orchestrare software (wake word, AI, viziune)
- ESP32 — control motoare în timp real, comunicare serială cu RPi5
- Servomotoare MG996V pilotate prin placă PCA9685 (16 canale)
- Cameră RPi (Picamera2) pentru viziune și urmărire
- Senzori ultrasonici pentru detecția distanței/obstacolelor
- Display TFT (ST7735) pentru "fața" robotului
- Baterie custom 4S LiFePO4 + placă eFuse (protecție la suprasarcină/subtensiune)
  proiectată separat în KiCad

## Instalare

1. Clonează repo-ul și instalează dependențele Python:

   ```bash
   git clone <link-ul-repo-ului-tau>
   cd Bimbo_Code
   pip install -r requirements.txt
   ```

   > Pe Raspberry Pi, `picamera2` se instalează de obicei prin `apt`, nu prin `pip`:
   > `sudo apt install -y python3-picamera2`

2. Copiază `.env.example` în `.env` și completează-ți propriile chei:

   ```bash
   cp .env.example .env
   ```

   Ai nevoie de:
   - o cheie **OpenAI** (`OPENAI_API_KEY`)
   - o cheie **ElevenLabs** (`ELEVENLABS_API_KEY`)
   - un fișier de service account **Google Cloud** pentru Speech-to-Text — pune-l
     la `config/speech_to_text_credentials.json` (structura e în
     `config/speech_to_text_credentials.example.json`) sau indică alt path prin
     `GOOGLE_APPLICATION_CREDENTIALS`

3. Pune modelul de wake word (`hey_bimbo.onnx`) și fișierele audio (`beep.mp3`,
   `bimbo_speech_oncs.mp3`) în `assets/` (sau setează alte path-uri prin
   `WAKEWORD_MODEL_PATH`, `BEEP_SOUND_PATH`, `ROBOT_SPEECH_PATH` în `.env`).

4. Pornește robotul:

   ```bash
   python main.py
   ```

## Siguranță

Bimbo este gândit ca asistent, nu ca înlocuitor de personal medical: nu pune
diagnostice, se oprește imediat la semnale de durere și confirmă mereu parametrii
lipsă (repetări, braț) înainte să execute o mișcare, pentru a evita acțiuni
nedorite asupra pacientului.

## Roadmap

Vezi [docs/ROADMAP.md](docs/ROADMAP.md) pentru direcțiile de dezvoltare viitoare.

## Context

Proiect realizat individual, ca parte a pregătirii pentru competiția
**InfoEducație**, cu scopul de a combina robotică, viziune computerizată și AI
conversațional într-un asistent fizic util pentru recuperare medicală.
