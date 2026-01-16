import streamlit as st
import pandas as pd
import joblib
import time
from datetime import datetime
import os
import gspread
from plyer import notification

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="GameBot | AI Guardian",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. TACTICAL CSS STYLING ---
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

    h1, h2, h3 { color: #ffffff !important; border-bottom: 1px solid #444; font-family: 'Rajdhani', sans-serif; }
    .stTextInput input, .stNumberInput input { background-color: #111 !important; color: #fff !important; border: 1px solid #444 !important; font-family: 'Roboto Mono', monospace; }
    .stButton > button { width: 100%; background-color: #222; color: white; border: 1px solid #555; font-family: 'Rajdhani', sans-serif; font-weight: 600; }
    .stButton > button:hover { background-color: #fff; color: #000; }
    .stChatMessage { background-color: rgba(20, 20, 20, 0.8); border: 1px solid #333; border-radius: 5px; }
    
    /* Sidebar Clock */
    .clock-style {
        font-family: 'Roboto Mono', monospace;
        font-size: 20px;
        color: #00ff00;
        border: 1px solid #00ff00;
        padding: 5px;
        text-align: center;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GOOGLE SHEETS CONNECTION (DEBUG MODE) ---
# NOTE: Removed @st.cache_resource for the connection to ensure it doesn't get stale during debugging
def get_db_connection():
    try:
        if os.path.exists("service_key.json"):
            client = gspread.service_account(filename="service_key.json")
            sheet = client.open("Nexus_DB")
            return sheet
        elif "gcp_service_account" in st.secrets:
            creds = dict(st.secrets["gcp_service_account"])
            client = gspread.service_account_from_dict(creds)
            sheet = client.open("Nexus_DB")
            return sheet
        return None
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return None

def register_user(username, password):
    try:
        sh = get_db_connection()
        if not sh: return False
        worksheet = sh.worksheet("users")
        users = worksheet.get_all_records()
        df = pd.DataFrame(users)
        if not df.empty and 'username' in df.columns and username in df['username'].values: 
            return False
        worksheet.append_row([username, password])
        return True
    except Exception as e:
        st.error(f"❌ Register Error: {e}")
        return False

def login_user(username, password):
    try:
        sh = get_db_connection()
        if not sh: return False
        worksheet = sh.worksheet("users")
        users = worksheet.get_all_records()
        df = pd.DataFrame(users)
        if df.empty: return False
        user_match = df[(df['username'].astype(str) == username) & (df['password'].astype(str) == password)]
        return not user_match.empty
    except Exception as e:
        st.error(f"❌ Login Error: {e}")
        return False

def save_history(username, result, prob):
    # NOW SHOWS ERRORS if it fails
    try:
        sh = get_db_connection()
        if not sh: 
            st.error("❌ Database not connected.")
            return
        
        worksheet = sh.worksheet("history")
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Append data
        worksheet.append_row([username, date, result, prob])
        st.toast("✅ Saved to History Log!", icon="💾") # Show a popup confirmation
        
    except Exception as e:
        st.error(f"❌ SAVE FAILED: {e}")
        st.error("Check: Does 'history' tab exist? Do headers match?")

def get_history(username):
    try:
        sh = get_db_connection()
        if not sh: return pd.DataFrame()
        worksheet = sh.worksheet("history")
        data = worksheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Fetch Log Error: {e}")
        return pd.DataFrame()

# --- 4. ALARM SOUND ---
def play_alarm_sound():
    sound_url = "https://www.soundjay.com/buttons/beep-01a.mp3"
    st.markdown(f'<audio autoplay="true"><source src="{sound_url}" type="audio/mp3"></audio>', unsafe_allow_html=True)

# --- 5. APP LOGIC ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔒 GAMEBOT GATEWAY")
    if os.path.exists("service_key.json"): st.success("✅ Cloud Connected")
    else: st.warning("⚠️ Local Mode (Key Missing)")
    
    tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
    with tab1:
        u = st.text_input("User", key="l_u")
        p = st.text_input("Pass", type="password", key="l_p")
        if st.button("LOGIN"):
            if login_user(u, p): st.session_state.logged_in = True; st.session_state.username = u; st.rerun()
            else: st.error("Invalid Credentials.")
    with tab2:
        nu = st.text_input("New User", key="r_u")
        np = st.text_input("New Pass", type="password", key="r_p")
        if st.button("REGISTER"):
            if register_user(nu, np): st.success("Done. Please Login.")
            else: st.error("User exists or Connection Error.")

else:
    try:
        model = joblib.load('gaming_model_full.pkl')
        encoders = joblib.load('encoders.pkl')
        model_loaded = True
    except: model_loaded = False

    with st.sidebar:
        st.title("GAMEBOT SYSTEM")
        st.write(f"PILOT: **{st.session_state.username.upper()}**")
        
        # Real-time Clock Placeholder
        sidebar_clock = st.empty()
        sidebar_clock.markdown(f"<div class='clock-style'>{datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        mode = st.radio("MODULE:", ["🖥️ MONITOR", "🧠 DIAGNOSTICS", "📂 LOGS"])
        st.markdown("---")
        if st.button("LOGOUT"): st.session_state.logged_in = False; st.rerun()

    # --- MONITOR MODULE (Now saves to History!) ---
    if mode == "🖥️ MONITOR":
        st.title("⏱️ SESSION MONITOR")
        col1, col2 = st.columns([2, 1])
        
        with col1:
             clock_placeholder = st.empty()
             if "tracking" not in st.session_state: st.session_state.tracking = False
             if not st.session_state.tracking:
                 clock_placeholder.markdown("<h1 style='font-size: 100px; color: #444; font-family: Roboto Mono;'>00:00:00</h1>", unsafe_allow_html=True)
        
        with col2:
            limit = st.number_input("LIMIT (HRS):", value=4.0, step=0.5)
            
            if st.button("START"): 
                st.session_state.tracking = True
                st.session_state.start = datetime.now()
            
            if st.button("STOP"):
                if st.session_state.tracking:
                    # CALCULATE DURATION
                    final_elapsed = (datetime.now() - st.session_state.start).total_seconds()
                    m, s = divmod(final_elapsed, 60)
                    h, m = divmod(m, 60)
                    duration_str = "{:02d}h {:02d}m {:02d}s".format(int(h), int(m), int(s))
                    
                    st.session_state.tracking = False
                    st.success(f"Session Stopped. Duration: {duration_str}")
                    
                    # SAVE TO HISTORY!
                    save_history(st.session_state.username, "SESSION LOG", duration_str)

        if st.session_state.tracking:
            while st.session_state.tracking:
                now = datetime.now()
                sidebar_clock.markdown(f"<div class='clock-style'>{now.strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
                
                elapsed = (now - st.session_state.start).total_seconds()
                m, s = divmod(elapsed, 60)
                h, m = divmod(m, 60)
                time_str = "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))
                
                clock_placeholder.markdown(f"<h1 style='font-size: 100px; color: #00ff00; font-family: Roboto Mono; text-shadow: 0 0 20px #00ff00;'>{time_str}</h1>", unsafe_allow_html=True)
                
                if elapsed > limit * 3600:
                    play_alarm_sound()
                    try: notification.notify(title='GAMEBOT', message='Time Limit Reached', timeout=10)
                    except: pass
                    
                    st.error("LIMIT REACHED")
                    st.session_state.tracking = False
                    
                    # SAVE TO HISTORY (Limit Reached)
                    save_history(st.session_state.username, "LIMIT EXCEEDED", f"Limit: {limit}h")
                    break
                time.sleep(1)

    # --- DIAGNOSTICS MODULE (With Safety Check) ---
    elif mode == "🧠 DIAGNOSTICS":
        st.title("🧠 DIAGNOSTICS")
        if not model_loaded: st.error("Brain not found. Run train_final.py")
        
        if "messages" not in st.session_state: st.session_state.messages = [{"role":"assistant", "content":"Type 'START' to begin scan."}]
        if "step" not in st.session_state: st.session_state.step = 0
        if "data" not in st.session_state: st.session_state.data = {}

        for m in st.session_state.messages: st.chat_message(m["role"]).write(m["content"])

        if prompt := st.chat_input("INPUT..."):
            st.session_state.messages.append({"role":"user", "content":prompt})
            st.chat_message("user").write(prompt)
            
            # Sidebar clock update
            sidebar_clock.markdown(f"<div class='clock-style'>{datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
            
            response = "Processing..."
            
            # --- CHAT STEPS ---
            if st.session_state.step == 0:
                if "start" in prompt.lower(): st.session_state.step = 1; response = "INITIALIZING... **Enter Age:**"
                else: response = "Type 'START'."
            elif st.session_state.step == 1:
                try: st.session_state.data['age'] = int(prompt); st.session_state.step = 2; response = "**Enter Gender:** (Male/Female)"
                except: response = "Enter a number."
            elif st.session_state.step == 2:
                st.session_state.data['gender'] = prompt; st.session_state.step = 3; response = "**Enter Occupation:**"
            elif st.session_state.step == 3:
                st.session_state.data['occupation'] = prompt; st.session_state.step = 4; response = "**Avg Daily Gaming Hours:**"
            elif st.session_state.step == 4:
                try: st.session_state.data['hours'] = float(prompt); st.session_state.step = 5; response = "**Days played per week:**"
                except: response = "Enter a number."
            elif st.session_state.step == 5:
                st.session_state.data['days'] = float(prompt); st.session_state.step = 6; response = "**Primary Game Type:**"
            elif st.session_state.step == 6:
                st.session_state.data['type'] = prompt; st.session_state.step = 7; response = "**Lose track of time?** (Yes/No)"
            elif st.session_state.step == 7:
                st.session_state.data['track'] = prompt; st.session_state.step = 8; response = "**Skipped meals/sleep?** (Yes/No)"
            elif st.session_state.step == 8:
                st.session_state.data['skip'] = prompt; st.session_state.step = 9; response = "**Others concerned?** (Yes/No)"
            elif st.session_state.step == 9:
                st.session_state.data['concern'] = prompt; st.session_state.step = 10; response = "**Stress Level (1-10):**"
            elif st.session_state.step == 10:
                st.session_state.data['stress'] = int(prompt); st.session_state.step = 11; response = "**Anxiety Level (1-10):**"
            elif st.session_state.step == 11:
                st.session_state.data['anxiety'] = int(prompt); st.session_state.step = 12; response = "**Avg Sleep Hours:**"
            elif st.session_state.step == 12:
                st.session_state.data['sleep'] = float(prompt); st.session_state.step = 13; response = "**Socially Withdrawn?** (Often/Sometimes/Never)"
            elif st.session_state.step == 13:
                st.session_state.data['social'] = prompt; st.session_state.step = 14; response = "**Felt Guilty?** (Yes/No)"
            elif st.session_state.step == 14:
                st.session_state.data['guilt'] = prompt; st.session_state.step = 15; response = "**Gaming helps cope?** (Yes/No)"
            elif st.session_state.step == 15:
                st.session_state.data['cope'] = prompt
                
                if model_loaded:
                    def safe_encode(col, val):
                        if col in encoders:
                            try: return encoders[col].transform([val])[0]
                            except: return encoders[col].transform([encoders[col].classes_[0]])[0]
                        return 0

                    input_row = [
                        st.session_state.data['age'],
                        safe_encode('What is your gender?', st.session_state.data['gender']),
                        st.session_state.data['hours'],
                        st.session_state.data['days'],
                        safe_encode('What type of games do you mostly play?', st.session_state.data['type']),
                        safe_encode('Do you often lose track of time while gaming?', st.session_state.data['track']),
                        safe_encode('Have you ever skipped meals or sleep due to gaming?', st.session_state.data['skip']),
                        safe_encode('Have others ever expressed concern about your gaming habits?', st.session_state.data['concern']),
                        st.session_state.data['stress'],
                        st.session_state.data['anxiety'],
                        st.session_state.data['sleep'],
                        safe_encode('How often do you feel socially withdrawn or isolated?', st.session_state.data['social']),
                        safe_encode('Have you ever felt guilty or depressed after long gaming sessions?', st.session_state.data['guilt']),
                        safe_encode('Do you think gaming helps you cope with stress or emotional issues?', st.session_state.data['cope'])
                    ]

                    pred = model.predict([input_row])[0]
                    prob = model.predict_proba([input_row])[0]
                    
                    if pred == 1:
                        res_txt = "HIGH RISK"
                        res_msg = f"🔴 **HIGH RISK** ({prob[1]:.0%})"
                        detail = "Patterns match at-risk profile."
                    else:
                        res_txt = "OPTIMAL"
                        res_msg = f"🟢 **OPTIMAL** ({prob[0]:.0%})"
                        detail = "Patterns within healthy range."

                    save_history(st.session_state.username, res_txt, f"{prob[1]:.0%}")
                    response = f"**RESULTS:** {res_msg}\n\n{detail}\n\n*Saved to Cloud.*"
                    st.session_state.step = 16

            elif st.session_state.step == 16:
                response = "Session Complete. Type 'START' to restart."
                if 'start' in prompt.lower(): st.session_state.step = 1; response = "RESTARTING... Enter Age:"

            st.session_state.messages.append({"role":"assistant", "content":response})
            st.chat_message("assistant").write(response)

    # --- LOGS MODULE ---
    elif mode == "📂 LOGS":
        st.title("ARCHIVES")
        sidebar_clock.markdown(f"<div class='clock-style'>{datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
        
        if st.button("🔄 REFRESH LOGS"):
            st.rerun()

        try:
            full = get_history(st.session_state.username)
            if not full.empty and 'username' in full.columns:
                 # Filter only logs for this user
                 user_logs = full[full['username'].astype(str) == st.session_state.username]
                 st.dataframe(user_logs, use_container_width=True)
            else: st.info("No logs found.")
        except Exception as e:
            st.error(f"Error: {e}")
