import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import heapq

st.set_page_config(
    page_title="Smart Metal Storage Dashboard",
    page_icon="📦",
    layout="wide"
)

# =====================================================
# DEMO DATA
# =====================================================
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
        "unit_id", "metal", "old_shelf", "new_shelf", "status", "order_id"
    ])

order_requirements = {
    "O100": {"Steel": 1, "Copper": 1},
    "O101": {"Brass": 1},
    "O102": {"Steel": 1},
    "O103": {"Aluminum": 1},
}

# =====================================================
# LAYOUT / MAP GEOMETRY
# =====================================================
# Shelf centers (for display)
shelf_centers = {
    "A1": (2, 7), "A2": (2, 5), "A3": (2, 3),
    "B1": (5, 7), "B2": (5, 5), "B3": (5, 3),
    "C1": (8, 7), "C2": (8, 5), "C3": (8, 3),
}

# Shelf access points = where humans stand to pick
# These are on walkable aisles, not inside shelves
shelf_access = {
    "A1": "L7", "A2": "L5", "A3": "L3",
    "B1": "M7", "B2": "M5", "B3": "M3",
    "C1": "R7", "C2": "R5", "C3": "R3",
}

# Walkable aisle nodes
nodes = {
    "PACK": (10, 1),
    "ENTRY": (5, 0.8),

    "L3": (1, 3), "L5": (1, 5), "L7": (1, 7),
    "M3": (4, 3), "M5": (4, 5), "M7": (4, 7),
    "R3": (7, 3), "R5": (7, 5), "R7": (7, 7),

    "F1": (1, 1.5), "F4": (4, 1.5), "F7": (7, 1.5), "F10": (10, 1.5),
    "B1": (1, 8.3), "B4": (4, 8.3), "B7": (7, 8.3),
}

# Graph edges: only walkable aisle connections
graph = {
    "PACK": ["F10"],
    "ENTRY": ["F4"],

    "F1": ["F4", "L3"],
    "F4": ["F1", "F7", "M3", "ENTRY"],
    "F7": ["F4", "F10", "R3"],
    "F10": ["F7", "PACK"],

    "L3": ["F1", "L5"],
    "L5": ["L3", "L7"],
    "L7": ["L5", "B1"],

    "M3": ["F4", "M5"],
    "M5": ["M3", "M7"],
    "M7": ["M5", "B4"],

    "R3": ["F7", "R5"],
    "R5": ["R3", "R7"],
    "R7": ["R5", "B7"],

    "B1": ["L7", "B4"],
    "B4": ["B1", "B7", "M7"],
    "B7": ["B4", "R7"],
}

gateway_positions = {
    "Gateway West": (0.4, 5.2),
    "Gateway North": (5, 8.9),
    "Gateway East": (9.2, 5.2),
}

# =====================================================
# HELPERS
# =====================================================
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

    event = pd.DataFrame([{
        "unit_id": unit_id,
        "metal": metal,
        "old_shelf": old_shelf,
        "new_shelf": shelf,
        "status": status,
        "order_id": order_id
    }])
    st.session_state.event_log = pd.concat([st.session_state.event_log, event], ignore_index=True)

def manhattan_distance(a, b):
    x1, y1 = nodes[a]
    x2, y2 = nodes[b]
    return abs(x1 - x2) + abs(y1 - y2)

def dijkstra(start, end):
    pq = [(0, start, [start])]
    visited = set()

    while pq:
        cost, current, path = heapq.heappop(pq)

        if current in visited:
            continue
        visited.add(current)

        if current == end:
            return path, cost

        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                edge_cost = manhattan_distance(current, neighbor)
                heapq.heappush(pq, (cost + edge_cost, neighbor, path + [neighbor]))

    return [], float("inf")

def build_pick_sequence(selected_units, df):
    # Greedy order selection based on aisle-path cost
    remaining = []
    for uid in selected_units:
        row = df[df["unit_id"] == uid].iloc[0]
        shelf = row["shelf"]
        access_node = shelf_access[shelf]
        remaining.append({
            "unit_id": uid,
            "shelf": shelf,
            "access_node": access_node
        })

    current_node = "PACK"
    visit_order = []
    total_cost = 0

    while remaining:
        best_item = None
        best_path = None
        best_cost = float("inf")

        for item in remaining:
            path, cost = dijkstra(current_node, item["access_node"])
            if cost < best_cost:
                best_cost = cost
                best_path = path
                best_item = item

        visit_order.append({
            "unit_id": best_item["unit_id"],
            "shelf": best_item["shelf"],
            "access_node": best_item["access_node"],
            "path": best_path,
            "cost": best_cost
        })
        total_cost += best_cost
        current_node = best_item["access_node"]
        remaining.remove(best_item)

    return visit_order, total_cost

def flatten_route_paths(visit_order):
    full_nodes = []
    for i, stop in enumerate(visit_order):
        segment = stop["path"]
        if i == 0:
            full_nodes.extend(segment)
        else:
            full_nodes.extend(segment[1:])
    return full_nodes

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

