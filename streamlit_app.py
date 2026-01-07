import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V19", layout="wide")

@st.cache_data(ttl=600)
def get_noaa_raw_val(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return float(df.iloc[-1].iloc[-1])
    except: return 0.0

@st.cache_data(ttl=3600)
def get_eia_storage_final(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {
            "api_key": api_key, "frequency": "weekly", "data[0]": "value",
            "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period",
            "sort[0][direction]": "desc", "length": 100
        }
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        df['val'] = df['value'].astype(int)
        curr = df.iloc[0]
        # Proksi za 5y avg (zadnjih 5 očitanja istog tjedna)
        avg_5y = int(df['val'].mean()) 
        return {"curr": curr['val'], "chg": curr['val'] - df.iloc[1]['val'], "diff_5y": curr['val'] - avg_5y, "date": curr['period']}
    except: return None

# CSS za čisti UI
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; font-weight: 800; color: #007BFF !important; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #333; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; border: 1px solid #eee; }
    h3 { font-size: 1.1rem !important; color: #000; border-left: 5px solid #007BFF; padding-left: 10px; margin-top: 20px; }
    .bias-box { padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 1.1rem; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- DOHVAT PODATAKA ---
ao_val = get_noaa_raw_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao_val = get_noaa_raw_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna_val = get_noaa_raw_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia_storage_final(EIA_API_KEY)

# --- UI DISPLAY ---
st.title("🛡️ NatGas Sniper V19.0 | High-Level Command")

# 1. MASTER BIAS (NA VRHU)
st.subheader("🏁 Global Master Bias Summary")
with st.expander("🏛️ COT Tjedni Unos (Tradingster)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    nc_long = col_c1.number_input("Non-Comm Long:", value=288456)
    nc_short = col_c2.number_input("Non-Comm Short:", value=424123)
    mm_net = nc_long - nc_short

b1, b2, b3 = st.columns(3)
with b1:
    meteo_bias = "BULLISH" if (ao_val < -0.5 or nao_val < -0.5 or pna_val > 0.5) else "BEARISH"
    st.markdown(f"<div class='bias-box'>🌍 METEO: {meteo_bias}</div>", unsafe_allow_html=True)
with b2:
    stor_bias = "BULLISH" if (storage and storage['diff_5y'] < 0) else "BEARISH"
    st.markdown(f"<div class='bias-box'>🛢️ STORAGE: {stor_bias}</div>", unsafe_allow_html=True)
with b3:
    cot_bias = "SQUEEZE RISK" if mm_net < -150000 else "BEARISH"
    st.markdown(f"<div class='bias-box'>🏛️ COT: {cot_bias}</div>", unsafe_allow_html=True)

st.markdown("---")

# 2. RADAR PROGRESIJE (TEMPERATURE & OBORINE)
st.subheader("🗺️ Forecast Radar (6-10d vs 8-14d)")
r1, r2 = st.columns(2)
r1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10 Day Temperature")
r2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14 Day Temperature")

p1, p2 = st.columns(2)
p1.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14 Day Precipitation")
p2.image("https://www.natice.noaa.gov/pub/ims/ims_gif/DATA/cursnow.gif", caption="Current Snow Cover (USA)")

st.markdown("---")

# 3. SPAGHETTI TRENDS & METRIKA (GRADACIJA I NAPOMENA)
st.subheader("📈 Atmospheric Forecast Trends")
v1, v2, v3 = st.columns(3)

with v1:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", caption="AO Forecast")
    ao_status = "EKSTREMNO BULLISH" if ao_val < -2.0 else "JAKO BULLISH" if ao_val < -1.0 else "BULLISH" if ao_val < -0.4 else "BEARISH"
    st.metric("AO Vrijednost", f"{ao_val:.2f}", ao_status)
    st.info("Napomena: Negativan AO znači da polarni vrtlog puca i hladnoća bježi na jug u SAD.")

with v2:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", caption="NAO Forecast")
    nao_status = "EKSTREMNO BULLISH" if nao_val < -1.5 else "JAKO BULLISH" if nao_val < -0.8 else "BULLISH" if nao_val < -0.4 else "BEARISH"
    st.metric("NAO Vrijednost", f"{nao_val:.2f}", nao_status)
    st.info("Napomena: Negativan NAO stvara blokadu iznad Grenlanda koja hladnoću drži nad Northeast regijom.")

with v3:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", caption="PNA Forecast")
    pna_status = "JAKO BULLISH" if pna_val > 1.2 else "BULLISH" if pna_val > 0.5 else "BEARISH"
    st.metric("PNA Vrijednost", f"{pna_val:.2f}", pna_status)
    st.info("Napomena: Pozitivan PNA znači greben na zapadu koji spušta hladni zrak u Midwest i na Istok.")

st.markdown("---")

# 4. EIA COMMAND CENTER
st.subheader("🛢️ EIA Storage Mirror")
if storage:
    e1, e2, e3 = st.columns(3)
    e1.metric("Trenutne Zalihe", f"{storage['curr']} Bcf", f"{storage['chg']} Bcf")
    e2.metric("vs 5y Average", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")
    
    # Countdown
    now = datetime.now(timezone.utc)
    target = (now + timedelta(days=(3 - now.weekday()) % 7)).replace(hour=15, minute=30, second=0)
    if now >= target: target += timedelta(days=7)
    diff = target - now
    e3.warning(f"Iduća EIA objava za: {int(diff.total_seconds()//3600)}h {int((diff.total_seconds()%3600)//60)}m")
else:
    st.error("EIA API trenutno nedostupan.")
