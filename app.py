import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

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

    # Default admin
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
    st.title("Manufacturing Control Tower")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = get_conn()
        c = conn.cursor()
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and user[2] == hash_password(password):
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid Credentials")

if st.session_state.user is None:
    login()
    st.stop()

# ---------------- MENU ----------------

PLANTS = ["JD","Snoair","APT","SP","Inhouse"]
CATEGORIES = ["Chimney","Burner"]

st.sidebar.write("Logged in:", st.session_state.user[1])
menu = st.sidebar.selectbox("Menu", ["Dashboard","Entry","User Management"])

# ---------------- ENTRY ----------------

if menu == "Entry":
    st.title("Shift Entry")

    plant = st.session_state.user[4]
    if st.session_state.user[3] == "Admin":
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
        st.success("Saved")

# ---------------- DASHBOARD ----------------

if menu == "Dashboard":
    st.title("Dashboard")

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM production", conn)
    conn.close()

    if df.empty:
        st.warning("No data available")
    else:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        selected_date = st.date_input("Select Date", datetime.today())
        df = df[df["date"] == selected_date]

        total_plan = df["plan"].sum()
        total_actual = df["actual"].sum()

        achievement = round((total_actual / total_plan) * 100, 2) if total_plan > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Plan", total_plan)
        col2.metric("Total Actual", total_actual)
        col3.metric("Achievement %", achievement)

# ---------------- USER MANAGEMENT ----------------

if menu == "User Management" and st.session_state.user[3] == "Admin":
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