def render_overview_grid(df):
    rows = ["A", "B", "C"]
    cols = ["1", "2", "3"]

    for r in rows:
        cols_ui = st.columns(3)
        for i, c in enumerate(cols):
            shelf = f"{r}{c}"
            units_here = df[df["shelf"] == shelf]
            if len(units_here) == 0:
                cols_ui[i].info(f"**{shelf}**\n\nEmpty")
            else:
                lines = [f"{row['unit_id']} ({row['metal']})" for _, row in units_here.iterrows()]
                cols_ui[i].success(f"**{shelf}**\n\n" + "\n".join(lines))

def draw_warehouse_map(df, selected_units=None):
    fig = go.Figure()

    # room
    fig.add_shape(
        type="rect",
        x0=0, y0=0, x1=11, y1=9.5,
        line=dict(width=2),
        fillcolor="rgba(245,245,245,0.3)"
    )

    # shelves as blocked rectangles
    for shelf, (x, y) in shelf_centers.items():
        fig.add_shape(
            type="rect",
            x0=x - 0.8, y0=y - 0.8,
            x1=x + 0.8, y1=y + 0.8,
            line=dict(width=2),
            fillcolor="rgba(80,120,200,0.35)"
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

    # aisles / walkable graph edges
    drawn = set()
    for node, neighbors in graph.items():
        for nb in neighbors:
            edge_key = tuple(sorted([node, nb]))
            if edge_key in drawn:
                continue
            drawn.add(edge_key)

            x0, y0 = nodes[node]
            x1, y1 = nodes[nb]

            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(width=3, dash="dot"),
                showlegend=False,
                hoverinfo="skip"
            ))

    # aisle nodes
    aisle_x = [coord[0] for coord in nodes.values()]
    aisle_y = [coord[1] for coord in nodes.values()]
    aisle_labels = list(nodes.keys())

    fig.add_trace(go.Scatter(
        x=aisle_x,
        y=aisle_y,
        mode="markers",
        marker=dict(size=8),
        text=aisle_labels,
        showlegend=False,
        hovertemplate="Node: %{text}<extra></extra>"
    ))

    # gateways
    for name, (x, y) in gateway_positions.items():
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            text=[name],
            textposition="top center",
            marker=dict(size=14, symbol="diamond"),
            name=name
        ))

    # packing station
    px, py = nodes["PACK"]
    fig.add_trace(go.Scatter(
        x=[px], y=[py],
        mode="markers+text",
        text=["Packing Station"],
        textposition="top center",
        marker=dict(size=18, symbol="square"),
        name="Packing Station"
    ))

    # entry
    ex, ey = nodes["ENTRY"]
    fig.add_trace(go.Scatter(
        x=[ex], y=[ey],
        mode="markers+text",
        text=["Entry / Exit"],
        textposition="top center",
        marker=dict(size=14, symbol="circle"),
        name="Entry / Exit"
    ))

    # route that respects aisles
    if selected_units:
        visit_order, total_cost = build_pick_sequence(selected_units, df)
        route_nodes = flatten_route_paths(visit_order)

        route_x = [nodes[n][0] for n in route_nodes]
        route_y = [nodes[n][1] for n in route_nodes]

        fig.add_trace(go.Scatter(
            x=route_x,
            y=route_y,
            mode="lines+markers",
            line=dict(width=5),
            marker=dict(size=9),
            name="Walking Route"
        ))

        # mark selected shelf access points
        access_x = []
        access_y = []
        access_text = []
        for stop in visit_order:
            ax, ay = nodes[stop["access_node"]]
            access_x.append(ax)
            access_y.append(ay)
            access_text.append(f"{stop['unit_id']} @ {stop['shelf']}")

        fig.add_trace(go.Scatter(
            x=access_x,
            y=access_y,
            mode="markers+text",
            text=access_text,
            textposition="bottom center",
            marker=dict(size=12, symbol="star"),
            name="Pick Stops"
        ))

    fig.update_layout(
        height=720,
        xaxis=dict(range=[-0.2, 11.2], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-0.2, 9.7], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h")
    )
    return fig

# =====================================================
# SIDEBAR
# =====================================================
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
    shelf = st.selectbox("Shelf Location", list(shelf_centers.keys()))
    status = st.selectbox("Status", ["Stored", "Packed", "Missing"])
    order_id = st.text_input("Order ID", "O999")
    submitted = st.form_submit_button("Update Unit")

    if submitted:
        update_unit(unit_id, metal, shelf, status, order_id)
        st.sidebar.success(f"{unit_id} updated")

df = get_units()
shortage_df = get_shortages(df)

# =====================================================
# HEADER
# =====================================================
st.title("Smart Metal Storage Dashboard")
st.caption("Aisle-based warehouse navigation, storage visibility, alerts, and packing support")

