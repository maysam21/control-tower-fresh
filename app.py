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
    st.session_state.clear()

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

    if st.button("Save Entry", use_container_width=True):
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

    st.markdown("## 🏢 EXECUTIVE CONTROL TOWER")

    conn = get_connection()
    df = pd.read_sql("SELECT * FROM production", conn)
    conn.close()

    if df.empty:
        st.warning("No production data available")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])

    selected_date = st.date_input("Select Date", datetime.today())

    # ---------------- TODAY DATA ----------------
    today_df = df[df["date"].dt.date == selected_date]

    # ---------------- MTD DATA ----------------
    mtd_df = df[
        (df["date"].dt.month == selected_date.month) &
        (df["date"].dt.year == selected_date.year)
    ]

    # ---------------- KPI SECTION ----------------

    total_today_plan = today_df["plan"].sum()
    total_today_actual = today_df["actual"].sum()
    total_mtd_plan = mtd_df["plan"].sum()
    total_mtd_actual = mtd_df["actual"].sum()

    ach_today = round((total_today_actual/total_today_plan)*100,2) if total_today_plan>0 else 0
    ach_mtd = round((total_mtd_actual/total_mtd_plan)*100,2) if total_mtd_plan>0 else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Today Plan", total_today_plan)
    c2.metric("Today Actual", total_today_actual)
    c3.metric("Today Achievement %", ach_today)
    c4.metric("MTD Achievement %", ach_mtd)

    st.markdown("---")

    # ---------------- PLANT RANKING ----------------

    st.subheader("📊 Plant Performance Ranking")

    plant_df = today_df.groupby("plant").sum(numeric_only=True).reset_index()
    plant_df["Achievement %"] = (
        (plant_df["actual"]/plant_df["plan"])*100
    ).round(1)

    plant_df = plant_df.sort_values("Achievement %", ascending=False)

    def highlight(row):
        if row["Achievement %"] >= 95:
            return ["background-color: #14532d"] * len(row)
        elif row["Achievement %"] >= 90:
            return ["background-color: #78350f"] * len(row)
        else:
            return ["background-color: #7f1d1d"] * len(row)

    st.dataframe(
        plant_df.style.apply(highlight, axis=1),
        use_container_width=True
    )

    st.markdown("---")

    # ---------------- CATEGORY PERFORMANCE ----------------

    st.subheader("🏭 Category Performance")

    cat_df = today_df.groupby("category").sum(numeric_only=True).reset_index()
    cat_df["Achievement %"] = (
        (cat_df["actual"]/cat_df["plan"])*100
    ).round(1)

    col1,col2 = st.columns(2)

    with col1:
        st.dataframe(cat_df, use_container_width=True)

    with col2:
        fig_cat = go.Figure()
        fig_cat.add_trace(go.Bar(
            x=cat_df["category"],
            y=cat_df["Achievement %"]
        ))
        fig_cat.update_layout(template="plotly_dark", height=350)
        st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("---")

    # ---------------- WEEKLY TREND ----------------

    st.subheader("📈 Weekly Production Trend")

    weekly = df.groupby("date").sum(numeric_only=True).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly["date"],
        y=weekly["actual"],
        mode="lines+markers",
        name="Actual"
    ))
    fig.update_layout(template="plotly_dark", height=450)

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ---------------- EXPORT REPORT ----------------

    st.subheader("📤 Export Report")

    export_df = today_df.copy()

    csv = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Today's Report (CSV)",
        data=csv,
        file_name="today_production_report.csv",
        mime="text/csv"
    )
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


