import geopandas as gpd
import pandas as pd
import plotly.express as px
import os

# Asegurar que la carpeta de salida exista
os.makedirs("outputs", exist_ok=True)
os.makedirs("outputs/html", exist_ok=True) # Carpeta para los gráficos interactivos

# 1. Cargar el GeoJSON final
print("Cargando base de datos espacial...")
gdf = gpd.read_file("data/processed/siniestros_analizados_final.geojson")

# EXTRACCIÓN DE CARACTERÍSTICAS (Vehículos)
col_vehiculos = 'VEHICULO_INVOLUCRADO' if 'VEHICULO_INVOLUCRADO' in gdf.columns else 'VEHICULO INVOLUCRADO'

if col_vehiculos in gdf.columns:
    print("Procesando tipos de vehículos...")
    gdf[col_vehiculos] = gdf[col_vehiculos].fillna('').astype(str)
    
    # EXTRACCIÓN DE CARACTERÍSTICAS (Vehículos)
print("Procesando tipos de vehículos desde variables booleanas...")

gdf['participa_automovil'] = gdf['PARTICIPA_AUTO'].astype(bool)
gdf['participa_camioneta'] = gdf['PARTICIPA_CAMIONETA'].astype(bool)
gdf['participa_camion'] = gdf['PARTICIPA_CAMION'].astype(bool)
gdf['participa_motocicleta'] = gdf['PARTICIPA_MOTO'].astype(bool)


tema = "plotly_white"
fuente_corporativa = dict(family="Arial, Helvetica, sans-serif", size=14, color="#2c3e50")

# GRÁFICO 1: Análisis Topológico (Distancias)
df_distancias = gdf.dropna(subset=['DIST_INTERSECCION_M']).copy()

fig1 = px.histogram(
    df_distancias, 
    x='DIST_INTERSECCION_M', 
    nbins=30,
    title='Distribución Espacial: Distancia a la Intersección más Cercana',
    labels={'DIST_INTERSECCION_M': 'Distancia a intersección (metros)'},
    color_discrete_sequence=['#2C3E50'],
    template=tema
)
fig1.update_layout(font=fuente_corporativa, yaxis_title="Cantidad de Siniestros Fatales", bargap=0.05)
fig1.write_image("outputs/diapositiva_1_distancias.png", width=1000, height=600, scale=2)
fig1.write_html("outputs/html/diapositiva_1_distancias.html")

# GRÁFICO 2: Conteo de Tipos de Vehículos Involucrados
conteos_vehiculos = [
    gdf['participa_automovil'].sum(),
    gdf['participa_camioneta'].sum(),
    gdf['participa_camion'].sum(),
    gdf['participa_motocicleta'].sum()
]
nombres_eje_vehiculos = ['Automóvil', 'Camioneta', 'Camion', 'Motocicleta']

df_conteos = pd.DataFrame({'Vehículo': nombres_eje_vehiculos, 'Cantidad': conteos_vehiculos})

fig2 = px.bar(
    df_conteos, 
    x='Vehículo', 
    y='Cantidad',
    text='Cantidad', # Muestra el número sobre la barra
    title='Frecuencia de Vehículos Involucrados en Siniestros Fatales (RN 5)',
    color='Vehículo',
    color_discrete_sequence=['#3498DB', '#E74C3C', '#2C3E50', '#9B59B6'],
    template=tema
)
fig2.update_traces(textposition='outside', textfont_size=14)
fig2.update_layout(font=fuente_corporativa, showlegend=False)
fig2.write_image("outputs/diapositiva_2_vehiculos.png", width=1000, height=600, scale=2)
fig2.write_html("outputs/html/diapositiva_2_vehiculos.html")


# PREPARACIÓN DE DATOS PARA BOXPLOT
columnas_v = ['participa_automovil', 'participa_camioneta', 'participa_camion', 'participa_motocicleta']
df_melted = df_distancias.melt(
    id_vars=['DIST_INTERSECCION_M'], 
    value_vars=columnas_v,
    var_name='Tipo_Vehiculo', 
    value_name='Involucrado'
)
df_plot = df_melted[df_melted['Involucrado'] == True].copy()
mapeo_nombres = {
    'participa_automovil': 'Automóvil', 'participa_camioneta': 'Camioneta',
    'participa_camion': 'Camión', 'participa_motocicleta': 'Motocicleta'
}
df_plot['Tipo_Vehiculo'] = df_plot['Tipo_Vehiculo'].map(mapeo_nombres)

