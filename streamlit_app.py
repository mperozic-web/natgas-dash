import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V12", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; }
    .stAlert { padding: 0.3rem !important; border-radius: 8px; }
    h3 { font-size: 1rem !important; color: #1E1E1E; margin-bottom: 0.5rem; border-bottom: 2px solid #3498db; width: fit-content; }
    .run-box { background-color: #f0f2f6; padding: 10px; border-radius: 10px; border-left: 5px solid #3498db; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. TACTICAL RUN IDENTIFICATION ---
def get_current_run():
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    if 0 <= hour < 6: run = "00z"
    elif 6 <= hour < 12: run = "06z"
    elif 12 <= hour < 18: run = "12z"
    else: run = "18z"
    return {"run": run, "time": now_utc.strftime("%Y-%m-%d %H:%M UTC")}

# --- 2. NOAA AO/NAO TREND (S MEMORIJOM ZA 'vs Prev') ---
def get_noaa_with_trend(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        val = float(df.iloc[-1][[c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]])
        
        # Session state memorija za usporedbu runova
        state_key = f"prev_{name}"
        if state_key not in st.session_state:
            st.session_state[state_key] = val
        
        diff = val - st.session_state[state_key]
        st.session_state[state_key] = val # Update za sljedeći refresh
        
        status = "BULLISH" if (name in ["AO", "NAO"] and val < -0.8) or (name == "PNA" and val > 0.8) else "BEARISH"
        return {"val": val, "diff": diff, "status": status}
    except: return None

# --- 3. DEMAND MODEL SIMULATION (00z/12z STYLE) ---
def draw_demand_table():
    st.subheader("📊 National Weather Demand (Model Run Analysis)")
    run_info = get_current_run()
    
    st.markdown(f"""
    <div class="run-box">
        <strong>MODEL RUN:</strong> {run_info['run']} | <strong>DATA AS OF:</strong> {run_info['time']}<br>
        <small>Status: Analiziram odstupanja u potražnji za 0-360 FH (Forecast Hours)</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Simulacija tablice sa slike bazirana na GFS trendu
    fh_steps = [0, 24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 360]
    data = []
    for fh in fh_steps:
        # Primjer logike: ako je AO jako negativan, Natl Dev raste (Bullish)
        base_dev = round((fh/100) * -1.5, 2) # Ovo bi bio stvarni GFS/AIFS output
        bias = "BULL" if base_dev > 0.5 or fh > 192 else "BEAR" if base_dev < -0.5 else "NEUT"
        color = "🟢" if bias == "BULL" else "🔴" if bias == "BEAR" else "⚪"
        
        data.append({
            "FH": f"+{fh}",
            "Valid Date": (datetime.now() + timedelta(hours=fh)).strftime("%Y-%m-%d"),
            "Bias": f"{color} {bias}",
            "Natl Dev": f"{base_dev:+.2f}DD",
            "vs Prev": f"{round(base_dev*0.1, 2):+.2f}",
            "Driver": "Midwest" if fh > 150 else "West"
        })
    st.table(pd.DataFrame(data))

# --- IZVRŠAVANJE ---
from datetime import timedelta
ao = get_noaa_with_trend("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_with_trend("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
storage = {"val": 3200, "diff": +150} # Placeholder za brzi load

# --- UI DISPLAY ---
st.title("🛡️ Sniper Mirror V12.0 | Tactical Run Sniper")

# 1. MODEL RUN TABLE (Glavni fokus sa slike)
draw_demand_table()

st.markdown("---")

# 2. MASTER BIAS BAR
st.subheader("🏁 Live Run Bias")
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("AO Index (Run Shift)", f"{ao['val']:.2f}" if ao else "N/A", f"{ao['diff']:+.2f} vs Prev" if ao else "0.0")
with m2:
    st.metric("NAO Index (Run Shift)", f"{nao['val']:.2f}" if nao else "N/A", f"{nao['diff']:+.2f} vs Prev" if nao else "0.0")
with m3:
    st.info(f"🛢️ STORAGE BIAS: {'BEARISH' if storage['diff'] > 0 else 'BULLISH'}")

st.markdown("---")

# 3. PROGRESIJA I TRENDOVI
st.subheader("🗺️ Forecast Progression & Index Trends")
c1, c2 = st.columns(2)
with c1:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14 Day Outlook")
with c2:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", caption="AO Spaghetti Forecast")

st.markdown("---")
st.caption("V12.0 Tactical Run Sniper | 00z/12z Cycle Monitoring | Data: NOAA NCEP")
