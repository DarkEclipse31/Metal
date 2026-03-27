import streamlit as st
import pandas as pd
import math

st.set_page_config(
    page_title="Smart Metal Storage Dashboard",
    page_icon="📦",
    layout="wide"
)

# -------------------------------------------------
# Demo data setup
# -------------------------------------------------
if "units" not in st.session_state:
    st.session_state.units = pd.DataFrame([
        {"unit_id": "U001", "metal": "Steel",    "shelf": "A1", "status": "Stored",  "order_id": "O100"},
        {"unit_id": "U002", "metal": "Copper",   "shelf": "A2", "status": "Stored",  "order_id": "O100"},
        {"unit_id": "U003", "metal": "Brass",    "shelf": "B1", "status": "Stored",  "order_id": "O101"},
        {"unit_id": "U004", "metal": "Steel",    "shelf": "B2", "status": "Packed",  "order_id": "O102"},
        {"unit_id": "U005", "metal": "Aluminum", "shelf": "C1", "status": "Stored",  "order_id": "O103"},
        {"unit_id": "U006", "metal": "Copper",   "shelf": "C3", "status": "Missing", "order_id": "O104"},
    ])

if "event_log" not in st.session_state:
    st.session_state.event_log = pd.DataFrame(columns=[
        "unit_id", "metal", "old_shelf", "new_shelf", "status"
    ])

shelf_coords = {
    "A1": (0, 0), "A2": (0, 1), "A3": (0, 2),
    "B1": (1, 0), "B2": (1, 1), "B3": (1, 2),
    "C1": (2, 0), "C2": (2, 1), "C3": (2, 2),
}

order_requirements = {
    "O100": {"Steel": 1, "Copper": 1},
    "O101": {"Brass": 1},
    "O102": {"Steel": 1},
    "O103": {"Aluminum": 1},
}

# -------------------------------------------------
# Helper functions
# -------------------------------------------------
def get_units():
    return st.session_state.units.copy()

def update_unit(unit_id, metal, shelf, status, order_id="O999"):
    df = get_units()

    if unit_id in df["unit_id"].values:
        old_shelf = df.loc[df["unit_id"] == unit_id, "shelf"].values[0]
        df.loc[df["unit_id"] == unit_id, ["metal", "shelf", "status"]] = [metal, shelf, status]
    else:
        old_shelf = "-"
        new_row = pd.DataFrame([{
            "unit_id": unit_id,
            "metal": metal,
            "shelf": shelf,
            "status": status,
            "order_id": order_id
        }])
        df = pd.concat([df, new_row], ignore_index=True)

    st.session_state.units = df

    new_event = pd.DataFrame([{
        "unit_id": unit_id,
        "metal": metal,
        "old_shelf": old_shelf,
        "new_shelf": shelf,
        "status": status
    }])

    st.session_state.event_log = pd.concat(
        [st.session_state.event_log, new_event],
        ignore_index=True
    )

def distance(p1, p2):
    return math.dist(p1, p2)

def build_route(selected_units, df):
    packing_station = (0, -1)
    remaining = []

    for uid in selected_units:
        row = df[df["unit_id"] == uid].iloc[0]
        remaining.append((uid, row["shelf"], shelf_coords[row["shelf"]]))

    current = packing_station
    route = []
    total_distance = 0

    while remaining:
        next_stop = min(remaining, key=lambda x: distance(current, x[2]))
        route.append(next_stop)
        total_distance += distance(current, next_stop[2])
        current = next_stop[2]
        remaining.remove(next_stop)

    return route, total_distance

def get_shortages(df):
    shortages = []

    for order_id, requirements in order_requirements.items():
        order_df = df[(df["order_id"] == order_id) & (df["status"] == "Stored")]
        for metal, required_qty in requirements.items():
            available_qty = len(order_df[order_df["metal"] == metal])
            if available_qty < required_qty:
                shortages.append({
                    "order_id": order_id,
                    "metal": metal,
                    "required": required_qty,
                    "available": available_qty
                })

    return pd.DataFrame(shortages)

def render_shelf_grid(df):
    rows = ["A", "B", "C"]
    cols = ["1", "2", "3"]

    for r in rows:
        grid_cols = st.columns(3)
        for i, c in enumerate(cols):
            shelf = f"{r}{c}"
            units_here = df[df["shelf"] == shelf]

            if len(units_here) == 0:
                label = f"**{shelf}**\n\nEmpty"
                grid_cols[i].info(label)
            else:
                unit_lines = []
                for _, row in units_here.iterrows():
                    unit_lines.append(f"{row['unit_id']} ({row['metal']})")
                label = f"**{shelf}**\n\n" + "\n".join(unit_lines)
                grid_cols[i].success(label)

# -------------------------------------------------
# Sidebar navigation
# -------------------------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "Overview",
        "Live Storage Map",
        "Unit Tracker",
        "Packing Route",
        "Alerts",
        "Sustainability"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Simulate Gateway / Tag Update")

with st.sidebar.form("update_form"):
    unit_id = st.text_input("Unit ID", "U001")
    metal = st.selectbox("Metal Type", ["Steel", "Copper", "Brass", "Aluminum"])
    shelf = st.selectbox("Shelf Location", list(shelf_coords.keys()))
    status = st.selectbox("Status", ["Stored", "Packed", "Missing"])
    order_id = st.text_input("Order ID", "O999")
    submitted = st.form_submit_button("Update Unit")

    if submitted:
        update_unit(unit_id, metal, shelf, status, order_id)
        st.sidebar.success(f"{unit_id} updated")

df = get_units()
shortage_df = get_shortages(df)

