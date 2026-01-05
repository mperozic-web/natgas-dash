import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V3.5", layout="wide", page_icon="⚡")
st.title("⚡ NatGas Sniper Desk V3.5 (Perfected)")

# ==============================================================================
# 🔑 API KLJUČEVI
# ==============================================================================
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
# ==============================================================================

# --- 1. NAPREDNA LOGIKA ZA VRIJEME (NOAA) ---
def interpret_noaa(index_name, val, date_str):
    val = float(val)
    status = "NEUTRALNO"
    color = "off"
    desc = ""
    
    if index_name == "AO":
        if val > 2.5:
            status, desc, color = "EKSTREMNO BEARISH", "Polarni vrtlog super-stabilan. Zima otkazana.", "inverse"
        elif val > 0.5:
            status, desc, color = "BEARISH (Toplo)", "Hladnoća se drži sjevera.", "inverse"
        elif val < -2.5:
            status, desc, color = "EKSTREMNO BULLISH", "Raspad polarnog vrtloga! Arktički udar.", "normal"
        elif val < -0.5:
            status, desc, color = "BULLISH (Hladno)", "Vrtlog nestabilan, hladnoća curi.", "normal"
        else:
            desc = "Nema jasnog trenda."

    elif index_name == "NAO":
        if val > 1.5:
            status, desc, color = "JAKO BEARISH", "Atlantik otvoren. Topli zrak juriša na SAD.", "inverse"
        elif val > 0.5:
            status, desc, color = "BEARISH", "Nema blokade.", "inverse"
        elif val < -1.5:
            status, desc, color = "JAKO BULLISH", "Grenlandska blokada! Hladnoća zarobljena.", "normal"
        elif val < -0.5:
            status, desc, color = "BULLISH", "Slabi zonalni vjetrovi.", "normal"
        else:
            desc = "Nema jasnog signala."

    elif index_name == "PNA":
        if val > 1.5:
            status, desc, color = "JAKO BULLISH", "Masivan greben na zapadu gura hladnoću.", "normal"
        elif val > 0.5:
            status, desc, color = "BULLISH", "Povoljan uzorak za hladnoću.", "normal"
        elif val < -1.5:
            status, desc, color = "JAKO BEARISH", "Pacifički mlaz ubija hladnoću.", "inverse"
        elif val < -0.5:
            status, desc, color = "BEARISH", "Nepovoljan uzorak.", "inverse"
        else:
            desc = "Miješani signali."

    return {"val": val, "status": status, "desc": desc, "color": color, "date": date_str}

