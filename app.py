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

    # USERS
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        plant TEXT
    )
    """)

    # PRODUCTION
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

    # SKU MASTER
    c.execute("""
    CREATE TABLE IF NOT EXISTS sku_master(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plant TEXT,
        sku TEXT
    )
    """)

    # DEFAULT ADMIN
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?)",
                  ("admin","admin123","Admin","All"))

    conn.commit()
    conn.close()

init_db()

# =====================================================
# DARK EXECUTIVE THEME
# =====================================================

st.markdown("""
<style>
.stApp { background-color: #0f172a; }

.title {
    font-size: 36px;
    font-weight: 700;
    color: white;
    margin-bottom: 20px;
}

.kpi-card {
    background: #1e293b;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    color: white;
}

.kpi-value {
    font-size: 28px;
    font-weight: 700;
}

.section {
    background: #1e293b;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 20px;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# LOGIN
# =====================================================

if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.markdown("<div class='title'>Manufacturing Control Tower</div>", unsafe_allow_html=True)

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
            st.rerun()
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
    menu = st.sidebar.selectbox("Menu",
                                ["Executive Dashboard","Shift Entry","User Management"])
else:
    menu = "Shift Entry"

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# =====================================================
# SHIFT ENTRY
# =====================================================

if menu == "Shift Entry":

    st.markdown("<div class='title'>Shift Entry</div>", unsafe_allow_html=True)

    if st.session_state.user["role"] == "Supervisor":
        plant = st.session_state.user["plant"]
        st.info(f"Plant Assigned: {plant}")
    else:
        plant = st.selectbox("Plant", PLANTS)

    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", CATEGORIES)

    # SKU filtered by plant
    conn = get_connection()
    sku_df = pd.read_sql("SELECT sku FROM sku_master WHERE plant=?",
                         conn, params=(plant,))
    conn.close()

    if not sku_df.empty:
        sku = st.selectbox("SKU", sku_df["sku"])
    else:
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
# EXECUTIVE DASHBOARD
# =====================================================

if menu == "Executive Dashboard":

    st.markdown("<div class='title'>Executive Control Tower</div>", unsafe_allow_html=True)

    conn = get_connection()
    df = pd.read_sql("SELECT * FROM production", conn)
    conn.close()

    if df.empty:
        st.warning("No Production Data")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])
    selected_date = st.date_input("Select Date", datetime.today())
    df = df[df["date"].dt.date == selected_date]

    # KPI STRIP
    total_plan = df["plan"].sum()
    total_actual = df["actual"].sum()
    total_rej = df["rejection"].sum()

    achievement = round((total_actual/total_plan)*100,2) if total_plan>0 else 0
    rejection_rate = round((total_rej/total_actual)*100,2) if total_actual>0 else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-card'><div class='kpi-value'>{total_plan}</div>Plan</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card'><div class='kpi-value'>{total_actual}</div>Actual</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card'><div class='kpi-value'>{achievement}%</div>Achievement</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-card'><div class='kpi-value'>{rejection_rate}%</div>Rejection</div>", unsafe_allow_html=True)

    st.markdown("<br>")

    # PLANT COMPARISON
    st.markdown("### Plant Comparison")

    plant_df = df.groupby("plant").sum(numeric_only=True).reset_index()
    plant_df["Achievement %"] = (plant_df["actual"]/plant_df["plan"]*100).round(1)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=plant_df["plant"],
                         y=plant_df["Achievement %"],
                         name="Achievement %"))
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # SKU PERFORMANCE
    st.markdown("### SKU Performance")

    sku_df = df.groupby("sku").sum(numeric_only=True).reset_index()
    sku_df["Achievement %"] = (sku_df["actual"]/sku_df["plan"]*100).round(1)

    st.dataframe(sku_df.sort_values("actual", ascending=False),
                 use_container_width=True)

    # REJECTION ANALYSIS
    st.markdown("### Rejection by SKU")

    rej_df = df.groupby("sku")["rejection"].sum().reset_index()

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=rej_df["sku"],
                          y=rej_df["rejection"]))
    fig2.update_layout(template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

# =====================================================
# USER MANAGEMENT
# =====================================================

if menu == "User Management":

    st.markdown("<div class='title'>User & SKU Management</div>", unsafe_allow_html=True)

    conn = get_connection()
    users_df = pd.read_sql("SELECT username,role,plant FROM users", conn)
    conn.close()

    st.dataframe(users_df, use_container_width=True)

    st.markdown("---")
    st.subheader("Create User")

    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Supervisor","Admin"])
    plant = st.selectbox("Plant Mapping", PLANTS)

    if st.button("Create User"):
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users VALUES (?,?,?,?)",
                      (new_user,new_pass,role,plant))
            conn.commit()
            st.success("User Created")
        except:
            st.error("User already exists")
        conn.close()

    st.markdown("---")
    st.subheader("SKU Mapping")

    plant_sel = st.selectbox("Plant", PLANTS, key="skuplant")
    new_sku = st.text_input("New SKU")

    if st.button("Add SKU"):
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO sku_master(plant,sku) VALUES (?,?)",
                  (plant_sel,new_sku))
        conn.commit()
        conn.close()
        st.success("SKU Added")
