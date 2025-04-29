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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗂️ Descripción de Datos", "🗺️ Mapas Estáticos", "🌍 Mapas Dinámicos", "Análisis Extra", "Zoom en Ica"])

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
# Tab 4: Análisis Extra
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
 
# ============================================================
# Tab 5: Zoom en Ica
# ============================================================

with tab5:
    # --- CONFIGURACIÓN DE STREAMLIT ---
    st.markdown("<h1 style='color:white;'>📊 Descripción de los Datos</h1>", unsafe_allow_html=True)
    
    # --- FILTRAR SOLO ICA ---
    filtered_schools_1 = schools_geo[
        schools_geo['Departamento'].str.upper() == 'ICA'
    ]
    escuelas = filtered_schools_1.copy()
    
    # --- LIMPIEZA Y FILTRO POR NIVELES ---
    niveles_validos = ['inicial', 'primaria', 'secundaria']
    escuelas = escuelas[escuelas['Nivel'].str.lower().isin(niveles_validos)]
    
    # --- CONTEOS ---
    total = len(escuelas)
    primarias = len(escuelas[escuelas['Nivel'].str.contains('primaria', case=False, na=False)])
    secundarias = len(escuelas[escuelas['Nivel'].str.contains('secundaria', case=False, na=False)])
    
    # --- CONTEO POR DISTRITO ---
    conteo_distrito = escuelas.groupby('Distrito').size().reset_index(name='Total')
    conteo_distrito = conteo_distrito.sort_values('Total', ascending=False)
    
    # --- METRICAS EN COLUMNAS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Escuelas", total)
    col2.metric("Escuelas Primarias", primarias)
    col3.metric("Escuelas Secundarias", secundarias)
    
    # --- GRÁFICO DE BARRAS ---
    st.markdown("<h3 style='color:white;'>Distribución por Distrito</h3>", unsafe_allow_html=True)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(conteo_distrito['Distrito'], conteo_distrito['Total'], color='skyblue')
    
    # Estética dark
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.tick_params(colors='white')
    plt.xticks(rotation=90, color='white')
    plt.yticks(color='white')
    ax.set_title('', color='white')
    
    plt.tight_layout()
    st.pyplot(fig)

with tab5:
    st.header("📊 Distribución de secundarias en el departamento de Ica")
    
    # Asegurarte de que los IDs estén en el formato correcto
    schools_geo['Ubigeo'] = schools_geo['Ubigeo'].astype(str).str.zfill(6)
    districts['IDDIST'] = districts['IDDIST'].astype(str).str.zfill(6)
    schools_geo['Nivel'] = schools_geo['Nivel'].str.lower()

    # Definir el nivel educativo que quieres visualizar 
    nivel = 'secundaria'  # 'inicial' o 'primaria'

    # Filtrar solo colegios de ese nivel
    filtered = schools_geo[schools_geo['Nivel'].str.contains(nivel, case=False, na=False)]

    # Función auxiliar para encontrar la primera columna que empiece con 'departamen'
    def get_departamento_col(df):
        for col in df.columns:
            if col.strip().lower().startswith('departamen'):
                return col
        raise KeyError("No se encontró una columna que represente el departamento.")
    
    # Buscar el nombre correcto de la columna en cada DataFrame
    col_dep_schools = get_departamento_col(schools_geo)
    col_dep_districts = get_departamento_col(districts)
    
    # Filtrar usando esas columnas (convierte a mayúsculas para asegurar coincidencia)
    filtered = schools_geo[schools_geo[col_dep_schools].str.upper() == 'ICA']
    districts_ica = districts[districts[col_dep_districts].str.upper() == 'ICA']

    # Conteo por distrito dentro de Ica
    conteo = filtered.groupby('Ubigeo').size().reset_index(name='Total_Colegios')
    conteo_ica = conteo[conteo['Ubigeo'].isin(districts_ica['IDDIST'])]

    # Merge shapefile ICA + conteo
    districts_plot_ica = districts_ica.merge(conteo_ica, left_on='IDDIST', right_on='Ubigeo', how='left')
    districts_plot_ica['Total_Colegios'] = districts_plot_ica['Total_Colegios'].fillna(0).astype(int)

    # Graficar
    fig, ax = plt.subplots(figsize=(10, 10))
    districts_plot_ica.plot(
        column='Total_Colegios',
        cmap='Reds',
        linewidth=0.5,
        edgecolor='black',
        legend=True,
        ax=ax
    )

    # Título y estilo
    ax.set_title(f'Distribución de colegios {nivel.capitalize()} en el Departamento de Ica', fontsize=16)
    ax.axis('off')

    # Agregar etiquetas con los valores sobre cada distrito
    for idx, row in districts_plot.iterrows():
        if row['Total_Colegios'] > 0:  # Solo etiquetar distritos con colegios
            centroid = row['geometry'].centroid
            ax.text(centroid.x, centroid.y, int(row['Total_Colegios']),
                    ha='center', va='center', fontsize=8, color='black')

    plt.tight_layout()
    plt.show()
 
