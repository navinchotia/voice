import streamlit as st
import sqlite3
from datetime import datetime

st.title("🧾 Neha Chatbot – User Database")

conn = sqlite3.connect("users.db")
c = conn.cursor()
c.execute("SELECT timestamp, name, session_id FROM users ORDER BY id DESC")
rows = c.fetchall()
conn.close()

if rows:
    st.dataframe(rows, use_container_width=True)
else:
    st.info("No users yet!")
