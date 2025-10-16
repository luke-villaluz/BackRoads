# BackRoads

Lightweight, fully local scenic-route planner for San Luis Obispo County. We cache OpenStreetMap drive networks, compute fastest routes with NetworkX, and will layer in scenic scoring next.

## Prerequisites
- Python 3.11+
- Git, `pip`, and the ability to create virtual environments (`python -m venv` or `virtualenv`)
- No external services; everything runs offline after the first graph download

## First-Time Setup
1. **Clone & enter the repo**
   ```bash
   git clone <your-fork-or-upstream-url>
   cd BackRoads
Create & activate a virtual environment

bash
Copy code
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
Install dependencies

bash
Copy code
pip install -r requirements.txt
Configure environment variables

bash
Copy code
cp .env.example .env
# adjust paths if you want the graph/config/output directories elsewhere
src/backroads/config.py uses .env to resolve:

GRAPH_PATH (default data_cache/slo_drive.graphml)

CONFIGS_DIR (default configs/)

OUTPUTS_DIR (default outputs/)

LOG_LEVEL for module logging (defaults to INFO)

(Optional) Verify .env paths

bash
Copy code
python - <<'PY'
from backroads.config import GRAPH_PATH, CONFIGS_DIR, OUTPUTS_DIR
print("GRAPH_PATH:", GRAPH_PATH)
print("CONFIGS_DIR:", CONFIGS_DIR)
print("OUTPUTS_DIR:", OUTPUTS_DIR)
PY
Core Modules
Graph I/O (src/backroads/core/graph_io.py)
load_graph() ensures cache/output folders exist, then tries to load the cached GRAPH_PATH. If the file is missing, it downloads the San Luis Obispo County drive network with OSMnx, saves it, and returns the networkx.MultiDiGraph.

Logging respects .env's LOG_LEVEL, making it clear when we load from disk vs. when a fresh download happens.

Routing (src/backroads/core/routing.py)
prepare_graph() calls load_graph() and annotates every edge with a travel_time estimate derived from length and normalized speed metadata.

_resolve_speed_kph() cleans up OSM speed values (numbers, “mph”, lists) into km/h; _edge_travel_time() converts the result into seconds.

_nearest_node() snaps latitude/longitude pairs to the closest graph node via OSMnx, with a haversine-based fallback if OSMnx snappy lookup is unavailable.

find_fastest_route(origin, destination, graph=None) snaps both endpoints, runs a travel-time-weighted shortest path, and returns the node sequence plus total travel time (seconds). Pass an existing graph if you’re issuing multiple queries.

Quick Commands
bash
Copy code
# 1. Ensure the cached graph exists (downloads on first run, then loads locally)
python - <<'PY'
from backroads.core.graph_io import load_graph
graph = load_graph()
print(f"Graph ready: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
PY

# 2. Compute a fastest route between two San Luis Obispo coordinates
python - <<'PY'
from backroads.core.routing import find_fastest_route
origin = (35.2828, -120.6596)        # Replace with your origin (lat, lon)
destination = (35.1810, -120.7340)  # Replace with your destination (lat, lon)
result = find_fastest_route(origin, destination)
print("Node sequence:", result["nodes"])
print("Travel time (minutes):", result["travel_time_seconds"] / 60)
PY
Repo Layout
configs/ — YAML scenic profiles (empty starter directory)

data_cache/ — cached OSM graph (GRAPH_PATH lives here by default)

outputs/ — placeholder for route GeoJSON or debug artifacts

src/backroads/config.py — central path/env loader

src/backroads/core/graph_io.py — download/load the SLO drive graph

src/backroads/core/routing.py — travel-time weighting and shortest-path logic

tests/ — reserved for future pytest suites (none yet)

Day-to-Day Workflow
Activate .venv, export any overrides, and use the quick commands above to fetch the graph or probe routes.

When hacking on new features, prefer small, testable steps—mirror PROJECT_CONTEXT.md guidelines.

Run pytest (once tests exist) before committing; currently there are no tests, so consider adding targeted unit tests for new logic.

Next Milestones (per hand-off notes)
Week 4 — Extract scenic features from the graph and wire up YAML weight profiles.

Week 5 — Rank candidate routes within a user-defined time budget.

Week 6 — Layer on a thin FastAPI API (health check + route endpoint).

With this setup, any teammate can install deps, cache the map, and start iterating on routing or upcoming scenic features immediately.