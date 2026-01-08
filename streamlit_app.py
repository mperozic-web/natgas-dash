import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V54", layout="wide")

# CSS (Strogo pridržavanje: nema em-dasha)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; background-color: #0A0A0A; }
    .status-box { padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.9rem; border: 1px solid #444; }
    .bull-text { color: #00FF00 !important; border-color: #00FF00 !important; }
    .bear-text { color: #FF4B4B !important; border-color: #FF4B4B !important; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    .debug-text { color: #FFA500; font-family: monospace; font-size: 0.75rem; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
NASDAQ_API_KEY = "sbgqUxBu5AfRNxSGQsky"

# --- CORE DATA ENGINES ---

def fetch_nasdaq():
    """Dohvat COT i Rig Count podataka s preciznim mapiranjem"""
    try:
        # 1. COT Dataset (Natural Gas Physical - Disaggregated)
        u_cot = f"https://data.nasdaq.com/api/v3/datasets/CFTC/023651_F_L_ALL/data.json?api_key={NASDAQ_API_KEY}&limit=1"
        r_cot = requests.get(u_cot).json()
        c_data = r_cot['dataset_data']['data'][0]
        
        # 2. Rig Count (Natural Gas US)
        u_rig = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS/data.json?api_key={NASDAQ_API_KEY}&limit=2"
        r_rig = requests.get(u_rig).json()
        rig_data = r_rig['dataset_data']['data']
        
        return {
            "nc_l": int(c_data[12]), "nc_s": int(c_data[13]),
            "c_l": int(c_data[5]) + int(c_data[8]), "c_s": int(c_data[6]) + int(c_data[9]),
            "nr_l": int(c_data[20]), "nr_s": int(c_data[21]),
            "rigs": int(rig_data[0][1]), "rig_chg": int(rig_data[0][1]) - int(rig_data[1][1])
        }
    except Exception as e:
        st.sidebar.error(f"Nasdaq Fail: {str(e)[:50]}")
        return None

def fetch_eia():
    """EIA V2 Engine s odvojenim pozivima za stabilnost"""
    try:
        headers = {"X-Params": "true"} # Neki EIA v2 endpointi zahtijevaju specificiranje parametara
        
        # Zalihe (Weekly)
        u_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=10"
        # Proizvodnja (Monthly)
        u_p = f"https://api.eia.gov/v2/natural-gas/prod/dry/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        # LNG Izvoz (Monthly)
        u_e = f"https://api.eia.gov/v2/natural-gas/move/exp/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        
        s_r = requests.get(u_s).json()['response']['data']
        p_r = requests.get(u_p).json()['response']['data']
        e_r = requests.get(u_e).json()['response']['data']
        
        curr_s = int(s_r[0]['value'])
        return {
            "stor": curr_s, "stor_chg": curr_s - int(s_r[1]['value']),
            "stor_5y": curr_s - int(pd.DataFrame(s_r)['value'].astype(int).mean()),
            "prod": float(p_r[0]['value']) / 30, "prod_chg": (float(p_r[0]['value']) - float(p_r[1]['value'])) / 30,
            "lng": float(e_r[0]['value']) / 30
        }
    except Exception as e:
        st.sidebar.error(f"EIA Fail: {str(e)[:50]}")
        return None

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=5)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return {"now": df.iloc[-1, -1], "yest": df.iloc[-2, -1]}
    except: return {"now": 0.0, "yest": 0.0}

# --- SIDEBAR & GLOBAL DATA ---
with st.sidebar:
    st.header("⚡ System Control")
    # Live Price (Yahoo)
    try:
        ng_p = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers={'User-Agent': 'Mozilla/5.0'}).json()['chart']['result'][0]['meta']['regularMarketPrice']
        st.metric("Henry Hub", f"${ng_p:.3f}")
    except: ng_p = 0.0

    nas_data = fetch_nasdaq()
    eia_data = fetch_eia()
    
    with st.form("cot_form"):
        st.header("🏛️ COT Center")
        nc_l = st.number_input("NC Long", value=nas_data['nc_l'] if nas_data else 288456)
        nc_s = st.number_input("NC Short", value=nas_data['nc_s'] if nas_data else 424123)
        st.form_submit_button("POTVRDI UNOS")

# --- DATA PROCESSING ---
ao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
prod_str = f"{eia_data['prod']:.1f} Bcf/d" if eia_data else "N/A"
stor_5y = f"{eia_data['stor_5y']:+}" if eia_data else "N/A"
rigs_str = f"{nas_data['rigs']}" if nas_data else "N/A"

st.markdown(f"""
<div class='summary-narrative'>
    Tržište operira pri <strong>${ng_p:.3f}</strong>. Managed Money neto pozicija: <strong>{nc_net:+,}</strong>.<br>
    Dnevna proizvodnja: <strong>{prod_str}</strong>. Zalihe u odnosu na 5y prosjek: <strong>{stor_5y} Bcf</strong>.<br>
    AO Index: <strong>{ao['now']:+.2f}</strong>. Status Rig Counta: <strong>{rigs_str}</strong>.
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

# --- 3. ATMOSPHERIC INDEX TRENDS ---
st.subheader("📈 Index Forecast Trends")
v1, v2, v3 = st.columns(3)

def draw_idx(col, title, d, img_url, leg):
    with col:
        st.image(img_url)
        bias = "BULLISH" if (d['now'] < -0.4 if title != "PNA" else d['now'] > 0.4) else "BEARISH"
        cl = "bull-text" if bias == "BULLISH" else "bear-text"
        st.markdown(f"**{title}: {d['now']:.2f}** (<span class='{cl}'>{bias}</span>)", unsafe_allow_html=True)
        st.write(f"Trend: {'Jačanje' if abs(d['now']) > abs(d['yest']) else 'Slabljenje'}")
        st.markdown(f"<div style='font-size:0.8rem; color:#888;'>{leg}</div>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "ISPOD 0 = HLADNIJE")
# NAO fiksiran URL
draw_idx(v2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "ISPOD 0 = HLADNIJE")
draw_idx(v3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "IZNAD 0 = HLADNIJE")

# --- 4. FUNDAMENTAL INTELLIGENCE ---
st.subheader("🛢️ Fundamental Intelligence")
if eia_data:
    f1, f2, f3 = st.columns(3)
    f1.metric("Storage", f"{eia_data['stor']} Bcf", f"{eia_data['stor_chg']} Bcf", delta_color="inverse")
    f2.metric("Production", f"{eia_data['prod']:.1f} Bcf/d", f"{eia_data['prod_chg']:+.1f}")
    if nas_data: f3.metric("Rig Count", f"{nas_data['rigs']}", f"{nas_data['rig_chg']:+}")
else:
    st.warning("EIA podaci nisu dohvaćeni. Provjeri API status.")
