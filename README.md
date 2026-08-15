# 🌾 KrishiRakshak (कृषि रक्षक)

> **AI-Driven Hyperlocal Agricultural Disaster Response & Mitigation Pipeline**

KrishiRakshak is an automated emergency advisory system designed to protect rural farmers from extreme weather events (such as cyclones, flash floods, and heavy rainfall). By integrating meteorological alerts with farmer registries, it generates crop-specific, hyper-localized pre-disaster precautions and post-disaster recovery advisories in both **Odia** and **Hindi**, delivered via **SMS** and **IVR Voice Calls**.

---

## 🌟 Key Features

- **🚨 Dynamic Disaster Feed Ingestion:** Automatically ingests live or simulated IMD disaster feeds (wind speed, precipitation, intensity level) from local databases (`db.json`) or remote endpoints.
- **🎯 Hyperlocal Farmer Targeting:** Correlates affected districts with registered farmers to trigger targeted warnings rather than broad broadcasts.
- **🧠 Generative Advisory Engine (Groq / LLaMA 3.3 70B):** Generates structured, crop-specific mitigation advice in fluent Odia and Hindi with English reference translations.
- **🔊 Dual-Stage Multi-Lingual IVR System:**
  - **Stage 1 (Pre-Disaster):** Emergency actions to protect crops and ensure drainage prior to impact.
  - **Stage 2 (Post-Disaster Mitigation):** Immediate recovery protocols, de-silting steps, and spray recommendations.
- **🎧 Lightweight Hybrid Text-to-Speech:** Produces `.mp3` voice broadcasts in native Odia and Hindi without requiring heavy GPU compute.

---

## 🛠️ Tech Stack

| Layer | Component | Technologies Used |
| :--- | :--- | :--- |
| **Core Runtime** | Execution Engine | Python 3.x |
| **Data Processing** | Registry & Filtering | Pandas |
| **Intelligence / LLM** | Advisory Generation | Groq API (`llama-3.3-70b-versatile`) |
| **Speech / TTS** | Audio Synthesis | Edge-TTS (`hi-IN-MadhurNeural`), gTTS, `asyncio` |
| **Data Storage** | Records & Alerts | JSON (`db.json`), CSV (`farmers.csv`) |
| **Configuration** | Environment Secrets | `python-dotenv` |

---

## 📂 Project Structure

```text
krishirakshak/
├── audio_broadcasts/        # Generated IVR voice alert files (.mp3)
├── db.json                  # IMD disaster alerts & scenario database
├── farmers.csv              # Farmer registry (Name, District, Crop, Phone)
├── main.py                  # End-to-end execution pipeline
├── requirements.txt         # Project dependencies
├── .env.example             # Environment variable template
└── README.md                # Project documentation
```


## 🚀 Getting Started

1. Clone the Repository
```Bash
git clone [https://github.com/dontcuttrees/krishirakshak.git](https://github.com/dontcuttrees/krishirakshak.git)
cd krishirakshak
```

2. Set Up Virtual Environment
```Bash
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate
```

3. Install Dependencies
```Bash
pip install -r requirements.txt
```

4. Configure Environment Variables
   
Create a .env file in the root directory:

```Code snippet
GROQ_API_KEY=your_groq_api_key_here
```

5. Run the Pipeline
```Bash
python main.py
```

📊 Sample Output Flow
```Plaintext
📡 Fetching IMD disaster alert feed...
📂 Loaded 5 alerts from local db.json

================================================================================
🚨 [IMD DISASTER ALERT TRIGGERED: IMD-OD-001]
📍 Location: Angul, Odisha
⚠️ Hazard: Severe Flash Flood & Inundation | Severity: RED ALERT | Level: High
📊 Forecast: Wind 95 km/h | 24h Rain 190 mm
================================================================================

🎯 Target Audience: Found 1 registered farmer(s) in Angul.

---------------------------------------------------------------------------
👨‍🌾 Recipient: Ramesh Nayak (ID: 1) | Phone: +919876543210 | Crop: Paddy
---------------------------------------------------------------------------

[STAGE 1: PRE-DISASTER WARNING DISPATCHED]
📱 SMS SENT:
   💬 [Odia]: ତୁରନ୍ତ ଧାନ ଫସଲରୁ ଅତିରିକ୍ତ ପାଣି ନିଷ୍କାସନ ପାଇଁ ନାଳି ଖୋଳନ୍ତୁ...
   💬 [Hindi]: तुरंत धान के खेत से जल निकासी की व्यवस्था करें...
📞 IVR VOICE CALL PLACED:
   📁 Odia Audio: audio_broadcasts/Farmer_1_pre_alert_ODIA.mp3 [200 OK]
   📁 Hindi Audio: audio_broadcasts/Farmer_1_pre_alert_HINDI.mp3 [200 OK]

[STAGE 2: POST-DISASTER MITIGATION DISPATCHED]
📱 SMS SENT:
   💬 [Odia]: ବନ୍ୟା ପାଣି ଛାଡିବା ପରେ ଫସଲରେ କବକନାଶକ ସ୍ପ୍ରେ କରନ୍ତୁ...
   💬 [Hindi]: जलभराव कम होने पर फफूंदनाशक का छिड़काव करें...
📞 IVR VOICE CALL PLACED:
   📁 Odia Recovery Audio: audio_broadcasts/Farmer_1_post_mitigation_ODIA.mp3 [200 OK]
   📁 Hindi Recovery Audio: audio_broadcasts/Farmer_1_post_mitigation_HINDI.mp3 [200 OK]

================================================================================
✅ All Odia & Hindi Emergency Dispatches Logged Successfully.
================================================================================
```
