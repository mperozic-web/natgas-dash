import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V8.0", layout="wide")

# CSS za čišći i pregledniji UI
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; text-transform: uppercase; }
    .stAlert { padding: 0.5rem !important; border-radius: 8px; }
    h3 { font-size: 1.1rem !important; color: #1E1E1E; margin-bottom: 0.5rem; border-bottom: 2px solid #3498db; width: fit-content; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. DETALJNA NOAA INTERPRETACIJA ---
def interpret_noaa(name, val):
    val = float(val)
    res = {"status": "NEUTRALNO", "color": "off", "desc": "", "bias": "Neutral"}
    
    if name == "AO":
        if val < -2.5: res = {"status": "EKSTREMNO BULLISH", "color": "normal", "desc": "Polarni vrtlog je potpuno razbijen. Hladnoća bježi s Arktika ravno u SAD.", "bias": "Strong Long"}
        elif val < -1.0: res = {"status": "JAKO BULLISH", "color": "normal", "desc": "Vrtlog je nestabilan, visoka vjerojatnost hladnih prodora.", "bias": "Long"}
        elif val > 2.5: res = {"status": "EKSTREMNO BEARISH", "color": "inverse", "desc": "Vrtlog je super-stabilan. Hladnoća je zaključana na polu. Toplo u SAD.", "bias": "Strong Short"}
        elif val > 1.0: res = {"status": "JAKO BEARISH", "color": "inverse", "desc": "Hladnoća se ne može probiti na jug.", "bias": "Short"}
    
    elif name == "NAO":
        if val < -1.2: res = {"status": "EKSTREMNO BULLISH", "color": "normal", "desc": "Snažna blokada iznad Grenlanda gura hladnoću na Istočnu obalu SAD-a.", "bias": "Strong Long"}
        elif val < -0.6: res = {"status": "BULLISH", "color": "normal", "desc": "Povoljna blokada za potražnju plina.", "bias": "Long"}
        elif val > 1.2: res = {"status": "EKSTREMNO BEARISH", "color": "inverse", "desc": "Atlantik je 'otvoren', topli zrak preplavljuje SAD.", "bias": "Strong Short"}
        elif val > 0.6: res = {"status": "BEARISH", "color": "inverse", "desc": "Brzi mlazni tokovi donose blago vrijeme.", "bias": "Short"}

    elif name == "PNA":
        if val > 1.2: res = {"status": "EKSTREMNO BULLISH", "color": "normal", "desc": "Greben na zapadu gura masivnu hladnoću na istok i u središte SAD-a.", "bias": "Strong Long"}
        elif val > 0.6: res = {"status": "BULLISH", "color": "normal", "desc": "Hladniji uzorak vremena.", "bias": "Long"}
        elif val < -1.2: res = {"status": "EKSTREMNO BEARISH", "color": "inverse", "desc": "Topli pacifički zrak dominira cijelim kontinentom.", "bias": "Strong Short"}
        elif val < -0.6: res = {"status": "BEARISH", "color": "inverse", "desc": "Nepovoljno za grijanje.", "bias": "Short"}

    return res

def get_noaa_data(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        val = float(lt[val_col])
        interp = interpret_noaa(name, val)
        return {"val": val, "status": interp['status'], "color": interp['color'], "desc": interp['desc'], "bias": interp['bias']}
    except: return None

# --- 2. EIA STORAGE ---
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

# --- UI DISPLAY ---
st.title("🛡️ NatGas Master Mirror V8.0")

# 1. MASTER BIAS
st.subheader("🏁 Globalni Tržišni Bias")
b1, b2 = st.columns(2)
with b1:
    m_bias = ao['bias'] if ao else "N/A"
    st.info(f"🌍 METEO SENTIMENT: {m_bias}")
with b2:
    s_bias = "BULLISH (Deficit)" if (storage and storage['diff'] < 0) else "BEARISH (Višak)"
    st.info(f"🛢️ STORAGE SENTIMENT: {s_bias}")

st.markdown("---")

# 2. NOAA DETALJNA SEKCIJA
st.subheader("📡 NOAA Meteo Intelligence (Indeksi + Interpretacija)")
c1, c2, c3 = st.columns(3)

def draw_noaa_card(col, name, d):
    with col:
        if d:
            st.metric(name, f"{d['val']:.2f}", d['status'], delta_color=d['color'])
            st.info(f"**Uputa:** {d['desc']}")
        else: st.error(f"{name} nedostupan")

draw_noaa_card(c1, "AO (Polar Vortex)", ao)
draw_noaa_card(c2, "NAO (Atlantic Block)", nao)
draw_noaa_card(c3, "PNA (Pacific Pattern)", pna)

st.markdown("---")

# 3. NOAA VIZUALNE KARTE (PROGNOZA)
st.subheader("🗺️ Vizualni Trend Prognoze (Gledaj kamo idu linije)")
v1, v2, v3 = st.columns(3)
with v1:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", caption="AO Forecast Trend")
with v2:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", caption="NAO Forecast Trend")
with v3:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", caption="PNA Forecast Trend")

st.markdown("---")

# 4. TEMPERATURNI OUTLOOK (8-14 DANA)
st.subheader("❄️ NOAA 8-14 Day Temperature Probability")
st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", use_container_width=True)

st.markdown("---")

# 5. STORAGE SEKCIJA
st.subheader("📦 Storage Mirror (vs 5y Average)")
if storage:
    s1, s2, s3 = st.columns(3)
    s1.metric("Trenutne Zalihe", f"{storage['val']} Bcf", f"{storage['chg']} Bcf Tjedno")
    s2.metric("Odstupanje od 5y Prosjeka", f"{storage['diff']:+} Bcf", delta_color="inverse")
    s3.caption(f"📅 Datum izvještaja: {storage['date']}")
else: st.error("EIA podaci nisu dostupni.")

st.markdown("---")
st.caption("NatGas Sniper V8.0 | Izvor: NOAA CPC i EIA API | Bez ručnog unosa.")
