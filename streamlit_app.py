import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Bot V3.2", layout="wide", page_icon="🔥")

st.title("🔥 NatGas Master Trading Desk")

# ==============================================================================
# 🔑 API KLJUČEVI
# ==============================================================================
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
# ==============================================================================

# --- 1. FUNKCIJE ZA VRIJEME (NOAA) ---
def get_noaa_index(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        latest = df.iloc[-1]
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        return {"value": float(latest[val_col])}
    except:
        return None

# --- 2. FUNKCIJE ZA ZALIHE (EIA) ---
def get_eia_storage(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {
            "api_key": api_key, "frequency": "weekly", "data[0]": "value",
            "facets[series][]": "NW2_EPG0_SWO_R48_BCF", 
            "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 2
        }
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if 'response' in data:
            recs = data['response']['data']
            return {"value": int(recs[0]['value']), "change": int(recs[0]['value']) - int(recs[1]['value'])}
    except:
        return None

# --- 3. FUNKCIJE ZA CIJENU (ROBUST FIX) ---
def get_market_data(interval, period):
    ticker = "NG=F"
    try:
        # Prvi pokušaj: Traženi interval
        df = yf.download(ticker, interval=interval, period=period, progress=False)
        
        # Ako je prazno i tražimo 1h, probaj backup na 90m ili 1d
        if df.empty and interval == '1h':
            df = yf.download(ticker, interval="1d", period="1mo", progress=False)
            st.toast("⚠️ 1H podaci nedostupni, prikazujem Dnevne (1D).", icon="ℹ️")

        if df.empty:
            return None

        # Fix za MultiIndex (Yahoo problem)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if 'Close' not in df.columns:
            return None

        # Indikatori
        df['RSI'] = df.ta.rsi(length=14)
        if interval == '2m':
            df['EMA_9'] = df.ta.ema(length=9)
        else:
            df['SMA_50'] = df.ta.sma(length=50)

        df.dropna(inplace=True)
        return df
        
    except Exception as e:
        return None

# --- DASHBOARD LOGIKA ---

# URL-ovi
URL_AO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv"
URL_NAO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv"
URL_PNA = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv"

# Dohvat
data_ao = get_noaa_index(URL_AO)
data_nao = get_noaa_index(URL_NAO)
data_pna = get_noaa_index(URL_PNA)
eia_data = get_eia_storage(EIA_API_KEY)
swing_data = get_market_data('1h', '1mo')
scalp_data = get_market_data('2m', '5d')

# --- LAYOUT V3.2 (POPRAVLJEN) ---

# 1. RED: NOAA (VRIJEME)
st.subheader("📡 Modul 1: Vrijeme (NOAA)")
c1, c2, c3 = st.columns(3)

with c1:
    if data_ao:
        val = data_ao['value']
        # AO Negativan = Hladno = BULLISH (Zeleno)
        lbl = "BEAR (Toplo)" if val > 0 else "BULL (Hladno)"
        col = "inverse" 
        st.metric("AO Index", f"{val:.2f}", delta=lbl, delta_color=col)

with c2:
    if data_nao:
        val = data_nao['value']
        # NAO Negativan = Blokada = BULLISH (Zeleno)
        lbl = "BEAR (Otvoren)" if val > 0 else "BULL (Blokada)"
        col = "inverse"
        st.metric("NAO Index", f"{val:.2f}", delta=lbl, delta_color=col)

with c3:
    if data_pna:
        val = data_pna['value']
        # PNA Pozitivan = Hladan Istok = BULLISH (Zeleno)
        lbl = "BULL (Hl. Istok)" if val > 0 else "BEAR (Top. Istok)"
        col = "normal"
        st.metric("PNA Index", f"{val:.2f}", delta=lbl, delta_color=col)

st.markdown("---")

# 2. RED: EIA (ZALIHE)
st.subheader("🛢️ Modul 2: Zalihe (EIA)")
c_eia, _ = st.columns([1, 2]) # Lijeva kolona za brojke, desna prazna

with c_eia:
    if eia_data:
        # Promjena pozitivna = Rast zaliha = Bearish (Crveno)
        st.metric("Ukupne Zalihe", f"{eia_data['value']} Bcf", f"{eia_data['change']} Bcf (Promjena)", delta_color="inverse")
    else:
        st.warning("EIA podaci se učitavaju...")

st.markdown("---")

# 3. RED: CIJENA (SWING & SCALP)
st.subheader("📈 Modul 3: Price Action")

c_swing, c_scalp = st.columns(2)

with c_swing:
    st.markdown("### 🐢 Swing (1H / 1D)")
    if swing_data is not None and not swing_data.empty:
        last_rsi = swing_data['RSI'].iloc[-1]
        last_price = swing_data['Close'].iloc[-1]
        st.metric("Cijena", f"${last_price:.3f}", f"RSI: {last_rsi:.1f}")
        st.line_chart(swing_data['Close'])
    else:
        st.error("⚠️ Greška s podacima za Swing.")

with c_scalp:
    st.markdown("### 🐇 Scalp (2 Min)")
    if scalp_data is not None and not scalp_data.empty:
        last_rsi = scalp_data['RSI'].iloc[-1]
        last_price = scalp_data['Close'].iloc[-1]
        st.metric("Cijena", f"${last_price:.3f}", f"RSI: {last_rsi:.1f}")
        st.line_chart(scalp_data['Close'])
    else:
        st.error("⚠️ Greška s podacima za Scalp (Burza zatvorena?).")
