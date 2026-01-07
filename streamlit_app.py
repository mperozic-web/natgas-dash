import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V26.1", layout="wide")

# STEALTH CSS
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    header, [data-testid="stHeader"] { background-color: #000000 !important; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 5px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #AAAAAA !important; }
    .stMetric { background-color: transparent; border: 1px solid #333; border-radius: 0px; padding: 10px; }
    .summary-text { font-size: 1.05rem; line-height: 1.6; color: #FFFFFF; border: 1px solid #444; padding: 20px; margin-bottom: 30px; }
    .legend-text { font-size: 0.85rem; color: #BBBBBB; margin-top: 5px; font-style: italic; }
    .trend-text { font-size: 0.8rem; color: #00FF00; font-weight: bold; }
    .trend-text-down { font-size: 0.8rem; color: #FF4B4B; font-weight: bold; }
    section[data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. DOHVAT NOAA PODATAKA S POVIJEŠĆU ---
@st.cache_data(ttl=600)
def get_noaa_with_history(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        val_col = df.columns[-1]
        latest = float(df.iloc[-1][val_col])
        yesterday = float(df.iloc[-2][val_col])
        last_week = float(df.iloc[-8][val_col])
        return {
            "latest": latest,
            "vs_y": latest - yesterday,
            "vs_w": latest - last_week
        }
    except:
        return {"latest": 0.0, "vs_y": 0.0, "vs_w": 0.0}

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

# --- SIDEBAR: COT ---
with st.sidebar:
    st.header("🏛️ COT DATA CENTER")
    nc_l = st.number_input("NC Long", value=288456)
    nc_s = st.number_input("NC Short", value=424123)
    c_l = st.number_input("Comm Long", value=512000)
    c_s = st.number_input("Comm Short", value=380000)
    nr_l = st.number_input("Retail Long", value=54120)
    nr_s = st.number_input("Retail Short", value=32100)
    nc_net = nc_l - nc_s
    nr_net = nr_l - nr_s

# --- DOHVAT ---
ao_data = get_noaa_with_history("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao_data = get_noaa_with_history("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna_data = get_noaa_with_history("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia_data(EIA_API_KEY)

def get_status(val, idx_type):
    if idx_type in ["AO", "NAO"]:
        if val < -2.0: return "EXTREME BULLISH"
        if val < -1.0: return "BULLISH"
        if val < -0.4: return "MINOR BULLISH"
        if val > 1.5: return "EXTREME BEARISH"
        if val > 0.8: return "BEARISH"
        if val > 0.4: return "MINOR BEARISH"
    else:
        if val > 1.5: return "EXTREME BULLISH"
        if val > 0.8: return "BULLISH"
        if val > 0.4: return "MINOR BULLISH"
        if val < -1.5: return "EXTREME BEARISH"
        if val < -0.8: return "BEARISH"
        if val < -0.4: return "MINOR BEARISH"
    return "NEUTRAL"

# --- 1. EXECUTIVE STRATEGIC SUMMARY ---
st.subheader("📋 Executive Strategic Summary")
ao = ao_data['latest']
nao = nao_data['latest']
pna = pna_data['latest']

meteo_b = "BULLISH" if (ao < -0.4 or nao < -0.4) else "BEARISH"
stor_b = "BULLISH" if (storage and storage['diff_5y'] < 0) else "BEARISH"

squeeze_play = "Pozicioniranje je u ravnoteži."
if nc_net < -150000 and nr_net < -10000 and meteo_b == "BULLISH":
    squeeze_play = "**SHORT SQUEEZE RISK:** Ekstremni shortovi pod pritiskom AO/NAO pada."
elif nc_net > 100000 and nr_net > 20000 and meteo_b == "BEARISH":
    squeeze_play = "**LONG SQUEEZE RISK:** Previše optimizma uz toplo vrijeme na radaru."

st.markdown(f"""<div class='summary-text'>
Atmosfera: **{meteo_b}** (AO: {ao:.2f}, NAO: {nao:.2f}) | 
Zalihe: **{stor_b}** ({storage['diff_5y']:+} Bcf vs 5y Avg) | 
{squeeze_play}</div>""", unsafe_allow_html=True)

# --- 2. NOAA RADAR ---
st.subheader("🗺️ NOAA Temperature Radar")
c_r1, c_r2 = st.columns(2)
c_r1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10 dana")
c_r2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14 dana")

st.markdown("---")

# --- 3. ATMOSPHERIC TRENDS ---
st.subheader("📈 Index Forecast Trends & Velocity")
v1, v2, v3 = st.columns(3)

def display_index_col(col, title, data, idx_type, inverse=True):
    with col:
        st.image(f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/{title.lower()}.sprd2.gif" if title=="AO" else f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/{title.lower()}.sprd2.gif")
        status = get_status(data['latest'], idx_type)
        st.metric(f"{title} INDEX", f"{data['latest']:.2f}", status, delta_color="inverse" if inverse else "normal")
        
        # Trendovi ispod metrike
        y_color = "green" if (data['vs_y'] < 0 if inverse else data['vs_y'] > 0) else "red"
        w_color = "green" if (data['vs_w'] < 0 if inverse else data['vs_w'] > 0) else "red"
        
        st.markdown(f"""
            <div style='margin-top:-10px; margin-bottom:10px;'>
                <span style='color:{y_color}; font-size:0.85rem;'>vs yesterday: {data['vs_y']:+.2f}</span><br>
                <span style='color:{w_color}; font-size:0.85rem;'>vs last week: {data['vs_w']:+.2f}</span>
            </div>
            <div class='legend-text'>Legenda: Pad crne linije ispod nule = BULLISH.</div>
        """, unsafe_allow_html=True)

display_index_col(v1, "AO", ao_data, "AO", True)
display_index_col(v2, "NAO", nao_data, "NAO", True)
display_index_col(v3, "PNA", pna_data, "PNA", False)

st.markdown("---")

# --- 4. EIA ---
st.subheader("🛢️ EIA Storage Intelligence")
if storage:
    e1, e2, e3 = st.columns(3)
    e1.metric("ZALIHE", f"{storage['curr']} Bcf", f"{storage['chg']} Bcf")
    stor_label = "BULLISH" if storage['diff_5y'] < 0 else "BEARISH"
    e2.metric(f"vs 5y AVG ({stor_label})", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")
    with e3:
        now = datetime.now(timezone.utc)
        target = (now + timedelta(days=(3 - now.weekday()) % 7)).replace(hour=15, minute=30, second=0)
        if now >= target: target += timedelta(days=7)
        diff = target - now
        st.write(f"⌛ EIA COUNTDOWN: {int(diff.total_seconds()//3600)}h {int((diff.total_seconds()%3600)//60)}m")
