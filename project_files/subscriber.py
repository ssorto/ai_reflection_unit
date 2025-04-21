import cv2
import numpy as np
import json
import paho.mqtt.client as mqtt
import time
from utils import color_to_emotion

# Load HSV thresholds
with open("project_files/hsv_ranges.json", "r") as f:
    hsv_ranges = json.load(f)

# ------------------ CONFIG ------------------
from utils import color_to_emotion  # maps 'red' → 'Frustrated'

BROKER = "test.mosquitto.org"
CARD_INPUT_TOPIC = "survey/card_input"
PROMPT_TOPIC = "survey/ai_prompt"
USER_INPUT_TOPIC = "survey/user_input"
SESSION_END_TOPIC = "survey/session_end"

# Load HSV ranges from JSON file
with open("project_files/hsv_ranges.json", "r") as f:
    hsv_ranges = json.load(f)

session_stage = "T1"
selected_emotions = []

# ------------------ FUNCTIONS ------------------

def detect_cards_from_frame(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    detected = []
    for color_name, bounds in hsv_ranges.items():
        lower = np.array(bounds["lower"])
        upper = np.array(bounds["upper"])
        mask = cv2.inRange(hsv, lower, upper)
        if cv2.countNonZero(mask) > 5000:
            emotion = color_to_emotion.get(color_name)
            if emotion and emotion not in detected:
                detected.append(emotion)
    return detected[:3]  # limit to 3 emotions


def wait_for_user_input():
    return input("Type your reflection: ")


def display_prompt(prompt):
    print("\nAI: ", prompt)


def handle_ai_prompt(client, userdata, msg):
    global session_stage
    prompt = json.loads(msg.payload.decode())["prompt"]
    display_prompt(prompt)

    if session_stage == "T2":
        reflection = wait_for_user_input()
        client.publish(USER_INPUT_TOPIC, json.dumps({"text": reflection}))
        session_stage = "T3"

    elif session_stage == "T3":
        reflection = wait_for_user_input()
        client.publish(USER_INPUT_TOPIC, json.dumps({"text": reflection}))
        # Now wait for session_end


def handle_session_end(client, userdata, msg):
    print("\nSession complete. Thank you for reflecting!")
    exit()

# ------------------ MQTT SETUP ------------------

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()

client.subscribe(PROMPT_TOPIC)
client.subscribe(SESSION_END_TOPIC)
client.message_callback_add(PROMPT_TOPIC, handle_ai_prompt)
client.message_callback_add(SESSION_END_TOPIC, handle_session_end)

# ------------------ MAIN ------------------

print("System Ready. Please place emotion cards in view...")

cap = cv2.VideoCapture(0)

while session_stage == "T1":
    ret, frame = cap.read()
    if not ret:
        print("Failed to read from camera.")
        break

    emotions = detect_cards_from_frame(frame)
    if emotions:
        print("Detected emotions:", emotions)
        selected_emotions = emotions
        client.publish(CARD_INPUT_TOPIC, json.dumps({"cards": emotions}))
        session_stage = "T2"
        print("Waiting for AI to generate Prompt 1...")
    
    time.sleep(1)

cap.release()
cv2.destroyAllWindows()

while True:
    time.sleep(1)  # Keep script running for MQTT listener