import streamlit as st
import pandas as pd
import requests
import io
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA I AUTO-REFRESH (120s) ---
st.set_page_config(page_title="NatGas Sniper V31", layout="wide")

st.markdown("<head><meta http-equiv='refresh' content='120'></head>", unsafe_allow_html=True)

# STEALTH CSS (Bez okvira, visok kontrast)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    header, [data-testid="stHeader"] { background-color: #000000 !important; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 8px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; margin-bottom: 35px; background-color: #0A0A0A; }
    .status-tag { padding: 2px 10px; border-radius: 4px; font-weight: bold; font-size: 0.95rem; }
    .bull-color { color: #00FF00; }
    .bear-color { color: #FF4B4B; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- HELPER FUNKCIJE ---
def get_ng_live():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers={'User-Agent': 'Mozilla/5.0'})
        meta = r.json()['chart']['result'][0]['meta']
        return meta['regularMarketPrice'], ((meta['regularMarketPrice'] - meta['previousClose']) / meta['previousClose']) * 100
    except: return 0.0, 0.0

@st.cache_data(ttl=600)
def get_noaa_data(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        col = df.columns[-1]
        v = df[col].tolist()
        return {"now": v[-1], "y": v[-2], "w": v[-8]}
    except: return {"now": 0.0, "y": 0.0, "w": 0.0}

def get_countdown(day, hour, minute):
    now = datetime.now(timezone.utc)
    target = (now + timedelta(days=(day - now.weekday()) % 7)).replace(hour=hour, minute=minute, second=0)
    if now >= target: target += timedelta(days=7)
    diff = target - now
    return f"{int(diff.total_seconds()//3600)}h {int((diff.total_seconds()%3600)//60)}m"

# --- SIDEBAR: MARKET & COT ---
with st.sidebar:
    st.header("⚡ Live Market")
    price, pct = get_ng_live()
    st.metric("Natural Gas Live", f"${price:.3f}", f"{pct:+.2f}%")
    
    st.markdown("---")
    st.header("🏛️ COT Data Center")
    st.info(f"⌛ COT Countdown: {get_countdown(4, 20, 30)}") # Petak 20:30 UTC
    nc_l = st.number_input("NC Long", value=288456)
    nc_s = st.number_input("NC Short", value=424123)
    c_l = st.number_input("Comm Long", value=512000)
    c_s = st.number_input("Comm Short", value=380000)
    nr_l = st.number_input("Retail Long", value=54120)
    nr_s = st.number_input("Retail Short", value=32100)
    
    st.markdown("---")
    st.header("📉 Futures Curve")
    f1 = st.number_input("M1 (Spot):", value=price if price > 0 else 2.50)
    f2 = st.number_input("M2 (Forward):", value=2.65)
    spread = f1 - f2
    struct = "BACKWARDATION" if spread > 0 else "CONTANGO"
    st.write(f"Struktura: **{struct}**")

# --- DOHVAT PODATAKA ---
ao_d = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao_d = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna_d = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = requests.get("https://api.eia.gov/v2/natural-gas/stor/wkly/data/", params={"api_key": EIA_API_KEY, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 50}).json()

# --- LOGIKA ANALIZE ---
def get_bias_color(val, itype):
    if itype in ["AO", "NAO"]:
        bias = "BULLISH" if val < -0.4 else "BEARISH" if val > 0.4 else "NEUTRAL"
    else:
        bias = "BULLISH" if val > 0.4 else "BEARISH" if val < -0.4 else "NEUTRAL"
    return bias, ("#00FF00" if bias == "BULLISH" else "#FF4B4B" if bias == "BEARISH" else "#AAAAAA")

ao_b, ao_c = get_bias_color(ao_d['now'], "AO")
nao_b, nao_c = get_bias_color(nao_d['now'], "NAO")

# EXECUTIVE SUMMARY DESKRIPCIJA
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
ao_vel = ao_d['now'] - ao_d['y']
meteo_st = "BULLISH" if (ao_b == "BULLISH" or nao_b == "BULLISH") else "BEARISH"

# Squeeze logic
squeeze_text = ""
if nc_net < -150000 and ao_vel < 0:
    squeeze_text = "Analiza pozicioniranja ukazuje na visok rizik od **SHORT SQUEEZEA**. Institucije su u ekstremnom shortu, a AO indeks ubrzano pada, što prisiljava tržište na reakciju."
elif nc_net > 100000 and ao_vel > 0:
    squeeze_text = "Rizik od **LONG SQUEEZEA**. Tržište je zasićeno kupcima dok atmosferski moment slabi."

narrative = f"""
Atmosfera je u **{meteo_st}** trendu. AO ({ao_d['now']:.2f}) trenutno {'ubrzava prodor' if ao_vel < 0 else 'gubi zamah'} (vs jučer: {ao_vel:+.2f}). 
COT Sentiment: NC Net je {nc_net:,}. {squeeze_text}
Strategija: Uoči sinkronizaciju AO i NAO špageta za potvrdu trajanja hladnoće.
"""
st.markdown(f"<div class='summary-narrative'>{narrative}</div>", unsafe_allow_html=True)

# --- NOAA RADAR ---
st.subheader("🗺️ NOAA Temperature Radar")
c1, c2 = st.columns(2)
c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="SHORT TERM")
c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="LONG TERM")

# --- INDICES ---
st.subheader("📈 Index Forecast Trends")
v1, v2, v3 = st.columns(3)

def draw_metric(col, title, d, itype, inv):
    with col:
        st.image(f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/{title.lower()}.sprd2.gif" if title=="AO" else f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/{title.lower()}.sprd2.gif")
        b, c = get_bias_color(d['now'], itype)
        st.markdown(f"**{title} INDEX**")
        st.markdown(f"<span style='font-size:1.8rem; font-weight:800;'>{d['now']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:{c}; font-weight:bold; border:1px solid {c}; padding:2px 5px;'>{b}</span>", unsafe_allow_html=True)
        y_d, w_d = d['now']-d['y'], d['now']-d['w']
        y_col = "#00FF00" if (y_d < 0 if inv else y_d > 0) else "#FF4B4B"
        st.markdown(f"<div style='font-size:0.85rem; margin-top:5px;'><span style='color:{y_col}'>vs yest: {y_d:+.2f}</span> | vs week: {w_d:+.2f}</div>", unsafe_allow_html=True)

draw_metric(v1, "AO", ao_d, "AO", True)
draw_metric(v2, "NAO", nao_d, "NAO", True)
draw_metric(v3, "PNA", pna_d, "PNA", False)

# --- EIA ---
st.subheader("🛢️ EIA Storage Intelligence")
if storage:
    df_e = pd.DataFrame(storage['response']['data'])
    df_e['val'] = df_e['value'].astype(int)
    curr_e = df_e.iloc[0]['val']
    diff_5y = curr_e - int(df_e['val'].mean())
    e1, e2, e3 = st.columns(3)
    e1.metric("ZALIHE", f"{curr_e} Bcf", f"{curr_e - df_e.iloc[1]['val']} Bcf")
    st_b = "BULLISH" if diff_5y < 0 else "BEARISH"
    e2.metric(f"vs 5y AVG ({st_b})", f"{diff_5y:+} Bcf", delta_color="inverse")
    e3.info(f"⌛ EIA Countdown: {get_countdown(3, 15, 30)}")
