import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA STRANICE ---
st.set_page_config(page_title="NatGas Bot V2.2", layout="wide", page_icon="⚡")

st.title("⚡ NatGas Trading Desk (Live)")
st.markdown("### Modul 1: Vrijeme & Modul 2: Zalihe")
st.markdown("---")

# ==============================================================================
# 🔑 TVOJ EIA API KLJUČ
# ==============================================================================
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
# ==============================================================================

# --- FUNKCIJE ZA DOHVAT PODATAKA ---

def get_noaa_master_data():
    """
    Dohvaća NOVU 'Master' CSV datoteku s NOAA servera koja sadrži sve indekse.
    URL: https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.nao.pna.aao.gdas.120days.csv
    """
    # Novi stabilni link (FTP server dostupan preko HTTP-a)
    url = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.nao.pna.aao.gdas.120days.csv"
    
    try:
        # Ponekad NOAA traži User-Agent, pa ga dodajemo za svaki slučaj
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Učitaj CSV. Očekujemo kolone: year, month, day, ao, nao, pna, aao
        df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
        
        # Očisti imena kolona (ukloni razmake ako postoje)
        df.columns = df.columns.str.strip().str.lower()
        
        # Uzmi zadnji red (najnoviji podaci)
        latest = df.iloc[-1]
        
        return {
            "date": f"{int(latest['day'])}.{int(latest['month'])}.{int(latest['year'])}",
            "ao": latest['ao'],
            "nao": latest['nao'],
            "pna": latest['pna']
        }

    except Exception as e:
        st.error(f"Greška kod NOAA dohvata: {e}")
        return None

def get_eia_storage(api_key):
    """Dohvaća EIA zalihe plina (Lower 48)"""
    url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
    
    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": "NW2_EPG0_SWO_R48_BCF",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": 2
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

# Dohvati podatke
noaa_data = get_noaa_master_data()
eia_data = get_eia_storage(EIA_API_KEY)

# 1. SEKCIJA: VREMENSKI SEMAFOR
st.subheader("📡 Modul 1: Vremenski Signali (NOAA Live)")

if noaa_data:
    col1, col2, col3 = st.columns(3)
    
    # --- AO ---
    with col1:
        val = noaa_data['ao']
        # Pozitivan AO = Toplo u SAD (Bearish)
        label = "Bearish (Toplo)" if val > 0 else "Bullish (Hladno)"
        color = "inverse" # Crveno ako je Bearish
        st.metric("Arctic Oscillation (AO)", f"{val:.2f}", delta=label, delta_color=color)

    # --- NAO ---
    with col2:
        val = noaa_data['nao']
        # Pozitivan NAO = Nema blokade (Bearish)
        label = "Bearish (Otvoren)" if val > 0 else "Bullish (Blokada)"
        color = "inverse"
        st.metric("North Atlantic (NAO)", f"{val:.2f}", delta=label, delta_color=color)

    # --- PNA ---
    with col3:
        val = noaa_data['pna']
        # Pozitivan PNA = Hladnoća na Istoku (Bullish)
        label = "Bullish (Hladan Istok)" if val > 0 else "Bearish (Topli Istok)"
        color = "normal" # Zeleno ako je Bullish
        st.metric("Pacific North (PNA)", f"{val:.2f}", delta=label, delta_color=color)
    
    st.caption(f"Zadnje ažuriranje NOAA podataka: {noaa_data['date']}")
else:
    st.warning("⚠️ NOAA podaci nisu dostupni. Server se možda osvježava.")

st.markdown("---")

# 2. SEKCIJA: ZALIHE PLINA
st.subheader("🛢️ Modul 2: Skladišta (EIA Report)")

if eia_data:
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(
            label=f"Ukupne Zalihe ({eia_data['date']})",
            value=f"{eia_data['value']} Bcf",
            delta=f"{eia_data['change']} Bcf (Promjena)",
            delta_color="inverse"
        )
    with col_b:
        st.info("💡 **Tumačenje:** Pozitivna promjena = Rast zaliha (Bearish). Negativna = Povlačenje (Bullish).")
else:
    st.error("⚠️ Greška s EIA podacima.")

st.markdown("---")
st.caption("NatGas Bot V2.2 | New Source: NOAA FTP Master File")
