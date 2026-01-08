import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta
import pytz

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V68", layout="wide")

# CSS: Bez em-dasha, maksimalni kontrast
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.1rem; line-height: 1.6; color: #EEEEEE; border: 1px solid #444; padding: 20px; background-color: #0A0A0A; border-radius: 5px; }
    .bull-text { color: #00FF00 !important; font-weight: bold; }
    .bear-text { color: #FF4B4B !important; font-weight: bold; }
    .legend-box { padding: 8px; border: 1px solid #333; background: #111; font-size: 0.75rem; color: #BBB; margin-top: 5px; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- CORE LOGIKA ---
def get_ng_price():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()
        price = r['chart']['result'][0]['meta']['regularMarketPrice']
        prev = r['chart']['result'][0]['meta']['previousClose']
        return price, ((price - prev) / prev) * 100
    except: return 0.0, 0.0

def get_eia_storage_clean():
    """Precizan dohvat tjednih zaliha (Total Stocks)"""
    try:
        # Koristimo facete za eliminaciju krivih serija podataka
        url = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=52"
        r = requests.get(url).json()['response']['data']
        curr = int(r[0]['value'])
        prev = int(r[1]['value'])
        # 5-year average (približno 52 tjedna)
        avg5y = sum(int(x['value']) for x in r[:52]) / 52
        return {"curr": curr, "chg": curr - prev, "v5y": curr - int(avg5y)}
    except: return None

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return df.iloc[-1, -1]
    except: return 0.0

def get_countdown():
    now = datetime.now(pytz.timezone('Europe/Zagreb'))
    days_to_fri = (4 - now.weekday()) % 7
    target = now.replace(hour=21, minute=30, second=0, microsecond=0) + timedelta(days=days_to_fri)
    if now > target: target += timedelta(days=7)
    diff = target - now
    return f"{diff.days}d {diff.seconds // 3600}h {(diff.seconds // 60) % 60}m"

# --- SIDEBAR: KONTROLA I UNOSI ---
with st.sidebar:
    st.header("⚡ Sniper Hub")
    if st.button("🔄 OSVJEŽI RADAR"):
        st.cache_data.clear()
        st.rerun()
    
    price, pct = get_ng_price()
    st.metric("Henry Hub", f"${price:.3f}", f"{pct:+.2f}%")
    
    st.markdown("---")
    with st.form("cot_entry"):
        st.subheader("🏛️ COT Intelligence")
        st.markdown(f"**Countdown:** {get_countdown()}")
        nc_l = st.number_input("MM Long", value=288456)
        nc_s = st.number_input("MM Short", value=424123)
        c_l = st.number_input("Commercial Long", value=512000)
        c_s = st.number_input("Commercial Short", value=380000)
        r_l = st.number_input("Retail Long", value=54120)
        r_s = st.number_input("Retail Short", value=32100)
        st.form_submit_button("SINKRONIZIRAJ")

# --- DATA ---
eia = get_eia_storage_clean()
ao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE SUMMARY ---
st.subheader("📋 Executive Strategic Summary")
nc_net = nc_l - nc_s
c_net = c_l - c_s
r_net = r_l - r_s
s_bias = "BULLISH" if (eia and eia['v5y'] < 0) else "BEARISH"

st.markdown(f"""
<div class='summary-narrative'>
    Tržište operira pri <strong>${price:.3f}</strong>. Managed Money neto: <strong>{nc_net:+,}</strong>. 
    Commercials neto: <strong>{c_net:+,}</strong> (Hedging status). Retail neto: <strong>{r_net:+,}</strong>.<br>
    Zalihe: <strong>{eia['curr'] if eia else 'ERR'} Bcf</strong> (<span class='{"bull-text" if s_bias == "BULLISH" else "bear-text"}'>{eia['v5y'] if eia else 'N/A':+} Bcf vs 5y Avg</span>).<br>
    Vrijeme: AO na <strong>{ao:.2f}</strong>. Kontekst: {'Hladnije (Potražnja raste)' if ao < 0 else 'Toplije (Potražnja pada)'}.
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA MAPS ---
st.subheader("🌡️ Temperature & Precipitation Forecast")
t_t, t_p = st.tabs(["TEMPERATURE", "PRECIPITATION"])
with t_t:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Temp")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Temp")
with t_p:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Prcp")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d Prcp")

# --- 3. INDEX SPAGHETTI (SIDE-BY-SIDE) ---
st.subheader("📈 Index Forecast Trends (AO, NAO, PNA)")
idx1, idx2, idx3 = st.columns(3)

def render_idx(col, title, val, url, logic):
    with col:
        st.image(url)
        bias = "BULLISH" if (val < 0 if title != "PNA" else val > 0) else "BEARISH"
        st.markdown(f"**{title}: {val:.2f}** (<span class='{'bull-text' if bias == 'BULLISH' else 'bear-text'}'>{bias}</span>)", unsafe_allow_html=True)
        st.markdown(f"<div class='legend-box'>{logic}<br><strong>Crna linija:</strong><br>Iznad 0 = Bearish<br>Ispod 0 = Bullish</div>", unsafe_allow_html=True)

render_idx(idx1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "Negativan AO = Arktički upad.")
render_idx(idx2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "Negativan NAO = Blokada na Atlantiku.")
render_idx(idx3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "Pozitivan PNA = Hladnoća na istoku.")

# --- 4. FUNDAMENTALS: EIA STORAGE ---
st.subheader("🛢️ EIA Storage Intelligence")
if eia:
    f1, f2, f3 = st.columns(3)
    f1.metric("Trenutne Zalihe", f"{eia['curr']} Bcf", f"{eia['chg']} Bcf", delta_color="inverse")
    f2.metric("vs 5y Average", f"{eia['v5y']:+} Bcf", delta_color="inverse")
    with f3:
        status = "BULLISH" if eia['v5y'] < 0 else "BEARISH"
        st.markdown(f"**Sentiment:** <h2 class='{'bull-text' if status == 'BULLISH' else 'bear-text'}'>{status}</h2>", unsafe_allow_html=True)
