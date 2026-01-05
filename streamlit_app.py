import streamlit as st
import pandas as pd
import requests
import io
import datetime

# --- KONFIGURACIJA STRANICE ---
st.set_page_config(page_title="NatGas Bot V2", layout="wide", page_icon="⚡")

st.title("⚡ NatGas Trading Desk (Alpha 2.0)")
st.markdown("### Modul 1: Vrijeme & Modul 2: Zalihe")
st.markdown("---")

# ==============================================================================
# 🔑 SIGURNOSNA ZONA - TVOJ KLJUČ
# ==============================================================================
# OVDJE ZALIJEPI SVOJ KLJUČ IZMEĐU NAVODNIKA:
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai" 
# ==============================================================================

# --- FUNKCIJE ZA DOHVAT PODATAKA (ENGINE ROOM) ---

def get_noaa_data(url, name):
    """Dohvaća meteorološke indekse (AO, NAO, PNA)"""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = pd.read_csv(io.StringIO(response.content.decode('utf-8')), sep='\s+', header=None, engine='python')
        latest_data = data.iloc[-1]
        return latest_data.mean()
    except Exception as e:
        return None

def get_eia_storage(api_key):
    """Dohvaća EIA zalihe plina (Lower 48)"""
    # EIA API v2 Endpoint
    url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
    
    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": "NW2_EPG0_SWO_R48_BCF", # Serija za Lower 48 Storage
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": 2 # Uzimamo zadnja dva tjedna da izračunamo promjenu
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        
        if 'response' in data and 'data' in data['response']:
            records = data['response']['data']
            current_week = records[0]
            last_week = records[1]
            
            return {
                "date": current_week['period'],
                "value": int(current_week['value']),
                "change": int(current_week['value']) - int(last_week['value'])
            }
        else:
            return None
    except Exception as e:
        st.error(f"EIA Error: {e}")
        return None

# --- VIZUALIZACIJA (DASHBOARD) ---

# 1. SEKCIJA: VREMENSKI SEMAFOR (MODUL 1)
st.subheader("📡 Modul 1: Vremenski Signali (NOAA)")
col1, col2, col3 = st.columns(3)

# Linkovi
AO_URL = "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.daily"
NAO_URL = "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.daily"
PNA_URL = "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.daily"

with col1:
    ao = get_noaa_data(AO_URL, "AO")
    if ao:
        color = "off" if ao > 0 else "normal" # Pojednostavljeno za demo
        st.metric("Arctic Oscillation (AO)", f"{ao:.2f}", delta="Bearish (Toplo)" if ao > 0 else "Bullish (Hladno)", delta_color=color)

with col2:
    nao = get_noaa_data(NAO_URL, "NAO")
    if nao:
        color = "off" if nao > 0 else "normal"
        st.metric("North Atlantic (NAO)", f"{nao:.2f}", delta="Bearish (Otvoren)" if nao > 0 else "Bullish (Blokada)", delta_color=color)

with col3:
    pna = get_noaa_data(PNA_URL, "PNA")
    if pna:
        # PNA je pozitivan = Hladno na istoku (Bullish)
        st.metric("Pacific North American (PNA)", f"{pna:.2f}", delta="Bullish (Hladan Istok)" if pna > 0 else "Bearish (Topli Istok)")

st.markdown("---")

# 2. SEKCIJA: ZALIHE PLINA (MODUL 2)
st.subheader("🛢️ Modul 2: Skladišta (EIA Report)")

eia_data = get_eia_storage(EIA_API_KEY)

if eia_data:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.metric(
            label=f"Ukupne Zalihe (Datum: {eia_data['date']})",
            value=f"{eia_data['value']} Bcf",
            delta=f"{eia_data['change']} Bcf (Tjedna Promjena)",
            delta_color="inverse" # Crveno ako rastu zalihe (loše za cijenu), Zeleno ako padaju
        )
    
    with col_b:
        # Ovdje ćemo kasnije dodati usporedbu s 5-godišnjim prosjekom
        st.info("💡 **Tumačenje:** Ako je 'Tjedna Promjena' pozitivna, zalihe rastu (Bearish). Ako je negativna, trošimo plin (Bullish).")

else:
    st.warning("⚠️ Ne mogu dohvatiti EIA podatke. Provjeri je li API ključ ispravno zalijepljen!")

st.markdown("---")
st.caption("Powered by NOAA & EIA Open Data | NatGas Algo v2.0")
