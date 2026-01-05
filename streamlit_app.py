import streamlit as st
import pandas as pd
import numpy as np
import requests
import io
import yfinance as yf
import pandas_ta as ta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V4.3", layout="wide", page_icon="⚡")

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. NOAA LOGIKA (GRADACIJA + BIAS) ---
def get_noaa_data(url, name):
    try:
        r = requests.get(url, timeout=12)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val = float(lt[[c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]])
        dt = f"{int(lt['day'])}.{int(lt['month'])}.{int(latest_year := lt['year'])}"
        
        # Gradacija i Bias
        status, color, bias = "NEUTRAL", "off", "Neutral"
        if name == "AO":
            if val < -2.0: status, color, bias = "EKSTREMNO BULLISH", "normal", "Long"
            elif val < -0.7: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 2.0: status, color, bias = "EKSTREMNO BEARISH", "inverse", "Short"
            elif val > 0.7: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "NAO":
            if val < -0.8: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 0.8: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "PNA":
            if val > 0.8: status, color, bias = "BULLISH", "normal", "Long"
            elif val < -0.8: status, color, bias = "BEARISH", "inverse", "Short"
            
        return {"val": val, "status": status, "color": color, "date": dt, "bias": bias}
    except: return None

# --- 2. EIA STORAGE (5y AVG + BIAS) ---
def get_eia_data(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 300}
        r = requests.get(url, params=params, timeout=15).json()
        df = pd.DataFrame(r['response']['data'])
        df['value'] = df['value'].astype(int)
        df['period'] = pd.to_datetime(df['period'])
        df['week'] = df['period'].dt.isocalendar().week
        
        curr = df.iloc[0]
        history = df.iloc[52:]
        avg_5y = int(history[history['week'] == curr['week']].head(5)['value'].mean())
        diff_5y = curr['value'] - avg_5y
        
        bias = "Bullish (Deficit)" if diff_5y < 0 else "Bearish (Višak)" if diff_5y > 0 else "Neutral"
        return {"date": curr['period'].strftime("%d.%m.%Y"), "val": curr['value'], "chg": curr['value'] - df.iloc[1]['value'], "avg_5y": avg_5y, "diff_5y": diff_5y, "bias": bias}
    except: return None

# --- 3. MARKET INTELLIGENCE (SNAJPER REVIZIJA) ---
def get_clean_market():
    ticker = "NG=F"
    res = {"price": 0.0, "pct": 0.0, "2m": 50.0, "1h": 50.0, "4h": 50.0, "bias": "Neutral"}
    
    try:
        # Satni podaci za trend i RSI
        h1 = yf.download(ticker, period="2mo", interval="1h", progress=False)
        if not h1.empty:
            if isinstance(h1.columns, pd.MultiIndex): h1.columns = h1.columns.get_level_values(0)
            h1 = h1[['Close']].copy().dropna()
            
            res["price"] = float(h1['Close'].iloc[-1])
            res["pct"] = float(((h1['Close'].iloc[-1] - h1['Close'].iloc[-24]) / h1['Close'].iloc[-24]) * 100) # 24h promjena
            
            res["1h"] = float(ta.rsi(h1['Close'], length=14).iloc[-1])
            
            # 4H Resample
            h4 = h1.resample('4H').last().dropna()
            res["4h"] = float(ta.rsi(h4['Close'], length=14).iloc[-1])

        # Scalp podaci (2m) - najkritičniji dio
        m2 = yf.download(ticker, period="1d", interval="2m", progress=False)
        if not m2.empty:
            if isinstance(m2.columns, pd.MultiIndex): m2.columns = m2.columns.get_level_values(0)
            m2 = m2[['Close']].copy().dropna()
            res["2m"] = float(ta.rsi(m2['Close'], length=14).iloc[-1])
            res["price"] = float(m2['Close'].iloc[-1]) # Stvarna live cijena

        # Technical Bias Logic
        if res["2m"] < 30 and res["1h"] < 40: res["bias"] = "STRONG LONG"
        elif res["2m"] > 70 and res["1h"] > 60: res["bias"] = "STRONG SHORT"
        elif res["2m"] < 30: res["bias"] = "Scalp Long"
        elif res["2m"] > 70: res["bias"] = "Scalp Short"
        
    except Exception as e:
        st.error(f"Market Error: {e}")
    return res

# --- IZVRŠAVANJE ---
ao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
mkt = get_clean_market()
eia = get_eia_data(EIA_API_KEY)

# --- DISPLAY ---
st.title("⚡ NatGas Sniper Desk V4.3")

# 1. MASTER BIAS BAR (SUMARNI PREGLED)
st.subheader("🏁 Master Bias Summary")
b1, b2, b3 = st.columns(3)
with b1:
    m_bias = "Long" if (ao and ao['bias'] == "Long") else "Short" if (ao and ao['bias'] == "Short") else "Neutral"
    st.info(f"🌍 METEO BIAS: {m_bias}")
with b2:
    st.info(f"📊 TECH BIAS: {mkt['bias']}")
with b3:
    s_bias = eia['bias'] if eia else "N/A"
    st.info(f"🛢️ STORAGE BIAS: {s_bias}")

st.markdown("---")

# 2. METEO
st.subheader("📡 NOAA Weather Logic")
c1, c2, c3 = st.columns(3)
def d_noaa(col, name, d):
    with col:
        if d:
            st.metric(name, f"{d['val']:.2f}", d['status'], delta_color=d['color'])
            st.write(f"**Meteo Bias: {d['bias']}**")
            st.caption(f"📅 {d['date']} | {d['status']}")
        else: st.error("N/A")
d_noaa(c1, "AO (Vortex)", ao); d_noaa(c2, "NAO (Atlantic)", nao); d_noaa(c3, "PNA (Pacific)", pna)

st.markdown("---")

# 3. MARKET
st.subheader("🎯 Market Intelligence")
col_p, col_r = st.columns([1, 2])
with col_p:
    st.metric("Price (NG=F)", f"${mkt['price']:.3f}", f"{mkt['pct']:.2f}%")
    st.write(f"**Technical Bias: {mkt['bias']}**")
with col_r:
    r1, r2, r3 = st.columns(3)
    r1.metric("RSI 2m", f"{mkt['2m']:.1f}")
    r2.metric("RSI 1h", f"{mkt['1h']:.1f}")
    r3.metric("RSI 4h", f"{mkt['4h']:.1f}")

st.markdown("---")

# 4. STORAGE
st.subheader("🛢️ EIA Inventory & 5-Year Average")
if eia:
    k1, k2, k3 = st.columns(3)
    k1.metric("Zalihe", f"{eia['val']} Bcf", f"{eia['chg']} Bcf")
    k2.metric("vs 5y Average", f"{eia['avg_5y']} Bcf", f"{eia['diff_5y']}:+ Bcf", delta_color="inverse")
    with k3:
        st.write(f"**Storage Bias: {eia['bias']}**")
        st.caption(f"📅 Izvještaj: {eia['date']}")
