import streamlit as st
import pandas as pd
import requests
import io
import re

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V9.1", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; text-transform: uppercase; }
    .stAlert { padding: 0.3rem !important; border-radius: 8px; }
    h3 { font-size: 0.95rem !important; color: #1E1E1E; margin-bottom: 0.4rem; border-bottom: 2px solid #3498db; width: fit-content; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. ROBUSTAN COT SCRAPER (S USER-AGENTOM) ---
def get_cot_final():
    url = "https://www.cftc.gov/dea/futures/nat_gas_lf.htm"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200: return None
        
        raw_text = r.text
        # Tražimo početak bloka za Natural Gas
        start_marker = "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE"
        if start_marker not in raw_text: return None
        
        block = raw_text.split(start_marker)[1]
        
        # Ekstrakcija Non-Commercial (Institucije)
        # Brojke su u prvom redu koji sadrži barem 5 grupa brojeva
        lines = block.split('\n')
        mm_net = 0
        ret_net = 0
        date_str = "N/A"
        
        # Datum je na vrhu cijele stranice
        date_match = re.search(r"(\w+ \d+, \d{4})", raw_text)
        if date_match: date_str = date_match.group(1)
        
        for line in lines:
            nums = re.findall(r"(\d{1,3}(?:,\d{3})*)", line)
            if len(nums) >= 8: # Non-Commercial linija ima puno brojki
                clean_nums = [int(n.replace(',', '')) for n in nums]
                mm_net = clean_nums[0] - clean_nums[1] # Long - Short
                break
        
        # Ekstrakcija Non-Reportable (Retail) - obično zadnji red s brojkama u bloku
        for line in reversed(lines[:50]):
            nums = re.findall(r"(\d{1,3}(?:,\d{3})*)", line)
            if len(nums) == 2: # Retail linija ima samo Long i Short na kraju
                clean_nums = [int(n.replace(',', '')) for n in nums]
                ret_net = clean_nums[0] - clean_nums[1]
                break
                
        return {"mm_net": mm_net, "ret_net": ret_net, "date": date_str}
    except:
        return None

# --- 2. NOAA INDEKSI ---
def get_noaa_indices(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        val = float(lt[val_col])
        
        status, color, bias = "NEUTRAL", "off", "Neutral"
        if name == "AO":
            if val < -1.0: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 1.0: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "NAO":
            if val < -0.7: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 0.7: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "PNA":
            if val > 0.7: status, color, bias = "BULLISH", "normal", "Long"
            elif val < -0.7: status, color, bias = "BEARISH", "inverse", "Short"
            
        return {"val": val, "status": status, "color": color, "bias": bias}
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
ao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
storage = get_eia_storage(EIA_API_KEY)
cot = get_cot_final()

# --- UI DISPLAY ---
st.title("🛡️ Institutional Sniper Mirror V9.1")

# 1. MASTER BIAS
st.subheader("🏁 Global Bias Summary")
m1, m2, m3 = st.columns(3)
with m1:
    m_bias = ao['bias'] if ao else "N/A"
    st.info(f"🌍 METEO: {m_bias}")
with m2:
    s_bias = "BULLISH" if (storage and storage['diff'] < 0) else "BEARISH"
    st.info(f"🛢️ STORAGE: {s_bias}")
with m3:
    c_bias = "SQUEEZE RISK" if (cot and cot['mm_net'] < -140000) else "BEARISH" if (cot and cot['mm_net'] > 0) else "NEUTRAL"
    st.info(f"🏛️ COT: {c_bias}")

st.markdown("---")

# 2. PROGRESIJA TEMPERATURE
st.subheader("🗺️ Forecast Progression (6-10d vs 8-14d)")
m_col1, m_col2 = st.columns(2)
m_col1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", use_container_width=True)
m_col2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", use_container_width=True)

st.markdown("---")

# 3. NOAA INDEKSI I COT
col_i, col_c = st.columns([2, 1])
with col_i:
    st.subheader("📡 NOAA Indeksi")
    idx = st.columns(3)
    if ao: idx[0].metric("AO", f"{ao['val']:.2f}", ao['status'], delta_color=ao['color'])
    if nao: idx[1].metric("NAO", f"{nao['val']:.2f}", nao['status'], delta_color=nao['color'])
    if pna: idx[2].metric("PNA", f"{pna['val']:.2f}", pna['status'], delta_color=pna['color'])

with col_c:
    st.subheader("🏛️ Institutional COT")
    if cot:
        st.metric("Non-Comm Net", f"{cot['mm_net']:,}", f"Retail: {cot['ret_net']:,}")
        st.caption(f"📅 {cot['date']}")
    else: st.error("COT nije dostupan")

st.markdown("---")

# 4. TRENDOVI (SPAGHETTI)
st.subheader("📈 Index Trends (14-Day)")
v1, v2, v3 = st.columns(3)
v1.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif")
v2.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif")
v3.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif")

st.markdown("---")

# 5. STORAGE
st.subheader("📦 Storage Mirror")
if storage:
    s1, s2 = st.columns(2)
    s1.metric("Zalihe", f"{storage['val']} Bcf", f"{storage['chg']} Bcf")
    s2.metric("vs 5y Avg", f"{storage['diff']:+} Bcf", delta_color="inverse")
