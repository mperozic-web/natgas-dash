import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA STRANICE ---
st.set_page_config(page_title="NatGas Bot V2.3", layout="wide", page_icon="⚡")

st.title("⚡ NatGas Trading Desk (Live)")
st.markdown("### Modul 1: Vrijeme & Modul 2: Zalihe")
st.markdown("---")

# ==============================================================================
# 🔑 TVOJ EIA API KLJUČ
# ==============================================================================
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
# ==============================================================================

# --- NOVI LINKOV (VERIFICIRANI 2026) ---
# Ovi linkovi vode direktno na 'current' CSV datoteke
URL_AO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv"
URL_NAO = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv"
URL_PNA = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.pna.cdas.z500.19500101_current.csv"

# --- FUNKCIJE ZA DOHVAT ---

def get_noaa_index(url, col_name):
    """
    Dohvaća specifični indeks iz nove CSV strukture.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Dohvat podataka
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        
        # Čitanje CSV-a
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
        
        # Uzmi zadnji red (najnoviji datum)
        latest = df.iloc[-1]
        
        # Stupac s vrijednosti je obično zadnji, ali nekad ima specifično ime
        # Tražimo stupac koji NIJE year, month, day
        value_col = [c for c in df.columns if 'index' in c.lower() or 'ao' in c.lower() or 'nao' in c.lower() or 'pna' in c.lower()][0]
        
        return {
            "date": f"{int(latest['day'])}.{int(latest['month'])}.{int(latest['year'])}",
            "value": float(latest[value_col])
        }

    except Exception as e:
        # st.error(f"Greška kod {col_name}: {e}") # Otkomentiraj za debugiranje
        return None

def get_eia_storage(api_key):
    """Dohvat EIA zaliha"""
    url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
    params = {
        "api_key": api_key, "frequency": "weekly", "data[0]": "value",
        "facets[series][]": "NW2_EPG0_SWO_R48_BCF",
        "sort[0][column]": "period", "sort[0][direction]": "desc",
        "offset": 0, "length": 2
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if 'response' in data and 'data' in data['response']:
            recs = data['response']['data']
            return {
                "date": recs[0]['period'],
                "value": int(recs[0]['value']),
                "change": int(recs[0]['value']) - int(recs[1]['value'])
            }
        return None
    except:
        return None

# --- DASHBOARD ---

# Dohvat podataka (paralelno bi bilo bolje, ali ovo je dovoljno brzo)
data_ao = get_noaa_index(URL_AO, "AO")
data_nao = get_noaa_index(URL_NAO, "NAO")
data_pna = get_noaa_index(URL_PNA, "PNA")
eia_data = get_eia_storage(EIA_API_KEY)

# 1. SEKCIJA: VREMENSKI SEMAFOR
st.subheader("📡 Modul 1: Vremenski Signali (NOAA Live)")
c1, c2, c3 = st.columns(3)

# AO
with c1:
    if data_ao:
        val = data_ao['value']
        # AO > 0 -> Toplo (Bearish), AO < 0 -> Hladno (Bullish)
        lbl = "Bearish (Toplo)" if val > 0 else "Bullish (Hladno)"
        col = "inverse" # Streamlit inverse: Crveno za pozitivno, Zeleno za negativno
        st.metric("Arctic Oscillation (AO)", f"{val:.2f}", delta=lbl, delta_color=col)
        st.caption(f"📅 {data_ao['date']}")
    else:
        st.warning("AO Učitavanje...")

# NAO
with c2:
    if data_nao:
        val = data_nao['value']
        # NAO > 0 -> Nema bloka (Bearish)
        lbl = "Bearish (Otvoren)" if val > 0 else "Bullish (Blokada)"
        col = "inverse"
        st.metric("North Atlantic (NAO)", f"{val:.2f}", delta=lbl, delta_color=col)
        st.caption(f"📅 {data_nao['date']}")
    else:
        st.warning("NAO Učitavanje...")

# PNA
with c3:
    if data_pna:
        val = data_pna['value']
        # PNA > 0 -> Hladno Istok (Bullish)
        lbl = "Bullish (Hladan Istok)" if val > 0 else "Bearish (Topli Istok)"
        col = "normal" # Normal: Zeleno za pozitivno
        st.metric("Pacific North (PNA)", f"{val:.2f}", delta=lbl, delta_color=col)
        st.caption(f"📅 {data_pna['date']}")
    else:
        st.warning("PNA Učitavanje...")

st.markdown("---")

# 2. SEKCIJA: ZALIHE
st.subheader("🛢️ Modul 2: Skladišta (EIA Report)")

if eia_data:
    ca, cb = st.columns(2)
    with ca:
        st.metric(
            f"Ukupne Zalihe ({eia_data['date']})",
            f"{eia_data['value']} Bcf",
            f"{eia_data['change']} Bcf (Promjena)",
            delta_color="inverse"
        )
    with cb:
        st.info("💡 **Legenda:**\n* **Crveno:** Zalihe rastu ili je pretoplo (Bearish)\n* **Zeleno:** Zalihe padaju ili je hladno (Bullish)")
else:
    st.error("⚠️ Greška s EIA podacima.")

st.markdown("---")
st.caption("NatGas Bot V2.3 | Live NOAA & EIA Data")
