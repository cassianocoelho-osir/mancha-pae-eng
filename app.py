import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import shapely.geometry as sg
from shapely.ops import unary_union
import json

st.set_page_config(layout="wide", page_title="Mapa de Mancha Unicor - Controle HP")
st.title("🟢 Mapa de Mancha de Atendimento PAE")

# Exporta a aba Controle HP (gid=1265583443) em CSV
URL_CSV = "https://docs.google.com/spreadsheets/d/1vmccPxvC4Z0rrfSyhF6HhehGSqpjY5oJboR-hG8O4bg/export?format=csv&gid=1265583443"

@st.cache_data(ttl=300)
def carregar_dados():
    df = pd.read_csv(URL_CSV, header=None)
    
    df_util = pd.DataFrame()
    df_util['coluna_a'] = df[0].fillna("").astype(str).str.strip()
    df_util['coordenada'] = df[2].fillna("").astype(str).str.strip()
    
    # Lê a Coluna D (HP) e converte para valor numérico
    df_util['hp'] = pd.to_numeric(df[5], errors='coerce').fillna(0).astype(int)
    
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
    total_hp = df_mapa['hp'].sum()
    
    m = folium.Map(
        location=[centro_lat, centro_lon], 
        zoom_start=15, 
        control_scale=True
    )
    
    # --- 1. MANCHA VERDE UNICOR (BUFFER 60m) ---
    RAIO_METROS = 60
    GRAUS_POR_METRO = 1 / 111139.0
    raio_graus = RAIO_METROS * GRAUS_POR_METRO

    poligonos = []
    for _, linha in df_mapa.iterrows():
        ponto = sg.Point(linha['lon'], linha['lat'])
        circulo = ponto.buffer(raio_graus)
        poligonos.append(circulo)

    mancha_unificada = unary_union(poligonos)

    estilo_verde = {
        'fillColor': '#00FF00',
        'color': '#00FF00',
        'weight': 0,
        'fillOpacity': 0.25
    }

    folium.GeoJson(
        json.loads(json.dumps(sg.mapping(mancha_unificada))),
        style_function=lambda x: estilo_verde
    ).add_to(m)

    # --- 2. AGRUPAMENTO E SOMA DE HP (MARKER CLUSTER) ---
    marker_cluster = MarkerCluster(
        name="Clusters de HP",
        overlay=True,
        control=True,
        icon_create_function="""
        function(cluster) {
            var markers = cluster.getAllChildMarkers();
            var sumHP = 0;
            for (var i = 0; i < markers.length; i++) {
                sumHP += parseInt(markers[i].options.hp_val || 0);
            }
            return L.divIcon({
                html: '<div style="background-color: rgba(0, 100, 0, 0.85); color: white; border-radius: 50%; width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.4);">' + sumHP + '</div>',
                className: 'marker-cluster-hp',
                iconSize: L.point(42, 42)
            });
        }
        """
    ).add_to(m)

    # Adiciona os pontos individuais no agrupador
    for _, linha in df_mapa.iterrows():
        val_hp = int(linha['hp'])
        folium.CircleMarker(
            location=[linha['lat'], linha['lon']],
            radius=5,
            color="#006400",
            fill=True,
            fill_color="#00FF00",
            fill_opacity=0.9,
            popup=f"<b>Ref:</b> {linha['coluna_a']}<br><b>HP:</b> {val_hp}",
            tooltip=f"{linha['coluna_a']} — {val_hp} HP",
            hp_val=val_hp
        ).add_to(marker_cluster)

    # --- EXIBIÇÃO DE MÉTRICAS ---
    col1, col2 = st.columns(2)
    col1.metric("Total de Registros Plotados", len(df_mapa))
    col2.metric("Soma Total de HP", f"{total_hp:,}".replace(",", "."))

    # Renderiza o mapa com captura de estado interativo
    st_data = st_folium(m, width=1300, height=700, key="mapa_hp_zoom")

else:
    st.warning("Nenhum dado válido encontrado para plotar.")
