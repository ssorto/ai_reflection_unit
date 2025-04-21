import paho.mqtt.client as mqtt
import json
import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# ------------------ CONFIG ------------------
load_dotenv()

BROKER = "test.mosquitto.org"
CARD_INPUT_TOPIC = "survey/card_input"
USER_INPUT_TOPIC = "survey/user_input"
PROMPT_TOPIC = "survey/ai_prompt"
SESSION_END_TOPIC = "survey/session_end"

session_state = {
    "stage": "T1",  # T1 → T2 → T3 → DONE
    "emotions": [],
    "reflections": []
}

# ------------------ HELPER ------------------

def generate_prompt(stage, emotions=None, reflection=None):
    if stage == "T1":
        joined = " and ".join(emotions)
        return f"What made you feel {joined} during your experience?"
    elif stage == "T2":
        return f"Thanks for sharing. How did that shape your overall impression?"
    else:
        return "What would you want a friend to know about your experience?"

# ------------------ CALLBACKS ------------------

def handle_card_input(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    session_state["emotions"] = payload["cards"]
    prompt1 = generate_prompt("T1", emotions=session_state["emotions"])
    client.publish(PROMPT_TOPIC, json.dumps({"prompt": prompt1}))
    session_state["stage"] = "T2"
    print("Sent Prompt 1:", prompt1)

def handle_user_input(client, userdata, msg):
    user_text = json.loads(msg.payload.decode())["text"]
    session_state["reflections"].append(user_text)

    if session_state["stage"] == "T2":
        prompt2 = generate_prompt("T2", reflection=user_text)
        client.publish(PROMPT_TOPIC, json.dumps({"prompt": prompt2}))
        session_state["stage"] = "T3"
        print("Sent Prompt 2:", prompt2)

    elif session_state["stage"] == "T3":
        closing = generate_prompt("T3")
        client.publish(PROMPT_TOPIC, json.dumps({"prompt": closing}))
        client.publish(SESSION_END_TOPIC, json.dumps({"status": "done"}))
        session_state["stage"] = "DONE"
        print("Session complete. Sent wrap-up message.")

# ------------------ MQTT SETUP ------------------

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()

client.subscribe(CARD_INPUT_TOPIC)
client.subscribe(USER_INPUT_TOPIC)
client.message_callback_add(CARD_INPUT_TOPIC, handle_card_input)
client.message_callback_add(USER_INPUT_TOPIC, handle_user_input)

print("Publisher running. Waiting for card input...")

# Keep the script running
try:
    while True:
        pass
except KeyboardInterrupt:
    print("\nShutting down...")
    client.loop_stop()
