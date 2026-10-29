import folium
from folium.plugins import HeatMap
import geopandas as gpd
import pandas as pd

def construir_mapa_interactivo(gdf: gpd.GeoDataFrame, output_path: str):
    print("Generando mapa interactivo final (DBSCAN + Topología)...")
    
    centro_lat = gdf['LAT'].mean()
    centro_lon = gdf['LON'].mean()


    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=8, tiles='OpenStreetMap')

    # 1. CAPA: HeatMap (Densidad / KDE)
    fg_heat = folium.FeatureGroup(name="Superficie de Densidad (KDE)", show=True)
    heat_data = [[row['LAT'], row['LON']] for _, row in gdf.iterrows()]
    HeatMap(heat_data, radius=18, blur=12, max_zoom=10).add_to(fg_heat)
    fg_heat.add_to(m)

    # 2. CAPA: Puntos Críticos (DBSCAN) - TU LÓGICA ORIGINAL
    fg_clusters = folium.FeatureGroup(name="Puntos Críticos Detectados (DBSCAN)", show=True)
    
    # 3. CAPA: Topología (Nodos y Distancias) - NUEVA CAPA
    fg_topologia = folium.FeatureGroup(name="Nodos y Distancias Topológicas", show=False)

    for _, row in gdf.iterrows():
        color = 'red' if row.get('ES_PUNTO_NEGRO', False) else 'blue'
        radius = 6 if row.get('ES_PUNTO_NEGRO', False) else 4

        info_html = f"""
        <div style="font-family: Arial; font-size: 11px;">
            <b>KM:</b> {row.get('KM', 'S/D')}<br>
            <b>Vehículo:</b> {row.get('VEHICULO INVOLUCRADO', 'S/D')}<br>
            <b>Tipo de accidente:</b> {row.get('TIPO DE ACCIDENTE', 'S/D')}<br>
            <b>Condición víctima:</b> {row.get('CONDICION VICTIMA', 'S/D')}<br>
        </div>
        """
        
        has_nodo = pd.notna(row.get('LAT_NODO')) and pd.notna(row.get('LON_NODO'))
        distancia = round(row['DIST_INTERSECCION_M'], 1) if has_nodo and 'DIST_INTERSECCION_M' in row else None
        

        tooltip_accidente = f"<b>Siniestro:</b> {row.get('TIPO DE ACCIDENTE', 'N/D')}"
        if distancia is not None:
            tooltip_accidente += f"<br><b>Distancia a nodo:</b> {int(distancia)} m"

        folium.CircleMarker(
            location=[row['LAT'], row['LON']],
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(info_html, max_width=250),
            tooltip=tooltip_accidente
        ).add_to(fg_clusters)

    
        if has_nodo:
            coord_nodo = [row['LAT_NODO'], row['LON_NODO']]
            
            # Nodo azul de intersección
            folium.CircleMarker(
                location=coord_nodo,
                radius=5,
                color="#0b9422",
                fill=True,
                fill_color="#16940b",
                fill_opacity=0.9,
            ).add_to(fg_topologia)
            

    # Añadimos las capas extra al mapa
    fg_clusters.add_to(m)
    fg_topologia.add_to(m)

    # Control de capas interactivo (permite tildar/destildar)
    folium.LayerControl(collapsed=False).add_to(m)

    m.save(output_path)
    print(f"Mapa interactivo unificado guardado exitosamente en: {output_path}")

    return m