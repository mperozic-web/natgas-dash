import streamlit as st
import pandas as pd
import requests
import io
import zipfile
from datetime import datetime

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V8.2", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; text-transform: uppercase; }
    .stAlert { padding: 0.4rem !important; border-radius: 8px; }
    h3 { font-size: 1.1rem !important; color: #1E1E1E; margin-bottom: 0.6rem; border-bottom: 2px solid #3498db; width: fit-content; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. ROBUSTAN COT DOHVAT ---
def get_cot_data():
    # Pokušavamo tekuću pa prethodnu godinu
    for yr in [datetime.now().year, datetime.now().year - 1]:
        try:
            url = f"https://www.cftc.gov/sites/default/files/files/dea/history/fut_disagg_txt_{yr}.zip"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    name = z.namelist()[0]
                    with z.open(name) as f:
                        df = pd.read_csv(f, sep=None, engine='python', low_memory=False)
                
                # Filtriranje za Natural Gas (NYMEX)
                # Koristimo kod ugovora 023651 ili naziv
                df_ng = df[df['CFTC_Contract_Market_Code'].astype(str).str.contains('023651', na=False)]
                if df_ng.empty:
                    df_ng = df[df['Market_and_Exchange_Names'].str.contains('NATURAL GAS', na=False)]
                
                if not df_ng.empty:
                    # Uzimamo zadnji dostupni izvještaj (vrh tablice)
                    latest = df_ng.iloc[0]
                    mm_net = int(latest['Managed_Money_Positions_Long_All']) - int(latest['Managed_Money_Positions_Short_All'])
                    ret_net = int(latest['NonRept_Positions_Long_All']) - int(latest['NonRept_Positions_Short_All'])
                    return {"mm_net": mm_net, "ret_net": ret_net, "date": latest['Report_Date_as_MM_DD_YYYY']}
        except:
            continue
    return None

# --- 2. NOAA & EIA FUNKCIJE ---
def interpret_noaa(name, val):
    val = float(val)
    res = {"status": "NEUTRAL", "color": "off", "desc": "", "bias": "Neutral"}
    if name == "AO":
        if val < -1.5: res = {"status": "JAKO BULLISH", "color": "normal", "desc": "Vrtlog razbijen, hladnoća bježi u SAD.", "bias": "Long"}
        elif val > 1.5: res = {"status": "JAKO BEARISH", "color": "inverse", "desc": "Hladnoća zaključana na Arktiku.", "bias": "Short"}
    elif name == "NAO":
        if val < -0.8: res = {"status": "BULLISH", "color": "normal", "desc": "Blokada iznad Grenlanda gura hladnoću na istok.", "bias": "Long"}
        elif val > 0.8: res = {"status": "BEARISH", "color": "inverse", "desc": "Mlazni tok donosi toplinu s Atlantika.", "bias": "Short"}
    elif name == "PNA":
        if val > 0.8: res = {"status": "BULLISH", "color": "normal", "desc": "Greben na zapadu gura hladnoću na istok.", "bias": "Long"}
        elif val < -0.8: res = {"status": "BEARISH", "color": "inverse", "desc": "Pacifička toplina dominira.", "bias": "Short"}
    return res

def get_noaa_data(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        interp = interpret_noaa(name, lt[val_col])
        return {"val": float(lt[val_col]), **interp}
    except: return None

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
cot = get_cot_data()

# --- UI DISPLAY ---
st.title("🛡️ Institutional Sniper Mirror V8.2")

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

# 2. PROGRESIJA TEMPERATURE
st.subheader("🗺️ Forecast Progression (6-10d vs 8-14d)")
m_col1, m_col2 = st.columns(2)
m_col1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", use_container_width=True)
m_col2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", use_container_width=True)

st.markdown("---")

# 3. NOAA INDEKSI & COT
c_idx, c_cot = st.columns([2, 1])

with c_idx:
    st.subheader("📡 NOAA Indeksi")
    i1, i2, i3 = st.columns(3)
    if ao: i1.metric("AO Index", f"{ao['val']:.2f}", ao['status'], delta_color=ao['color'])
    if nao: i2.metric("NAO Index", f"{nao['val']:.2f}", nao['status'], delta_color=nao['color'])
    if pna: i3.metric("PNA Index", f"{pna['val']:.2f}", pna['status'], delta_color=pna['color'])

with c_cot:
    st.subheader("🏛️ Institutional COT")
    if cot:
        st.metric("Managed Money Net", f"{cot['mm_net']:,}")
        st.caption(f"📅 Izvještaj: {cot['date']} | Retail: {cot['ret_net']:,}")
    else: st.error("Dohvat COT-a nije uspio.")

st.markdown("---")

# 4. TRENDOVI INDEKSA (Spaghetti Plots)
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
