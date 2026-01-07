import streamlit as st
import pandas as pd
import requests
import io
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V35", layout="wide")

# --- KONTROLA OSVJEŽAVANJA ---
with st.sidebar:
    st.header("⚙️ Sustav")
    pause_refresh = st.checkbox("Pauziraj osvježavanje (Lock UI)", value=False)
    
if not pause_refresh:
    st.markdown("<head><meta http-equiv='refresh' content='120'></head>", unsafe_allow_html=True)

# STEALTH CSS (Potpuno crno, visoki kontrast)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    header, [data-testid="stHeader"] { background-color: #000000 !important; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 8px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; margin-bottom: 35px; background-color: #0A0A0A; }
    .legend-text { font-size: 0.85rem; color: #999999; margin-top: 5px; font-style: italic; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    .stButton>button { width: 100%; background-color: #007BFF; color: white; border-radius: 5px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- POMOĆNE FUNKCIJE ---
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

# --- SIDEBAR: CIJENA, COT & FUTURES ---
with st.sidebar:
    st.markdown("---")
    st.header("⚡ Live Price")
    price, pct = get_ng_live()
    st.metric("Natural Gas Live", f"${price:.3f}", f"{pct:+.2f}%")
    
    st.markdown("---")
    with st.form("cot_form"):
        st.header("🏛️ COT Data Center")
        nc_l = st.number_input("NC Long", value=288456, key="nc_l_s")
        nc_s = st.number_input("NC Short", value=424123, key="nc_s_s")
        c_l = st.number_input("Comm Long", value=512000, key="c_l_s")
        c_s = st.number_input("Comm Short", value=380000, key="c_s_s")
        nr_l = st.number_input("Retail Long", value=54120, key="nr_l_s")
        nr_s = st.number_input("Retail Short", value=32100, key="nr_s_s")
        submitted = st.form_submit_button("POTVRDI I ANALIZIRAJ")
    
    st.markdown("---")
    st.header("📉 Futures Curve")
    f1 = st.number_input("M1 (Current):", value=price if price > 0 else 2.50)
    f2 = st.number_input("M2 (Forward):", value=2.65)
    spread = f1 - f2
    struct = "BACKWARDATION" if spread > 0 else "CONTANGO"
    st.write(f"Struktura: **{struct}**")

# --- ANALIZA ---
ao_d = get_noaa_h("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao_d = get_noaa_h("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna_d = get_noaa_h("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia()

def get_logic(val, yest, week, itype):
    if itype in ["AO", "NAO"]:
        bias = "BULLISH" if val < -0.4 else "BEARISH" if val > 0.4 else "NEUTRAL"
        mom = "ubrzava" if val < yest else "usporava"
    else:
        bias = "BULLISH" if val > 0.4 else "BEARISH" if val < -0.4 else "NEUTRAL"
        mom = "ubrzava" if val > yest else "usporava"
    color = "#00FF00" if bias == "BULLISH" else "#FF4B4B" if bias == "BEARISH" else "#AAAAAA"
    return bias, color, mom

ao_b, ao_c, ao_m = get_logic(ao_d['now'], ao_d['y'], ao_d['w'], "AO")
nao_b, nao_c, nao_m = get_logic(nao_d['now'], nao_d['y'], nao_d['w'], "NAO")

# --- 1. EXECUTIVE STRATEGIC NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
nr_net = nr_l - nr_s
meteo_st = "BULLISH" if (ao_b == "BULLISH" or nao_b == "BULLISH") else "BEARISH"
stor_st = "BULLISH" if (storage and storage['diff_5y'] < 0) else "BEARISH"

sq_msg = ""
if nc_net < -150000 and ao_m == "ubrzava" and meteo_st == "BULLISH":
    sq_msg = "Detektiran je **SHORT SQUEEZE** moment. Managed Money i Retail su u ekstremnom shortu, dok AO i NAO ubrzano tonu u minus, što je recept za nasilni rast."
elif nc_net > 100000 and ao_m == "usporava":
    sq_msg = "Rizik od **LONG SQUEEZEA**. Tržište je zasićeno kupcima uz vizualno slabljenje plavih zona na radaru."

narrative = f"""
Cijena NG (**${price:.3f}**) operira u **{meteo_st}** meteo okruženju. 
AO indeks ({ao_d['now']:.2f}) trenutno **{ao_m}** (vs jučer: {ao_d['now']-ao_d['y']:+.2f}). 
Zalihe plina su **{stor_st}** ({storage['diff_5y']:+} Bcf vs 5y Avg). 
{sq_msg} 
**Strateški uvid:** Usporedi 'Current Outlook' s '24h Trend' kartama. Ako su trend karte plave, prognoza postaje hladnija iz sata u sat, bez obzira na trenutnu boju Outlook karata.
"""
st.markdown(f"<div class='summary-narrative'>{narrative}</div>", unsafe_allow_html=True)

# --- 2. NOAA RADAR: CURRENT vs 24H TREND ---
st.subheader("🗺️ Temperature Radar: Current Outlook vs 24h Forecast Trend")
col1, col2 = st.columns(2)
with col1:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="DANAŠNJI OUTLOOK (6-10 dana)")
    # 24h Trend karta (pokazuje je li danas hladnije ili toplije nego jučer)
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.diff.new.gif", caption="24H TREND (ŠTO SE PROMIJENILO OD JUČER - 6-10d)")

with col2:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="DANAŠNJI OUTLOOK (8-14 dana)")
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.diff.new.gif", caption="24H TREND (ŠTO SE PROMIJENILO OD JUČER - 8-14d)")

st.markdown("---")

# --- 3. ATMOSPHERIC TRENDS & VELOCITY ---
st.subheader("📈 Index Forecast Trends & Velocity")
v1, v2, v3 = st.columns(3)

def draw_metric(col, title, d, bias, color, inv):
    with col:
        st.image(f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/{title.lower()}.sprd2.gif" if title=="AO" else f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/{title.lower()}.sprd2.gif")
        st.markdown(f"**{title} INDEX**")
        st.markdown(f"<span style='font-size:1.8rem; font-weight:800;'>{d['now']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:{color}; font-weight:bold; border:1px solid {color}; padding:2px 8px;'>{bias}</span>", unsafe_allow_html=True)
        y_d, w_d = d['now']-d['y'], d['now']-d['w']
        y_col = "#00FF00" if (y_d < 0 if inv else y_d > 0) else "#FF4B4B"
        st.markdown(f"<div style='font-size:0.85rem; margin-top:8px;'><span style='color:{y_col}'>vs yest: {y_d:+.2f}</span> | vs week: {w_d:+.2f}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='legend-text'>Crna linija {'ispod' if inv else 'iznad'} nule = BULLISH.</div>", unsafe_allow_html=True)

draw_metric(v1, "AO", ao_d, ao_b, ao_c, True)
draw_metric(v2, "NAO", nao_d, nao_b, nao_c, True)
draw_metric(v3, "PNA", pna_d, *get_logic(pna_d['now'], pna_d['y'], pna_d['w'], "PNA")[:2], False)

# --- 4. EIA STORAGE ---
st.subheader("🛢️ EIA Storage Intelligence")
if storage:
    e1, e2, e3 = st.columns(3)
    e1.metric("ZALIHE", f"{storage['curr']} Bcf", f"{storage['chg']} Bcf")
    st_label = "BULLISH" if storage['diff_5y'] < 0 else "BEARISH"
    e2.metric(f"vs 5y AVG ({st_label})", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")
    with e3:
        now = datetime.now(timezone.utc)
        target = (now + timedelta(days=(3 - now.weekday()) % 7)).replace(hour=15, minute=30, second=0)
        if now >= target: target += timedelta(days=7)
        diff = target - now
        st.write(f"⌛ EIA COUNTDOWN: {int(diff.total_seconds()//3600)}h {int((diff.total_seconds()%3600)//60)}m")
