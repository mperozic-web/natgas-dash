import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V53", layout="wide")

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
    .diag-box { background-color: #1A0000; color: #FF4B4B; padding: 10px; border: 1px solid #FF4B4B; font-family: monospace; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
NASDAQ_API_KEY = "sbgqUxBu5AfRNxSGQsky"

# --- DIAGNOSTIC WRAPPER ---
def safe_request(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            st.sidebar.error(f"Error {r.status_code}: {url[:40]}...")
            return None
    except Exception as e:
        st.sidebar.error(f"Exception: {str(e)[:50]}")
        return None

# --- DOHVAT PODATAKA ---
@st.cache_data(ttl=3600)
def get_nasdaq_hardened():
    # Korištenje /data.json za robusniji dohvat
    u_c = f"https://data.nasdaq.com/api/v3/datasets/CFTC/023651_F_L_ALL/data.json?api_key={NASDAQ_API_KEY}&limit=1"
    u_r = f"https://data.nasdaq.com/api/v3/datasets/BAKERHUGHES/RIGS_US_NATURAL_GAS/data.json?api_key={NASDAQ_API_KEY}&limit=2"
    
    c_res = safe_request(u_c)
    r_res = safe_request(u_r)
    
    if c_res and r_res:
        c_val = c_res['dataset_data']['data'][0]
        r_val = r_res['dataset_data']['data']
        return {
            "nc_l": int(c_val[12]), "nc_s": int(c_val[13]),
            "c_l": int(c_val[5]) + int(c_val[8]), "c_s": int(c_val[6]) + int(c_val[9]),
            "nr_l": int(c_val[20]), "nr_s": int(c_val[21]),
            "rigs": int(r_val[0][1]), "rig_chg": int(r_val[0][1]) - int(r_val[1][1])
        }
    return None

@st.cache_data(ttl=1800)
def get_eia_hardened():
    # Eksplicitni parametri za EIA V2
    u_s = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=5"
    u_p = f"https://api.eia.gov/v2/natural-gas/prod/dry/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
    u_e = f"https://api.eia.gov/v2/natural-gas/move/exp/data/?api_key={EIA_API_KEY}&frequency=monthly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=2"
    
    s_r = safe_request(u_s)
    p_r = safe_request(u_p)
    e_r = safe_request(u_e)
    
    if s_r and p_r and e_r:
        s_d = s_r['response']['data']
        p_d = p_r['response']['data']
        e_d = e_r['response']['data']
        c_s = int(s_d[0]['value'])
        return {
            "stor": c_s, "stor_chg": c_s - int(s_d[1]['value']),
            "stor_5y": c_s - int(pd.DataFrame(s_d)['value'].astype(int).mean()),
            "prod": float(p_d[0]['value'])/30, "prod_chg": (float(p_d[0]['value']) - float(p_d[1]['value']))/30,
            "lng": float(e_d[0]['value'])/30, "lng_chg": (float(e_d[0]['value']) - float(e_d[1]['value']))/30
        }
    return None

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=5)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        v = df[df.columns[-1]].tolist()
        return {"now": v[-1], "y": v[-2]}
    except: return {"now": 0.0, "y": 0.0}

# --- SIDEBAR & GLOBAL ---
with st.sidebar:
    st.header("🌍 Global Hubs")
    # Live cijene (Yahoo)
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers={'User-Agent': 'Mozilla/5.0'})
        ng_p = r.json()['chart']['result'][0]['meta']['regularMarketPrice']
    except: ng_p = 0.0
    st.metric("Henry Hub", f"${ng_p:.3f}")

    nasdaq = get_nasdaq_hardened()
    st.markdown("---")
    with st.form("cot_form"):
        st.header("🏛️ COT Intelligence")
        nc_l = st.number_input("NC Long", value=nasdaq['nc_l'] if nasdaq else 288456)
        nc_s = st.number_input("NC Short", value=nasdaq['nc_s'] if nasdaq else 424123)
        st.form_submit_button("POTVRDI")

# --- ANALIZA ---
eia = get_eia_hardened()
ao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE NARRATIVE ---
st.subheader("📋 Executive Strategic Narrative")
nc_net = nc_l - nc_s
p_val = f"{eia['prod']:.1f}" if eia else "ERR"
s_5y = f"{eia['stor_5y']:+}" if eia else "ERR"

st.markdown(f"""
<div class='summary-narrative'>
    NG operira pri <strong>${ng_p:.3f}</strong>. Managed Money neto: <strong>{nc_net:+,}</strong>.<br>
    Proizvodnja: <strong>{p_val} Bcf/d</strong>. Zalihe vs 5y: <strong>{s_5y} Bcf</strong>.<br>
    AO Index: <strong>{ao['now']:+.2f}</strong>. Status: {'BULLISH' if ao['now'] < ao['y'] else 'BEARISH'}.
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA TABS (FIXED URLS) ---
t1, t2 = st.tabs(["🌡️ Temperature", "🌧️ Precipitation"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d")
with t2:
    p1, p2 = st.columns(2)
    p1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d")
    p2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d")

# --- 3. INDEX TRENDS (FIXED NAO URL) ---
st.subheader("📈 Index Forecast Trends")
v1, v2, v3 = st.columns(3)

def draw_idx(col, title, d, img_url, leg):
    with col:
        st.image(img_url)
        st.markdown(f"**{title}: {d['now']:.2f}**")
        st.markdown(f"<p class='legend-text'>{leg}</p>", unsafe_allow_html=True)

draw_idx(v1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "ISPOD 0 = BULLISH")
# NAO špageti su često u pna direktoriju na NOAA serveru
draw_idx(v2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "ISPOD 0 = BULLISH")
draw_idx(v3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "IZNAD 0 = BULLISH")

# --- 4. FUNDAMENTALS (SAFE MODULE) ---
st.subheader("🛢️ Fundamental Intelligence")
if eia:
    f1, f2, f3 = st.columns(3)
    f1.metric("Storage", f"{eia['stor']} Bcf", f"{eia['stor_chg']} Bcf", delta_color="inverse")
    f2.metric("Production", f"{eia['prod']:.1f} Bcf/d", f"{eia['prod_chg']:+.1f}")
    if nasdaq: f3.metric("Rig Count", f"{nasdaq['rigs']}", f"{nasdaq['rig_chg']:+}")
else:
    st.markdown("<div class='diag-box'>DIAGNOSTIKA: EIA API nije vratio podatke. Provjeri ključ u kodu.</div>", unsafe_allow_html=True)
