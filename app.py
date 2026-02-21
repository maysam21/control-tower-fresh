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

# ---------------- SIMPLE LOGIN ----------------

USERS = {
    "admin": {"password": "admin123", "role": "Admin", "plant": "All"},
    "jd_user": {"password": "1234", "role": "Supervisor", "plant": "JD"},
}

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

# ---------------- CONSTANTS ----------------

PLANTS = ["JD","Snoair","APT","SP","Inhouse"]
CATEGORIES = ["Chimney","Burner"]

st.sidebar.write("Logged in:", st.session_state.user["username"])
menu = st.sidebar.selectbox("Menu", ["Dashboard","Shift Entry"])

# =========================================================
# SHIFT ENTRY PAGE
# =========================================================

if menu == "Shift Entry":

    st.title("SHIFT ENTRY")

    plant = st.session_state.user["plant"]

    if st.session_state.user["role"] == "Admin":
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
# CONTROL TOWER DASHBOARD
# =========================================================

if menu == "Dashboard":

    # ---------- Styling ----------
    st.markdown("""
    <style>
    .stApp { background-color: #0b1622; }
    .main-title {
        font-size: 44px;
        font-weight: 800;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .kpi-box {
        padding: 25px;
        border-radius: 14px;
        text-align: center;
        font-size: 24px;
        font-weight: 700;
        color: white;
    }
    .blue {background: linear-gradient(135deg,#1e3a8a,#1e293b);}
    .green {background: linear-gradient(135deg,#16a34a,#065f46);}
    .amber {background: linear-gradient(135deg,#f59e0b,#b45309);}
    .panel {
        background: #132235;
        padding: 20px;
        border-radius: 14px;
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

    total_plan = df["plan"].sum()
    total_actual = df["actual"].sum()

    achievement = round((total_actual/total_plan)*100,2) if total_plan>0 else 0
    rejection = round(((total_plan-total_actual)/total_plan)*100,2) if total_plan>0 else 0

    # ---------- KPI STRIP ----------
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-box blue'>{total_plan}<br>Total Plan</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-box blue'>{total_actual}<br>Total Actual</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-box green'>{achievement}%<br>Achievement</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-box amber'>{rejection}%<br>Rejection</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- MAIN PANELS ----------
    col1,col2,col3 = st.columns([1.2,1,1])

    # Plant Performance
    with col1:
        st.markdown("<div class='panel'><h3>Plant Performance</h3>", unsafe_allow_html=True)
        plant_df = df.groupby("plant").agg({"plan":"sum","actual":"sum"}).reset_index()

        plant_df["plan"] = pd.to_numeric(plant_df["plan"], errors="coerce")
        plant_df["actual"] = pd.to_numeric(plant_df["actual"], errors="coerce")

        plant_df["Ach %"] = ((plant_df["actual"] / plant_df["plan"]) * 100).round(1)

        for _,row in plant_df.iterrows():
            color = "lightgreen" if row["Ach %"]>=95 else "orange" if row["Ach %"]>=90 else "red"
            st.markdown(
                f"<p style='color:{color};font-size:20px;'><b>{row['plant']}</b> - {row['Ach %']}%</p>",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # Category Panels
    with col2:
        for cat in CATEGORIES:
            st.markdown(f"<div class='panel'><h3>{cat}</h3>", unsafe_allow_html=True)
            cat_df = df[df["category"]==cat]
            if not cat_df.empty:
                plan_sum = pd.to_numeric(cat_df["plan"], errors="coerce").sum()
actual_sum = pd.to_numeric(cat_df["actual"], errors="coerce").sum()

ach = round((actual_sum / plan_sum) * 100, 1) if plan_sum > 0 else 0
                st.markdown(f"<h2>{ach}%</h2>", unsafe_allow_html=True)
            st.markdown("</div><br>", unsafe_allow_html=True)

    # Alerts
    with col3:
        st.markdown("<div class='panel'><h3>Alerts</h3>", unsafe_allow_html=True)
        if achievement < 90:
            st.markdown("<p style='color:red;'>🔴 Achievement below 90%</p>", unsafe_allow_html=True)
        if rejection > 5:
            st.markdown("<p style='color:orange;'>⚠ High Rejection</p>", unsafe_allow_html=True)
        if achievement >= 95:
            st.markdown("<p style='color:lightgreen;'>✅ Performing Well</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- PRODUCTION TREND ----------
    st.markdown("<h3 style='color:white;'>Production Trend</h3>", unsafe_allow_html=True)

    weekly = st.session_state.production.copy()
    weekly["date"] = pd.to_datetime(weekly["date"])
    weekly = weekly.groupby("date").sum(numeric_only=True).reset_index()

    if not weekly.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=weekly["date"],
            y=weekly["plan"],
            mode='lines+markers',
            name='Plan'
        ))
        fig.add_trace(go.Scatter(
            x=weekly["date"],
            y=weekly["actual"],
            mode='lines+markers',
            name='Actual'
        ))
        fig.update_layout(template="plotly_dark", height=450)
        st.plotly_chart(fig, use_container_width=True)

