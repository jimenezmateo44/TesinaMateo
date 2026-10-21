import numpy as np
import geopandas as gpd
from sklearn.cluster import DBSCAN

def identificar_puntos_negros(gdf: gpd.GeoDataFrame, eps_km: float = 2.5, min_samples: int = 3) -> gpd.GeoDataFrame:
    """
    Agrupa los siniestros utilizando DBSCAN con métrica Haversine.
    - eps_km: Radio de búsqueda en kilómetros (ej. 2.5 km).
    - min_samples: Mínimo de siniestros para considerarlo tramo crítico / clúster.
    """
    # Radio de la Tierra en kilómetros
    kms_per_radian = 6371.0088
    epsilon = eps_km / kms_per_radian

    # Coordenadas en radianes para Haversine (lat, lon)
    coords = np.radians(gdf[['LAT', 'LON']].to_numpy())

    db = DBSCAN(eps=epsilon, min_samples=min_samples, metric='haversine', algorithm='ball_tree')
    gdf['CLUSTER_DBSCAN'] = db.fit_predict(coords)

    # Cluster -1 indica ruido (siniestro aislado fuera de puntos críticos)
    gdf['ES_PUNTO_NEGRO'] = gdf['CLUSTER_DBSCAN'] != -1
    return gdf