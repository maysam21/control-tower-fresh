import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# =====================================================
# FILE PATHS (Persistent Storage)
# =====================================================

USERS_FILE = "users.json"
DATA_FILE = "production.json"

PLANTS = ["JD", "Snoair", "APT", "SP", "Inhouse"]
CATEGORIES = ["Chimney", "Burner"]

# =====================================================
# INITIAL FILE SETUP
# =====================================================

def init_files():

    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "password": "admin123",
                "role": "Admin",
                "plant": "All"
            }
        }
        with open(USERS_FILE, "w") as f:
            json.dump(default_users, f)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump([], f)

init_files()

# =====================================================
# LOAD & SAVE FUNCTIONS
# =====================================================

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return pd.DataFrame(json.load(f))

def save_data(df):
    df["date"] = df["date"].astype(str)
    with open(DATA_FILE, "w") as f:
        json.dump(df.to_dict(orient="records"), f)

# =====================================================
# SESSION INIT
# =====================================================

if "user" not in st.session_state:
    st.session_state.user = None

# =====================================================
# STYLING
# =====================================================

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
    padding: 25px;
    border-radius: 12px;
    text-align: center;
    font-size: 24px;
    font-weight: 700;
    color: white;
}

.blue {background: linear-gradient(135deg,#1e3a8a,#1e293b);}
.green {background: linear-gradient(135deg,#16a34a,#065f46);}
.amber {background: linear-gradient(135deg,#f59e0b,#b45309);}
.red {background: linear-gradient(135deg,#dc2626,#7f1d1d);}

.panel {
    background: #132235;
    padding: 20px;
    border-radius: 14px;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# LOGIN SYSTEM
# =====================================================

def login_screen():

    st.markdown("<div class='main-title'>MANUFACTURING CONTROL TOWER</div>", unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        users = load_users()

        if username in users and users[username]["password"] == password:
            st.session_state.user = {
                "username": username,
                "role": users[username]["role"],
                "plant": users[username]["plant"]
            }
            st.rerun()
        else:
            st.error("Invalid Credentials")

if st.session_state.user is None:
    login_screen()
    st.stop()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.success(f"Logged in: {st.session_state.user['username']}")

if st.session_state.user["role"] == "Admin":
    menu = st.sidebar.selectbox("Menu", ["Dashboard", "Shift Entry", "User Management"])
else:
    menu = "Shift Entry"

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# =====================================================
# SHIFT ENTRY (SUPERVISOR ONLY)
# =====================================================

if menu == "Shift Entry":

    st.markdown("<div class='main-title'>SHIFT ENTRY</div>", unsafe_allow_html=True)

    if st.session_state.user["role"] == "Admin":
        plant = st.selectbox("Plant", PLANTS)
    else:
        plant = st.session_state.user["plant"]
        st.info(f"Plant Assigned: {plant}")

    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", CATEGORIES)

    col1, col2 = st.columns(2)
    plan = col1.number_input("Plan", 0)
    actual = col2.number_input("Actual", 0)

    if st.button("Save Entry"):

        df = load_data()

        new_row = pd.DataFrame([{
            "date": date,
            "plant": plant,
            "category": category,
            "plan": plan,
            "actual": actual
        }])

        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df)

        st.success("Entry Saved")

# =====================================================
# DASHBOARD
# =====================================================

if menu == "Dashboard":

    st.markdown("<div class='main-title'>MANUFACTURING CONTROL TOWER</div>", unsafe_allow_html=True)

    df = load_data()

    if df.empty:
        st.warning("No data available")
        st.stop()

    df["date"] = pd.to_datetime(df["date"]).dt.date

    selected_date = st.date_input("Select Date", datetime.today())
    df = df[df["date"] == selected_date]

    total_plan = df["plan"].sum()
    total_actual = df["actual"].sum()

    achievement = round((total_actual / total_plan) * 100, 2) if total_plan > 0 else 0
    rejection = round(((total_plan - total_actual) / total_plan) * 100, 2) if total_plan > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-box blue'>{total_plan}<br>Total Plan</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-box blue'>{total_actual}<br>Total Actual</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-box green'>{achievement}%<br>Achievement</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-box amber'>{rejection}%<br>Rejection</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    weekly = load_data()
    weekly["date"] = pd.to_datetime(weekly["date"])
    weekly = weekly.groupby("date").sum(numeric_only=True).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["plan"], mode='lines+markers', name='Plan'))
    fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["actual"], mode='lines+markers', name='Actual'))
    fig.update_layout(template="plotly_dark", height=450)

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# USER MANAGEMENT
# =====================================================

if menu == "User Management":

    st.markdown("<div class='main-title'>USER MANAGEMENT</div>", unsafe_allow_html=True)

    users = load_users()

    users_df = pd.DataFrame([
        {
            "Username": u,
            "Role": users[u]["role"],
            "Plant": users[u]["plant"]
        }
        for u in users
    ])

    st.dataframe(users_df)

    st.markdown("---")
    st.subheader("Create User")

    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Supervisor", "Admin"])
    plant = st.selectbox("Plant Mapping", PLANTS)

    if st.button("Create User"):
        if new_user in users:
            st.error("User already exists")
        else:
            users[new_user] = {
                "password": new_pass,
                "role": role,
                "plant": plant
            }
            save_users(users)
            st.success("User Created")
            st.rerun()
