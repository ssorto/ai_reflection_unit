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

def generate_prompt(stage, emotions=None, reflections=None):
    if stage == "T1":
        joined = " and ".join(emotions)
        return (f"Thinking about your car shopping experience today, "
                f"what specific moments made you feel {joined} — "
                f"was it during browsing, financing, or delivery?")
    
    elif stage == "T2" and reflections:
        return (f"The user reflected: \"{reflections[0]}\" "
                f"Based on this, generate a thoughtful follow-up question to explore how this emotional journey influenced their trust or loyalty.")
    
    elif stage == "T3" and reflections:
        return (f"The user reflected: {reflections} "
                f"Based on these reflections, generate a final open-ended question to encourage the user to summarize their overall experience as if telling a friend.")
    
    else:
        return "Thank you for reflecting!"

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
        prompt2 = generate_prompt("T2", reflections=session_state["reflections"])
        ai_response = call_gemini(prompt2)  # <<<<< NEW: Ask Gemini
        client.publish(PROMPT_TOPIC, json.dumps({"prompt": ai_response}))

        # Adding this fallback check here
        if not ai_response:
            ai_response = "Thanks for sharing! Could you tell me a bit more about that experience?"

        session_state["stage"] = "T3"
        print("Sent Prompt 2:", ai_response)

    elif session_state["stage"] == "T3":
        closing = generate_prompt("T3", reflections=session_state["reflections"])
        ai_response = call_gemini(closing)  # <<<<< NEW: Ask Gemini
        client.publish(PROMPT_TOPIC, json.dumps({"prompt": ai_response}))

        # Adding fallback check here too
        if not ai_response:
            ai_response = "Thank you for reflecting with us! Is there anything else you’d like to share?"

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
