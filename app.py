import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# =====================================================
# DATABASE SETUP
# =====================================================

def get_connection():
    conn = sqlite3.connect("control_tower.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Users Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            plant TEXT
        )
    """)

    # Production Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            plant TEXT,
            category TEXT,
            plan INTEGER,
            actual INTEGER
        )
    """)

    # Default Admin
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?)",
                  ("admin","admin123","Admin","All"))

    conn.commit()
    conn.close()

init_db()

# =====================================================
# LOGIN SYSTEM
# =====================================================

if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.title("MANUFACTURING CONTROL TOWER")

    username = st.text_input("Username").strip()
    password = st.text_input("Password", type="password").strip()

    if st.button("Login"):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (username,password))
        user = c.fetchone()
        conn.close()

        if user:
            st.session_state.user = {
                "username": user[0],
                "role": user[2],
                "plant": user[3]
            }
        else:
            st.error("Invalid Credentials")

if st.session_state.user is None:
    login()
    st.stop()

# =====================================================
# SIDEBAR
# =====================================================

PLANTS = ["JD","Snoair","APT","SP","Inhouse"]
CATEGORIES = ["Chimney","Burner"]

st.sidebar.success(f"Logged in: {st.session_state.user['username']}")

if st.session_state.user["role"] == "Admin":
    menu = st.sidebar.selectbox("Menu", ["Dashboard","Shift Entry","User Management"])
else:
    menu = "Shift Entry"

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.stop()

# =====================================================
# SHIFT ENTRY
# =====================================================

if menu == "Shift Entry":

    st.title("SHIFT ENTRY")

    if st.session_state.user["role"] == "Supervisor":
        plant = st.session_state.user["plant"]
        st.info(f"Plant Assigned: {plant}")
    else:
        plant = st.selectbox("Plant", PLANTS)

    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", CATEGORIES)

    col1,col2 = st.columns(2)
    plan = col1.number_input("Plan", 0)
    actual = col2.number_input("Actual", 0)

    if st.button("Save Entry"):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO production (date,plant,category,plan,actual)
            VALUES (?,?,?,?,?)
        """,(str(date),plant,category,plan,actual))
        conn.commit()
        conn.close()
        st.success("Entry Saved Successfully")

# =====================================================
# DASHBOARD
# =====================================================

if menu == "Dashboard":

    st.title("MANUFACTURING CONTROL TOWER")

    conn = get_connection()
    df = pd.read_sql("SELECT * FROM production", conn)
    conn.close()

    if df.empty:
        st.warning("No production data available")
        st.stop()

    df["date"] = pd.to_datetime(df["date"]).dt.date
    selected_date = st.date_input("Select Date", datetime.today())
    df = df[df["date"] == selected_date]

    total_plan = df["plan"].sum()
    total_actual = df["actual"].sum()

    achievement = round((total_actual/total_plan)*100,2) if total_plan>0 else 0

    col1,col2,col3 = st.columns(3)
    col1.metric("Total Plan", total_plan)
    col2.metric("Total Actual", total_actual)
    col3.metric("Achievement %", achievement)

    weekly = pd.read_sql("SELECT date,SUM(plan) plan,SUM(actual) actual FROM production GROUP BY date", get_connection())
    weekly["date"] = pd.to_datetime(weekly["date"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["plan"], name="Plan"))
    fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["actual"], name="Actual"))
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# USER MANAGEMENT
# =====================================================

if menu == "User Management":

    st.title("USER MANAGEMENT")

    conn = get_connection()
    users_df = pd.read_sql("SELECT username,role,plant FROM users", conn)
    conn.close()

    st.dataframe(users_df)

    st.subheader("Create User")

    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Supervisor","Admin"])
    plant_map = st.selectbox("Plant", PLANTS)

    if st.button("Create User"):
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users VALUES (?,?,?,?)",
                      (new_user,new_pass,role,plant_map))
            conn.commit()
            st.success("User Created")
        except:
            st.error("User already exists")
        conn.close()
