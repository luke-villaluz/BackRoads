from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
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
from backroads.core.utils.visualize_route import visualize
from backroads.core.routing.directions import get_directions
from backroads.core.routing.breakdown import get_scenic_breakdown
from backroads.core.utils.geo import validate_coord_in_bounds, parse_coord
from fastapi.responses import StreamingResponse
from backroads.core.routing.profiles import (
    load_profile,
    save_profile,
    list_profiles,
    initialize_preset_profiles,
)

# backroads/api/main.py
import logging

logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

CURRENT_SCENIC_BY_TYPE = dict(DEFAULT_SCENIC_BY_TYPE)
CURRENT_NATURAL_BY_TYPE = dict(DEFAULT_NATURAL_BY_TYPE)
graph = None  # Initialize graph as None


class LoadGraphRequest(BaseModel):
    annotate: bool = Field(
        True,
        description="Whether to annotate nodes with nearby natural features."
    )
    place_name: Optional[str] = Field(
        "San Luis Obispo County, California, USA",
        description="OSM place name to use when downloading the graph if no cache exists."
    )
    save_annotated: bool = Field(
        True,
        description="Whether to save an annotated GraphML file next to the original."
    )


class LoadGraphResponse(BaseModel):
    status: str
    nodes: int
    edges: int
    annotate: bool
    place_name: str

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

@app.on_event("startup")
async def startup_event():
    """Initialize preset profiles on startup."""
    try:
        initialize_preset_profiles()
    except Exception as e:
        logging.error(f"Failed to initialize preset profiles: {e}", exc_info=True)

class RouteRequest(BaseModel):
    start: Coordinate 
    end: Coordinate   
    extra_minutes: Optional[float] = 0.0
    profile: Optional[str] = "default"

class RouteResponse(BaseModel):
    route: Dict[str, Any]
    directions: Any
    breakdown: Dict[str, Any]
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

class VisualizeRequest(BaseModel):
    nodes: list[int]

class ProfileCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the profile")
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

class ProfileResponse(BaseModel):
    name: str
    scenic_by_type: Dict[str, float]
    natural_by_type: Dict[str, float]

class ProfileListResponse(BaseModel):
    profiles: List[str]

@app.post(
    "/graph/load",
    tags=["Admin"],
    summary="Load or reload the SLO County routing graph",
)
def load_graph_endpoint():
    """
    Load (or reload) the routing graph for
    San Luis Obispo County, California, USA.

    Recomputes travel time, scenic weights, and composite cost
    using the current weight settings.
    """
    global graph, CURRENT_SCENIC_BY_TYPE, CURRENT_NATURAL_BY_TYPE

    try:

        # Always SLO, always annotated, always save annotated version
        graph = load_graph(
            annotate=True,
            place_name="San Luis Obispo County, California, USA",
            save_annotated=True,
        )

        if graph is None:
            raise RuntimeError("load_graph returned None")

        # Recompute weights with current mappings
        add_travel_time(graph)
        add_scenic_weights(
            graph,
            scenic_by_type=CURRENT_SCENIC_BY_TYPE,
            natural_by_type=CURRENT_NATURAL_BY_TYPE,
        )
        add_composite_cost(
            graph,
            lam = 0.9
        )
        #add_composite_cost(graph, alpha=0.5)

        nodes = graph.number_of_nodes()
        edges = graph.number_of_edges()


        node_lats = [data["y"] for _, data in graph.nodes(data=True)]
        node_lons = [data["x"] for _, data in graph.nodes(data=True)]

        GRAPH_BOUNDS = {
            "min_lat": min(node_lats),
            "max_lat": max(node_lats),
            "min_lon": min(node_lons),
            "max_lon": max(node_lons),
        }

        return {
            "status": "ok",
            "message": "Graph loaded for San Luis Obispo County, California, USA",
            "nodes": nodes,
            "edges": edges,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading graph: {e}",
        )


