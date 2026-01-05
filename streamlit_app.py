import streamlit as st
import pandas as pd
import requests
import io
import yfinance as yf
import pandas_ta as ta
import datetime

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Data Desk", layout="wide", page_icon="⚡")

st.title("⚡ NatGas Data Desk (Numeric Only)")

# ==============================================================================
# 🔑 API KLJUČEVI
# ==============================================================================
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
# ==============================================================================

# --- 1. NAPREDNA LOGIKA ZA VRIJEME (NOAA) ---
def interpret_noaa(index_name, val):
    """Vraća tekstualno objašnjenje i jačinu signala."""
    val = float(val)
    status = "NEUTRALNO"
    color = "off"
    desc = ""
    
    # --- AO (ARCTIC OSCILLATION) ---
    if index_name == "AO":
        # AO Pozitivan = Hladnoća zaključana na polu (Toplo u US) -> Bearish
        # AO Negativan = Hladnoća se izlijeva (Hladno u US) -> Bullish
        if val > 2.5:
            status = "EKSTREMNO BEARISH"
            desc = "Polarni vrtlog super-stabilan. Zima otkazana."
            color = "inverse" # Crveno
        elif val > 0.5:
            status = "BEARISH (Toplo)"
            desc = "Hladnoća se drži sjevera."
            color = "inverse"
        elif val < -2.5:
            status = "EKSTREMNO BULLISH"
            desc = "Raspad polarnog vrtloga! Arktički udar."
            color = "normal" # Zeleno
        elif val < -0.5:
            status = "BULLISH (Hladno)"
            desc = "Vrtlog nestabilan, hladnoća curi."
            color = "normal"
        else:
            status = "NEUTRALNO"
            desc = "Nema jasnog trenda."

    # --- NAO (NORTH ATLANTIC) ---
    elif index_name == "NAO":
        # NAO Pozitivan = Zonalni vjetrovi jaki (Toplo Istok US) -> Bearish
        # NAO Negativan = Blokada na Grenlandu (Hladno Istok US) -> Bullish
        if val > 1.5:
            status = "JAKO BEARISH"
            desc = "Atlantik otvoren. Topli zrak juriša na SAD."
            color = "inverse"
        elif val > 0.5:
            status = "BEARISH"
            desc = "Nema blokade."
            color = "inverse"
        elif val < -1.5:
            status = "JAKO BULLISH"
            desc = "Grenlandska blokada! Hladnoća zarobljena na istoku."
            color = "normal"
        elif val < -0.5:
            status = "BULLISH"
            desc = "Slabi zonalni vjetrovi."
            color = "normal"
        else:
            status = "NEUTRALNO"
            desc = "Nema jasnog signala."

    # --- PNA (PACIFIC NORTH AMERICAN) ---
    elif index_name == "PNA":
        # PNA Pozitivan = Greben na Zapadu, Korito na Istoku (Hladno) -> Bullish
        # PNA Negativan = Zonalni tok (Toplo) -> Bearish
        if val > 1.5:
            status = "JAKO BULLISH"
            desc = "Masivan greben na zapadu gura hladnoću na istok."
            color = "normal"
        elif val > 0.5:
            status = "BULLISH"
            desc = "Povoljan uzorak za hladnoću."
            color = "normal"
        elif val < -1.5:
            status = "JAKO BEARISH"
            desc = "Pacifički mlaz ubija hladnoću."
            color = "inverse"
        elif val < -0.5:
            status = "BEARISH"
            desc = "Nepovoljan uzorak."
            color = "inverse"
        else:
            status = "NEUTRALNO"
            desc = "Miješani signali."

    return {"val": val, "status": status, "desc": desc, "color": color}

