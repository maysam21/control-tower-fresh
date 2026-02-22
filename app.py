import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# =====================================================
# DATABASE
# =====================================================

def get_connection():
    return sqlite3.connect("control_tower.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
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
        sku TEXT,
        plan INTEGER,
        actual INTEGER,
        rejection INTEGER
    )
    """)

    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?)",
                  ("admin","admin123","Admin","All"))

    conn.commit()
    conn.close()

init_db()

# =====================================================
# INDUSTRIAL CSS
# =====================================================

st.markdown("""
<style>

.stApp {
    background-color: #f3f4f6;
}

.topbar {
    background-color: #0f172a;
    padding: 15px;
    color: white;
    font-size: 20px;
    font-weight: 600;
}

.plant-card {
    background-color: white;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 20px;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.15);
}

.oee-green {background-color:#16a34a;color:white;padding:15px;border-radius:6px;text-align:center;font-size:24px;font-weight:700;}
.oee-yellow {background-color:#facc15;color:black;padding:15px;border-radius:6px;text-align:center;font-size:24px;font-weight:700;}
.oee-red {background-color:#dc2626;color:white;padding:15px;border-radius:6px;text-align:center;font-size:24px;font-weight:700;}

.small-box {
    background-color:#e5e7eb;
    padding:10px;
    border-radius:6px;
    text-align:center;
    font-weight:600;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# LOGIN
# =====================================================

if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.markdown("<div class='topbar'>Manufacturing Control Tower</div>", unsafe_allow_html=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

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

    st.markdown("<div class='topbar'>Shift Entry</div>", unsafe_allow_html=True)

    if st.session_state.user["role"] == "Supervisor":
        plant = st.session_state.user["plant"]
        st.info(f"Plant Assigned: {plant}")
    else:
        plant = st.selectbox("Plant", PLANTS)

    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", CATEGORIES)
    sku = st.text_input("SKU")

    col1,col2,col3 = st.columns(3)
    plan = col1.number_input("Plan", 0)
    actual = col2.number_input("Actual", 0)
    rejection = col3.number_input("Rejection", 0)

    if st.button("Save Entry"):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
        INSERT INTO production(date,plant,category,sku,plan,actual,rejection)
        VALUES (?,?,?,?,?,?,?)
        """,(str(date),plant,category,sku,plan,actual,rejection))
        conn.commit()
        conn.close()
        st.success("Saved Successfully")

# =====================================================
# INDUSTRIAL DASHBOARD
# =====================================================

if menu == "Dashboard":

    st.markdown("<div class='topbar'>Cell Status</div>", unsafe_allow_html=True)

    conn = get_connection()
    df = pd.read_sql("SELECT * FROM production", conn)
    conn.close()

    if df.empty:
        st.warning("No Data Available")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])
    selected_date = st.date_input("Date Range: Today", datetime.today())
    df = df[df["date"].dt.date == selected_date]

    plants = df["plant"].unique()
    cols = st.columns(3)

    for i, plant in enumerate(plants):
        plant_df = df[df["plant"] == plant]

        total_plan = plant_df["plan"].sum()
        total_actual = plant_df["actual"].sum()
        total_rej = plant_df["rejection"].sum()

        availability = (total_actual/total_plan)*100 if total_plan>0 else 0
        quality = ((total_actual-total_rej)/total_actual)*100 if total_actual>0 else 0
        performance = (total_actual/total_plan)*100 if total_plan>0 else 0
        oee = (availability/100)*(quality/100)*(performance/100)*100

        col = cols[i % 3]

        with col:
            st.markdown("<div class='plant-card'>", unsafe_allow_html=True)
            st.subheader(plant)

            if oee >= 85:
                css = "oee-green"
            elif oee >= 70:
                css = "oee-yellow"
            else:
                css = "oee-red"

            st.markdown(f"<div class='{css}'>{round(oee,1)}% OEE</div>", unsafe_allow_html=True)

            c1,c2 = st.columns(2)
            c1.markdown(f"<div class='small-box'>Target<br>{total_plan}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='small-box'>Actual<br>{total_actual}</div>", unsafe_allow_html=True)

            c3,c4,c5 = st.columns(3)
            c3.markdown(f"<div class='small-box'>Perf<br>{round(performance,1)}%</div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='small-box'>Qual<br>{round(quality,1)}%</div>", unsafe_allow_html=True)
            c5.markdown(f"<div class='small-box'>Avail<br>{round(availability,1)}%</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("Downtime / Rejection Trend")

    trend = df.groupby("date").sum(numeric_only=True).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend["date"], y=trend["rejection"], name="Rejection"))
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

