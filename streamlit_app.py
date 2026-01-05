import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V3.4", layout="wide", page_icon="⚡")
st.title("⚡ NatGas Sniper Desk V3.4")

# ==============================================================================
# 🔑 API KLJUČEVI
# ==============================================================================
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
# ==============================================================================

# --- 1. FUNKCIJE ZA VRIJEME (NOAA) ---
def interpret_noaa(index_name, val, date_str):
    val = float(val)
    status = "NEUTRAL"
    color = "off"
    
    # Logika za boje i status
    if index_name == "AO":
        if val > 1.0: status, color = "BEARISH (Toplo)", "inverse"
        elif val < -1.0: status, color = "BULLISH (Hladno)", "normal"
    elif index_name == "NAO":
        if val > 1.0: status, color = "BEARISH (Otvoren)", "inverse"
        elif val < -1.0: status, color = "BULLISH (Blokada)", "normal"
    elif index_name == "PNA":
        if val > 1.0: status, color = "BULLISH (Hl. Istok)", "normal"
        elif val < -1.0: status, color = "BEARISH (Top. Istok)", "inverse"

    return {"val": val, "status": status, "color": color, "date": date_str}

def get_noaa_index(url, name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        
        # Uzmi zadnji red
        latest = df.iloc[-1]
        
        # Datum formatiranje (Year, Month, Day su stupci)
        date_str = f"{int(latest['day'])}.{int(latest['month'])}.{int(latest['year'])}"
        
        # Nađi stupac s vrijednosti
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
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        df = pd.DataFrame(data['response']['data'])
        df['value'] = df['value'].astype(int)
        
        current = df.iloc[0]
        change = current['value'] - df.iloc[1]['value']
        
        # 5-Year Avg Logic
        df['period'] = pd.to_datetime(df['period'])
        df['week'] = df['period'].dt.isocalendar().week
        curr_week = current['week']
        history = df.iloc[52:]
        avg_5y = int(history[history['week'] == curr_week].head(5)['value'].mean())
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

# --- 3. FUNKCIJE ZA RSI MATRICU (MULTI-TIMEFRAME) ---
def get_rsi_matrix():
    ticker = "NG=F"
    matrix = {}
    
    try:
        # 1. SCALP (2 MIN)
        df_2m = yf.download(ticker, interval="2m", period="1d", progress=False)
        if not df_2m.empty:
            if isinstance(df_2m.columns, pd.MultiIndex): df_2m.columns = df_2m.columns.get_level_values(0)
            df_2m['RSI'] = df_2m.ta.rsi(length=14)
            matrix['2m'] = df_2m['RSI'].iloc[-1]
            matrix['price'] = df_2m['Close'].iloc[-1] # Trenutna cijena
        
        # 2. SWING (1 H)
        df_1h = yf.download(ticker, interval="1h", period="1mo", progress=False)
        if not df_1h.empty:
            if isinstance(df_1h.columns, pd.MultiIndex): df_1h.columns = df_1h.columns.get_level_values(0)
            df_1h['RSI'] = df_1h.ta.rsi(length=14)
            matrix['1h'] = df_1h['RSI'].iloc[-1]
            
            # 3. TREND (4 H) - Resampling iz 1H podataka
            # (Yahoo API nema čistih 4h, pa ih sami kreiramo spajanjem 1h svijeća)
            df_4h = df_1h.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
            df_4h['RSI'] = df_4h.ta.rsi(length=14)
            matrix['4h'] = df_4h['RSI'].iloc[-1]
            
    except Exception as e:
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

# ==============================================================================
# DASHBOARD LAYOUT
# ==============================================================================

# --- RED 1: NOAA (Vrijeme) ---
st.markdown("### 📡 Weather Sentiment (NOAA)")
c1, c2, c3 = st.columns(3)

def show_noaa(col, name, data):
    with col:
        if data:
            st.metric(name, f"{data['val']:.2f}", delta=data['status'], delta_color=data['color'])
            st.caption(f"📅 Datum: {data['date']}")
        else:
            st.warning("N/A")

show_noaa(c1, "AO (Vrtlog)", ao)
show_noaa(c2, "NAO (Blokada)", nao)
show_noaa(c3, "PNA (Pacifik)", pna)

st.markdown("---")

# --- RED 2: RSI MATRICA (Cijena) ---
st.markdown("### 🎯 Price & RSI Matrix")

if rsi_data:
    # Trenutna cijena velika
    st.metric("Trenutna Cijena (Futures)", f"${rsi_data.get('price', 0):.3f}")
    
    # Tablica RSI-a
    cols = st.columns(3)
    
    # Funkcija za bojanje RSI-a
    def rsi_card(col, tf, val):
        state = "NEUTRAL"
        color = "off"
        if val > 70: 
            state = "OVERBOUGHT"
            color = "inverse" # Crveno
        elif val < 30: 
            state = "OVERSOLD"
            color = "normal" # Zeleno
        
        with col:
            st.metric(f"RSI ({tf})", f"{val:.1f}", delta=state, delta_color=color)
    
    rsi_card(cols[0], "2 MIN (Scalp)", rsi_data.get('2m', 50))
    rsi_card(cols[1], "1 H (Swing)", rsi_data.get('1h', 50))
    rsi_card(cols[2], "4 H (Trend)", rsi_data.get('4h', 50))
else:
    st.error("⚠️ Greška pri dohvatu burzovnih podataka.")

st.markdown("---")

# --- RED 3: FUNDAMENTALS (Production & Supply) ---
st.markdown("### 🏭 Fundamentals (Daily Estimates)")

# NAPOMENA: Ovo su placeholderi jer besplatni API ne daje te podatke
f1, f2, f3, f4 = st.columns(4)

with f1:
    st.metric("Dry Gas Production", "N/A", delta="Premium Data Only", delta_color="off")
    st.caption("Traži Bloomberg/WoodMac feed")

with f2:
    st.metric("LNG Exports", "N/A", delta="Premium Data Only", delta_color="off")
    st.caption("Praćenje feedgasa na terminalima")

with f3:
    st.metric("Total Supply", "N/A", delta="Premium Data Only", delta_color="off")
    
with f4:
    st.metric("Total Demand", "N/A", delta="Premium Data Only", delta_color="off")

st.markdown("---")

# --- RED 4: EIA STORAGE (Zalihe) ---
st.markdown("### 🛢️ EIA Storage (Weekly)")
if eia:
    e1, e2 = st.columns(2)
    with e1:
        st.metric("Ukupne Zalihe", f"{eia['current']} Bcf", f"{eia['change']} Bcf (Promjena)", delta_color="inverse")
        st.caption(f"📅 Datum izvještaja: {eia['date']}")
    with e2:
        val_diff = eia['diff_5y']
        lbl = "Višak vs 5y Avg" if val_diff > 0 else "Manjak vs 5y Avg"
        col = "inverse" # Crveno ako je višak
        st.metric("5-Year Average", f"{eia['avg_5y']} Bcf", f"{val_diff:+} Bcf", delta_color=col)
