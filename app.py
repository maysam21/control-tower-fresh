import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# ---------------- SESSION INIT ----------------

if "users" not in st.session_state:
    st.session_state.users = {
        "admin": {
            "password": "admin123",
            "role": "Admin",
            "plant": "All"
        }
    }

if "user" not in st.session_state:
    st.session_state.user = None

if "production" not in st.session_state:
    st.session_state.production = pd.DataFrame(
        columns=["date","plant","category","plan","actual"]
    )

PLANTS = ["JD","Snoair","APT","SP","Inhouse"]
CATEGORIES = ["Chimney","Burner"]

# =========================================================
# LOGIN
# =========================================================

def login():
    st.title("MANUFACTURING CONTROL TOWER")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users = st.session_state.users

        if username in users and users[username]["password"] == password:
            st.session_state.user = {
                "username": username,
                "role": users[username]["role"],
                "plant": users[username]["plant"]
            }
        else:
            st.error("Invalid Credentials")

if st.session_state.user is None:
    login()
    st.stop()

user = st.session_state.user

# =========================================================
# ROLE BASED MENU
# =========================================================

if user["role"] == "Admin":
    menu = st.sidebar.selectbox("Menu", ["Dashboard","Shift Entry","User Management"])
else:
    menu = "Shift Entry"

st.sidebar.write("Logged in:", user["username"])
st.sidebar.write("Role:", user["role"])
st.sidebar.write("Plant:", user["plant"])

# =========================================================
# USER MANAGEMENT (ADMIN ONLY)
# =========================================================

if menu == "User Management" and user["role"] == "Admin":

    st.title("USER MANAGEMENT")

    st.subheader("Create New User")

    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    new_role = st.selectbox("Role", ["Supervisor"])
    mapped_plant = st.selectbox("Map to Plant", PLANTS)

    if st.button("Create User"):

        if new_username in st.session_state.users:
            st.error("User already exists")
        else:
            st.session_state.users[new_username] = {
                "password": new_password,
                "role": new_role,
                "plant": mapped_plant
            }
            st.success("User Created Successfully")

    st.markdown("---")

    st.subheader("Existing Users")

    users_df = pd.DataFrame.from_dict(
        st.session_state.users, orient="index"
    ).reset_index().rename(columns={"index": "Username"})

    st.dataframe(users_df, use_container_width=True)

# =========================================================
# SHIFT ENTRY
# =========================================================

if menu == "Shift Entry":

    st.title("SHIFT ENTRY")

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
# DASHBOARD (ADMIN ONLY)
# =========================================================

if menu == "Dashboard" and user["role"] == "Admin":

    st.title("MANUFACTURING CONTROL TOWER DASHBOARD")

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

    col1,col2,col3 = st.columns(3)
    col1.metric("Total Plan", int(total_plan))
    col2.metric("Total Actual", int(total_actual))
    col3.metric("Achievement %", achievement)

    plant_df = df.groupby("plant").sum(numeric_only=True).reset_index()

    if not plant_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=plant_df["plant"],
            y=plant_df["actual"],
            name="Actual"
        ))
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
