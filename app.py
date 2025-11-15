import streamlit as st
import google.generativeai as genai
import requests
from gtts import gTTS
from io import BytesIO
import base64
import json
import os

# --------------------------
# CONFIG
# --------------------------
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
genai.configure(api_key=API_KEY)

TTS_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-tts:generateContent?key=" + API_KEY

# --------------------------
# FUNCTIONS
# --------------------------

def text_to_speech_gemini(text):
    """Generate audio using Gemini Flash TTS via REST API."""
    try:
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generation_config": {
                "audioConfig": {
                    "voiceName": "HINDI_FEMALE_1"
                }
            }
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(TTS_URL, headers=headers, data=json.dumps(payload))

        if response.status_code != 200:
            st.error(f"Gemini error: {response.text}")
            return None

        data = response.json()

        # Extract base64 audio
        audio_b64 = (
            data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("audioData")
        )

        if not audio_b64:
            st.error("No audio data received from Gemini.")
            return None

        return base64.b64decode(audio_b64)

    except Exception as e:
        st.error(f"Gemini TTS error: {e}")
        return None


def text_to_speech_gtts(text):
    """Generate audio using gTTS offline."""
    try:
        tts = gTTS(text=text, lang="hi")
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        st.error(f"gTTS error: {e}")
        return None

# --------------------------
# UI
# --------------------------

st.title("Neha Chatbot – Gemini Flash TTS + gTTS")

text = st.text_area("Enter Hindi text to speak:", height=150)

col1, col2 = st.columns(2)

with col1:
    if st.button("🔊 Gemini Flash TTS"):
        if text.strip():
            audio = text_to_speech_gemini(text)
            if audio:
                st.audio(audio, format="audio/mp3")
        else:
            st.warning("Please enter some text.")

with col2:
    if st.button("🎙️ gTTS Speech"):
        if text.strip():
            audio = text_to_speech_gtts(text)
            if audio:
                st.audio(audio, format="audio/mp3")
        else:
            st.warning("Please enter some text.")
