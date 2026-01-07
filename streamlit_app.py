import streamlit as st
import pandas as pd
import requests
import io
import re

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V9.0", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; text-transform: uppercase; }
    .stAlert { padding: 0.4rem !important; border-radius: 8px; }
    h3 { font-size: 1.1rem !important; color: #1E1E1E; margin-bottom: 0.6rem; border-bottom: 2px solid #3498db; width: fit-content; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. DIREKTNI COT SCRAPER (CFTC HTML) ---
def get_cot_from_html():
    try:
        url = "https://www.cftc.gov/dea/futures/nat_gas_lf.htm"
        r = requests.get(url, timeout=15)
        text = r.text
        
        # Tražimo sekciju za NYMEX Natural Gas
        section = re.search(r"NATURAL GAS - NEW YORK MERCANTILE EXCHANGE(.*?)Total", text, re.DOTALL)
        if not section: return None
        
        content = section.group(1)
        
        # Ekstrakcija brojeva iz Non-Commercial reda (Long, Short)
        # Tražimo prvi red s brojkama nakon Non-Commercial zaglavlja
        lines = content.split('\n')
        pos_line = ""
        for line in lines:
            if re.search(r"\d", line) and len(line.split()) > 5:
                pos_line = line
                break
        
        nums = re.findall(r"(\d{1,3}(?:,\d{3})*)", pos_line)
        nums = [int(n.replace(',', '')) for n in nums]
        
        # Legacy Format: Non-Commercial Long [0], Non-Commercial Short [1], Non-Reportable Long [6], Non-Reportable Short [7]
        mm_net = nums[0] - nums[1]
        ret_net = nums[6] - nums[7]
        
        # Ekstrakcija datuma
        date_match = re.search(r"(\w+ \d+, \d{4})", text)
        date_str = date_match.group(1) if date_match else "Nepoznat datum"
        
        return {"mm_net": mm_net, "ret_net": ret_net, "date": date_str}
    except Exception as e:
        return None

# --- 2. NOAA INDEKSI I INTERPRETACIJA ---
def interpret_noaa(name, val):
    val = float(val)
    res = {"status": "NEUTRAL", "color": "off", "bias": "Neutral"}
    if name == "AO":
        if val < -1.5: res = {"status": "JAKO BULLISH", "color": "normal", "bias": "Long"}
        elif val > 1.5: res = {"status": "JAKO BEARISH", "color": "inverse", "bias": "Short"}
    elif name == "NAO":
        if val < -0.8: res = {"status": "BULLISH", "color": "normal", "bias": "Long"}
        elif val > 0.8: res = {"status": "BEARISH", "color": "inverse", "bias": "Short"}
    elif name == "PNA":
        if val > 0.8: res = {"status": "BULLISH", "color": "normal", "bias": "Long"}
        elif val < -0.8: res = {"status": "BEARISH", "color": "inverse", "bias": "Short"}
    return res

def get_noaa_data(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        val = float(lt[val_col])
        interp = interpret_noaa(name, val)
        return {"val": val, **interp}
    except: return None

# --- 3. EIA STORAGE ---
def get_eia_storage(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 250}
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        df['val'] = df['value'].astype(int)
        df['week'] = pd.to_datetime(df['period']).dt.isocalendar().week
        curr = df.iloc[0]
        avg_5y = int(df.iloc[52:][df.iloc[52:]['week'] == curr['week']].head(5)['val'].mean())
        return {"val": curr['val'], "chg": curr['val'] - df.iloc[1]['val'], "diff": curr['val'] - avg_5y, "date": pd.to_datetime(curr['period']).strftime("%d.%m.%Y")}
    except: return None

# --- DOHVAT PODATAKA ---
ao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
storage = get_eia_storage(EIA_API_KEY)
cot = get_cot_from_html()

# --- UI DISPLAY ---
st.title("🛡️ Institutional Sniper Mirror V9.0")

# 1. MASTER BIAS BAR
st.subheader("🏁 Globalni Tržišni Bias")
b1, b2, b3 = st.columns(3)
with b1:
    m_bias = ao['bias'] if ao else "N/A"
    st.info(f"🌍 METEO BIAS: {m_bias}")
with b2:
    s_bias = "BULLISH" if (storage and storage['diff'] < 0) else "BEARISH"
    st.info(f"🛢️ STORAGE BIAS: {s_bias}")
with b3:
    c_bias = "SQUEEZE RISK" if (cot and cot['mm_net'] < -140000) else "BEARISH" if (cot and cot['mm_net'] > 0) else "NEUTRAL"
    st.info(f"🏛️ COT SENTIMENT: {c_bias}")

st.markdown("---")

# 2. PROGRESIJA TEMPERATURE (PROGRESIVNI FILTR)
st.subheader("🗺️ Forecast Progression (6-10d vs 8-14d)")
m_col1, m_col2 = st.columns(2)
m_col1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", use_container_width=True, caption="Trend 6-10 dana")
m_col2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", use_container_width=True, caption="Trend 8-14 dana")

st.markdown("---")

# 3. NOAA INDEKSI I COT
c_idx, c_cot = st.columns([2, 1])
with c_idx:
    st.subheader("📡 NOAA Indeksi")
    idx = st.columns(3)
    if ao: idx[0].metric("AO", f"{ao['val']:.2f}", ao['status'], delta_color=ao['color'])
    if nao: idx[1].metric("NAO", f"{nao['val']:.2f}", nao['status'], delta_color=nao['color'])
    if pna: idx[2].metric("PNA", f"{pna['val']:.2f}", pna['status'], delta_color=pna['color'])

with c_cot:
    st.subheader("🏛️ Institutional COT")
    if cot:
        st.metric("Non-Commercial Net", f"{cot['mm_net']:,}")
        st.caption(f"📅 Izvještaj: {cot['date']}")
        st.write(f"Retail Net: {cot['ret_net']:,}")
    else: st.error("Dohvat COT-a nije uspio.")

st.markdown("---")

# 4. TRENDOVI INDEKSA (SPAGHETTI PLOTS)
st.subheader("📈 Index Forecast Trends (14-Day)")
v1, v2, v3 = st.columns(3)
v1.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif")
v2.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif")
v3.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif")

st.markdown("---")

# 5. STORAGE
st.subheader("📦 Storage Mirror (vs 5y Average)")
if storage:
    s1, s2 = st.columns(2)
    s1.metric("Zalihe", f"{storage['val']} Bcf", f"{storage['chg']} Bcf")
    s2.metric("vs 5y Average", f"{storage['diff']:+} Bcf", delta_color="inverse")
