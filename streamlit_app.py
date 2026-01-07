import streamlit as st
import pandas as pd
import requests
import io
import zipfile

# --- KONFIGURACIJA ---
st.set_page_config(page_title="NatGas Sniper V7.0", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; text-transform: uppercase; }
    .stAlert { padding: 0.3rem !important; border-radius: 8px; }
    h3 { font-size: 0.95rem !important; color: #31333F; margin-bottom: 0.4rem; border-bottom: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

# --- 1. AUTOMATSKI COT DOHVAT (CFTC) ---
def get_automated_cot():
    try:
        # CFTC URL za tekuću 2026. godinu
        url = "https://www.cftc.gov/sites/default/files/files/dea/history/deafut2026.zip"
        r = requests.get(url, timeout=15)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            # Tražimo CSV datoteku unutar zip-a
            csv_name = z.namelist()[0]
            with z.open(csv_name) as f:
                df = pd.read_csv(f, low_memory=False)
        
        # Filtriranje za Natural Gas (NYMEX)
        ticker = "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE"
        ng_data = df[df['Market_and_Exchange_Names'].str.contains(ticker, na=False, case=False)].iloc[0]
        
        # Managed Money (Smart Money)
        mm_long = int(ng_data['M_Money_Positions_Long_All'])
        mm_short = int(ng_data['M_Money_Positions_Short_All'])
        mm_net = mm_long - mm_short
        
        # Non-Reportable (Retail)
        ret_long = int(ng_data['NonRept_Positions_Long_All'])
        ret_short = int(ng_data['NonRept_Positions_Short_All'])
        ret_net = ret_long - ret_short
        
        return {"mm_net": mm_net, "ret_net": ret_net, "date": ng_data['Report_Date_as_MM_DD_YYYY']}
    except Exception as e:
        return None

# --- 2. NOAA INDEKSI ---
def get_noaa_indices(url, name):
    try:
        r = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        lt = df.iloc[-1]
        val_col = [c for c in df.columns if any(x in c.lower() for x in ['index', 'ao', 'nao', 'pna'])][0]
        val = float(lt[val_col])
        
        status, color, bias = "NEUTRAL", "off", "Neutral"
        if name == "AO":
            if val < -2.0: status, color, bias = "EKSTREMNO BULL", "normal", "Long"
            elif val < -0.7: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 2.0: status, color, bias = "EKSTREMNO BEAR", "inverse", "Short"
            elif val > 0.7: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "NAO":
            if val < -0.7: status, color, bias = "BULLISH", "normal", "Long"
            elif val > 0.7: status, color, bias = "BEARISH", "inverse", "Short"
        elif name == "PNA":
            if val > 0.7: status, color, bias = "BULLISH", "normal", "Long"
            elif val < -0.7: status, color, bias = "BEARISH", "inverse", "Short"
            
        return {"val": val, "status": status, "color": color, "bias": bias}
    except: return None

# --- 3. EIA PODACI ---
def get_eia_data(api_key):
    data = {"storage": None, "balance": None}
    try:
        # Storage
        url_s = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
        params_s = {"api_key": api_key, "frequency": "weekly", "data[0]": "value", "facets[series][]": "NW2_EPG0_SWO_R48_BCF", "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 250}
        r_s = requests.get(url_s, params=params_s, timeout=10).json()
        df_s = pd.DataFrame(r_s['response']['data'])
        df_s['val'] = df_s['value'].astype(int)
        df_s['week'] = pd.to_datetime(df_s['period']).dt.isocalendar().week
        curr = df_s.iloc[0]
        avg_5y = int(df_s.iloc[52:][df_s.iloc[52:]['week'] == curr['week']].head(5)['val'].mean())
        data["storage"] = {"val": curr['val'], "chg": curr['val'] - df_s.iloc[1]['val'], "diff": curr['val'] - avg_5y, "date": pd.to_datetime(curr['period']).strftime("%d.%m.%Y")}
        
        # Balance (Macro)
        url_b = "https://api.eia.gov/v2/natural-gas/sum/lsum/data/"
        params_b = {"api_key": api_key, "frequency": "monthly", "data[0]": "value", "facets[series][]": ["N9010US2", "N9070US2"], "sort[0][column]": "period", "sort[0][direction] : desc", "length": 4}
        r_b = requests.get(url_b, params=params_b, timeout=10).json()
        df_b = pd.DataFrame(r_b['response']['data'])
        p_val = df_b[df_b['series'] == "N9010US2"].iloc[0]['value'] / 30
        c_val = df_b[df_b['series'] == "N9070US2"].iloc[0]['value'] / 30
        data["balance"] = {"prod": p_val, "cons": c_val, "net": p_val - c_val}
    except: pass
    return data

# --- IZVRŠAVANJE ---
ao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv", "AO")
nao = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv", "NAO")
pna = get_noaa_indices("https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv", "PNA")
eia = get_eia_data(EIA_API_KEY)
cot = get_automated_cot()

# --- UI DISPLAY ---
st.title("🛡️ Institutional Sniper Mirror V7.0")

# 1. PREMIUM TREND INPUT (Side-by-side)
with st.container():
    c1, c2 = st.columns(2)
    with c1:
        st.caption("💎 CELSIUS TREND (15d GWDD)")
        g1, g2 = st.columns(2)
        g_today = g1.number_input("Danas:", value=0.0, step=0.1)
        g_yest = g2.number_input("Jučer:", value=0.0, step=0.1)
        velocity = g_today - g_yest
    with c2:
        st.caption("🚀 TREND VELOCITY")
        v_label = "BULLISH (Toplina slabi)" if velocity > 0 else "BEARISH (Toplina jača)"
        st.metric("Odstupanje Trenda", f"{velocity:+.1f}", v_label, delta_color="normal" if velocity > 0 else "inverse")

st.markdown("---")

# 2. MASTER BIAS BAR
m1, m2, m3, m4 = st.columns(4)
m1.info(f"🌍 METEO: {'BULL' if (ao and ao['bias'] == 'Long') else 'BEAR'}")
m2.info(f"🛢️ STORAGE: {'BULL' if (eia['storage'] and eia['storage']['diff'] < 0) else 'BEAR'}")
m3.info(f"📈 TREND: {'BULL' if velocity > 0 else 'BEAR'}")
cot_b = "SQUEEZE RISK" if (cot and cot['mm_net'] < -140000) else "BEARISH" if (cot and cot['mm_net'] > 0) else "NEUTRAL"
m4.info(f"🏛️ COT: {cot_b}")

st.markdown("---")

# 3. NOAA KARTE
k1, k2 = st.columns(2)
k1.image("https://www.cpc.ncep.noaa.gov/products/predictions/610day/610temp.new.gif", use_container_width=True, caption="6-10 DANA")
k2.image("https://www.cpc.ncep.noaa.gov/products/predictions/814day/814temp.new.gif", use_container_width=True, caption="8-14 DANA")

# 4. INDEKSI I FUNDAMENTI
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("📡 NOAA Indeksi")
    idx = st.columns(3)
    if ao: idx[0].metric("AO", f"{ao['val']:.2f}", ao['status'], delta_color=ao['color'])
    if nao: idx[1].metric("NAO", f"{nao['val']:.2f}", nao['status'], delta_color=nao['color'])
    if pna: idx[2].metric("PNA", f"{pna['val']:.2f}", pna['status'], delta_color=pna['color'])

with col_b:
    st.subheader("🏭 Market Balance (Macro)")
    if eia['balance']:
        f1, f2, f3 = st.columns(3)
        f1.metric("Supply", f"{eia['balance']['prod']:.1f}")
        f2.metric("Demand", f"{eia['balance']['cons']:.1f}")
        net = eia['balance']['net']
        f3.metric("Net Flow", "SURPLUS" if net > 0 else "DEFICIT", f"{net:+.1f}", delta_color="inverse")

st.markdown("---")

# 5. COT I STORAGE
col_cot, col_sto = st.columns(2)
with col_cot:
    st.subheader("🏛️ Institutional COT (Managed Money)")
    if cot:
        c_net = cot['mm_net']
        st.metric("Net Pozicija (Managed Money)", f"{c_net:,}", f"Retail: {cot['ret_net']:,}")
        st.caption(f"📅 Datum izvještaja: {cot['date']}")
        if c_net < -150000:
            st.warning("⚠️ Managed Money je u ekstremnom shortu. Rizik od short squeezea je visok!")
    else: st.error("Dohvat COT podataka nije uspio.")

with col_sto:
    st.subheader("📦 Storage & 5y Avg")
    if eia['storage']:
        s1, s2 = st.columns(2)
        s1.metric("Inventory", f"{eia['storage']['val']} Bcf", f"{eia['storage']['chg']} Bcf")
        s2.metric("vs 5y Avg", f"{eia['storage']['diff']:+} Bcf", delta_color="inverse")

# 6. TRADING MIRROR
st.markdown("---")
st.subheader("🪞 Objektivni Mirror Zaključak")
score = 0
if eia['storage'] and eia['storage']['diff'] < 0: score += 1
if ao and ao['bias'] == "Long": score += 1
if velocity > 0: score += 1
if cot and cot['mm_net'] < -150000: score += 1

if score >= 4: st.success("🚀 ULTRA CONVICTION LONG: Sve karte su na tvojoj strani.")
elif score == 0: st.error("📉 ULTRA CONVICTION SHORT: Fundamenti su slomljeni, traži izlaz.")
else: st.warning("⚖️ DIVERGENCIJA: Signali nisu unificirani. Pažljivo sa scalpingom.")
