import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta
import pytz

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V67", layout="wide")

# CSS: Visoki kontrast i eliminacija em-dasha
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.1rem; line-height: 1.6; color: #EEEEEE; border: 1px solid #444; padding: 20px; background-color: #0A0A0A; border-radius: 5px; }
    .bull-text { color: #00FF00 !important; font-weight: bold; }
    .bear-text { color: #FF4B4B !important; font-weight: bold; }
    .legend-box { padding: 10px; border: 1px solid #333; background: #111; font-size: 0.85rem; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- POMOĆNE FUNKCIJE ---
def get_ng_price():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()
        price = r['chart']['result'][0]['meta']['regularMarketPrice']
        prev = r['chart']['result'][0]['meta']['previousClose']
        change = ((price - prev) / prev) * 100
        return price, change
    except: return 0.0, 0.0

def get_eia_data():
    try:
        url = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=10"
        r = requests.get(url).json()['response']['data']
        curr = int(r[0]['value'])
        prev = int(r[1]['value'])
        avg5y = sum(int(x['value']) for x in r) / len(r)
        return {"curr": curr, "chg": curr - prev, "v5y": curr - int(avg5y)}
    except: return None

def get_noaa_index(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return df.iloc[-1, -1], df.iloc[-2, -1]
    except: return 0.0, 0.0

def get_cot_countdown():
    now = datetime.now(pytz.timezone('Europe/Zagreb'))
    # COT izlazi petkom u 21:30 CET
    days_to_friday = (4 - now.weekday()) % 7
    next_release = now.replace(hour=21, minute=30, second=0, microsecond=0) + timedelta(days=days_to_friday)
    if now > next_release:
        next_release += timedelta(days=7)
    diff = next_release - now
    return f"{diff.days}d {diff.seconds // 3600}h {(diff.seconds // 60) % 60}m"

# --- SIDEBAR: KONTROLA I CIJENA ---
with st.sidebar:
    st.header("⚡ Sniper Control")
    if st.button("🔄 OSVJEŽI PODATKE"):
        st.cache_data.clear()
        st.rerun()
    
    price, pct = get_ng_price()
    st.metric("Henry Hub Live", f"${price:.3f}", f"{pct:+.2f}%")
    
    st.markdown("---")
    st.subheader("🏛️ COT Ručni Unos")
    nc_l = st.number_input("Managed Money Long", value=288456)
    nc_s = st.number_input("Managed Money Short", value=424123)
    
    st.markdown(f"**Countdown do objave:**\n{get_cot_countdown()}")

# --- DOHVAT PODATAKA ---
eia = get_eia_data()
ao_now, ao_y = get_noaa_index("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao_now, nao_y = get_noaa_index("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna_now, pna_y = get_noaa_index("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE SUMMARY ---
st.subheader("📋 Executive Strategic Summary")
s_bias = "BULLISH" if (eia and eia['v5y'] < 0) else "BEARISH"
ao_bias = "BULLISH" if ao_now < 0 else "BEARISH"
cot_net = nc_l - nc_s

st.markdown(f"""
<div class='summary-narrative'>
    Tržište operira pri <strong>${price:.3f}</strong>. Managed Money neto pozicija iznosi <strong>{cot_net:+,}</strong>. 
    Zalihe su na <strong>{eia['curr'] if eia else 'N/A'} Bcf</strong>, što je 
    <span class='{"bull-text" if s_bias == "BULLISH" else "bear-text"}'>{eia['v5y'] if eia else 'N/A':+} Bcf</span> u odnosu na 5y prosjek. 
    AO Indeks je na <strong>{ao_now:.2f}</strong>, signalizirajući <span class='{"bull_text" if ao_bias == "BULLISH" else "bear_text"}'>{ao_bias}</span> 
    vremenski okvir za potražnju. Kombinirani podaci ukazuju na asimetriju u korist {'kupaca' if (ao_now < 0 and eia['v5y'] < 0) else 'prodavača'}.
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA MAPS (Tabs for toggling) ---
st.subheader("🌡️ NOAA Weather Forecast")
tab_temp, tab_precip = st.tabs(["TEMPERATURA", "PADALINE"])

with tab_temp:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="Short Term (6-10 Day)")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="Long Term (8-14 Day)")

with tab_precip:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="Short Term (6-10 Day)")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="Long Term (8-14 Day)")

# --- 3. INDEX SPAGHETTI SECTION ---
st.subheader("📈 Index Spaghetti Trends")



def show_index_module(title, val, trend_val, img_url, logic_text):
    col1, col2 = st.columns([2, 1])
    with col1:
        st.image(img_url)
    with col2:
        bias = "BULLISH" if (val < 0 if title != "PNA" else val > 0) else "BEARISH"
        st.markdown(f"### {title}: {val:.2f}")
        st.markdown(f"Status: <span class='{'bull-text' if bias == 'BULLISH' else 'bear-text'}'>{bias}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='legend-box'><strong>Legenda:</strong><br>{logic_text}<br><br><strong>Crna linija:</strong><br>Iznad 0 = Toplije (Medvjeđe)<br>Ispod 0 = Hladnije (Bikovski)</div>", unsafe_allow_html=True)

show_index_module("AO", ao_now, ao_y, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "AO negativan = Hladni zrak se spušta na jug.")
show_index_module("NAO", nao_now, nao_y, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "NAO negativan = Jači blokovi na Atlantiku.")
show_index_module("PNA", pna_now, pna_y, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "PNA pozitivan = Hladnoća na istoku SAD-a.")

# --- 4. FUNDAMENTALS: EIA STORAGE ---
st.subheader("🛢️ Fundamental Intelligence: EIA Storage")



if eia:
    f1, f2, f3 = st.columns(3)
    f1.metric("Trenutne Zalihe", f"{eia['curr']} Bcf", f"{eia['chg']} Bcf", delta_color="inverse")
    f2.metric("vs 5y Average", f"{eia['v5y']:+} Bcf", delta_color="inverse")
    
    with f3:
        status = "BULLISH" if eia['v5y'] < 0 else "BEARISH"
        st.markdown(f"**Market Sentiment:**")
        st.markdown(f"<h2 class='{'bull-text' if status == 'BULLISH' else 'bear-text'}'>{status}</h2>", unsafe_allow_html=True)
else:
    st.error("EIA podaci trenutno nedostupni.")
