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
    @keyframes scrollGrid { 0% { background-position: 0 0; } 100% { background-position: 40px 40px; } }
    .stApp {
        background-color: #0a0a0a;
        background-image: linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
        background-size: 40px 40px;
        animation: scrollGrid 4s linear infinite;
        font-family: 'Rajdhani', sans-serif;
        color: #e0e0e0;
    }
    h1, h2, h3 { color: #ffffff !important; border-bottom: 1px solid #444; font-family: 'Rajdhani', sans-serif; }
    .stTextInput input, .stNumberInput input { background-color: #111 !important; color: #fff !important; border: 1px solid #444 !important; font-family: 'Roboto Mono', monospace; }
    .stButton > button { width: 100%; background-color: #222; color: white; border: 1px solid #555; font-family: 'Rajdhani', sans-serif; font-weight: 600; }
    .stButton > button:hover { background-color: #fff; color: #000; }
    .clock-style { font-family: 'Roboto Mono', monospace; font-size: 20px; color: #00ff00; border: 1px solid #00ff00; padding: 5px; text-align: center; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 3. SMART CONNECTION (Fixes "Key Missing" Error) ---
def get_db_connection():
    try:
        # Priority 1: Local File (Laptop)
        if os.path.exists("service_key.json"):
            client = gspread.service_account(filename="service_key.json")
            return client.open("Nexus_DB")
            
        # Priority 2: Cloud Secrets (Streamlit Website)
        # This handles both [gcp_service_account] format AND raw JSON format
        if "gcp_service_account" in st.secrets:
            creds = dict(st.secrets["gcp_service_account"])
            client = gspread.service_account_from_dict(creds)
            return client.open("Nexus_DB")
            
        # Priority 3: Raw JSON in Secrets (Fallback)
        if "private_key" in st.secrets:
            creds = dict(st.secrets)
            client = gspread.service_account_from_dict(creds)
            return client.open("Nexus_DB")

        return None
    except Exception as e:
        return None

# Helper to auto-create sheets
def get_or_create_worksheet(sh, name, headers):
    try: return sh.worksheet(name)
    except: 
        ws = sh.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers); return ws

def register_user(username, password):
    try:
        sh = get_db_connection()
        if not sh: return False
        ws = get_or_create_worksheet(sh, "users", ["username", "password"])
        df = pd.DataFrame(ws.get_all_records())
        if not df.empty and 'username' in df.columns and username in df['username'].values: return False
        ws.append_row([username, password]); return True
    except: return False

def login_user(username, password):
    try:
        sh = get_db_connection()
        if not sh: return False
        ws = get_or_create_worksheet(sh, "users", ["username", "password"])
        df = pd.DataFrame(ws.get_all_records())
        if df.empty: return False
        return not df[(df['username'].astype(str) == username) & (df['password'].astype(str) == password)].empty
    except: return False

def save_history(username, result, prob):
    try:
        sh = get_db_connection()
        if sh:
            ws = get_or_create_worksheet(sh, "history", ["username", "date", "result", "probability"])
            ws.append_row([username, datetime.now().strftime("%Y-%m-%d %H:%M"), result, prob])
            st.toast("✅ Saved!", icon="💾")
    except: pass

def get_history(username):
    try:
        sh = get_db_connection()
        if not sh: return pd.DataFrame()
        ws = get_or_create_worksheet(sh, "history", ["username", "date", "result", "probability"])
        return pd.DataFrame(ws.get_all_records())
    except: return pd.DataFrame()

# --- 4. AUDIO ---
def play_alarm_sound():
    st.markdown(f'<audio autoplay="true"><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3"></audio>', unsafe_allow_html=True)

# --- 5. MAIN APP ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔒 GAMEBOT GATEWAY")
    
    # --- SMART STATUS CHECK ---
    # This checks if connection actually works, not just if file exists
    if get_db_connection(): st.success("✅ Cloud Connected (Ready)")
    else: st.warning("⚠️ Local Mode (Add 'service_key.json' or Configure Secrets)")

    tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
    with tab1:
        u = st.text_input("User", key="l_u")
        p = st.text_input("Pass", type="password", key="l_p")
        if st.button("LOGIN"):
            if login_user(u, p): st.session_state.logged_in = True; st.session_state.username = u; st.rerun()
            else: st.error("Invalid or No Connection.")
    with tab2:
        nu = st.text_input("New User", key="r_u")
        np = st.text_input("New Pass", type="password", key="r_p")
        if st.button("REGISTER"):
            if register_user(nu, np): st.success("Done. Login.")
            else: st.error("Error.")

else:
    try:
        model = joblib.load('gaming_model_full.pkl')
        encoders = joblib.load('encoders.pkl')
        model_loaded = True
    except: model_loaded = False

    with st.sidebar:
        st.title("GAMEBOT SYSTEM")
        st.write(f"PILOT: **{st.session_state.username.upper()}**")
        clock = st.empty()
        clock.markdown(f"<div class='clock-style'>{datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
        st.markdown("---")
        mode = st.radio("MODULE:", ["🖥️ MONITOR", "🧠 DIAGNOSTICS", "📂 LOGS"])
        if st.button("LOGOUT"): st.session_state.logged_in = False; st.rerun()

    if mode == "🖥️ MONITOR":
        st.title("⏱️ MONITOR")
        col1, col2 = st.columns([2, 1])
        with col1:
             ph = st.empty()
             if "tracking" not in st.session_state: st.session_state.tracking = False
             if not st.session_state.tracking: ph.markdown("<h1 style='font-size: 80px; color: #444;'>00:00:00</h1>", unsafe_allow_html=True)
        with col2:
            limit = st.number_input("LIMIT (HRS):", value=4.0, step=0.5)
            if st.button("START"): st.session_state.tracking = True; st.session_state.start = datetime.now()
            if st.button("STOP"):
                if st.session_state.tracking:
                    dur = str(datetime.now() - st.session_state.start).split('.')[0]
                    st.session_state.tracking = False; st.success(f"Stopped: {dur}"); save_history(st.session_state.username, "SESSION", dur)

        if st.session_state.tracking:
            while st.session_state.tracking:
                now = datetime.now()
                clock.markdown(f"<div class='clock-style'>{now.strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
                el = (now - st.session_state.start).total_seconds()
                ph.markdown(f"<h1 style='font-size: 80px; color: #0f0;'>{time.strftime('%H:%M:%S', time.gmtime(el))}</h1>", unsafe_allow_html=True)
                if el > limit * 3600:
                    play_alarm_sound(); st.error("LIMIT REACHED"); st.session_state.tracking = False; save_history(st.session_state.username, "LIMIT", f"{limit}h")
                    break
                time.sleep(1)

    elif mode == "🧠 DIAGNOSTICS":
        st.title("🧠 DIAGNOSTICS")
        if not model_loaded: st.error("Run train_final.py first")
        if "messages" not in st.session_state: st.session_state.messages = [{"role":"assistant", "content":"Type 'START'."}]
        if "step" not in st.session_state: st.session_state.step = 0
        if "data" not in st.session_state: st.session_state.data = {}
        
        for m in st.session_state.messages: st.chat_message(m["role"]).write(m["content"])
        if prompt := st.chat_input("INPUT..."):
            st.session_state.messages.append({"role":"user", "content":prompt})
            st.chat_message("user").write(prompt)
            resp = "Processing..."
            
            # CHAT LOGIC (Compact)
            s = st.session_state.step
            d = st.session_state.data
            if s==0: 
                if 'start' in prompt.lower(): st.session_state.step=1; resp="**Age:**"
                else: resp="Type 'START'"
            elif s==1: d['age']=int(prompt); st.session_state.step=2; resp="**Gender:** (Male/Female)"
            elif s==2: d['gender']=prompt; st.session_state.step=3; resp="**Occupation:**"
            elif s==3: d['occupation']=prompt; st.session_state.step=4; resp="**Daily Hours:**"
            elif s==4: d['hours']=float(prompt); st.session_state.step=5; resp="**Days/Week:**"
            elif s==5: d['days']=float(prompt); st.session_state.step=6; resp="**Game Type:**"
            elif s==6: d['type']=prompt; st.session_state.step=7; resp="**Lose Track of Time?** (Yes/No)"
            elif s==7: d['track']=prompt; st.session_state.step=8; resp="**Skip Meals?** (Yes/No)"
            elif s==8: d['skip']=prompt; st.session_state.step=9; resp="**Others Concerned?** (Yes/No)"
            elif s==9: d['concern']=prompt; st.session_state.step=10; resp="**Stress (1-10):**"
            elif s==10: d['stress']=int(prompt); st.session_state.step=11; resp="**Anxiety (1-10):**"
            elif s==11: d['anxiety']=int(prompt); st.session_state.step=12; resp="**Sleep Hours:**"
            elif s==12: d['sleep']=float(prompt); st.session_state.step=13; resp="**Socially Withdrawn?**"
            elif s==13: d['social']=prompt; st.session_state.step=14; resp="**Guilty?** (Yes/No)"
            elif s==14: d['guilt']=prompt; st.session_state.step=15; resp="**Gaming helps cope?**"
            elif s==15:
                d['cope']=prompt
                if model_loaded:
                    def enc(c,v): return encoders[c].transform([v])[0] if v in encoders[c].classes_ else 0
                    row = [d['age'], enc('What is your gender?', d['gender']), d['hours'], d['days'], enc('What type of games do you mostly play?', d['type']),
                           enc('Do you often lose track of time while gaming?', d['track']), enc('Have you ever skipped meals or sleep due to gaming?', d['skip']),
                           enc('Have others ever expressed concern about your gaming habits?', d['concern']), d['stress'], d['anxiety'], d['sleep'],
                           enc('How often do you feel socially withdrawn or isolated?', d['social']), enc('Have you ever felt guilty or depressed after long gaming sessions?', d['guilt']),
                           enc('Do you think gaming helps you cope with stress or emotional issues?', d['cope'])]
                    p = model.predict([row])[0]; prob = model.predict_proba([row])[0]
                    res = "HIGH RISK" if p==1 else "OPTIMAL"
                    resp = f"**RESULT:** {res} ({prob[1 if p==1 else 0]:.0%})\n\n*Saved to Cloud.*"
                    save_history(st.session_state.username, res, f"{prob[1]:.0%}")
                    st.session_state.step = 16
            elif s==16: resp="Type 'START' to restart."; st.session_state.step=1 if 'start' in prompt.lower() else 16
            
            st.session_state.messages.append({"role":"assistant", "content":resp})
            st.chat_message("assistant").write(resp)

    elif mode == "📂 LOGS":
        st.title("ARCHIVES")
        if st.button("REFRESH"): st.rerun()
        h = get_history(st.session_state.username)
        if not h.empty and 'username' in h.columns: st.dataframe(h[h['username'].astype(str) == st.session_state.username], use_container_width=True)
        else: st.info("No logs.")
