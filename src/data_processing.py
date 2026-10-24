import re
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

def dms_a_decimal(dms_str: str) -> float:
    #Convierte un string en formato Grados, Minutos, Segundos a grados decimales.
    if pd.isna(dms_str):
        return None
    dms_str = str(dms_str).strip()
    
    try:
        return float(dms_str)
    except ValueError:
        pass

    partes = re.findall(r"[-+]?\d*\.\d+|\d+", dms_str)
    if not partes:
        return None

    grados = float(partes[0])
    minutos = float(partes[1]) if len(partes) > 1 else 0.0
    segundos = float(partes[2]) if len(partes) > 2 else 0.0

    decimal = abs(grados) + (minutos / 60.0) + (segundos / 3600.0)
    
    if any(c in dms_str.upper() for c in ['S', 'W', 'O']) or grados < 0:
        decimal = -decimal

    return decimal

def procesar_tipos_vehiculos(df):
    #Genera variables booleanas basadas en los vehículos y el entorno.
    df['VEHICULO INVOLUCRADO'] = df['VEHICULO INVOLUCRADO'].astype(str).str.upper().str.strip()
    
    # 1. Identificar actores clave
    df['PARTICIPA_CAMION'] = df['VEHICULO INVOLUCRADO'].str.contains('CAMION').astype(bool)
    df['PARTICIPA_MOTO'] = df['VEHICULO INVOLUCRADO'].str.contains('MOTOCICLETA').astype(bool)
    df['PARTICIPA_AUTO'] = df['VEHICULO INVOLUCRADO'].str.contains('AUTOMOVIL').astype(bool)
    df['PARTICIPA_CAMIONETA'] = df['VEHICULO INVOLUCRADO'].str.contains('CAMIONETA').astype(bool)
    
    # 2. Identificar impactos contra INFRAESTRUCTURA (Objetos fijos)
    objetos_fijos = ['ARBOL', 'GUARDARRAIL']
    patron_fijos = '|'.join(objetos_fijos)
    df['CONTRA_OBJETO_FIJO'] = df['VEHICULO INVOLUCRADO'].str.contains(patron_fijos).astype(bool)
    
    # 3. Corregir Choque Múltiple
    tiene_guion = df['VEHICULO INVOLUCRADO'].str.contains('-')
    df['CHOQUE_MULTIPLE'] = tiene_guion & ~df['CONTRA_OBJETO_FIJO']
    
    return df

def cargar_y_limpiar_siniestros(filepath: str) -> gpd.GeoDataFrame:
    #Carga el Excel, limpia coordenadas, genera el GeoDataFrame y clasifica vehículos
    df = pd.read_excel(filepath)
    df.columns = [col.strip().upper() for col in df.columns]

    if 'LATITUD' in df.columns and 'LONGITUD' in df.columns:
        df['LAT'] = df['LATITUD'].apply(dms_a_decimal)
        df['LON'] = df['LONGITUD'].apply(dms_a_decimal)
    elif 'COORDENADAS' in df.columns:
# 1. Extraemos latitud (grupo 0) y longitud (grupo 1) basándonos en el espacio que las separa
        coords = df['COORDENADAS'].astype(str).str.extract(r'^(.*?)\s+([^ ]+)$')

        # 2. Aplicamos la conversión asegurándonos de que las columnas 0 y 1 existan
        df['LAT'] = coords[0].apply(dms_a_decimal)
        df['LON'] = coords[1].apply(dms_a_decimal)
    else:
        raise KeyError("No se detectaron columnas de coordenadas válidas.")

    df_geo = df.dropna(subset=['LAT', 'LON']).copy()

    geometry = [Point(xy) for xy in zip(df_geo['LON'], df_geo['LAT'])]
    gdf = gpd.GeoDataFrame(df_geo, geometry=geometry, crs="EPSG:4326")

    # Aplicamos la limpieza de vehículos acá, antes de devolver los datos
    gdf = procesar_tipos_vehiculos(gdf)

    return gdf  