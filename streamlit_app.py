import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V3.8", layout="wide", page_icon="⚡")
st.title("⚡ NatGas Sniper Desk V3.8")

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. NOAA LOGIKA ---
def get_noaa(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val = float(lt[[c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]])
        dt = f"{int(lt['day'])}.{int(lt['month'])}.{int(lt['year'])}"
        
        status, color, bias = "NEUTRAL", "off", "Neutral"
        if name == "AO":
            if val < -0.8: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 0.8: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "NAO":
            if val < -0.5: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 0.5: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "PNA":
            if val > 0.5: status, color, bias = "BULLISH", "normal", "Long"
            elif val < -0.5: status, color, bias = "BEARISH", "inverse", "Short"
            
        return {"val": val, "status": status, "color": color, "date": dt, "bias": bias}
    except: return None

# --- 2. EIA LOGIKA ---
def get_eia(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 50}
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        df['value'] = df['value'].astype(int)
        df['period'] = pd.to_datetime(df['period'])
        curr = df.iloc[0]
        return {"date": curr['period'].strftime("%d.%m.%Y"), "val": curr['value'], "chg": curr['value'] - df.iloc[1]['value']}
    except: return None

# --- 3. MARKET DATA (NO-ZERO PRICE FIX) ---
def get_market():
    ticker = "NG=F"
    res = {"price": 0.0, "pct": 0.0, "2m": 50.0, "1h": 50.0, "4h": 50.0}
    try:
        # Sigurnosni dohvat cijene (Dnevni)
        df_d = yf.download(ticker, period="5d", interval="1d", progress=False)
        if not df_d.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            res["price"] = df_d['Close'].iloc[-1]
            res["pct"] = ((df_d['Close'].iloc[-1] - df_d['Close'].iloc[-2]) / df_d['Close'].iloc[-2]) * 100
        
        # RSI i preciznija cijena (ako postoji)
        df_1h = yf.download(ticker, period="1mo", interval="1h", progress=False)
        if not df_1h.empty:
            if isinstance(df_1h.columns, pd.MultiIndex): df_1h.columns = df_1h.columns.get_level_values(0)
            df_1h['RSI'] = df_1h.ta.rsi(length=14)
            res["1h"] = df_1h['RSI'].iloc[-1]
            if res["price"] == 0: res["price"] = df_1h['Close'].iloc[-1]
            df_4h = df_1h.resample('4H').agg({'Close': 'last'})
            df_4h['RSI'] = df_4h.ta.rsi(length=14)
            res["4h"] = df_4h['RSI'].iloc[-1]

        df_2m = yf.download(ticker, period="1d", interval="2m", progress=False)
        if not df_2m.empty:
            if isinstance(df_2m.columns, pd.MultiIndex): df_2m.columns = df_2m.columns.get_level_values(0)
            df_2m['RSI'] = df_2m.ta.rsi(length=14)
            res["2m"] = df_2m['RSI'].iloc[-1]
            res["price"] = df_2m['Close'].iloc[-1] # Najsvježije
    except: pass
    return res

# --- IZVRŠAVANJE ---
ao = get_noaa("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
mkt = get_market()
eia = get_eia(EIA_API_KEY)

# --- DISPLAY ---
st.markdown("### 📡 Weather Indices (NOAA)")
c1, c2, c3 = st.columns(3)
def d_n(col, name, d):
    with col:
        if d: st.metric(name, f"{d['val']:.2f}", d['status'], delta_color=d['color']); st.caption(f"📅 {d['date']}")
        else: st.warning("N/A")
d_n(c1, "AO", ao); d_n(c2, "NAO", nao); d_n(c3, "PNA", pna)

st.markdown("---")

# SEKCIJA: CIJENA I STRATEGIJA
st.markdown("### 🎯 Price & Signal Intelligence")
s1, s2 = st.columns([1, 2])

with s1:
    st.metric("NG Price", f"${mkt['price']:.3f}", f"{mkt['pct']:.2f}%")
    rsi_val = mkt['2m']
    if rsi_val < 30: st.success("🟢 RSI (2m) OVERSOLD: Razmisli o Long ulazu")
    elif rsi_val > 70: st.error("🔴 RSI (2m) OVERBOUGHT: Razmisli o Short izlazu")
    else: st.info(f"RSI (2m): {rsi_val:.1f} - Neutralno")

with s2:
    # ANALIZA USKLAĐENOSTI
    weather_long = sum(1 for x in [ao, nao, pna] if x and x['bias'] == "Long")
    weather_short = sum(1 for x in [ao, nao, pna] if x and x['bias'] == "Short")
    
    st.markdown("**Usporedba NOAA vs. Momentum:**")
    if weather_long >= 2:
        w_bias = "LONG (Bullish weather)"
        if rsi_val < 40: st.success("✅ KONFLUENCIJA: I Vrijeme i RSI sugeriraju LONG.")
        else: st.warning("⚠️ DIVERGENCIJA: Vrijeme je Long, ali RSI je preskup.")
    elif weather_short >= 2:
        w_bias = "SHORT (Bearish weather)"
        if rsi_val > 60: st.success("✅ KONFLUENCIJA: I Vrijeme i RSI sugeriraju SHORT.")
        else: st.warning("⚠️ DIVERGENCIJA: Vrijeme je Short, ali RSI je preprodan.")
    else:
        w_bias = "NEUTRAL"

st.markdown("---")
st.markdown("### 🛢️ Storage & Final Bias")
b1, b2 = st.columns(2)

with b1:
    if eia:
        st.metric("EIA Inventory", f"{eia['val']} Bcf", f"{eia['chg']} Bcf")
        st.caption(f"📅 Podatak od: {eia['date']}")
    else: st.error("EIA nedostupan.")

with b2:
    st.subheader("🏁 Favorizirana pozicija:")
    if weather_long >= 2 and mkt['2m'] < 50:
        st.write("🔥 **STRATEGIJA: FAVORIZIRAJ LONG**")
    elif weather_short >= 2 and mkt['2m'] > 50:
        st.write("❄️ **STRATEGIJA: FAVORIZIRAJ SHORT**")
    else:
        st.write("⚖️ **STRATEGIJA: NEUTRAL / SCALPING**")

st.markdown("---")
# RSI MATRICA NA DNU
r1, r2, r3 = st.columns(3)
r1.metric("RSI 2m", f"{mkt['2m']:.1f}")
r2.metric("RSI 1h", f"{mkt['1h']:.1f}")
r3.metric("RSI 4h", f"{mkt['4h']:.1f}")
