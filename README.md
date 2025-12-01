# BackRoads
The Backroads API is a Python routing service that recommends scenic or alternative routes given the origin and destination coordinates using data from OpenStreetMaps. The system focuses on identifying routes that are more scenic than routes provided by popular GPS services. The goal is to provide users with routes they would not typically take, allowing them to explore the less-traveled roads of San Luis Obispo County.


## Prerequisites
- Python 3.11+
- Git, `pip`, and the ability to create virtual environments (`python -m venv` or `virtualenv`)
- No external services; everything runs offline after the first graph download

## Project Setup 
1. Clone the repository
2. Install the dependencies:

   `pip install -r requirements.txt`

3. Create virtual environment

   `python3 -m venv venv`
4. Activate environment

   Mac: `source venv/bin/activate`

   Windows: `venv\Scripts\activate`
5. Set up env file

## Running the API 
1. Run API Server at root
      ` PYTHONPATH=src uvicorn src.backroads.api.main:app --reload`
2. Access the server locally at
      http://127.0.0.1:8000/

## Project Structure 

## API EndPoints 

## About The Data
The graph of San Luis Obispo was loaded from OpenStreetMaps (OMSnx) in October 2025. 














   
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