# Accepts query parameters for now; can switch to POST/JSON if needed
@app.post(
    "/route",
    tags=["Routing"],
    summary="Compute a scenic or fastest route",
    response_model=RouteResponse,
)
def compute_route_endpoint(req: RouteRequest):
    """
    Compute a route between two coordinates, optionally allowing extra minutes
    for a more scenic path. Returns:
    - route: GeoJSON + metadata (and nodes, if your compute_route adds them)
    - directions: step-by-step street directions
    - breakdown: scenic score, time, and other stats
    """
    if graph is None:
        raise HTTPException(status_code=500, detail="Routing graph is not initialized")

    # Build origin/destination from Coordinate objects
    origin = (req.start.lat, req.start.lon)
    destination = (req.end.lat, req.end.lon)

    # Validate coords are within your graph bounds
    try:
        validate_coord_in_bounds(origin[0], origin[1], "Origin")
        validate_coord_in_bounds(destination[0], destination[1], "Destination")
    except ValueError as e:
        # Coordinate validation failure
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Likely GRAPH_BOUNDS / initialization issue
        raise HTTPException(status_code=500, detail=str(e))

    # Load profile weights if a profile is specified
    try:
        if req.profile and req.profile != "default":
            profile_data = load_profile(req.profile)
            scenic_weights = profile_data.get("scenic_by_type", DEFAULT_SCENIC_BY_TYPE)
            natural_weights = profile_data.get("natural_by_type", DEFAULT_NATURAL_BY_TYPE)
        else:
            scenic_weights = CURRENT_SCENIC_BY_TYPE
            natural_weights = CURRENT_NATURAL_BY_TYPE
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading profile: {e}",
        )

    try:
        route = compute_route(
            graph,
            origin,
            destination,
            req.extra_minutes,
            scenic_weights,
            natural_weights,
            req.profile,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error computing route: {e}",
        )

    # route["nodes"] must be present in your compute_route return
    try:
        street_data = get_directions(graph, route["nodes"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error computing directions: {e}",
        )

    try:
        stats = get_scenic_breakdown(graph, route["nodes"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error computing scenic breakdown: {e}",
        )

    return RouteResponse(route=route, directions=street_data, breakdown=stats)

@app.post(
    "/weights",
    tags=["Customization"],
    summary="Update scenic and natural feature weights",
    response_model=WeightsResponse,
)
def apply_weights(payload: WeightsRequest):
    """
    Update the per-type scenic and natural weights used in routing.
    Omitted keys fall back to defaults.
    """
    global graph, CURRENT_SCENIC_BY_TYPE, CURRENT_NATURAL_BY_TYPE

    try:
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
        add_composite_cost(graph, lam = 0.9)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating weights: {e}",
        )

    return WeightsResponse(scenic_by_type=scenic, natural_by_type=natural)


@app.post(
    "/profiles",
    tags=["Customization"],
    summary="Create or update a custom profile",
    response_model=ProfileResponse,
)
def create_profile(payload: ProfileCreateRequest):
    """
    Create or update a custom profile with a name. Profiles can be reused
    by specifying the profile name in route requests.
    """
    try:
        # Start from defaults
        scenic = dict(DEFAULT_SCENIC_BY_TYPE)
        natural = dict(DEFAULT_NATURAL_BY_TYPE)

        # Apply user overrides (if provided)
        if payload.scenic_by_type:
            scenic.update(payload.scenic_by_type)

        if payload.natural_by_type:
            natural.update(payload.natural_by_type)

        # Save profile to disk
        save_profile(payload.name, scenic, natural)

        return ProfileResponse(
            name=payload.name,
            scenic_by_type=scenic,
            natural_by_type=natural,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating profile: {e}",
        )

@app.get(
    "/profiles",
    tags=["Customization"],
    summary="List all available profiles",
    response_model=ProfileListResponse,
)
def list_profiles_endpoint():
    """
    Get a list of all saved custom profiles.
    """
    try:
        profiles = list_profiles()
        return ProfileListResponse(profiles=profiles)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing profiles: {e}",
        )


@app.post(
    "/visualize",
    tags=["Visualization"],
    summary="Render a route (given node IDs) as a PNG image",
    responses={200: {"content": {"image/png": {}}, "description": "Route image"}},
)
def visualize_route(req: VisualizeRequest):
    if graph is None:
        raise HTTPException(status_code=500, detail="Routing graph is not initialized")

    if not req.nodes:
        raise HTTPException(status_code=400, detail="nodes list cannot be empty")

    try:
        img_bytes = visualize(graph, req.nodes, show=False)
    except ValueError as e:
        # e.g. "Route nodes list is empty!"
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering visualization: {e}")

    return StreamingResponse(img_bytes, media_type="image/png")