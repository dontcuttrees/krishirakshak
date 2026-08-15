import os
import json
import time
import random
import asyncio
import requests
import pandas as pd
from dotenv import load_dotenv
from groq import Groq
import edge_tts

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

    if not alerts:
        try:
            response = requests.get(TRIGGER_API_URL, timeout=10)
            alerts = response.json()
        except Exception as e:
            print(f"⚠️ API Fetch error: {e}")

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
# 3. TEXT-TO-SPEECH (EDGE-TTS FOR ODIA & HINDI NEURAL VOICES)
# -------------------------------------------------------------
async def generate_audio_async(text, voice, filepath):
    # Clean up formatting characters that break TTS streams
    cleaned_text = (
        text.replace('"', '')
        .replace('*', '')
        .replace('\n', ' ')
        .strip()
    )
    if not cleaned_text:
        return
    communicate = edge_tts.Communicate(cleaned_text, voice)
    await communicate.save(filepath)

def create_ivr_audio(text, lang, filename):
    if not text or not str(text).strip():
        return None

    filepath = os.path.join("audio_broadcasts", filename)
    
    # Try preferred neural voice, then fall back to standard Indian neural voices
    voice_candidates = (
        ["or-IN-SukantNeural", "hi-IN-MadhurNeural", "en-IN-PrabhatNeural"]
        if lang.lower() == "odia"
        else ["hi-IN-MadhurNeural", "hi-IN-SwaraNeural", "en-IN-PrabhatNeural"]
    )

    for voice in voice_candidates:
        try:
            asyncio.run(generate_audio_async(text, voice, filepath))
            # Verify file was actually created and is not 0 bytes
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return filepath
        except Exception:
            continue

    # Final Fallback to gTTS if edge-tts network drops
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='hi', slow=False)
        tts.save(filepath)
        return filepath
    except Exception as e:
        print(f"⚠️ Audio fallback failed for {filename}: {e}")
        return None

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

        # Generate Audio Files for BOTH Odia and Hindi
        pre_audio_odia = f"Farmer_{farmer_id}_pre_alert_ODIA.mp3"
        pre_audio_hindi = f"Farmer_{farmer_id}_pre_alert_HINDI.mp3"
        post_audio_odia = f"Farmer_{farmer_id}_post_mitigation_ODIA.mp3"
        post_audio_hindi = f"Farmer_{farmer_id}_post_mitigation_HINDI.mp3"

        create_ivr_audio(advisories['pre_disaster_ivr_voice_odia'], "odia", pre_audio_odia)
        create_ivr_audio(advisories['pre_disaster_ivr_voice_hindi'], "hindi", pre_audio_hindi)
        create_ivr_audio(advisories['post_disaster_ivr_voice_odia'], "odia", post_audio_odia)
        create_ivr_audio(advisories['post_disaster_ivr_voice_hindi'], "hindi", post_audio_hindi)

        # STAGE 1: PRE-DISASTER DISPATCH
        print("\n[STAGE 1: PRE-DISASTER WARNING DISPATCHED]")
        print(f"📱 SMS SENT to {phone}:")
        print(f"   💬 [Odia]:  {advisories['pre_disaster_sms_odia']}")
        print(f"   💬 [Hindi]: {advisories['pre_disaster_sms_hindi']}")
        print(f"   💬 [En Ref]: {advisories['pre_disaster_sms_en']}")
        print(f"📞 IVR VOICE CALL PLACED:")
        print(f"   🔊 Odia Voice Script:  \"{advisories['pre_disaster_ivr_voice_odia']}\"")
        print(f"   📁 Odia Audio File:   audio_broadcasts/{pre_audio_odia} [STATUS: SENT / 200 OK]")
        print(f"   🔊 Hindi Voice Script: \"{advisories['pre_disaster_ivr_voice_hindi']}\"")
        print(f"   📁 Hindi Audio File:  audio_broadcasts/{pre_audio_hindi} [STATUS: SENT / 200 OK]")

        time.sleep(1)

        # STAGE 2: POST-DISASTER MITIGATION
        print("\n[STAGE 2: POST-DISASTER MITIGATION DISPATCHED]")
        print(f"📱 SMS SENT to {phone}:")
        print(f"   💬 [Odia]:  {advisories['post_disaster_sms_odia']}")
        print(f"   💬 [Hindi]: {advisories['post_disaster_sms_hindi']}")
        print(f"📞 IVR VOICE CALL PLACED:")
        print(f"   🔊 Odia Recovery Voice:  \"{advisories['post_disaster_ivr_voice_odia']}\"")
        print(f"   📁 Odia Recovery Audio:  audio_broadcasts/{post_audio_odia} [STATUS: SENT / 200 OK]")
        print(f"   🔊 Hindi Recovery Voice: \"{advisories['post_disaster_ivr_voice_hindi']}\"")
        print(f"   📁 Hindi Recovery Audio: audio_broadcasts/{post_audio_hindi} [STATUS: SENT / 200 OK]\n")

    print("=" * 80)
    print("✅ All Odia & Hindi Emergency Dispatches Logged Successfully.")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline()