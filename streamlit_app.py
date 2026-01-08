import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V50", layout="wide")

# Kontrola osvježavanja
with st.sidebar:
    st.header("⚙️ Postavke")
    pause_refresh = st.checkbox("Pauziraj auto-osvježavanje", value=False)
    
if not pause_refresh:
    st.markdown("<head><meta http-equiv='refresh' content='120'></head>", unsafe_allow_html=True)

# STEALTH CSS (Bez em-dasha, visoki kontrast)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    header, [data-testid="stHeader"] { background-color: #000000 !important; }
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
@st.cache_data(ttl=600)
def get_price(ticker):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}", headers={'User-Agent': 'Mozilla/5.0'})
        m = r.json()['chart']['result'][0]['meta']
        return m['regularMarketPrice'], ((m['regularMarketPrice'] - m['previousClose']) / m['previousClose']) * 100
    except: return 0.0, 0.0

@st.cache_data(ttl=3600)
def get_eia_fortress():
    try:
        u_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&facets[series][]=NW2_EPG0_SWO_R48_BCF&sort[0][column]=period&sort[0][direction]=desc&length=10"
        u_p = f"https://api.eia.gov/v2/natural-gas/prod/dry/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        u_e = f"https://api.eia.gov/v2/natural-gas/move/exp/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&facets[process][]=N9011US2&sort[0][column]=period&sort[0][direction]=desc&length=2"
        s_res = requests.get(u_s).json()['response']['data']
        p_res = requests.get(u_p).json()['response']['data']
        e_res = requests.get(u_e).json()['response']['data']
        c_s = int(s_res[0]['value'])
        avg5y = pd.DataFrame(s_res)['value'].astype(int).mean()
        return {
            "stor": c_s, "stor_chg": c_s - int(s_res[1]['value']), "stor_5y": c_s - int(avg5y),
            "prod": float(p_res[0]['value']) / 30, "prod_chg": (float(p_res[0]['value']) - float(p_res[1]['value'])) / 30,
            "lng": float(e_res[0]['value']) / 30, "lng_chg": (float(e_res[0]['value']) - float(e_res[1]['value'])) / 30
        }
    except: return None

def get_nasdaq_data():
    try:
        u_cot = f"https://data.nasdaq.com/api/v3/datasets/CFTC/023651_F_L_ALL.json?api_key={NASDAQ_API_KEY}&limit=1"
        u_rig = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS.json?api_key={NASDAQ_API_KEY}&limit=2"
        cot_d = requests.get(u_cot).json()['dataset']['data'][0]
        rig_d = requests.get(u_rig).json()['dataset']['data']
        return {
            "nc_l": int(cot_d[12]), "nc_s": int(cot_d[13]),
            "c_l": int(cot_d[5]) + int(cot_d[8]), "c_s": int(cot_d[6]) + int(cot_d[9]),
            "nr_l": int(cot_d[20]), "nr_s": int(cot_d[21]),
            "rigs": int(rig_d[0][1]), "rig_chg": int(rig_d[0][1]) - int(rig_d[1][1])
        }
    except: return None

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=5)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        v = df[df.columns[-1]].tolist()
        return {"now": v[-1], "y": v[-2], "w": v[-8]}
    except: return {"now": 0.0, "y": 0.0, "w": 0.0}

# --- SIDEBAR & COT FORM ---
with st.sidebar:
    st.header("🌎 Global Hubs")
    ng_p, ng_pct = get_price("NG=F")
    ttf_p, ttf_pct = get_price("TTF=F")
    st.metric("Henry Hub", f"${ng_p:.3f}", f"{ng_pct:+.2f}%")
    st.metric("Dutch TTF", f"€{ttf_p:.2f}", f"{ttf_pct:+.2f}%")
    arb_spread = (ttf_p * 1.08 / 3.41) - ng_p
    st.metric("US-EU Arb Spread", f"${arb_spread:.2f}")

    st.markdown("---")
    nasdaq = get_nasdaq_data()
    with st.form("cot_form"):
        st.header("🏛️ COT Intelligence")
        nc_l = st.number_input("Managed Money Long", value=nasdaq['nc_l'] if nasdaq else 288456)
        nc_s = st.number_input("Managed Money Short", value=nasdaq['nc_s'] if nasdaq else 424123)
        c_l = st.number_input("Commercial Long", value=nasdaq['c_l'] if nasdaq else 512000)
        c_s = st.number_input("Commercial Short", value=nasdaq['c_s'] if nasdaq else 380000)
        nr_l = st.number_input("Retail Long", value=nasdaq['nr_l'] if nasdaq else 54120)
        nr_s = st.number_input("Retail Short", value=nasdaq['nr_s'] if nasdaq else 32100)
        submitted = st.form_submit_button("POTVRDI I ANALIZIRAJ")

