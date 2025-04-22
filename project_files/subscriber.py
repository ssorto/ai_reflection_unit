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

# ------------------ CAMERA INIT ------------------
picam2 = Picamera2()
picam2.preview_configuration.main.size = (1240, 1280)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()
time.sleep(2)

# ------------------ FUNCTION ------------------
def detect_cards_from_frame():
    frame = picam2.capture_array()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    detected = []

    for color_name, bounds in hsv_ranges.items():
        lower = np.array(bounds["lower"])
        upper = np.array(bounds["upper"])
        mask = cv2.inRange(hsv, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 2000:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, color_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 0), 2)
                emotion = color_to_emotion.get(color_name)
                if emotion and emotion not in detected:
                    detected.append(emotion)

    cv2.imshow("PiCam View", frame)
    return detected[:3]

# ------------------ MQTT CALLBACKS ------------------
def on_message(client, userdata, msg):
    global session_stage
    if msg.topic == PROMPT_TOPIC:
        payload = json.loads(msg.payload.decode())
        prompt = payload.get("prompt", "")
        print(f"\n? AI Prompt: {prompt}")

        if session_stage == "T2":
            response = input("?? Your response: ")
            client.publish(USER_INPUT_TOPIC, json.dumps({"text": response}))
            session_stage = "T3"

        elif session_stage == "T3":
            response = input("?? Final reflection: ")
            client.publish(USER_INPUT_TOPIC, json.dumps({"text": response}))
            session_stage = "DONE"

    elif msg.topic == SESSION_END_TOPIC:
        print("\n? Session complete!")

# ------------------ MAIN ------------------
client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()
client.subscribe(PROMPT_TOPIC)
client.subscribe(SESSION_END_TOPIC)
client.on_message = on_message

print("System Ready. Press 'q' in the camera window to stop.")

try:
    while True:
        emotions = detect_cards_from_frame()
        if session_stage == "T1" and emotions:
            print(f"? Detected emotions: {emotions}")
            client.publish(CARD_INPUT_TOPIC, json.dumps({"cards": emotions}))
            session_stage = "T2"

        # Keep imshow responsive
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    client.loop_stop()
    picam2.close()
    cv2.destroyAllWindows()
