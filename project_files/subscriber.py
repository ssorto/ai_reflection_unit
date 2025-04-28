import cv2
import numpy as np
import json
import paho.mqtt.client as mqtt
import time
from utils import color_to_emotion
from picamera2 import Picamera2

# ------------------ MQTT CONFIG ------------------
BROKER = "test.mosquitto.org"
CARD_INPUT_TOPIC = "survey/card_input"
PROMPT_TOPIC = "survey/ai_prompt"
USER_INPUT_TOPIC = "survey/user_input"
SESSION_END_TOPIC = "survey/session_end"

# ------------------ LOAD HSV RANGES ------------------
with open("project_files/hsv_ranges.json", "r") as f:
    hsv_ranges = json.load(f)

# ------------------ STATE ------------------
session_stage = "T1"
selected_emotions = []
awaiting_user_input = False

# ------------------ CAMERA INIT ------------------
picam2 = Picamera2()
picam2.preview_configuration.main.size = (1240, 1280)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()
time.sleep(2)

# ------------------ FUNCTION ------------------
detection_counter = {}

def detect_cards_from_frame():
    global detection_counter
    frame = picam2.capture_array()

    # Define tray mask region
    y1, y2 = 150, 800
    x1, x2 = 100, 1140
    tray_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    tray_mask[y1:y2, x1:x2] = 255

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    masked_hsv = cv2.bitwise_and(hsv, hsv, mask=tray_mask)

    detected = []

    for color_name, bounds in hsv_ranges.items():
        if color_name == "red":
            lower1 = np.array(bounds["lower1"])
            upper1 = np.array(bounds["upper1"])
            lower2 = np.array(bounds["lower2"])
            upper2 = np.array(bounds["upper2"])
            mask1 = cv2.inRange(masked_hsv, lower1, upper1)
            mask2 = cv2.inRange(masked_hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            lower = np.array(bounds["lower"])
            upper = np.array(bounds["upper"])
            mask = cv2.inRange(masked_hsv, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 2500:
                x, y, w, h = cv2.boundingRect(cnt)
                emotion = color_to_emotion.get(color_name)
                detection_counter[color_name] = detection_counter.get(color_name, 0) + 1

                if detection_counter[color_name] >= 4:
                    if emotion and emotion not in detected:
                        detected.append(emotion)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(frame, color_name, (x, y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    break

    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
    cv2.imshow("Tray View", frame)
    cv2.waitKey(1)

    return detected[:3]

# ------------------ MQTT CALLBACKS ------------------

awaiting_user_input = False

def on_message(client, userdata, msg):
    global awaiting_user_input
    payload = json.loads(msg.payload.decode())

    if msg.topic == PROMPT_TOPIC:
        prompt = payload.get("prompt", "")
        print("\n-----------------------------------------------")
        print(f"AI Prompt: {prompt}")
        print("-----------------------------------------------")

        if prompt.lower().startswith("thank you"):
            # Final closing message ? no input expected
            awaiting_user_input = False
        else:
            awaiting_user_input = True
            while True:
                user_response = input("?? Your response: ").strip()
                if user_response:
                    client.publish(USER_INPUT_TOPIC, json.dumps({"text": user_response}))
                    break

    elif msg.topic == SESSION_END_TOPIC:
        print("\n==============================================")
        print("Session complete!")
        print("==============================================")

# ------------------ MAIN ------------------
client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()

client.subscribe(PROMPT_TOPIC)
client.subscribe(SESSION_END_TOPIC)
client.on_message = on_message

print("\n" + "="*60)
print("Welcome! We'd love to hear about your car shopping experience.")
print("Please select 1-3 cards that capture how you felt during your visit.")
print("Place your selected cards onto the tray to begin.")
print("Press 'q' at any time to exit.\n")
print("="*60)

print("System Ready. Press 'q' in the camera window to stop.")
print("\nTake a moment to place your cards. Detection will start in 10 seconds...")
time.sleep(10)
detection_counter.clear()
print("Starting detection now!")

try:
    while True:
        emotions = detect_cards_from_frame()
        if session_stage == "T1" and emotions:
            print(f"? Final detected emotions: {emotions}")
            client.publish(CARD_INPUT_TOPIC, json.dumps({"cards": emotions}))
            session_stage = "T2"

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    client.loop_stop()
    picam2.close()
    cv2.destroyAllWindows()