def get_noaa_index(url, name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        latest = df.iloc[-1]
        date_str = f"{int(latest['day'])}.{int(latest['month'])}.{int(latest['year'])}"
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        return interpret_noaa(name, latest[val_col], date_str)
    except:
        return None

# --- 2. FUNKCIJE ZA ZALIHE (EIA) ---
def get_eia_analysis(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {
            "api_key": api_key, "frequency": "weekly", "data[0]": "value",
            "facets[series][]": "NW2_EPG0_SWO_R48_BCF", 
            "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 300
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if 'response' not in data: return None
        df = pd.DataFrame(data['response']['data'])
        df['value'] = df['value'].astype(int)
        current = df.iloc[0]
        last_week = df.iloc[1]
        change = current['value'] - last_week['value']
        df['period'] = pd.to_datetime(df['period'])
        df['week'] = df['period'].dt.isocalendar().week
        curr_week_num = current['week']
        history = df.iloc[52:]
        same_weeks = history[history['week'] == curr_week_num]
        avg_5y = int(same_weeks.head(5)['value'].mean())
        diff_5y = current['value'] - avg_5y
        return {
            "date": current['period'].strftime("%d.%m.%Y"),
            "current": current['value'],
            "change": change,
            "avg_5y": avg_5y,
            "diff_5y": diff_5y
        }
    except:
        return None

# --- 3. RSI MATRICA (MULTI-TF) ---
def get_rsi_matrix():
    ticker = "NG=F"
    matrix = {}
    try:
        df_2m = yf.download(ticker, interval="2m", period="1d", progress=False)
        if not df_2m.empty:
            if isinstance(df_2m.columns, pd.MultiIndex): df_2m.columns = df_2m.columns.get_level_values(0)
            df_2m['RSI'] = df_2m.ta.rsi(length=14)
            matrix['2m'] = df_2m['RSI'].iloc[-1]
            matrix['price'] = df_2m['Close'].iloc[-1]
        
        df_1h = yf.download(ticker, interval="1h", period="1mo", progress=False)
        if not df_1h.empty:
            if isinstance(df_1h.columns, pd.MultiIndex): df_1h.columns = df_1h.columns.get_level_values(0)
            df_1h['RSI'] = df_1h.ta.rsi(length=14)
            matrix['1h'] = df_1h['RSI'].iloc[-1]
            df_4h = df_1h.resample('4H').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
            df_4h['RSI'] = df_4h.ta.rsi(length=14)
            matrix['4h'] = df_4h['RSI'].iloc[-1]
    except:
        return None
    return matrix

# --- DOHVAT PODATAKA ---
URL_AO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv"
URL_NAO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv"
URL_PNA = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv"

ao = get_noaa_index(URL_AO, "AO")
nao = get_noaa_index(URL_NAO, "NAO")
pna = get_noaa_index(URL_PNA, "PNA")
eia = get_eia_analysis(EIA_API_KEY)
rsi_data = get_rsi_matrix()

# --- DASHBOARD LAYOUT ---
st.markdown("### 📡 Weather Sentiment (NOAA)")
c1, c2, c3 = st.columns(3)

def show_noaa(col, name, data):
    with col:
        st.markdown(f"**{name}**")
        if data:
            st.metric("Vrijednost", f"{data['val']:.2f}", delta=data['status'], delta_color=data['color'])
            st.caption(f"📝 {data['desc']}")
            st.caption(f"📅 Datum: {data['date']}")
        else:
            st.warning("Učitavanje...")

show_noaa(c1, "AO (Polar Vortex)", ao)
show_noaa(c2, "NAO (Atlantic Block)", nao)
show_noaa(c3, "PNA (Pacific Pattern)", pna)

st.markdown("---")
st.markdown("### 🎯 Price & RSI Matrix")
if rsi_data:
    st.metric("Trenutna Cijena (Futures)", f"${rsi_data.get('price', 0):.3f}")
    cols = st.columns(3)
    def rsi_card(col, tf, val):
        state = "NEUTRAL"
        color = "off"
        if val > 70: state, color = "OVERBOUGHT", "inverse"
        elif val < 30: state, color = "OVERSOLD", "normal"
        with col:
            st.metric(f"RSI ({tf})", f"{val:.1f}", delta=state, delta_color=color)
    rsi_card(cols[0], "2 MIN (Scalp)", rsi_data.get('2m', 50))
    rsi_card(cols[1], "1 H (Swing)", rsi_data.get('1h', 50))
    rsi_card(cols[2], "4 H (Trend)", rsi_data.get('4h', 50))

st.markdown("---")
st.markdown("### 🛢️ EIA Storage Analysis")
if eia:
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Ukupne Zalihe", f"{eia['current']} Bcf", f"{eia['change']} Bcf (Promjena)", delta_color="inverse")
    with k2:
        val_diff = eia['diff_5y']
        lbl = "Višak vs 5y Avg" if val_diff > 0 else "Manjak vs 5y Avg"
        st.metric("5-Year Average", f"{eia['avg_5y']} Bcf", f"{val_diff:+} Bcf", delta_color="inverse")
    with k3:
        st.info(f"📅 Tjedan: {eia['date']}")
        if eia['diff_5y'] > 100: st.error("⚠️ PREZASIĆENJE")
        elif eia['diff_5y'] < -100: st.success("✅ DEFICIT")