# GRÁFICO 3: Boxplot - Distancia vs Tipo de Vehículo
fig3 = px.box(
    df_plot, 
    x='Tipo_Vehiculo', 
    y='DIST_INTERSECCION_M',
    color='Tipo_Vehiculo',
    title='Distribución Espacial de Siniestros por Tipo de Vehículo',
    labels={'DIST_INTERSECCION_M': 'Distancia a intersección (metros)', 'Tipo_Vehiculo': 'Tipo de Vehículo'},
    color_discrete_sequence=['#1ABC9C', '#F39C12', '#34495E', '#E74C3C'],
    template=tema
)
fig3.update_layout(font=fuente_corporativa, showlegend=False)
fig3.write_image("outputs/diapositiva_3_boxplot_vehiculos.png", width=1000, height=600, scale=2)
fig3.write_html("outputs/html/diapositiva_3_boxplot.html")


# GRÁFICO 4: Donut Chart - Proporción de Puntos Negros (DBSCAN)
if 'cluster' in gdf.columns: 
    aislados = len(gdf[gdf['cluster'] == -1])
    en_cluster = len(gdf[gdf['cluster'] != -1])
    
    df_cluster = pd.DataFrame({
        'Categoría': ['En Puntos Negros (Clústeres)', 'Eventos Aislados (Ruido)'],
        'Cantidad': [en_cluster, aislados]
    })

    fig4 = px.pie(
        df_cluster, 
        values='Cantidad', 
        names='Categoría',
        hole=0.6, 
        title='Agrupamiento Espacial de Siniestros (DBSCAN)',
        color_discrete_sequence=['#E74C3C', '#BDC3C7'],
        template=tema
    )
    fig4.update_traces(textposition='inside', textinfo='percent+label', textfont_size=14)
    fig4.update_layout(font=fuente_corporativa, showlegend=False)
    fig4.write_image("outputs/diapositiva_4_dbscan.png", width=800, height=800, scale=2)
    fig4.write_html("outputs/html/diapositiva_4_dbscan.html")



# CDF (Proporción Acumulada)
fig_cdf = px.ecdf(
    df_distancias, 
    x='DIST_INTERSECCION_M',
    title='Proporción Acumulada de Siniestros vs. Distancia',
    labels={'DIST_INTERSECCION_M': 'Distancia a intersección (metros)'},
    template=tema
)
fig_cdf.update_traces(line_color='#E74C3C', line_width=4)
fig_cdf.update_layout(font=fuente_corporativa, yaxis_title="Proporción Acumulada (0 a 1)")
fig_cdf.write_image("outputs/anexo_1_curva_cdf.png", width=1000, height=600, scale=2)

#  Swarm Plot
fig_strip = px.strip(
    df_plot, 
    x='Tipo_Vehiculo', 
    y='DIST_INTERSECCION_M',
    color='Tipo_Vehiculo',
    title='Distribución Exacta de Siniestros (1 Punto = 1 Vehículo)',
    labels={'DIST_INTERSECCION_M': 'Distancia a intersección (metros)', 'Tipo_Vehiculo': 'Tipo de Vehículo'},
    color_discrete_sequence=['#1ABC9C', '#F39C12', '#34495E', '#E74C3C'],
    template=tema,
    stripmode='overlay'
)
fig_strip.update_traces(marker=dict(size=7, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
fig_strip.update_layout(font=fuente_corporativa, showlegend=False)
fig_strip.write_image("outputs/anexo_2_swarm_plot.png", width=1000, height=600, scale=2)

# Violin Plot
fig_violin = px.violin(
    df_plot, 
    x='Tipo_Vehiculo', 
    y='DIST_INTERSECCION_M',
    color='Tipo_Vehiculo',
    box=True, 
    title='Densidad Espacial de Riesgo (Violin Plot)',
    labels={'DIST_INTERSECCION_M': 'Distancia a intersección (metros)', 'Tipo_Vehiculo': 'Tipo de Vehículo'},
    color_discrete_sequence=['#1ABC9C', '#F39C12', '#34495E', '#E74C3C'],
    template=tema
)
fig_violin.update_layout(font=fuente_corporativa, showlegend=False)
fig_violin.write_image("outputs/anexo_3_violin_plot.png", width=1000, height=600, scale=2)

print("Graficos generados en la carpeta 'outputs/'!")  

