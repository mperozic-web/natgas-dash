import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V47", layout="wide")

# Kontrola osvježavanja (120s)
with st.sidebar:
    st.header("⚙️ Sustav")
    pause_refresh = st.checkbox("Pauziraj osvježavanje (Lock UI)", value=False)
    
if not pause_refresh:
    st.markdown("<head><meta http-equiv='refresh' content='120'></head>", unsafe_allow_html=True)

# STEALTH CSS (Maksimalan kontrast, bez okvira)
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
NASDAQ_API_KEY = "sbgqUxBu5AfRNxSGQsky"

# --- DOHVAT PODATAKA ---
@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}", headers={'User-Agent': 'Mozilla/5.0'})
        m = r.json()['chart']['result'][0]['meta']
        return m['regularMarketPrice'], ((m['regularMarketPrice'] - m['previousClose']) / m['previousClose']) * 100
    except: return 0.0, 0.0

@st.cache_data(ttl=3600)
def get_eia_expanded():
    try:
        # 1. Zalihe (Weekly)
        url_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&facets[series][]=NW2_EPG0_SWO_R48_BCF&sort[0][column]=period&sort[0][direction]=desc&length=5"
        # 2. Proizvodnja (Monthly - Dry Gas)
        url_p = f"https://api.eia.gov/v2/natural-gas/prod/dry/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        # 3. LNG Izvoz (Monthly)
        url_e = f"https://api.eia.gov/v2/natural-gas/move/exp/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&facets[process][]=N9011US2&sort[0][column]=period&sort[0][direction]=desc&length=2"
        
        s_res = requests.get(url_s).json()['response']['data']
        p_res = requests.get(url_p).json()['response']['data']
        e_res = requests.get(url_e).json()['response']['data']
        
        return {
            "stor": int(s_res[0]['value']), "stor_chg": int(s_res[0]['value']) - int(s_res[1]['value']),
            "prod": float(p_res[0]['value']) / 30, "prod_chg": (float(p_res[0]['value']) - float(p_res[1]['value'])) / 30,
            "lng": float(e_res[0]['value']) / 30, "lng_chg": (float(e_res[0]['value']) - float(e_res[1]['value'])) / 30
        }
    except: return None

def fetch_rig_count():
    try:
        url = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS.json?api_key={NASDAQ_API_KEY}&limit=2"
        r = requests.get(url).json()
        d = r['dataset']['data']
        return int(d[0][1]), int(d[0][1]) - int(d[1][1])
    except: return 0, 0

# --- SIDEBAR: GLOBAL MARKET & COT FORM ---
with st.sidebar:
    st.header("🌎 Global Hubs")
    ng_p, ng_pct = get_price("NG=F")
    ttf_p, ttf_pct = get_price("TTF=F")
    st.metric("Henry Hub (US)", f"${ng_p:.3f}", f"{ng_pct:+.2f}%")
    st.metric("Dutch TTF (EU)", f"€{ttf_p:.2f}", f"{ttf_pct:+.2f}%")
    
    st.markdown("---")
    with st.form("cot_form"):
        st.header("🏛️ COT Intelligence")
        nc_l = st.number_input("Managed Money Long", value=288456)
        nc_s = st.number_input("Managed Money Short", value=424123)
        submitted = st.form_submit_button("POTVRDI I ANALIZIRAJ")

# --- ANALIZA PODATAKA ---
eia = get_eia_expanded()
rigs, rig_chg = fetch_rig_count()
ao_url = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv"
ao_r = requests.get(ao_url, timeout=5)
ao_val = pd.read_csv(io.StringIO(ao_r.content.decode('utf-8'))).iloc[-1, -1]

# --- 1. EXECUTIVE STRATEGIC NARRATIVE (SINTEZA) ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
tightness = "TIGHT" if (eia and eia['prod'] < (eia['lng'] + 80)) else "LOOSE" # 80 Bcf/d je prosječna potrošnja

# Detekcija anomalija
supply_alert = "BULLISH" if (eia and eia['prod_chg'] < 0) else "BEARISH"
export_alert = "BULLISH" if (eia and eia['lng_chg'] > 0) else "BEARISH"

narrative = f"""
Tržišna sinteza pokazuje status **{tightness}**. 
Dnevna proizvodnja iznosi **{eia['prod']:.1f} Bcf/d** ({eia['prod_chg']:+.1f} promjena), dok LNG izvozni pritisak iznosi **{eia['lng']:.1f} Bcf/d** ({eia['lng_chg']:+.1f} promjena). 

Managed Money pozicija od **{nc_net:+,}** ugovora je u neskladu s **{supply_alert}** trendom proizvodnje. 
Uz AO Index na **{ao_val:+.2f}**, fundamentalna podloga za cijenu od **${ng_p:.3f}** je izrazito snažna. 
Rig Count od **{rigs}** ({rig_chg:+} tjedno) potvrđuje da proizvođači ne povećavaju ponudu unatoč globalnoj potražnji na TTF-u (pretvoreno: **${(ttf_p * 1.08 / 3.41):.2f}/MMBtu**).
"""
st.markdown(f"<div class='summary-narrative'>{narrative}</div>", unsafe_allow_html=True)

# --- 2. NOAA DUAL RADAR ---
t1, t2 = st.tabs(["🌡️ Temperature Outlook", "🌧️ Precipitation Outlook"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Temp")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Temp")
with t2:
    p1, p2 = st.columns(2)
    p1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Precipitation")
    p2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d Precipitation")

# --- 3. EXPANDED EIA MODULE ---
st.subheader("🛢️ EIA Fundamental Fortress")

col1, col2, col3 = st.columns(3)
if eia:
    with col1:
        st.write("**SUPPLY (Ponuda)**")
        st.metric("Dry Production", f"{eia['prod']:.1f} Bcf/d", f"{eia['prod_chg']:+.1f} mjesečno", delta_color="inverse")
        st.metric("US Rig Count", f"{rigs}", f"{rig_chg:+} tjedno", delta_color="inverse")
    
    with col2:
        st.write("**DEMAND (Potražnja)**")
        st.metric("Zalihe (Storage)", f"{eia['stor']} Bcf", f"{eia['stor_chg']} Bcf", delta_color="inverse")
        st.write(f"Status zaliha: **{'BULLISH' if eia['stor_chg'] < 0 else 'BEARISH'}**")

    with col3:
        st.write("**EXPORT (Izvoz)**")
        st.metric("LNG Gross Exports", f"{eia['lng']:.1f} Bcf/d", f"{eia['lng_chg']:+.1f} mjesečno")
        st.write(f"Export Pull: **{'SNAŽAN' if eia['lng_chg'] > 0 else 'STABILAN'}**")

st.markdown("---")
st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", caption="AO Index (Crna linija ISPOD 0 = BULLISH)")
