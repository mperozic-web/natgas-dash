import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V5.3", layout="wide", page_icon="📈")
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. NOAA METEO LOGIKA ---
def get_noaa_indices(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val = float(lt[[c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]])
        status = "BULLISH" if (name in ["AO", "NAO"] and val < -0.5) or (name == "PNA" and val > 0.5) else "BEARISH" if (name in ["AO", "NAO"] and val > 0.5) or (name == "PNA" and val < -0.5) else "NEUTRAL"
        color = "normal" if status == "BULLISH" else "inverse" if status == "BEARISH" else "off"
        return {"val": val, "status": status, "color": color}
    except: return None

# --- 2. EIA STORAGE ---
def get_eia_storage(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 250}
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        df['value'] = df['value'].astype(int)
        df['week'] = pd.to_datetime(df['period']).dt.isocalendar().week
        curr = df.iloc[0]
        avg_5y = int(df.iloc[52:][df.iloc[52:]['week'] == curr['week']].head(5)['value'].mean())
        return {"val": curr['value'], "chg": curr['value'] - df.iloc[1]['value'], "diff_5y": curr['value'] - avg_5y, "date": pd.to_datetime(curr['period']).strftime("%d.%m.%Y")}
    except: return None

# --- DOHVAT PODATAKA ---
ao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
storage = get_eia_storage(EIA_API_KEY)

# --- DASHBOARD LAYOUT ---
st.title("🛡️ NatGas Fundamental Sniper V5.3")

# SIDEBAR: CELSIUS INPUT
with st.sidebar:
    st.header("💎 Celsius Premium Data")
    st.markdown("Unesi podatke iz današnjeg reporta:")
    c_gwdd_15 = st.number_input("15-Day GWDD Deviation:", value=0.0, step=0.5, help="Unesi kumulativno odstupanje za sljedećih 15 dana.")
    c_storage_est = st.number_input("Est. Next Storage Draw (Bcf):", value=0, help="Celsiusova procjena sljedećeg EIA izvještaja.")
    
    st.markdown("---")
    st.write("**Trenutni Celsius Sentiment:**")
    if c_gwdd_15 > 10: st.success("🔥 BULLISH (Hladno)")
    elif c_gwdd_15 < -10: st.error("❄️ BEARISH (Toplo)")
    else: st.info("⚪ NEUTRALNO")

# SEKCIJA 1: MASTER BIAS
st.subheader("🏁 Global Bias Summary")
b1, b2, b3 = st.columns(3)
with b1:
    m_bias = "LONG" if (ao and ao['status'] == "BULLISH") else "SHORT" if (ao and ao['status'] == "BEARISH") else "NEUTRAL"
    st.info(f"🌍 METEO BIAS: {m_bias}")
with b2:
    s_bias = "BULLISH" if (storage and storage['diff_5y'] < 0) else "BEARISH"
    st.info(f"🛢️ STORAGE BIAS: {s_bias}")
with b3:
    c_bias = "BULLISH" if c_gwdd_15 > 5 else "BEARISH" if c_gwdd_15 < -5 else "NEUTRAL"
    st.info(f"💎 CELSIUS BIAS: {c_bias}")

st.markdown("---")

# SEKCIJA 2: NOAA KARTI (PROGRESIJA PROGNOZE)
st.subheader("🗺️ NOAA Forecast Progression (Trend)")
st.caption("Usporedba 6-10 dana vs. 8-14 dana pokazuje kuda se hladnoća pomiče.")
m_col1, m_col2 = st.columns(2)
with m_col1:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10 Day Outlook")
with m_col2:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14 Day Outlook")

st.markdown("---")

# SEKCIJA 3: INDEKSI I STORAGE
c1, c2 = st.columns(2)
with c1:
    st.subheader("📡 Meteo Indices")
    i1, i2, i3 = st.columns(3)
    if ao: i1.metric("AO Index", f"{ao['val']:.2f}", ao['status'], delta_color=ao['color'])
    if nao: i2.metric("NAO Index", f"{nao['val']:.2f}", nao['status'], delta_color=nao['color'])
    if pna: i3.metric("PNA Index", f"{pna['val']:.2f}", pna['status'], delta_color=pna['color'])

with c2:
    st.subheader("📦 Storage Mirror (vs. 5y Avg)")
    if storage:
        s1, s2 = st.columns(2)
        s1.metric("Current", f"{storage['val']} Bcf", f"{storage['chg']} Bcf")
        s2.metric("vs 5y Average", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")

st.markdown("---")
# SEKCIJA 4: STRATEŠKI ZAKLJUČAK
st.subheader("🪞 Trading Mirror & Strategy")
if storage and ao:
    st.markdown("### Analiza usklađenosti:")
    
    # Logika za preporuku
    total_score = 0
    if storage['diff_5y'] < 0: total_score += 1 # Storage Bullish
    if ao['status'] == "BULLISH": total_score += 1 # Meteo Bullish
    if c_gwdd_15 > 5: total_score += 1 # Celsius Bullish
    
    if total_score >= 3:
        st.success("🚀 **HIGH CONVICTION LONG:** Svi fundamenti su usklađeni. Potražnja raste, zalihe su male.")
    elif total_score <= 0:
        st.error("📉 **HIGH CONVICTION SHORT:** Svi fundamenti su usklađeni za pad. Višak plina i toplo vrijeme.")
    else:
        st.warning("⚠️ **DIVERGENCIJA:** Signali nisu usklađeni. Budi oprezan s dugoročnim holdanjem.")

st.caption("NatGas Sniper V5.3 | Data: NOAA FTP, EIA API, User Premium Input")
