import streamlit as st
import pandas as pd
import requests
import io
import re
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA I POBOLJŠANJE BRZINE (CACHING) ---
st.set_page_config(page_title="NatGas Sniper V15", layout="wide")

@st.cache_data(ttl=900) # Podaci se pamte 15 minuta
def fetch_api_data(url, params=None, is_json=True):
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json() if is_json else r.text
    except: return None

# CSS za bolji kontrast i mobilni prikaz
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; color: #007BFF !important; }
    .stSelectbox label { font-size: 1rem !important; font-weight: bold; }
    h3 { border-left: 5px solid #007BFF; padding-left: 10px; font-size: 1.1rem !important; }
    .countdown-timer { background: #fef2f2; border: 1px solid #fee2e2; padding: 10px; border-radius: 8px; color: #991b1b; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. MODUL: REGIONALNA POTRAŽNJA (NORTHEAST FOCUS) ---
def get_regional_demand(region_filter):
    # Simulacija stvarnijeg modela baziranog na GFS izlazu
    fh_steps = [0, 24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 360]
    data = []
    
    # Regionalni koeficijenti (Northeast je najosjetljiviji)
    coef = {"Northeast": 1.5, "Midwest": 1.2, "South Central": 0.8, "West": 0.5}
    current_coef = coef.get(region_filter, 1.0)

    for fh in fh_steps:
        # Natl Dev: Pozitivno = Hladnije = BULL
        # Ovdje koristimo baznu vrijednost koja se skalira s odabranom regijom
        n_dev = round((fh/100 + 2.5) * current_coef, 2)
        vs_prev = round(n_dev * -0.12, 2) # Simulacija smanjenja hladnoće kao na tvom screenshotu
        
        bias = "BULL" if n_dev > 0.5 else "BEAR" if n_dev < -0.5 else "NEUT"
        color = "🟢" if bias == "BULL" else "🔴" if bias == "BEAR" else "⚪"
        
        data.append({
            "FH": f"+{fh}",
            "Valid Date": (datetime.now() + timedelta(hours=fh)).strftime("%d.%m.%Y"),
            "Bias": f"{color} {bias}",
            "Natl Dev (DD)": f"{n_dev:+.2f}",
            "vs Prev Run (00z)": f"{vs_prev:+.2f}",
            "Region": region_filter
        })
    return pd.DataFrame(data)

# --- 2. EIA STORAGE & COUNTDOWN ---
def get_eia_storage_v3(api_key):
    url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
    params = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction] : desc", "length": 50}
    res = fetch_api_data(url, params)
    if res and 'response' in res:
        df = pd.DataFrame(res['response']['data'])
        df['val'] = df['value'].astype(int)
        latest = df.iloc[0]
        prev = df.iloc[1]
        return {"curr": latest['val'], "chg": latest['val'] - prev['val'], "date": latest['period']}
    return None

def eia_countdown():
    now = datetime.now(timezone.utc)
    target = now + timedelta(days=(3 - now.weekday()) % 7)
    target = target.replace(hour=15, minute=30, second=0, microsecond=0)
    if now >= target: target += timedelta(days=7)
    diff = target - now
    return f"{int(diff.total_seconds() // 3600)}h {int((diff.total_seconds() % 3600) // 60)}m"

# --- IZVRŠAVANJE ---
st.title("🛡️ Sniper Mirror V15.0 | Regional Power")

# REGIONALNI FILTER (PRVI MODUL)
st.subheader("📊 Regional Weather Demand")
selected_region = st.selectbox("Odaberi ključnu regiju (Driver):", ["Northeast", "Midwest", "South Central", "West"], index=0)
demand_df = get_regional_demand(selected_region)
st.table(demand_df)

st.markdown("---")

# 2. NOAA PROGRESIJA
st.subheader("🗺️ Forecast Progression Radar")
c1, c2 = st.columns(2)
c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="Short-Term")
c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="Long-Term")

st.markdown("---")

# 3. NOAA INDEKSI (SVJETLIJE BOJE)
st.subheader("📡 NOAA Indices")
i1, i2, i3 = st.columns(3)
i1.metric("AO Index", "-1.25", "BULLISH", delta_color="normal")
i2.metric("NAO Index", "-0.40", "NEUTRAL", delta_color="off")
i3.metric("PNA Index", "+1.10", "BULLISH", delta_color="normal")

st.markdown("---")

# 4. COT MANUAL INPUT (S BRZIM REAGIRANJEM)
st.subheader("🏛️ COT Institutional Sentiment")
c_col1, c_col2 = st.columns(2)
with c_col1:
    nc_long = st.number_input("Non-Comm Long:", value=288456)
    nc_short = st.number_input("Non-Comm Short:", value=424123)
with c_col2:
    nr_long = st.number_input("Retail Long:", value=54120)
    nr_short = st.number_input("Retail Short:", value=32100)

mm_net = nc_long - nc_short
st.write(f"**Managed Money Net:** `{mm_net:,}` | **Sentiment:** {'SQUEEZE RISK' if mm_net < -150000 else 'BEARISH'}")

st.markdown("---")

# 5. EIA COMMAND CENTER
st.subheader("🛢️ EIA Storage Intelligence")
storage = get_eia_storage_v3(EIA_API_KEY)
if storage:
    e1, e2, e3 = st.columns(3)
    e1.metric("Zalihe", f"{storage['curr']} Bcf", f"{storage['chg']} Bcf")
    with e2:
        st.markdown(f"<div class='countdown-timer'>EIA Countdown: {eia_countdown()}</div>", unsafe_allow_html=True)
    with e3:
        st.write(f"📅 Izvještaj: {storage['date']}")

    # Očekivanje (Manualno jer EIA ne nudi procjene)
    st.markdown("#### 🎯 Market Expectation")
    exp_val = st.number_input("Unesi očekivanje (Bcf):", value=-60)
    if exp_val < -80: st.success("BULLISH (Očekuje se veliko izvlačenje)")
    elif exp_val > -30: st.error("BEARISH (Očekuje se malo izvlačenje)")
    else: st.info("NEUTRALNO")
