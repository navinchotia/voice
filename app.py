import streamlit as st
import tempfile
import os
import json
from gtts import gTTS
import random

# --- Helper Functions ---

def get_user_session_id():
    if "user_session_id" not in st.session_state:
        st.session_state.user_session_id = f"user_{random.randint(1000,9999)}"
    return st.session_state.user_session_id

def load_memory(session_id):
    path = f"memory_{session_id}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(session_id, memory):
    path = f"memory_{session_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f)

def generate_reply(memory, user_input):
    # --- Dummy logic for now ---
    # You can replace this with your OpenAI or Gemini model logic later
    reply = f"Neha: Tumne kaha '{user_input}', sahi kaha 😊"
    return reply

def speak_text(text):
    tts = gTTS(text=text, lang='hi')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        return fp.name

# --- Streamlit UI ---
st.set_page_config(page_title="Neha - Hindi Chatbot", page_icon="💬")

st.title("💬 Neha - Hindi Practice Chatbot")

session_id = get_user_session_id()
if "memory" not in st.session_state:
    st.session_state.memory = load_memory(session_id)

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Display chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("audio_path"):
            st.audio(msg["audio_path"], format="audio/mp3")

# --- Input ---
user_input = st.chat_input("Type your message here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Neha type kar rahi hai... 💭"):
        reply = generate_reply(st.session_state.memory, user_input)

    # Generate speech
    audio_path = speak_text(reply)

    # Save assistant message (text + audio)
    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "audio_path": audio_path
    })

    # Update memory
    st.session_state.memory.append({"user": user_input, "neha": reply})
    save_memory(session_id, st.session_state.memory)

    # Rerun to display message + audio
    st.rerun()
