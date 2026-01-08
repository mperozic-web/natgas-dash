import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V58", layout="wide")

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

# --- DATA ENGINES ---

def fetch_nasdaq_all():
    try:
        # COT Natural Gas Physical (CSV je zakon ovdje)
        u_c = f"https://data.nasdaq.com/api/v3/datasets/CFTC/023651_F_L_ALL.csv?api_key={NASDAQ_API_KEY}&limit=1"
        df_c = pd.read_csv(u_c)
        # Rigs
        u_r = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS.csv?api_key={NASDAQ_API_KEY}&limit=2"
        df_r = pd.read_csv(u_r)
        
        # Mapiranje neto pozicija
        return {
            "nc_l": int(df_c.iloc[0, 12]), "nc_s": int(df_c.iloc[0, 13]),
            "c_l": int(df_c.iloc[0, 5]) + int(df_c.iloc[0, 8]),
            "c_s": int(df_c.iloc[0, 6]) + int(df_c.iloc[0, 9]),
            "nr_l": int(df_c.iloc[0, 20]), "nr_s": int(df_c.iloc[0, 21]),
            "rigs": int(df_r.iloc[0, 1]), "rig_chg": int(df_r.iloc[0, 1]) - int(df_r.iloc[1, 1])
        }
    except: return None

def fetch_eia_fortress():
    try:
        # 1. Zalihe (Weekly)
        u_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=5"
        # 2. Proizvodnja (Monthly)
        u_p = f"https://api.eia.gov/v2/natural-gas/prod/dry/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        # 3. Izvoz (Monthly)
        u_e = f"https://api.eia.gov/v2/natural-gas/move/exp/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
        
        s_data = requests.get(u_s).json()['response']['data']
        p_data = requests.get(u_p).json()['response']['data']
        e_data = requests.get(u_e).json()['response']['data']
        
        c_s = int(s_data[0]['value'])
        return {
            "stor": c_s, "stor_chg": c_s - int(s_data[1]['value']),
            "stor_5y": c_s - int(pd.DataFrame(s_data)['value'].astype(int).mean()),
            "prod": float(p_data[0]['value']) / 30, "prod_chg": (float(p_data[0]['value']) - float(p_data[1]['value'])) / 30,
            "lng": float(e_data[0]['value']) / 30, "lng_chg": (float(e_data[0]['value']) - float(e_data[1]['value'])) / 30
        }
    except: return None

def get_noaa_v(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return {"now": df.iloc[-1, -1], "y": df.iloc[-2, -1]}
    except: return {"now": 0.0, "y": 0.0}

# --- SIDEBAR & CORE DATA ---
with st.sidebar:
    st.header("⚡ Live Market")
    try:
        p_res = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers={'User-Agent': 'Mozilla/5.0'}).json()
        price = p_res['chart']['result'][0]['meta']['regularMarketPrice']
        st.metric("Henry Hub Live", f"${price:.3f}")
    except: price = 0.0

    nas = fetch_nasdaq_all()
    eia = fetch_eia_fortress()
    
    with st.form("cot_form"):
        st.header("🏛️ COT Intelligence")
        nc_l = st.number_input("Managed Money Long", value=nas['nc_l'] if nas else 288456)
        nc_s = st.number_input("Managed Money Short", value=nas['nc_s'] if nas else 424123)
        c_l = st.number_input("Commercial Long", value=nas['c_l'] if nas else 512000)
        c_s = st.number_input("Commercial Short", value=nas['c_s'] if nas else 380000)
        nr_l = st.number_input("Retail Long", value=nas['nr_l'] if nas else 54120)
        nr_s = st.number_input("Retail Short", value=nas['nr_s'] if nas else 32100)
        st.form_submit_button("POTVRDI UNOS")

# --- ANALIZA ---
ao = get_noaa_v("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_v("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_v("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE STRATEGIC NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
c_net = c_l - c_s
s_5y = f"{eia['stor_5y']:+}" if eia else "N/A"
prod_val = f"{eia['prod']:.1f}" if eia else "N/A"
rig_val = f"{nas['rigs']}" if nas else "N/A"

st.markdown(f"""
<div class='summary-narrative'>
    Tržište operira pri cijeni od <strong>${price:.3f}</strong>. Managed Money neto: <strong>{nc_net:+,}</strong>, Commercials neto: <strong>{c_net:+,}</strong>.<br>
    Dnevna proizvodnja: <strong>{prod_val} Bcf/d</strong>. Zalihe vs 5y prosjek: <strong>{s_5y} Bcf</strong>. Rig Count: <strong>{rig_val}</strong>.<br>
    AO Index: <strong>{ao['now']:+.2f}</strong>. Status: {'BULLISH' if ao['now'] < ao['y'] else 'BEARISH'}.
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

# --- 3. INDEX FORECAST MOMENTUM ---
st.subheader("📈 Index Forecast Trends")
v1, v2, v3 = st.columns(3)
def draw_idx(col, title, d, url, leg):
    with col:
        st.image(url)
        bias = "BULLISH" if (d['now'] < -0.4 if title != "PNA" else d['now'] > 0.4) else "BEARISH"
        cl = "bull-text" if bias == "BULLISH" else "bear-text"
        st.markdown(f"**{title} Index: {d['now']:.2f}** (<span class='{cl}'>{bias}</span>)", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:0.8rem; color:#888;'>{leg}</p>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "ISPOD 0 = HLADNIJE")

draw_idx(v2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "ISPOD 0 = HLADNIJE")
draw_idx(v3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "IZNAD 0 = HLADNIJE")

# --- 4. FUNDAMENTAL INTELLIGENCE ---
st.subheader("🛢️ Supply & Storage Fundamentals")

if eia:
    f1, f2, f3 = st.columns(3)
    with f1:
        st.write("**STORAGE**")
        st.metric("Zalihe", f"{eia['stor']} Bcf", f"{eia['stor_chg']} Bcf", delta_color="inverse")
        st.metric("vs 5y Average", f"{eia['stor_5y']:+} Bcf", delta_color="inverse")
    with f2:
        st.write("**SUPPLY**")
        st.metric("Production", f"{eia['prod']:.1f} Bcf/d", f"{eia['prod_chg']:+.1f}")
        if nas: st.metric("Rig Count", f"{nas['rigs']}", f"{nas['rig_chg']:+}", delta_color="inverse")
    with f3:
        st.write("**EXPORT**")
        st.metric("LNG Exports", f"{eia['lng']:.1f} Bcf/d", f"{eia['lng_chg']:+.1f}")
