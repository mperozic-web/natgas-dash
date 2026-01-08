import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V52", layout="wide")

with st.sidebar:
    st.header("⚙️ Postavke")
    pause_refresh = st.checkbox("Pauziraj auto-osvježavanje", value=False)
    
if not pause_refresh:
    st.markdown("<head><meta http-equiv='refresh' content='120'></head>", unsafe_allow_html=True)

# STEALTH CSS (Bez em-dasha, visoki kontrast)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 8px; }
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
@st.cache_data(ttl=300)
def get_live_price(ticker):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}", headers={'User-Agent': 'Mozilla/5.0'})
        m = r.json()['chart']['result'][0]['meta']
        return m['regularMarketPrice'], ((m['regularMarketPrice'] - m['previousClose']) / m['previousClose']) * 100
    except: return 0.0, 0.0

def get_nasdaq_data():
    try:
        # COT (Natural Gas Physical)
        u_c = f"https://data.nasdaq.com/api/v3/datasets/CFTC/023651_F_L_ALL.json?api_key={NASDAQ_API_KEY}&limit=1"
        c_res = requests.get(u_c).json()['dataset']['data'][0]
        # Rigs
        u_r = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS.json?api_key={NASDAQ_API_KEY}&limit=2"
        r_res = requests.get(u_r).json()['dataset']['data']
        
        return {
            "nc_l": int(c_res[12]), "nc_s": int(c_res[13]),
            "c_l": int(c_res[5]) + int(c_res[8]), "c_s": int(c_res[6]) + int(c_res[9]),
            "nr_l": int(c_res[20]), "nr_s": int(c_res[21]),
            "rigs": int(r_res[0][1]), "rig_chg": int(r_res[0][1]) - int(r_res[1][1])
        }
    except Exception as e:
        return None

@st.cache_data(ttl=1800)
def get_eia_fortress():
    try:
        # Zalihe
        u_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&facets[series][]=NW2_EPG0_SWO_R48_BCF&sort[0][column]=period&sort[0][direction]=desc&length=5"
        # Proizvodnja (Mjesečno)
        u_p = f"https://api.eia.gov/v2/natural-gas/prod/dry/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        # Izvoz (Mjesečno)
        u_e = f"https://api.eia.gov/v2/natural-gas/move/exp/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&facets[process][]=N9011US2&sort[0][column]=period&sort[0][direction]=desc&length=2"
        
        s_d = requests.get(u_s).json()['response']['data']
        p_d = requests.get(u_p).json()['response']['data']
        e_d = requests.get(u_e).json()['response']['data']
        
        c_s = int(s_d[0]['value'])
        return {
            "stor": c_s, "stor_chg": c_s - int(s_d[1]['value']),
            "stor_5y": c_s - int(pd.DataFrame(s_d)['value'].astype(int).mean()),
            "prod": float(p_d[0]['value'])/30, "prod_chg": (float(p_d[0]['value']) - float(p_d[1]['value']))/30,
            "lng": float(e_d[0]['value'])/30, "lng_chg": (float(e_d[0]['value']) - float(e_d[1]['value']))/30
        }
    except: return None

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=5)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        v = df[df.columns[-1]].tolist()
        return {"now": v[-1], "y": v[-2]}
    except: return {"now": 0.0, "y": 0.0}

# --- SIDEBAR & GLOBAL HUB ---
with st.sidebar:
    st.header("🌎 Global Market")
    ng_p, ng_pct = get_live_price("NG=F")
    ttf_p, ttf_pct = get_live_price("TTF=F")
    st.metric("Henry Hub", f"${ng_p:.3f}", f"{ng_pct:+.2f}%")
    st.metric("Dutch TTF", f"€{ttf_p:.2f}", f"{ttf_pct:+.2f}%")
    arb = (ttf_p * 1.08 / 3.41) - ng_p
    st.metric("US-EU Arb Spread", f"${arb:.2f}")

    st.markdown("---")
    nas_data = get_nasdaq_data()
    with st.form("cot_form"):
        st.header("🏛️ COT Data")
        nc_l = st.number_input("Managed Money Long", value=nas_data['nc_l'] if nas_data else 288456)
        nc_s = st.number_input("Managed Money Short", value=nas_data['nc_s'] if nas_data else 424123)
        c_l = st.number_input("Commercial Long", value=nas_data['c_l'] if nas_data else 512000)
        c_s = st.number_input("Commercial Short", value=nas_data['c_s'] if nas_data else 380000)
        nr_l = st.number_input("Retail Long", value=nas_data['nr_l'] if nas_data else 54120)
        nr_s = st.number_input("Retail Short", value=nas_data['nr_s'] if nas_data else 32100)
        st.form_submit_button("POTVRDI I ANALIZIRAJ")