# -------------------------------------------------
# Header
# -------------------------------------------------
st.title("Smart Metal Storage Dashboard")
st.caption("IoT-inspired storage visibility, packing support, and simple sustainability tracking")

# -------------------------------------------------
# Overview page
# -------------------------------------------------
if page == "Overview":
    total_units = len(df)
    stored_units = len(df[df["status"] == "Stored"])
    packed_units = len(df[df["status"] == "Packed"])
    missing_units = len(df[df["status"] == "Missing"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Units", total_units)
    c2.metric("Stored", stored_units)
    c3.metric("Packed", packed_units)
    c4.metric("Missing", missing_units)

    st.markdown("### What this system does")
    st.write("""
    This dashboard helps workers and supervisors:
    - track where each metal unit is stored
    - detect missing or misplaced units
    - identify shortages for orders
    - support faster packing with route suggestions
    - estimate simple movement-based carbon impact
    """)

    st.markdown("### Quick View of Storage")
    render_shelf_grid(df)

    st.markdown("### Recent Unit Activity")
    if len(st.session_state.event_log) > 0:
        st.dataframe(
            st.session_state.event_log.tail(10).iloc[::-1],
            use_container_width=True
        )
    else:
        st.info("No updates yet. Use the sidebar to simulate a unit update.")

# -------------------------------------------------
# Live Storage Map
# -------------------------------------------------
elif page == "Live Storage Map":
    st.subheader("Live Storage Map")
    st.write("This view shows where units are currently located in the warehouse.")
    render_shelf_grid(df)

    st.markdown("### Current Storage Table")
    st.dataframe(
        df.sort_values(by=["shelf", "unit_id"]),
        use_container_width=True
    )

# -------------------------------------------------
# Unit Tracker
# -------------------------------------------------
elif page == "Unit Tracker":
    st.subheader("Unit Tracker")

    search_unit = st.text_input("Search by Unit ID")
    filtered_df = df.copy()

    if search_unit:
        filtered_df = filtered_df[filtered_df["unit_id"].str.contains(search_unit, case=False, na=False)]

    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("### View a Single Unit")
    unit_options = df["unit_id"].tolist()
    selected_unit = st.selectbox("Select Unit", unit_options)

    selected_row = df[df["unit_id"] == selected_unit].iloc[0]

    col1, col2 = st.columns(2)
    col1.write(f"**Unit ID:** {selected_row['unit_id']}")
    col1.write(f"**Metal:** {selected_row['metal']}")
    col1.write(f"**Shelf:** {selected_row['shelf']}")
    col2.write(f"**Status:** {selected_row['status']}")
    col2.write(f"**Order ID:** {selected_row['order_id']}")

    st.markdown("### Unit Movement History")
    history = st.session_state.event_log[st.session_state.event_log["unit_id"] == selected_unit]
    if len(history) > 0:
        st.dataframe(history.iloc[::-1], use_container_width=True)
    else:
        st.info("No movement history for this unit yet.")

# -------------------------------------------------
# Packing Route
# -------------------------------------------------
elif page == "Packing Route":
    st.subheader("Packing Route Optimizer")
    st.write("Choose stored units and the system suggests an easy picking order.")

    stored_df = df[df["status"] == "Stored"]
    selected_units = st.multiselect(
        "Select units for packing",
        stored_df["unit_id"].tolist()
    )

    if selected_units:
        route, total_distance = build_route(selected_units, df)

        route_text = "Packing Station"
        for stop in route:
            route_text += f" → {stop[0]} ({stop[1]})"

        st.success("Suggested route generated")
        st.write(route_text)
        st.metric("Estimated Travel Distance", round(total_distance, 2), "meters")

        st.markdown("### Route Details")
        route_df = pd.DataFrame([
            {"Unit ID": stop[0], "Shelf": stop[1], "Coordinates": stop[2]}
            for stop in route
        ])
        st.dataframe(route_df, use_container_width=True)
    else:
        st.info("Select at least one stored unit to calculate a route.")

# -------------------------------------------------
# Alerts
# -------------------------------------------------
elif page == "Alerts":
    st.subheader("System Alerts")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Missing Units")
        missing_df = df[df["status"] == "Missing"]
        if len(missing_df) > 0:
            st.dataframe(missing_df, use_container_width=True)
        else:
            st.success("No missing units")

    with col2:
        st.markdown("### Order Shortages")
        if len(shortage_df) > 0:
            st.dataframe(shortage_df, use_container_width=True)
        else:
            st.success("No shortages detected")

    st.markdown("### Packed Units")
    packed_df = df[df["status"] == "Packed"]
    if len(packed_df) > 0:
        st.dataframe(packed_df, use_container_width=True)
    else:
        st.info("No packed units currently recorded")

# -------------------------------------------------
# Sustainability
# -------------------------------------------------
elif page == "Sustainability":
    st.subheader("Sustainability / Carbon Demo")
    st.write("This is a simple demo panel showing estimated internal movement impact.")

    stored_df = df[df["status"] == "Stored"]
    selected_units = st.multiselect(
        "Select units for carbon estimate",
        stored_df["unit_id"].tolist(),
        key="carbon_units"
    )

    if selected_units:
        route, total_distance = build_route(selected_units, df)
        carbon_factor = 0.05
        estimated_co2 = total_distance * carbon_factor

        c1, c2 = st.columns(2)
        c1.metric("Estimated Travel Distance", round(total_distance, 2), "meters")
        c2.metric("Estimated CO₂ Impact", round(estimated_co2, 2), "kg CO₂")

        st.info("This is a simple demo estimate based on travel distance only.")
    else:
        st.info("Select stored units to estimate travel-based carbon impact.")
