import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timezone, timedelta

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V13", layout="wide")

# CSS za maksimalnu čitljivost i moderan UI
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 800; color: #1E1E1E; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #555; }
    .stAlert { padding: 0.6rem !important; border-radius: 10px; border: 1px solid #ddd; }
    h3 { font-size: 1.2rem !important; color: #000; margin-bottom: 0.8rem; border-left: 5px solid #3498db; padding-left: 10px; }
    .header-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. NOAA INTERPRETACIJA I GRADACIJA ---
def interpret_noaa(name, val):
    val = float(val)
    res = {"status": "NEUTRALNO", "color": "off", "desc": "", "bias": "Neutral"}
    if name == "AO":
        if val < -2.2: res = {"status": "EKSTREMNO BULLISH", "color": "normal", "desc": "Vrtlog razbijen. Arktička jezgra prodire u Midwest i Northeast.", "bias": "Strong Long"}
        elif val < -0.8: res = {"status": "JAKO BULLISH", "color": "normal", "desc": "Vrtlog nestabilan. Visoka potražnja za grijanjem.", "bias": "Long"}
        elif val > 1.5: res = {"status": "JAKO BEARISH", "color": "inverse", "desc": "Hladnoća zaključana na polu. Toplo na ključnim tržištima.", "bias": "Short"}
    elif name == "NAO":
        if val < -0.8: res = {"status": "BULLISH", "color": "normal", "desc": "Blokada iznad Grenlanda gura hladnoću na Istočnu obalu (Northeast).", "bias": "Long"}
        elif val > 0.8: res = {"status": "BEARISH", "color": "inverse", "desc": "Atlantik otvoren. Topli zrak preplavljuje SAD.", "bias": "Short"}
    elif name == "PNA":
        if val > 0.8: res = {"status": "BULLISH", "color": "normal", "desc": "Greben na zapadu spušta hladnoću u Midwest i Istok.", "bias": "Long"}
        elif val < -0.8: res = {"status": "BEARISH", "color": "inverse", "desc": "Pacifička toplina gura hladnoću van SAD-a.", "bias": "Short"}
    return res

def get_noaa_indices(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        val = float(df.iloc[-1][[c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]])
        interp = interpret_noaa(name, val)
        return {"val": val, **interp}
    except: return None

# --- 2. EIA AUTOMATIZACIJA ---
def get_eia_data(api_key):
    data = {"storage": None, "balance": None}
    try:
        # Storage
        u_s = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        p_s = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 250}
        df_s = pd.DataFrame(requests.get(u_s, params=p_s).json()['response']['data'])
        df_s['val'] = df_s['value'].astype(int)
        df_s['week'] = pd.to_datetime(df_s['period']).dt.isocalendar().week
        curr = df_s.iloc[0]
        avg_5y = int(df_s.iloc[52:][pd.to_datetime(df_s.iloc[52:]['period']).dt.isocalendar().week == pd.to_datetime(curr['period']).dt.isocalendar().week].head(5)['val'].mean())
        data["storage"] = {"val": curr['val'], "chg": curr['val'] - df_s.iloc[1]['val'], "diff": curr['val'] - avg_5y, "date": pd.to_datetime(curr['period']).strftime("%d.%m.%Y")}
        # Balance
        u_b = "https://api.eia.gov/v2/natural-gas/sum/lsum/data/"
        p_b = {"api_key": api_key, "frequency": "monthly", "data[0]": "value", "facets[series][]": ["N9010US2", "N9070US2"], "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 4}
        df_b = pd.DataFrame(requests.get(u_b, params=p_b).json()['response']['data'])
        p_v = df_b[df_b['series'] == "N9010US2"].iloc[0]['value'] / 30
        c_v = df_b[df_b['series'] == "N9070US2"].iloc[0]['value'] / 30
        data["balance"] = {"prod": p_v, "cons": c_v, "net": p_v - c_v}
    except: pass
    return data

# --- IZVRŠAVANJE ---
ao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
eia = get_eia_data(EIA_API_KEY)

# --- UI DISPLAY ---
st.title("🛡️ Regional Sniper Mirror V13.0")

# 1. TACTICAL HEADER (Contrast Fixed)
with st.container():
    now_utc = datetime.now(timezone.utc)
    run = "00z" if 0 <= now_utc.hour < 12 else "12z"
    st.markdown(f"""
    <div class="header-box">
        <h2 style='margin:0; color:#1E1E1E;'>Model Run: {run} | Date: {now_utc.strftime('%Y-%m-%d')}</h2>
        <p style='margin:0; color:#555;'>Fokus: Northeast & Midwest Regional Demand Drivers</p>
    </div>
    """, unsafe_allow_html=True)

# 2. NATIONAL WEATHER DEMAND (REGIONAL DRIVERS)
st.subheader("📊 Weather Demand Progression (0-360 FH)")
fh_steps = [0, 24, 72, 120, 168, 216, 240, 360]
demand_data = []
for fh in fh_steps:
    # Simulacija bazirana na AO/NAO stanju
    is_bull = (ao['val'] < -0.5) if ao else False
    dev = round((fh/100) * (3.5 if is_bull else -2.5), 2)
    bias = "BULL" if dev > 0.5 else "BEAR" if dev < -0.5 else "NEUT"
    color = "🟢" if bias == "BULL" else "🔴" if bias == "BEAR" else "⚪"
    
    # Regionalna logika: što je FH veći, to više gledamo Midwest/Northeast
    region = "Northeast" if fh in [120, 216] else "Midwest" if fh in [72, 240, 360] else "West"
    
    demand_data.append({
        "FH": f"+{fh}",
        "Valid Date": (datetime.now() + timedelta(hours=fh)).strftime("%Y-%m-%d"),
        "Bias": f"{color} {bias}",
        "Score": round(dev/5, 2),
        "Natl Dev": f"{dev:+.2f}DD",
        "Driver Region": region
    })
st.table(pd.DataFrame(demand_data))

st.markdown("---")

# 3. NOAA PROGRESIJA (6-10d vs 8-14d)
st.subheader("🗺️ Forecast Progression (Radar)")
m_col1, m_col2 = st.columns(2)
m_col1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="SHORT TERM (6-10 DANA)")
m_col2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="LONG TERM (8-14 DANA)")

st.markdown("---")

# 4. NOAA INDEKSI (Interpretacija + Gradacija)
st.subheader("📡 Meteo Intelligence")
idx_c1, idx_c2, idx_c3 = st.columns(3)
def draw_idx(col, name, d):
    with col:
        if d:
            st.metric(name, f"{d['val']:.2f}", d['status'], delta_color=d['color'])
            st.write(f"**Učinak:** {d['desc']}")
        else: st.error(f"{name} N/A")
draw_idx(idx_c1, "AO (Polar Vortex)", ao)
draw_idx(idx_c2, "NAO (Atlantic Block)", nao)
draw_idx(idx_c3, "PNA (Pacific Flow)", pna)

st.markdown("---")

# 5. EIA FUNDAMENTALS (Automated)
st.subheader("🏭 Market Fundamentals (EIA)")
f_col1, f_col2 = st.columns(2)
with f_col1:
    if eia['balance']:
        st.write("**Supply & Demand Balance**")
        f1, f2, f3 = st.columns(3)
        f1.metric("Proizvodnja", f"{eia['balance']['prod']:.1f}")
        f2.metric("Potrošnja", f"{eia['balance']['cons']:.1f}")
        net = eia['balance']['net']
        f3.metric("Net Flow", "SURPLUS" if net > 0 else "DEFICIT", f"{net:+.1f}", delta_color="inverse")
with f_col2:
    if eia['storage']:
        st.write("**Storage Mirror (vs 5y Average)**")
        s1, s2 = st.columns(2)
        s1.metric("Inventory", f"{eia['storage']['val']} Bcf", f"{eia['storage']['chg']} Bcf")
        s2.metric("vs 5y Avg", f"{eia['storage']['diff']:+} Bcf", delta_color="inverse")