# =====================================================
# PAGES
# =====================================================
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
    render_overview_grid(df)

    st.markdown("### Recent Activity")
    if len(st.session_state.event_log) > 0:
        st.dataframe(st.session_state.event_log.tail(10).iloc[::-1], use_container_width=True)
    else:
        st.info("No updates yet.")

elif page == "2D Warehouse Map":
    st.subheader("2D Warehouse Navigation Map")
    st.write("Routes follow walkable aisles only and do not pass through shelves.")

    stored_df = df[df["status"] == "Stored"]
    selected_units = st.multiselect(
        "Select stored units to generate a walking route",
        stored_df["unit_id"].tolist(),
        key="map_units"
    )

    fig = draw_warehouse_map(df, selected_units if selected_units else None)
    st.plotly_chart(fig, use_container_width=True)

    if selected_units:
        visit_order, total_cost = build_pick_sequence(selected_units, df)

        st.markdown("### Walking Instructions")
        for i, stop in enumerate(visit_order, start=1):
            st.write(f"{i}. Walk to **{stop['shelf']}** and pick **{stop['unit_id']}**.")

        st.metric("Estimated Walking Distance", round(total_cost, 2), "meters")

elif page == "Unit Tracker":
    st.subheader("Unit Tracker")

    search_unit = st.text_input("Search by Unit ID")
    filtered_df = df.copy()

    if search_unit:
        filtered_df = filtered_df[filtered_df["unit_id"].str.contains(search_unit, case=False, na=False)]

    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("### Unit Details")
    selected_unit = st.selectbox("Select Unit", df["unit_id"].tolist())
    row = df[df["unit_id"] == selected_unit].iloc[0]

    c1, c2 = st.columns(2)
    c1.write(f"**Unit ID:** {row['unit_id']}")
    c1.write(f"**Metal:** {row['metal']}")
    c1.write(f"**Shelf:** {row['shelf']}")
    c2.write(f"**Status:** {row['status']}")
    c2.write(f"**Order ID:** {row['order_id']}")

    st.markdown("### Unit Movement History")
    history = st.session_state.event_log[st.session_state.event_log["unit_id"] == selected_unit]
    if len(history) > 0:
        st.dataframe(history.iloc[::-1], use_container_width=True)
    else:
        st.info("No movement history yet.")

elif page == "Packing Route":
    st.subheader("Packing Route Optimizer")
    st.write("This route respects warehouse aisles and avoids shelf obstacles.")

    stored_df = df[df["status"] == "Stored"]
    selected_units = st.multiselect(
        "Select units for packing",
        stored_df["unit_id"].tolist(),
        key="packing_units"
    )

    if selected_units:
        visit_order, total_cost = build_pick_sequence(selected_units, df)

        route_table = pd.DataFrame([
            {
                "Stop": i + 1,
                "Unit ID": stop["unit_id"],
                "Shelf": stop["shelf"],
                "Aisle Node": stop["access_node"],
                "Segment Distance": round(stop["cost"], 2)
            }
            for i, stop in enumerate(visit_order)
        ])
        st.dataframe(route_table, use_container_width=True)

        st.metric("Total Walking Distance", round(total_cost, 2), "meters")
        st.plotly_chart(draw_warehouse_map(df, selected_units), use_container_width=True)
    else:
        st.info("Select at least one stored unit.")

elif page == "Alerts":
    st.subheader("System Alerts")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Missing Units")
        missing_df = df[df["status"] == "Missing"]
        if len(missing_df) > 0:
            st.dataframe(missing_df, use_container_width=True)
        else:
            st.success("No missing units.")

    with c2:
        st.markdown("### Order Shortages")
        if len(shortage_df) > 0:
            st.dataframe(shortage_df, use_container_width=True)
        else:
            st.success("No shortages detected.")

    st.markdown("### Packed Units")
    packed_df = df[df["status"] == "Packed"]
    if len(packed_df) > 0:
        st.dataframe(packed_df, use_container_width=True)
    else:
        st.info("No packed units currently recorded.")

elif page == "Sustainability":
    st.subheader("Sustainability / Carbon Demo")
    st.write("Simple estimate based on walking distance along aisles.")

    stored_df = df[df["status"] == "Stored"]
    selected_units = st.multiselect(
        "Select stored units for carbon estimate",
        stored_df["unit_id"].tolist(),
        key="carbon_units"
    )

    if selected_units:
        visit_order, total_cost = build_pick_sequence(selected_units, df)
        carbon_factor = 0.05
        estimated_co2 = total_cost * carbon_factor

        c1, c2 = st.columns(2)
        c1.metric("Estimated Walking Distance", round(total_cost, 2), "meters")
        c2.metric("Estimated CO₂ Impact", round(estimated_co2, 2), "kg CO₂")

        st.plotly_chart(draw_warehouse_map(df, selected_units), use_container_width=True)
    else:
        st.info("Select stored units to estimate travel-based impact.")
