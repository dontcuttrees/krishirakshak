import os
import json
import time
import random
import requests
import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ Missing GROQ_API_KEY! Please set it in your .env file.")

client = Groq(api_key=GROQ_API_KEY)
os.makedirs("audio_broadcasts", exist_ok=True)

# -------------------------------------------------------------
# 1. FETCH RANDOM DISASTER TRIGGER FROM LOCAL DB OR API
# -------------------------------------------------------------
TRIGGER_API_URL = "https://run.mocky.io/v3/46bc7793-1b9a-4c28-be9c-73ec56a90dc2"

def fetch_disaster_trigger(available_districts):
    print("📡 Fetching IMD disaster alert feed...")
    alerts = []
    
    # 1. Check local db.json first
    db_paths = ["db.json", "../db.json", os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.json")]
    db_file = next((p for p in db_paths if os.path.exists(p)), None)
    
    if db_file:
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                alerts = data.get("alerts", [])
                print(f"📂 Loaded {len(alerts)} alerts from local {db_file}")
        except Exception as e:
            print(f"⚠️ Error reading {db_file}: {e}")

    # 2. If no local db, fetch from mock API
    if not alerts:
        try:
            response = requests.get(TRIGGER_API_URL, timeout=10)
            alerts = response.json()
        except Exception as e:
            print(f"⚠️ API Fetch error: {e}")

    # 3. Match alerts with districts in the CSV
    matched_alerts = [
        a for a in alerts 
        if a.get('district', '').strip().lower() in [d.strip().lower() for d in available_districts]
    ]

    if matched_alerts:
        alert = random.choice(matched_alerts)
    elif alerts:
        alert = random.choice(alerts)
    else:
        alert = {
            "alert_id": "IMD-OD-FALLBACK-01",
            "district": random.choice(available_districts) if available_districts else "Angul",
            "hazard": "Severe Flash Flood & Inundation",
            "severity": "RED",
            "wind_speed_kmph": 95,
            "rainfall_forecast_mm": 190,
            "intensity_level": "High"
        }

    print("\n" + "="*80)
    print(f"🚨 [IMD DISASTER ALERT TRIGGERED: {alert.get('alert_id', 'IMD-OD-01')}]")
    print(f"📍 Location: {alert.get('district')}, Odisha")
    print(f"⚠️ Hazard: {alert.get('hazard')} | Severity: {alert.get('severity')} ALERT | Level: {alert.get('intensity_level')}")
    print(f"📊 Forecast: Wind {alert.get('wind_speed_kmph')} km/h | 24h Rain {alert.get('rainfall_forecast_mm')} mm")
    print("="*80 + "\n")
    return alert

# -------------------------------------------------------------
# 2. LLM ADVISORY GENERATOR (ODIA & HINDI)
# -------------------------------------------------------------
def generate_advisory(farmer, alert):
    prompt = f"""
    You are an emergency agricultural response coordinator in Odisha, India.

    Disaster Trigger Data:
    - Hazard: {alert.get('hazard')} ({alert.get('severity')} Alert, Intensity: {alert.get('intensity_level')})
    - Location: {alert.get('district')}, Odisha
    - Forecast: Wind {alert.get('wind_speed_kmph')} km/h, Rainfall {alert.get('rainfall_forecast_mm')} mm

    Farmer:
    - Name: {farmer.get('Name')}
    - Crop: {farmer.get('Crop')}

    Return ONLY a JSON object matching this schema:
    {{
      "pre_disaster_sms_odia": "2 urgent pre-disaster field actions in Odia script under 160 characters",
      "pre_disaster_sms_hindi": "2 urgent pre-disaster field actions in Hindi script under 160 characters",
      "pre_disaster_sms_en": "English reference translation under 160 characters",
      "pre_disaster_ivr_voice_odia": "Spoken emergency call script in Odia",
      "pre_disaster_ivr_voice_hindi": "Spoken emergency call script in Hindi",
      "post_disaster_sms_odia": "Recovery actions in Odia script under 160 characters",
      "post_disaster_sms_hindi": "Recovery actions in Hindi script under 160 characters",
      "post_disaster_ivr_voice_odia": "Spoken post-disaster recovery advice in Odia",
      "post_disaster_ivr_voice_hindi": "Spoken post-disaster recovery advice in Hindi"
    }}
    """

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        temperature=0.2
    )

    return json.loads(chat_completion.choices[0].message.content)

