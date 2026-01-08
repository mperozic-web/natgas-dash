import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V62", layout="wide")

# CSS (Strogo bez em-dasha, visok kontrast)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; background-color: #0A0A0A; }
    .status-box { padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.9rem; border: 1px solid #444; }
    .bull-text { color: #00FF00 !important; border-color: #00FF00 !important; }
    .bear-text { color: #FF4B4B !important; border-color: #FF4B4B !important; }
    .debug-box { background-color: #1A0000; color: #FFA500; padding: 10px; border: 1px solid #FFA500; font-family: monospace; font-size: 0.7rem; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
NASDAQ_API_KEY = "Vxj869NUowFMm2j2ManG"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# --- DATA ENGINES ---

def fetch_nasdaq_v62():
    try:
        # COT Natural Gas Physical - CSV format za maksimalnu stabilnost
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
        st.sidebar.markdown(f"<div class='debug-box'>Nasdaq Error: {str(e)[:50]}</div>", unsafe_allow_html=True)
        return None

def fetch_eia_v62():
    try:
        # Zalihe Weekly - v2 API
        u_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=5"
        res = requests.get(u_s).json()
        d = res['response']['data']
        curr = int(d[0]['value'])
        avg5y = pd.DataFrame(d)['value'].astype(int).mean()
        return {"stor": curr, "chg": curr - int(d[1]['value']), "v5y": curr - int(avg5y)}
    except Exception as e:
        st.sidebar.markdown(f"<div class='debug-box'>EIA Error: {str(e)[:50]}</div>", unsafe_allow_html=True)
        return None

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return {"now": df.iloc[-1, -1], "yest": df.iloc[-2, -1]}
    except: return {"now": 0.0, "yest": 0.0}

# --- SIDEBAR & GLOBAL ---
with st.sidebar:
    st.header("🌎 Market Context")
    # Live cijena s Yahooa
    try:
        r_p = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()
        hh_p = r_p['chart']['result'][0]['meta']['regularMarketPrice']
        hh_prev = r_p['chart']['result'][0]['meta']['previousClose']
        hh_pct = ((hh_p - hh_prev) / hh_prev) * 100
        st.metric("Henry Hub", f"${hh_p:.3f}", f"{hh_pct:+.2f}%")
    except: hh_p = 0.0

    nas = fetch_nasdaq_v62()
    eia = fetch_eia_v62()
    
    with st.form("cot_form"):
        st.header("🏛️ COT Manual Override")
        nc_l = st.number_input("NC Long", value=nas['nc_l'] if nas else 288456)
        nc_s = st.number_input("NC Short", value=nas['nc_s'] if nas else 424123)
        st.form_submit_button("ANALIZIRAJ")

# --- ANALIZA ---
ao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
s_5y = f"{eia['v5y']:+}" if eia else "N/A"
st.markdown(f"""
<div class='summary-narrative'>
    NG operira pri cijeni od <strong>${hh_p:.3f}</strong>. Managed Money neto: <strong>{nc_l - nc_s:+,}</strong>.<br>
    Zalihe vs 5y prosjek: <strong>{s_5y} Bcf</strong>. AO Index: <strong>{ao['now']:+.2f}</strong>.<br>
    Status Rig Counta: <strong>{nas['rigs'] if nas else 'N/A'}</strong>.
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA DUAL RADAR ---
t1, t2 = st.tabs(["🌡️ Temperature Outlook", "🌧️ Oborine"])
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
        cl = "bull-text" if bias == "BULLISH" else "bear-text"
        st.markdown(f"**{title}: {d['now']:.2f}** (<span class='{cl}'>{bias}</span>)")
        st.markdown(f"<p style='font-size:0.8rem; color:#888;'>{leg}</p>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "ISPOD 0 = HLADNIJE")
draw_idx(v2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "ISPOD 0 = HLADNIJE")
draw_idx(v3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "IZNAD 0 = HLADNIJE")

# --- 4. FUNDAMENTALS ---
st.subheader("🛢️ Fundamental Intelligence")
if eia:
    f1, f2 = st.columns(2)
    f1.metric("Storage", f"{eia['stor']} Bcf", f"{eia['chg']} Bcf", delta_color="inverse")
    f2.metric("vs 5y Average", f"{eia['v5y']:+} Bcf", delta_color="inverse")
else:
    st.error("EIA podaci nisu dohvaćeni. Provjeri status servera ili ključ.")
