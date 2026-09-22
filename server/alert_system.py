import math
import time 
import vonage
import json
import sys
import winsound  # <--- Added: Inbuilt Windows sound module
from geopy.geocoders import Nominatim
from datetime import datetime
import pyautogui  # <--- NEW: For the pop-up box
import os # to save modified data files

   
# --- CONFIGURATION ---
#VONAGE_KEY = "89368dee"
#VONAGE_SECRET = "PzVyi0ywfz7xzyza" 
#TARGET_PHONE = ""   --- Avik.

#VONAGE_KEY = "b870c2db"
#VONAGE_SECRET = "PQVVfMpcqDC3a8dw" 
#TARGET_PHONE = "" --- Taimur (sms limit reached).

#VONAGE_KEY = "507ff9c3"
#VONAGE_SECRET = "NrypXf*Bjd$uDtL*amH7uT4" 
#TARGET_PHONE = "" --- Kuntal (sms limit reached).
  
#VONAGE_KEY = "e2bd36f3"
#VONAGE_SECRET = "xKfTn@A4BCo" 
#TARGET_PHONE = "phn no." #--- Kuntal 

"""VONAGE_KEY = "b89a7f91"
VONAGE_SECRET = "9GSKsQdpyQQ6igR4" 
TARGET_PHONE = "916296437848" #--- Ankan """

from twilio.rest import Client
  
# --- TWILIO CONFIGURATION ---
# Get these from your Twilio Console (twilio.com/console)
TWILIO_ACCOUNT_SID = "AC92bc3ae7afed595bd0af63738dddd033" 
TWILIO_AUTH_TOKEN = "0b7158cc552543f7ab31549590306e42"
TWILIO_PHONE = "+13527667221" # Format: +1XXXXXXXXXX
TARGET_PHONE = "+917477542838" # Must be verified in Twilio Console first
   
ACCEL_THRESHOLD = 20.0   
      
# --- GLOBAL STORAGE ---
# This stores the last known location since GPS and Sensors come in different messages
last_known_lat = 0.0
last_known_lon = 0.0
 
# Initialize Clients
"""client = vonage.Client(key=VONAGE_KEY, secret=VONAGE_SECRET)
sms = vonage.Sms(client)"""

geolocator = Nominatim(user_agent="fall_detection_app_v1")


def get_location_name(lat, lon):
    if lat == 0.0 or lon == 0.0:
        return "Coordinates not available"
    try:
        location = geolocator.reverse(f"{lat}, {lon}", timeout=10)
        return location.address if location else "Address not found"
    except Exception as e:
        print(f"🌍 Geocoding Error: {e}")
        return f"Lat: {lat}, Lon: {lon}"

def process_sensor_data(path, message):
    global last_known_lat, last_known_lon
     
    try:
        data = json.loads(message)
        
        # 1. UPDATE GLOBAL LOCATION 
        # Check if this message is a geolocation update (nested structure)
        if "position" in data:
            coords = data["position"].get("coords", {})
            last_known_lat = coords.get("latitude", last_known_lat)
            last_known_lon = coords.get("longitude", last_known_lon)
            return # Exit here, as location messages don't have x, y, z data

        # 2. PROCESS MOTION DATA
        # Only proceed if the message contains x, y, z
        if "accelerometer" in path and 'x' in data and 'y' in data and 'z' in data:
            sensor_name = data.get("SensorName", "Unknown")
            x, y, z = float(data['x']), float(data['y']), float(data['z'])
            magnitude = math.sqrt(x**2 + y**2 + z**2)

            if magnitude > ACCEL_THRESHOLD:
                readable_time = datetime.now().strftime("%I:%M %p, %d %b %Y")

                # Determine which file to update
                file_path = "../data/accelerometer.txt" 
                  
                # Create the data folder if it doesn't exist
                if not os.path.exists('../data'): os.makedirs('../data')

                # Write (Append) the magnitude and time to your data files
                with open(file_path, "a") as f:
                    f.write(f"\n--- ALERT: {readable_time} | Magnitude: {magnitude:.2f} ---\n")
                # -------------------------------------

                print(f"🚨 SPIKE DETECTED: {sensor_name} at {magnitude:.2f}")
                
                # --- NEW: AUDIO ALERT ---
                print("🔊 PROMPTING AUDIO ALARM...")
                for _ in range(3): # This will beep 3 times
                    winsound.Beep(2500, 3000) # frequency 2500Hz, duration 3000ms
                # ------------------------
    
                print("🔍 Fetching location name from last known GPS...")
                  
                # Fetch address using the stored global coordinates
                location_name = get_location_name(last_known_lat, last_known_lon)
                gmaps_link = f"https://www.google.com/maps?q={last_known_lat},{last_known_lon}"
 
                # CONSOLE LOGGING
                print("\n" + "!"*40)
                print("🚨 FALL ALERT TRIGGERED 🚨")
                print(f"Time:    {readable_time}")
                print(f"Magnitude: {magnitude:.2f}")
                print(f"Sensor:    {sensor_name}") 
                print(f"Address: {location_name}")
                print("!"*40 + "\n")
      
                # SEND SMS
                #send_vonage_sms(readable_time, location_name, gmaps_link)
                send_twilio_sms(readable_time, location_name, gmaps_link)

                # 3. --- NEW: SCREEN POP-UP ---
                # This will show a Windows alert box on top of everything
                pyautogui.alert(
                    text=f"FALL DETECTED!\nTime: {readable_time}\nMagnitude: {magnitude:.2f}\nLocation: {location_name}\nSMS has been sent to emergency contacts.",
                    title="EMERGENCY ALERT SYSTEM",
                    button="OK"  
                )
                # -----------------------------
                       
                # KILL PROCESS
                print("Stopping all sensor tracking. System offline.")
                sys.exit()
                
    except (json.JSONDecodeError, KeyError, ValueError):
        pass

"""def send_vonage_sms(readable_time, location_name, gmaps_link):
    print(f"📲 Sending SMS to {TARGET_PHONE}...")
    
    text_message = (
        f"EMERGENCY: Fall detected at {readable_time}. "
        f"Location: {location_name}. "
        f"Map: {gmaps_link}"
    )

    response = sms.send_message({
        "from": "AlertSystem",
        "to": TARGET_PHONE,
        "text": text_message,
    })

    if response["messages"][0]["status"] == "0":
        print("✅ SMS successfully delivered.")
    else:
        print(f"❌ SMS failed: {response['messages'][0].get('error-text')}")
"""

def send_twilio_sms(readable_time, location_name, gmaps_link):
    print(f"📲 Sending Twilio SMS to {TARGET_PHONE}...")
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        text_body = (
            f"EMERGENCY: Fall detected at {readable_time}. "
            f"Location: {location_name}. "
            f"Map: {gmaps_link}"
        )

        message = client.messages.create(
            body=text_body,
            from_=TWILIO_PHONE,
            to=TARGET_PHONE
        )

        print(f"✅ SMS sent successfully! SID: {message.sid}")
        
    except Exception as e:
        print(f"❌ Twilio Error: {e}")
