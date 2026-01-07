import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V23", layout="wide")

# HIGH-CONTRAST CSS
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    h2, h3 { color: #000000 !important; font-weight: 900 !important; border-bottom: 2px solid #000; padding-bottom: 5px; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 800 !important; color: #1A1A1A !important; }
    [data-testid="stMetricLabel"] { font-size: 1rem !important; color: #333333 !important; text-transform: uppercase; }
    .stMetric { background-color: #F0F2F6; padding: 15px; border-radius: 5px; border: 2px solid #000000; }
    .summary-card { background-color: #000000; color: #FFFFFF; padding: 20px; border-radius: 5px; margin-bottom: 25px; }
    .bias-bull { color: #00FF00; font-weight: bold; }
    .bias-bear { color: #FF0000; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- DOHVAT PODATAKA ---
@st.cache_data(ttl=600)
def get_noaa_val(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return float(df.iloc[-1].iloc[-1])
    except: return 0.0

@st.cache_data(ttl=3600)
def get_eia_data(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 50}
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        df['val'] = df['value'].astype(int)
        curr = df.iloc[0]
        avg_5y = int(df['val'].mean())
        return {"curr": curr['val'], "chg": curr['val'] - df.iloc[1]['val'], "diff_5y": curr['val'] - avg_5y, "date": curr['period']}
    except: return None

# --- SIDEBAR: COT INPUT ---
with st.sidebar:
    st.header("🏛️ COT DATA ENTRY")
    nc_l = st.number_input("Non-Comm Long", value=288456)
    nc_s = st.number_input("Non-Comm Short", value=424123)
    c_l = st.number_input("Commercial Long", value=512000)
    c_s = st.number_input("Commercial Short", value=380000)
    
    nc_net = nc_l - nc_s
    comm_net = c_l - c_s

# --- IZVRŠAVANJE ANALIZE ---
ao = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia_data(EIA_API_KEY)

# --- 1. EXECUTIVE SUMMARY ---
meteo_bull = (ao < -0.5 or nao < -0.5)
stor_bull = (storage and storage['diff_5y'] < 0)
cot_bull = (nc_net < -150000)

st.markdown(f"""
    <div class="summary-card">
        <h2 style="color:white; border:none;">STRATEŠKI SAŽETAK</h2>
        <p style="font-size:1.2rem;">
            BIAS: {"LONG" if (meteo_bull and stor_bull) else "SHORT" if (not meteo_bull and not stor_bull) else "NEUTRAL"}
        </p>
        <p>
            NOAA: <span class="{"bias-bull" if meteo_bull else "bias-bear"}">{'BULL' if meteo_bull else 'BEAR'}</span> | 
            EIA: <span class="{"bias-bull" if stor_bull else "bias-bear"}">{'BULL' if stor_bull else 'BEAR'}</span> | 
            COT: <span class="{"bias-bull" if cot_bull else "bias-bear"}">{'SQUEEZE RISK' if cot_bull else 'BEARISH'}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. NOAA RADAR: SHORT vs LONG TERM ---
st.subheader("🗺️ NOAA Temperature Radar")
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="SHORT TERM (6-10 dana)", use_container_width=True)
with col_r2:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="LONG TERM (8-14 dana)", use_container_width=True)

st.markdown("---")

# --- 3. ATMOSPHERIC DRIVERS ---
st.subheader("📈 Index Forecast Trends")
v1, v2, v3 = st.columns(3)
with v1:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif")
    st.metric("AO INDEX", f"{ao:.2f}", "BULLISH" if ao < -0.5 else "BEARISH", delta_color="inverse")
with v2:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif")
    st.metric("NAO INDEX", f"{nao:.2f}", "BULLISH" if nao < -0.5 else "BEARISH", delta_color="inverse")
with v3:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif")
    st.metric("PNA INDEX", f"{pna:.2f}", "BULLISH" if pna > 0.5 else "BEARISH")

st.markdown("---")

# --- 4. EIA STORAGE & COUNTDOWN ---
st.subheader("🛢️ EIA Storage Control")
if storage:
    e1, e2, e3 = st.columns(3)
    e1.metric("ZALIHE", f"{storage['curr']} Bcf", f"{storage['chg']} Bcf")
    # vs 5y Average: rast (plus) je crven, pad (minus) je zelen. 
    e2.metric("vs 5y AVG", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")
    
    with e3:
        now = datetime.now(timezone.utc)
        target = (now + timedelta(days=(3 - now.weekday()) % 7)).replace(hour=15, minute=30, second=0)
        if now >= target: target += timedelta(days=7)
        diff = target - now
        st.error(f"EIA COUNTDOWN: {int(diff.total_seconds()//3600)}h {int((diff.total_seconds()%3600)//60)}m")
