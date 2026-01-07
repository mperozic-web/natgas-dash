import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V22", layout="wide")

# Moderni, sitniji UI optimiziran za mobitel
st.markdown("""
    <style>
    .reportview-container { background: #fcfcfc; }
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; font-weight: 800; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #eee; }
    h3 { font-size: 1rem !important; color: #1a1a1a; border-left: 4px solid #007BFF; padding-left: 10px; margin: 20px 0 10px 0; }
    .summary-box { padding: 15px; border-radius: 10px; border: 1px solid #007BFF; background-color: #f0f7ff; margin-bottom: 20px; }
    .bias-tag { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9rem; }
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

ao = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia_data(EIA_API_KEY)

# --- UI: COT INPUT ---
with st.sidebar:
    st.header("🏛️ COT Manual Entry")
    st.caption("Data source: Tradingster Legacy Futures")
    nc_l = st.number_input("Non-Comm Long", value=288456)
    nc_s = st.number_input("Non-Comm Short", value=424123)
    c_l = st.number_input("Commercial Long", value=512000)
    c_s = st.number_input("Commercial Short", value=380000)
    nr_l = st.number_input("Retail Long", value=54120)
    nr_s = st.number_input("Retail Short", value=32100)
    
    nc_net = nc_l - nc_s
    comm_net = c_l - c_s
    
    # COT BIAS LOGIC
    if nc_net < -150000 and comm_net > 100000:
        cot_bias, cot_color = "BULLISH (Squeeze Play)", "green"
    elif nc_net > 100000 and comm_net < -100000:
        cot_bias, cot_color = "BEARISH (Distribution)", "red"
    else:
        cot_bias, cot_color = "NEUTRAL", "gray"

# --- 1. EXECUTIVE SUMMARY (Vrh aplikacije) ---
st.subheader("📋 Executive Summary")
# Sinteza svih podataka
meteo_bullish = (ao < -0.5 or nao < -0.5 or pna > 0.5)
storage_bullish = (storage and storage['diff_5y'] < 0)
cot_bullish = (nc_net < -150000)

summary_text = ""
if meteo_bullish and storage_bullish and cot_bullish:
    summary_text = "HIGH CONVICTION LONG. Fundamenti (EIA), Meteo (NOAA) i Pozicioniranje (COT) su usklađeni za snažan rast. Oportunitetni trošak čekanja je visok."
elif not meteo_bullish and not storage_bullish:
    summary_text = "BEARISH BIAS. Zalihe su u suficitu, a meteo prognoza ne podržava potražnju. Fokus na Short prilike."
else:
    summary_text = "DIVERGENCIJA SIGNALA. Tržište je u tranziciji. Potrebna potvrda 12z modela za smjer. Scalp trading preporučen."

st.markdown(f"""
    <div class="summary-box">
        <strong>Strateški Zaključak:</strong> {summary_text}<br><br>
        <span class="bias-tag" style="background-color: {'#dcfce7' if meteo_bullish else '#fee2e2'}">NOAA: {'BULL' if meteo_bullish else 'BEAR'}</span>
        <span class="bias-tag" style="background-color: {'#dcfce7' if storage_bullish else '#fee2e2'}">EIA: {'BULL' if storage_bullish else 'BEAR'}</span>
        <span class="bias-tag" style="background-color: {'#dcfce7' if cot_bullish else '#fee2e2'}">COT: {cot_bias}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# 2. RADAR: TEMPERATURE & SNOW
st.subheader("🗺️ Weather Radar & Snow Cover")
r1, r2 = st.columns(2)
with r1:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14 Day Outlook", use_container_width=True)
with r2:
    # Stabilniji link za Snow Depth (NOHRSC)
    st.image("https://www.nohrsc.noaa.gov/snow_model/images/full/National/nsm_depth/latest_nsm_depth_National.jpg", caption="Current Snow Depth (USA)", use_container_width=True)

st.markdown("---")

# 3. ATMOSPHERIC TRENDS (Spaghetti vs Metrika)
st.subheader("📈 Atmospheric Trends & Real-time Indices")
st.caption("Razlika: Brojka (Metrika) je trenutno stanje, Špageti su ansambl prognoza budućnosti.")

v1, v2, v3 = st.columns(3)
with v1:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif")
    st.metric("AO Index", f"{ao:.2f}", "BULLISH" if ao < -0.5 else "BEARISH")
    st.info("AO (-) = Hladnoća bježi s Arktika u SAD.")

with v2:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif")
    st.metric("NAO Index", f"{nao:.2f}", "BULLISH" if nao < -0.5 else "BEARISH")
    st.info("NAO (-) = Blokada Istoka (Northeast).")

with v3:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif")
    st.metric("PNA Index", f"{pna:.2f}", "BULLISH" if pna > 0.5 else "BEARISH")
    st.info("PNA (+) = Hladnoća u Midwestu.")

st.markdown("---")

# 4. EIA STORAGE (MODERNE BOJE)
st.subheader("🛢️ EIA Storage Intelligence")
if storage:
    e1, e2, e3 = st.columns(3)
    e1.metric("Aktualne Zalihe", f"{storage['curr']} Bcf", f"{storage['chg']} Bcf")
    
    # Boja: Bullish (Zelena) ako je storage < 5y Avg, Bearish (Crvena) ako je > 5y Avg
    # 'inverse' parametar u Streamlitu: rast (plus) je crven, pad (minus) je zelen. Idealno za zalihe.
    e2.metric("vs 5y Average", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")
    
    with e3:
        now = datetime.now(timezone.utc)
        target = (now + timedelta(days=(3 - now.weekday()) % 7)).replace(hour=15, minute=30, second=0)
        if now >= target: target += timedelta(days=7)
        diff = target - now
        st.warning(f"Iduća EIA za: {int(diff.total_seconds()//3600)}h {int((diff.total_seconds()%3600)//60)}m")
