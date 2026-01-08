import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V56", layout="wide")

# STEALTH CSS
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
NASDAQ_API_KEY = "sbgqUxBu5AfRNxSGQsky"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# --- DATA ENGINES ---

def get_nasdaq_robust():
    """Dohvaća COT i Rig Count preko CSV-a (puno stabilnije od JSON-a)"""
    try:
        # COT Natural Gas Physical
        u_c = f"https://data.nasdaq.com/api/v3/datasets/CFTC/023651_F_L_ALL.csv?api_key={NASDAQ_API_KEY}&limit=1"
        df_c = pd.read_csv(u_c)
        # Rig Count
        u_r = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS.csv?api_key={NASDAQ_API_KEY}&limit=2"
        df_r = pd.read_csv(u_r)
        
        return {
            "nc_l": int(df_c.iloc[0]['Managed Money Positions - Long']),
            "nc_s": int(df_c.iloc[0]['Managed Money Positions - Short']),
            "rigs": int(df_r.iloc[0]['Value']),
            "rig_chg": int(df_r.iloc[0]['Value']) - int(df_r.iloc[1]['Value'])
        }
    except Exception as e:
        return None

def get_eia_hardened():
    """EIA V2 s preciznim putanjama"""
    try:
        # Storage
        u_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=5"
        # Production (Dry Natural Gas Production)
        u_p = f"https://api.eia.gov/v2/natural-gas/prod/dry/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        
        s_res = requests.get(u_s).json()['response']['data']
        p_res = requests.get(u_p).json()['response']['data']
        
        c_s = int(s_res[0]['value'])
        return {
            "stor": c_s, "stor_chg": c_s - int(s_res[1]['value']),
            "stor_5y": c_s - int(pd.DataFrame(s_res)['value'].astype(int).mean()),
            "prod": float(p_res[0]['value']) / 30, "prod_chg": (float(p_res[0]['value']) - float(p_res[1]['value'])) / 30
        }
    except: return None

# --- SIDEBAR & PRICE ---
with st.sidebar:
    st.header("⚡ Live Core")
    try:
        ng_p = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()['chart']['result'][0]['meta']['regularMarketPrice']
        st.metric("Henry Hub", f"${ng_p:.3f}")
    except: ng_p = 0.0

    nas = get_nasdaq_robust()
    eia = get_eia_hardened()
    
    with st.form("cot_form"):
        st.header("🏛️ COT Center")
        nc_l = st.number_input("NC Long", value=nas['nc_l'] if nas else 288456)
        nc_s = st.number_input("NC Short", value=nas['nc_s'] if nas else 424123)
        st.form_submit_button("ANALIZIRAJ")

# --- ANALIZA ---
ao_r = requests.get("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
ao_val = pd.read_csv(io.StringIO(ao_r.content.decode('utf-8'))).iloc[-1, -1]

# --- 1. EXECUTIVE NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
p_str = f"{eia['prod']:.1f} Bcf/d" if eia else "N/A"
s_5y = f"{eia['stor_5y']:+}" if eia else "N/A"
r_val = f"{nas['rigs']}" if nas else "N/A"

st.markdown(f"""
<div class='summary-narrative'>
    Tržište operira pri <strong>${ng_p:.3f}</strong>. Managed Money neto: <strong>{nc_net:+,}</strong>.<br>
    Proizvodnja: <strong>{p_str}</strong>. Zalihe vs 5y: <strong>{s_5y} Bcf</strong>. Rig Count: <strong>{r_val}</strong>.<br>
    AO Index: <strong>{ao_val:+.2f}</strong>.
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA DUAL RADAR ---
t1, t2 = st.tabs(["🌡️ Temperature", "🌧️ Oborine"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d")
with t2:
    p1, p2 = st.columns(2)
    p1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d")
    p2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d")

# --- 3. INDEX TRENDS ---
st.subheader("📈 Index Forecast Trends")
v1, v2, v3 = st.columns(3)
def draw_idx(col, title, url, leg):
    with col:
        st.image(url)
        st.markdown(f"**{title} Outlook**")
        st.markdown(f"<p style='font-size:0.8rem; color:#888;'>{leg}</p>", unsafe_allow_html=True)

draw_idx(v1, "AO", "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "ISPOD 0 = BULLISH")
draw_idx(v2, "NAO", "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "ISPOD 0 = BULLISH")
draw_idx(v3, "PNA", "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "IZNAD 0 = BULLISH")

# --- 4. FUNDAMENTALS ---
st.subheader("🛢️ Fundamental Intelligence")
if eia:
    f1, f2 = st.columns(2)
    f1.metric("Storage", f"{eia['stor']} Bcf", f"{eia['stor_chg']} Bcf", delta_color="inverse")
    f2.metric("Production", f"{eia['prod']:.1f} Bcf/d", f"{eia['prod_chg']:+.1f}")
