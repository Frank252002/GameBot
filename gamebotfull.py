import streamlit as st
import pandas as pd
import joblib
import time
from datetime import datetime
import os
import platform
import gspread
from plyer import notification

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="GameBot | Gaming Guardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. TACTICAL CSS STYLING (The Cool Stuff) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Roboto+Mono:wght@400;500&display=swap');
    
    /* Moving Grid Animation */
    @keyframes scrollGrid {
        0% { background-position: 0 0; }
        100% { background-position: 40px 40px; }
    }

    /* Main Background */
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

    /* Headers */
    h1, h2, h3 {
        font-family: 'Rajdhani', sans-serif !important;
        text-transform: uppercase;
        color: #ffffff !important;
        border-bottom: 1px solid #444;
        padding-bottom: 10px;
    }

    /* Input Fields */
    .stTextInput input, .stNumberInput input {
        background-color: #111 !important;
        color: #fff !important;
        border: 1px solid #444 !important;
        font-family: 'Roboto Mono', monospace;
    }

    /* Buttons */
    .stButton > button {
        width: 100%;
        background-color: #222;
        color: white;
        border: 1px solid #555;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        text-transform: uppercase;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #fff;
        color: #000;
        box-shadow: 0 0 10px #fff;
    }

    /* Chat Bubbles */
    .stChatMessage {
        background-color: rgba(20, 20, 20, 0.8);
        border: 1px solid #333;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def get_db_connection():
    try:
        # Priority 1: Check for the local file "service_key.json"
        if os.path.exists("service_key.json"):
            client = gspread.service_account(filename="service_key.json")
            sheet = client.open("Nexus_DB")
            return sheet
            
        # Priority 2: Check for Cloud Secrets (If you deploy later)
        elif "gcp_service_account" in st.secrets:
            creds = dict(st.secrets["gcp_service_account"])
            client = gspread.service_account_from_dict(creds)
            sheet = client.open("Nexus_DB")
            return sheet
            
        else:
            return None
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def register_user(username, password):
    try:
        sh = get_db_connection()
        if not sh: return False
        
        worksheet = sh.worksheet("users")
        users = worksheet.get_all_records()
        df = pd.DataFrame(users)
        
        # Check if user exists
        if not df.empty and 'username' in df.columns and username in df['username'].values:
            return False
        
        worksheet.append_row([username, password])
        return True
    except:
        return False

def login_user(username, password):
    try:
        sh = get_db_connection()
        if not sh: return False
        
        worksheet = sh.worksheet("users")
        users = worksheet.get_all_records()
        df = pd.DataFrame(users)
        
        if df.empty: return False
        
        # Verify credentials
        user_match = df[(df['username'].astype(str) == username) & (df['password'].astype(str) == password)]
        return not user_match.empty
    except:
        return False

def save_history(username, result, prob):
    try:
        sh = get_db_connection()
        if not sh: return
        
        worksheet = sh.worksheet("history")
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        worksheet.append_row([username, date, result, prob])
    except:
        pass

def get_history(username):
    try:
        sh = get_db_connection()
        if not sh: return pd.DataFrame()
        
        worksheet = sh.worksheet("history")
        data = worksheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 4. WEB ALARM SOUND ---
def play_alarm_sound():
    sound_url = "https://www.soundjay.com/buttons/beep-01a.mp3"
    st.markdown(f'<audio autoplay="true"><source src="{sound_url}" type="audio/mp3"></audio>', unsafe_allow_html=True)

# --- 5. APP LOGIC ---

# Login State
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""

# LOGIN SCREEN
if not st.session_state.logged_in:
    st.title("🔒 NEXUS CLOUD GATEWAY")
    
    # Status Check
    if os.path.exists("service_key.json"):
        st.success("✅ SYSTEM ONLINE: Database Connected")
    else:
        st.warning("⚠️ SYSTEM OFFLINE: Key File Missing")

    tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
    
    with tab1:
        u = st.text_input("Username", key="l_u")
        p = st.text_input("Password", type="password", key="l_p")
        if st.button("AUTHENTICATE"):
            with st.spinner("Verifying Credentials..."):
                if login_user(u, p):
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.rerun()
                else: st.error("Access Denied.")

    with tab2:
        nu = st.text_input("New Username", key="r_u")
        np = st.text_input("New Password", type="password", key="r_p")
        if st.button("REGISTER ID"):
            with st.spinner("Creating Secure Record..."):
                if register_user(nu, np): st.success("Registration Complete. Please Login.")
                else: st.error("Username taken or System Error.")

# MAIN INTERFACE
else:
    # Load AI Models
    try:
        model = joblib.load('gaming_model_full.pkl')
        encoders = joblib.load('encoders.pkl')
        model_loaded = True
    except:
        model_loaded = False

    # Sidebar
    with st.sidebar:
        st.title("NEXUS SYSTEM")
        st.caption(f"OPERATOR: {st.session_state.username.upper()}")
        st.markdown("---")
        mode = st.radio("MODULE SELECT:", ["🖥️ SESSION MONITOR", "🧠 NEURAL DIAGNOSTICS", "📂 HISTORY LOGS"])
        st.markdown("---")
        if st.button("LOGOUT"):
            st.session_state.logged_in = False
            st.rerun()

    # ====================================================
    # MODULE 1: MONITOR
    # ====================================================
    if mode == "🖥️ SESSION MONITOR":
        st.title("⏱️ ACTIVE SESSION MONITOR")
        
        col1, col2 = st.columns([2, 1])
        with col1:
             # Timer Display
             if "tracking" not in st.session_state:
                st.session_state.tracking = False
                st.session_state.start_time = None
             
             clock_placeholder = st.empty()
             if not st.session_state.tracking:
                 clock_placeholder.markdown("<h1 style='font-size: 80px; color: #444; font-family: Roboto Mono;'>00:00:00</h1>", unsafe_allow_html=True)

        with col2:
            st.markdown("### CONFIGURATION")
            limit_hours = st.number_input("SET LIMIT (HOURS):", value=4.0, step=0.5)
            limit_seconds = limit_hours * 3600
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("▶ INITIATE PROTOCOL"):
                st.session_state.tracking = True
                st.session_state.start_time = datetime.now()
            if st.button("⏹ TERMINATE PROTOCOL"):
                st.session_state.tracking = False
                st.success("Session Logged.")

        if st.session_state.tracking:
            while st.session_state.tracking:
                now = datetime.now()
                elapsed = now - st.session_state.start_time
                elapsed_seconds = elapsed.total_seconds()
                
                # Live Clock
                clock_placeholder.markdown(f"<h1 style='font-size: 100px; color: #fff; font-family: Roboto Mono;'>{str(elapsed).split('.')[0]}</h1>", unsafe_allow_html=True)
                
                if elapsed_seconds > limit_seconds:
                    play_alarm_sound()
                    # Also try windows notification if available
                    try: notification.notify(title='🛑 ALERT', message='Time Limit Reached', app_name='NEXUS', timeout=10)
                    except: pass
                    
                    st.error("⚠️ CRITICAL ALERT: TIME LIMIT EXCEEDED. TAKE A BREAK.")
                    st.session_state.tracking = False
                    break
                time.sleep(1)

    # ====================================================
    # MODULE 2: DIAGNOSTICS (THE FULL CHATBOT)
    # ====================================================
    elif mode == "🧠 NEURAL DIAGNOSTICS":
        st.title("🧠 NEURAL DIAGNOSTICS ENGINE")
        
        if not model_loaded:
            st.error("⚠️ SYSTEM ERROR: 'gaming_model_full.pkl' not found.")
        
        # Chat History
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": ">> SYSTEM ONLINE. TYPE 'START' TO BEGIN ANALYSIS."}]
        
        if "step" not in st.session_state: st.session_state.step = 0
        if "data" not in st.session_state: st.session_state.data = {}

        # Display Chat
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Input
        if prompt := st.chat_input("ENTER DATA STREAM..."):
            with st.chat_message("user"): st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            response = "PROCESSING..."
            
            # --- FULL 10-STEP LOGIC ---
            if st.session_state.step == 0:
                if "start" in prompt.lower():
                    response = "INITIALIZING SCAN...\n\n**ENTER USER AGE:**"
                    st.session_state.step = 1
                else: response = "COMMAND UNKNOWN. TYPE 'START'."

            elif st.session_state.step == 1:
                try:
                    st.session_state.data['What is your age?'] = int(prompt)
                    response = "**ENTER GENDER:** (Male/Female/Other)"
                    st.session_state.step = 2
                except: response = ">> ERROR: NUMERIC INPUT REQUIRED."

            elif st.session_state.step == 2:
                st.session_state.data['What is your gender?'] = prompt
                response = "**DAILY GAMING HOURS:**"
                st.session_state.step = 3

            elif st.session_state.step == 3:
                try:
                    hours = float(prompt)
                    st.session_state.data['How many hours do you play video games per day on average?'] = hours
                    response = "**DAYS PLAYED PER WEEK:**"
                    st.session_state.step = 4
                except: response = ">> ERROR: NUMERIC INPUT REQUIRED."

            elif st.session_state.step == 4:
                st.session_state.data['How many days per week do you play games?'] = float(prompt)
                response = "**PRIMARY GENRE:** (FPS, RPG, ETC.)"
                st.session_state.step = 5

            elif st.session_state.step == 5:
                st.session_state.data['What type of games do you mostly play?'] = prompt
                response = "**STRESS LEVEL (1-10):**"
                st.session_state.step = 6
            
            elif st.session_state.step == 6:
                st.session_state.data['On a scale of 1 to 10, how stressed do you feel on average?'] = int(prompt)
                response = "**ANXIETY LEVEL (1-10):**"
                st.session_state.step = 7

            elif st.session_state.step == 7:
                st.session_state.data['On a scale of 1 to 10, how anxious do you feel regularly?'] = int(prompt)
                response = "**SLEEP HOURS:**"
                st.session_state.step = 8

            elif st.session_state.step == 8:
                st.session_state.data['On average, how many hours of sleep do you get per night?'] = float(prompt)
                response = "**SOCIAL WITHDRAWAL FREQUENCY:** (Often/Sometimes/Never)"
                st.session_state.step = 9

            elif st.session_state.step == 9:
                st.session_state.data['How often do you feel socially withdrawn or isolated?'] = prompt
                response = "**GAMING AS COPING MECHANISM?** (Yes/No)"
                st.session_state.step = 10

            elif st.session_state.step == 10:
                st.session_state.data['Do you think gaming helps you cope with stress or emotional issues?'] = prompt
                
                # PREDICTION
                if model_loaded:
                    def encode_input(col_name, user_input):
                        encoder = encoders[col_name]
                        if user_input in encoder.classes_:
                            return encoder.transform([user_input])[0]
                        else:
                            return encoder.transform([encoder.classes_[0]])[0]

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
                        result = "HIGH RISK"
                        display_text = f"🔴 **HIGH RISK DETECTED** ({probs[1]:.0%} PROBABILITY)"
                        details = ">> ANALYSIS: PATTERNS MATCH AT-RISK GROUP."
                    else:
                        result = "OPTIMAL"
                        display_text = f"🟢 **LOW RISK / OPTIMAL** ({probs[0]:.0%} PROBABILITY)"
                        details = ">> ANALYSIS: PATTERNS WITHIN HEALTHY PARAMETERS."

                    # SAVE TO CLOUD
                    save_history(st.session_state.username, result, f"{probs[1]:.0%}")

                    response = f"**DIAGNOSTIC RESULT:** {display_text}\n\n{details}\n\n*Results uploaded to secure cloud.*"
                    st.session_state.step = 11

            elif st.session_state.step == 11:
                response = ">> SESSION COMPLETE. TYPE 'START' TO RESTART."
                if 'start' in prompt.lower():
                    st.session_state.step = 1
                    response = "RESTARTING... ENTER AGE:"

            time.sleep(0.5)
            with st.chat_message("assistant"): st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    # ====================================================
    # MODULE 3: HISTORY
    # ====================================================
    elif mode == "📂 HISTORY LOGS":
        st.title("📂 USER DATA ARCHIVES")
        
        try:
            full_history = get_history(st.session_state.username)
            if not full_history.empty:
                 # Filter by current username
                 if 'username' in full_history.columns:
                     user_logs = full_history[full_history['username'].astype(str) == st.session_state.username]
                     
                     st.dataframe(
                         user_logs[['date', 'result', 'probability']], 
                         use_container_width=True,
                         hide_index=True
                     )
                 else:
                     st.info("Log format refreshing...")
            else:
                 st.info("No logs found in cloud archive.")
        except Exception as e:
             st.error(f"Error fetching logs: {e}")
