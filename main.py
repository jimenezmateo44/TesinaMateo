import os
import networkx as nx
from shapely import wkt
import geopandas as gpd
from src.data_processing import cargar_y_limpiar_siniestros
from src.infrastructure import calcular_distancia_intersecciones_local, extraer_red_local_pbf
from src.spatial_analysis import identificar_puntos_negros
from src.visualization import construir_mapa_interactivo, generar_mapa_topologico

def run_pipeline():
    raw_path = os.path.join("data", "raw", "Siniestros_Tesis.xlsx")
    ruta_grafo = os.path.join("data", "processed", "red_rn5_local.graphml")
    output_html = os.path.join("data/outputs", "mapa_riesgo_interactivo.html")

    print("1/4 Procesando datos, coordenadas y variables operativas...")
    gdf = cargar_y_limpiar_siniestros(raw_path)


    print("2/4 Cargando grafo local de la red vial...")
 
    # #extraer_red_local_pbf
    # print("3. Iniciando extracción del mapa")
    # # Ejecutamos la función por primera vez
    # G = extraer_red_local_pbf(
    #     gdf=gdf, 
    #     pbf_path="data/raw/argentina-260909.osm.pbf"
    # )
    
    # Cargamos el grafo base
    G = nx.read_graphml(ruta_grafo, node_type=int)
    G = nx.MultiDiGraph(G)
    
   
    G.graph['crs'] = 'EPSG:4326'
    
    #Convertimos el texto plano de las calles de vuelta a geometrías espaciales
    for u, v, k, data in G.edges(keys=True, data=True):
        if 'geometry' in data and isinstance(data['geometry'], str):
            data['geometry'] = wkt.loads(data['geometry'])

    print("3/4 Calculando distancias topológicas a intersecciones...")
    gdf = calcular_distancia_intersecciones_local(gdf, G)

    print("4/4 Aplicando clustering DBSCAN y generando visualización...")
    gdf = identificar_puntos_negros(gdf, eps_km=3.0, min_samples=3)
    construir_mapa_interactivo(gdf, output_html)
    
    # Guardamos los resultados finales
    processed_path = os.path.join("data", "processed", "siniestros_analizados_final.geojson")
    gdf.to_file(processed_path, driver="GeoJSON")
    print("¡Pipeline finalizado con éxito!")

    
    # Lectura del archivo del archivo que ya tiene las distancias calculadas
    ruta_datos = "data/processed/siniestros_analizados_final.geojson"
    gdf_final = gpd.read_file(ruta_datos)
    
    # 3. Ejecutás la función pasándole el GeoDataFrame
    generar_mapa_topologico(gdf_final, ruta_salida="mapa_interactivo_rn5.html")
    
    print("Ejecución finalizada.")

    
if __name__ == "__main__":
    run_pipeline()