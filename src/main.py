import streamlit as st
from streamlit_folium import st_folium
import requests
import folium
import matplotlib.cm as cm
import matplotlib.colors as colors
import branca.colormap as cm_branca
import json

# Streamlit app title and description
st.title("San Miguel Zoning Map")
st.markdown(
    "Interactive map showing maximum building heights by zone in San Miguel, Buenos Aires, Argentina."
)

# Zone to max height dictionary with numeric values
zone_max_height = {
    "Mi1": 14,
    "Mi21": 12,
    "Mi22": 10,
    "Mi23": 8,
    "Mi24": 6,
    "Ma": 7,
    "C1": 3,
    "C2": 3,
    "C3": 4,
    "Rmi": 2,
    "Rme": 2,
    "Rma": 2,
    "Rma2": 2,
    "ZIN": 2,
    "ZUE": 5,
    "ZDUP1": 9,
    "ZDUP2": 5,
    "ZDUP3": 3,
    "UE7": 5,
    "UE8": 3,
}


# Function to get color based on height using a continuous color scale
def get_color(height, min_height=1, max_height=14):
    try:
        height = int(height)  # Ensure height is an integer
        norm = colors.Normalize(vmin=min_height, vmax=max_height)
        colormap = cm.get_cmap("YlOrRd")  # Yellow (low) to Red (high)
        rgba = colormap(norm(height))
        return colors.rgb2hex(rgba)
    except:
        return "#808080"  # Gray for invalid/unknown heights


# Fetch GeoJSON
@st.cache_data
def fetch_geojson():
    url = "https://mapas.msm.gov.ar/arcgis/rest/services/geos_paquetes/uso_suelo/MapServer/1/query?where=1%3D1&outFields=*&f=geojson&returnGeometry=true"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for bad status codes
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching GeoJSON data: {e}")
        return None


geojson_data = fetch_geojson()

# Debug: Inspect GeoJSON structure
if geojson_data:
    st.write("GeoJSON fetched successfully. Structure overview:")
    st.write(f"GeoJSON type: {geojson_data.get('type', 'Unknown')}")
    st.write(f"Number of features: {len(geojson_data.get('features', []))}")
    if geojson_data.get("features"):
        st.write(
            "Sample feature properties:",
            geojson_data["features"][0].get("properties", {}),
        )
        if geojson_data["features"][0].get("properties"):
            st.write(
                "Available fields in properties:",
                list(geojson_data["features"][0]["properties"].keys()),
            )
        else:
            st.error("No properties found in GeoJSON features.")
else:
    st.error(
        "No GeoJSON data fetched. Please check the URL or provide a local GeoJSON file."
    )
    geojson_data = {"type": "FeatureCollection", "features": []}

# Interactive filter: Slider for maximum height
st.sidebar.header("Filter Zones by Max Height")
min_height = st.sidebar.slider(
    "Minimum Height (Floors)", min_value=1, max_value=14, value=1
)
max_height = st.sidebar.slider(
    "Maximum Height (Floors)", min_value=1, max_value=14, value=14
)

# Create Folium map
m = folium.Map(location=[-34.543, -58.712], zoom_start=13, tiles="OpenStreetMap")

# Process GeoJSON features
filtered_features = []
available_fields = ["nombre", "altura_maxima"]  # Default fields for tooltip
if geojson_data["features"] and geojson_data["features"][0].get("properties"):
    available_fields = [
        f
        for f in ["codigo", "CODIGO", "nombre", "altura_maxima"]
        if f in geojson_data["features"][0]["properties"]
    ]
    for feature in geojson_data["features"]:
        properties = feature.get("properties", {})
        zone_code = properties.get("codigo", properties.get("CODIGO", ""))
        height_str = properties.get("altura_maxima", "")
        try:
            if height_str:
                if "PB" in height_str:
                    height = (
                        int(height_str.split("+")[1].strip()) + 1
                    )  # Include PB as ground
                else:
                    height = int(height_str)
            else:
                height = zone_max_height.get(zone_code, 1)  # Fallback to dictionary
        except:
            height = zone_max_height.get(zone_code, 1)  # Fallback to dictionary or 1

        if min_height <= height <= max_height:
            filtered_features.append(feature)
else:
    st.warning("No valid features to display. Using empty GeoJSON.")

filtered_geojson = {"type": "FeatureCollection", "features": filtered_features}

# Add GeoJSON layer with color scale
folium.GeoJson(
    filtered_geojson,
    style_function=lambda feature: {
        "fillColor": get_color(
            zone_max_height.get(
                feature["properties"].get(
                    "codigo", feature["properties"].get("CODIGO", "")
                ),
                feature["properties"].get("altura_maxima", 1),
            )
        ),
        "color": "black",
        "weight": 1,
        "fillOpacity": 0.6,
    },
    tooltip=(
        folium.GeoJsonTooltip(
            fields=available_fields,
            aliases=[
                f.replace("CODIGO", "Zone Code")
                .replace("codigo", "Zone Code")
                .replace("nombre", "Zone Name")
                .replace("altura_maxima", "Max Height")
                for f in available_fields
            ],
            localize=True,
        )
        if available_fields
        else None
    ),
).add_to(m)

# Add color scale legend
colormap = cm_branca.LinearColormap(
    colors=[
        "#FFFFCC",
        "#FFEDA0",
        "#FED976",
        "#FEB24C",
        "#FD8D3C",
        "#FC4E2A",
        "#E31A1C",
        "#B10026",
    ],
    vmin=min_height,
    vmax=max_height,
    caption="Maximum Building Height (Floors)",
)
m.add_child(colormap)

# Render map in Streamlit
st_folium(m, width=700, height=500)
