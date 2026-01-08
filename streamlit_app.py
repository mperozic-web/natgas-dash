import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V48", layout="wide")

# Kontrola osvježavanja
with st.sidebar:
    st.header("⚙️ Sustav")
    pause_refresh = st.checkbox("Pauziraj osvježavanje", value=False)
    
if not pause_refresh:
    st.markdown("<head><meta http-equiv='refresh' content='120'></head>", unsafe_allow_html=True)

# STEALTH CSS
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 8px; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; margin-bottom: 35px; background-color: #0A0A0A; }
    .bull-text { color: #00FF00 !important; }
    .bear-text { color: #FF4B4B !important; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    .stButton>button { width: 100%; background-color: #007BFF; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
NASDAQ_API_KEY = "sbgqUxBu5AfRNxSGQsky"

# --- DOHVAT PODATAKA (ROBUST) ---
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
        # Povećan length na 10 kako bismo osigurali da imamo barem 2 valjane točke za diff
        u_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&facets[series][]=NW2_EPG0_SWO_R48_BCF&sort[0][column]=period&sort[0][direction]=desc&length=10"
        u_p = f"https://api.eia.gov/v2/natural-gas/prod/dry/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=5"
        u_e = f"https://api.eia.gov/v2/natural-gas/move/exp/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&facets[process][]=N9011US2&sort[0][column]=period&sort[0][direction]=desc&length=5"
        
        s_data = requests.get(u_s).json()['response']['data']
        p_data = requests.get(u_p).json()['response']['data']
        e_data = requests.get(u_e).json()['response']['data']
        
        c_s = int(s_data[0]['value'])
        avg5y = pd.DataFrame(s_data)['value'].astype(int).mean()
        
        return {
            "stor": c_s, "stor_chg": c_s - int(s_data[1]['value']), "stor_5y": c_s - int(avg5y),
            "prod": float(p_data[0]['value']) / 30, "prod_chg": (float(p_data[0]['value']) - float(p_data[1]['value'])) / 30,
            "lng": float(e_data[0]['value']) / 30, "lng_chg": (float(e_data[0]['value']) - float(e_data[1]['value'])) / 30
        }
    except: return None

def fetch_rig_count():
    try:
        url = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS.json?api_key={NASDAQ_API_KEY}&limit=2"
        r = requests.get(url).json()
        d = r['dataset']['data']
        return int(d[0][1]), int(d[0][1]) - int(d[1][1])
    except: return 0, 0

# --- SIDEBAR & COT FORM ---
with st.sidebar:
    st.header("🌎 Global Hubs")
    ng_p, ng_pct = get_price("NG=F")
    ttf_p, ttf_pct = get_price("TTF=F")
    st.metric("Henry Hub", f"${ng_p:.3f}", f"{ng_pct:+.2f}%")
    st.metric("Dutch TTF", f"€{ttf_p:.2f}", f"{ttf_pct:+.2f}%")
    
    with st.form("cot_form"):
        st.header("🏛️ COT Manual")
        nc_l = st.number_input("NC Long", value=288456)
        nc_s = st.number_input("NC Short", value=424123)
        submitted = st.form_submit_button("POTVRDI I ANALIZIRAJ")

# --- ANALIZA PODATAKA ---
eia = get_eia_expanded()
rigs, rig_chg = fetch_rig_count()
ao_url = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv"
ao_val = 0.0
try:
    ao_r = requests.get(ao_url, timeout=5)
    ao_val = pd.read_csv(io.StringIO(ao_r.content.decode('utf-8'))).iloc[-1, -1]
except: pass

# --- EXECUTIVE STRATEGIC NARRATIVE (SINTEZA S PROVJEROM) ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s

# Safe variables za narativ
prod_val = f"{eia['prod']:.1f}" if eia else "N/A"
prod_chg = f"{eia['prod_chg']:+.1f}" if eia else "N/A"
lng_val = f"{eia['lng']:.1f}" if eia else "N/A"
lng_chg = f"{eia['lng_chg']:+.1f}" if eia else "N/A"
stor_5y = f"{eia['stor_5y']:+}" if eia else "N/A"

narrative = f"""
Tržišna sinteza operira pri cijeni od **${ng_p:.3f}**. 
Managed Money pozicija iznosi **{nc_net:+,}** ugovora. 
Dnevna proizvodnja je **{prod_val} Bcf/d** ({prod_chg} promjena), dok LNG izvozni pull iznosi **{lng_val} Bcf/d** ({lng_chg} promjena). 

Zalihe plina su na **{stor_5y} Bcf** u odnosu na petogodišnji prosjek. 
AO Index je na **{ao_val:+.2f}**, što u kombinaciji s Rig Countom od **{rigs}** ({rig_chg:+} tjedno) definira fundamentalni okvir. 
{'Upozorenje: EIA podaci privremeno nedostupni, narativ koristi zadnje poznato stanje.' if not eia else ''}
"""
st.markdown(f"<div class='summary-narrative'>{narrative}</div>", unsafe_allow_html=True)

# --- 2. NOAA DUAL RADAR ---
t1, t2 = st.tabs(["🌡️ Temperature Outlook", "🌧️ Precipitation Outlook"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d")
with t2:
    p1, p2 = st.columns(2)
    p1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Precip")
    p2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d Precip")

# --- 3. EXPANDED EIA MODULE (SAFE UI) ---
st.subheader("🛢️ Fundamental Intelligence")

if eia:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**SUPPLY**")
        st.metric("Production", f"{eia['prod']:.1f} Bcf/d", f"{eia['prod_chg']:+.1f}")
        st.metric("Rig Count", f"{rigs}", f"{rig_chg:+}")
    with col2:
        st.write("**STORAGE**")
        st.metric("Zalihe", f"{eia['stor']} Bcf", f"{eia['stor_chg']} Bcf", delta_color="inverse")
        st.metric("vs 5y Avg", f"{eia['stor_5y']:+} Bcf", delta_color="inverse")
    with col3:
        st.write("**EXPORT**")
        st.metric("LNG Exports", f"{eia['lng']:.1f} Bcf/d", f"{eia['lng_chg']:+.1f}")
else:
    st.error("EIA API trenutno ne vraća podatke. Provjeri status na eia.gov.")

st.markdown("---")
st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", caption="AO Index")
