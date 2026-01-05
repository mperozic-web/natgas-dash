import streamlit as st
import pandas as pd
import requests
import io

st.set_page_config(page_title="NatGas Debug", layout="wide")
st.title("🛠️ DEBUG MODE")

# 1. TESTIRANJE PANDAS (Da vidimo radi li requirements.txt)
try:
    df_test = pd.DataFrame({'test': [1, 2, 3]})
    st.success("✅ Pandas biblioteka radi ispravno.")
except Exception as e:
    st.error(f"❌ PANDAS NE RADI! Jesi li kreirao requirements.txt? Greška: {e}")

# 2. TESTIRANJE NOAA VEZE (Sirovi ispis)
st.subheader("Testiranje NOAA veze...")
url = "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.nao.pna.aao.gdas.120days.csv"

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    st.write("1. Šaljem zahtjev prema NOAA...")
    response = requests.get(url, headers=headers, timeout=10)
    
    st.write(f"2. Status Kod: {response.status_code}") # 200 je dobro, 403 je zabranjeno
    
    if response.status_code == 200:
        st.success("✅ Veza uspješna! NOAA odgovara.")
        st.write("Prvih 5 redova podataka:")
        content = response.content.decode('utf-8')
        st.code(content[:500]) # Ispiši sirovi tekst
        
        # Test parsiranja
        df = pd.read_csv(io.StringIO(content))
        st.write("✅ Uspješno pretvoreno u tablicu.")
        st.dataframe(df.tail(3)) # Pokaži tablicu
    else:
        st.error(f"❌ NOAA je odbila vezu. Status: {response.status_code}")

except Exception as e:
    st.error(f"❌ KRITIČNA GREŠKA: {e}")

# 3. TVOJ EIA KLJUČ (Da ne izgubimo zalihe)
st.subheader("Testiranje EIA Zaliha...")
EIA_API_KEY = "UKanfPJLVukxpG4BTdDDSH4V4cVVtSNdk0JgEgai"

url_eia = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
params = {
    "api_key": EIA_API_KEY,
    "frequency": "weekly",
    "data[0]": "value",
    "facets[series][]": "NW2_EPG0_SWO_R48_BCF",
    "sort[0][column]": "period",
    "sort[0][direction]": "desc",
    "length": 1
}
try:
    r = requests.get(url_eia, params=params)
    if r.status_code == 200:
        st.success(f"✅ EIA radi! Zadnja zaliha: {r.json()['response']['data'][0]['value']} Bcf")
    else:
        st.error(f"❌ EIA greška: {r.status_code}")
except Exception as e:
    st.error(f"EIA Exception: {e}")
