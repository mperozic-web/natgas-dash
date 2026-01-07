import streamlit as st
import pandas as pd
import requests
import io
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V38", layout="wide")

# --- KONTROLA OSVJEŽAVANJA ---
with st.sidebar:
    st.header("⚙️ Sustav")
    pause_refresh = st.checkbox("Pauziraj osvježavanje (Lock UI)", value=False)
    
if not pause_refresh:
    st.markdown("<head><meta http-equiv='refresh' content='120'></head>", unsafe_allow_html=True)

# STEALTH CSS
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    header, [data-testid="stHeader"] { background-color: #000000 !important; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 8px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; margin-bottom: 35px; background-color: #0A0A0A; }
    .status-box { padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.9rem; border: 1px solid #444; }
    .bull-text { color: #00FF00 !important; border-color: #00FF00 !important; }
    .bear-text { color: #FF4B4B !important; border-color: #FF4B4B !important; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    .stButton>button { width: 100%; background-color: #007BFF; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- DOHVAT PODATAKA ---
def get_ng_live():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers={'User-Agent': 'Mozilla/5.0'})
        m = r.json()['chart']['result'][0]['meta']
        return m['regularMarketPrice'], ((m['regularMarketPrice'] - m['previousClose']) / m['previousClose']) * 100
    except: return 0.0, 0.0

@st.cache_data(ttl=600)
def get_noaa_h(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        col = df.columns[-1]
        v = df[col].tolist()
        return {"now": v[-1], "y": v[-2], "w": v[-8]}
    except: return {"now": 0.0, "y": 0.0, "w": 0.0}

@st.cache_data(ttl=3600)
def get_eia():
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {"api_key": EIA_API_KEY, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 50}
        r = requests.get(url, params=params).json()
        df = pd.DataFrame(r['response']['data'])
        df['val'] = df['value'].astype(int)
        c = df.iloc[0]['val']
        diff = c - int(df['val'].mean())
        return {"curr": c, "chg": c - df.iloc[1]['val'], "diff_5y": diff, "date": df.iloc[0]['period']}
    except: return None

# --- SIDEBAR: LIVE PRICE & COT FORM ---
with st.sidebar:
    st.markdown("---")
    st.header("⚡ Live Market")
    price, pct = get_ng_live()
    st.metric("Natural Gas Live", f"${price:.3f}", f"{pct:+.2f}%")
    
    st.markdown("---")
    with st.form("cot_form"):
        st.header("🏛️ COT Data Center")
        nc_l = st.number_input("NC Long", value=288456)
        nc_s = st.number_input("NC Short", value=424123)
        c_l = st.number_input("Comm Long", value=512000)
        c_s = st.number_input("Comm Short", value=380000)
        nr_l = st.number_input("Retail Long", value=54120)
        nr_s = st.number_input("Retail Short", value=32100)
        submitted = st.form_submit_button("POTVRDI I ANALIZIRAJ")

    st.header("📉 Futures Curve")
    f1 = st.number_input("M1 (Spot):", value=price if price > 0 else 2.50)
    f2 = st.number_input("M2 (Forward):", value=2.65)
    spread = f1 - f2
    struct = "BACKWARDATION" if spread > 0 else "CONTANGO"
    st.write(f"Struktura: **{struct}**")

# --- ANALIZA ---
ao_d = get_noaa_h("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao_d = get_noaa_h("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna_d = get_noaa_h("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia()

def get_color_logic(val, itype):
    if itype in ["AO", "NAO"]:
        bias = "BULLISH" if val < -0.4 else "BEARISH" if val > 0.4 else "NEUTRAL"
    else:
        bias = "BULLISH" if val > 0.4 else "BEARISH" if val < -0.4 else "NEUTRAL"
    return bias, "bull-text" if bias == "BULLISH" else "bear-text" if bias == "BEARISH" else ""

ao_b, ao_c = get_color_logic(ao_d['now'], "AO")
nao_b, nao_c = get_color_logic(nao_d['now'], "NAO")

# --- 1. EXECUTIVE STRATEGIC NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
meteo_st = "BULLISH" if (ao_b == "BULLISH" or nao_b == "BULLISH") else "BEARISH"
stor_st = "BULLISH" if (storage and storage['diff_5y'] < 0) else "BEARISH"

sq_msg = ""
if nc_net < -150000 and ao_d['now'] < ao_d['y'] and meteo_st == "BULLISH":
    sq_msg = "Kritičan **SHORT SQUEEZE** rizik. NC je ekstremno kratak dok atmosferski moment (AO) ubrzava u minus."

narrative = f"""
NG Cijena (**${price:.3f}**) je pod utjecajem **{meteo_st}** trenda. 
AO indeks ({ao_d['now']:.2f}) trenutačno **{'hladniji' if ao_d['now'] < ao_d['y'] else 'topliji'}** (vs yest: {ao_d['now']-ao_d['y']:+.2f}, vs week: {ao_d['now']-ao_d['w']:+.2f}). 
Zalihe: **{stor_st}** ({storage['diff_5y']:+} Bcf vs 5y Avg). {sq_msg}
**Strategija:** WPC karte ispod pokazuju točan pomak u prognozi. Plava boja na WPC kartama znači da modeli postaju agresivno hladniji.
"""
st.markdown(f"<div class='summary-narrative'>{narrative}</div>", unsafe_allow_html=True)

# --- 2. WPC CHANGE MAPS (AS REQUESTED) ---
st.subheader("🗺️ WPC 24h Temperature Change Radar")

c1, c2 = st.columns(2)
with c1:
    st.image("https://www.wpc.ncep.noaa.gov/exper/change/f024_f048_t_change.gif", caption="Promjena prognoze Day 1 -> Day 2")
    st.image("https://www.wpc.ncep.noaa.gov/exper/change/f048_f072_t_change.gif", caption="Promjena prognoze Day 2 -> Day 3")
with c2:
    st.image("https://www.wpc.ncep.noaa.gov/exper/change/f072_f096_t_change.gif", caption="Promjena prognoze Day 3 -> Day 4")
    st.image("https://www.wpc.ncep.noaa.gov/exper/change/f096_f120_t_change.gif", caption="Promjena prognoze Day 4 -> Day 5")

st.markdown("---")

# --- 3. ATMOSPHERIC TRENDS ---
st.subheader("📈 Index Forecast Trends & Momentum")
v1, v2, v3 = st.columns(3)

def draw_idx(col, title, d, b, c_class, inv):
    with col:
        st.image(f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/{title.lower()}.sprd2.gif" if title=="AO" else f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/{title.lower()}.sprd2.gif")
        st.markdown(f"**{title} INDEX**")
        st.markdown(f"<span style='font-size:1.8rem; font-weight:800;'>{d['now']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"<span class='status-box {c_class}'>{b}</span>", unsafe_allow_html=True)
        y_d = d['now']-d['y']
        y_col = "#00FF00" if (y_d < 0 if inv else y_d > 0) else "#FF4B4B"
        st.markdown(f"<div style='font-size:0.85rem; margin-top:10px;'><span style='color:{y_col}'>vs yest: {y_d:+.2f}</span> | vs week: {d['now']-d['w']:+.2f}</div>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao_d, ao_b, ao_c, True)
draw_idx(v2, "NAO", nao_d, nao_b, nao_c, True)
draw_idx(v3, "PNA", pna_d, *get_color_logic(pna_d['now'], "PNA"), False)

# --- 4. EIA & COT COUNTDOWN ---
st.subheader("🛢️ Storage & Reporting")
e1, e2 = st.columns(2)
with e1:
    st.metric(f"EIA vs 5y AVG ({stor_st})", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")
with e2:
    def get_cd(d, h, m):
        n = datetime.now(timezone.utc)
        t = (n + timedelta(days=(d - n.weekday()) % 7)).replace(hour=h, minute=m, second=0)
        if n >= t: t += timedelta(days=7)
        df = t - n
        return f"{int(df.total_seconds()//3600)}h {int((df.total_seconds()%3600)//60)}m"
    st.write(f"⌛ COT Countdown: {get_cd(4, 20, 30)}")
    st.write(f"⌛ EIA Countdown: {get_cd(3, 15, 30)}")
