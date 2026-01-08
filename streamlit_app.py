import streamlit as st
import pandas as pd
import requests
import io
import nasdaq_data_link
from datetime import datetime

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V64", layout="wide")

# Inicijalizacija Nasdaq biblioteke
nasdaq_data_link.read_key(st.secrets.get("NASDAQ_API_KEY", "Vxj869NUowFMm2j2ManG"))

# CSS: Stealth & High-Contrast
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; background-color: #0A0A0A; }
    .status-box { padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.9rem; border: 1px solid #444; }
    .bull-text { color: #00FF00 !important; border-color: #00FF00 !important; }
    .bear-text { color: #FF4B4B !important; border-color: #FF4B4B !important; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- RADAR ENGINES ---

@st.cache_data(ttl=3600)
def fetch_nasdaq_pro():
    """Koristi službenu biblioteku za zaobilaženje 403 greške"""
    try:
        # COT Natural Gas Physical
        cot = nasdaq_data_link.get("CFTC/023651_F_L_ALL", limit=1)
        # US Natural Gas Rig Count
        rigs = nasdaq_data_link.get("BAKERHUGHES/RIGS_US_NATURAL_GAS", limit=2)
        
        return {
            "nc_l": int(cot['Managed Money Positions - Long'].iloc[0]),
            "nc_s": int(cot['Managed Money Positions - Short'].iloc[0]),
            "c_l": int(cot['Producer/Merchant/Processor/User Positions - Long'].iloc[0]) + int(cot['Swap Dealer Positions - Long'].iloc[0]),
            "c_s": int(cot['Producer/Merchant/Processor/User Positions - Short'].iloc[0]) + int(cot['Swap Dealer Positions - Short'].iloc[0]),
            "rig_val": int(rigs['Value'].iloc[0]),
            "rig_chg": int(rigs['Value'].iloc[0]) - int(rigs['Value'].iloc[1])
        }
    except Exception as e:
        st.sidebar.error(f"Nasdaq Library Error: {e}")
        return None

@st.cache_data(ttl=1800)
def fetch_eia_pro():
    """EIA V2 s preciznim filtriranjem"""
    try:
        url = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=10"
        r = requests.get(url, timeout=15).json()
        d = r['response']['data']
        curr = int(d[0]['value'])
        avg5y = sum(int(x['value']) for x in d) / len(d)
        return {"stor": curr, "chg": curr - int(d[1]['value']), "v5y": curr - int(avg5y)}
    except: return None

def get_idx(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return df.iloc[-1, -1]
    except: return 0.0

# --- SIDEBAR & CORE METRICS ---
with st.sidebar:
    st.header("🌎 Global Monitoring")
    # Live cijene (Yahoo)
    try:
        yh = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers={'User-Agent': 'Mozilla/5.0'}).json()
        price = yh['chart']['result'][0]['meta']['regularMarketPrice']
        st.metric("Henry Hub Live", f"${price:.3f}")
    except: price = 0.0

    nas = fetch_nasdaq_pro()
    eia = fetch_eia_pro()
    
    with st.form("cot_center"):
        st.header("🏛️ COT Intelligence")
        nc_l = st.number_input("NC Long", value=nas['nc_l'] if nas else 288456)
        nc_s = st.number_input("NC Short", value=nas['nc_s'] if nas else 424123)
        st.form_submit_button("SINKRONIZIRAJ")

# --- ANALITIČKA SINTEZA ---
ao = get_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")

# --- 1. EXECUTIVE STRATEGIC NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
s_5y = f"{eia['v5y']:+.0f}" if eia else "N/A"

st.markdown(f"""
<div class='summary-narrative'>
    Sustav operira pri cijeni od <strong>${price:.3f}</strong>. Managed Money neto pozicija: <strong>{nc_net:+,}</strong>.<br>
    Strukturni deficit zaliha (vs 5y avg): <strong>{s_5y} Bcf</strong>. AO Index: <strong>{ao:+.2f}</strong>.<br>
    Status proizvodnje (Rig Count): <strong>{nas['rig_val'] if nas else 'N/A'}</strong> ({nas['rig_chg']:+ if nas else ''}).
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA RADAR TABS ---
t1, t2 = st.tabs(["🌡️ Temperature", "🌧️ Oborine"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Outlook")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Outlook")

# --- 3. INDEX SPAGHETTI CHARTS ---
st.subheader("📈 Index Velocity Trends")

v1, v2, v3 = st.columns(3)
v1.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", caption="AO - Arctic Oscillation")
v2.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", caption="NAO - North Atlantic")
v3.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", caption="PNA - Pacific North American")

# --- 4. FUNDAMENTALS ---
st.subheader("🛢️ Fundamental Intelligence")
if eia:
    f1, f2, f3 = st.columns(3)
    f1.metric("Storage", f"{eia['stor']} Bcf", f"{eia['chg']} Bcf", delta_color="inverse")
    f2.metric("vs 5y Average", f"{eia['v5y']:+.1f} Bcf", delta_color="inverse")
    if nas: f3.metric("Rig Count", f"{nas['rig_val']}", f"{nas['rig_chg']:+}", delta_color="inverse")
