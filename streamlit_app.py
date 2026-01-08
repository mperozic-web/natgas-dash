import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta
import pytz

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V71", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.1rem; line-height: 1.6; color: #EEEEEE; border: 1px solid #444; padding: 20px; background-color: #0A0A0A; border-radius: 5px; }
    .bull-text { color: #00FF00 !important; font-weight: bold; }
    .bear-text { color: #FF4B4B !important; font-weight: bold; }
    .legend-box { padding: 8px; border: 1px solid #333; background: #111; font-size: 0.75rem; color: #BBB; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- POMOĆNE FUNKCIJE ---
def get_ng_price():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()
        price = r['chart']['result'][0]['meta']['regularMarketPrice']
        prev = r['chart']['result'][0]['meta']['previousClose']
        return price, ((price - prev) / prev) * 100
    except: return 0.0, 0.0

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return df.iloc[-1, -1]
    except: return 0.0

def get_countdown(day_idx, hour, minute):
    now = datetime.now(pytz.timezone('Europe/Zagreb'))
    days_to_target = (day_idx - now.weekday()) % 7
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_to_target)
    if now > target: target += timedelta(days=7)
    diff = target - now
    return f"{diff.days}d {diff.seconds // 3600}h {(diff.seconds // 60) % 60}m"

# --- SIDEBAR: KONTROLA ---
with st.sidebar:
    st.header("⚡ Sniper Hub")
    if st.button("🔄 OSVJEŽI RADAR"):
        st.cache_data.clear()
        st.rerun()
    
    price, pct = get_ng_price()
    st.metric("Henry Hub Live", f"${price:.3f}", f"{pct:+.2f}%")
    
    st.markdown("---")
    with st.form("master_input"):
        st.subheader("🏛️ COT Data")
        st.write(f"**COT Countdown:** {get_countdown(4, 21, 30)}")
        c1, c2 = st.columns(2)
        mm_l = c1.number_input("MM Long", value=288456)
        mm_s = c2.number_input("MM Short", value=424123)
        com_l = c1.number_input("Comm Long", value=512000)
        com_s = c2.number_input("Comm Short", value=380000)
        
        st.markdown("---")
        st.subheader("🛢️ EIA Storage")
        st.write(f"**EIA Countdown:** {get_countdown(3, 16, 30)}")
        eia_val = st.number_input("Current Storage (Bcf)", value=3375)
        eia_chg = st.number_input("Net Change (Bcf)", value=-38)
        eia_5y = st.number_input("5y Average (Bcf)", value=3317)
        
        st.form_submit_button("SINKRONIZIRAJ")

# --- KALKULACIJE ---
ao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

mm_net = mm_l - mm_s
com_net = com_l - com_s
eia_diff = eia_val - eia_5y
eia_pct = (eia_diff / eia_5y) * 100

# --- 1. EXECUTIVE SUMMARY ---
st.subheader("📋 Executive Strategic Summary")
s_color = "bull-text" if eia_diff < 0 else "bear-text"
w_bias = "BULLISH" if (ao < 0 or nao < 0 or pna > 0) else "BEARISH"

st.markdown(f"""
<div class='summary-narrative'>
    Henry Hub: <strong>${price:.3f}</strong>. Managed Money Neto: <strong>{mm_net:+,}</strong> | Commercials Neto: <strong>{com_net:+,}</strong>.<br>
    Zalihe: <strong>{eia_val} Bcf</strong> (Promjena: <strong>{eia_chg:+} Bcf</strong>). 
    Odstupanje od 5y prosjeka: <span class='{s_color}'><strong>{eia_diff:+} Bcf ({eia_pct:+.2f}%)</strong></span>.<br>
    Weather Bias: <strong>{w_bias}</strong> (AO: {ao:.2f}, NAO: {nao:.2f}, PNA: {pna:.2f}). 
    {'Korelacija hladnoće i deficita zaliha stvara asimetriju.' if (eia_diff < 0 and ao < 0) else 'Tržište je u stanju ravnoteže ili medvjeđem trendu.'}
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA MAPS ---
st.subheader("🌡️ Weather Radar")
t1, t2 = st.tabs(["TEMPERATURA", "PADALINE"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Forecast")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Forecast")

# --- 3. INDEX SPAGHETTI (TRIPLE LAYOUT) ---
st.subheader("📈 Index Forecast Trends")
idx_c1, idx_c2, idx_c3 = st.columns(3)

def draw_spag(col, title, val, url, logic_bull, logic_bear):
    with col:
        st.image(url)
        bias = "BULLISH" if (val < 0 if title != "PNA" else val > 0) else "BEARISH"
        st.markdown(f"**{title} Index: {val:.2f}** (<span class='{'bull-text' if bias == 'BULLISH' else 'bear-text'}'>{bias}</span>)", unsafe_allow_html=True)
        st.markdown(f"<div class='legend-box'>Crna linija:<br><strong>Ispod 0</strong> = {logic_bull}<br><strong>Iznad 0</strong> = {logic_bear}</div>", unsafe_allow_html=True)

draw_spag(idx_c1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "Hladno (BULL)", "Toplo (BEAR)")
draw_spag(idx_c2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "Hladno (BULL)", "Toplo (BEAR)")
draw_spag(idx_c3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "Toplo (BEAR)", "Hladno (BULL)")

# --- 4. EIA VISUALIZATION ---
st.subheader("🛢️ EIA Storage Analysis")
f1, f2, f3 = st.columns(3)
f1.metric("Storage", f"{eia_val} Bcf", f"{eia_chg} Bcf", delta_color="inverse")
f2.metric("vs 5y Average", f"{eia_diff:+} Bcf", f"{eia_pct:+.2f}%", delta_color="inverse")
with f3:
    st.markdown(f"**Sentiment:** <h2 class='{s_color}'>{'BULLISH' if eia_diff < 0 else 'BEARISH'}</h2>", unsafe_allow_html=True)
