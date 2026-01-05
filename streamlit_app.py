import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta
from datetime import datetime, timedelta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V4.4", layout="wide", page_icon="⚡")

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- POMOĆNA FUNKCIJA ZA SIGURNU CIJENU ---
def get_live_price():
    """Pokušava dobiti cijenu putem više metoda ako yfinance zakaže."""
    ticker = "NG=F"
    try:
        # Metoda 1: Brzi snapshot
        t = yf.Ticker(ticker)
        p = t.fast_info['last_price']
        if p > 0: return p
    except:
        try:
            # Metoda 2: Povijesni podaci zadnja 2 dana
            df = yf.download(ticker, period="2d", interval="1m", progress=False)
            if not df.empty:
                return df['Close'].iloc[-1]
        except: return 0.0
    return 0.0

# --- 1. NOAA LOGIKA ---
def get_noaa_data(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val = float(lt[[c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]])
        dt = f"{int(lt['day'])}.{int(lt['month'])}.{int(lt['year'])}"
        
        status, color, bias = "NEUTRAL", "off", "Neutral"
        if name == "AO":
            if val < -1.0: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 1.0: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "NAO":
            if val < -0.6: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 0.6: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "PNA":
            if val > 0.6: status, color, bias = "BULLISH", "normal", "Long"
            elif val < -0.6: status, color, bias = "BEARISH", "inverse", "Short"
            
        return {"val": val, "status": status, "color": color, "date": dt, "bias": bias}
    except: return None

# --- 2. EIA STORAGE (SA ZASTARJELOST INDIKATOROM) ---
def get_eia_data(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 250}
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        df['value'] = df['value'].astype(int)
        df['period'] = pd.to_datetime(df['period'])
        df['week'] = df['period'].dt.isocalendar().week
        
        curr = df.iloc[0]
        # Provjera starosti
        is_stale = (datetime.now() - curr['period']).days > 7
        
        history = df.iloc[52:]
        same_weeks = history[history['week'] == curr['week']]
        avg_5y = int(same_weeks.head(5)['value'].mean())
        diff_5y = curr['value'] - avg_5y
        
        bias = "Bullish (Deficit)" if diff_5y < 0 else "Bearish (Višak)"
        return {"date": curr['period'].strftime("%d.%m.%Y"), "val": curr['value'], "chg": curr['value'] - df.iloc[1]['value'], "avg_5y": avg_5y, "diff_5y": diff_5y, "bias": bias, "stale": is_stale}
    except: return None

# --- 3. MARKET DATA (RESILIENT VERSION) ---
def get_market_data():
    ticker = "NG=F"
    res = {"price": 0.0, "pct": 0.0, "2m": None, "1h": None, "4h": None, "bias": "No Data"}
    try:
        # Primarni dohvat: 1h podaci za stabilnost
        df_h = yf.download(ticker, period="1mo", interval="1h", progress=False)
        if not df_h.empty:
            if isinstance(df_h.columns, pd.MultiIndex): df_h.columns = df_h.columns.get_level_values(0)
            res["price"] = float(df_h['Close'].iloc[-1])
            res["pct"] = ((df_h['Close'].iloc[-1] - df_h['Close'].iloc[-2]) / df_h['Close'].iloc[-2]) * 100
            
            rsi_h = ta.rsi(df_h['Close'], length=14)
            res["1h"] = float(rsi_h.iloc[-1]) if not rsi_h.empty else None
            
            df_4h = df_h.resample('4H').last().dropna()
            rsi_4h = ta.rsi(df_4h['Close'], length=14)
            res["4h"] = float(rsi_4h.iloc[-1]) if not rsi_4h.empty else None

        # Scalp podaci (2m)
        df_m = yf.download(ticker, period="1d", interval="2m", progress=False)
        if not df_m.empty:
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)
            rsi_m = ta.rsi(df_m['Close'], length=14)
            res["2m"] = float(rsi_m.iloc[-1]) if not rsi_m.empty else None
            res["price"] = float(df_m['Close'].iloc[-1]) # Update na najnoviju

        # Bias Logic
        if res["1h"] and res["1h"] < 35: res["bias"] = "LONG (Technical)"
        elif res["1h"] and res["1h"] > 65: res["bias"] = "SHORT (Technical)"
        else: res["bias"] = "NEUTRAL"
            
    except: pass
    return res

# --- IZVRŠAVANJE ---
ao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
mkt = get_market_data()
eia = get_eia_data(EIA_API_KEY)

# --- DISPLAY ---
st.title("⚡ NatGas Sniper Desk V4.4")

# MASTER BIAS BAR
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

# METEO
st.subheader("📡 NOAA Weather Logic")
c1, c2, c3 = st.columns(3)
def draw_noaa(col, name, d):
    with col:
        if d:
            st.metric(name, f"{d['val']:.2f}", d['status'], delta_color=d['color'])
            st.write(f"**Meteo Bias: {d['bias']}**")
        else: st.error(f"{name} Error")
draw_noaa(c1, "AO (Vortex)", ao); draw_noaa(c2, "NAO (Atlantic)", nao); draw_noaa(c3, "PNA (Pacific)", pna)

st.markdown("---")

# MARKET
st.subheader("🎯 Market Intelligence")
col_p, col_r = st.columns([1, 2])
with col_p:
    if mkt['price'] > 0:
        st.metric("Price (NG=F)", f"${mkt['price']:.3f}", f"{mkt['pct']:.2f}%")
        st.write(f"**Technical Bias: {mkt['bias']}**")
    else: st.error("Market Price Unavailable (API Limit)")

with col_r:
    r1, r2, r3 = st.columns(3)
    r1.metric("RSI 2m", f"{mkt['2m']:.1f}" if mkt['2m'] else "N/A")
    r2.metric("RSI 1h", f"{mkt['1h']:.1f}" if mkt['1h'] else "N/A")
    r3.metric("RSI 4h", f"{mkt['4h']:.1f}" if mkt['4h'] else "N/A")

st.markdown("---")

# STORAGE
st.subheader("🛢️ EIA Inventory & 5-Year Average")
if eia:
    if eia['stale']: st.warning("⚠️ Čeka se novi tjedni izvještaj (podatak je od prošlog tjedna)")
    k1, k2, k3 = st.columns(3)
    k1.metric("Zalihe", f"{eia['val']} Bcf", f"{eia['chg']} Bcf")
    k2.metric("vs 5y Average", f"{eia['avg_5y']} Bcf", f"{eia['diff_5y']}:+ Bcf", delta_color="inverse")
    with k3:
        st.write(f"**Storage Bias: {eia['bias']}**")
        st.caption(f"📅 Datum izvještaja: {eia['date']}")
