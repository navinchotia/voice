import streamlit as st
from openai import OpenAI
from google.cloud import speech
from gtts import gTTS
import io
import os

# --- Configuration ---
st.set_page_config(page_title="Neha Hindi Chatbot - with Voice", page_icon="🪷")
st.title("🪷 Neha - Hindi Practice Chatbot (with Voice)")
st.markdown("Chat with Neha in Hindi or Hinglish — now with voice support!")

# --- Initialize API keys ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_key.json"

# --- Transcribe Audio using Google Cloud ---
def transcribe_audio(audio_bytes):
    client_speech = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="hi-IN"
    )
    response = client_speech.recognize(config=config, audio=audio)
    return response.results[0].alternatives[0].transcript if response.results else ""

# --- Generate TTS (gTTS) ---
def speak_text(text):
    tts = gTTS(text=text, lang='hi')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    st.audio(audio_fp, format='audio/mp3', autoplay=True)

# --- Chatbot logic (same as your Neha chatbot) ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def get_neha_reply(user_input):
    conversation = [{"role": "system", "content": "You are Neha, a friendly Hindi practice chatbot."}]
    for msg in st.session_state.chat_history:
        conversation.append({"role": msg["role"], "content": msg["content"]})
    conversation.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation,
    )
    reply = response.choices[0].message.content
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.session_state.chat_history.append({"role": "assistant", "content": reply})
    return reply

# --- UI ---
audio_data = st.audio_input("🎤 Record your message (Hindi or Hinglish):")

if audio_data:
    st.info("Transcribing speech...")
    transcript = transcribe_audio(audio_data.getvalue())
    if transcript:
        st.write(f"**You said:** {transcript}")
        reply = get_neha_reply(transcript)
        st.markdown(f"**Neha:** {reply}")
        speak_text(reply)
    else:
        st.warning("Could not understand the audio. Try again.")

user_text = st.text_input("💬 Or type your message here:")
if st.button("Send") and user_text:
    reply = get_neha_reply(user_text)
    st.markdown(f"**Neha:** {reply}")
    speak_text(reply)
