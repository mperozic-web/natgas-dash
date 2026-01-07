import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V6.0", layout="wide")

# CSS za moderniji i sitniji UI
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    .stAlert { padding: 0.5rem !important; }
    h3 { font-size: 1.2rem !important; margin-bottom: 0.5rem !important; }
    </style>
    """, unsafe_allow_stdio=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. NOAA LOGIKA S GRADACIJOM ---
def get_noaa_indices(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val = float(lt[[c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]])
        
        status, color, bias = "NEUTRAL", "off", "Neutral"
        if name == "AO":
            if val < -2.5: status, color, bias = "EKSTREMNO BULLISH", "normal", "Long"
            elif val < -1.2: status, color, bias = "JAKO BULLISH", "normal", "Long"
            elif val < -0.5: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 2.5: status, color, bias = "EKSTREMNO BEARISH", "inverse", "Short"
            elif val > 1.2: status, color, bias = "JAKO BEARISH", "inverse", "Short"
            elif val > 0.5: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "NAO":
            if val < -1.2: status, color, bias = "JAKO BULLISH", "normal", "Long"
            elif val < -0.5: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 1.2: status, color, bias = "JAKO BEARISH", "inverse", "Short"
            elif val > 0.5: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "PNA":
            if val > 1.2: status, color, bias = "JAKO BULLISH", "normal", "Long"
            elif val > 0.5: status, color, bias = "BULLISH", "normal", "Long"
            elif val < -1.2: status, color, bias = "JAKO BEARISH", "inverse", "Short"
            elif val < -0.5: status, color, bias = "BEARISH", "inverse", "Short"
            
        return {"val": val, "status": status, "color": color, "bias": bias}
    except: return None

# --- 2. EIA FUNDAMENTALS (SUPPLY/DEMAND) ---
def get_eia_fundamentals(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/sum/lsum/data/"
        params = {
            "api_key": api_key, "frequency": "monthly", "data[0]": "value",
            "facets[series][]": ["N9010US2", "N9070US2"],
            "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 10
        }
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        prod = df[df['series'] == "N9010US2"].iloc[0]['value'] / 30
        cons = df[df['series'] == "N9070US2"].iloc[0]['value'] / 30
        return {"prod": prod, "cons": cons, "balance": prod - cons}
    except: return None

# --- 3. EIA STORAGE ---
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
funds = get_eia_fundamentals(EIA_API_KEY)

# --- SUČELJE ---

# 0. PREMIUM INPUT (ODMAH NA VRHU)
with st.container():
    c1, c2 = st.columns(2)
    with c1:
        gwdd_in = st.number_input("Celsius GWDD Devijacija (15d):", value=0.0, step=0.1, format="%.1f")
    with c2:
        stor_in = st.number_input("Celsius Storage Est. (Bcf):", value=0)

# 1. MASTER BIAS
st.markdown("### 🏁 Global Bias Summary")
m1, m2, m3 = st.columns(3)
with m1:
    m_bias = "LONG" if (ao and ao['bias'] == "Long") else "SHORT" if (ao and ao['bias'] == "Short") else "NEUTRAL"
    st.info(f"🌍 METEO: {m_bias}")
with m2:
    s_bias = "BULLISH" if (storage and storage['diff_5y'] < 0) else "BEARISH"
    st.info(f"🛢️ STORAGE: {s_bias}")
with m3:
    c_bias = "BULLISH" if gwdd_in > 5 else "BEARISH" if gwdd_in < -5 else "NEUTRAL"
    st.info(f"💎 CELSIUS: {c_bias}")

st.markdown("---")

# 2. METEO & KARTE
st.subheader("📡 Meteo Intelligence")
# Karte (Manje i jedna do druge)
k1, k2 = st.columns(2)
k1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", use_column_width=True)
k2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", use_column_width=True)

# Indeksi (Sitnije)
i1, i2, i3 = st.columns(3)
if ao: i1.metric("AO Index", f"{ao['val']:.2f}", ao['status'], delta_color=ao['color'])
if nao: i2.metric("NAO Index", f"{nao['val']:.2f}", nao['status'], delta_color=nao['color'])
if pna: i3.metric("PNA Index", f"{pna['val']:.2f}", pna['status'], delta_color=pna['color'])

st.markdown("---")

# 3. EIA FUNDAMENTALS (SUPPLY/DEMAND)
st.subheader("🏭 Market Balance (Supply vs Demand)")
if funds:
    f1, f2, f3 = st.columns(3)
    f1.metric("Proizvodnja (Supply)", f"{funds['prod']:.1f} Bcf/d")
    f2.metric("Potrošnja (Demand)", f"{funds['cons']:.1f} Bcf/d")
    bal_val = funds['balance']
    bal_lbl = "SURPLUS (Bearish)" if bal_val > 0 else "DEFICIT (Bullish)"
    f3.metric("NET BALANCE", bal_lbl, f"{bal_val:+.1f} Bcf/d", delta_color="inverse")

st.markdown("---")

# 4. STORAGE
st.subheader("📦 Storage Mirror")
if storage:
    s1, s2, s3 = st.columns(3)
    s1.metric("Trenutno", f"{storage['val']} Bcf", f"{storage['chg']} Bcf")
    s2.metric("vs 5y Average", f"{storage['diff_5y']:+} Bcf", delta_color="inverse")
    s3.caption(f"📅 Zadnji podatak: {storage['date']}")

# 5. FINAL MIRROR
st.markdown("---")
st.subheader("🪞 Objektivni Zaključak")
score = 0
if storage and storage['diff_5y'] < 0: score += 1
if ao and ao['bias'] == "Long": score += 1
if gwdd_in > 5: score += 1

if score >= 3: st.success("🚀 HIGH CONVICTION LONG: Svi fundamenti su usklađeni.")
elif score == 0: st.error("📉 HIGH CONVICTION SHORT: Svi fundamenti su usklađeni.")
else: st.warning("⚖️ NEUTRAL/DIVERGENCIJA: Pažljivo sa scalpingom.")
