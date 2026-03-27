import streamlit as st
import random
import math
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("📦 IoT Smart Storage Digital Twin")

GRID_SIZE = 5
NUM_UNITS = 12

# ---------------------------
# INIT STATE
# ---------------------------
if "units" not in st.session_state:
    st.session_state.units = [
        {
            "id": f"U{i+1}",
            "x": random.randint(0, GRID_SIZE-1),
            "y": random.randint(0, GRID_SIZE-1),
            "status": "stored"
        }
        for i in range(NUM_UNITS)
    ]

if "order_units" not in st.session_state:
    st.session_state.order_units = []

# ---------------------------
# SIDEBAR CONTROLS
# ---------------------------
st.sidebar.header("Controls")

if st.sidebar.button("🔄 Move Units"):
    for u in st.session_state.units:
        u["x"] = random.randint(0, GRID_SIZE-1)
        u["y"] = random.randint(0, GRID_SIZE-1)
        u["status"] = "stored"

if st.sidebar.button("📦 Generate Order"):
    st.session_state.order_units = random.sample(st.session_state.units, 4)

if st.sidebar.button("🔁 Reset"):
    st.session_state.units = [
        {
            "id": f"U{i+1}",
            "x": random.randint(0, GRID_SIZE-1),
            "y": random.randint(0, GRID_SIZE-1),
            "status": "stored"
        }
        for i in range(NUM_UNITS)
    ]
    st.session_state.order_units = []

# ---------------------------
# DUPLICATE DETECTION
# ---------------------------
positions = [(u["x"], u["y"]) for u in st.session_state.units]
duplicates = set([p for p in positions if positions.count(p) > 1])

for u in st.session_state.units:
    if (u["x"], u["y"]) in duplicates:
        u["status"] = "error"

# ---------------------------
# MISSING / SHORTAGE
# ---------------------------
expected_units = [f"U{i+1}" for i in range(NUM_UNITS)]
detected_ids = [u["id"] for u in st.session_state.units]
missing_units = [u for u in expected_units if u not in detected_ids]

# ---------------------------
# SHORTEST PATH
# ---------------------------
def distance(a, b):
    return math.sqrt((a["x"]-b["x"])**2 + (a["y"]-b["y"])**2)

path = []
if st.session_state.order_units:
    start = {"x": 0, "y": 0}
    remaining = st.session_state.order_units.copy()
    current = start

    while remaining:
        next_unit = min(remaining, key=lambda u: distance(current, u))
        path.append(next_unit)
        current = next_unit
        remaining.remove(next_unit)

# ---------------------------
# PLOT GRID
# ---------------------------
fig = go.Figure()

# Draw grid
for x in range(GRID_SIZE):
    for y in range(GRID_SIZE):
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode='markers',
            marker=dict(size=8, color='lightgrey'),
            showlegend=False
        ))

# Draw units
for u in st.session_state.units:
    color = "green"

    if u["status"] == "error":
        color = "red"
    elif u in st.session_state.order_units:
        color = "blue"

    fig.add_trace(go.Scatter(
        x=[u["x"]],
        y=[u["y"]],
        mode='markers+text',
        text=[u["id"]],
        textposition="top center",
        marker=dict(size=18, color=color),
        showlegend=False
    ))

# Draw path
for i in range(len(path)-1):
    fig.add_trace(go.Scatter(
        x=[path[i]["x"], path[i+1]["x"]],
        y=[path[i]["y"], path[i+1]["y"]],
        mode='lines',
        line=dict(color='blue', width=3),
        showlegend=False
    ))

fig.update_layout(
    xaxis=dict(range=[-1, GRID_SIZE], dtick=1),
    yaxis=dict(range=[-1, GRID_SIZE], dtick=1),
    height=600
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# ALERTS
# ---------------------------
st.subheader("⚠️ System Alerts")

if duplicates:
    st.error(f"Duplicate locations detected at: {duplicates}")

if missing_units:
    st.warning(f"Missing units: {missing_units}")

if not duplicates and not missing_units:
    st.success("All systems normal")

# ---------------------------
# ORDER DISPLAY
# ---------------------------
st.subheader("📦 Current Order")

if st.session_state.order_units:
    order_ids = [u["id"] for u in path]
    st.write(" → ".join(order_ids))
else:
    st.write("No active order")
