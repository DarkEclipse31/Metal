import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go

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
    "A1": (1, 7), "A2": (1, 5), "A3": (1, 3),
    "B1": (4, 7), "B2": (4, 5), "B3": (4, 3),
    "C1": (7, 7), "C2": (7, 5), "C3": (7, 3),
}

gateway_coords = {
    "Gateway West": (0.3, 5),
    "Gateway North": (4, 8.5),
    "Gateway East": (8.7, 5),
}

packing_station = (9.2, 1.2)
entry_door = (4.5, 0.3)

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
        df.loc[df["unit_id"] == unit_id, ["metal", "shelf", "status", "order_id"]] = [metal, shelf, status, order_id]
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

def draw_warehouse_map(df, selected_route_units=None):
    fig = go.Figure()

    # Room boundary
    fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=9,
                  line=dict(width=2), fillcolor="rgba(240,240,240,0.2)")

    # Shelves
    for shelf, (x, y) in shelf_coords.items():
        fig.add_shape(
            type="rect",
            x0=x - 0.8, y0=y - 0.6,
            x1=x + 0.8, y1=y + 0.6,
            line=dict(width=2),
            fillcolor="rgba(100,149,237,0.35)"
        )

        units_here = df[df["shelf"] == shelf]
        if len(units_here) == 0:
            label = f"{shelf}<br>Empty"
        else:
            label = f"{shelf}<br>" + "<br>".join(units_here["unit_id"].tolist())

        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="text",
            text=[label],
            textposition="middle center",
            showlegend=False,
            hoverinfo="skip"
        ))

    # Gateways
    for name, (x, y) in gateway_coords.items():
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            text=[name],
            textposition="top center",
            marker=dict(size=14, symbol="diamond"),
            name=name
        ))

    # Packing station
    fig.add_trace(go.Scatter(
        x=[packing_station[0]], y=[packing_station[1]],
        mode="markers+text",
        text=["Packing Station"],
        textposition="top center",
        marker=dict(size=18, symbol="square"),
        name="Packing Station"
    ))

    # Entry door
    fig.add_trace(go.Scatter(
        x=[entry_door[0]], y=[entry_door[1]],
        mode="markers+text",
        text=["Entry / Exit"],
        textposition="top center",
        marker=dict(size=14, symbol="circle"),
        name="Entry / Exit"
    ))

    # Route
    if selected_route_units:
        route, total_distance = build_route(selected_route_units, df)
        route_points_x = [packing_station[0]]
        route_points_y = [packing_station[1]]

        for stop in route:
            route_points_x.append(stop[2][0])
            route_points_y.append(stop[2][1])

        fig.add_trace(go.Scatter(
            x=route_points_x,
            y=route_points_y,
            mode="lines+markers",
            name="Pick Route",
            line=dict(width=4, dash="dash"),
            marker=dict(size=10)
        ))

    fig.update_layout(
        height=700,
        xaxis=dict(range=[-0.5, 10.5], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-0.5, 9.5], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
        margin=dict(l=20, r=20, t=20, b=20)
    )

    return fig

# -------------------------------------------------
# Sidebar navigation
# -------------------------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "Overview",
        "2D Warehouse Map",
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
st.caption("IoT-inspired storage visibility, route guidance, and simple sustainability tracking")

# -------------------------------------------------
# Overview
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

    st.markdown("### Quick Storage View")
    render_shelf_grid(df)

    st.markdown("### Recent Activity")
    if len(st.session_state.event_log) > 0:
        st.dataframe(st.session_state.event_log.tail(10).iloc[::-1], use_container_width=True)
    else:
        st.info("No updates yet.")

# -------------------------------------------------
# 2D Map
# -------------------------------------------------
elif page == "2D Warehouse Map":
    st.subheader("2D Warehouse Navigation Map")
    st.write("This map shows shelf locations, gateways, packing station, and unit positions.")

    stored_df = df[df["status"] == "Stored"]
    selected_route_units = st.multiselect(
        "Select stored units to draw a picking route",
        stored_df["unit_id"].tolist(),
        key="map_route_units"
    )

    fig = draw_warehouse_map(df, selected_route_units if selected_route_units else None)
    st.plotly_chart(fig, use_container_width=True)

    if selected_route_units:
        route, total_distance = build_route(selected_route_units, df)
        route_text = "Packing Station"
        for stop in route:
            route_text += f" → {stop[0]} ({stop[1]})"
        st.success("Route generated")
        st.write(route_text)
        st.metric("Estimated Route Distance", round(total_distance, 2), "meters")

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
    selected_unit = st.selectbox("Select Unit", df["unit_id"].tolist())
    selected_row = df[df["unit_id"] == selected_unit].iloc[0]

    c1, c2 = st.columns(2)
    c1.write(f"**Unit ID:** {selected_row['unit_id']}")
    c1.write(f"**Metal:** {selected_row['metal']}")
    c1.write(f"**Shelf:** {selected_row['shelf']}")
    c2.write(f"**Status:** {selected_row['status']}")
    c2.write(f"**Order ID:** {selected_row['order_id']}")

    history = st.session_state.event_log[st.session_state.event_log["unit_id"] == selected_unit]
    st.markdown("### Unit Movement History")
    if len(history) > 0:
        st.dataframe(history.iloc[::-1], use_container_width=True)
    else:
        st.info("No movement history yet.")

# -------------------------------------------------
# Packing Route
# -------------------------------------------------
elif page == "Packing Route":
    st.subheader("Packing Route Optimizer")

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

        st.write(route_text)
        st.metric("Estimated Travel Distance", round(total_distance, 2), "meters")

        route_df = pd.DataFrame([
            {"Unit ID": stop[0], "Shelf": stop[1], "Coordinates": stop[2]}
            for stop in route
        ])
        st.dataframe(route_df, use_container_width=True)

        fig = draw_warehouse_map(df, selected_units)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select at least one stored unit.")

# -------------------------------------------------
# Alerts
# -------------------------------------------------
elif page == "Alerts":
    st.subheader("System Alerts")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Missing Units")
        missing_df = df[df["status"] == "Missing"]
        if len(missing_df) > 0:
            st.dataframe(missing_df, use_container_width=True)
        else:
            st.success("No missing units")

    with c2:
        st.markdown("### Order Shortages")
        if len(shortage_df) > 0:
            st.dataframe(shortage_df, use_container_width=True)
        else:
            st.success("No shortages detected")

# -------------------------------------------------
# Sustainability
# -------------------------------------------------
elif page == "Sustainability":
    st.subheader("Sustainability / Carbon Demo")

    stored_df = df[df["status"] == "Stored"]
    selected_units = st.multiselect(
        "Select stored units for carbon estimate",
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

        fig = draw_warehouse_map(df, selected_units)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select stored units to estimate travel-based carbon impact.")
