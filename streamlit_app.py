import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V57", layout="wide")

# CSS (Strogo bez em-dasha)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; padding-bottom: 8px; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; background-color: #0A0A0A; }
    .status-box { padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.9rem; border: 1px solid #444; }
    .bull-text { color: #00FF00 !important; border-color: #00FF00 !important; }
    .bear-text { color: #FF4B4B !important; border-color: #FF4B4B !important; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    .stMetricValue { font-size: 1.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
NASDAQ_API_KEY = "sbgqUxBu5AfRNxSGQsky"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- DATA ENGINES ---

def fetch_nasdaq_raw():
    try:
        # COT Natural Gas (NYMEX)
        url_c = f"https://data.nasdaq.com/api/v3/datasets/CFTC/023651_F_L_ALL.csv?api_key={NASDAQ_API_KEY}&limit=1"
        df_c = pd.read_csv(url_c)
        # Rig Count
        url_r = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS.csv?api_key={NASDAQ_API_KEY}&limit=2"
        df_r = pd.read_csv(url_r)
        
        return {
            "nc_l": int(df_c.iloc[0, 12]), # Managed Money Long
            "nc_s": int(df_c.iloc[0, 13]), # Managed Money Short
            "rigs": int(df_r.iloc[0, 1]),
            "rig_chg": int(df_r.iloc[0, 1]) - int(df_r.iloc[1, 1])
        }
    except: return None

def fetch_eia_basic():
    try:
        # storage weekly - v2 API ali s minimalnim parametrima
        url = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=5"
        r = requests.get(url, timeout=10).json()
        data = r['response']['data']
        curr = int(data[0]['value'])
        avg5y = pd.DataFrame(data)['value'].astype(int).mean()
        return {"curr": curr, "chg": curr - int(data[1]['value']), "v5y": curr - int(avg5y)}
    except: return None

def get_noaa_csv(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return {"now": df.iloc[-1, -1], "yest": df.iloc[-2, -1]}
    except: return {"now": 0.0, "yest": 0.0}

# --- SIDEBAR & CORE DATA ---
with st.sidebar:
    st.header("⚡ Live Core")
    try:
        # Live cijena s Yahooa (Henry Hub)
        p_res = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()
        price = p_res['chart']['result'][0]['meta']['regularMarketPrice']
        st.metric("Henry Hub Live", f"${price:.3f}")
    except: price = 0.0

    nas = fetch_nasdaq_raw()
    eia = fetch_eia_basic()
    
    with st.form("cot_form"):
        st.header("🏛️ COT Manual")
        val_l = nas['nc_l'] if nas else 288456
        val_s = nas['nc_s'] if nas else 424123
        nc_l = st.number_input("NC Long", value=val_l)
        nc_s = st.number_input("NC Short", value=val_s)
        st.form_submit_button("ANALIZIRAJ")

# --- ANALITIČKI MODULI ---
ao = get_noaa_csv("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_csv("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_csv("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE STRATEGIC NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
s_5y = f"{eia['v5y']:+}" if eia else "N/A"
rig_val = f"{nas['rigs']}" if nas else "N/A"

st.markdown(f"""
<div class='summary-narrative'>
    NG operira pri cijeni od <strong>${price:.3f}</strong>. Managed Money neto pozicija: <strong>{nc_net:+,}</strong>.<br>
    Zalihe u odnosu na 5y prosjek: <strong>{s_5y} Bcf</strong>. Trenutni Rig Count: <strong>{rig_val}</strong>.<br>
    AO Indeks: <strong>{ao['now']:+.2f}</strong>. Status: {'BULLISH' if ao['now'] < ao['yest'] else 'BEARISH'}.
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA DUAL RADAR ---
t1, t2 = st.tabs(["🌡️ Temperature Outlook", "🌧️ Oborine (Precip)"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Outlook")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Outlook")
with t2:
    p1, p2 = st.columns(2)
    p1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Oborine")
    p2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d Oborine")

# --- 3. ATMOSPHERIC INDEX TRENDS ---
st.subheader("📈 Index Velocity & Forecast")
v1, v2, v3 = st.columns(3)

def draw_idx(col, title, d, url, leg):
    with col:
        st.image(url)
        st.markdown(f"**{title} Index: {d['now']:.2f}**")
        st.write(f"Trend: {'JAČANJE' if abs(d['now']) > abs(d['yest']) else 'SLABLJENJE'}")
        st.markdown(f"<p style='font-size:0.8rem; color:#888;'>{leg}</p>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "ISPOD 0 = BULLISH (HLADNIJE)")
draw_idx(v2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "ISPOD 0 = BULLISH (HLADNIJE)")
draw_idx(v3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "IZNAD 0 = BULLISH (HLADNIJE)")

# --- 4. FUNDAMENTAL INTELLIGENCE ---
st.subheader("🛢️ Supply & Storage Fundamentals")

if eia:
    f1, f2, f3 = st.columns(3)
    f1.metric("Zalihe (Storage)", f"{eia['curr']} Bcf", f"{eia['chg']} Bcf", delta_color="inverse")
    f2.metric("vs 5y Average", f"{eia['v5y']:+} Bcf", delta_color="inverse")
    if nas:
        f3.metric("NG Rig Count", f"{nas['rigs']}", f"{nas['rig_chg']:+}", delta_color="inverse")
else:
    st.warning("EIA podaci nisu dohvaćeni. Provjeri API ključ ili server status.")
