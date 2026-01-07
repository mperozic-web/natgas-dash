import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V24", layout="wide")

# PROFESIONALNI UI CSS (Vraćanje na plavo/bijelo)
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    h2, h3 { color: #007BFF !important; font-weight: 800 !important; border-bottom: 2px solid #007BFF; padding-bottom: 5px; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 800 !important; color: #1E1E1E !important; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #555555 !important; }
    .stMetric { background-color: #F8F9FA; padding: 15px; border-radius: 8px; border: 1px solid #E0E0E0; }
    .summary-box { background-color: #E7F1FF; color: #084298; padding: 20px; border-radius: 10px; border: 1px solid #B6D4FE; margin-bottom: 25px; }
    .tag-bull { color: #155724; background-color: #d4edda; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .tag-bear { color: #721c24; background-color: #f8d7da; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
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

# --- SIDEBAR: POTPUNI COT INPUT ---
with st.sidebar:
    st.header("🏛️ COT DATA CENTER")
    st.write("Source: Tradingster Legacy")
    
    st.subheader("Managed Money (NC)")
    nc_l = st.number_input("Long", value=288456, key="nc_l")
    nc_s = st.number_input("Short", value=424123, key="nc_s")
    
    st.subheader("Commercial (Hedgers)")
    c_l = st.number_input("Long", value=512000, key="c_l")
    c_s = st.number_input("Short", value=380000, key="c_s")
    
    st.subheader("Retail (Non-Report)")
    nr_l = st.number_input("Long", value=54120, key="nr_l")
    nr_s = st.number_input("Short", value=32100, key="nr_s")
    
    nc_net = nc_l - nc_s
    comm_net = c_l - c_s
    nr_net = nr_l - nr_s

# --- ANALIZA ---
ao = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_val("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia_data(EIA_API_KEY)

# --- 1. EXECUTIVE SUMMARY ---
meteo_bull = (ao < -0.4 or nao < -0.4)
stor_bull = (storage and storage['diff_5y'] < 0)
cot_squeeze = (nc_net < -140000 and nr_net < -10000)

st.subheader("📋 Executive Summary")
summary_msg = "NEUTRAL"
if meteo_bull and stor_bull:
    summary_msg = "CONVICTION LONG: Meteo i zalihe podržavaju rast."
elif cot_squeeze and meteo_bull:
    summary_msg = "SQUEEZE ALERT: Ekstremni shortovi pod pritiskom dolaska hladnoće!"
elif not meteo_bull and not stor_bull:
    summary_msg = "BEARISH: Toplo vrijeme i višak zaliha."

st.markdown(f"""
    <div class="summary-box">
        <strong>Strateški Bias:</strong> {summary_msg}<br><br>
        NOAA: <span class="{'tag-bull' if meteo_bull else 'tag-bear'}">{'BULL' if meteo_bull else 'BEAR'}</span> | 
        EIA: <span class="{'tag-bull' if stor_bull else 'tag-bear'}">{'BULL' if stor_bull else 'BEAR'}</span> | 
        COT: <span class="{'tag-bull' if nc_net < 0 else 'tag-bear'}">{'NC Net: ' + str(nc_net)}</span> | 
        RETAIL: <span class="{'tag-bull' if nr_net < 0 else 'tag-bear'}">{'NR Net: ' + str(nr_net)}</span>
    </div>
    """, unsafe_allow_html=True)

# --- 2. NOAA RADAR ---
st.subheader("🗺️ Temperature Progression (Radar)")
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10 Day Outlook")
with col_r2:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14 Day Outlook")

st.markdown("---")

# --- 3. ATMOSPHERIC TRENDS ---
st.subheader("📈 Index Forecast Trends")
v1, v2, v3 = st.columns(3)
with v1:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif")
    st.metric("AO INDEX", f"{ao:.2f}", "BULLISH" if ao < -0.5 else "BEARISH", delta_color="inverse")
    st.caption("AO (-) = Hladnoća izlazi s Arktika.")
with v2:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif")
    st.metric("NAO INDEX", f"{nao:.2f}", "BULLISH" if nao < -0.5 else "BEARISH", delta_color="inverse")
    st.caption("NAO (-) = Blokada na Istoku SAD-a.")
with v3:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif")
    st.metric("PNA INDEX", f"{pna:.2f}", "BULLISH" if pna > 0.5 else "BEARISH")
    st.caption("PNA (+) = Hladnoća u Midwestu.")




st.markdown("---")

# --- 4. EIA STORAGE CONTROL ---
st.subheader("🛢️ EIA Storage Intelligence")
if storage:
    e1, e2, e3 = st.columns(3)
    e1.metric("Trenutne Zalihe", f"{storage['curr']} Bcf", f"{storage['chg']} Bcf")
    
    stor_label = "BULLISH" if storage['diff_5y'] < 0 else "BEARISH"
    e2.metric(f"vs 5y AVG ({stor_label})", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")
    
    with e3:
        now = datetime.now(timezone.utc)
        target = (now + timedelta(days=(3 - now.weekday()) % 7)).replace(hour=15, minute=30, second=0)
        if now >= target: target += timedelta(days=7)
        diff = target - now
        st.info(f"⌛ Iduća EIA za: {int(diff.total_seconds()//3600)}h {int((diff.total_seconds()%3600)//60)}m")
