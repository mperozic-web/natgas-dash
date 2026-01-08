import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V55", layout="wide")

# CSS (Bez em-dasha)
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
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# --- CORE DATA ENGINES (IRONCLAD) ---

def fetch_nasdaq():
    try:
        # COT Dataset
        url_cot = f"https://data.nasdaq.com/api/v3/datasets/CFTC/023651_F_L_ALL/data.json?api_key={NASDAQ_API_KEY}&limit=1"
        res_cot = requests.get(url_cot, headers=HEADERS).json()
        c = res_cot['dataset_data']['data'][0]
        
        # Rigs
        url_rig = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS/data.json?api_key={NASDAQ_API_KEY}&limit=2"
        res_rig = requests.get(url_rig, headers=HEADERS).json()
        r = res_rig['dataset_data']['data']
        
        return {
            "nc_l": int(c[12]), "nc_s": int(c[13]),
            "c_l": int(c[5]) + int(c[8]), "c_s": int(c_l[6]) if 'c_l' in locals() else int(c[6]) + int(c[9]),
            "nr_l": int(c[20]), "nr_s": int(c[21]),
            "rigs": int(r[0][1]), "rig_chg": int(r[0][1]) - int(r[1][1])
        }
    except: return None

def fetch_eia():
    try:
        # Samo zalihe za početak, da stabiliziramo sustav
        url = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=5"
        r = requests.get(url, headers=HEADERS).json()
        data = r['response']['data']
        curr = int(data[0]['value'])
        prev = int(data[1]['value'])
        avg5y = pd.DataFrame(data)['value'].astype(int).mean()
        return {"stor": curr, "stor_chg": curr - prev, "stor_5y": curr - int(avg5y)}
    except: return None

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return {"now": df.iloc[-1, -1], "yest": df.iloc[-2, -1]}
    except: return {"now": 0.0, "yest": 0.0}

# --- SIDEBAR & PRICE ---
with st.sidebar:
    st.header("⚡ Live Price")
    try:
        p_res = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()
        ng_p = p_res['chart']['result'][0]['meta']['regularMarketPrice']
        st.metric("Henry Hub", f"${ng_p:.3f}")
    except: ng_p = 0.0

    nas_data = fetch_nasdaq()
    eia_data = fetch_eia()
    
    with st.form("cot_form"):
        st.header("🏛️ COT Center")
        nc_l = st.number_input("NC Long", value=nas_data['nc_l'] if nas_data else 288456)
        nc_s = st.number_input("NC Short", value=nas_data['nc_s'] if nas_data else 424123)
        st.form_submit_button("ANALIZIRAJ")

# --- DATA ---
ao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
stor_str = f"{eia_data['stor_5y']:+}" if eia_data else "N/A"
rigs_str = f"{nas_data['rigs']}" if nas_data else "N/A"

st.markdown(f"""
<div class='summary-narrative'>
    Tržište operira pri <strong>${ng_p:.3f}</strong>. Managed Money neto: <strong>{nc_net:+,}</strong>.<br>
    Zalihe vs 5y prosjek: <strong>{stor_str} Bcf</strong>. Rig Count: <strong>{rigs_str}</strong>.<br>
    AO Index: <strong>{ao['now']:+.2f}</strong>. Status: {'BULLISH' if ao['now'] < ao['yest'] else 'BEARISH'}.
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
def draw_idx(col, title, d, url, leg):
    with col:
        st.image(url)
        bias = "BULLISH" if (d['now'] < -0.4 if title != "PNA" else d['now'] > 0.4) else "BEARISH"
        st.markdown(f"**{title}: {d['now']:.2f}** ({bias})")
        st.markdown(f"<p style='font-size:0.8rem; color:#888;'>{leg}</p>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "ISPOD 0 = BULLISH")
draw_idx(v2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "ISPOD 0 = BULLISH")
draw_idx(v3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "IZNAD 0 = BULLISH")

# --- 4. FUNDAMENTALS ---
st.subheader("🛢️ Fundamental Intelligence")
if eia_data:
    f1, f2 = st.columns(2)
    f1.metric("Storage", f"{eia_data['stor']} Bcf", f"{eia_data['stor_chg']} Bcf", delta_color="inverse")
    f2.metric("vs 5y Avg", f"{eia_data['stor_5y']:+} Bcf", delta_color="inverse")
else:
    st.warning("EIA podaci nisu dohvaćeni. Provjeri API ključ ili status servera.")
