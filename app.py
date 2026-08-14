import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import shapely.geometry as sg
from shapely.ops import unary_union
import json

st.set_page_config(layout="wide", page_title="Mapa de Mancha Unicor - Controle HP")
st.title("🟢 Mapa de Mancha de Atendimento PAE (Soma de Entregue)")

# Exporta a aba Controle HP (gid=1265583443) em CSV
URL_CSV = "https://docs.google.com/spreadsheets/d/1vmccPxvC4Z0rrfSyhF6HhehGSqpjY5oJboR-hG8O4bg/export?format=csv&gid=1265583443"

@st.cache_data(ttl=300)
def carregar_dados():
    df = pd.read_csv(URL_CSV, header=None)
    
    df_util = pd.DataFrame()
    df_util['coluna_a'] = df[0].fillna("").astype(str).str.strip()
    df_util['coordenada'] = df[2].fillna("").astype(str).str.strip()
    
    # Coluna F (índice 5) é o valor ENTREGUE
    df_util['entregue'] = pd.to_numeric(
        df[5].astype(str).str.replace(r'[^\d]', '', regex=True), 
        errors='coerce'
    ).fillna(0).astype(int)
    
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
    total_entregue = df_mapa['entregue'].sum()
    
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

    # --- 2. SOMA DE ENTREGUE VIA MARKER CLUSTER (JAVASCRIPT) ---
    icon_create_function = """
    function(cluster) {
        var markers = cluster.getAllChildMarkers();
        var sumEntregue = 0;
        for (var i = 0; i < markers.length; i++) {
            var val = parseInt(markers[i].options.alt) || 0;
            sumEntregue += val;
        }
        return L.divIcon({
            html: '<div style="background-color: #006400; color: white; border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; border: 2px solid #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.5);">' + sumEntregue + '</div>',
            className: 'marker-cluster-entregue',
            iconSize: L.point(44, 44)
        });
    }
    """

    marker_cluster = MarkerCluster(
        name="Clusters Entregue",
        icon_create_function=icon_create_function
    ).add_to(m)

    # Adiciona marcadores individuais no cluster
    for _, linha in df_mapa.iterrows():
        val_entregue = int(linha['entregue'])
        
        icon_html = f"""
        <div style="background-color: #008000; color: white; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 11px; border: 1.5px solid white;">
            {val_entregue}
        </div>
        """
        
        folium.Marker(
            location=[linha['lat'], linha['lon']],
            icon=folium.DivIcon(html=icon_html, icon_size=(28, 28)),
            alt=str(val_entregue),  # Armazena o valor do 'Entregue' para o JavaScript somar
            popup=f"<b>Ref:</b> {linha['coluna_a']}<br><b>Entregue:</b> {val_entregue}",
            tooltip=f"{linha['coluna_a']} — {val_entregue} Entregues"
        ).add_to(marker_cluster)

    # --- EXIBIÇÃO DE MÉTRICAS ---
    col1, col2 = st.columns(2)
    col1.metric("Total de Registros Plotados", len(df_mapa))
    col2.metric("Soma Total Entregue", f"{total_entregue:,}".replace(",", "."))

    st_folium(m, width=1300, height=700, returned_objects=[], key="mapa_entregue_soma")

else:
    st.warning("Nenhum dado válido encontrado para plotar.")
