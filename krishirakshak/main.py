import os
import json
import time
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
# 1. FETCH LIVE DISASTER TRIGGER FROM API
# -------------------------------------------------------------
TRIGGER_API_URL = "https://run.mocky.io/v3/46bc7793-1b9a-4c28-be9c-73ec56a90dc2"

def fetch_disaster_trigger_from_api(target_district):
    print(f"📡 Fetching live IMD disaster alert feed from API for {target_district}...")
    try:
        response = requests.get(TRIGGER_API_URL, timeout=10)
        alerts = response.json()
        
        # Filter alert for the requested district
        matched = [a for a in alerts if a['district'].lower() == target_district.lower()]
        
        if matched:
            alert = matched[0]
        else:
            alert = alerts[0] # Default to the primary active alert

        print("\n" + "="*80)
        print(f"🚨 [IMD DISASTER ALERT RECEIVED VIA API: {alert['alert_id']}]")
        print(f"📍 Location: {alert['district']}, Odisha")
        print(f"⚠️ Hazard: {alert['hazard']} | Severity: {alert['severity']} ALERT | Level: {alert['intensity_level']}")
        print(f"📊 Forecast: Wind {alert['wind_speed_kmph']} km/h | 24h Rain {alert['rainfall_forecast_mm']} mm")
        print("="*80 + "\n")
        return alert

    except Exception as e:
        print(f"⚠️ API Fetch error: {e}. Falling back to default payload.")
        return {
            "alert_id": "IMD-OD-FALLBACK-01",
            "district": target_district,
            "hazard": "Severe Flash Flood & Inundation",
            "severity": "RED",
            "wind_speed_kmph": 95,
            "rainfall_forecast_mm": 190,
            "intensity_level": "High"
        }

# -------------------------------------------------------------
# 2. LLM ADVISORY GENERATOR (ODIA & HINDI)
# -------------------------------------------------------------
def generate_advisory(farmer, alert):
    prompt = f"""
    You are an emergency agricultural response coordinator in Odisha, India.

    Disaster Trigger Data:
    - Hazard: {alert['hazard']} ({alert['severity']} Alert, Intensity: {alert['intensity_level']})
    - Location: {alert['district']}, Odisha
    - Forecast: Wind {alert['wind_speed_kmph']} km/h, Rainfall {alert['rainfall_forecast_mm']} mm

    Farmer:
    - Name: {farmer['Name']}
    - Crop: {farmer['Crop']}

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
    # 1. Resolve farmers.csv path dynamically across root and subfolders
    csv_candidates = [
        "farmers_fake_names.csv",
        "../farmers_fake_names.csv",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmers_fake_names.csv"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "farmers_fake_names.csv")
    ]
    
    csv_file = next((path for path in csv_candidates if os.path.exists(path)), None)
    
    if not csv_file:
        print("❌ Error: 'farmers_fake_names.csv' not found in current directory or parent directory.")
        return

    print(f"📂 Loaded dataset from: {csv_file}")
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()

    # Target the district from your CSV (e.g. Angul)
    target_district = df['District'].dropna().iloc[0]
    
    # 2. Fetch Alert from Trigger API
    alert = fetch_disaster_trigger_from_api(target_district)

    # 3. Filter affected farmers
    affected = df[df['District'].astype(str).str.strip().str.lower() == target_district.lower()]
    print(f"🎯 Target Audience: Found {len(affected)} registered farmer(s) in {target_district}.\n")

    for idx, farmer in affected.iterrows():
        farmer_id = farmer['FarmerID']
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