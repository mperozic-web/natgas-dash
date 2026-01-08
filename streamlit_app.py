import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta
import pytz

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V73", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.1rem; line-height: 1.6; color: #EEEEEE; border: 2px solid #008CFF; padding: 25px; background-color: #0A0A0A; border-radius: 8px; }
    .bull-text { color: #00FF00 !important; font-weight: bold; }
    .bear-text { color: #FF4B4B !important; font-weight: bold; }
    .legend-box { padding: 12px; border: 1px solid #333; background: #111; font-size: 0.8rem; color: #CCC; line-height: 1.4; }
    .broker-box { padding: 15px; background: #1A1A1A; border: 1px solid #333; border-radius: 5px; text-align: center; margin-top: 10px; }
    .external-link { display: block; padding: 12px; margin-bottom: 10px; background: #002B50; color: #008CFF; text-decoration: none; border-radius: 4px; font-weight: bold; text-align: center; border: 1px solid #004080; }
    .external-link:hover { background: #004080; color: #FFFFFF; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- POMOĆNE FUNKCIJE ---
def get_ng_price():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()
        price = r['chart']['result'][0]['meta']['regularMarketPrice']
        prev = r['chart']['result'][0]['meta']['previousClose']
        return price, ((price - prev) / prev) * 100
    except: return 0.0, 0.0

def get_noaa_idx(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        return df.iloc[-1, -1]
    except: return 0.0

def get_countdown(day_idx, hour, minute):
    now = datetime.now(pytz.timezone('Europe/Zagreb'))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=(day_idx - now.weekday()) % 7)
    if now > target: target += timedelta(days=7)
    diff = target - now
    return f"{diff.days}d {diff.seconds // 3600}h {(diff.seconds // 60) % 60}m"

# --- SIDEBAR LIJEVO: KONTROLA ---
with st.sidebar:
    st.header("⚡ Sniper Inputs")
    price, pct = get_ng_price()
    st.metric("Henry Hub Live", f"${price:.3f}", f"{pct:+.2f}%")
    
    with st.form("master_input"):
        st.subheader("🏛️ COT Sektori")
        c1, c2 = st.columns(2)
        mm_l = c1.number_input("MM Long", value=288456)
        mm_s = c2.number_input("MM Short", value=424123)
        com_l = c1.number_input("Comm Long", value=512000)
        com_s = c2.number_input("Comm Short", value=380000)
        ret_l = c1.number_input("Retail Long", value=54120)
        ret_s = c2.number_input("Retail Short", value=32100)
        
        st.markdown("---")
        st.subheader("🛢️ EIA Manual")
        eia_val = st.number_input("Storage (Bcf)", value=3375)
        eia_chg = st.number_input("Net Chg (Bcf)", value=-38)
        eia_5y = st.number_input("5y Avg (Bcf)", value=3317)
        st.form_submit_button("SINKRONIZIRAJ")

# --- GLAVNI RASPORED (Layout s "Desnim Sidebarom") ---
col_main, col_right = st.columns([4, 1])

# --- DOHVAT PODATAKA ---
ao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_idx("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

mm_net = mm_l - mm_s
com_net = com_l - com_s
ret_net = ret_l - ret_s
eia_diff = eia_val - eia_5y
eia_pct = (eia_diff / eia_5y) * 100

with col_main:
    # --- 1. EXECUTIVE STRATEGIC NARRATIVE ---
    st.subheader("📋 Executive Strategic Narrative")
    s_color = "bull-text" if eia_diff < 0 else "bear-text"
    
    # Detaljnija deskripcija
    cot_bias = "Snažna asimetrija (MM Short / Comm Long)" if (mm_net < -100000 and com_net > 0) else "Neutralno pozicioniranje"
    weather_desc = "Ekstremna hladnoća u dolasku" if (ao < -1.0 and pna > 0.5) else "Umjereni ili topli uvjeti"
    
    st.markdown(f"""
    <div class='summary-narrative'>
        <strong>TRŽIŠNI STATUS:</strong> NG trguje na <strong>${price:.3f}</strong>. 
        Managed Money neto pozicija od <strong>{mm_net:+,}</strong> ukazuje na {cot_bias.lower()}.<br>
        <strong>FUNDAMENTALNI DEFICIT:</strong> Zalihe su na <strong>{eia_val} Bcf</strong>. 
        Odstupanje od 5y prosjeka iznosi <span class='{s_color}'><strong>{eia_diff:+} Bcf ({eia_pct:+.2f}%)</strong></span>. 
        Trenutna stopa povlačenja je <strong>{eia_chg:+} Bcf</strong>.<br>
        <strong>METEOROLOŠKI RADAR:</strong> Indeksi AO ({ao:.2f}) i PNA ({pna:.2f}) sugeriraju: <strong>{weather_desc}</strong>.<br>
        <strong>STRATEŠKI VERDIKT:</strong> {'Sustav detektira BULLISH konvergenciju: niske zalihe + hladni val + MM Short Squeeze rizik.' if (eia_diff < 0 and ao < 0 and mm_net < 0) else 'Čekati potvrdu AO/NAO indeksa prije ulaska u Long poziciju.'}
    </div>
    """, unsafe_allow_html=True)

    # BROKER LINKS BOX
    b1, b2 = st.columns(2)
    with b1:
        st.markdown('<div class="broker-box"><a href="https://www.plus500.com/" target="_blank" style="color:#008CFF;text-decoration:none;font-weight:bold;">PLUS 500 EXECUTION</a></div>', unsafe_allow_html=True)
    with b2:
        st.markdown('<div class="broker-box"><a href="https://capital.com/" target="_blank" style="color:#008CFF;text-decoration:none;font-weight:bold;">CAPITAL.COM EXECUTION</a></div>', unsafe_allow_html=True)

    # --- 2. NOAA MAPS ---
    st.subheader("🌡️ Weather Radar")
    t1, t2 = st.tabs(["TEMPERATURE", "PRECIPITATION"])
    with t1:
        c1, c2 = st.columns(2)
        c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Forecast")
        c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Forecast")
    with t2:
        c1, c2 = st.columns(2)
        c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Precipitation")
        c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d Precipitation")

    # --- 3. INDEX SPAGHETTI ---
    st.subheader("📈 Index Forecast Trends")
    
    idx_c1, idx_c2, idx_c3 = st.columns(3)

    def draw_spag(col, title, val, url, detailed_logic):
        with col:
            st.image(url)
            bias = "BULLISH" if (val < 0 if title != "PNA" else val > 0) else "BEARISH"
            st.markdown(f"**{title} Index: {val:.2f}** (<span class='{'bull-text' if bias == 'BULLISH' else 'bear-text'}'>{bias}</span>)", unsafe_allow_html=True)
            st.markdown(f"<div class='legend-box'>{detailed_logic}</div>", unsafe_allow_html=True)

    draw_spag(idx_c1, "AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", 
              "<strong>AO:</strong> Ispod 0 = Polarni vrtlog slabi, hladnoća 'curi' na jug (BULL). Iznad 0 = Bearish.")
    draw_spag(idx_c2, "NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", 
              "<strong>NAO:</strong> Ispod 0 = Atlantski blok usmjerava hladnoću na US East Coast (BULL). Iznad 0 = Bearish.")
    draw_spag(idx_c3, "PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", 
              "<strong>PNA:</strong> Iznad 0 = Hladna 'dolina' na istoku SAD-a (BULL). Ispod 0 = Bearish.")

# --- DESNI SIDEBAR (Simulacija preko kolone) ---
with col_right:
    st.subheader("🔗 Intelligence")
    
    st.markdown(f"""
    <a href="http://celsiusenergy.co/" target="_blank" class="external-link">CELSIUS ENERGY</a>
    <a href="https://ir.eia.gov/secure/ngs/ngs.html?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9pci5laWEuZ292L3NlY3VyZS9uZ3MvKiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc5ODc3OTU0MH0sIkRhdGVHcmVhdGVyVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzY3ODg2MjAwfX19XX0&Signature=bhfnMPQp~JATNQQyMiYqKsPKwCxl5gt30nOXBCE9KynqI7x924FQqfQlPFrqXfbq0oQvYCFuxlyP4r4ReBBl8dTLDj8hxsSLwy3qZAPbQqSokQscrWLW5WqlSLJ~bVyToj-a2Yqaecby239tW66Qq-zD4k1rMo8h0g-C2cy0WH~5x3nA8q6NgRxHn6I-3y7Jb5LxhGGSdY0gLEln2trAqNGoi2cHReKpxq6~03pL2Oqk8e9icyk5L2pZRN~PgpP98s~jwy8ApUdoTJcdHWN3pJS~waZ6tqW1GWyvJYI0UsrXwBau8AklK2VewEurEHqSfLXmk9sxpAF30ivRZpocZg&Key-Pair-Id=KMFHYU05NRCDK" target="_blank" class="external-link">EIA STORAGE REPORT</a>
    <a href="https://www.wxcharts.com/?dataset=ecmwf_op&region=usa&element=850temp_anom&run=12&dtg=2026-01-07T12%3A00%3A00Z&meteoModel=ecop&ensModel=eceps&chartRun=0&lat=46.44&lon=16.41" target="_blank" class="external-link">WX CHARTS (ECMWF)</a>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.write("**Next Timings:**")
    st.info(f"EIA: {get_countdown(3, 16, 30)}")
    st.info(f"COT: {get_countdown(4, 21, 30)}")
