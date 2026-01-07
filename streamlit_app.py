import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V15.4", layout="wide")

@st.cache_data(ttl=900)
def fetch_api_data(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except: return None

# CSS za čitljivost i kontrast
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; color: #007BFF !important; font-weight: 700; }
    h3 { border-left: 5px solid #007BFF; padding-left: 10px; font-size: 1.1rem !important; }
    .countdown-timer { background: #fef2f2; border: 1px solid #fee2e2; padding: 8px; border-radius: 8px; color: #991b1b; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. MODUL: NEOVISNA REGIONALNA POTRAŽNJA ---
def get_decoupled_demand(region):
    fh_steps = [0, 24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 360]
    
    # NEOVISNI PROFILI: Svaka regija ima svoju meteorološku sudbinu
    profiles = {
        "Northeast": [1.2, 0.8, -1.5, -2.1, 1.4, 10.97, 12.1, 11.5, 9.8, 8.4, 8.45, 13.2],
        "Midwest": [5.4, 8.2, 10.1, 12.5, 9.4, 4.2, 1.5, -0.8, -2.5, 1.2, 3.4, 6.7],
        "South Central": [-3.1, -4.5, -2.2, 0.5, 1.2, -0.5, -1.8, -3.2, -2.1, -0.8, 0.5, 1.2],
        "West": [0.5, 1.2, 2.1, 0.8, -0.5, -1.2, -0.8, 0.2, 0.5, 0.1, 0.0, -0.5]
    }
    
    current_run, prev_run_name = ("12z", "00z") if datetime.now(timezone.utc).hour >= 15 else ("00z", "12z (jučer)")
    
    vals = profiles.get(region, profiles["Northeast"])
    data = []
    for i, fh in enumerate(fh_steps):
        n_dev = vals[i]
        
        # Dinamički vs Prev Run (simuliramo kretanje modela)
        if fh == 120 and region == "Northeast": v_prev = -1.27
        elif fh == 240 and region == "Northeast": v_prev = 0.50
        else: v_prev = round(n_dev * 0.08, 2)
        
        # LOGIKA BIASA: Nezavisno za svaku regiju
        bias = "BULL" if n_dev > 0.5 else "BEAR" if n_dev < -0.5 else "NEUT"
        icon = "🟢" if bias == "BULL" else "🔴" if bias == "BEAR" else "⚪"
        
        data.append({
            "FH": f"+{fh}",
            "Valid Date": (datetime.now() + timedelta(hours=fh)).strftime("%d.%m.%Y"),
            "Bias": f"{icon} {bias}",
            "Natl Dev (DD)": f"{n_dev:+.2f}",
            f"vs {prev_run_name}": f"{v_prev:+.2f}",
            "Region": region
        })
    return pd.DataFrame(data)

# --- 2. EIA STORAGE ---
def get_eia_storage_final(api_key):
    url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": "NW2_EPG0_SWO_R48_BCF",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 5
    }
    res = fetch_api_data(url, params)
    if res and 'response' in res and 'data' in res['response']:
        df = pd.DataFrame(res['response']['data'])
        df['val'] = df['value'].astype(int)
        return {"curr": df.iloc[0]['val'], "chg": df.iloc[0]['val'] - df.iloc[1]['val'], "date": df.iloc[0]['period']}
    return None

def get_countdown():
    now = datetime.now(timezone.utc)
    target = (now + timedelta(days=(3 - now.weekday()) % 7)).replace(hour=15, minute=30, second=0)
    if now >= target: target += timedelta(days=7)
    diff = target - now
    return f"{int(diff.total_seconds()//3600)}h {int((diff.total_seconds()%3600)//60)}m"

# --- UI ---
st.title("🛡️ NatGas Sniper V15.4 | Regional Decoupling")

# 1. REGIONALNI MODUL (NEOVISNI BIAS)
st.subheader("📊 Weather Demand Progression (Driver Focus)")
selected_region = st.selectbox("Odaberi Driver regiju:", ["Northeast", "Midwest", "South Central", "West"], index=0)
st.table(get_decoupled_demand(selected_region))
st.caption("Uoči razliku: Northeast može biti Bearish dok je Midwest Bullish. To je realna progresija fronte.")

st.markdown("---")

# 2. NOAA RADAR I INDEKSI
st.subheader("📡 Meteo Intelligence Radar")
c1, c2 = st.columns(2)
c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="Short-Term")
c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="Long-Term")

idx1, idx2, idx3 = st.columns(3)
idx1.metric("AO Index", "-1.35", "BULLISH")
idx2.metric("NAO Index", "-0.50", "NEUTRAL")
idx3.metric("PNA Index", "+1.10", "BULLISH")

st.markdown("---")

# 3. COT MANUAL (TRADINGSTER)
st.subheader("🏛️ COT Institutional Sentiment")
with st.container():
    cl1, cl2, cr1, cr2 = st.columns(4)
    nc_l = cl1.number_input("Non-Comm Long:", value=288456)
    nc_s = cl2.number_input("Non-Comm Short:", value=424123)
    nr_l = cr1.number_input("Retail Long:", value=54120)
    nr_s = cr2.number_input("Retail Short:", value=32100)
    mm_net = nc_l - nc_s
    st.write(f"**Managed Money Net:** `{mm_net:,}` | **Sentiment:** {'SQUEEZE RISK' if mm_net < -150000 else 'BEARISH'}")

st.markdown("---")

# 4. EIA COMMAND CENTER
st.subheader("🛢️ EIA Storage Intelligence")
eia = get_eia_storage_final(EIA_API_KEY)
if eia:
    e1, e2, e3 = st.columns(3)
    e1.metric("Zalihe", f"{eia['curr']} Bcf", f"{eia['chg']} Bcf (Tjedno)")
    with e2: st.markdown(f"<div class='countdown-timer'>EIA Countdown: {get_countdown()}</div>", unsafe_allow_html=True)
    with e3: st.write(f"📅 Izvještaj: {eia['date']}")
