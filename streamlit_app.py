import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Smart Storage Dashboard", layout="wide")

st.title("Smart Storage Dashboard")
st.write("IoT-inspired unit tracking prototype for storage visibility and packing support")

if "units" not in st.session_state:
    st.session_state.units = pd.DataFrame([
        {"unit_id": "U001", "metal": "Steel",  "shelf": "A1", "status": "Stored",  "order_id": "O100"},
        {"unit_id": "U002", "metal": "Copper", "shelf": "A2", "status": "Stored",  "order_id": "O100"},
        {"unit_id": "U003", "metal": "Steel",  "shelf": "B1", "status": "Packed",  "order_id": "O101"},
        {"unit_id": "U004", "metal": "Brass",  "shelf": "C2", "status": "Missing", "order_id": "O102"},
        {"unit_id": "U005", "metal": "Steel",  "shelf": "B3", "status": "Stored",  "order_id": "O103"},
    ])

shelf_coords = {
    "A1": (0, 0), "A2": (0, 1), "A3": (0, 2),
    "B1": (1, 0), "B2": (1, 1), "B3": (1, 2),
    "C1": (2, 0), "C2": (2, 1), "C3": (2, 2)
}

st.sidebar.header("Simulated Gateway Update")

unit_id = st.sidebar.text_input("Unit ID", "U001")
metal = st.sidebar.selectbox("Metal", ["Steel", "Copper", "Brass", "Aluminum"])
shelf = st.sidebar.selectbox("Shelf", list(shelf_coords.keys()))
status = st.sidebar.selectbox("Status", ["Stored", "Packed", "Missing"])

if st.sidebar.button("Update Unit"):
    df = st.session_state.units.copy()

    if unit_id in df["unit_id"].values:
        df.loc[df["unit_id"] == unit_id, ["metal", "shelf", "status"]] = [metal, shelf, status]
    else:
        new_row = pd.DataFrame([{
            "unit_id": unit_id,
            "metal": metal,
            "shelf": shelf,
            "status": status,
            "order_id": "O999"
        }])
        df = pd.concat([df, new_row], ignore_index=True)

    st.session_state.units = df
    st.success(f"Updated {unit_id}")

df = st.session_state.units.copy()

total_units = len(df)
packed_units = len(df[df["status"] == "Packed"])
missing_units = len(df[df["status"] == "Missing"])
stored_units = len(df[df["status"] == "Stored"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Units", total_units)
col2.metric("Stored", stored_units)
col3.metric("Packed", packed_units)
col4.metric("Missing", missing_units)

st.divider()

st.subheader("Current Unit Status")
st.dataframe(df, use_container_width=True)

st.divider()

st.subheader("Alerts")

duplicate_units = df[df.duplicated(subset=["unit_id"], keep=False)]

if len(duplicate_units) > 0:
    st.error("Duplicate unit IDs detected")
    st.dataframe(duplicate_units, use_container_width=True)
else:
    st.success("No duplicate unit IDs detected")

required_steel = 3
available_steel = len(df[(df["metal"] == "Steel") & (df["status"] == "Stored")])

if available_steel < required_steel:
    st.warning(f"Steel shortage detected: need {required_steel}, available {available_steel}")
else:
    st.success(f"Steel availability OK: need {required_steel}, available {available_steel}")

st.divider()

st.subheader("Shelf Map")

shelf_display = []
for shelf_name in shelf_coords.keys():
    units_here = df[df["shelf"] == shelf_name]["unit_id"].tolist()
    if len(units_here) == 0:
        text = "Empty"
    else:
        text = ", ".join(units_here)
    shelf_display.append({"Shelf": shelf_name, "Units": text})

shelf_df = pd.DataFrame(shelf_display)
st.dataframe(shelf_df, use_container_width=True)

st.divider()

st.subheader("Packing Path Demo")

stored_df = df[df["status"] == "Stored"]

selected_units = st.multiselect(
    "Select units to pack",
    stored_df["unit_id"].tolist()
)

def distance(p1, p2):
    return math.dist(p1, p2)

if selected_units:
    packing_station = (0, -1)
    selected_shelves = []

    for uid in selected_units:
        row = df[df["unit_id"] == uid].iloc[0]
        selected_shelves.append((uid, row["shelf"], shelf_coords[row["shelf"]]))

    remaining = selected_shelves.copy()
    current = packing_station
    route = []
    total_distance = 0

    while remaining:
        next_stop = min(remaining, key=lambda x: distance(current, x[2]))
        route.append(next_stop)
        total_distance += distance(current, next_stop[2])
        current = next_stop[2]
        remaining.remove(next_stop)

    route_text = "Packing Station"
    for stop in route:
        route_text += f" → {stop[0]} ({stop[1]})"

    st.write("Suggested route:")
    st.info(route_text)
    st.metric("Estimated Travel Distance", round(total_distance, 2))

    carbon_factor = 0.05
    estimated_carbon = total_distance * carbon_factor
    st.metric("Estimated CO₂ Impact", round(estimated_carbon, 2))
else:
    st.write("Select stored units to generate a route.")
