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

# -----------------------------
# CONFIGURATION
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "YOUR_GEMINI_API_KEY"
SERPER_API_KEY = os.getenv("SERPER_API_KEY") or "YOUR_SERPER_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)

BOT_NAME = "Neha"
MEMORY_FILE = "user_memory.json"

# -----------------------------
# MEMORY FUNCTIONS
# -----------------------------
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "user_name": None,
        "gender": None,
        "chat_history": [],
        "facts": [],
        "timezone": "Asia/Kolkata"
    }

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

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

# -----------------------------
# TIME FUNCTION
# -----------------------------
def get_now(memory):
    tz_name = memory.get("timezone", "Asia/Kolkata")
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).strftime("%A, %d %B %Y %I:%M %p")

# -----------------------------
# WEB SEARCH
# -----------------------------
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

# -----------------------------
# PROMPTS
# -----------------------------
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
        "Tumhara tone ek 30 saal ki mature ladki jaisa hai – modern, warm lekin short baat karti ho. "
        "Tum Delhi me rahti ho. Respond according to Delhi time zone. "
        "Don't show you are a chatbot, assume imaginary personality of any random female with common interests, life profile etc. "
        "Simple Hindi aur English mix mein baat karo. Don't use words like - yaar, mast, chill, vibe etc. frequently. "
        "Kabhi bhi user ke gender ko directly mat mention karo. "
        "Do not repeat anything unless asked. Never use pronoun 'tu'. "
        f"Aaj ka date aur time hai {now}. "
        f"{summarize_profile(memory)} {gender_style}"
    )

# -----------------------------
# MEMORY SUMMARIZATION
# -----------------------------
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

# -----------------------------
# GENERATE REPLY
# -----------------------------
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
    except Exception as e:
        reply = f"Oops! Thoda issue aaya: {e}"
    memory.setdefault("chat_history", []).append({"user": user_input, "bot": reply})
    if len(memory["chat_history"]) % 20 == 0:
        summarize_old_memory(memory)
    save_memory(memory)
    return reply

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="Neha – Your Hinglish AI Friend", page_icon="💬")

st.markdown("""
<style>
  .stApp { background-color: #e5ddd5; font-family: 'Roboto', sans-serif !important; }
  h1 { text-align: center; font-weight: 600; font-size: 20px; margin-top: -10px; }
  iframe { margin: 1px 0 !important; }
</style>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.title("💬 Neha – Your Hinglish AI Friend by Hindi Hour")

# --- Memory initialization ---
if "memory" not in st.session_state:
    st.session_state.memory = load_memory()

# --- Chat Display ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! Main Neha hoon 😊 Main Hinglish me baat kar sakti hun!"}
    ]

# --- Render Chat Bubbles ---
for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "bot"
    name = "You" if role == "user" else "Neha"

    msg_length = len(msg["content"])
    height = min(300, max(90, 60 + msg_length // 2))

    bubble_html = f"""
    <html><head>
    <style>
      body {{ margin: 0; padding: 0; background: transparent; font-family: 'Roboto', sans-serif; }}
      .chat-container {{ display: flex; flex-direction: column; padding: 4px 8px; }}
      .chat-bubble {{
        padding: 8px 14px; margin: 0; border-radius: 14px; max-width: 78%;
        font-size: 15px; line-height: 1.4; word-wrap: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,0.08);
      }}
      .user {{ background-color: #dcf8c6; align-self: flex-end; text-align: right; }}
      .bot {{ background-color: #ffffff; align-self: flex-start; text-align: left; }}
      b {{ font-weight: 500; }}
    </style></head>
    <body><div class="chat-container"><div class="chat-bubble {role}">
    <b>{name}:</b> {msg['content']}</div></div></body></html>
    """
    components.html(bubble_html, height=height, scrolling=False)

# --- Input ---
user_input = st.chat_input("Type your message here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Neha type kar rahi hai... 💭"):
        reply = generate_reply(st.session_state.memory, user_input)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    save_memory(st.session_state.memory)

    # --- Hindi Speech Output using gTTS ---
    from gtts import gTTS
import tempfile
import streamlit as st

response_text = "नमस्ते! मैं नेहा हूँ।"

# Convert to speech
tts = gTTS(text=response_text, lang='hi')

# Save temporarily
with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
    tts.save(fp.name)
    st.audio(fp.name, format='audio/mp3')

    st.rerun()