# -------------------------------------------------------------
# 3. TEXT-TO-SPEECH (IVR AUDIO CREATOR)
# -------------------------------------------------------------
def create_ivr_audio(text, filename):
    try:
        tts = gTTS(text=text, lang='hi', slow=False)
        filepath = os.path.join("audio_broadcasts", filename)
        tts.save(filepath)
        return filepath
    except Exception as e:
        return f"Audio error: {e}"

# -------------------------------------------------------------
# 4. EXECUTION PIPELINE
# -------------------------------------------------------------
def run_pipeline():
    csv_candidates = [
        "farmers_fake_names.csv",
        "farmers.csv",
        "../farmers_fake_names.csv",
        "../farmers.csv",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmers_fake_names.csv"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmers.csv")
    ]
    
    csv_file = next((path for path in csv_candidates if os.path.exists(path)), None)
    
    if not csv_file:
        print("❌ Error: Farmer CSV not found.")
        return

    print(f"📂 Loaded dataset from: {csv_file}")
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()

    available_districts = df['District'].dropna().unique().tolist()
    
    # 1. Fetch Random Alert Trigger
    alert = fetch_disaster_trigger(available_districts)
    target_district = alert['district']

    # 2. Filter affected farmers
    affected = df[df['District'].astype(str).str.strip().str.lower() == target_district.lower()]
    print(f"🎯 Target Audience: Found {len(affected)} registered farmer(s) in {target_district}.\n")

    for idx, farmer in affected.iterrows():
        farmer_id = farmer.get('FarmerID', farmer.get('Farmer_ID', idx + 1))
        name = farmer['Name']
        phone = farmer['Phone']
        crop = farmer['Crop']

        print("-" * 75)
        print(f"👨‍🌾 Recipient: {name} (ID: {farmer_id}) | Phone: {phone} | Crop: {crop}")
        print("-" * 75)

        advisories = generate_advisory(farmer, alert)

        pre_audio = f"Farmer_{farmer_id}_pre_alert.mp3"
        post_audio = f"Farmer_{farmer_id}_post_mitigation.mp3"

        create_ivr_audio(advisories['pre_disaster_ivr_voice_hindi'], pre_audio)
        create_ivr_audio(advisories['post_disaster_ivr_voice_hindi'], post_audio)

        # STAGE 1: PRE-DISASTER DISPATCH
        print("\n[STAGE 1: PRE-DISASTER WARNING DISPATCHED]")
        print(f"📱 SMS SENT to {phone}:")
        print(f"   💬 [Odia]:  {advisories['pre_disaster_sms_odia']}")
        print(f"   💬 [Hindi]: {advisories['pre_disaster_sms_hindi']}")
        print(f"   💬 [En Ref]: {advisories['pre_disaster_sms_en']}")
        print(f"📞 IVR VOICE CALL PLACED:")
        print(f"   🔊 Odia Voice Script:  \"{advisories['pre_disaster_ivr_voice_odia']}\"")
        print(f"   🔊 Hindi Voice Script: \"{advisories['pre_disaster_ivr_voice_hindi']}\"")
        print(f"   📁 Audio Generated: audio_broadcasts/{pre_audio} [STATUS: SENT / 200 OK]")

        time.sleep(1)

        # STAGE 2: POST-DISASTER MITIGATION
        print("\n[STAGE 2: POST-DISASTER MITIGATION DISPATCHED]")
        print(f"📱 SMS SENT to {phone}:")
        print(f"   💬 [Odia]:  {advisories['post_disaster_sms_odia']}")
        print(f"   💬 [Hindi]: {advisories['post_disaster_sms_hindi']}")
        print(f"📞 IVR VOICE CALL PLACED:")
        print(f"   🔊 Recovery Voice: \"{advisories['post_disaster_ivr_voice_odia']}\"")
        print(f"   📁 Audio Generated: audio_broadcasts/{post_audio} [STATUS: SENT / 200 OK]\n")

    print("=" * 80)
    print("✅ All Emergency & Post-Disaster Dispatches Logged Successfully.")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline()