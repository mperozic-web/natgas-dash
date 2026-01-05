import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Bot V3.1", layout="wide", page_icon="🔥")

st.title("🔥 NatGas Master Trading Desk (V3.1 Fix)")
st.markdown("### 📡 Weather | 🛢️ Storage | 📈 Price Action")
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

# --- 3. FUNKCIJE ZA CIJENU (YAHOO FINANCE FIX) ---
def get_market_data(interval, period):
    try:
        ticker = "NG=F"
        # Download s isključenim progress barom da ne guši logove
        df = yf.download(ticker, interval=interval, period=period, progress=False)
        
        if df.empty:
            st.error(f"Yahoo vratio praznu tablicu za {interval}")
            return None

        # --- FIX ZA YAHOO MULTI-INDEX (Ključni popravak) ---
        # Yahoo nekad vraća stupce kao (Price, Ticker). Ovo to spljošti u (Price).
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Provjera imamo li 'Close' kolonu
        if 'Close' not in df.columns:
            st.error(f"Fali 'Close' kolona. Dostupne: {df.columns}")
            return None

        # Izračun indikatora (Pandas TA)
        df['RSI'] = df.ta.rsi(length=14)
        
        if interval == '1h':
            df['SMA_50'] = df.ta.sma(length=50)
        
        if interval == '2m':
            df['EMA_9'] = df.ta.ema(length=9)

        # Očisti NaN vrijednosti koje nastanu na početku zbog računanja prosjeka
        df.dropna(inplace=True)
        
        return df
        
    except Exception as e:
        st.error(f"Greška u get_market_data ({interval}): {e}")
        return None

# --- DASHBOARD LOGIKA ---

# Dohvat podataka
URL_AO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv"
URL_NAO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv"
URL_PNA = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv"

data_ao = get_noaa_index(URL_AO, "AO")
data_nao = get_noaa_index(URL_NAO, "NAO")
data_pna = get_noaa_index(URL_PNA, "PNA")
eia_data = get_eia_storage(EIA_API_KEY)

# Pokušaj dohvata burze
swing_data = get_market_data('1h', '1mo')
scalp_data = get_market_data('2m', '5d')

# --- PRIKAZ ---

# RED 1: INFO
c1, c2, c3, c4 = st.columns(4)
with c1:
    if data_ao: st.metric("AO", f"{data_ao['value']:.2f}")
with c2:
    if data_nao: st.metric("NAO", f"{data_nao['value']:.2f}")
with c3:
    if data_pna: st.metric("PNA", f"{data_pna['value']:.2f}")
with c4:
    if eia_data: st.metric("Storage", f"{eia_data['value']}", f"{eia_data['change']}")

st.markdown("---")

# RED 2: GRAFOVI
c_swing, c_scalp = st.columns(2)

with c_swing:
    st.subheader("Swing (1H)")
    if swing_data is not None and not swing_data.empty:
        last_rsi = swing_data['RSI'].iloc[-1]
        last_price = swing_data['Close'].iloc[-1]
        
        st.metric("Cijena", f"${last_price:.3f}", f"RSI: {last_rsi:.1f}")
        st.line_chart(swing_data['Close'])
    else:
        st.warning("Čekam Swing podatke...")

with c_scalp:
    st.subheader("Scalp (2m)")
    if scalp_data is not None and not scalp_data.empty:
        last_rsi = scalp_data['RSI'].iloc[-1]
        last_price = scalp_data['Close'].iloc[-1]
        
        st.metric("Cijena", f"${last_price:.3f}", f"RSI: {last_rsi:.1f}")
        st.line_chart(scalp_data['Close'])
    else:
        st.warning("Čekam Scalp podatke...")
