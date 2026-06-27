import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from sklearn.cluster import KMeans
import numpy as np

st.set_page_config(page_title="Tucker Dynamic Logistics Router", layout="wide")
st.title("🇹🇹 Tucker Energy Services - Dynamic Transport Router")
st.markdown("---")

# 1. FIXED CORPORATE FACILITY COORDINATES
FACILITIES = {
    "San Fernando (Base)": {"lat": 10.2795, "lon": -61.4542},
    "TESL Wireline Division (San Fernando)": {"lat": 10.2748, "lon": -61.4645},
    "TESL Head Office (Port of Spain)": {"lat": 10.6548, "lon": -61.5162},
    "TESL Chaguaramas Service Centre": {"lat": 10.6811, "lon": -61.6295},
    "Cronstadt Island Facility": {"lat": 10.6552, "lon": -61.6310},
    "TESL Guapo Facility": {"lat": 10.1983, "lon": -61.6421},
    "Point Fortin (Atlantic LNG)": {"lat": 10.1818, "lon": -61.6781},
    "Point Lisas Industrial Estate": {"lat": 10.3952, "lon": -61.4795},
    "Galeota Point / Mayaro Terminal": {"lat": 10.1415, "lon": -61.0112},
    "Chaguanas Hub": {"lat": 10.5167, "lon": -61.4111},
    "Arima Area": {"lat": 10.6385, "lon": -61.2825},
    "Sangre Grande": {"lat": 10.5833, "lon": -61.1167},
}
BASE_COORDS = FACILITIES["San Fernando (Base)"]

# 2. INITIALIZE LIVE SESSION DATABASE
if "job_queue" not in st.session_state:
    st.session_state.job_queue = []

# 3. SIDEBAR CONTROLS
st.sidebar.header("🚚 Fleet Status")
available_trucks = st.sidebar.slider("Active Trucks Today", min_value=1, max_value=10, value=4)

st.sidebar.markdown("---")
st.sidebar.header("📍 Log New Transport Request")

# Job input form
with st.sidebar.form(key="job_form", clear_on_submit=True):
    equipment = st.text_input("Equipment Description", placeholder="e.g., Wireline Toolstring, Pumping Manifold")
    pickup = st.selectbox("Pick-up Location", options=list(FACILITIES.keys()))
    dropoff = st.selectbox("Drop-off Location", options=list(FACILITIES.keys()))
    priority = st.selectbox("Urgency", ["Normal Routine", "🚨 LAST MINUTE / URGENT"])
    
    submit_job = st.form_submit_button(label="Add Job to Queue")
    
    if submit_job:
        if pickup == dropoff:
            st.error("Pick-up and Drop-off cannot be the same location.")
        elif not equipment:
            st.error("Please enter an equipment description.")
        else:
            # Append new job to live session list
            new_job = {
                "id": len(st.session_state.job_queue) + 1,
                "equipment": equipment,
                "pickup": pickup,
                "dropoff": dropoff,
                "priority": priority,
                "status": "Pending Dispatch"
            }
            st.session_state.job_queue.append(new_job)
            st.success(f"Added: {equipment}")

# Clear board function
if st.sidebar.button("🗑️ Clear Entire Board for New Day"):
    st.session_state.job_queue = []
    st.rerun()

# 4. DISPLAY LIVE JOB QUEUE TABLE
st.subheader("📋 Active Job Queue")
if not st.session_state.job_queue:
    st.info("No jobs logged yet. Use the sidebar menu to log morning runs or add last-minute day requests.")
