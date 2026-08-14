import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import shapely.geometry as sg
from shapely.ops import unary_union
import json

st.set_page_config(layout="wide", page_title="Mapa de Mancha Unicor - Controle HP")
st.title("Mapa de Mancha de Atendimento PAE")

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
    
    # --- CONSTRUÇÃO DO POLÍGONO UNIFICADO (SBA / UNARY UNION) ---
    # Conversão de 60 metros para graus aproximados em latitude/longitude
    RAIO_METROS = 60
    GRAUS_POR_METRO = 1 / 111139.0
    raio_graus = RAIO_METROS * GRAUS_POR_METRO

    poligonos = []
    for _, linha in df_mapa.iterrows():
        ponto = sg.Point(linha['lon'], linha['lat'])
        # Cria o buffer circular de 60 metros
        circulo = ponto.buffer(raio_graus)
        poligonos.append(circulo)

    # Une todos os círculos em uma única geometria sem sobreposições internas
    mancha_unificada = unary_union(poligonos)

    # Estilo verde unicor
    estilo_verde = {
        'fillColor': '#00FF00',  # Verde limão/vivo (ajuste para '#2ECC71' se preferir mais suave)
        'color': '#00FF00',
        'weight': 0,             # Sem bordas para manter a área 100% limpa
        'fillOpacity': 0.45      # Opacidade fixa (não escurece nas sobreposições)
    }

    # Adiciona a mancha verde unificada ao mapa
    folium.GeoJson(
        json.loads(json.dumps(sg.mapping(mancha_unificada))),
        style_function=lambda x: estilo_verde
    ).add_to(m)
            
    st.write(f"🟢 **{len(df_mapa)}** registros plotados ")
    st_folium(m, width=1300, height=700, returned_objects=[], key="mapa_mancha_unicor_verde")
else:
    st.warning("Nenhum dado válido encontrado para plotar.")
