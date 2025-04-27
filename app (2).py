# app.py

# --- Librerías necesarias ---
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium import Choropleth, LayerControl
import matplotlib.pyplot as plt
from streamlit_folium import folium_static

# --- Cargar los datos ---
# Asegúrate de tener los archivos en las rutas correctas:
# listado_iiee.xlsx y Shapefile/DISTRITOS.shp

# 1. Cargar colegios
escuelas = pd.read_excel('listado_iiee.xlsx')

# 2. Crear GeoDataFrame de colegios
schools_geo = gpd.GeoDataFrame(
    escuelas,
    crs="EPSG:4326",
    geometry=gpd.points_from_xy(escuelas['Longitud'], escuelas['Latitud'])
)

# 3. Cargar shapefile de distritos
districts = gpd.read_file('Shapefile/DISTRITOS.shp')

# --- Preprocesar districts para Streamlit ---

# 1. QUEDARTE SOLO CON ID Y GEOMETRÍA
districts = districts[['IDDIST', 'geometry']].copy()

# 2. SIMPLIFICAR POLÍGONOS
districts['geometry'] = districts['geometry'].simplify(tolerance=0.01, preserve_topology=True)

# 4. Ajustes de formato
schools_geo['Ubigeo'] = schools_geo['Ubigeo'].astype(str).str.zfill(6)
districts['IDDIST'] = districts['IDDIST'].astype(str).str.zfill(6)
schools_geo['Nivel'] = schools_geo['Nivel / Modalidad'].str.lower()

# --- Configurar página de Streamlit ---
st.set_page_config(page_title="Análisis Geoespacial de Colegios en Perú", layout="wide")

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["🗂️ Descripción de Datos", "🗺️ Mapas Estáticos", "🌍 Mapas Dinámicos", "Análisis Extra"])

# ============================================================
# Tab 1: Descripción de datos
# ============================================================

with tab1:
    st.header("🗂️ Descripción de Datos")

    st.subheader("Unidad de Análisis")
    st.write("""
    La unidad de análisis de este proyecto es cada institución educativa (colegio) en el Perú.
    Cada colegio está identificado de manera única por sus coordenadas geográficas (latitud y longitud) y su nivel educativo (Inicial, Primaria o Secundaria).
    El análisis espacial agrega los colegios a nivel distrital para observar patrones de acceso educativo en el ámbito local.
    """)

    st.subheader("Fuentes de Datos")
    st.write("""
    - **Base de datos de colegios**: Ministerio de Educación del Perú (MINEDU), extraído del portal SIGMED (https://sigmed.minedu.gob.pe/mapaeducativo/).
    - **Shapefile de límites distritales**: Fuente oficial del Instituto Nacional de Estadística e Informática (INEI).
    """)

    st.subheader("Supuestos y Preprocesamiento")
    st.write("""
    - Solo se incluyeron colegios que cuentan con coordenadas geográficas válidas y completas.
    - Se categorizaron los colegios en tres niveles educativos: Inicial, Primaria y Secundaria.
    - Se excluyeron las instituciones sin clasificación de nivel o con errores de geolocalización.
    - La agregación distrital asume que los límites provistos por el INEI son actuales y precisos.
    - El análisis de proximidad basado en radio utiliza un buffer de 5 km alrededor de las escuelas primarias.
    """)

# ============================================================
# Tab 2: Mapas Estáticos
# ============================================================

with tab2:
    st.header("🗺️ Mapas Estáticos")

    niveles = ['inicial', 'primaria', 'secundaria']

    for nivel in niveles:
        st.subheader(f"Distribución de colegios - Nivel {nivel.capitalize()}")

        # Filtrar colegios del nivel
        filtered = schools_geo[schools_geo['Nivel'].str.contains(nivel, case=False, na=False)]

        # Contar por distrito
        conteo = filtered.groupby('Ubigeo').size().reset_index(name='Total_Colegios')

        # Merge shapefile
        districts_plot = districts.merge(conteo, left_on='IDDIST', right_on='Ubigeo', how='left')
        districts_plot['Total_Colegios'] = districts_plot['Total_Colegios'].fillna(0)

        # Plot
        fig, ax = plt.subplots(figsize=(10, 10))
        districts_plot.plot(
            column='Total_Colegios',
            cmap='YlOrRd',
            linewidth=0.5,
            edgecolor='black',
            legend=True,
            ax=ax
        )
        ax.set_title(f'Distribución de colegios - Nivel {nivel.capitalize()}', fontsize=16)
        ax.axis('off')
        st.pyplot(fig)

# ============================================================
# Tab 3: Mapas Dinámicos
# ============================================================

with tab3:
    st.header("🌍 Mapas Dinámicos")

    st.subheader("Distribución de colegios por nivel educativo (mapa interactivo)")

    niveles = ['inicial', 'primaria', 'secundaria']
    conteos = {}

    for nivel in niveles:
        filtered = schools_geo[schools_geo['Nivel'].str.contains(nivel, case=False, na=False)]
        conteo = filtered.groupby('Ubigeo').size().reset_index(name='Total_Colegios')
        conteos[nivel] = conteo

    # Crear el mapa base
    m = folium.Map(location=[-12.04318, -77.02824], zoom_start=6, tiles='OpenStreetMap')

    # Agregar capas
    for nivel, conteo in conteos.items():
        Choropleth(
            geo_data=districts.to_json(),
            data=conteo,
            columns=['Ubigeo', 'Total_Colegios'],
            key_on='feature.properties.IDDIST',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            name=f"{nivel.capitalize()}",
            legend_name=f"Colegios de {nivel.capitalize()}"
        ).add_to(m)

    LayerControl(collapsed=False).add_to(m)

    folium_static(m, width=1200, height=700)

# ============================================================
# Tab 4: Mapas Dinámicos
# ============================================================

with tab4:
    st.header("🏆 Top 10 distritos con más colegios")
    
    # Crear tabla de conteo de colegios por distrito
    conteo_colegios_distrito = schools_geo.groupby('Ubigeo').size().reset_index(name='Total_Colegios')

    top10 = conteo_colegios_distrito.sort_values('Total_Colegios', ascending=False).head(10)

    fig, ax = plt.subplots(figsize=(10, 6))
    top10.plot(kind='barh', x='Ubigeo', y='Total_Colegios', color='skyblue', ax=ax)
    ax.set_xlabel('Número de colegios')
    ax.set_title('Top 10 distritos con más colegios')
    ax.invert_yaxis()  # Para que el distrito con más colegios esté arriba
    plt.tight_layout()

    st.pyplot(fig)

with tab4:
    st.header("📊 Distribución de colegios por distrito")

    fig2, ax2 = plt.subplots(figsize=(10, 6))
    conteo_colegios_distrito['Total_Colegios'].plot(
        kind='hist', bins=30, color='orchid', edgecolor='black', ax=ax2
    )
    ax2.set_xlabel('Número de colegios por distrito')
    ax2.set_title('Distribución de colegios por distrito')
    plt.tight_layout()

    st.pyplot(fig2)