else:
    df_queue = pd.DataFrame(st.session_state.job_queue)
    st.dataframe(df_queue, use_container_width=True, hide_index=True)
    
    # 5. OPTIMIZATION AND ROUTING MATH
    st.markdown("---")
    
    # Extract unique locations involved in today's pending jobs to perform clustering
    active_jobs = st.session_state.job_queue
    
    # Calculate geographical routing
    coordinates = []
    job_mapping = []
    
    for idx, job in enumerate(active_jobs):
        # We grab coordinates for the pickup point to decide which truck handles the zone
        p_coords = FACILITIES[job["pickup"]]
        coordinates.append([p_coords["lat"], p_coords["lon"]])
        job_mapping.append(idx)
        
    if coordinates:
        num_clusters = min(available_trucks, len(coordinates))
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10).fit(coordinates)
        labels = kmeans.labels_
        
        truck_assignments = {f"Truck {i+1}": [] for i in range(num_clusters)}
        for job_idx, label in zip(job_mapping, labels):
            truck_assignments[f"Truck {label+1}"].append(active_jobs[job_idx])
            
        # UI Columns
        col1, col2 = st.columns([2, 1])
        
        with col2:
            st.subheader("🏁 Live Dispatch Manifest")
            for truck, jobs in truck_assignments.items():
                # Visual separator if a last-minute hot job is inside
                has_urgent = any(j["priority"] == "🚨 LAST MINUTE / URGENT" for j in jobs)
                
                if has_urgent:
                    st.error(f"⚡ **{truck}** - Modified Route (Urgent Job Attached!)")
                else:
                    st.subheader(f"🚛 {truck}")
                    
                st.write("📍 **Sequence:**")
                st.write("🏠 *Depart:* San Fernando (Base)")
                
                for j in jobs:
                    marker_prefix = "⚡ [URGENT] " if j["priority"] == "🚨 LAST MINUTE / URGENT" else ""
                    st.write(f" 📦 **Pick up:** {marker_prefix}{j['equipment']} @ *{j['pickup']}*")
                    st.write(f" 🏁 **Drop off:** {j['equipment']} @ *{j['dropoff']}*")
                st.write("🏠 *Return:* San Fernando (Base)")
                st.markdown("---")
                
        with col1:
            st.subheader("🗺️ Live Route Monitoring")
            m = folium.Map(location=[10.4, -61.3], zoom_start=10, tiles="CartoDB positron")
            
            # Base Marker
            folium.Marker(
                location=[BASE_COORDS["lat"], BASE_COORDS["lon"]],
                popup="<b>MAIN PUMPING BASE</b>",
                icon=folium.Icon(color="red", icon="home", prefix="fa")
            ).add_to(m)
            
            colors = ['blue', 'green', 'orange', 'purple', 'cadetblue', 'darkred', 'pink', 'gray']
            
            for truck_idx, (truck, jobs) in enumerate(truck_assignments.items()):
                truck_color = colors[truck_idx % len(colors)]
                route_points = [[BASE_COORDS["lat"], BASE_COORDS["lon"]]]
                
                for j in jobs:
                    p_loc = FACILITIES[j["pickup"]]
                    d_loc = FACILITIES[j["dropoff"]]
                    
                    route_points.append([p_loc["lat"], p_loc["lon"]])
                    route_points.append([d_loc["lat"], d_loc["lon"]])
                    
                    # Map pin flags
                    folium.Marker(
                        location=[p_loc["lat"], p_loc["lon"]],
                        popup=f"Pick up: {j['equipment']} ({truck})",
                        icon=folium.Icon(color=truck_color, icon="arrow-up", prefix="fa")
                    ).add_to(m)
                    
                    folium.Marker(
                        location=[d_loc["lat"], d_loc["lon"]],
                        popup=f"Drop off: {j['equipment']} ({truck})",
                        icon=folium.Icon(color=truck_color, icon="flag", prefix="fa")
                    ).add_to(m)
                    
                route_points.append([BASE_COORDS["lat"], BASE_COORDS["lon"]])
                
                folium.PolyLine(
                    locations=route_points,
                    color=truck_color,
                    weight=4,
                    opacity=0.75
                ).add_to(m)
                
            st_folium(m, width=800, height=600, returned_objects=[])
