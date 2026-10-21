# import osmnx as ox
# import geopandas as gpd
# from shapely.ops import nearest_points
# from pathlib import Path

# def calcular_distancia_intersecciones(gdf: gpd.GeoDataFrame, dist_buffer: int = 1000) -> gpd.GeoDataFrame:
#     print("Iniciando cálculo de red vial...")
    
#     # --- FORZADO EXTREMO JUSTO ANTES DE USAR LA LIBRERÍA ---
#     # Sin el "/interpreter" al final, porque OSMnx se lo agrega automáticamente
#     ox.settings.overpass_endpoint = "https://overpass.kumi.systems/api"
#     ox.settings.timeout = 300
#     # -------------------------------------------------------

#     # Proyectar a UTM
#     gdf_proj = gdf.to_crs(epsg=5347)
#     bbox_union = gdf.union_all.envelope.buffer(0.05)
    
#     print(f"Límites de búsqueda: {bbox_union.bounds}")
#     print(f"Servidor actual de OSMnx: {ox.settings.overpass_endpoint}")

#     cache_path = Path("data/processed/grafo_red_vial.graphml")
    
#     if cache_path.exists():
#         print("Cargando grafo vial desde archivo local (caché)...")
#         G = ox.load_graphml(cache_path)
#     else:
#         print("Descargando red vial... esto puede tardar unos minutos.")
#         try:
#             # Intento 1: Kumi Systems
#             G = ox.graph_from_polygon(bbox_union, network_type='drive')
#         except Exception as e:
#             print("Falló Kumi Systems. Intentando con el servidor de Francia...")
#             # Intento 2: Francia
#             ox.settings.overpass_endpoint = "https://overpass.openstreetmap.fr/api"
#             G = ox.graph_from_polygon(bbox_union, network_type='drive')
            
#         cache_path.parent.mkdir(parents=True, exist_ok=True)
#         ox.save_graphml(G, cache_path)
#         print("Grafo descargado y guardado exitosamente.")
    
#     nodes, edges = ox.graph_to_gdfs(G)
#     intersecciones = nodes[nodes['street_count'] > 1].to_crs(gdf_proj.crs)

#     def get_min_distance(punto):
#         punto_cercano = nearest_points(punto, intersecciones.unary_union)[1]
#         return punto.distance(punto_cercano)

#     print("Calculando distancias para cada siniestro...")
#     gdf['DIST_INTERSECCION_M'] = gdf_proj.geometry.apply(get_min_distance)
    
#     return gdf

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from pyrosm import OSM
from shapely.ops import nearest_points

def extraer_red_local_pbf(gdf: gpd.GeoDataFrame, pbf_path: str = "data/raw/argentina-latest.osm.pbf") -> nx.MultiDiGraph:
    """
    Lee el archivo .pbf local y recorta solo la zona de interés usando los límites de los siniestros.
    """
    print("Calculando el área de influencia")
    # Obtener los límites geográficos exactos de tus 213 datos
    min_lon, min_lat, max_lon, max_lat = gdf.total_bounds
    
    # Le damos un pequeño margen (buffer) para no cortar intersecciones en el borde
    margen = 0.05 
    bbox = [min_lon - margen, min_lat - margen, max_lon + margen, max_lat + margen]

    print("Leyendo el archivo .pbf local")
    osm = OSM(pbf_path, bounding_box=bbox)

    print("Extrayendo la red vial (solo calles aptas para vehículos)...")
    nodes, edges = osm.get_network(network_type="driving", nodes=True)

    print("Convirtiendo a formato de grafo para análisis espacial...")
    G = osm.to_graph(nodes, edges, graph_type="networkx")
    
    # Guardamos el grafo ya recortado para no tener que volver a leer el .pbf
    ox.save_graphml(G, "data/processed/red_rn5_local.graphml")
    print("Grafo local generado y guardado con éxito.")
    
    return G


def calcular_distancia_intersecciones_local(gdf: gpd.GeoDataFrame, G: nx.MultiDiGraph) -> gpd.GeoDataFrame:
    """
    Calcula la distancia de cada siniestro a la intersección más cercana 
    utilizando el grafo generado localmente.
    """
    # Proyectamos a metros (EPSG:5347 es POSGAR 2007 para Argentina) para medir distancias reales
    gdf_proj = gdf.to_crs(epsg=5347) 
    
    # Extraer los nodos (esquinas/cruces) del grafo
    print("Extrayendo nodos del grafo...")
    nodes, _ = ox.graph_to_gdfs(G)
    nodes_proj = nodes.to_crs(gdf_proj.crs)

    nodes_proj['street_count'] = pd.to_numeric(nodes_proj['street_count'], errors='coerce').fillna(0)
    # Filtrar intersecciones reales (nodos donde se cruzan 2 o más calles)
    intersecciones = nodes_proj[nodes_proj['street_count'] > 1]

    def get_min_distance(punto):
        punto_cercano = nearest_points(punto, intersecciones.unary_union)[1]
        return punto.distance(punto_cercano)

    print("Calculando distancias a intersecciones (esto puede tomar unos segundos)...")
    gdf['DIST_INTERSECCION_M'] = gdf_proj.geometry.apply(get_min_distance)
    
    return gdf