def get_noaa_index(url, name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        latest = df.iloc[-1]
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        return interpret_noaa(name, latest[val_col])
    except:
        return None

# --- 2. NAPREDNA LOGIKA ZA ZALIHE (EIA 5Y AVG) ---
def get_eia_analysis(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        # Povlačimo 300 tjedana (cca 6 godina) da izračunamo 5-year average
        params = {
            "api_key": api_key, "frequency": "weekly", "data[0]": "value",
            "facets[series][]": "NW2_EPG0_SWO_R48_BCF", 
            "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 300
        }
        r = requests.get(url, params=params, timeout=8)
        data = r.json()
        
        if 'response' not in data: return None
        
        df = pd.DataFrame(data['response']['data'])
        df['period'] = pd.to_datetime(df['period'])
        df['value'] = df['value'].astype(int)
        df['week_of_year'] = df['period'].dt.isocalendar().week
        
        # 1. Trenutni podaci
        current = df.iloc[0]
        current_val = current['value']
        current_week_num = current['week_of_year']
        
        # 2. Promjena (Current vs Last Week)
        last_week = df.iloc[1]
        change = current_val - last_week['value']
        
        # 3. Izračun 5-Year Average za OVAJ tjedan
        # Filtriramo povijesne podatke za isti broj tjedna u godini (isključujući ovu godinu)
        # Uzimamo redove od indexa 52 (godinu dana unatrag) pa na dalje
        history = df.iloc[52:] 
        same_weeks = history[history['week_of_year'] == current_week_num]
        
        # Uzmi zadnjih 5 godina (top 5 rezultata)
        last_5_years = same_weeks.head(5)
        
        if not last_5_years.empty:
            avg_5y = int(last_5_years['value'].mean())
            diff_5y = current_val - avg_5y
            pct_5y = (diff_5y / avg_5y) * 100
        else:
            avg_5y = 0
            diff_5y = 0
            pct_5y = 0

        return {
            "date": current['period'].strftime("%d.%m.%Y"),
            "current": current_val,
            "change": change,
            "avg_5y": avg_5y,
            "diff_5y": diff_5y,
            "pct_5y": pct_5y
        }
    except Exception as e:
        st.error(f"EIA Error: {e}")
        return None

# --- 3. LOGIKA ZA CIJENU (SAMO BROJKE) ---
def get_simple_price():
    try:
        df = yf.download("NG=F", interval="1d", period="1mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Izračun RSI
        df['RSI'] = df.ta.rsi(length=14)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        price = latest['Close']
        change = price - prev['Close']
        pct_change = (change / prev['Close']) * 100
        rsi = latest['RSI']
        
        return {"price": price, "change": change, "pct": pct_change, "rsi": rsi}
    except:
        return None

# --- PRIKAZ PODATAKA ---

# URL-ovi
URL_AO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv"
URL_NAO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv"
URL_PNA = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv"

# Dohvat
ao = get_noaa_index(URL_AO, "AO")
nao = get_noaa_index(URL_NAO, "NAO")
pna = get_noaa_index(URL_PNA, "PNA")
eia = get_eia_analysis(EIA_API_KEY)
price = get_simple_price()

# === SEKCIJA 1: VRIJEME (NOAA) ===
st.markdown("### 📡 NOAA Weather Matrix")
c1, c2, c3 = st.columns(3)

def show_noaa_metric(col, title, data):
    with col:
        st.markdown(f"**{title}**")
        if data:
            st.metric("Vrijednost", f"{data['val']:.2f}", delta=data['status'], delta_color=data['color'])
            st.caption(f"📝 {data['desc']}")
        else:
            st.warning("Nema podataka")

show_noaa_metric(c1, "AO (Polar Vortex)", ao)
show_noaa_metric(c2, "NAO (Atlantic Block)", nao)
show_noaa_metric(c3, "PNA (Pacific Pattern)", pna)

st.markdown("---")

# === SEKCIJA 2: ZALIHE (EIA 5-YEAR ANALYSIS) ===
st.markdown("### 🛢️ EIA Storage Analysis")

if eia:
    k1, k2, k3 = st.columns(3)
    
    with k1:
        st.metric("Ukupne Zalihe", f"{eia['current']} Bcf", f"{eia['change']} Bcf (Promjena)", delta_color="inverse")
    
    with k2:
        # Prikaz odstupanja od 5-godišnjeg prosjeka
        # Ako je diff > 0 (Višak), to je Bearish (Crveno)
        # Ako je diff < 0 (Manjak), to je Bullish (Zeleno)
        lbl = "Višak vs 5y Avg" if eia['diff_5y'] > 0 else "Manjak vs 5y Avg"
        color = "inverse" 
        st.metric("5-Year Average", f"{eia['avg_5y']} Bcf", f"{eia['diff_5y']:+} Bcf ({eia['pct_5y']:.1f}%)", delta_color=color)
        
    with k3:
        st.info(f"📅 Podaci za tjedan: {eia['date']}")
        if eia['diff_5y'] > 100:
            st.error("⚠️ **JAKO BEARISH:** Ogroman višak plina u odnosu na prosjek!")
        elif eia['diff_5y'] < -100:
            st.success("✅ **JAKO BULLISH:** Veliki deficit zaliha!")
else:
    st.error("EIA podaci nisu dostupni.")

st.markdown("---")

# === SEKCIJA 3: CIJENA (NO CHARTS) ===
st.markdown("### 📈 Price & Momentum")

if price:
    m1, m2, m3 = st.columns(3)
    
    with m1:
        st.metric("Cijena (Futures)", f"${price['price']:.3f}", f"{price['pct']:.2f}%", delta_color="normal")
        
    with m2:
        # RSI Boje: >70 Crveno (Overbought), <30 Zeleno (Oversold)
        rsi_val = price['rsi']
        rsi_delta = "Neutral"
        rsi_color = "off"
        
        if rsi_val > 70: 
            rsi_delta = "OVERBOUGHT (Prodaj)"
            rsi_color = "inverse"
        elif rsi_val < 30: 
            rsi_delta = "OVERSOLD (Kupi)"
            rsi_color = "normal"
            
        st.metric("RSI (14-Day)", f"{rsi_val:.1f}", delta=rsi_delta, delta_color=rsi_color)
        
    with m3:
        st.caption("Podaci s burze (15min odgoda ili Live). Koristi RSI za tajming ulaza.")
else:
    st.warning("Burza nedostupna.")
