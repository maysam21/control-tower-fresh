import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# ---------------- DATABASE ----------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect("enterprise.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        plant TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS production(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        plant TEXT,
        category TEXT,
        plan INTEGER,
        actual INTEGER
    )
    """)

    conn.commit()

    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users(username,password,role,plant) VALUES (?,?,?,?)",
            ("admin", hash_password("admin123"), "Admin", "All")
        )
        conn.commit()

    conn.close()

def get_conn():
    return sqlite3.connect("enterprise.db")

init_db()

# ---------------- LOGIN ----------------

if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.title("Manufacturing Control Tower Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        conn = get_conn()
        c = conn.cursor()
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and user[2] == hash_password(password):
            st.session_state.user = {
                "id": user[0],
                "username": user[1],
                "role": user[3],
                "plant": user[4]
            }
            st.success("Login Successful")
            st.experimental_rerun()
        else:
            st.error("Invalid Credentials")

if st.session_state.user is None:
    login()
    st.stop()

# ---------------- CONSTANTS ----------------

PLANTS = ["JD","Snoair","APT","SP","Inhouse"]
CATEGORIES = ["Chimney","Burner"]

st.sidebar.write("Logged in:", st.session_state.user["username"])
menu = st.sidebar.selectbox("Menu", ["Dashboard","Entry","User Management"])

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
        conn = get_conn()
        c = conn.cursor()
        c.execute("""
        INSERT INTO production(date,plant,category,plan,actual)
        VALUES (?,?,?,?,?)
        """, (str(date), plant, category, plan, actual))
        conn.commit()
        conn.close()
        st.success("Saved Successfully")

# ---------------- DASHBOARD ----------------

if menu == "Dashboard":

    st.markdown("""
    <style>
    .stApp { background-color: #0b1622; }
    .title {
        font-size: 42px;
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
    .panel {
        background: #132235;
        padding: 20px;
        border-radius: 12px;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='title'>MANUFACTURING CONTROL TOWER</div>", unsafe_allow_html=True)

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM production", conn)
    conn.close()

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

    # KPI Row
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-box blue'>{total_plan}<br>Total Plan</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-box blue'>{total_actual}<br>Total Actual</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-box green'>{achievement}%<br>Achievement</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-box amber'>{rejection}%<br>Rejection</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1,col2,col3 = st.columns([1.2,1,1])

    # Plant Performance
    with col1:
        st.markdown("<div class='panel'><h3>Plant Performance</h3>", unsafe_allow_html=True)
        plant_df = df.groupby("plant").agg({"plan":"sum","actual":"sum"}).reset_index()
        plant_df["Ach %"] = round((plant_df["actual"]/plant_df["plan"])*100,1)
        for _,row in plant_df.iterrows():
            color = "lightgreen" if row["Ach %"]>=95 else "orange" if row["Ach %"]>=90 else "red"
            st.markdown(f"<p style='color:{color};font-size:18px;'><b>{row['plant']}</b> - {row['Ach %']}%</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Category Panels
    with col2:
        for cat in CATEGORIES:
            st.markdown(f"<div class='panel'><h3>{cat}</h3>", unsafe_allow_html=True)
            cat_df = df[df["category"]==cat]
            if not cat_df.empty:
                ach = round((cat_df["actual"].sum()/cat_df["plan"].sum())*100,1)
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

    # Trend Chart
    st.markdown("<h3 style='color:white;'>Production Trend</h3>", unsafe_allow_html=True)

    weekly = pd.read_sql("SELECT * FROM production", get_conn())
    weekly["date"] = pd.to_datetime(weekly["date"])
    weekly = weekly.groupby("date").sum(numeric_only=True).reset_index()

    if not weekly.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["plan"], mode='lines+markers', name='Plan'))
        fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["actual"], mode='lines+markers', name='Actual'))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

# ---------------- USER MANAGEMENT ----------------

if menu == "User Management" and st.session_state.user["role"] == "Admin":

    st.title("User Management")

    conn = get_conn()
    users = pd.read_sql("SELECT id,username,role,plant FROM users", conn)
    conn.close()

    st.dataframe(users)

    st.subheader("Add User")

    new_user = st.text_input("New Username")
    new_pass = st.text_input("New Password")
    plant = st.selectbox("Plant", PLANTS)

    if st.button("Create User"):
        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute(
                "INSERT INTO users(username,password,role,plant) VALUES (?,?,?,?)",
                (new_user, hash_password(new_pass), "Supervisor", plant)
            )
            conn.commit()
            conn.close()
            st.success("User Created")
        except:
            st.error("User already exists")
