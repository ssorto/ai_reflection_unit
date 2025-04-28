import paho.mqtt.client as mqtt
import json
import os
import time
from dotenv import load_dotenv
import google.generativeai as genai

# ---------------- CONFIG ----------------
load_dotenv()

BROKER = "test.mosquitto.org"
CARD_INPUT_TOPIC = "survey/card_input"
USER_INPUT_TOPIC = "survey/user_input"
PROMPT_TOPIC = "survey/ai_prompt"
SESSION_END_TOPIC = "survey/session_end"

# Gemini API Setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# ---------------- HELPER FUNCTIONS ----------------
def generate_followup_prompt(user_text, emotions):
    system_prompt = (
        f"""The user reflected on their car shopping experience, mentioning the emotions: {emotions}.
Their response was: "{user_text}".
Analyze their reflection:
- If they describe a timeline (e.g., 'first', 'then', 'after that'), ask a follow-up question diving into the emotional journey.
- If they don't describe a timeline, ask a thoughtful question about key emotional highlights.
Use a warm, conversational, curious tone.
Return only the follow-up question."""
    )
    response = model.generate_content(system_prompt)
    return response.text.strip()

def generate_final_prompt(user_text, emotions):
    system_prompt = (
        f"""The user just reflected: \"{user_text}\" with these emotions: {emotions}.
Generate a warm closing question inviting them to summarize their overall car shopping journey in a few words.
If it feels natural, invite them to imagine how they'd describe their experience to a friend.
Be warm, reflective, and concise.
Only return the final prompt."""
    )
    response = model.generate_content(system_prompt)
    return response.text.strip()

# ---------------- SESSION STATE ----------------
session_state = {
    "stage": "WAITING_FOR_CARDS",
    "emotions": [],
    "reflections": []
}

# ---------------- MQTT CALLBACKS ----------------
def handle_card_input(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    session_state["emotions"] = payload["cards"]
    emotions_text = " and ".join(session_state["emotions"])
    greeting = (
        f"Thinking about your car shopping experience today, what specific moments made you feel {emotions_text} — was it during browsing, financing, or delivery?"
    )
    client.publish(PROMPT_TOPIC, json.dumps({"prompt": greeting}))
    session_state["stage"] = "WAITING_FOR_T1"
    print("\nSent Greeting Prompt:", greeting)

def handle_user_input(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    user_text = payload.get("text", "").strip()

    if not user_text:
        print("\nNo user input received — skipping...")
        return

    session_state["reflections"].append(user_text)

    if session_state["stage"] == "WAITING_FOR_T1":
        followup_prompt = generate_followup_prompt(user_text, session_state["emotions"])
        client.publish(PROMPT_TOPIC, json.dumps({"prompt": followup_prompt}))
        session_state["stage"] = "WAITING_FOR_T2"
        print("\nSent AI Follow-up Prompt:", followup_prompt)

    elif session_state["stage"] == "WAITING_FOR_T2":
        final_prompt = generate_final_prompt(user_text, session_state["emotions"])
        client.publish(PROMPT_TOPIC, json.dumps({"prompt": final_prompt}))
        session_state["stage"] = "WAITING_FOR_T3"
        print("\nSent Final Summary Prompt:", final_prompt)

    elif session_state["stage"] == "WAITING_FOR_T3":
        closing_message = (
            "Thank you for reflecting with us! Session complete. Your insights help us continually improve the car shopping experience."
        )
        client.publish(PROMPT_TOPIC, json.dumps({"prompt": closing_message}))
        print("\nSent closing message:", closing_message)

        time.sleep(2)  # Small delay to let subscriber show closing
        client.publish(SESSION_END_TOPIC, json.dumps({"status": "done"}))
        session_state["stage"] = "DONE"
        print("\nSession complete!")

# ---------------- MAIN ----------------
client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()

client.subscribe(CARD_INPUT_TOPIC)
client.subscribe(USER_INPUT_TOPIC)

client.on_message = lambda client, userdata, msg: (
    handle_card_input(client, userdata, msg) if msg.topic == CARD_INPUT_TOPIC else handle_user_input(client, userdata, msg)
)

print("Publisher running. Waiting for card input...")

try:
    while True:
        pass
except KeyboardInterrupt:
    print("\nExiting...")
finally:
    client.loop_stop()
    client.disconnect()