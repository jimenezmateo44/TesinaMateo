import geopandas as gpd
import networkx as nx
from pyrosm import OSM
from shapely.ops import nearest_points
import osmnx as ox
import pandas as pd
import warnings


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

# Silenciamos advertencias de deprecación para mantener limpia la consola
warnings.filterwarnings('ignore', category=FutureWarning)

def unir_geometrias(geoms):
    """
    Función auxiliar universal: unifica geometrías sin importar 
    si tenés Shapely 1.x o Shapely 2.x instalado.
    """
    if geoms is None or (hasattr(geoms, 'empty') and geoms.empty):
        return None
    try:
        from shapely import union_all
        return union_all(geoms)
    except (ImportError, AttributeError):
        if hasattr(geoms, 'unary_union'):
            return geoms.unary_union
        from shapely.ops import unary_union
        return unary_union(geoms)

def calcular_distancia_intersecciones_local(gdf: gpd.GeoDataFrame, G) -> gpd.GeoDataFrame:
    """
    Calcula la distancia a la intersección más cercana utilizando un cruce 
    GEOMÉTRICO puro totalmente compatible con cualquier versión de Shapely.
    """
    # Proyectamos a metros (EPSG:5347 POSGAR 2007 para Argentina)
    gdf_proj = gdf.to_crs(epsg=5347) 
    
    print("Extrayendo aristas para cálculo geométrico...")
    nodes, edges = ox.graph_to_gdfs(G)
    edges_proj = edges.to_crs(gdf_proj.crs)

    if 'name' not in edges_proj.columns: edges_proj['name'] = ''
    if 'ref' not in edges_proj.columns: edges_proj['ref'] = ''
    if 'highway' not in edges_proj.columns: edges_proj['highway'] = ''
        
    name_str = edges_proj['name'].astype(str).str.upper()
    ref_str = edges_proj['ref'].astype(str).str.upper()
    hwy_str = edges_proj['highway'].astype(str).str.upper()
    
    # Identificamos el trazado de la Ruta Nacional 5
    mask_rn5 = (
        name_str.str.contains("RUTA NACIONAL 5|RUTA 5|RN5|RN 5", na=False) |
        ref_str.str.contains("RN5|RN 5", na=False) |
        hwy_str.str.contains("TRUNK", na=False)
    )
    
    print("Separando la Ruta 5 de la red secundaria...")
    aristas_rn5 = edges_proj[mask_rn5]
    aristas_otras = edges_proj[~mask_rn5]
    
    print("Calculando cruces geométricos exactos...")
    linea_rn5 = unir_geometrias(aristas_rn5.geometry)
    linea_otras = unir_geometrias(aristas_otras.geometry)
    
    cruces_geom = linea_rn5.intersection(linea_otras)
    
    puntos_cruce = []
    def extraer_puntos(geom):
        if geom is None or geom.is_empty:
            return
        if geom.geom_type == 'Point':
            puntos_cruce.append(geom)
        elif geom.geom_type == 'MultiPoint':
            puntos_cruce.extend(list(geom.geoms))
        elif geom.geom_type in ['GeometryCollection', 'MultiLineString', 'MultiPolygon']:
            for g in geom.geoms:
                extraer_puntos(g)
                
    extraer_puntos(cruces_geom)
    intersecciones = gpd.GeoSeries(puntos_cruce, crs=gdf_proj.crs)
    
    if intersecciones.empty:
        intersecciones_final = gpd.GeoSeries([], crs=gdf_proj.crs)
    else:
        # Buffer de 15m para consolidar rotondas y cruces dobles
        union_geom = unir_geometrias(intersecciones.buffer(15))
        
        puntos_finales = []
        if hasattr(union_geom, 'geom_type'):
            if union_geom.geom_type == 'Polygon':
                puntos_finales.append(union_geom.centroid)
            elif union_geom.geom_type == 'MultiPolygon':
                puntos_finales.extend([poly.centroid for poly in union_geom.geoms])
            elif union_geom.geom_type == 'GeometryCollection':
                for g in union_geom.geoms:
                    if g.geom_type == 'Polygon':
                        puntos_finales.append(g.centroid)
                    elif g.geom_type == 'MultiPolygon':
                        puntos_finales.extend([poly.centroid for poly in g.geoms])
                        
        intersecciones_final = gpd.GeoSeries(puntos_finales, crs=gdf_proj.crs)

    intersec_union = unir_geometrias(intersecciones_final.geometry) if not intersecciones_final.empty else None

    def get_nearest_info(punto):
        if intersec_union is None or intersec_union.is_empty:
            return pd.Series([None, None, None])
        punto_cercano = nearest_points(punto, intersec_union)[1]
        distancia = punto.distance(punto_cercano)
        return pd.Series([distancia, punto_cercano.x, punto_cercano.y])

    print(f"Se detectaron {len(intersecciones_final)} intersecciones físicas. Midiendo distancias...")
    
    gdf[['DIST_INTERSECCION_M', 'X_NODO_PROJ', 'Y_NODO_PROJ']] = gdf_proj.geometry.apply(get_nearest_info)
    
    nodos_geom = gpd.points_from_xy(gdf['X_NODO_PROJ'], gdf['Y_NODO_PROJ'], crs=5347)
    nodos_wgs84 = gpd.GeoSeries(nodos_geom).to_crs(4326)
    
    gdf['LON_NODO'] = nodos_wgs84.x
    gdf['LAT_NODO'] = nodos_wgs84.y
    gdf = gdf.drop(columns=['X_NODO_PROJ', 'Y_NODO_PROJ'])
    
    return gdf