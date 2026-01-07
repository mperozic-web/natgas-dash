import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta, timezone

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V18", layout="wide")

# CSS za maksimalnu preglednost i čiste linije
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 800; color: #007BFF !important; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #444; }
    .stMetric { background-color: #ffffff; padding: 12px; border-radius: 10px; border: 1px solid #e0e0e0; }
    h3 { font-size: 1.15rem !important; color: #000; border-left: 5px solid #007BFF; padding-left: 10px; margin-top: 20px; }
    .countdown-timer { background: #fef2f2; border: 1px solid #fee2e2; padding: 8px; border-radius: 8px; color: #991b1b; font-weight: bold; text-align: center; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. EIA STORAGE DOHVAT ---
@st.cache_data(ttl=3600)
def get_eia_storage_v18(api_key):
    try:
        url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params = {
            "api_key": api_key, "frequency": "weekly", "data[0]": "value",
            "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period",
            "sort[0][direction]": "desc", "length": 5
        }
        r = requests.get(url, params=params, timeout=10).json()
        df = pd.DataFrame(r['response']['data'])
        df['val'] = df['value'].astype(int)
        return {"curr": df.iloc[0]['val'], "chg": df.iloc[0]['val'] - df.iloc[1]['val'], "date": df.iloc[0]['period']}
    except: return None

# --- 2. COUNTDOWN DO EIA ---
def get_eia_countdown():
    now = datetime.now(timezone.utc)
    target = (now + timedelta(days=(3 - now.weekday()) % 7)).replace(hour=15, minute=30, second=0)
    if now >= target: target += timedelta(days=7)
    diff = target - now
    h, rem = divmod(int(diff.total_seconds()), 3600)
    m, _ = divmod(rem, 60)
    return f"{h}h {m}m"

# --- UI DISPLAY ---
st.title("🛡️ NatGas Sniper V18.0 | Visual Radar Mirror")

# 1. EIA & COT TOP BAR (Ono što se unosi ili je kritično)
st.subheader("🏁 Core Sentiment & Fundamentals")
col_c1, col_c2, col_c3 = st.columns([2, 1, 1])

with col_c1:
    with st.expander("🏛️ COT Manual Entry (Tradingster)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        nc_l = c1.number_input("Non-Comm Long:", value=288456)
        nc_s = c2.number_input("Non-Comm Short:", value=424123)
        mm_net = nc_l - nc_s
        st.markdown(f"**Managed Money Net:** `{mm_net:,}` | **Bias:** {'🔴 SQUEEZE RISK' if mm_net < -150000 else '⚪ NEUTRAL'}")

with col_c2:
    storage = get_eia_storage_v18(EIA_API_KEY)
    if storage:
        st.metric("Zalihe (Bcf)", f"{storage['curr']}", f"{storage['chg']} Bcf")
    else: st.error("EIA API Error")

with col_c3:
    st.markdown(f"<div class='countdown-timer'>EIA Countdown:<br>{get_eia_countdown()}</div>", unsafe_allow_html=True)

st.markdown("---")

# 2. TEMPERATURE PROGRESSION (Radar)
st.subheader("🗺️ Temperature Progression (6-10d vs 8-14d)")
t1, t2 = st.columns(2)
t1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", use_container_width=True)
t2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", use_container_width=True)

st.markdown("---")

# 3. PRECIPITATION & SNOW COVER (The Hidden Demand)
st.subheader("❄️ Oborine i Snježni Pokrivač (Northeast Demand Driver)")
p1, p2 = st.columns([1, 1.2])
with p1:
    st.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="Precipitation Outlook (8-14d)", use_container_width=True)
with p2:
    # NOAA National Snow Analysis
    st.image("https://www.natice.noaa.gov/pub/ims/ims_gif/DATA/cursnow.gif", caption="Aktualni Snježni Pokrivač (SAD)", use_container_width=True)

st.markdown("---")

# 4. ATMOSPHERIC DRIVERS (Spaghetti Forecast Trends)
st.subheader("📈 Atmospheric Trends (Kamo idu indeksi?)")
v1, v2, v3 = st.columns(3)
with v1:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", caption="AO Index Forecast")
with v2:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", caption="NAO Index Forecast")
with v3:
    st.image("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", caption="PNA Index Forecast")

st.markdown("---")

# 5. OBJEKTIVNA INTERPRETACIJA
st.subheader("🪞 Trading Mirror Interpretacija")
st.info("""
**Kako čitati radar:**
1. **AO Spaghetti:** Ako linije padaju ispod -1.0, hladnoća se spušta s Arktika.
2. **NAO Spaghetti:** Ako linije idu u minus, imamo blokadu na Atlantiku (Northeast zahladi).
3. **Snow Map:** Što je više bijele boje u Northeast i Midwest regijama, to je veća baza potražnje.
4. **COT:** Ako je MM Net u dubokom minusu, a AO/NAO padaju, spremi se za 'Long' eksploziju.
""")
