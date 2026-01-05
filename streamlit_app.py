import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V3.7", layout="wide", page_icon="⚡")
st.title("⚡ NatGas Sniper Desk V3.7")

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. NOAA GRADACIJA ---
def interpret_noaa(name, val, date_str):
    val = float(val)
    status, color, desc = "NEUTRALNO", "off", "Nema jasnog trenda."
    
    # AO Gradacija
    if name == "AO":
        if val < -2.5: status, color, desc = "EKSTREMNO BULLISH", "normal", "Raspad vrtloga! Arktički udar."
        elif val < -1.0: status, color, desc = "JAKO BULLISH", "normal", "Hladnoća se izlijeva na jug."
        elif val < -0.5: status, color, desc = "BULLISH", "normal", "Vrtlog nestabilan."
        elif val > 2.5: status, color, desc = "EKSTREMNO BEARISH", "inverse", "Vrtlog prejak. Zaboravi zimu."
        elif val > 1.0: status, color, desc = "JAKO BEARISH", "inverse", "Hladnoća zaključana na polu."
        elif val > 0.5: status, color, desc = "BEARISH", "inverse", "Topliji uzorak."

    # NAO Gradacija
    elif name == "NAO":
        if val < -1.5: status, color, desc = "EKSTREMNO BULLISH", "normal", "Snažna blokada na Grenlandu!"
        elif val < -0.5: status, color, desc = "BULLISH", "normal", "Povoljno za hladnoću na istoku SAD."
        elif val > 1.5: status, color, desc = "EKSTREMNO BEARISH", "inverse", "Atlantik 'puše' toplinu."
        elif val > 0.5: status, color, desc = "BEARISH", "inverse", "Nema blokade."

    # PNA Gradacija
    elif name == "PNA":
        if val > 1.5: status, color, desc = "EKSTREMNO BULLISH", "normal", "Masivan greben na zapadu."
        elif val > 0.5: status, color, desc = "BULLISH", "normal", "Hladnoća ide na istok."
        elif val < -1.5: status, color, desc = "EKSTREMNO BEARISH", "inverse", "Topli pacifički zrak dominira."
        elif val < -0.5: status, color, desc = "BEARISH", "inverse", "Nepovoljan uzorak."

    return {"val": val, "status": status, "desc": desc, "color": color, "date": date_str}

def get_noaa(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        dt = f"{int(lt['day'])}.{int(lt['month'])}.{int(lt['year'])}"
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        return interpret_noaa(name, lt[val_col], dt)
    except: return None

# --- 2. EIA STORAGE ---
def get_eia(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 200}
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        df['value'] = df['value'].astype(int)
        df['period'] = pd.to_datetime(df['period'])
        df['week'] = df['period'].dt.isocalendar().week
        curr = df.iloc[0]
        hist = df.iloc[52:]
        avg5 = int(hist[hist['week'] == curr['week']].head(5)['value'].mean())
        return {"date": curr['period'].strftime("%d.%m.%Y"), "val": curr['value'], "chg": curr['value'] - df.iloc[1]['value'], "avg": avg5, "diff": curr['value'] - avg5}
    except: return None

# --- 3. MARKET DATA (PRICE + DAILY % + RSI) ---
def get_market():
    ticker = "NG=F"
    res = {"price": 0.0, "pct": 0.0, "2m": 50.0, "1h": 50.0, "4h": 50.0}
    try:
        # Uzimamo dnevni interval za točan % pomak
        df_d = yf.download(ticker, period="2d", interval="1d", progress=False)
        if not df_d.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            c_price = df_d['Close'].iloc[-1]
            p_price = df_d['Close'].iloc[-2]
            res["price"] = c_price
            res["pct"] = ((c_price - p_price) / p_price) * 100
        
        # RSI 1H & 4H
        df_1h = yf.download(ticker, period="1mo", interval="1h", progress=False)
        if not df_1h.empty:
            if isinstance(df_1h.columns, pd.MultiIndex): df_1h.columns = df_1h.columns.get_level_values(0)
            df_1h['RSI'] = df_1h.ta.rsi(length=14)
            res["1h"] = df_1h['RSI'].iloc[-1]
            df_4h = df_1h.resample('4H').agg({'Close': 'last'})
            df_4h['RSI'] = df_4h.ta.rsi(length=14)
            res["4h"] = df_4h['RSI'].iloc[-1]

        # RSI 2M
        df_2m = yf.download(ticker, period="1d", interval="2m", progress=False)
        if not df_2m.empty:
            if isinstance(df_2m.columns, pd.MultiIndex): df_2m.columns = df_2m.columns.get_level_values(0)
            df_2m['RSI'] = df_2m.ta.rsi(length=14)
            res["2m"] = df_2m['RSI'].iloc[-1]
    except: pass
    return res

# --- DASHBOARD ---
ao = get_noaa("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
eia = get_eia(EIA_API_KEY)
mkt = get_market()

# Sekcija 1: NOAA
st.markdown("### 📡 Weather Sentiment (NOAA)")
c1, c2, c3 = st.columns(3)
def disp_n(col, name, d):
    with col:
        if d: 
            st.metric(name, f"{d['val']:.2f}", delta=d['status'], delta_color=d['color'])
            st.caption(f"**{d['desc']}**")
            st.caption(f"📅 Datum: {d['date']}")
        else: st.warning(f"{name} N/A")
disp_n(c1, "AO (Vortex)", ao); disp_n(c2, "NAO (Atlantic)", nao); disp_n(c3, "PNA (Pacific)", pna)

st.markdown("---")

# Sekcija 2: Price & RSI
st.markdown("### 🎯 Price & RSI Matrix")
st.metric("NatGas Futures", f"${mkt['price']:.3f}", f"{mkt['pct']:.2f}%")
r1, r2, r3 = st.columns(3)
def r_card(col, tf, val):
    s, c = "NEUTRAL", "off"
    if val > 70: s, c = "OVERBOUGHT", "inverse"
    elif val < 30: s, c = "OVERSOLD", "normal"
    col.metric(f"RSI ({tf})", f"{val:.1f}", delta=s, delta_color=c)
r_card(r1, "2 MIN", mkt['2m']); r_card(r2, "1 H", mkt['1h']); r_card(r3, "4 H", mkt['4h'])

st.markdown("---")

# Sekcija 3: EIA
st.markdown("### 🛢️ EIA Storage Analysis")
if eia:
    k1, k2, k3 = st.columns(3)
    k1.metric("Trenutne Zalihe", f"{eia['val']} Bcf", f"{eia['chg']} Bcf", delta_color="inverse")
    k2.metric("5y Average", f"{eia['avg']} Bcf", f"{eia['diff']:+} Bcf vs Avg", delta_color="inverse")
    k3.info(f"📅 Zadnji EIA podatak: {eia['date']}")
    if eia['diff'] > 150: st.error("⚠️ EKSTREMNI VIŠAK (Bearish)")
    elif eia['diff'] < -150: st.success("🚀 EKSTREMNI DEFICIT (Bullish)")
else: st.error("EIA server ne šalje podatke.")
