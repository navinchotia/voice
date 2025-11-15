import streamlit as st
import google.generativeai as genai
import os
import json
from datetime import datetime
import pytz
import requests
from gtts import gTTS
from io import BytesIO
import tempfile
import base64
import hashlib
import re

# ---------------------------
# Streamlit App Config
# ---------------------------
st.set_page_config(page_title="Neha Chatbot", layout="centered")
st.title("Neha Hinglish Chatbot 🇮🇳")

# ---------------------------
# API Key
# ---------------------------
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    st.error("Gemini API key missing in Streamlit Secrets!")
else:
    genai.configure(api_key=api_key)

# ---------------------------
# Chat Initialization
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Bubble CSS
bubble_css = """
<style>
.user {
  background: #dcf8c6;
  padding: 10px;
  border-radius: 10px;
  margin: 5px;
  width: fit-content;
}
.bot {
  background: #ffffff;
  padding: 10px;
  border-radius: 10px;
  margin: 5px;
  width: fit-content;
  border: 1px solid #ddd;
}
</style>
"""
st.markdown(bubble_css, unsafe_allow_html=True)

# ---------------------------
# Display Chat
# ---------------------------
for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "bot"
    st.markdown(f"<div class='{role}'>{msg['content']}</div>", unsafe_allow_html=True)

    # ----------------------------------
    # gTTS AUTOMATIC SPEECH FOR BOT
    # ----------------------------------
    if role == "bot":
        try:
            if len(msg["content"].strip()) == 0:
                continue

            clean_text = re.sub(r'[^a-zA-Z0-9\u0900-\u097F\s,.!?-]', '', msg["content"])
            cache_key = hashlib.md5(clean_text.encode()).hexdigest()
            cache_file = f"/tmp/{cache_key}.mp3"

            if not os.path.exists(cache_file):
                tts = gTTS(text=clean_text, lang="hi", tld='co.in', slow=False)
                tts.save(cache_file)

            audio_bytes = open(cache_file, "rb").read()
            audio_base64 = base64.b64encode(audio_bytes).decode()

            st.markdown(
                f"""
                <audio controls style='margin-top:-6px;'>
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                </audio>
                """,
                unsafe_allow_html=True
            )

        except Exception:
            st.warning("Speech issue: TTS temporarily unavailable. Try again.")

# ---------------------------
# User Input
# ---------------------------
prompt = st.chat_input("Type your message…")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f"<div class='user'>{prompt}</div>", unsafe_allow_html=True)

    try:
        response = genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"Error: {e}"

    st.session_state.messages.append({"role": "bot", "content": bot_reply})
    st.markdown(f"<div class='bot'>{bot_reply}</div>", unsafe_allow_html=True)