with tab5:
    st.header("📊 Panorama escolar en Ica: Identificación de escuelas primarias con mayor y menor cantidad de escuelas secundarias cerca")
        
    # Filtrar solo Ica
    primarias_ica = schools_geo[
        (schools_geo['Nivel'].str.contains("primaria", case=False, na=False)) &
        (schools_geo['Departamento'].str.upper() == 'ICA')
    ].copy()
    
    secundarias_ica = schools_geo[
        (schools_geo['Nivel'].str.contains("secundaria", case=False, na=False)) &
        (schools_geo['Departamento'].str.upper() == 'ICA')
    ].copy()
    
    # Crear geometría
    primarias_ica = primarias_ica.set_geometry(gpd.points_from_xy(primarias_ica.Longitud, primarias_ica.Latitud)).set_crs(epsg=4326).to_crs(epsg=32718)
    secundarias_ica = secundarias_ica.set_geometry(gpd.points_from_xy(secundarias_ica.Longitud, secundarias_ica.Latitud)).set_crs(epsg=4326).to_crs(epsg=32718)
    
    # Crear buffer de 5km
    primarias_ica['buffer_5km'] = primarias_ica.geometry.buffer(5000)
    
    # Contar secundarias dentro del buffer
    primarias_ica['conteo_secundarias'] = primarias_ica['buffer_5km'].apply(
        lambda buf: secundarias_ica[secundarias_ica.geometry.within(buf)].shape[0]
    )
    
    # Identificar primaria con más y menos secundarias cercanas
    primaria_max = primarias_ica.loc[primarias_ica['conteo_secundarias'].idxmax()]
    primaria_min = primarias_ica.loc[primarias_ica['conteo_secundarias'].idxmin()]
    
    # Volver a lat/lon
    primarias_ica = primarias_ica.to_crs(epsg=4326)
    secundarias_ica = secundarias_ica.to_crs(epsg=4326)
    
    
    # Filtrar solo Ica
    primarias_ica = schools_geo[
        (schools_geo['Nivel'].str.contains("primaria", case=False, na=False)) &
        (schools_geo['Departamento'].str.upper() == 'ICA')
    ].copy()
    
    secundarias_ica = schools_geo[
        (schools_geo['Nivel'].str.contains("secundaria", case=False, na=False)) &
        (schools_geo['Departamento'].str.upper() == 'ICA')
    ].copy()
    
    # Crear geometría
    primarias_ica = primarias_ica.set_geometry(gpd.points_from_xy(primarias_ica.Longitud, primarias_ica.Latitud)).set_crs(epsg=4326).to_crs(epsg=32718)
    secundarias_ica = secundarias_ica.set_geometry(gpd.points_from_xy(secundarias_ica.Longitud, secundarias_ica.Latitud)).set_crs(epsg=4326).to_crs(epsg=32718)
    
    # Crear buffer de 5km
    primarias_ica['buffer_5km'] = primarias_ica.geometry.buffer(5000)
    
    # Contar secundarias dentro del buffer
    primarias_ica['conteo_secundarias'] = primarias_ica['buffer_5km'].apply(
        lambda buf: secundarias_ica[secundarias_ica.geometry.within(buf)].shape[0]
    )
    
    # Identificar primaria con más y menos secundarias cercanas
    primaria_max = primarias_ica.loc[primarias_ica['conteo_secundarias'].idxmax()]
    primaria_min = primarias_ica.loc[primarias_ica['conteo_secundarias'].idxmin()]
    
    # Volver a lat/lon
    primarias_ica = primarias_ica.to_crs(epsg=4326)
    secundarias_ica = secundarias_ica.to_crs(epsg=4326)
    
    # Crear mapa centrado en Ica
    m = folium.Map(location=[-14.07, -75.73], zoom_start=8, tiles='CartoDB positron')
    
    # Agregar buffers como círculos
    for _, row in primarias_ica.iterrows():
        folium.Circle(
            location=[row.geometry.y, row.geometry.x],
            radius=5000,
            color='red',
            fill=True,
            fill_opacity=0.2
        ).add_to(m)
        
    # Marcador para mi colegio
    folium.Marker(
        location=[-14.08831, -75.75128],
        popup=folium.Popup("<b>IE: DE LA CRUZ</b><br>Distrito: ICA<br>Nivel: Secundaria<br>Gestión: Privada", max_width=250),
        icon=folium.Icon(color='blue', icon='graduation-cap', prefix='fa')
    ).add_to(m)
    
    # Marcador para la primaria con más secundarias
    folium.Marker(
        location=[-14.07166, -75.72748],
        popup=folium.Popup(
            f"<b>Escuela con MÁS secundarias cercanas:</b><br>"
            f"{primaria_max['Código Modular']}<br>Conteo: {primaria_max['conteo_secundarias']}", max_width=250
        ),
        icon=folium.Icon(color="green", icon="arrow-up", prefix='fa')
    ).add_to(m)
    
    # Marcador para la primaria con menos secundarias
    folium.Marker(
        location=[-13.87274, -76.00486],
        popup=folium.Popup(
            f"<b>Escuela con MENOS secundarias cercanas:</b><br>"
            f"{primaria_min['Código Modular']}<br>Conteo: {primaria_min['conteo_secundarias']}", max_width=250
        ),
        icon=folium.Icon(color="purple", icon="arrow-down", prefix='fa')
    ).add_to(m)
    
    # Mostrar mapa
    m
    
    
    
    
    
    
