import streamlit as st
import libsql_experimental as libsql_client
from datetime import datetime

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
TURSO_URL = st.secrets["TURSO_URL"]
TURSO_AUTH_TOKEN = st.secrets["TURSO_AUTH_TOKEN"]

# ✅ Compatible connection (works for both sync and async builds)
try:
    # new-style
    client = libsql_client.create_client(
        url=TURSO_URL,
        auth_token=TURSO_AUTH_TOKEN
    )
except AttributeError:
    # fallback if only sync version is available
    client = libsql_client.create_client_sync(
        url=TURSO_URL,
        auth_token=TURSO_AUTH_TOKEN
    )

# -----------------------------
# CREATE TABLE (if not exists)
# -----------------------------
client.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    name TEXT,
    session_id TEXT
);
""")

# -----------------------------
# STREAMLIT ADMIN DASHBOARD
# -----------------------------
st.set_page_config(page_title="Admin Dashboard – Neha Chat", page_icon="🧠")

st.title("🧠 Neha Chat Admin Dashboard")
st.markdown("View user sessions and details from the Turso database.")

# -----------------------------
# FETCH USER DATA
# -----------------------------
try:
    result = client.execute("SELECT name, session_id, timestamp FROM users ORDER BY id DESC;")
    rows = result.rows
except Exception as e:
    st.error(f"Failed to fetch data: {e}")
    rows = []

if not rows:
    st.info("No users found yet.")
else:
    st.subheader("📋 User Sessions")
    st.dataframe(rows)
