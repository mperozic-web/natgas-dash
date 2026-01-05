import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta
import datetime

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V3.6", layout="wide", page_icon="⚡")
st.title("⚡ NatGas Sniper Desk V3.6")

# ==============================================================================
# 🔑 API KLJUČEVI
# ==============================================================================
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
# ==============================================================================

# --- 1. NOAA IZVORI ---
def interpret_noaa(index_name, val, date_str):
    val = float(val)
    status, color, desc = "NEUTRALNO", "off", "Nema jasnog trenda."
    if index_name == "AO":
        if val > 1.0: status, color, desc = "BEARISH (Toplo)", "inverse", "Hladnoća na sjeveru."
        elif val < -1.0: status, color, desc = "BULLISH (Hladno)", "normal", "Hladnoća se izlijeva."
    elif index_name == "NAO":
        if val > 1.0: status, color, desc = "BEARISH (Otvoren)", "inverse", "Toplina s Atlantika."
        elif val < -1.0: status, color, desc = "BULLISH (Blokada)", "normal", "Grenlandska blokada."
    elif index_name == "PNA":
        if val > 1.0: status, color, desc = "BULLISH (Hladno)", "normal", "Greben na zapadu."
        elif val < -1.0: status, color, desc = "BEARISH (Toplo)", "inverse", "Pacifički mlaz."
    return {"val": val, "status": status, "desc": desc, "color": color, "date": date_str}

def get_noaa_index(url, name):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        latest = df.iloc[-1]
        date_str = f"{int(latest['day'])}.{int(latest['month'])}.{int(latest['year'])}"
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        return interpret_noaa(name, latest[val_col], date_str)
    except: return None

# --- 2. EIA IZVORI (POJAČANO) ---
def get_eia_analysis(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 200}
        r = requests.get(url, params=params, timeout=15)
        res = r.json()
        if 'response' not in res: return None
        df = pd.DataFrame(res['response']['data'])
        df['value'] = df['value'].astype(int)
        df['period'] = pd.to_datetime(df['period'])
        df['week'] = df['period'].dt.isocalendar().week
        current = df.iloc[0]
        history = df.iloc[52:]
        avg_5y = int(history[history['week'] == current['week']].head(5)['value'].mean())
        return {"date": current['period'].strftime("%d.%m.%Y"), "current": current['value'], "change": current['value'] - df.iloc[1]['value'], "avg_5y": avg_5y, "diff_5y": current['value'] - avg_5y}
    except Exception as e:
        return f"Greška: {str(e)}"

# --- 3. MARKET DATA (YAHOO FIX) ---
def get_rsi_and_price():
    ticker = "NG=F"
    data = {"price": 0.0, "2m": 50.0, "1h": 50.0, "4h": 50.0}
    try:
        # 1. 1H Podaci (Najstabilniji za cijenu)
        df_1h = yf.download(ticker, interval="1h", period="1mo", progress=False)
        if not df_1h.empty:
            if isinstance(df_1h.columns, pd.MultiIndex): df_1h.columns = df_1h.columns.get_level_values(0)
            data["price"] = float(df_1h['Close'].iloc[-1])
            df_1h['RSI'] = df_1h.ta.rsi(length=14)
            data["1h"] = float(df_1h['RSI'].iloc[-1])
            # 4H Resample
            df_4h = df_1h.resample('4H').agg({'Close': 'last'})
            df_4h['RSI'] = df_4h.ta.rsi(length=14)
            data["4h"] = float(df_4h['RSI'].iloc[-1])
        
        # 2. 2m Podaci (Često failaju)
        df_2m = yf.download(ticker, interval="2m", period="1d", progress=False)
        if not df_2m.empty:
            if isinstance(df_2m.columns, pd.MultiIndex): df_2m.columns = df_2m.columns.get_level_values(0)
            df_2m['RSI'] = df_2m.ta.rsi(length=14)
            data["2m"] = float(df_2m['RSI'].iloc[-1])
            # Ako 2m radi, uzmi tu najsvježiju cijenu
            data["price"] = float(df_2m['Close'].iloc[-1])
    except: pass
    return data

# --- DOHVAT ---
ao = get_noaa_index("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_index("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_index("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
eia = get_eia_analysis(EIA_API_KEY)
market = get_rsi_and_price()

# --- LAYOUT ---
st.markdown("### 📡 Weather Sentiment (NOAA)")
c1, c2, c3 = st.columns(3)
def show_n(col, name, d):
    with col:
        if d: st.metric(name, f"{d['val']:.2f}", delta=d['status'], delta_color=d['color']); st.caption(f"📝 {d['desc']}\n📅 {d['date']}")
        else: st.warning(f"{name} nedostupan")
show_n(c1, "AO (Vortex)", ao); show_n(c2, "NAO (Atlantic)", nao); show_n(c3, "PNA (Pacific)", pna)

st.markdown("---")
st.markdown("### 🎯 Price & RSI Matrix")
st.metric("Trenutna Cijena (Futures)", f"${market['price']:.3f}")
m1, m2, m3 = st.columns(3)
def rsi_c(col, tf, val):
    state, color = "NEUTRAL", "off"
    if val > 70: state, color = "OVERBOUGHT", "inverse"
    elif val < 30: state, color = "OVERSOLD", "normal"
    with col: st.metric(f"RSI ({tf})", f"{val:.1f}", delta=state, delta_color=color)
rsi_c(m1, "2 MIN", market['2m']); rsi_c(m2, "1 H", market['1h']); rsi_c(m3, "4 H", market['4h'])

st.markdown("---")
st.markdown("### 🛢️ EIA Storage Analysis")
if isinstance(eia, dict):
    k1, k2, k3 = st.columns(3)
    k1.metric("Ukupne Zalihe", f"{eia['current']} Bcf", f"{eia['change']} Bcf", delta_color="inverse")
    k2.metric("5-Year Average", f"{eia['avg_5y']} Bcf", f"{eia['diff_5y']}:+ Bcf", delta_color="inverse")
    k3.info(f"📅 Izvještaj: {eia['date']}")
else: st.error(f"EIA Podaci: {eia if eia else 'Server ne odgovara'}")
