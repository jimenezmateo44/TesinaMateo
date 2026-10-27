import geopandas as gpd
import networkx as nx
from pyrosm import OSM


def extraer_red_local_pbf(gdf: gpd.GeoDataFrame, pbf_path: str = "data/raw/argentina-260909.osm.pbf") -> nx.MultiDiGraph:

    # Lee el archivo .pbf local y recorta solo la zona de interés usando los límites de los siniestros.
    # Incluye limpieza exhaustiva para compatibilidad de exportación a Gephi.

    print("Calculando el área de influencia")
    min_lon, min_lat, max_lon, max_lat = gdf.total_bounds
    
    margen = 0.05 
    bbox = [min_lon - margen, min_lat - margen, max_lon + margen, max_lat + margen]

    print("Leyendo el archivo .pbf local")
    osm = OSM(pbf_path, bounding_box=bbox)

    print("Extrayendo la red vial (solo calles aptas para vehículos)...")
    nodes, edges = osm.get_network(network_type="driving", nodes=True)

    print("Convirtiendo a formato de grafo para análisis espacial...")
    G = osm.to_graph(nodes, edges, graph_type="networkx")
    
    print("Limpiando geometrías, listas y forzando lat/lon para Gephi...")
    # Limpieza de Nodos
    for nodo, datos in list(G.nodes(data=True)):
        if 'y' in datos and 'x' in datos:
            datos['lat'] = float(datos['y'])
            datos['lon'] = float(datos['x'])
        
        if 'geometry' in datos:
            del datos['geometry']
            
        for key, val in datos.items():
            if type(val) in [list, dict]:
                datos[key] = str(val)

    # Limpieza de Aristas
    for u, v, k, datos in list(G.edges(data=True, keys=True)):
        if 'geometry' in datos:
            del datos['geometry']
        for key, val in datos.items():
            if type(val) in [list, dict]:
                datos[key] = str(val)

    print("Exportando versión simple para Gephi...")
    
    return G

