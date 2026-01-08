import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta
import pytz

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V74", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; border-bottom: 1px solid #333; }
    .summary-narrative { font-size: 1.15rem; line-height: 1.8; color: #EEEEEE; border: 2px solid #008CFF; padding: 30px; background-color: #0A0A0A; border-radius: 10px; margin-bottom: 25px; }
    .bull-text { color: #00FF00 !important; font-weight: bold; }
    .ext-bull { color: #00FF00 !important; font-weight: 900; text-decoration: underline; }
    .bear-text { color: #FF4B4B !important; font-weight: bold; }
    .ext-bear { color: #FF4B4B !important; font-weight: 900; text-decoration: underline; }
    .legend-box { padding: 15px; border: 1px solid #333; background: #111; font-size: 0.85rem; color: #CCC; line-height: 1.5; border-radius: 5px; }
    .broker-box { padding: 15px; background: #1A1A1A; border: 1px solid #333; border-radius: 5px; text-align: center; }
    .external-link { display: block; padding: 12px; margin-bottom: 10px; background: #002B50; color: #008CFF; text-decoration: none; border-radius: 4px; font-weight: bold; text-align: center; border: 1px solid #004080; font-size: 0.9rem; }
    section[data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- DATA ENGINES ---
def get_ng_price():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/NG=F", headers=HEADERS).json()
        price = r['chart']['result'][0]['meta']['regularMarketPrice']
        prev = r['chart']['result'][0]['meta']['previousClose']
        return price, ((price - prev) / prev) * 100
    except: return 0.0, 0.0

def get_noaa_full(url):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        now = df.iloc[-1, -1]
        yesterday = df.iloc[-2, -1]
        last_week = df.iloc[-7, -1]
        return {"now": now, "d_chg": now - yesterday, "w_chg": now - last_week}
    except: return {"now": 0.0, "d_chg": 0.0, "w_chg": 0.0}

def get_countdown(day_idx, hour, minute):
    now = datetime.now(pytz.timezone('Europe/Zagreb'))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=(day_idx - now.weekday()) % 7)
    if now > target: target += timedelta(days=7)
    diff = target - now
    return f"{diff.days}d {diff.seconds // 3600}h {(diff.seconds // 60) % 60}m"

# --- SIDEBAR LIJEVO: UNOSI ---
with st.sidebar:
    st.header("⚡ Sniper Hub Inputs")
    price, pct = get_ng_price()
    st.metric("Henry Hub Live", f"${price:.3f}", f"{pct:+.2f}%")
    
    with st.form("master_input_v74"):
        st.subheader("🏛️ COT Sektori")
        c1, c2 = st.columns(2)
        mm_l = c1.number_input("MM Long", value=288456)
        mm_s = c2.number_input("MM Short", value=424123)
        com_l = c1.number_input("Comm Long", value=512000)
        com_s = c2.number_input("Comm Short", value=380000)
        ret_l = c1.number_input("Retail Long", value=54120)
        ret_s = c2.number_input("Retail Short", value=32100)
        st.markdown("---")
        st.subheader("🛢️ EIA Storage")
        eia_val = st.number_input("Current Bcf", value=3375)
        eia_chg = st.number_input("Weekly Chg", value=-38)
        eia_5y = st.number_input("5y Avg", value=3317)
        st.form_submit_button("SINKRONIZIRAJ")

# --- DATA FETCH ---
ao = get_noaa_full("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv")
nao = get_noaa_full("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv")
pna = get_noaa_full("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv")

# --- LOGIKA GRADACIJE ---
def get_bias_class(val, title):
    if title == "PNA":
        if val > 1.5: return "EXTREME BULLISH", "ext-bull"
        if val > 0: return "BULLISH", "bull-text"
        if val < -1.5: return "EXTREME BEARISH", "ext-bear"
        return "BEARISH", "bear-text"
    else:
        if val < -2.0: return "EXTREME BULLISH", "ext-bull"
        if val < 0: return "BULLISH", "bull-text"
        if val > 2.0: return "EXTREME BEARISH", "ext-bear"
        return "BEARISH", "bear-text"

# --- EXECUTIVE NARRATIVE ENGINE ---
col_main, col_right = st.columns([4, 1])

with col_main:
    st.subheader("📜 The Strategic Narrative")
    
    # Proračuni za priču
    mm_net = mm_l - mm_s
    com_net = com_l - com_s
    eia_diff = eia_val - eia_5y
    eia_pct = (eia_diff / eia_5y) * 100
    
    # Dinamička priča
    story_storage = f"Zalihe od {eia_val} Bcf pokazuju deficit od {abs(eia_diff)} Bcf u odnosu na petogodišnji prosjek" if eia_diff < 0 else f"Zalihe od {eia_val} Bcf bilježe suficit od {eia_diff} Bcf"
    story_weather = "polarni vrtlog puca i šalje arktičku hladnoću prema ključnim čvorištima" if ao['now'] < -1.0 else "atmosfera ostaje stabilna bez ekstremnih prijetnji potražnji"
    story_cot = "Managed Money je u defenzivi sa snažnom neto kratkom pozicijom" if mm_net < -100000 else "pozicioniranje velikih špekulanata je neutralno"
    
    st.markdown(f"""
    <div class='summary-narrative'>
        U trenutku dok promatramo Henry Hub na razini od <strong>${price:.3f}</strong>, tržište prirodnog plina piše složenu priču o asimetriji. 
        {story_storage}, što stvara fundamentalni pritisak koji trenutna cijena možda još nije u potpunosti apsorbirala. 
        Gledajući prema nebu, <strong>{story_weather}</strong> (AO: {ao['now']:.2f}, PNA: {pna['now']:.2f}), što u siječnju djeluje kao katalizator za agresivno pražnjenje rezervoara.<br><br>
        U pozadini, {story_cot}. Divergencija između Commercialsa ({com_net:+,}) i Managed Money sektora ({mm_net:+,}) sugerira da se 'pametni novac' pozicionira za otpor, dok bi špekulanti mogli biti prisiljeni na zatvaranje pozicija (Short Squeeze) ako se hladnoća materijalizira. 
        <strong>Verdikt:</strong> {'Sustav detektira visoku konvergenciju bika. Svi senzori (zalihe, vrijeme, COT) su sinkronizirani za rast.' if (eia_diff < 0 and ao['now'] < 0 and mm_net < 0) else 'Priča je još uvijek fragmentirana. Potreban je jači impuls AO indeksa ili veći tjedni withdrawal.'}
    </div>
    """, unsafe_allow_html=True)

    # Broker Execution Links
    b1, b2 = st.columns(2)
    b1.markdown('<div class="broker-box"><a href="https://www.plus500.com/" target="_blank" style="color:#00FF00;text-decoration:none;font-weight:bold;">EXECUTE ON PLUS 500</a></div>', unsafe_allow_html=True)
    b2.markdown('<div class="broker-box"><a href="https://capital.com/" target="_blank" style="color:#00FF00;text-decoration:none;font-weight:bold;">EXECUTE ON CAPITAL.COM</a></div>', unsafe_allow_html=True)

    # --- 2. NOAA MAPS ---
    st.subheader("🌡️ Weather Radar")
    t1, t2 = st.tabs(["TEMPERATURE", "PRECIPITATION"])
    with t1:
        c1, c2 = st.columns(2)
        c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", caption="6-10d Temp Forecast")
        c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", caption="8-14d Temp Forecast")
    with t2:
        c1, c2 = st.columns(2)
        c1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610prcp.new.gif", caption="6-10d Precip Forecast")
        c2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814prcp.new.gif", caption="8-14d Precip Forecast")

    # --- 3. INDEX SPAGHETTI (TRIPLE WITH TRENDS) ---
    st.subheader("📈 Index Forecast Trends & Momentum")
    
    idx_cols = st.columns(3)
    
    indices = [
        ("AO", ao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.gif", 
         "<strong>Arktička Oscilacija:</strong> Negativna faza (<0) znači slabljenje jet streama, što omogućuje hladnom zraku s Arktika prodor u SAD. <strong>Ispod -2.0 = EXTREME BULLISH.</strong>"),
        ("NAO", nao, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.gif", 
         "<strong>Sjevernoatlantska Oscilacija:</strong> Negativna faza (<0) donosi 'blokadu' koja usmjerava hladnoću na istočnu obalu SAD-a. <strong>Ispod -1.5 = EXTREME BULLISH.</strong>"),
        ("PNA", pna, "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.gif", 
         "<strong>Pacifičko-Američki Obrazac:</strong> Pozitivna faza (>0) korelira s hladnim dolinama na istoku i grebenima na zapadu. <strong>Iznad 1.5 = EXTREME BULLISH.</strong>")
    ]

    for i, (name, data, img, legend) in enumerate(indices):
        with idx_cols[i]:
            st.image(img)
            label, css = get_bias_class(data['now'], name)
            st.markdown(f"**{name}: {data['now']:.2f}** | <span class='{css}'>{label}</span>", unsafe_allow_html=True)
            st.write(f"Dnevna promjena: {data['d_chg']:+.2f} | Tjedna: {data['w_chg']:+.2f}")
            st.markdown(f"<div class='legend-box'>{legend}</div>", unsafe_allow_html=True)

with col_right:
    st.subheader("🔗 Intelligence")
    st.markdown(f"""
    <a href="http://celsiusenergy.co/" target="_blank" class="external-link">CELSIUS ENERGY</a>
    <a href="https://ir.eia.gov/secure/ngs/ngs.html" target="_blank" class="external-link">EIA STORAGE REPORT</a>
    <a href="https://www.wxcharts.com/?region=usa&element=850temp_anom" target="_blank" class="external-link">WX CHARTS (ECMWF)</a>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.write("**Fundamental Timings:**")
    st.info(f"EIA: {get_countdown(3, 16, 30)}")
    st.info(f"COT: {get_countdown(4, 21, 30)}")
    
    st.subheader("🛢️ Storage Stats")
    st.metric("vs 5y Average", f"{eia_diff:+} Bcf", f"{eia_pct:+.2f}%", delta_color="inverse")
