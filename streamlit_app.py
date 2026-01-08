import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta
import pytz

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V69", layout="wide")

# CSS: Bez em-dasha, maksimalni kontrast
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.1rem; line-height: 1.6; color: #EEEEEE; border: 1px solid #444; padding: 20px; background-color: #0A0A0A; border-radius: 5px; }
    .bull-text { color: #00FF00 !important; font-weight: bold; }
    .bear-text { color: #FF4B4B !important; font-weight: bold; }
    .legend-box { padding: 8px; border: 1px solid #333; background: #111; font-size: 0.75rem; color: #BBB; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 800 !important; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- CORE LOGIKA ---
def get_ng_price():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()
        price = r['chart']['result'][0]['meta']['regularMarketPrice']
        prev = r['chart']['result'][0]['meta']['previousClose']
        return price, ((price - prev) / prev) * 100
    except: return 0.0, 0.0

def get_eia_storage_hardened():
    """Povlači isključivo Lower 48 ukupne zalihe"""
    try:
        # Dodan facet za 'R48' (Lower 48) kako ne bi vukao regije poput Pacifica
        url = f"https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&facets[location][]=R48&sort[0][column]=period&sort[0][direction]=desc&length=52"
        r = requests.get(url).json()['response']['data']
        curr = int(r[0]['value'])
        prev = int(r[1]['value'])
        # 5y Average (iz zadnja 52 tjedna)
        avg5y = sum(int(x['value']) for x in r) / len(r)
        return {"curr": curr, "chg": curr - prev, "v5y": curr - int(avg5y)}
    except: return None

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return df.iloc[-1, -1]
    except: return 0.0

def get_countdown():
    now = datetime.now(pytz.timezone('Europe/Zagreb'))
    days_to_fri = (4 - now.weekday()) % 7
    target = now.replace(hour=21, minute=30, second=0, microsecond=0) + timedelta(days=days_to_fri)
    if now > target: target += timedelta(days=7)
    diff = target - now
    return f"{diff.days}d {diff.seconds // 3600}h {(diff.seconds // 60) % 60}m"

# --- SIDEBAR: KONTROLA I COT ---
with st.sidebar:
    st.header("⚡ Sniper Hub")
    if st.button("🔄 OSVJEŽI RADAR"):
        st.cache_data.clear()
        st.rerun()
    
    price, pct = get_ng_price()
    st.metric("Henry Hub Live", f"${price:.3f}", f"{pct:+.2f}%")
    
    st.markdown("---")
    with st.form("cot_master_form"):
        st.subheader("🏛️ COT Full Entry")
        st.write(f"**Next Release:** {get_countdown()}")
        c1, c2 = st.columns(2)
        mm_l = c1.number_input("MM Long", value=288456)
        mm_s = c2.number_input("MM Short", value=424123)
        com_l = c1.number_input("Comm Long", value=512000)
        com_s = c2.number_input("Comm Short", value=380000)
        ret_l = c1.number_input("Retail Long", value=54120)
        ret_s = c2.number_input("Retail Short", value=32100)
        st.form_submit_button("SINKRONIZIRAJ")

# --- DOHVAT PODATAKA ---
eia = get_eia_storage_hardened()
ao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- 1. EXECUTIVE SUMMARY ---
st.subheader("📋 Executive Strategic Summary")
mm_net = mm_l - mm_s
com_net = com_l - com_s
s_bias = "BULLISH" if (eia and eia['curr'] < eia['v5y'] + eia['v5y']*0.02) else "BEARISH" # Tolerancija 2%

st.markdown(f"""
<div class='summary-narrative'>
    Henry Hub trguje na <strong>${price:.3f}</strong>. MM Neto: <strong>{mm_net:+,}</strong> | Comm Neto: <strong>{com_net:+,}</strong>.<br>
    Zalihe (L48): <strong>{eia['curr'] if eia else 'N/A'} Bcf</strong>. Promjena: <strong>{eia['chg'] if eia else 'N/A':+} Bcf</strong>.<br>
    Status vs 5y Avg: <span class='{"bull-text" if eia and eia['curr'] < 3317 else "bear-text"}'>{eia['curr'] - 3317 if eia else 'N/A':+} Bcf</span>. 
    Atmosferski bias: {'Hladnije (BULL)' if ao < 0 else 'Toplije (BEAR)'}.
</div>
""", unsafe_allow_html=True)

# --- 2. NOAA MAPS ---
st.subheader("🌡️ Weather Radar")
t1, t2 = st.tabs(["TEMPERATURA", "PADALINE"])
with t1:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Forecast")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Forecast")
with t2:
    c1, c2 = st.columns(2)
    c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Precipitation")
    c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Precipitation")

# --- 3. INDEX SPAGHETTI (TRIPLE LAYOUT) ---
st.subheader("📈 Index Spaghetti Trends")

idx_c1, idx_c2, idx_c3 = st.columns(3)

def draw_spag(col, title, val, url, logic):
    with col:
        st.image(url)
        bias = "BULLISH" if (val < 0 if title != "PNA" else val > 0) else "BEARISH"
        st.markdown(f"**{title} Index: {val:.2f}** (<span class='{'bull-text' if bias == 'BULLISH' else 'bear-text'}'>{bias}</span>)", unsafe_allow_html=True)
        st.markdown(f"<div class='legend-box'>{logic}<br>Crna linija: Ispod 0 = Hladno (BULL)</div>", unsafe_allow_html=True)

draw_spag(idx_c1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", "Negativan AO = Hladni zrak ide na jug.")
draw_spag(idx_c2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", "Negativan NAO = Blokada Atlantika.")
draw_spag(idx_c3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", "Pozitivan PNA = Hladnoća na istoku SAD-a.")

# --- 4. EIA STORAGE (RE-CALIBRATED) ---
st.subheader("🛢️ EIA Storage Intelligence (Lower 48)")

if eia:
    f1, f2, f3 = st.columns(3)
    f1.metric("Storage (L48)", f"{eia['curr']} Bcf", f"{eia['chg']} Bcf", delta_color="inverse")
    # Koristimo korisnikove 5y avg podatke (3317 Bcf) za točnost
    f2.metric("vs 5y Average (3317)", f"{eia['curr'] - 3317:+} Bcf", delta_color="inverse")
    with f3:
        status = "BULLISH" if eia['curr'] < 3317 else "BEARISH"
        st.markdown(f"**Sentiment:** <h2 class='{'bull-text' if status == 'BULLISH' else 'bear-text'}'>{status}</h2>", unsafe_allow_html=True)
else:
    st.error("EIA Fail: Provjeri API ključ ili status servera.")
