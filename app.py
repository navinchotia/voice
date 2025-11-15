import streamlit as st
import google.generativeai as genai
from google.generativeai import client
import os
import json
from datetime import datetime
import pytz
import requests
import sqlite3
import re
import tempfile
import base64
import hashlib
from gtts import gTTS

# -----------------------------
# CONFIGURATION
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "YOUR_GEMINI_API_KEY"
SERPER_API_KEY = os.getenv("SERPER_API_KEY") or "YOUR_SERPER_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)

india_tz = pytz.timezone("Asia/Kolkata")

# -----------------------------
# DATABASE
# -----------------------------
DB_PATH = "userlog.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            name TEXT,
            session_id TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_user_to_db(name, session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO user (timestamp, name, session_id) VALUES (?, ?, ?)",
              (datetime.now(india_tz).strftime("%Y-%m-%d %H:%M:%S"), name, session_id))
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# MEMORY
# -----------------------------
BOT_NAME = "Neha"
MEMORY_DIR = "user_memories"
os.makedirs(MEMORY_DIR, exist_ok=True)

def get_user_id():
    session_id = st.session_state.get("session_id")
    if not session_id:
        raw = str(st.session_state) + str(datetime.now())
        session_id = hashlib.md5(raw.encode()).hexdigest()[:10]
        st.session_state.session_id = session_id
    return session_id

def get_memory_file():
    return os.path.join(MEMORY_DIR, f"{get_user_id()}.json")

def load_memory():
    mem_file = get_memory_file()
    if os.path.exists(mem_file):
        return json.load(open(mem_file, "r", encoding="utf-8"))
    return {"user_name": None, "gender": None, "chat_history": [], "facts": [], "timezone": "Asia/Kolkata"}

def save_memory(memory):
    json.dump(memory, open(get_memory_file(), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def remember_user_info(memory, user_input):
    text = user_input.lower()
    for phrase in ["mera naam", "my name is ", "i am ", "this is "]:
        if phrase in text:
            try:
                memory["user_name"] = text.split(phrase)[1].split()[0].title()
                save_memory(memory)
                return
            except:
                pass

def get_now(memory):
    try:
        tz = pytz.timezone(memory.get("timezone", "Asia/Kolkata"))
    except:
        tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).strftime("%A, %d %B %Y %I:%M %p")

def summarize_profile(memory):
    parts = []
    if memory.get("user_name"):
        parts.append(f"User ka naam {memory['user_name']} hai.")
    if memory.get("facts"):
        parts.append("Recent info: " + "; ".join(memory["facts"][-2:]))
    return " ".join(parts)

# -----------------------------
# CHAT MODEL PROMPT
# -----------------------------
def build_system_prompt(memory):
    now = get_now(memory)
    return (
        f"Tum ek friendly female Hinglish chatbot ho jiska naam {BOT_NAME} hai. "
        "Tone warm, short, natural Hinglish. Never use 'tu'. "
        f"Aaj ka time: {now}. {summarize_profile(memory)}"
    )

# -----------------------------
# WEB SEARCH (optional)
# -----------------------------
def web_search(query):
    if not SERPER_API_KEY:
        return "Search unavailable."
    try:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        data = {"q": query}
        r = requests.post("https://google.serper.dev/search", headers=headers, json=data, timeout=12)
        results = r.json()
        if "knowledge" in results and results["knowledge"].get("description"):
            return results["knowledge"]["description"]
        if "organic" in results and results["organic"]:
            return results["organic"][0].get("snippet", "")
        return "No result mila."
    except:
        return "Search error."

# -----------------------------
# CHAT GENERATION
# -----------------------------
def generate_reply(memory, user_input):
    remember_user_info(memory, user_input)
    if any(w in user_input.lower() for w in ["news", "weather", "price", "rate"]):
        return "Search info: " + web_search(user_input)

    context = "\n".join([f"You: {c['user']}\nNeha: {c['bot']}" for c in memory["chat_history"][-8:]])
    prompt = f"{build_system_prompt(memory)}\n\n{context}\nYou: {user_input}\nNeha:"

    model = genai.GenerativeModel("gemini-2.5-flash")
    result = model.generate_content(prompt)
    reply = result.text.strip()

    memory["chat_history"].append({"user": user_input, "bot": reply})
    save_memory(memory)
    return reply

# -----------------------------
# TTS FUNCTIONS
# -----------------------------
def generate_tts_gtts(text):
    try:
        tts = gTTS(text=text, lang="hi", tld="co.in")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return open(fp.name, "rb").read()
    except Exception as e:
        st.warning(f"gTTS error: {e}")
        return None

def generate_tts_gemini(text):
    try:
        media = client.speech.generate(
            model="gemini-2.5-flash-tts",
            input_text=text
        )
        return media.audio
    except Exception as e:
        st.warning(f"Gemini TTS error: {e}")
        return None

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="Neha Chat", page_icon="💬")

st.markdown("""
<style>
  .stApp { background:#e5ddd5; font-family:'Roboto', sans-serif; }
  .bubble { padding:8px 14px; border-radius:14px; max-width:75%; margin:5px 0; }
</style>
""", unsafe_allow_html=True)

if "memory" not in st.session_state:
    st.session_state.memory = load_memory()
memory = st.session_state.memory

# Ask name
if not memory.get("user_name"):
    name = st.text_input("Your Name:")
    if st.button("Start Chat"):
        if name.strip():
            memory["user_name"] = name.strip().title()
            save_memory(memory)
            save_user_to_db(memory["user_name"], get_user_id())
            st.rerun()
        else:
            st.warning("Enter name.")
    st.stop()

# Chat messages
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": f"Namaste {memory['user_name']}! 😊 Main Neha hun, Hinglish me baat karti hun."}
    ]

# Display chat history
for msg in st.session_state.messages:
    role = msg["role"]
    text = msg["content"]
    color = "#dcf8c6" if role == "user" else "#ffffff"
    name = "You" if role == "user" else "Neha"

    st.markdown(
        f"<div class='bubble' style='background:{color}'><b>{name}:</b> {text}</div>",
        unsafe_allow_html=True
    )

    # TTS only for bot
    if role == "assistant":
        clean_text = re.sub(r'[^\w\s,.!?\-]', '', text)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔊 gTTS", key=f"g{hash(text)}"):
                audio = generate_tts_gtts(clean_text)
                if audio:
                    st.audio(audio, format="audio/mp3")

        with col2:
            if st.button("🎙 Gemini TTS", key=f"gm{hash(text)}"):
                audio = generate_tts_gemini(clean_text)
                if audio:
                    st.audio(audio, format="audio/mp3")

# Input box
user_input = st.chat_input("Type your message...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    reply = generate_reply(memory, user_input)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
