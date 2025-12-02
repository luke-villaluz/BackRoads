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
from uuid import uuid4

ROUTE_CACHE = {}

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
# @app.post(
#     "/route",
#     tags=["Routing"],
#     summary="Compute a scenic or fastest route",
#     operation_id="compute_route"
# )
# def route(req: RouteRequest):
#     global graph, CURRENT_SCENIC_BY_TYPE, CURRENT_NATURAL_BY_TYPE

#     if graph is None:
#         raise HTTPException(status_code=500, detail="Routing graph is not initialized")

#     origin = parse_coord(req.start)
#     destination = parse_coord(req.end)

#     try:
#         validate_coord_in_bounds(origin[0], origin[1], "Origin")
#         validate_coord_in_bounds(destination[0], destination[1], "Destination")
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
   
#     return compute_route(
#         graph,
#         origin,
#         destination,
#         req.extra_minutes,
#         CURRENT_SCENIC_BY_TYPE,
#         CURRENT_NATURAL_BY_TYPE,
#         req.profile)
"""
POST Compute Route 
Response: GeoJSON route of coordinates 
"""
@app.post(
    "/route/compute",
    tags=["Routing"],
    summary="Compute a scenic or fastest route, returns GeoJSON Route",
    operation_id="compute_route"
)
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
    
    result = compute_route(
        graph,
        origin,
        destination,
        req.extra_minutes,
        CURRENT_SCENIC_BY_TYPE,
        CURRENT_NATURAL_BY_TYPE,
        req.profile
    )

    route_id = str(uuid4())
    ROUTE_CACHE[route_id] = result

    return { "route_id": route_id, **result }

"""
GET Directions 
Response: Street directions
"""
@app.get(
        "/route/{route_id}/directions",
        tags=["Routing"],
        summary="Get the street directions to the route",
        operation_id="route_directions"
        )
def route_directions(route_id: str):
    route = ROUTE_CACHE.get(route_id)
    if not route:
        raise HTTPException(404, "Route not found")

    street_data = get_directions(graph, route["nodes"])

    return {"route_id": route_id, "directions": street_data}

"""
GET Scenic Breakdown 
Response: scenic score and travel time 
"""
@app.get(
        "/route/{route_id}/breakdown",
        tags=["Routing"],
        summary="Get thebreakdown of the route: including scenic score, weights, and travel time in seconds ",
        operation_id="scenic_breakdown"
        )
def scenic_breakdown(route_id: str):
    route = ROUTE_CACHE.get(route_id)
    if not route:
        raise HTTPException(404, "Route not found")

    stats = get_scenic_breakdown(
        graph,
        route["nodes"]
    )

    return {
        "route_id": route_id,
        "breakdown": stats,
        "weights_used": {
            "scenic_by_type": CURRENT_SCENIC_BY_TYPE,
            "natural_by_type": CURRENT_NATURAL_BY_TYPE
        }
    }


@app.post("/weights", tags=["Customization"])
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
