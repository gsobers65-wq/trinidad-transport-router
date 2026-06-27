import streamlit as tf
import pandas as pd
import folium
from streamlit_folium import st_folium
from sklearn.cluster import KMeans
import numpy as np

# Set up page config
st.set_page_config(page_title="Trinidad Transport Router", layout="wide")

st.title("🇹🇹 Trinidad Transport Logistics Router")
st.markdown("---")

# 1. DEFINE GEOGRAPHIC DATA MATRIX (Trinidad Hubs)
# Base coordinates set to San Fernando
BASE_COORDS = (10.2741, -61.4583) # San Fernando

LOCATIONS = {
    "San Fernando (Base)": {"lat": 10.2741, "lon": -61.4583},
    "Point Lisas Industrial Estate": {"lat": 10.3952, "lon": -61.4795},
    "Port of Spain Port": {"lat": 10.6520, "lon": -61.5170},
    "Chaguaramas": {"lat": 10.6830, "lon": -61.6331},
    "Arima": {"lat": 10.6385, "lon": -61.2825},
    "Caroni / Chaguanas": {"lat": 10.5167, "lon": -61.4111},
    "Point Fortin (Atlantic LNG)": {"lat": 10.1818, "lon": -61.6781},
    "Siparia": {"lat": 10.1333, "lon": -61.5000},
    "Fyzabad": {"lat": 10.1770, "lon": -61.5451},
    "Princes Town": {"lat": 10.2667, "lon": -61.3833},
    "Mayaro / Galeota Point": {"lat": 10.1415, "lon": -61.0112},
    "Sangre Grande": {"lat": 10.5833, "lon": -61.1167},
    "Guayaguayare": {"lat": 10.1333, "lon": -61.0333},
}

# 2. SIDEBAR - COORDINATOR INPUTS
st.sidebar.header("🚚 Dispatch Controls")

available_trucks = st.sidebar.slider("Number of Available Trucks Today", min_value=1, max_value=8, value=3)
max_stops = st.sidebar.slider("Max Allowed Stops per Truck", min_value=1, max_value=4, value=2)

st.sidebar.subheader("📍 Select Today's Job Locations")
selected_locs = []
for loc in LOCATIONS.keys():
    if loc == "San Fernando (Base)":
        continue # Base is mandatory, don't checkbox it
    if st.sidebar.checkbox(loc, value=False):
        selected_locs.append(loc)

# 3. ROUTING & CLUSTERING LOGIC
if st.sidebar.button("🚀 Optimize Routes & Assign Trucks"):
    if not selected_locs:
        st.warning("Please select at least one job location from the sidebar.")
    else:
        st.subheader("📋 Optimized Dispatch Plan")
        
        # Prepare coordinates for clustering
        coordinates = np.array([[LOCATIONS[l]["lat"], LOCATIONS[l]["lon"]] for l in selected_locs])
        
        # Determine optimal number of clusters (cannot exceed number of selected locations or available trucks)
        num_clusters = min(available_trucks, len(selected_locs))
        
        # Run KMeans to cluster geographically close locations together
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10).fit(coordinates)
        labels = kmeans.labels_
        
        # Organize jobs by truck
        truck_assignments = {f"Truck {i+1}": [] for i in range(num_clusters)}
        for loc, label in zip(selected_locs, labels):
            truck_assignments[f"Truck {label+1}"].append(loc)
            
        # Color palette for map visualization
        colors = ['blue', 'green', 'orange', 'purple', 'cadetblue', 'darkred', 'pink', 'gray']
        
        # Create Layout Columns: Left for Map, Right for Text Summary
        col1, col2 = st.columns([2, 1])
        
        with col2:
            st.info("💡 **Routing Summary**")
            for truck, jobs in truck_assignments.items():
                if len(jobs) > max_stops:
                    # Split if it exceeds the coordinator's maximum stops rule
                    st.error(f"⚠️ **{truck}** overloaded! Needs {len(jobs)} stops. Consider adding more trucks.")
                
                st.write(f"**{truck}:**")
                st.write(f"🚩 *Start:* San Fernando (Base)")
                for idx, job in enumerate(jobs, 1):
                    st.write(f" ➡️ **Stop {idx}:** {job}")
                st.write(f" ➡️ *Return:* San Fernando (Base)")
                st.markdown("---")
                
        with col1:
            # Build the interactive Map
            m = folium.Map(location=[10.4, -61.3], zoom_start=10, tiles="CartoDB positron")
            
            # Draw Base Location (San Fernando)
            folium.Marker(
                location=BASE_COORDS,
                popup="<b>CENTRAL BASE: San Fernando</b>",
                icon=folium.Icon(color="red", icon="home", prefix="fa")
            ).add_to(m)
            
            # Draw routes and drop-off markers
            for truck_idx, (truck, jobs) in enumerate(truck_assignments.items()):
                truck_color = colors[truck_idx % len(colors)]
                
                # We start a line string path tracking: Base -> Jobs -> Base
                route_points = [BASE_COORDS]
                
                for job in jobs:
                    job_coords = (LOCATIONS[job]["lat"], LOCATIONS[job]["lon"])
                    route_points.append(job_coords)
                    
                    # Add job marker
                    folium.Marker(
                        location=job_coords,
                        popup=f"<b>{job}</b><br>Assigned to: {truck}",
                        icon=folium.Icon(color=truck_color, icon="truck", prefix="fa")
                    ).add_to(m)
                    
                route_points.append(BASE_COORDS) # Loop back to base
                
                # Draw the driving path line on the map
                folium.PolyLine(
                    locations=route_points,
                    color=truck_color,
                    weight=4,
                    opacity=0.7,
                    tooltip=f"Route Path for {truck}"
                ).add_to(m)
            
            # Display map in Streamlit layout
            st_folium(m, width=800, height=600, returned_objects=[])

else:
    # Default State when app first opens
    st.info("👈 Select available trucks and checked job destinations on the left sidebar, then click 'Optimize Routes'.")
    
    # Show an empty layout map centered on Trinidad
    m = folium.Map(location=[10.4, -61.3], zoom_start=10, tiles="CartoDB positron")
    folium.Marker(location=BASE_COORDS, popup="San Fernando Base", icon=folium.Icon(color="red", icon="home")).add_to(m)
    st_folium(m, width=800, height=500, returned_objects=[])
