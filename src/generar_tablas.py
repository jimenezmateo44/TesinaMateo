import geopandas as gpd
import pandas as pd

# 1. Cargar el dataset final procesado
print("Cargando dataset...")
gdf_final = gpd.read_file("data/processed/siniestros_analizados_final.geojson")

# 2. TABLA 1: Estadísticos de la Distancia Topológica (General)
stats_dist = gdf_final['DIST_INTERSECCION_M'].describe().to_frame().T
stats_dist = stats_dist.rename(columns={
    'count': 'Total_Siniestros',
    'mean': 'Media_(m)',
    'std': 'Desvio_Std_(m)',
    'min': 'Minimo_(m)',
    '25%': 'Q1_25%_(m)',
    '50%': 'Mediana_50%_(m)',
    '75%': 'Q3_75%_(m)',
    'max': 'Maximo_(m)'
}).round(0).astype(int)

print("\n--- RESUMEN ESTADÍSTICO DE DISTANCIAS TOPOLÓGICAS ---")
print(stats_dist.to_string(index=False))

# 3. TABLA 2: Estadísticos según Tipo de Vehículo (NORMALIZADO CON BOOLEANOS)
# Mapeamos las columnas booleanas de tu GeoJSON a los nombres formales para la tesina
categorias_vehiculos = {
    'PARTICIPA_AUTO': 'Automóvil',
    'PARTICIPA_CAMIONETA': 'Camioneta',
    'PARTICIPA_CAMION': 'Camión',
    'PARTICIPA_MOTO': 'Motocicleta'
}

filas_stats = []
for col_booleana, nombre_limpio in categorias_vehiculos.items():
    # Filtramos la base para quedarnos solo con los siniestros donde participó este vehículo
    df_filtrado = gdf_final[gdf_final[col_booleana] == True]
    
    if not df_filtrado.empty:
        # Calculamos los estadísticos espaciales, transponemos a fila y asignamos el nombre limpio
        stats = df_filtrado['DIST_INTERSECCION_M'].describe().to_frame().T
        stats.index = [nombre_limpio]
        filas_stats.append(stats)

# Unimos las 4 filas resultantes en una sola tabla estructurada
stats_vehiculos = pd.concat(filas_stats)
stats_vehiculos.index.name = 'Clasificacion_Vehicular'

# Renombramos y convertimos a enteros puros
stats_vehiculos = stats_vehiculos.rename(columns={
    'count': 'Siniestros',
    'mean': 'Media_(m)',
    'std': 'Desvio_(m)',
    'min': 'Min_(m)',
    '25%': 'Q1_(m)',
    '50%': 'Mediana_(m)',
    '75%': 'Q3_(m)',
    'max': 'Max_(m)'
})
stats_vehiculos = stats_vehiculos.fillna(0).round(0).astype(int)

print("\n--- ESTADÍSTICOS ESPACIALES POR TIPO DE VEHÍCULO ---")
print(stats_vehiculos.to_string())

# 4. TABLA 3: Distribución de Clústeres (Ruido vs Puntos Negros)
conteo_clusters = gdf_final['CLUSTER_DBSCAN'].value_counts().to_frame().reset_index()
conteo_clusters.columns = ['ID_Punto_Negro', 'Cantidad_Siniestros']

# Reemplazamos el -1 por texto claro
conteo_clusters['ID_Punto_Negro'] = conteo_clusters['ID_Punto_Negro'].apply(
    lambda x: 'Ruido Espacial' if x == -1 else f'Clúster {x}'
)

print("\n--- RESUMEN DE CLÚSTERES (PUNTOS NEGROS VS RUIDO) ---")
print(conteo_clusters.to_string(index=False))