import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# ---------------- SIMPLE AUTH ----------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Default users stored in memory
USERS = {
    "admin": {
        "password": hash_password("admin123"),
        "role": "Admin",
        "plant": "All"
    }
}

# ---------------- SESSION INIT ----------------

if "user" not in st.session_state:
    st.session_state.user = None

if "production" not in st.session_state:
    st.session_state.production = pd.DataFrame(
        columns=["date","plant","category","plan","actual"]
    )

# ---------------- LOGIN ----------------

def login():
    st.title("Manufacturing Control Tower Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if username in USERS and USERS[username]["password"] == hash_password(password):
            st.session_state.user = {
                "username": username,
                "role": USERS[username]["role"],
                "plant": USERS[username]["plant"]
            }
        else:
            st.error("Invalid Credentials")

if st.session_state.user is None:
    login()
    st.stop()

# ---------------- CONSTANTS ----------------

PLANTS = ["JD","Snoair","APT","SP","Inhouse"]
CATEGORIES = ["Chimney","Burner"]

st.sidebar.write("Logged in:", st.session_state.user["username"])
menu = st.sidebar.selectbox("Menu", ["Dashboard","Entry"])

# ---------------- ENTRY ----------------

if menu == "Entry":

    st.title("Shift Entry")

    plant = st.session_state.user["plant"]

    if st.session_state.user["role"] == "Admin":
        plant = st.selectbox("Plant", PLANTS)

    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", CATEGORIES)

    col1, col2 = st.columns(2)
    plan = col1.number_input("Plan", 0)
    actual = col2.number_input("Actual", 0)

    if st.button("Save"):

        new_row = pd.DataFrame([{
            "date": date,
            "plant": plant,
            "category": category,
            "plan": plan,
            "actual": actual
        }])

        st.session_state.production = pd.concat(
            [st.session_state.production, new_row],
            ignore_index=True
        )

        st.success("Saved Successfully")

# ---------------- DASHBOARD ----------------

if menu == "Dashboard":

    st.markdown("""
    <style>
    .stApp { background-color: #0b1622; }
    .title {
        font-size: 40px;
        font-weight: 700;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .kpi-box {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        font-size: 20px;
        font-weight: 600;
        color: white;
    }
    .blue {background: linear-gradient(135deg,#1e3a8a,#1e293b);}
    .green {background: linear-gradient(135deg,#16a34a,#065f46);}
    .amber {background: linear-gradient(135deg,#f59e0b,#b45309);}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='title'>MANUFACTURING CONTROL TOWER</div>", unsafe_allow_html=True)

    df = st.session_state.production.copy()

    if df.empty:
        st.warning("No data available")
        st.stop()

    df["date"] = pd.to_datetime(df["date"]).dt.date
    selected_date = st.date_input("Select Date", datetime.today())
    df = df[df["date"] == selected_date]

    total_plan = df["plan"].sum()
    total_actual = df["actual"].sum()

    achievement = round((total_actual/total_plan)*100,2) if total_plan>0 else 0
    rejection = round(((total_plan-total_actual)/total_plan)*100,2) if total_plan>0 else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-box blue'>{total_plan}<br>Total Plan</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-box blue'>{total_actual}<br>Total Actual</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-box green'>{achievement}%<br>Achievement</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-box amber'>{rejection}%<br>Rejection</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    weekly = st.session_state.production.copy()
    weekly["date"] = pd.to_datetime(weekly["date"])
    weekly = weekly.groupby("date").sum(numeric_only=True).reset_index()

    if not weekly.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["plan"], mode='lines+markers', name='Plan'))
        fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["actual"], mode='lines+markers', name='Actual'))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)
