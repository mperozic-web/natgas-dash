import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V59", layout="wide")

# Kontrola osvježavanja
with st.sidebar:
    st.header("⚙️ Sustav")
    pause_refresh = st.checkbox("Pauziraj osvježavanje", value=False)
    
if not pause_refresh:
    st.markdown("<head><meta http-equiv='refresh' content='120'></head>", unsafe_allow_html=True)

# STEALTH CSS (Maksimalan kontrast, bez em-dasha)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.05rem; line-height: 1.7; color: #EEEEEE; border: 1px solid #444; padding: 25px; background-color: #0A0A0A; }
    .status-box { padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.9rem; border: 1px solid #444; }
    .bull-text { color: #00FF00 !important; border-color: #00FF00 !important; }
    .bear-text { color: #FF4B4B !important; border-color: #FF4B4B !important; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    .stMetricValue { font-size: 1.6rem !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
NASDAQ_API_KEY = "sbgqUxBu5AfRNxSGQsky"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- DATA ENGINES ---

def get_price_data(ticker):
    """Vraća cijenu i postotnu promjenu"""
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}", headers=HEADERS).json()
        meta = r['chart']['result'][0]['meta']
        price = meta['regularMarketPrice']
        prev = meta['previousClose']
        pct = ((price - prev) / prev) * 100
        return price, pct
    except: return 0.0, 0.0

def fetch_nasdaq_robust():
    """Povlači COT i Rig Count preko CSV-a (najstabilnije)"""
    try:
        u_c = f"https://data.nasdaq.com/api/v3/datasets/CFTC/023651_F_L_ALL.csv?api_key={NASDAQ_API_KEY}&limit=1"
        u_r = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS.csv?api_key={NASDAQ_API_KEY}&limit=2"
        df_c = pd.read_csv(u_c)
        df_r = pd.read_csv(u_r)
        return {
            "nc_l": int(df_c.iloc[0, 12]), "nc_s": int(df_c.iloc[0, 13]),
            "c_l": int(df_c.iloc[0, 5]) + int(df_c.iloc[0, 8]),
            "c_s": int(df_c.iloc[0, 6]) + int(df_c.iloc[0, 9]),
            "nr_l": int(df_c.iloc[0, 20]), "nr_s": int(df_c.iloc[0, 21]),
            "rigs": int(df_r.iloc[0, 1]), "rig_chg": int(df_r.iloc[0, 1]) - int(df_r.iloc[1, 1])
        }
    except: return None

def fetch_eia_fortress():
    """EIA V2 s odvojenim pozivima za maksimalnu sigurnost"""
    try:
        u_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=5"
        u_p = f"https://api.eia.gov/v2/natural-gas/prod/dry/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        u_e = f"https://api.eia.gov/v2/natural-gas/move/exp/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        
        s_d = requests.get(u_s).json()['response']['data']
        p_d = requests.get(u_p).json()['response']['data']
        e_d = requests.get(u_e).json()['response']['data']
        
        c_s = int(s_d[0]['value'])
        return {
            "stor": c_s, "stor_chg": c_s - int(s_d[1]['value']),
            "stor_5y": c_s - int(pd.DataFrame(s_d)['value'].astype(int).mean()),
            "prod": float(p_d[0]['value']) / 30, "prod_chg": (float(p_d[0]['value']) - float(p_d[1]['value'])) / 30,
            "lng": float(e_d[0]['value']) / 30, "lng_chg": (float(e_d[0]['value']) - float(e_d[1]['value'])) / 30
        }
    except: return None

def get_noaa_data(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return {"now": df.iloc[-1, -1], "y": df.iloc[-2, -1]}
    except: return {"now": 0.0, "y": 0.0}

# --- SIDEBAR: GLOBAL HUBS & COT ---
with st.sidebar:
    st.header("🌎 Global Hubs")
    hh_p, hh_pct = get_price_data("NG=F")
    ttf_p, ttf_pct = get_price_data("TTF=F")
    
    st.metric("Henry Hub (US)", f"${hh_p:.3f}", f"{hh_pct:+.2f}%")
    st.metric("Dutch TTF (EU)", f"€{ttf_p:.2f}", f"{ttf_pct:+.2f}%")
    
    # Preračun spreada
    ttf_usd = (ttf_p * 1.08) / 3.41
    spread = ttf_usd - hh_p
    st.metric("US-EU Arb Spread", f"${spread:.2f}")

    st.markdown("---")
    nas = fetch_nasdaq_robust()
    with st.form("cot_form"):
        st.header("🏛️ COT Center")
        nc_l = st.number_input("NC Long", value=nas['nc_l'] if nas else 288456)
        nc_s = st.number_input("NC Short", value=nas['nc_s'] if nas else 424123)
        st.form_submit_button("POTVRDI I ANALIZIRAJ")

# --- ANALIZA ---
eia = fetch_eia_fortress()
ao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
s_5y = f"{eia['stor_5y']:+}" if eia else "N/A"
p_val = f"{eia['prod']:.1f}" if eia else "N/A"
r_val = f"{nas['rigs']}" if nas else "N/A"

st.markdown(f"""
<div class='summary-narrative'>
    Henry Hub operira pri <strong>${hh_p:.3f}</strong> ({hh_pct:+.2f}%). Managed Money neto: <strong>{nc_net:+,}</strong>.<br>
    Dnevna proizvodnja: <strong>{p_val} Bcf/d</strong>. Zalihe vs 5y prosjek: <strong>{s_5y} Bcf</strong>. Rig Count: <strong>{r_val}</strong>.<br>
    Arbitražni spread prema Europi: <strong>${spread:.2f}/MMBtu</strong>. AO Index: <strong>{ao['now']:+.2f}</strong>.
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA DUAL RADAR TABS ---
t1, t2 = st.tabs(["🌡️ Temperature", "🌧️ Oborine"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Outlook")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Outlook")
with t2:
    p1, p2 = st.columns(2)
    p1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Oborine")
    p2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d Oborine")

# --- 3. INDEX TRENDS ---
st.subheader("📈 Index Forecast Trends")
v1, v2, v3 = st.columns(3)
def draw_idx(col, title, d, url, leg):
    with col:
        st.image(url)
        bias = "BULLISH" if (d['now'] < -0.4 if title != "PNA" else d['now'] > 0.4) else "BEARISH"
        cl = "bull-text" if bias == "BULLISH" else "bear-text"
        st.markdown(f"**{title} Index: {d['now']:.2f}** (<span class='{cl}'>{bias}</span>)")
        st.markdown(f"<p style='font-size:0.8rem; color:#888;'>{leg}</p>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "ISPOD 0 = HLADNIJE")
draw_idx(v2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "ISPOD 0 = HLADNIJE")
draw_idx(v3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "IZNAD 0 = HLADNIJE")

# --- 4. FUNDAMENTALS ---
st.subheader("🛢️ Fundamental Intelligence")
if eia:
    f1, f2, f3 = st.columns(3)
    with f1:
        st.metric("Storage", f"{eia['stor']} Bcf", f"{eia['stor_chg']} Bcf", delta_color="inverse")
        st.metric("vs 5y Average", f"{eia['stor_5y']:+} Bcf", delta_color="inverse")
    with f2:
        st.metric("Production", f"{eia['prod']:.1f} Bcf/d", f"{eia['prod_chg']:+.1f}")
        if nas: st.metric("Rig Count", f"{nas['rigs']}", f"{nas['rig_chg']:+}", delta_color="inverse")
    with f3:
        st.metric("LNG Exports", f"{eia['lng']:.1f} Bcf/d", f"{eia['lng_chg']:+.1f}")