# --- OBRADA ---
eia = get_eia_fortress()
ao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE STRATEGIC NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
c_net = c_l - c_s

# Display helper strings
p_str = f"{eia['prod']:.1f} Bcf/d" if eia else "N/A"
l_str = f"{eia['lng']:.1f} Bcf/d" if eia else "N/A"
s_5y = f"{eia['stor_5y']:+}" if eia else "N/A"
r_val = f"{nas_data['rigs']}" if nas_data else "N/A"

narrative = f"""
Tržište operira pri cijeni od **${ng_p:.3f}**. Managed Money neto pozicija iznosi **{nc_net:+,}**, dok su Commercials na **{c_net:+,}**. 
Dnevna proizvodnja je **{p_str}**, uz LNG izvoz od **{l_str}**. 

Zalihe su na **{s_5y} Bcf** u odnosu na petogodišnji prosjek. 
AO Index ({ao['now']:+.2f}) je u statusu **{'BULLISH' if ao['now'] < ao['y'] else 'BEARISH'}** (momentum vs yesterday). 
Arbitražni spread od **${arb:.2f}** i Rig Count od **{r_val}** potvrđuju fundamentalno dno.
"""
st.markdown(f"<div class='summary-narrative'>{narrative}</div>", unsafe_allow_html=True)

# --- 2. NOAA DUAL RADAR TABS ---
t1, t2 = st.tabs(["🌡️ Temperature Outlook", "🌧️ Precipitation Outlook"])
with t1:
    col1, col2 = st.columns(2)
    col1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Outlook")
    col2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Outlook")
with t2:
    col1, col2 = st.columns(2)
    col1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Oborine")
    col2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d Oborine")

# --- 3. ATMOSPHERIC INDEX VELOCITY ---
st.subheader("📈 Index Forecast Trends")
v1, v2, v3 = st.columns(3)

def draw_idx(col, title, d, inv, leg):
    with col:
        st.image(f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/{title.lower()}.sprd2.gif" if title != "PNA" else "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif")
        bias = "BULLISH" if (d['now'] < -0.4 if inv else d['now'] > 0.4) else "BEARISH" if (d['now'] > 0.4 if inv else d['now'] < -0.4) else "NEUTRAL"
        cl = "bull-text" if bias == "BULLISH" else "bear-text" if bias == "BEARISH" else ""
        st.markdown(f"**{title}: {d['now']:.2f}** (<span class='status-box {cl}'>{bias}</span>)", unsafe_allow_html=True)
        st.markdown(f"<p class='legend-text'>{leg}</p>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao, True, "ISPOD 0 = BULLISH")
draw_idx(v2, "NAO", nao, True, "ISPOD 0 = BULLISH")
draw_idx(v3, "PNA", pna, False, "IZNAD 0 = BULLISH")

# --- 4. EIA & SUPPLY FORTRESS ---
st.subheader("🛢️ Fundamental Intelligence Fortress")

f1, f2, f3 = st.columns(3)
if eia:
    with f1:
        st.write("**STORAGE**")
        st.metric("Zalihe", f"{eia['stor']} Bcf", f"{eia['stor_chg']} Bcf", delta_color="inverse")
        st.metric("vs 5y Avg", f"{eia['stor_5y']:+} Bcf", delta_color="inverse")
    with f2:
        st.write("**SUPPLY**")
        st.metric("Dry Production", f"{eia['prod']:.1f} Bcf/d", f"{eia['prod_chg']:+.1f}")
        if nas_data: st.metric("Rig Count", f"{nas_data['rigs']}", f"{nas_data['rig_chg']:+}")
    with f3:
        st.write("**EXPORT**")
        st.metric("LNG Exports", f"{eia['lng']:.1f} Bcf/d", f"{eia['lng_chg']:+.1f}")
else:
    st.error("EIA podaci trenutno nisu dostupni (Provjeri API ključ ili server).")
