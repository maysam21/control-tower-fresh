import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# ---------------- SESSION INIT ----------------

if "user" not in st.session_state:
    st.session_state.user = None

if "production" not in st.session_state:
    st.session_state.production = pd.DataFrame(
        columns=["date","plant","category","plan","actual"]
    )

# ---------------- USER DATABASE ----------------

USERS = {
    "admin": {"password": "admin123", "role": "Admin", "plant": "All"},
    "jd_supervisor": {"password": "1234", "role": "Supervisor", "plant": "JD"},
    "snoair_supervisor": {"password": "1234", "role": "Supervisor", "plant": "Snoair"},
}

PLANTS = ["JD","Snoair","APT","SP","Inhouse"]
CATEGORIES = ["Chimney","Burner"]

# ---------------- LOGIN ----------------

def login():
    st.title("MANUFACTURING CONTROL TOWER")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username]["password"] == password:
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

user = st.session_state.user

# =========================================================
# ROLE BASED MENU CONTROL
# =========================================================

if user["role"] == "Admin":
    menu = st.sidebar.selectbox("Menu", ["Dashboard","Shift Entry"])
else:
    menu = "Shift Entry"   # Supervisor sees only entry

st.sidebar.write("Logged in:", user["username"])
st.sidebar.write("Role:", user["role"])
st.sidebar.write("Plant:", user["plant"])

# =========================================================
# SHIFT ENTRY (Supervisor & Admin)
# =========================================================

if menu == "Shift Entry":

    st.title("SHIFT ENTRY")

    # Supervisor fixed plant
    if user["role"] == "Supervisor":
        plant = user["plant"]
        st.subheader(f"Plant: {plant}")
    else:
        plant = st.selectbox("Plant", PLANTS)

    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", CATEGORIES)

    col1, col2 = st.columns(2)
    plan = col1.number_input("Plan", 0)
    actual = col2.number_input("Actual", 0)

    if st.button("Save Entry"):

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

        st.success("Entry Saved Successfully")

# =========================================================
# DASHBOARD (Admin Only)
# =========================================================

if menu == "Dashboard" and user["role"] == "Admin":

    st.markdown("""
    <style>
    .stApp { background-color: #0b1622; }
    .main-title {
        font-size: 42px;
        font-weight: 800;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .kpi-box {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        font-size: 22px;
        font-weight: 700;
        color: white;
    }
    .blue {background: linear-gradient(135deg,#1e3a8a,#1e293b);}
    .green {background: linear-gradient(135deg,#16a34a,#065f46);}
    .amber {background: linear-gradient(135deg,#f59e0b,#b45309);}
    .panel {
        background: #132235;
        padding: 20px;
        border-radius: 12px;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='main-title'>MANUFACTURING CONTROL TOWER</div>", unsafe_allow_html=True)

    df = st.session_state.production.copy()

    if df.empty:
        st.warning("No production data available")
        st.stop()

    df["date"] = pd.to_datetime(df["date"]).dt.date

    selected_date = st.date_input("Select Date", datetime.today())
    df = df[df["date"] == selected_date]

    df["plan"] = pd.to_numeric(df["plan"], errors="coerce")
    df["actual"] = pd.to_numeric(df["actual"], errors="coerce")

    total_plan = df["plan"].sum()
    total_actual = df["actual"].sum()

    achievement = round((total_actual/total_plan)*100,2) if total_plan>0 else 0
    rejection = round(((total_plan-total_actual)/total_plan)*100,2) if total_plan>0 else 0

    # KPI STRIP
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-box blue'>{int(total_plan)}<br>Total Plan</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-box blue'>{int(total_actual)}<br>Total Actual</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-box green'>{achievement}%<br>Achievement</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-box amber'>{rejection}%<br>Rejection</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Plant Performance
    st.markdown("<div class='panel'><h3>Plant Performance</h3>", unsafe_allow_html=True)

    plant_df = df.groupby("plant").agg({"plan":"sum","actual":"sum"}).reset_index()
    plant_df["plan"] = pd.to_numeric(plant_df["plan"], errors="coerce")
    plant_df["actual"] = pd.to_numeric(plant_df["actual"], errors="coerce")
    plant_df["Ach %"] = ((plant_df["actual"]/plant_df["plan"])*100).round(1)

    for _,row in plant_df.iterrows():
        ach_val = row["Ach %"] if pd.notna(row["Ach %"]) else 0
        color = "lightgreen" if ach_val>=95 else "orange" if ach_val>=90 else "red"
        st.markdown(
            f"<p style='color:{color};font-size:18px;'><b>{row['plant']}</b> - {ach_val}%</p>",
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)
