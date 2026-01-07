import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V6.2", layout="wide")

# CSS za ultra-clean mobilni UI
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; text-transform: uppercase; }
    .stAlert { padding: 0.4rem !important; border-radius: 10px; }
    section[data-testid="stSidebar"] { width: 250px !important; }
    h3 { font-size: 1.1rem !important; color: #31333F; margin-bottom: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. NOAA INDEKSI ---
def get_noaa_indices(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        val = float(lt[val_col])
        
        status, color, bias = "NEUTRAL", "off", "Neutral"
        if name == "AO":
            if val < -1.5: status, color, bias = "JAKO BULLISH", "normal", "Long"
            elif val > 1.5: status, color, bias = "JAKO BEARISH", "inverse", "Short"
        elif name == "NAO":
            if val < -0.8: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 0.8: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "PNA":
            if val > 0.8: status, color, bias = "BULLISH", "normal", "Long"
            elif val < -0.8: status, color, bias = "BEARISH", "inverse", "Short"
            
        return {"val": val, "status": status, "color": color, "bias": bias}
    except: return None

# --- 2. EIA FUNDAMENTALS (REVIZIRANO ZA SVJEŽIJE PODATKE) ---
def get_eia_balance(api_key):
    try:
        # Koristimo tjednu bazu jer je svježija od mjesečne
        url = "https://api.eia.gov/v2/natural-gas/sum/lsum/data/"
        params = {
            "api_key": api_key, "frequency": "monthly", "data[0]": "value",
            "facets[series][]": ["N9010US2", "N9070US2"],
            "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 4
        }
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        # Izdvajanje najnovijeg dostupnog (iako kasni, pokazuje trend)
        p_val = df[df['series'] == "N9010US2"].iloc[0]['value'] / 30
        c_val = df[df['series'] == "N9070US2"].iloc[0]['value'] / 30
        return {"prod": p_val, "cons": c_val, "bal": p_val - c_val}
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

# --- DOHVAT ---
ao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
storage = get_eia_storage(EIA_API_KEY)
balance = get_eia_balance(EIA_API_KEY)

# --- UI RASPODJELA ---

# 1. CELSIUS TREND ENGINE
st.subheader("💎 Celsius Trend Engine")
c1, c2, c3 = st.columns(3)
with c1:
    gwdd_today = st.number_input("Danas (15d Dev):", value=0.0, step=0.5, format="%.1f")
with c2:
    gwdd_yesterday = st.number_input("Jučer (15d Dev):", value=0.0, step=0.5, format="%.1f")
with c3:
    # Izračun trenda: ako je danas -20, a jučer -30, razlika je +10 (Bullish)
    velocity = gwdd_today - gwdd_yesterday
    v_color = "normal" if velocity > 0 else "inverse" if velocity < 0 else "off"
    st.metric("Trend (Velocity)", f"{velocity:+.1f}", delta="BULLISH" if velocity > 0 else "BEARISH", delta_color=v_color)

st.markdown("---")

# 2. MASTER BIAS
b1, b2, b3 = st.columns(3)
with b1:
    m_bias = "LONG" if (ao and ao['bias'] == "Long") else "SHORT" if (ao and ao['bias'] == "Short") else "NEUTRAL"
    st.info(f"🌍 METEO: {m_bias}")
with b2:
    s_bias = "BULLISH" if (storage and storage['diff'] < 0) else "BEARISH"
    st.info(f"🛢️ STORAGE: {s_bias}")
with b3:
    # Celsius bias sada gleda i apsolutni broj i trend
    c_bias = "BULLISH" if (gwdd_today > -5 or velocity > 2) else "BEARISH" if (gwdd_today < 5 or velocity < -2) else "NEUTRAL"
    st.info(f"💎 CELSIUS: {c_bias}")

st.markdown("---")

# 3. METEO KARTE
k1, k2 = st.columns(2)
k1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", use_container_width=True, caption="6-10 DANA")
k2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", use_container_width=True, caption="8-14 DANA")

# 4. INDEKSI I FUNDAMENTI
col_idx, col_fund = st.columns(2)
with col_idx:
    st.subheader("📡 NOAA Indeksi")
    idx_cols = st.columns(3)
    if ao: idx_cols[0].metric("AO", f"{ao['val']:.2f}", ao['status'], delta_color=ao['color'])
    if nao: idx_cols[1].metric("NAO", f"{nao['val']:.2f}", nao['status'], delta_color=nao['color'])
    if pna: idx_cols[2].metric("PNA", f"{pna['val']:.2f}", pna['status'], delta_color=pna['color'])

with col_fund:
    st.subheader("🏭 EIA Tjedni Balans")
    if balance:
        f1, f2 = st.columns(2)
        f1.metric("Est. Supply", f"{balance['prod']:.1f} Bcf/d")
        f2.metric("Est. Demand", f"{balance['cons']:.1f} Bcf/d")
    else: st.warning("EIA podaci u kašnjenju.")

st.markdown("---")

# 5. STORAGE & MIRROR
st.subheader("📦 Storage Mirror")
if storage:
    s1, s2, s3 = st.columns(3)
    s1.metric("Zalihe", f"{storage['val']} Bcf", f"{storage['chg']} Bcf")
    s2.metric("vs 5y Avg", f"{storage['diff']:+} Bcf", delta_color="inverse")
    s3.caption(f"📅 Datum: {storage['date']}")

st.markdown("---")
# FINALNA STRATEGIJA
score = 0
if storage and storage['diff'] < 0: score += 1
if ao and ao['bias'] == "Long": score += 1
if velocity > 0: score += 1 # Trend je Bullish

st.subheader("🪞 Trading Mirror")
if score >= 3: st.success("🚀 STRATEGIJA: AGRESIVNI LONG. Trend, zalihe i meteo su usklađeni.")
elif score == 0: st.error("📉 STRATEGIJA: AGRESIVNI SHORT. Sve komponente padaju.")
else: st.warning("⚖️ STRATEGIJA: OPREZ/DIVERGENCIJA. Čekaj usklađivanje trenda i zaliha.")
