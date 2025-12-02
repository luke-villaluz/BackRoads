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
from backroads.core.routing.produce_routes import compute_route
from backroads.core.routing.directions import get_directions
from backroads.core.routing.breakdown import get_scenic_breakdown
from backroads.core.utils.geo import validate_coord_in_bounds, parse_coord

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

node_lats = [data["y"] for _, data in graph.nodes(data=True)]
node_lons = [data["x"] for _, data in graph.nodes(data=True)]

GRAPH_BOUNDS = {
    "min_lat": min(node_lats),
    "max_lat": max(node_lats),
    "min_lon": min(node_lons),
    "max_lon": max(node_lons),
}



class Coordinate(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")

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
    start: Coordinate 
    end: Coordinate   
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
@app.post("/route")
def compute_route_endpoint(req: RouteRequest):
    global graph, CURRENT_SCENIC_BY_TYPE, CURRENT_NATURAL_BY_TYPE

    if graph is None:
        raise HTTPException(status_code=500, detail="Routing graph is not initialized")

    origin = parse_coord(req.start)
    destination = parse_coord(req.end)

    try:
        validate_coord_in_bounds(origin[0], origin[1], "Origin")
        validate_coord_in_bounds(destination[0], destination[1], "Destination")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    route = compute_route(
        graph,
        origin,
        destination,
        req.extra_minutes,
        CURRENT_SCENIC_BY_TYPE,
        CURRENT_NATURAL_BY_TYPE,
        req.profile
    )

    street_data = get_directions(graph, route["nodes"])
    stats = get_scenic_breakdown(graph, route["nodes"])
    return { "route": route, "directions": street_data, "breakdown": stats }

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
