import folium
from folium.plugins import HeatMap
import geopandas as gpd

def construir_mapa_interactivo(gdf: gpd.GeoDataFrame, output_path: str):
    """Crea un mapa HTML con capas de calor y puntos con pop-up."""
    centro_lat = gdf['LAT'].mean()
    centro_lon = gdf['LON'].mean()

    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=8, tiles='OpenStreetMap')

    # 1. Capa HeatMap (Densidad / KDE)
    fg_heat = folium.FeatureGroup(name="Superficie de Densidad (KDE)", show=True)
    heat_data = [[row['LAT'], row['LON']] for _, row in gdf.iterrows()]
    HeatMap(heat_data, radius=18, blur=12, max_zoom=10).add_to(fg_heat)
    fg_heat.add_to(m)

    # 2. Capa Puntos Críticos (DBSCAN)
    fg_clusters = folium.FeatureGroup(name="Puntos Críticos Detectados", show=True)
    
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
        
        folium.CircleMarker(
            location=[row['LAT'], row['LON']],
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(info_html, max_width=250)
        ).add_to(fg_clusters)

    fg_clusters.add_to(m)

    # Control de capas interactivo
    folium.LayerControl(collapsed=False).add_to(m)

    m.save(output_path)
    print(f"Mapa interactivo guardado exitosamente en: {output_path}")