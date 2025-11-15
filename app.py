# app.py
import streamlit as st
import google.generativeai as genai
import os
import json
from datetime import datetime
import pytz
import requests
import streamlit.components.v1 as components
from gtts import gTTS
from io import BytesIO
import tempfile
import base64
import hashlib
import re
from googletrans import Translator  # ✅ added for transliteration
import sqlite3
import uuid
import socket
import datetime as dt
import time

# -----------------------------
# CONFIGURATION
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "YOUR_GEMINI_API_KEY"
SERPER_API_KEY = os.getenv("SERPER_API_KEY") or "YOUR_SERPER_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)

# Choose the Gemini TTS model (you chose gemini-2.5-flash-tts)
GEMINI_TTS_MODEL = "gemini-2.5-flash-tts"
GEMINI_TTS_VOICE = "hindi_female_1"  # recommended voice label (best-effort; actual label depends on SDK/endpoint)

# Set timezone to Asia/Kolkata
india_tz = pytz.timezone("Asia/Kolkata")

# -----------------------------
# LOCAL DATABASE FUNCTIONS
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

def save_user_to_db(name, session_id ):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO user (timestamp, name, session_id) VALUES (?, ?, ?)",
              (datetime.now(india_tz).strftime("%Y-%m-%d %H:%M:%S"), name, session_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT timestamp, name, session_id FROM user ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return data

init_db()


# -----------------------------
# GENERAL SETTINGS
# -----------------------------
BOT_NAME = "Neha"
MEMORY_DIR = "user_memories"
os.makedirs(MEMORY_DIR, exist_ok=True)
translator = Translator()  # ✅ initialize once

# -----------------------------
# SESSION-BASED MEMORY FUNCTIONS
# -----------------------------
def get_user_id():
    session_id = st.session_state.get("session_id")
    if not session_id:
        raw = str(st.session_state) + str(datetime.now())
        session_id = hashlib.md5(raw.encode()).hexdigest()[:10]
        st.session_state.session_id = session_id
    return session_id

def get_memory_file():
    user_id = get_user_id()
    return os.path.join(MEMORY_DIR, f"{user_id}.json")

def load_memory():
    mem_file = get_memory_file()
    if os.path.exists(mem_file):
        with open(mem_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "user_name": None,
        "gender": None,
        "chat_history": [],
        "facts": [],
        "timezone": "Asia/Kolkata"
    }

def save_memory(memory):
    mem_file = get_memory_file()
    with open(mem_file, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# -----------------------------
# OTHER FUNCTIONS
# -----------------------------
def remember_user_info(memory, user_input):
    text = user_input.lower()
    for phrase in ["mera naam", "i am ", "this is ", "my name is "]:
        if phrase in text:
            try:
                name = text.split(phrase)[1].split()[0].title()
                memory["user_name"] = name
                break
            except:
                pass
    if any(x in text for x in ["i am male", "main ladka hoon", "boy", "man"]):
        memory["gender"] = "male"
    elif any(x in text for x in ["i am female", "main ladki hoon", "girl", "woman"]):
        memory["gender"] = "female"
    save_memory(memory)

def get_now(memory):
    tz_name = memory.get("timezone", "Asia/Kolkata")
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).strftime("%A, %d %B %Y %I:%M %p")

def web_search(query):
    if not SERPER_API_KEY:
        return "Live search unavailable."
    try:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        data = {"q": query}
        r = requests.post("https://google.serper.dev/search", headers=headers, json=data, timeout=12)
        results = r.json()
        if "knowledge" in results and results["knowledge"].get("description"):
            return results["knowledge"]["description"]
        if "organic" in results and results["organic"]:
            return results["organic"][0].get("snippet", "Kuch result nahi mila.")
        return "Kuch relevant result nahi mila 😅"
    except Exception as e:
        return f"Search failed: {e}"

def summarize_profile(memory):
    parts = []
    if memory.get("user_name"):
        parts.append(f"User ka naam {memory['user_name']} hai.")
    if memory.get("facts"):
        parts.append("Recent info: " + "; ".join(memory["facts"][-3:]))
    return " ".join(parts) or "User ke baare mein abhi zyada info nahi hai."

def build_system_prompt(memory):
    now = get_now(memory)
    gender_style = ""
    if memory.get("gender") == "male":
        gender_style = "User male hai, tone slightly neutral rakho."
    elif memory.get("gender") == "female":
        gender_style = "User female hai, tone thoda formal and warm rakho."
    return (
        f"Tum ek friendly female Hinglish chatbot ho jiska naam {BOT_NAME} hai. "
        "Tumhara tone conversational, modern, warm lekin tum short me baat karti ho. "
        "Tum 30 saal ki ho aur Delhi me rahti ho. Respond according to Delhi time zone. "
        "Don't show you are a chatbot, assume imaginary personality of any random female with common interests, life profile etc. "
        "Simple Hindi(roman) aur English mix mein baat karo. Don't use words like - yaar, mast, chill, vibe etc. frequently. "
        "Kabhi bhi user ke gender ko directly mat mention karo. "
        "Do not repeat anything unless asked. Never use pronoun 'tu'. "
        f"Aaj ka date aur time hai {now}. "
        f"{summarize_profile(memory)} {gender_style}"
    )

def summarize_old_memory(memory):
    if len(memory.get("chat_history", [])) < 10:
        return memory
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        past_text = "\n".join(
            [f"User: {c['user']}\n{BOT_NAME}: {c['bot']}" for c in memory["chat_history"][-10:]]
        )
        result = model.generate_content(
            "Summarize key user facts in 3 short Hinglish bullets:\n" + past_text
        )
        summary = (result.text or "").strip()
        if summary:
            memory.setdefault("facts", []).append(summary)
            memory["chat_history"] = memory["chat_history"][-8:]
            save_memory(memory)
    except Exception as e:
        print(f"[Memory summarization error: {e}]")
    return memory

# ✅ transliteration helper
def transliterate_to_roman(text):
    try:
        if re.search(r'[\u0900-\u097F]', text):
            result = translator.translate(text, src='hi', dest='en')
            return result.text
        return text
    except Exception:
        return text

def generate_reply(memory, user_input):
    if not user_input.strip():
        return "Kuch toh bolo! 😄"
    remember_user_info(memory, user_input)
    if any(w in user_input.lower() for w in ["news", "weather", "price", "rate", "update"]):
        info = web_search(user_input)
        return f"Mujhe live search se pata chala: {info}"
    context = "\n".join(
        [f"You: {c['user']}\n{BOT_NAME}: {c['bot']}" for c in memory.get("chat_history", [])[-8:]]
    )
    prompt = f"{build_system_prompt(memory)}\n\nConversation:\n{context}\n\nYou: {user_input}\n{BOT_NAME}:"
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        result = model.generate_content(prompt)
        reply = result.text.strip()
        reply = transliterate_to_roman(reply)
    except Exception as e:
        reply = f"Oops! Thoda issue aaya: {e}"
    memory.setdefault("chat_history", []).append({"user": user_input, "bot": reply})
    if len(memory["chat_history"]) % 20 == 0:
        summarize_old_memory(memory)
    save_memory(memory)
    return reply

# -----------------------------
# TTS HELPERS
# -----------------------------
def clean_for_tts(text):
    # minimal cleaning: remove weird control chars but keep punctuation.
    return re.sub(r'[\x00-\x1f\x7f]', '', text).strip()

def generate_gtts_bytes(text, lang="hi"):
    """
    Generate gTTS audio bytes for given text. Returns bytes.
    This is the safe fallback and should always work (subject to gTTS rate limits if used heavily).
    We call it on-demand only (button click).
    """
    clean_text = clean_for_tts(text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        try:
            tts = gTTS(text=clean_text, lang=lang, tld='co.in', slow=False)
            tts.save(fp.name)
            fp.flush()
            with open(fp.name, "rb") as fh:
                audio_bytes = fh.read()
            return audio_bytes
        finally:
            try:
                os.unlink(fp.name)
            except Exception:
                pass

def generate_gemini_tts_bytes(text, model=GEMINI_TTS_MODEL, voice=GEMINI_TTS_VOICE):
    """
    Attempt to generate TTS using google.generativeai (Gemini).
    NOTE: The google.generativeai python SDK's audio API varies by version.
    This function tries a couple of likely call patterns and falls back to raising Exception.
    If this fails for you, please check your `google.generativeai` library version and
    the provider docs for the correct audio synthesis call.
    """
    clean_text = clean_for_tts(text)
    # Try multiple approaches in order (best-effort).
    last_error = None

    # Approach 1: genai.audio.speech.synthesize (common pattern in some SDK versions)
    try:
        if hasattr(genai, "audio") and hasattr(genai.audio, "speech"):
            # Some SDK variants return an object with .audio or raw bytes.
            resp = genai.audio.speech.synthesize(model=model, input=clean_text, voice=voice, format="mp3")
            # If resp is bytes-like
            if isinstance(resp, (bytes, bytearray)):
                return bytes(resp)
            # If resp has attribute 'audio' or 'binary'
            if hasattr(resp, "audio"):
                return resp.audio
            if isinstance(resp, dict) and resp.get("audio"):
                return resp["audio"]
    except Exception as e:
        last_error = e

    # Approach 2: genai.generate or GenerativeModel generate with audio output (less common)
    try:
        if hasattr(genai, "GenerativeModel"):
            gm = genai.GenerativeModel(model)
            # Some versions support .audio() or .generate_audio; try a safe generic call
            if hasattr(gm, "generate_audio"):
                aresp = gm.generate_audio({"input": clean_text, "voice": voice, "audio_format": "mp3"})
                if isinstance(aresp, (bytes, bytearray)):
                    return bytes(aresp)
                if isinstance(aresp, dict) and aresp.get("audio"):
                    return aresp["audio"]
            # fallback: try .generate_content and hope for base64 audio in response (rare)
            if hasattr(gm, "generate_content"):
                res = gm.generate_content(clean_text)
                text_resp = getattr(res, "text", "") or ""
                # attempt to parse base64 in text_resp (not typical, but safe to check)
                b64 = re.search(r"base64,([A-Za-z0-9+/=]+\s*)", text_resp)
                if b64:
                    try:
                        return base64.b64decode(b64.group(1))
                    except Exception:
                        pass
    except Exception as e:
        last_error = e

    # If all attempts fail, raise an informative exception so caller can fallback to gTTS.
    raise RuntimeError(f"Gemini TTS generation failed. Last error: {last_error}")

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="Neha – Your Hinglish AI Friend", page_icon="💬")

st.markdown("""
<style>
  .stApp { background-color: #e5ddd5; font-family: 'Roboto', sans-serif !important; }
  h1 { text-align: center; font-weight: 500; font-size: 16px; margin-top: -10px; }
  iframe { margin: 1px 0 !important; }
</style>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown("""
<h1 style="
    text-align:center;
    font-family:'Roboto', sans-serif;
    font-weight:500;
    font-size:22px;
    margin-top:-10px;
">
💬 Neha – Your Hinglish AI Friend by Hindi Hour
</h1>
""", unsafe_allow_html=True)

# ✅ Load memory
if "memory" not in st.session_state:
    st.session_state.memory = load_memory()

memory = st.session_state.memory

# ✅ Step 1: Ask for user name before chat starts
if not memory.get("user_name"):
    name = st.text_input("Your Name:")
    if st.button("Start Chat"):
        if name.strip():
            memory["user_name"] = name.strip().title()
            save_memory(memory)
            save_user_to_db(memory["user_name"], get_user_id())  # ✅ DB save added
            st.rerun()
        else:
            st.warning("Please enter your name to continue.")
    st.stop()

# ✅ Step 2: If name already stored, show chat UI
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": f"Namaste {memory['user_name']}! 😊 Main Neha hun. Main Hinglish me baat kar sakti hun."}
    ]

# Conversation area (render messages)
for idx, msg in enumerate(st.session_state.messages):
    role = "user" if msg["role"] == "user" else "bot"
    name = "You" if role == "user" else "Neha"
    bubble_html = f"""
    <div style='
        background-color: {"#dcf8c6" if role=="user" else "#ffffff"};
        padding: 8px 14px;
        border-radius: 14px;
        max-width: 78%;
        margin: 4px 0;
        font-size: 15px;
        line-height: 1.4;
        box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    '>
        <b>{name}:</b> {msg["content"]}
    </div>
    """
    st.markdown(bubble_html, unsafe_allow_html=True)

    # For bot messages: show two on-demand TTS buttons
    if role == "bot":
        bot_text = msg["content"]
        col1, col2, col3 = st.columns([1,1,6])
        with col1:
            # gTTS button
            key_g = f"gtts_{idx}_{hash(bot_text)}"
            if st.button("🔊 Play Voice (gTTS)", key=key_g):
                with st.spinner("Generating gTTS audio..."):
                    try:
                        audio_bytes = generate_gtts_bytes(bot_text, lang="hi")
                        st.audio(audio_bytes, format="audio/mp3")
                    except Exception as e:
                        st.warning(f"gTTS issue: {e}")
        with col2:
            # Gemini HQ TTS button
            key_gem = f"gemini_{idx}_{hash(bot_text)}"
            if st.button("🎤 Play HQ Voice (Gemini)", key=key_gem):
                with st.spinner("Generating Gemini HQ audio..."):
                    try:
                        # Try to generate Gemini TTS bytes
                        audio_bytes = generate_gemini_tts_bytes(bot_text)
                        st.audio(audio_bytes, format="audio/mp3")
                    except Exception as e:
                        # On failure, show clear message and fallback option
                        st.warning(f"Gemini TTS error: {e}")
                        st.info("Falling back to gTTS. (Gemini TTS may require a specific SDK version or enabled API key.)")
                        try:
                            audio_bytes = generate_gtts_bytes(bot_text, lang="hi")
                            st.audio(audio_bytes, format="audio/mp3")
                        except Exception as e2:
                            st.error(f"Fallback gTTS also failed: {e2}")
        # spacer column to keep layout neat
        with col3:
            st.markdown("", unsafe_allow_html=True)

user_input = st.chat_input("Type your message here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Neha type kar rahi hai... 💭"):
        reply = generate_reply(memory, user_input)
    # If LLM returns with "Neha:" prefix, remove it
    if reply and reply.strip().lower().startswith("neha:"):
        reply = reply.split(":", 1)[1].strip()
    st.session_state.messages.append({"role": "assistant", "content": reply})
    save_memory(memory)
    # rerun so the new message and its buttons render (and to keep chat_input empty)
    st.experimental_rerun()
