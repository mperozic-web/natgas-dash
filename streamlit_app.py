import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V4.1", layout="wide", page_icon="⚡")

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. NOAA LOGIKA ---
def get_noaa_data(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val = float(lt[[c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]])
        dt = f"{int(lt['day'])}.{int(lt['month'])}.{int(lt['year'])}"
        
        status, color, bias = "NEUTRALNO", "off", "Neutral"
        
        if name == "AO":
            if val < -2.5: status, color, bias = "EKSTREMNO BULLISH", "normal", "Long"
            elif val < -1.0: status, color, bias = "JAKO BULLISH", "normal", "Long"
            elif val > 2.5: status, color, bias = "EKSTREMNO BEARISH", "inverse", "Short"
            elif val > 1.0: status, color, bias = "JAKO BEARISH", "inverse", "Short"
        elif name == "NAO":
            if val < -1.2: status, color, bias = "JAKO BULLISH", "normal", "Long"
            elif val > 1.2: status, color, bias = "JAKO BEARISH", "inverse", "Short"
        elif name == "PNA":
            if val > 1.2: status, color, bias = "JAKO BULLISH", "normal", "Long"
            elif val < -1.2: status, color, bias = "JAKO BEARISH", "inverse", "Short"
            
        return {"val": val, "status": status, "color": color, "date": dt, "bias": bias}
    except: return None

# --- 2. EIA STORAGE (S USPPOREDBOM 5y AVG) ---
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
        curr_val = curr['value']
        curr_week_num = curr['week']
        
        # 5-Year Average Kalkulacija
        history = df.iloc[52:]
        same_weeks = history[history['week'] == curr_week_num]
        avg_5y = int(same_weeks.head(5)['value'].mean())
        diff_5y = curr_val - avg_5y
        
        bias = "Bullish (Deficit)" if diff_5y < 0 else "Bearish (Višak)" if diff_5y > 0 else "Neutral"
        
        return {
            "date": curr['period'].strftime("%d.%m.%Y"), 
            "val": curr_val, 
            "chg": curr_val - df.iloc[1]['value'], 
            "avg_5y": avg_5y,
            "diff_5y": diff_5y,
            "bias": bias
        }
    except: return None

# --- 3. MARKET DATA ---
def get_market_data():
    ticker = "NG=F"
    res = {"price": 0.0, "pct": 0.0, "2m": 50.0, "1h": 50.0, "4h": 50.0, "bias": "Neutral"}
    try:
        df = yf.download(ticker, period="5d", interval="1h", progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            res["price"] = df['Close'].iloc[-1]
            res["pct"] = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
            df['RSI'] = df.ta.rsi(length=14)
            res["1h"] = df['RSI'].iloc[-1]
            if res["1h"] < 35: res["bias"] = "Long (Oversold)"
            elif res["1h"] > 65: res["bias"] = "Short (Overbought)"

        df_2m = yf.download(ticker, period="1d", interval="2m", progress=False)
        if not df_2m.empty:
            if isinstance(df_2m.columns, pd.MultiIndex): df_2m.columns = df_2m.columns.get_level_values(0)
            df_2m['RSI'] = df_2m.ta.rsi(length=14)
            res["2m"] = df_2m['RSI'].iloc[-1]
            res["price"] = df_2m['Close'].iloc[-1]
    except: pass
    return res

# --- IZVRŠAVANJE ---
ao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_data("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
mkt = get_market_data()
eia = get_eia_data(EIA_API_KEY)

# --- 1. TOP BAR: MASTER BIAS ---
st.title("⚡ NatGas Sniper Desk V4.1")
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

# --- 2. METEO SEKCIJA ---
st.subheader("📡 NOAA Weather Logic")
c1, c2, c3 = st.columns(3)
def draw_noaa(col, name, d):
    with col:
        if d:
            st.metric(name, f"{d['val']:.2f}", d['status'], delta_color=d['color'])
            st.write(f"**Meteo Bias: {d['bias']}**")
            st.caption(f"📅 Datum: {d['date']}")
        else: st.error(f"{name} Error")
draw_noaa(c1, "AO (Vortex)", ao)
draw_noaa(c2, "NAO (Atlantic)", nao)
draw_noaa(c3, "PNA (Pacific)", pna)

st.markdown("---")

# --- 3. MARKET SEKCIJA ---
st.subheader("🎯 Market Intelligence")
col_p, col_r = st.columns([1, 2])
with col_p:
    st.metric("NatGas Price", f"${mkt['price']:.3f}", f"{mkt['pct']:.2f}%")
    st.markdown(f"**Technical Bias: {mkt['bias']}**")
with col_r:
    r1, r2, r3 = st.columns(3)
    r1.metric("RSI 2m", f"{mkt['2m']:.1f}")
    r2.metric("RSI 1h", f"{mkt['1h']:.1f}")
    r3.metric("RSI 4h", f"{mkt['4h']:.1f}")

st.markdown("---")

# --- 4. STORAGE SEKCIJA (REVIZIRANA) ---
st.subheader("🛢️ EIA Inventory & 5-Year Average")
if eia:
    k1, k2, k3 = st.columns(3)
    k1.metric("Zalihe", f"{eia['val']} Bcf", f"{eia['chg']} Bcf Tjedno")
    k2.metric("5y Average", f"{eia['avg_5y']} Bcf", f"{eia['diff_5y']}:+ Bcf vs Avg", delta_color="inverse")
    with k3:
        st.write(f"**Storage Bias: {eia['bias']}**")
        st.caption(f"📅 Izvještaj od: {eia['date']}")
else: st.error("EIA podaci trenutno nedostupni.")
