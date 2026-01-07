import streamlit as st
import pandas as pd
import requests
import io
import time
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA I AUTO-REFRESH (120s) ---
st.set_page_config(page_title="NatGas Sniper V30", layout="wide")

# Skripta za automatsko osvježavanje stranice svake 2 minute
st.markdown("""
    <head>
        <meta http-equiv="refresh" content="120">
    </head>
    """, unsafe_allow_html=True)

# STEALTH CSS (Potpuno crno, bez okvira u boji, maksimalan kontrast)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    header, [data-testid="stHeader"] { background-color: #000000 !important; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 8px; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 800 !important; color: #FFFFFF !important; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; margin-bottom: 35px; background-color: #0A0A0A; }
    .legend-text { font-size: 0.85rem; color: #999999; margin-top: 5px; font-style: italic; }
    .status-tag { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9rem; }
    .bull-tag { color: #00FF00; border: 1px solid #00FF00; }
    .bear-tag { color: #FF4B4B; border: 1px solid #FF4B4B; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- DOHVAT PODATAKA ---
def get_ng_live():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers={'User-Agent': 'Mozilla/5.0'})
        meta = r.json()['chart']['result'][0]['meta']
        return meta['regularMarketPrice'], ((meta['regularMarketPrice'] - meta['previousClose']) / meta['previousClose']) * 100
    except: return 0.0, 0.0

@st.cache_data(ttl=300)
def get_noaa_history(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        col = df.columns[-1]
        vals = df[col].tolist()
        return {"now": vals[-1], "yest": vals[-2], "week": vals[-8]}
    except: return {"now": 0.0, "yest": 0.0, "week": 0.0}

@st.cache_data(ttl=3600)
def get_eia():
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        p = {"api_key": EIA_API_KEY, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 50}
        r = requests.get(url, params=p).json()
        df = pd.DataFrame(r['response']['data'])
        df['val'] = df['value'].astype(int)
        curr = df.iloc[0]['val']
        diff_5y = curr - int(df['val'].mean())
        return {"curr": curr, "chg": curr - df.iloc[1]['val'], "diff_5y": diff_5y, "date": df.iloc[0]['period']}
    except: return None

# --- SIDEBAR: LIVE MARKET ---
with st.sidebar:
    st.header("⚡ Live Market Structure")
    price, pct = get_ng_live()
    st.metric("Natural Gas Live", f"${price:.3f}", f"{pct:+.2f}%")
    
    st.markdown("---")
    st.header("🏛️ COT DATA")
    nc_l = st.number_input("NC Long", value=288456)
    nc_s = st.number_input("NC Short", value=424123)
    c_l = st.number_input("Comm Long", value=512000)
    c_s = st.number_input("Comm Short", value=380000)
    nr_l = st.number_input("Retail Long", value=54120)
    nr_s = st.number_input("Retail Short", value=32100)
    
    st.markdown("---")
    st.header("📉 Futures Curve")
    f1 = st.number_input("Month 1:", value=price if price > 0 else 2.50)
    f2 = st.number_input("Month 2:", value=2.65)
    spread = f1 - f2
    struct = "BACKWARDATION" if spread > 0 else "CONTANGO"
    st.write(f"Status: **{struct}**")

# --- PROCESIRANJE INDEKSA ---
ao_d = get_noaa_history("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao_d = get_noaa_history("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna_d = get_noaa_history("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia()

# LOGIKA BIASA I BOJA (Fixed per screenshot request)
def analyze_idx(val, yesterday, last_week, itype):
    # AO i NAO: minus je Bull
    if itype in ["AO", "NAO"]:
        bias = "BULLISH" if val < -0.4 else "BEARISH" if val > 0.4 else "NEUTRAL"
    else: # PNA: plus je Bull
        bias = "BULLISH" if val > 0.4 else "BEARISH" if val < -0.4 else "NEUTRAL"
    
    color = "#00FF00" if bias == "BULLISH" else "#FF4B4B" if bias == "BEARISH" else "#AAAAAA"
    
    # Trend analiza za Executive Summary
    trend = "ubrzava" if (val < yesterday < last_week if itype != "PNA" else val > yesterday > last_week) else "usporava/okreće"
    return bias, color, trend

ao_bias, ao_col, ao_tr = analyze_idx(ao_d['now'], ao_d['yest'], ao_d['week'], "AO")
nao_bias, nao_col, nao_tr = analyze_idx(nao_d['now'], nao_d['yest'], nao_d['week'], "NAO")
pna_bias, pna_col, pna_tr = analyze_idx(pna_d['now'], pna_d['yest'], pna_d['week'], "PNA")

# --- 1. EXECUTIVE STRATEGIC SUMMARY ---
st.subheader("📋 Executive Strategic Narrative")
meteo_overall = "BULLISH" if (ao_bias == "BULLISH" or nao_bias == "BULLISH") else "BEARISH"
stor_overall = "BULLISH" if (storage and storage['diff_5y'] < 0) else "BEARISH"
nc_net = nc_l - nc_s
nr_net = nr_l - nr_s

squeeze_msg = ""
if nc_net < -150000 and nr_net < -10000 and meteo_overall == "BULLISH":
    squeeze_msg = "Detektiran je kritičan rizik od **SHORT SQUEEZEA**. Institucije i retail su u teškom shortu dok atmosferski moment ubrzava hladnoću."
elif nc_net > 100000 and meteo_overall == "BEARISH":
    squeeze_msg = "Rizik od **LONG SQUEEZEA**. Tržište je prenatrpano kupcima uz slabljenje meteo potražnje."

narrative = f"""
Atmosferski profil je **{meteo_overall}**. AO ({ao_d['now']:.2f}) trenutačno **{ao_tr}** (vs jučer: {ao_d['now']-ao_d['yest']:+.2f}), dok NAO ({nao_d['now']:.2f}) **{nao_tr}**. Tjedni trend AO indeksa ({ao_d['now']-ao_d['week']:+.2f}) sugerira {'jačanje prodora' if ao_d['now'] < ao_d['week'] else 'slabljenje pritiska'}.

Fundamenti zaliha su **{stor_overall}** ({storage['diff_5y']:+} Bcf vs 5y Avg). Tržišna struktura je u statusu **{struct}**.

{squeeze_msg}
**Strategija:** Uoči nesklad između metrike i špageta. Ako metrika pokazuje usporavanje (vs yesterday), a špageti su i dalje u provaliji, nastavi držati smjer.
"""
st.markdown(f"<div class='summary-narrative'>{narrative}</div>", unsafe_allow_html=True)

# --- 2. NOAA RADAR ---
st.subheader("🗺️ NOAA Temperature Radar")
r1, r2 = st.columns(2)
r1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="SHORT TERM (6-10 dana)")
r2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="LONG TERM (8-14 dana)")

st.markdown("---")

# --- 3. ATMOSPHERIC TRENDS & VELOCITY ---
st.subheader("📈 Index Forecast Trends & Velocity")
v1, v2, v3 = st.columns(3)

def draw_idx(col, title, d, bias, color, inv):
    with col:
        st.image(f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/{title.lower()}.sprd2.gif" if title=="AO" else f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/{title.lower()}.sprd2.gif")
        st.markdown(f"**{title} INDEX**")
        st.markdown(f"<span style='font-size:1.8rem; font-weight:800;'>{d['now']:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"<span class='status-tag' style='color:{color}; border:1px solid {color};'>{bias}</span>", unsafe_allow_html=True)
        
        y_diff, w_diff = d['now']-d['yest'], d['now']-d['week']
        # Trend boje: zeleno ako ide prema Bull, crveno ako ide prema Bear
        y_c = "#00FF00" if (y_diff < 0 if inv else y_diff > 0) else "#FF4B4B"
        w_c = "#00FF00" if (w_diff < 0 if inv else w_diff > 0) else "#FF4B4B"
        st.markdown(f"<div style='font-size:0.85rem; margin-top:8px;'><span style='color:{y_c}'>vs yest: {y_diff:+.2f}</span> | <span style='color:{w_c}'>vs week: {w_diff:+.2f}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='legend-text'>Crna linija {'ispod' if inv else 'iznad'} nule = BULLISH.</div>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao_d, ao_bias, ao_col, True)
draw_idx(v2, "NAO", nao_d, nao_bias, nao_col, True)
draw_idx(v3, "PNA", pna_d, pna_bias, pna_col, False)

st.markdown("---")

# --- 4. EIA STORAGE ---
st.subheader("🛢️ EIA Storage Intelligence")
if storage:
    e1, e2, e3 = st.columns(3)
    e1.metric("ZALIHE", f"{storage['curr']} Bcf", f"{storage['chg']} Bcf")
    st_bias = "BULLISH" if storage['diff_5y'] < 0 else "BEARISH"
    e2.metric(f"vs 5y AVG ({st_bias})", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")
    
    with e3:
        now = datetime.now(timezone.utc)
        target = (now + timedelta(days=(3 - now.weekday()) % 7)).replace(hour=15, minute=30, second=0)
        if now >= target: target += timedelta(days=7)
        diff = target - now
        st.write(f"⌛ EIA COUNTDOWN: {int(diff.total_seconds()//3600)}h {int((diff.total_seconds()%3600)//60)}m")
