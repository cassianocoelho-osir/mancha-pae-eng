import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Mapa de Mancha - Controle HP")
st.title("Entrega Hp Mancha")

# Exporta a aba Controle HP (gid=1265583443) em CSV
URL_CSV = "https://docs.google.com/spreadsheets/d/1vmccPxvC4Z0rrfSyhF6HhehGSqpjY5oJboR-hG8O4bg/export?format=csv&gid=1265583443"

@st.cache_data(ttl=300)
def carregar_dados():
    df = pd.read_csv(URL_CSV, header=None)
    
    df_util = pd.DataFrame()
    df_util['coluna_a'] = df[0].fillna("").astype(str).str.strip()
    df_util['coordenada'] = df[2].fillna("").astype(str).str.strip()
    
    # 1. Filtra apenas linhas onde a Coluna A NÃO está vazia e desconsidera o cabeçalho
    df_util = df_util[(df_util['coluna_a'] != "") & (df_util['coluna_a'] != "CEO/SPL REF.")]
    
    # 2. Extrai latitude e longitude
    def extrair_lat_lon(txt):
        try:
            partes = str(txt).split(',')
            return float(partes[0].strip()), float(partes[1].strip())
        except:
            return None, None

    coords = df_util['coordenada'].apply(extrair_lat_lon)
    df_util['lat'] = [c[0] for c in coords]
    df_util['lon'] = [c[1] for c in coords]
    
    # Remove qualquer registro inválido
    df_util = df_util.dropna(subset=['lat', 'lon'])
    
    return df_util

try:
    df_mapa = carregar_dados()
except Exception as e:
    st.error(f"Erro ao ler os dados da planilha: {e}")
    st.stop()

# --- MONTAGEM DO MAPA ---
if not df_mapa.empty:
    centro_lat = df_mapa['lat'].mean()
    centro_lon = df_mapa['lon'].mean()
    
    m = folium.Map(
        location=[centro_lat, centro_lon], 
        zoom_start=15, 
        control_scale=True
    )
    
    # Adiciona a camada de mancha de calor (HeatMap)
    dados_calor = df_mapa[['lat', 'lon']].values.tolist()
    HeatMap(
        dados_calor,
        radius=25,
        blur=15,
        min_opacity=0.4
    ).add_to(m)
    
    # Adiciona o buffer real de 75 metros para cada ponto
    for _, linha in df_mapa.iterrows():
        folium.Circle(
            location=[linha['lat'], linha['lon']],
            radius=75,
            color='red',
            weight=1,
            fill=True,
            fill_opacity=0.1
        ).add_to(m)
            
    st.write(f"🟢 **{len(df_mapa)}** registros válidos encontrados e plotados.")
    st_folium(m, width=1300, height=700, returned_objects=[], key="mapa_mancha_final")
else:
    st.warning("Nenhum dado válido encontrado para plotar.")
