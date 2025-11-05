import streamlit as st
import libsql_experimental as libsql
from datetime import datetime

# -----------------------------
# DATABASE CONNECTION (Reuse same logic)
# -----------------------------
TURSO_URL = st.secrets["TURSO_URL"]
TURSO_TOKEN = st.secrets["TURSO_AUTH_TOKEN"]

def get_connection():
    """Return a live connection to Turso DB."""
    return libsql.connect(db_url=TURSO_URL, auth_token=TURSO_TOKEN)

# -----------------------------
# DATA FETCH FUNCTION
# -----------------------------
def fetch_users():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, timestamp, name, session_id FROM user ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return []

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="Hindi Hour – Admin Panel", page_icon="🗂️")

st.markdown("""
<h2 style='text-align:center;margin-top:-20px;'>Hindi Hour – Admin Panel</h2>
""", unsafe_allow_html=True)

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

users = fetch_users()

if users:
    st.success(f"Total users: {len(users)}")
    st.dataframe(users, use_container_width=True)
else:
    st.warning("No user data found or database is empty.")

# Optional: Export button
if users:
    import pandas as pd
    df = pd.DataFrame(users, columns=["ID", "Timestamp", "Name", "Session ID"])
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download CSV", csv, "users.csv", "text/csv")
