from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from backroads.core.data.graph import load_graph
from backroads.core.routing.weighting import (
    add_travel_time,
    add_scenic_weights,
    add_composite_cost,
    DEFAULT_SCENIC_BY_TYPE,
    DEFAULT_NATURAL_BY_TYPE,
)
from backroads.core.routing.pathfinding import find_route
from backroads.core.routing.produce_routes import (
    k_candidate_routes,
    path_time,
    path_scenic_avg,
    rank_routes,
)

CURRENT_SCENIC_BY_TYPE = dict(DEFAULT_SCENIC_BY_TYPE)
CURRENT_NATURAL_BY_TYPE = dict(DEFAULT_NATURAL_BY_TYPE)

graph = load_graph()
add_travel_time(graph)
add_scenic_weights(
    graph,
    scenic_by_type=CURRENT_SCENIC_BY_TYPE,
    natural_by_type=CURRENT_NATURAL_BY_TYPE,
)
add_composite_cost(graph, alpha=0.5)
for u, v, data in list(graph.edges(data=True))[:5]:
    print(f"{u} → {v}: {data}")

node_lats = [data["y"] for _, data in graph.nodes(data=True)]
node_lons = [data["x"] for _, data in graph.nodes(data=True)]

GRAPH_BOUNDS = {
    "min_lat": min(node_lats),
    "max_lat": max(node_lats),
    "min_lon": min(node_lons),
    "max_lon": max(node_lons),
}


def validate_coord_in_graph(lat: float, lon: float, label: str = "coordinate") -> None:
    """
    Raise HTTPException if (lat, lon) is outside the graph's bounding box.
    """
    if not (
        GRAPH_BOUNDS["min_lat"] <= lat <= GRAPH_BOUNDS["max_lat"]
        and GRAPH_BOUNDS["min_lon"] <= lon <= GRAPH_BOUNDS["max_lon"]
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{label} ({lat:.6f}, {lon:.6f}) is outside the supported routing area. "
                "This API currently only supports routes within the graph's coverage "
                "(San Luis Obispo County)."
            ),
        )


app = FastAPI(
    title="BackRoads Scenic Routing API",
    description="API for computing fastest and most scenic routes in San Luis Obispo County. Returns GeoJSON and scenic breakdowns.",
    version="1.0.0"
)

# Enable CORS for all origins (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RouteRequest(BaseModel):
    start: list[float]  # [lat, lon]
    end: list[float]    # [lat, lon]
    extra_minutes: Optional[float] = 0.0
    profile: Optional[str] = "default"

class WeightsRequest(BaseModel):
    scenic_by_type: Optional[Dict[str, float]] = Field(
        None,
        example=DEFAULT_SCENIC_BY_TYPE,
        description="Override some or all highway scenic weights. Omitted keys use defaults.",
    )
    natural_by_type: Optional[Dict[str, float]] = Field(
        None,
        example=DEFAULT_NATURAL_BY_TYPE,
        description="Override some or all natural feature weights. Omitted keys use defaults.",
    )

class WeightsResponse(BaseModel):
    scenic_by_type: Dict[str, float] = Field(
        ..., example=DEFAULT_SCENIC_BY_TYPE
    )
    natural_by_type: Dict[str, float] = Field(
        ..., example=DEFAULT_NATURAL_BY_TYPE
    )

