import streamlit as st
import libsql_experimental as libsql
from datetime import datetime

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
TURSO_URL = st.secrets["TURSO_URL"]
TURSO_AUTH_TOKEN = st.secrets["TURSO_AUTH_TOKEN"]

def get_connection():
    """Create a synchronous connection to Turso"""
    # Some builds of libsql_experimental expect positional args only
    return libsql.connect(TURSO_URL, TURSO_AUTH_TOKEN)

def get_all_users():
    """Fetch all user records"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT timestamp, name, session_id FROM user ORDER BY id DESC;")
        data = cur.fetchall()
    except Exception as e:
        st.error(f"Database query error: {e}")
        data = []
    conn.close()
    return data

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
    rows = get_all_users()
except Exception as e:
    st.error(f"Failed to fetch data: {e}")
    rows = []

if not rows:
    st.info("No users found yet.")
else:
    st.subheader("📋 User Sessions")
    st.dataframe(rows)
