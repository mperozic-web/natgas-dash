import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta
import datetime

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Bot V3.0", layout="wide", page_icon="🔥")

st.title("🔥 NatGas Master Trading Desk (V3.0)")
st.markdown("### 📡 Weather | 🛢️ Storage | 📈 Price Action (Swing & Scalp)")
st.markdown("---")

# ==============================================================================
# 🔑 API KLJUČEVI
# ==============================================================================
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
# ==============================================================================

# --- 1. FUNKCIJE ZA VRIJEME (NOAA) ---
def get_noaa_index(url, col_name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        latest = df.iloc[-1]
        
        # Tražimo stupac s vrijednosti (onaj koji nije datum)
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        
        return {"date": f"{int(latest['day'])}.{int(latest['month'])}", "value": float(latest[val_col])}
    except:
        return None

# --- 2. FUNKCIJE ZA ZALIHE (EIA) ---
def get_eia_storage(api_key):
    url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
    params = {
        "api_key": api_key, "frequency": "weekly", "data[0]": "value",
        "facets[series][]": "NW2_EPG0_SWO_R48_BCF", 
        "sort[0][column]": "period", "sort[0][direction]": "desc", 
        "length": 2
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if 'response' in data:
            recs = data['response']['data']
            return {"date": recs[0]['period'], "value": int(recs[0]['value']), "change": int(recs[0]['value']) - int(recs[1]['value'])}
    except:
        return None

# --- 3. FUNKCIJE ZA CIJENU (YAHOO FINANCE) ---
def get_market_data(interval, period):
    """
    Dohvaća podatke za NG=F (Futures).
    interval: '1h' (Swing) ili '2m' (Scalp)
    period: '1mo' za Swing, '5d' za Scalp
    """
    try:
        ticker = "NG=F"
        df = yf.download(ticker, interval=interval, period=period, progress=False)
        
        if df.empty:
            return None
            
        # Izračun indikatora (Pandas TA)
        # 1. RSI (14)
        df['RSI'] = df.ta.rsi(length=14)
        
        # 2. SMA (50) - Samo za Swing trend
        if interval == '1h':
            df['SMA_50'] = df.ta.sma(length=50)
            
        # 3. EMA (9) - Za Scalp momentum
        if interval == '2m':
            df['EMA_9'] = df.ta.ema(length=9)

        return df
    except Exception as e:
        return None

# --- PRIKAZ PODATAKA (DASHBOARD) ---

# URL-ovi za NOAA
URL_AO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv"
URL_NAO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv"
URL_PNA = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv"

# Paralelni dohvat podataka
data_ao = get_noaa_index(URL_AO, "AO")
data_nao = get_noaa_index(URL_NAO, "NAO")
data_pna = get_noaa_index(URL_PNA, "PNA")
eia_data = get_eia_storage(EIA_API_KEY)
swing_data = get_market_data('1h', '1mo')
scalp_data = get_market_data('2m', '5d')

# --- MODUL 1 & 2 (GORNJI RED) ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("##### 📡 AO (Vrtlog)")
    if data_ao:
        val = data_ao['value']
        lbl = "BEAR (Toplo)" if val > 0 else "BULL (Hladno)"
        st.metric("AO", f"{val:.2f}", delta=lbl, delta_color="inverse")

with c2:
    st.markdown("##### 📡 NAO (Blokada)")
    if data_nao:
        val = data_nao['value']
        lbl = "BEAR (Otvoren)" if val > 0 else "BULL (Blok)"
        st.metric("NAO", f"{val:.2f}", delta=lbl, delta_color="inverse")

with c3:
    st.markdown("##### 📡 PNA (Pacifik)")
    if data_pna:
        val = data_pna['value']
        lbl = "BULL (Hl. Istok)" if val > 0 else "BEAR (Top. Istok)"
        st.metric("PNA", f"{val:.2f}", delta=lbl, delta_color="normal")

with c4:
    st.markdown("##### 🛢️ Zalihe (EIA)")
    if eia_data:
        st.metric("Storage", f"{eia_data['value']}", delta=f"{eia_data['change']} Bcf", delta_color="inverse")

st.markdown("---")

# --- MODUL 3: PRICE ACTION (DONJI RED) ---
st.subheader("📈 Modul 3: Price Action Radar")

col_swing, col_scalp = st.columns(2)

# === SWING RADAR (1H) ===
with col_swing:
    st.markdown("### 🐢 SWING RADAR (1H Timeframe)")
    if swing_data is not None:
        last_close = swing_data['Close'].iloc[-1].item() # .item() pretvara u float
        last_rsi = swing_data['RSI'].iloc[-1].item()
        
        # Trend detekcija (Cijena vs SMA50)
        sma_50 = swing_data['SMA_50'].iloc[-1].item()
        trend = "UPTREND (Bullish)" if last_close > sma_50 else "DOWNTREND (Bearish)"
        trend_color = "green" if last_close > sma_50 else "red"

        # Prikaz Cijene
        st.metric("Trenutna Cijena (Futures)", f"${last_close:.3f}")
        
        # Prikaz Trenda
        st.info(f"**Glavni Trend:** :{trend_color}[{trend}]")
        
        # RSI Mjerač
        st.write(f"**RSI Snaga (14):** {last_rsi:.1f}")
        if last_rsi > 70:
            st.error("⚠️ OVERBOUGHT (Preskupo) -> Traži Short!")
        elif last_rsi < 30:
            st.success("✅ OVERSOLD (Jeftino) -> Traži Long!")
        else:
            st.warning("⚪ NEUTRALNO (Čekaj signal)")
            
        # Mali graf
        st.line_chart(swing_data['Close'].tail(72)) # Zadnja 3 dana (72 sata)
    else:
        st.error("Nema Swing podataka (Yahoo greška)")

# === SCALP SNAJPER (2 MIN) ===
with col_scalp:
    st.markdown("### 🐇 SCALP SNAJPER (2 Min Timeframe)")
    if scalp_data is not None:
        sc_close = scalp_data['Close'].iloc[-1].item()
        sc_rsi = scalp_data['RSI'].iloc[-1].item()
        sc_ema = scalp_data['EMA_9'].iloc[-1].item()
        
        # Momentum (Cijena vs EMA9)
        mom = "Jaki Momentum" if sc_close > sc_ema else "Slabi Momentum"
        
        # Skrivena logika za "Brzi Signal"
        signal = "ČEKAJ"
        if sc_rsi > 75: signal = "PRODAJ ODMAH (Scalp Short)"
        elif sc_rsi < 25: signal = "KUPI ODMAH (Scalp Long)"
        
        st.metric("Scalp Cijena", f"${sc_close:.3f}", delta=f"RSI: {sc_rsi:.1f}")
        
        # Dinamički signal
        if "PRODAJ" in signal:
            st.error(f"🚨 **SIGNAL:** {signal}")
        elif "KUPI" in signal:
            st.success(f"🚨 **SIGNAL:** {signal}")
        else:
            st.info(f"💤 **SIGNAL:** {signal}")

        st.line_chart(scalp_data['Close'].tail(60)) # Zadnjih 2 sata (60 svijeća od 2 min)
    else:
        st.error("Nema Scalp podataka (Možda je burza zatvorena?)")

st.markdown("---")
st.caption("NatGas Bot V3.0 | Power by: NOAA (Meteo), EIA (Storage), Yahoo (Price)")
