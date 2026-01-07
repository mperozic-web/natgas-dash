import streamlit as st
import pandas as pd
import requests
import io
import re
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V29", layout="wide")

# STEALTH CSS (Bez em-dasha, visoki kontrast)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    header, [data-testid="stHeader"] { background-color: #000000 !important; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 8px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #AAAAAA !important; }
    .stMetric { background-color: transparent; border: 1px solid #333; border-radius: 0px; padding: 10px; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; margin-bottom: 35px; background-color: #0A0A0A; }
    .legend-text { font-size: 0.85rem; color: #999999; margin-top: 5px; font-style: italic; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. DOHVAT CIJENA (PUBLIC API PROXY) ---
def get_ng_price():
    try:
        # Koristimo javni API za dobivanje osnovne cijene
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers={'User-Agent': 'Mozilla/5.0'})
        data = r.json()['chart']['result'][0]['meta']
        price = data['regularMarketPrice']
        prev_close = data['previousClose']
        pct_chg = ((price - prev_close) / prev_close) * 100
        return price, pct_chg
    except:
        return 0.0, 0.0

# --- 2. DOHVAT NOAA S POVIJEŠĆU ---
@st.cache_data(ttl=600)
def get_noaa_with_history(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        val_col = df.columns[-1]
        latest = float(df.iloc[-1][val_col])
        yesterday = float(df.iloc[-2][val_col])
        last_week = float(df.iloc[-8][val_col])
        return {"latest": latest, "vs_y": latest - yesterday, "vs_w": latest - last_week}
    except:
        return {"latest": 0.0, "vs_y": 0.0, "vs_w": 0.0}

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

# --- SIDEBAR: PRICE, COT & FUTURES ---
with st.sidebar:
    st.header("⚡ Live Market Structure")
    price, pct = get_ng_price()
    st.metric("Natural Gas Price", f"${price:.3f}", f"{pct:+.2f}%")
    
    st.markdown("---")
    st.header("🏛️ COT DATA CENTER")
    nc_l = st.number_input("NC Long", value=288456)
    nc_s = st.number_input("NC Short", value=424123)
    c_l = st.number_input("Comm Long", value=512000)
    c_s = st.number_input("Comm Short", value=380000)
    nr_l = st.number_input("Retail Long", value=54120)
    nr_s = st.number_input("Retail Short", value=32100)
    
    nc_net = nc_l - nc_s
    nr_net = nr_l - nr_s
    
    st.markdown("---")
    st.header("📉 Futures Curve")
    f1 = st.number_input("Front Month (M1):", value=price if price > 0 else 2.50)
    f2 = st.number_input("Next Month (M2):", value=2.65)
    spread = f1 - f2
    structure = "BACKWARDATION (Bullish)" if spread > 0 else "CONTANGO (Bearish)"
    st.write(f"Struktura: **{structure}**")
    st.caption("Backwardation signalizira manjak plina odmah.")

# --- DOHVAT PODATAKA ---
ao_d = get_noaa_with_history("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao_d = get_noaa_with_history("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna_d = get_noaa_with_history("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")
storage = get_eia_data(EIA_API_KEY)

# --- ANALITIČKI SAŽETAK ---
ao, nao, pna = ao_d['latest'], nao_d['latest'], pna_d['latest']
meteo_bull = (ao < -0.4 or nao < -0.4)
stor_bull = (storage and storage['diff_5y'] < 0)

# Brzina (Velocity) analitika
ao_velocity = "ubrzava u minus" if ao_d['vs_y'] < 0 else "usporava pad"
nao_velocity = "jača blokadu" if nao_d['vs_y'] < 0 else "slabi blokadu"

squeeze_msg = ""
if nc_net < -150000 and nr_net < -10000 and meteo_bull:
    squeeze_msg = "Detektiran je snažan SHORT SQUEEZE moment. Institucije i retail su u ekstremnom 'short' položaju dok atmosferski moment (AO/NAO) ubrzava prema hladnoći."
elif nc_net > 100000 and not meteo_bull:
    squeeze_msg = "Rizik od LONG SQUEEZEA. Previše optimizma dok atmosferski moment slabi."

# --- 1. EXECUTIVE STRATEGIC NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
narrative = f"""
Atmosferski profil je **{'BULLISH' if meteo_bull else 'BEARISH'}**. AO indeks ({ao:.2f}) trenutno **{ao_velocity}**, dok NAO ({nao:.2f}) **{nao_velocity}**. Brzina promjene u odnosu na prošli tjedan (AO vs last week: {ao_d['vs_w']:+.2f}) ukazuje na {'snažan dolazak fronte' if ao_d['vs_w'] < 0 else 'postepeno popuštanje hladnoće'}.

Fundamenti zaliha su **{'BULLISH' if stor_bull else 'BEARISH'}** ({storage['diff_5y']:+} Bcf vs 5y Avg). Tržišna struktura je u statusu **{structure}**, što {'podržava trenutnu potražnju' if spread > 0 else 'ukazuje na dobru opskrbljenost'}.

{squeeze_msg}
Strategija: Ako špageti grafovi AO indeksa pokažu daljnji pad, a cijena NG ostane stabilna, očekuj nasilan proboj prema gore zbog 'coveranja' short pozicija.
"""
st.markdown(f"<div class='summary-narrative'>{narrative}</div>", unsafe_allow_html=True)

# --- 2. NOAA RADAR ---
st.subheader("🗺️ NOAA Temperature Radar")
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="SHORT TERM (6-10 dana)")
with col_r2:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="LONG TERM (8-14 dana)")

st.markdown("---")

# --- 3. ATMOSPHERIC TRENDS & VELOCITY ---
st.subheader("📈 Index Forecast Trends & Velocity")
v1, v2, v3 = st.columns(3)

def get_status(val, itype):
    if itype in ["AO", "NAO"]:
        if val < -2.0: return "EXTREME BULLISH"
        if val < -1.0: return "BULLISH"
        if val < -0.4: return "MINOR BULLISH"
        return "BEARISH" if val > 0.4 else "NEUTRAL"
    else: # PNA
        if val > 1.5: return "EXTREME BULLISH"
        if val > 0.8: return "BULLISH"
        if val > 0.4: return "MINOR BULLISH"
        return "BEARISH" if val < -0.4 else "NEUTRAL"

def display_idx(col, title, data, itype, inv=True):
    with col:
        st.image(f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/{title.lower()}.sprd2.gif" if title=="AO" else f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/{title.lower()}.sprd2.gif")
        status = get_status(data['latest'], itype)
        # ISPRAVLJENA LOGIKA BOJA: Bullish (Zeleno), Bearish (Crveno)
        st.metric(f"{title} INDEX", f"{data['latest']:.2f}", status, delta_color="inverse" if inv else "normal")
        
        y_c = "#00FF00" if (data['vs_y'] < 0 if inv else data['vs_y'] > 0) else "#FF4B4B"
        w_c = "#00FF00" if (data['vs_w'] < 0 if inv else data['vs_w'] > 0) else "#FF4B4B"
        st.markdown(f"""
            <div style='margin-top:-10px; margin-bottom:10px;'>
                <span style='color:{y_c}; font-size:0.85rem;'>vs yesterday: {data['vs_y']:+.2f}</span><br>
                <span style='color:{w_c}; font-size:0.85rem;'>vs last week: {data['vs_w']:+.2f}</span>
            </div>
            <div class='legend-text'>{'Crna linija ispod nule = BULLISH' if inv else 'Crna linija iznad nule = BULLISH'}.</div>
        """, unsafe_allow_html=True)

display_idx(v1, "AO", ao_d, "AO", True)
display_idx(v2, "NAO", nao_d, "NAO", True)
display_idx(v3, "PNA", pna_d, "PNA", False)

st.markdown("---")

# --- 4. EIA STORAGE ---
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
