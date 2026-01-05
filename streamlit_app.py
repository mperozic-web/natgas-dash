import streamlit as st
import pandas as pd
import requests
import io

# --- KONFIGURACIJA STRANICE ---
st.set_page_config(page_title="NatGas Bot V2.1", layout="wide", page_icon="⚡")

st.title("⚡ NatGas Trading Desk (Beta)")
st.markdown("### Modul 1: Vrijeme & Modul 2: Zalihe")
st.markdown("---")

# ==============================================================================
# 🔑 TVOJ EIA API KLJUČ (Integriran)
# ==============================================================================
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"
# ==============================================================================

# --- FUNKCIJE ZA DOHVAT PODATAKA (ENGINE ROOM) ---

def get_noaa_data(url, name):
    """Dohvaća meteorološke indekse s maskiranjem (User-Agent) da izbjegnemo blokadu"""
    try:
        # Glumimo da smo običan preglednik
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Čitanje podataka
        data = pd.read_csv(io.StringIO(response.content.decode('utf-8')), sep='\s+', header=None, engine='python')
        
        if data.empty:
            return None
            
        # Uzimamo prosjek zadnjeg dana (zadnji red)
        latest_data = data.iloc[-1]
        return latest_data.mean()
        
    except Exception as e:
        # Tiha greška - vratit će None pa ćemo ispisati upozorenje u sučelju
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

# 1. SEKCIJA: VREMENSKI SEMAFOR (MODUL 1)
st.subheader("📡 Modul 1: Vremenski Signali (NOAA)")
col1, col2, col3 = st.columns(3)

AO_URL = "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/ao.sprd2.daily"
NAO_URL = "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/nao.sprd2.daily"
PNA_URL = "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/pna.sprd2.daily"

# --- AO ---
with col1:
    ao = get_noaa_data(AO_URL, "AO")
    if ao is not None:
        val_str = f"{ao:.2f}"
        # Logika: Pozitivan AO = Vrtlog jak = Hladnoća zaključana gore = BEARISH za US
        label = "Bearish (Toplo)" if ao > 0 else "Bullish (Hladno)"
        color = "inverse" # Crveno za Bearish, Zeleno za Bullish u Streamlitu
        st.metric("Arctic Oscillation (AO)", val_str, delta=label, delta_color=color)
    else:
        st.warning("AO: Nema podataka (NOAA server)")

# --- NAO ---
with col2:
    nao = get_noaa_data(NAO_URL, "NAO")
    if nao is not None:
        val_str = f"{nao:.2f}"
        # Logika: Pozitivan NAO = Nema bloka = Hladnoća bježi = BEARISH
        label = "Bearish (Otvoren)" if nao > 0 else "Bullish (Blokada)"
        color = "inverse"
        st.metric("North Atlantic (NAO)", val_str, delta=label, delta_color=color)
    else:
        st.warning("NAO: Nema podataka (NOAA server)")

# --- PNA ---
with col3:
    pna = get_noaa_data(PNA_URL, "PNA")
    if pna is not None:
        val_str = f"{pna:.2f}"
        # Logika: Pozitivan PNA = Hladno na Istoku = BULLISH
        label = "Bullish (Hladan Istok)" if pna > 0 else "Bearish (Topli Istok)"
        color = "normal" # Ovdje je pozitivno zeleno
        st.metric("Pacific North (PNA)", val_str, delta=label, delta_color=color)
    else:
        st.warning("PNA: Nema podataka (NOAA server)")

st.markdown("---")

# 2. SEKCIJA: ZALIHE PLINA (MODUL 2)
st.subheader("🛢️ Modul 2: Skladišta (EIA Report)")

eia_data = get_eia_storage(EIA_API_KEY)

if eia_data:
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(
            label=f"Ukupne Zalihe (Tjedan: {eia_data['date']})",
            value=f"{eia_data['value']} Bcf",
            delta=f"{eia_data['change']} Bcf (Promjena)",
            delta_color="inverse" # Crveno ako raste (loše), Zeleno ako pada (dobro)
        )
    with col_b:
        st.info("💡 **Tumačenje:** Ako je broj ispod crven (pozitivan), zalihe rastu -> Cijena pada. Ako je zelen (negativan), trošimo zalihe -> Cijena raste.")
else:
    st.error("⚠️ Greška s EIA podacima. Provjeri API ključ ili internet vezu.")

st.markdown("---")
st.caption("NatGas Bot V2.1 | Integrirani EIA API & NOAA Fix")