# --- OBRADA PODATAKA ZA NARRATIVE (Display Layer) ---
eia = get_eia_fortress()
ao_d = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao_d = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")

# Sigurna priprema stringova za Narrative kako bi izbjegli TypeError
nc_net = nc_l - nc_s
c_net = c_l - c_s
prod_str = f"{eia['prod']:.1f} Bcf/d" if eia else "N/A"
prod_chg_str = f"{eia['prod_chg']:+.1f}" if eia else "N/A"
lng_str = f"{eia['lng']:.1f} Bcf/d" if eia else "N/A"
stor_5y_str = f"{eia['stor_5y']:+}" if eia else "N/A"
rig_val_str = f"{nasdaq['rigs']}" if nasdaq else "N/A"
rig_chg_str = f"({nasdaq['rig_chg']:+})" if nasdaq else ""

# --- 1. EXECUTIVE STRATEGIC NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
narrative = f"""
Tržište operira pri cijeni od **${ng_p:.3f}**. Managed Money neto pozicija iznosi **{nc_net:+,}**, dok su Commercials na **{c_net:+,}**. 
Dnevna proizvodnja iznosi **{prod_str}** ({prod_chg_str} promjena), uz LNG izvoz od **{lng_str}**. 

Zalihe plina su na **{stor_5y_str} Bcf** u odnosu na petogodišnji prosjek. 
AO Index ({ao_d['now']:+.2f}) je u statusu **{'BULLISH' if ao_d['now'] < ao_d['y'] else 'BEARISH'}** (momentum vs jučer). 
Arbitražni spread od **${arb_spread:.2f}** i Rig Count od **{rig_val_str}** {rig_chg_str} definiraju fundamentalno dno.
"""
st.markdown(f"<div class='summary-narrative'>{narrative}</div>", unsafe_allow_html=True)

# --- 2. NOAA DUAL RADAR TABS ---
t1, t2 = st.tabs(["🌡️ Temperature Outlook", "🌧️ Precipitation Outlook"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d")
with t2:
    p1, p2 = st.columns(2)
    p1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Oborine")
    p2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d Oborine")

# --- 3. ATMOSPHERIC INDEX & VELOCITY ---
st.subheader("📈 Index Forecast Trends")
v1, v2 = st.columns(2)
def draw_idx(col, title, d, leg):
    with col:
        st.image(f"https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/{title.lower()}.sprd2.gif")
        bias = "BULLISH" if d['now'] < -0.4 else "BEARISH" if d['now'] > 0.4 else "NEUTRAL"
        cl = "bull-text" if bias == "BULLISH" else "bear-text" if bias == "BEARISH" else ""
        st.markdown(f"**{title} Index: {d['now']:.2f}** (<span class='status-box {cl}'>{bias}</span>)", unsafe_allow_html=True)
        y_d = d['now'] - d['y']
        y_col = "#00FF00" if y_d < 0 else "#FF4B4B"
        st.markdown(f"<div style='font-size:0.85rem; margin-top:10px;'><span style='color:{y_col}'>vs yest: {y_d:+.2f}</span> | vs week: {d['now']-d['w']:+.2f}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='legend-text'>{leg}</div>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao_d, "Crna linija ISPOD 0 = HLADNIJE (BULLISH)")
draw_idx(v2, "NAO", nao_d, "Crna linija ISPOD 0 = HLADNIJE (BULLISH)")

# --- 4. EIA & SUPPLY FUNDAMENTALS ---
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
        if nasdaq: st.metric("Rig Count", f"{nasdaq['rigs']}", f"{nasdaq['rig_chg']:+}")
    with col3 if 'col3' in locals() else f3:
        st.write("**EXPORT**")
        st.metric("LNG Exports", f"{eia['lng']:.1f} Bcf/d", f"{eia['lng_chg']:+.1f}")
else:
    st.error("EIA podaci privremeno nedostupni.")
