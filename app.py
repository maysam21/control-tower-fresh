import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# ================================
# SESSION INITIALIZATION
# ================================

if "users" not in st.session_state:
    st.session_state.users = {
        "admin": {
            "password": "admin123",
            "role": "Admin",
            "plant": "All"
        }
    }

if "production" not in st.session_state:
    st.session_state.production = pd.DataFrame(
        columns=["date","plant","category","plan","actual"]
    )

if "user" not in st.session_state:
    st.session_state.user = None


PLANTS = ["JD","Snoair","APT","SP","Inhouse"]
CATEGORIES = ["Chimney","Burner"]

# ================================
# GLOBAL STYLING
# ================================

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
.panel {
    background: #132235;
    padding: 20px;
    border-radius: 14px;
    color: white;
}

button {
    border-radius: 8px !important;
}

</style>
""", unsafe_allow_html=True)

# ================================
# LOGIN SYSTEM (STABLE VERSION)
# ================================

def login():

    st.markdown("<div class='main-title'>MANUFACTURING CONTROL TOWER</div>", unsafe_allow_html=True)

    username = st.text_input("Username", key="login_user").strip()
    password = st.text_input("Password", type="password", key="login_pass").strip()

    if st.button("Login", key="login_btn"):

        users = st.session_state.users

        if username in users and users[username]["password"] == password:

            st.session_state.user = {
                "username": username,
                "role": users[username]["role"],
                "plant": users[username]["plant"]
            }

        else:
            st.error("Invalid Credentials")


# Show login only if not logged in
if st.session_state.user is None:
    login()
    st.stop()

# ================================
# SIDEBAR MENU
# ================================

st.sidebar.markdown("### Logged in as")
st.sidebar.success(st.session_state.user["username"])

if st.session_state.user["role"] == "Admin":
    menu = st.sidebar.selectbox("Menu", ["Dashboard","Shift Entry","User Management"])
else:
    menu = "Shift Entry"

if st.sidebar.button("Logout"):
    st.session_state.user = None
# =========================================================
# SHIFT ENTRY (Supervisor Only)
# =========================================================

if menu == "Shift Entry":

    st.markdown("<div class='main-title'>SHIFT ENTRY</div>", unsafe_allow_html=True)

    if st.session_state.user["role"] == "Admin":
        plant = st.selectbox("Plant", PLANTS)
    else:
        plant = st.session_state.user["plant"]
        st.info(f"Plant Assigned: {plant}")

    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", CATEGORIES)

    col1,col2 = st.columns(2)
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
# DASHBOARD
# =========================================================

if menu == "Dashboard":

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

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-box blue'>{total_plan}<br>Total Plan</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-box blue'>{total_actual}<br>Total Actual</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-box green'>{achievement}%<br>Achievement</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-box amber'>{rejection}%<br>Rejection</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    weekly = st.session_state.production.copy()
    weekly["date"] = pd.to_datetime(weekly["date"])
    weekly = weekly.groupby("date").sum(numeric_only=True).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["plan"], mode='lines+markers', name='Plan'))
    fig.add_trace(go.Scatter(x=weekly["date"], y=weekly["actual"], mode='lines+markers', name='Actual'))
    fig.update_layout(template="plotly_dark", height=450)

    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# USER MANAGEMENT (ADMIN ONLY)
# =========================================================

if menu == "User Management":

    st.markdown("<div class='main-title'>USER MANAGEMENT</div>", unsafe_allow_html=True)

    users_df = pd.DataFrame([
        {
            "Username": u,
            "Role": st.session_state.users[u]["role"],
            "Plant": st.session_state.users[u]["plant"]
        }
        for u in st.session_state.users
    ])

    st.dataframe(users_df)

    st.markdown("---")

    st.subheader("Add / Modify User")

    selected_user = st.selectbox("Select User", list(st.session_state.users.keys()))
    new_password = st.text_input("New Password", type="password")
    new_role = st.selectbox("Role", ["Admin","Supervisor"])
    new_plant = st.selectbox("Plant", PLANTS + ["All"])

    col1,col2 = st.columns(2)

    if col1.button("Update User"):
       if new_password:
           st.session_state.users[selected_user]["password"] = new_password
       st.session_state.users[selected_user]["role"] = new_role
       st.session_state.users[selected_user]["plant"] = new_plant
       st.success("User Updated")

    if col2.button("Delete User"):
        if selected_user != "admin":
            del st.session_state.users[selected_user]
            st.success("User Deleted")
        else:
            st.error("Cannot delete Admin user")

    st.markdown("---")

    st.subheader("Create New User")

    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    role = st.selectbox("Role ", ["Supervisor","Admin"])
    plant_map = st.selectbox("Plant Mapping", PLANTS)

    if st.button("Create User"):
        if new_user in st.session_state.users:
            st.error("User already exists")
        elif not new_pass:
            st.error("Password required")
        else:
            st.session_state.users[new_user] = {
                "password": new_pass,
                "role": role,
                "plant": plant_map
            }
            st.success("User Created Successfully")


