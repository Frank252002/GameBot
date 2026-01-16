import streamlit as st
import pandas as pd
import joblib
import time
from datetime import datetime
import os
import platform
from plyer import notification

# --- CLOUD COMPATIBILITY SETUP ---
# Streamlit Cloud runs on Linux, which does not have 'winsound'.
# We use this check to prevent the app from crashing online.
if platform.system() == "Windows":
    import winsound
    sound_available = True
else:
    winsound = None
    sound_available = False

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="NEXUS AI | Gaming Guardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS STYLING (Tactical Theme) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Roboto+Mono:wght@400;500&display=swap');
    
    @keyframes scrollGrid {
        0% { background-position: 0 0; }
        100% { background-position: 40px 40px; }
    }

    .stApp {
        background-color: #0a0a0a;
        background-image: 
            linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
        background-size: 40px 40px;
        animation: scrollGrid 4s linear infinite;
        font-family: 'Rajdhani', sans-serif;
        color: #e0e0e0;
    }

    h1, h2, h3 {
        font-family: 'Rajdhani', sans-serif !important;
        text-transform: uppercase;
        color: #ffffff !important;
        border-bottom: 1px solid #444;
    }

    /* Inputs & Buttons */
    .stTextInput input, .stNumberInput input {
        background-color: #111 !important;
        color: #fff !important;
        border: 1px solid #444 !important;
        font-family: 'Roboto Mono', monospace;
    }
    .stButton > button {
        width: 100%;
        background-color: #222;
        color: white;
        border: 1px solid #555;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #fff;
        color: #000;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. BACKEND FUNCTIONS (DATABASE) ---
USERS_FILE = 'users.csv'
HISTORY_FILE = 'history.csv'

def init_db():
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=['username', 'password']).to_csv(USERS_FILE, index=False)
    if not os.path.exists(HISTORY_FILE):
        pd.DataFrame(columns=['username', 'date', 'result', 'probability']).to_csv(HISTORY_FILE, index=False)

def register_user(username, password):
    df = pd.read_csv(USERS_FILE)
    # Basic check to avoid duplicates
    if username in df['username'].values:
        return False
    new_user = pd.DataFrame([[username, password]], columns=['username', 'password'])
    new_user.to_csv(USERS_FILE, mode='a', header=False, index=False)
    return True

def login_user(username, password):
    df = pd.read_csv(USERS_FILE)
    user_match = df[(df['username'] == username) & (df['password'] == password)]
    return not user_match.empty

def save_history(username, result, prob):
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_row = pd.DataFrame([[username, date, result, prob]], columns=['username', 'date', 'result', 'probability'])
    new_row.to_csv(HISTORY_FILE, mode='a', header=False, index=False)

def get_history(username):
    df = pd.read_csv(HISTORY_FILE)
    return df[df['username'] == username]

# Initialize DB files
init_db()

# --- 4. SESSION STATE MANAGEMENT ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

# --- 5. AUTHENTICATION SCREENS ---
if not st.session_state.logged_in:
    st.title("🔒 NEXUS SECURITY GATEWAY")
    st.info("System Ready. Please Login or Register.")
    
    tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
    
    with tab1:
        st.write("### > ACCESS TERMINAL")
        username_login = st.text_input("Username", key="login_user")
        password_login = st.text_input("Password", type="password", key="login_pass")
        if st.button("AUTHENTICATE"):
            if login_user(username_login, password_login):
                st.session_state.logged_in = True
                st.session_state.username = username_login
                st.success("ACCESS GRANTED.")
                st.rerun()
            else:
                st.error("ACCESS DENIED. Invalid Credentials.")

    with tab2:
        st.write("### > CREATE NEW ID")
        new_user = st.text_input("New Username", key="reg_user")
        new_pass = st.text_input("New Password", type="password", key="reg_pass")
        if st.button("REGISTER ID"):
            if new_user and new_pass:
                if register_user(new_user, new_pass):
                    st.success("REGISTRATION SUCCESSFUL. PLEASE LOGIN.")
                else:
                    st.error("ERROR: Username already exists.")
            else:
                st.warning("Please enter both username and password.")

