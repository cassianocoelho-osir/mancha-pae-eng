import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Mapa de Mancha - Buffer 75m")
st.title("🔥 Mapa de Mancha (Buffer 75m)")

# URL exportando a aba específica da planilha (gid=1265583443)
URL_CSV = "https://docs.google.com/spreadsheets/d/1vmccPxvC4Z0rrfSyhF6HhehGSqpjY5oJboR-hG8O4bg/export?format=csv&gid=1265583443"

@st.cache_data(ttl=300)
def carregar_dados():
    # Lê a planilha mantendo cabeçalho original se houver, ou via índice
    df = pd.read_csv(URL_CSV, header=None)
    
    # Coluna 0 = Coluna A, Coluna 2 = Coluna C
    df_util = pd.DataFrame()
    df_util['coluna_a'] = df[0].fillna("").astype(str).str.strip()
    df_util['coordenada'] = df[2].astype(str).str.strip()
    
    # 1. Regra: Apenas linhas onde a Coluna A NÃO está vazia e não é cabeçalho
    df_util = df_util[df_util['coluna_a'] != ""]
    
    # 2. Limpeza das coordenadas na Coluna C
    df_util = df_util[~df_util['coordenada'].str.lower().str.contains('coordenada', na=False)]
    df_util = df_util[df_util['coordenada'].str.contains(',', na=False)]

    def extrair_lat_lon(txt):
        try:
            partes = str(txt).split(',')
            return float(partes[0].strip()), float(partes[1].strip())
        except:
            return None, None

    coords = df_util['coordenada'].apply(extrair_lat_lon)
    df_util['lat'] = [c[0] for c in coords]
    df_util['lon'] = [c[1] for c in coords]
    
    # Remove entradas sem coordenadas válidas
    df_util = df_util.dropna(subset=['lat', 'lon'])
    
    return df_util

try:
    df_mapa = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados da planilha: {e}")
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Opções do Mapa")

exibir_circulos = st.sidebar.checkbox("Exibir círculos de buffer (Raio 75m)", value=False)
raio_mancha = st.sidebar.slider("Intensidade/Tamanho Visual da Mancha:", min_value=10, max_value=60, value=25)
desfoco = st.sidebar.slider("Desfoco (Blur):", min_value=5, max_value=30, value=15)

# --- MONTAGEM DO MAPA ---
if not df_mapa.empty:
    centro_lat = df_mapa['lat'].mean()
    centro_lon = df_mapa['lon'].mean()
    
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=14, control_scale=True)
    
    # Lista de coordenadas [lat, lon] para a mancha
    dados_calor = df_mapa[['lat', 'lon']].values.tolist()
    
    # Adiciona a mancha de calor
    HeatMap(
        dados_calor,
        radius=raio_mancha,
        blur=desfoco,
        min_opacity=0.4
    ).add_to(m)
    
    # Opcional: Adiciona círculos exatos de 75 metros de raio para ver a área exata
    if exibir_circulos:
        for _, linha in df_mapa.iterrows():
            folium.Circle(
                location=[linha['lat'], linha['lon']],
                radius=75,  # Raio fixo de 75 metros
                color='red',
                weight=1,
                fill=True,
                fill_opacity=0.15
            ).add_to(m)
            
    st.write(f"🟢 **{len(df_mapa)}** registros válidos encontrados (Coluna A preenchida + Coordenada na Coluna C).")
    st_folium(m, width=1300, height=700, returned_objects=[], key="mapa_mancha_75m")
else:
    st.warning("Nenhum registro válido encontrado (verifique se a Coluna A possui valores e se as coordenadas na Coluna C estão corretas).")