# Accepts query parameters for now; can switch to POST/JSON if needed
@app.get("/route")
def route(
    start: str = Query(..., description="Origin as 'lat,lon', currently supporting SLO county"),
    end: str = Query(..., description="Destination as 'lat,lon', currently supporting SLO county"),
    extra_minutes: float = Query(0.0, description="Extra minutes allowed for scenic detour"),
    profile: str = Query("default", description="Scenic profile name")
):
    # Parse coordinates
    try:
        start_coords = [float(x) for x in start.split(",")]
        end_coords = [float(x) for x in end.split(",")]
        assert len(start_coords) == 2 and len(end_coords) == 2
    except Exception:
        return {"error": "Invalid start or end coordinates. Use 'lat,lon' format."}
    


    global graph, CURRENT_SCENIC_BY_TYPE, CURRENT_NATURAL_BY_TYPE

    if graph is None:
        raise HTTPException(status_code=500, detail="Routing graph is not initialized")

    origin = tuple(start_coords)      # (lat, lon)
    destination = tuple(end_coords)   # (lat, lon)

    validate_coord_in_graph(origin[0], origin[1], label="Origin")
    validate_coord_in_graph(destination[0], destination[1], label="Destination")


    # 1) Always compute the fastest route first (using travel_time)
    fastest_result = find_route(origin, destination, graph, weight="travel_time")
    fastest_nodes = fastest_result["nodes"]

    # compute its time
    fastest_time = 0.0
    for u, v in zip(fastest_nodes, fastest_nodes[1:]):
        data = graph.get_edge_data(u, v, default={})
        if isinstance(data, dict) and 0 in data:
            data = data[0]
        fastest_time += float(data.get("travel_time", 0.0))

    # If no extra time is allowed, just return this fastest route
    if extra_minutes <= 0:
        chosen_nodes = fastest_nodes
        chosen_cost = fastest_result["cost"]
        chosen_weight = "travel_time"
    else:
        # 2) Use k-candidate + ranking logic, constrained by extra_minutes
        routes = k_candidate_routes(graph, origin, destination, weight="scenic_cost", k=10)

        if not routes:
            # fallback to fastest if something weird happens
            chosen_nodes = fastest_nodes
            chosen_cost = fastest_result["cost"]
            chosen_weight = "travel_time"
        else:
    
            allowed_time = fastest_time + extra_minutes * 60.0
            time_budget_factor = allowed_time / fastest_time

            ranked = rank_routes(graph, routes, time_budget_factor=time_budget_factor)

            if ranked:
                top_path, scenic_avg, time_seconds = ranked[0]
                chosen_nodes = top_path
                chosen_cost = time_seconds 
                chosen_weight = "scenic_cost"
            else:
                # If no candidate route fits within the budget, fallback to fastest
                chosen_nodes = fastest_nodes
                chosen_cost = fastest_result["cost"]
                chosen_weight = "travel_time"

    # 3) Build GeoJSON etc. from chosen_nodes
    coords = [
        [graph.nodes[n]["x"], graph.nodes[n]["y"]]
        for n in chosen_nodes
    ]
    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords
        },
        "properties": {
            "cost": chosen_cost,
            "weight": chosen_weight
        }
    }

    # Scenic & time breakdown for the chosen route
    scenic_sum = 0.0
    time_sum = 0.0
    for u, v in zip(chosen_nodes, chosen_nodes[1:]):
        data = graph.get_edge_data(u, v, default={})
        if isinstance(data, dict) and 0 in data:
            data = data[0]
        scenic_sum += float(data.get("scenic_score", 0.0))
        time_sum += float(data.get("travel_time", 0.0))

    # street_breakdown: reuse your existing code, but use chosen_nodes instead of result["nodes"]
    from backroads.core.utils.streets import get_street_distances_from_path
    street_segments = get_street_distances_from_path(graph, chosen_nodes)
    direction_symbols = {
        'N': '↑', 'S': '↓', 'E': '→', 'W': '←',
        'NE': '↗', 'NW': '↖', 'SE': '↘', 'SW': '↙'
    }
    street_breakdown = []
    for name, miles, direction in street_segments:
        symbol = direction_symbols.get(direction, '')
        street_breakdown.append({
            "direction": direction,
            "direction_symbol": symbol,
            "street": name,
            "miles": round(miles, 2)
        })

    return {
        "geojson": geojson,
        "scenic_breakdown": {
            "total_scenic_score": scenic_sum,
            "total_travel_time_seconds": time_sum
        },
        "street_breakdown": street_breakdown,
        "start": start_coords,
        "end": end_coords,
        "extra_minutes": extra_minutes,
        "profile": profile,
        "weights_used": {
            "scenic_by_type": CURRENT_SCENIC_BY_TYPE,
            "natural_by_type": CURRENT_NATURAL_BY_TYPE,
        },
    }

@app.post("/weights")
def apply_weights(payload: WeightsRequest):
    global graph, CURRENT_SCENIC_BY_TYPE, CURRENT_NATURAL_BY_TYPE

    # Start from defaults
    scenic = dict(DEFAULT_SCENIC_BY_TYPE)
    natural = dict(DEFAULT_NATURAL_BY_TYPE)

    # Apply user overrides (if provided)
    if payload.scenic_by_type:
        scenic.update(payload.scenic_by_type)

    if payload.natural_by_type:
        natural.update(payload.natural_by_type)

    # Update the module-level “current” mappings
    CURRENT_SCENIC_BY_TYPE = scenic
    CURRENT_NATURAL_BY_TYPE = natural

    # Recompute weights on the existing graph
    add_travel_time(graph)
    add_scenic_weights(
        graph,
        scenic_by_type=scenic,
        natural_by_type=natural,
    )
    add_composite_cost(graph, alpha=0.5)

    return {
        "scenic_by_type": scenic,
        "natural_by_type": natural,
    }