# --- 6. MAIN APP (ONLY VISIBLE IF LOGGED IN) ---
else:
    # --- LOAD BRAIN ---
    try:
        model = joblib.load('gaming_model_full.pkl')
        encoders = joblib.load('encoders.pkl')
        model_loaded = True
    except:
        model_loaded = False

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("NEXUS SYSTEM")
        st.write(f"👤 **USER:** {st.session_state.username.upper()}")
        st.write(f"🕒 **TIME:** {datetime.now().strftime('%H:%M')}")
        st.markdown("---")
        mode = st.radio("SELECT MODULE:", ["🖥️ SESSION MONITOR", "🧠 NEURAL DIAGNOSTICS", "📂 HISTORY LOGS"])
        st.markdown("---")
        if st.button("LOGOUT"):
            st.session_state.logged_in = False
            st.rerun()

    # ====================================================
    # MODULE 1: SESSION MONITOR
    # ====================================================
    if mode == "🖥️ SESSION MONITOR":
        col1, col2 = st.columns([2, 1])
        with col1:
            st.title("ACTIVE MONITOR")
            if "tracking" not in st.session_state:
                st.session_state.tracking = False
                st.session_state.start_time = None
            clock_placeholder = st.empty()
            if not st.session_state.tracking:
                 clock_placeholder.markdown("<h1 style='font-size: 80px; color: #444; font-family: Roboto Mono;'>00:00:00</h1>", unsafe_allow_html=True)
        with col2:
            st.markdown("### CONFIGURATION")
            limit_hours = st.number_input("SESSION LIMIT (HOURS):", value=4.0, step=0.5)
            limit_seconds = limit_hours * 3600
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("▶ INITIATE"):
                st.session_state.tracking = True
                st.session_state.start_time = datetime.now()
            if st.button("⏹ TERMINATE"):
                st.session_state.tracking = False
                st.success("Session Logged.")

        if st.session_state.tracking:
            while st.session_state.tracking:
                now = datetime.now()
                elapsed = now - st.session_state.start_time
                elapsed_seconds = elapsed.total_seconds()
                clock_placeholder.markdown(f"<h1 style='font-size: 100px; color: #fff; font-family: Roboto Mono;'>{str(elapsed).split('.')[0]}</h1>", unsafe_allow_html=True)
                
                if elapsed_seconds > limit_seconds:
                    # Windows Notification
                    try:
                        notification.notify(title='🛑 SYSTEM ALERT', message=f'Limit Reached ({limit_hours} hrs).', app_name='NEXUS', timeout=10)
                    except: 
                        pass
                    
                    # Sound Alarm (Only on Windows/Local)
                    if sound_available:
                        winsound.Beep(1000, 1000)
                    
                    st.error("⚠️ TIME LIMIT REACHED. PLEASE BREAK.")
                    st.session_state.tracking = False
                    break
                time.sleep(1)

    # ====================================================
    # MODULE 2: NEURAL DIAGNOSTICS
    # ====================================================
    elif mode == "🧠 NEURAL DIAGNOSTICS":
        st.title("DIAGNOSTICS ENGINE")
        if not model_loaded: st.error("Error: Model file missing.")
        
        chat_container = st.container()
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "System online. Type 'start' to begin analysis."}]
        if "step" not in st.session_state: st.session_state.step = 0
        if "data" not in st.session_state: st.session_state.data = {}

        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if prompt := st.chat_input("Enter data stream..."):
            with st.chat_message("user"): st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            response = "Processing..."
            
            # --- CHAT FLOW ---
            if st.session_state.step == 0:
                if "start" in prompt.lower():
                    response = "Initializing scan. **Enter Subject Age:**"
                    st.session_state.step = 1
                else: response = "Command unknown. Type 'start'."
            elif st.session_state.step == 1:
                try:
                    st.session_state.data['What is your age?'] = int(prompt)
                    response = "**Select Gender:** (Male/Female/Other)"
                    st.session_state.step = 2
                except: response = "Error: Numeric input required."
            elif st.session_state.step == 2:
                st.session_state.data['What is your gender?'] = prompt
                response = "**Average Daily Session (Hours):**"
                st.session_state.step = 3
            elif st.session_state.step == 3:
                try:
                    hours = float(prompt)
                    st.session_state.data['How many hours do you play video games per day on average?'] = hours
                    response = "**Weekly Frequency (Days):**"
                    st.session_state.step = 4
                except: response = "Error: Numeric input required."
            elif st.session_state.step == 4:
                st.session_state.data['How many days per week do you play games?'] = float(prompt)
                response = "**Primary Genre:** (FPS, RPG, etc.)"
                st.session_state.step = 5
            elif st.session_state.step == 5:
                st.session_state.data['What type of games do you mostly play?'] = prompt
                response = "**Stress Index (1-10):**"
                st.session_state.step = 6
            elif st.session_state.step == 6:
                st.session_state.data['On a scale of 1 to 10, how stressed do you feel on average?'] = int(prompt)
                response = "**Anxiety Index (1-10):**"
                st.session_state.step = 7
            elif st.session_state.step == 7:
                st.session_state.data['On a scale of 1 to 10, how anxious do you feel regularly?'] = int(prompt)
                response = "**Average Sleep (Hours):**"
                st.session_state.step = 8
            elif st.session_state.step == 8:
                st.session_state.data['On average, how many hours of sleep do you get per night?'] = float(prompt)
                response = "**Social Isolation Frequency:** (Often/Sometimes/Never)"
                st.session_state.step = 9
            elif st.session_state.step == 9:
                st.session_state.data['How often do you feel socially withdrawn or isolated?'] = prompt
                response = "**Gaming as Coping Mechanism?** (Yes/No)"
                st.session_state.step = 10
            elif st.session_state.step == 10:
                st.session_state.data['Do you think gaming helps you cope with stress or emotional issues?'] = prompt
                
                if model_loaded:
                    def encode_input(col_name, user_input):
                        encoder = encoders[col_name]
                        if user_input in encoder.classes_: return encoder.transform([user_input])[0]
                        else: return encoder.transform([encoder.classes_[0]])[0]

                    input_row = [
                        st.session_state.data['What is your age?'],
                        encode_input('What is your gender?', st.session_state.data['What is your gender?']),
                        st.session_state.data['How many hours do you play video games per day on average?'],
                        st.session_state.data['How many days per week do you play games?'],
                        encode_input('What type of games do you mostly play?', st.session_state.data['What type of games do you mostly play?']),
                        st.session_state.data['On a scale of 1 to 10, how stressed do you feel on average?'],
                        st.session_state.data['On a scale of 1 to 10, how anxious do you feel regularly?'],
                        st.session_state.data['On average, how many hours of sleep do you get per night?'],
                        encode_input('How often do you feel socially withdrawn or isolated?', st.session_state.data['How often do you feel socially withdrawn or isolated?']),
                        encode_input('Do you think gaming helps you cope with stress or emotional issues?', st.session_state.data['Do you think gaming helps you cope with stress or emotional issues?'])
                    ]
                    prediction = model.predict([input_row])[0]
                    probs = model.predict_proba([input_row])[0]
                    
                    if prediction == 1:
                        result_text = "HIGH RISK"
                        result_prob = f"{probs[1]:.0%}"
                        result_msg = f"🔴 **HIGH RISK** ({result_prob})"
                        details = "Analysis: Patterns match at-risk cohort."
                    else:
                        result_text = "OPTIMAL"
                        result_prob = f"{probs[0]:.0%}"
                        result_msg = f"🟢 **OPTIMAL** ({result_prob})"
                        details = "Analysis: Patterns within healthy parameters."

                    # SAVE TO HISTORY
                    save_history(st.session_state.username, result_text, result_prob)
                    
                    response = f"**Diagnostic Complete:** {result_msg}\n\n{details}\n\n*Result saved to user history.*"
                    st.session_state.step = 11

            elif st.session_state.step == 11:
                response = "Session closed. Type 'start' to begin new scan."
                if 'start' in prompt.lower():
                    st.session_state.step = 1
                    response = "Restarting scan... **Enter Subject Age:**"

            time.sleep(0.5)
            with st.chat_message("assistant"): st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    # ====================================================
    # MODULE 3: HISTORY LOGS
    # ====================================================
    elif mode == "📂 HISTORY LOGS":
        st.title("USER DATA ARCHIVES")
        
        user_history = get_history(st.session_state.username)
        
        if user_history.empty:
            st.info("No logs found for this user.")
        else:
            # Display metrics
            total_scans = len(user_history)
            risk_count = len(user_history[user_history['result'] == 'HIGH RISK'])
            
            m1, m2 = st.columns(2)
            m1.metric("Total Assessments", total_scans)
            m2.metric("High Risk Alerts", risk_count, delta_color="inverse")
            
            st.markdown("### > DIAGNOSTIC LOGS")
            st.dataframe(
                user_history[['date', 'result', 'probability']], 
                use_container_width=True,
                hide_index=True
            )