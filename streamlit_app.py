import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V25", layout="wide")

# STEALTH CSS (Potpuno crna pozadina, bez okvira u boji)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    header, [data-testid="stHeader"] { background-color: #000000 !important; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 5px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #AAAAAA !important; }
    .stMetric { background-color: transparent; border: 1px solid #333; border-radius: 0px; padding: 10px; }
    .summary-text { font-size: 1.1rem; line-height: 1.6; color: #FFFFFF; border: 1px solid #444; padding: 20px; margin-bottom: 30px; }
    /* Sidebar styling */
    section[data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown p { color: #FFFFFF; }
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

# --- SIDEBAR: COT DATA CENTER ---
with st.sidebar:
    st.header("🏛️ COT DATA")
    nc_l = st.number_input("NC Long", value=288456)
    nc_s = st.number_input("NC Short", value=424123)
    c_l = st.number_input("Comm Long", value=512000)
    c_s = st.number_input("Comm Short", value=380000)
    nr_l = st.number_input("Retail Long", value=54120)
    nr_s = st.number_input("Retail Short", value=32100)
    
    nc_net = nc_l - nc_s
    comm_net = c_l - c_s
    nr_net = nr_l - nr_s

# --- ANALIZA ---
ao = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia_data(EIA_API_KEY)

# --- 1. EXECUTIVE STRATEGIC SUMMARY ---
st.subheader("📋 Executive Strategic Summary")

# Logika za deskriptivni sažetak
meteo_setup = "BULLISH" if (ao < -0.5 or nao < -0.5) else "BEARISH"
stor_setup = "BULLISH" if (storage and storage['diff_5y'] < 0) else "BEARISH"

# Squeeze Logic
squeeze_msg = ""
if nc_net < -150000 and nr_net < -10000 and meteo_setup == "BULLISH":
    squeeze_msg = "Detektiran je rizik od SHORT SQUEEZEA. Institucije i retail su u ekstremnom shortu dok atmosferski indeksi AO i NAO padaju, što sugerira da bi prva potvrda hladnoće na 12z runu mogla prisiliti medvjede na panično zatvaranje pozicija."
elif nc_net > 100000 and nr_net > 20000 and meteo_setup == "BEARISH":
    squeeze_msg = "Detektiran je rizik od LONG SQUEEZEA. Previše je optimizma na tržištu dok meteo radar pokazuje toplinu (Bearish), što bi moglo izazvati lančano aktiviranje stop-loss naloga prema dolje."
else:
    squeeze_msg = "Tržišno pozicioniranje je trenutno u ravnoteži bez ekstremnih pritisaka na jednu stranu."

summary_desc = f"""
Trenutna situacija na tržištu ukazuje na **{meteo_setup}** meteorološki trend (AO: {ao:.2f}, NAO: {nao:.2f}). 
Fundamenti zaliha su **{stor_setup}** u odnosu na petogodišnji prosjek ({storage['diff_5y']:+} Bcf). 
{squeeze_msg} 
Preporuka je pratiti AO špagete: ako se trend strmoglavljivanja nastavi, očekuj povećanu volatilnost.
"""

st.markdown(f"<div class='summary-text'>{summary_desc}</div>", unsafe_allow_html=True)

# --- 2. NOAA RADAR: SHORT vs LONG TERM ---
st.subheader("🗺️ NOAA Temperature Radar")
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="SHORT TERM (6-10 dana)")
with col_r2:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="LONG TERM (8-14 dana)")

st.markdown("---")

# --- 3. ATMOSPHERIC DRIVERS (SPAGHETTI TRENDS) ---
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
