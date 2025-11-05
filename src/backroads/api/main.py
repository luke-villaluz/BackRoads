from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query
from typing import Optional
from pydantic import BaseModel
from backroads.core.data.graph import load_graph
from backroads.core.routing.weighting import add_travel_time, add_scenic_weights, add_composite_cost
from backroads.core.routing.pathfinding import find_route
import networkx as nx

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

# Accepts query parameters for now; can switch to POST/JSON if needed
@app.get("/route")
def route(
    start: str = Query(..., description="Origin as 'lat,lon'"),
    end: str = Query(..., description="Destination as 'lat,lon'"),
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

    # Load and prepare the graph
    graph = load_graph()
    add_travel_time(graph)
    add_scenic_weights(graph)
    add_composite_cost(graph, alpha=0.5)  # TODO: tune alpha or use profile

    # Compute route (use 'scenic_cost' if extra_minutes > 0, else 'travel_time')
    weight = "scenic_cost" if extra_minutes > 0 else "travel_time"
    result = find_route(tuple(start_coords), tuple(end_coords), graph, weight=weight)

    # Build GeoJSON LineString for the route
    coords = [
        [graph.nodes[n]["x"], graph.nodes[n]["y"]]
        for n in result["nodes"]
    ]
    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords
        },
        "properties": {
            "cost": result["cost"],
            "weight": weight
        }
    }

    # Scenic breakdown: sum scenic_score and travel_time for each edge
    scenic_sum = 0.0
    time_sum = 0.0
    for u, v in zip(result["nodes"], result["nodes"][1:]):
        data = graph.get_edge_data(u, v, default={})
        # If multiple edges, pick the first
        if isinstance(data, dict) and 0 in data:
            data = data[0]
        scenic_sum += float(data.get("scenic_score", 0.0))
        time_sum += float(data.get("travel_time", 0.0))

    # Get street names for the route
    from main import get_street_distances_from_path
    street_segments = get_street_distances_from_path(graph, result["nodes"])

    # Map cardinal direction to symbol
    direction_symbols = {
        'N': '↑', 'S': '↓', 'E': '→', 'W': '←',
        'NE': '↗', 'NW': '↖', 'SE': '↘', 'SW': '↙'
    }
    street_breakdown = []
    for seg in street_segments:
        name, miles, direction = seg
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
        "profile": profile
    }
