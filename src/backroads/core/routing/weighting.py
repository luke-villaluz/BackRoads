# weighting.py
'''
Weighting: 
Contains functions for assigned edge weights and composite costs
to the road network graph 

Includes:
    - Travel time: travel time between nodes 
    - Scenic score: scenic weights between nodes
    - Scenic cost: Calculating composite cost of scenery and time betweem nodes
'''
from backroads.core.data.graph import load_graph
from typing import Optional, Dict, Any


# Module-level defaults so callers (API) can present them to users
DEFAULT_SCENIC_BY_TYPE = {
    "motorway": 0.05,
    "trunk": 0.25,
    "primary": 0.40,
    "secondary": 0.55,
    "tertiary": 0.70,
    "residential": 0.85,
    "service": 0.70,
    "unclassified": 0.90,
}

DEFAULT_NATURAL_BY_TYPE = {
    "grassland": 0.5, "heath": 0.5, "scrub": 0.5, "tree": 0.5,
    "tree_row": 0.5, "wood": 0.5, "bay": 0.5, "beach": 0.5,
    "cape": 0.5, "coastline": 0.5, "hot_spring": 0.5, "spring": 0.5,
    "water": 0.5, "wetland": 0.5, "arch": 0.5, "bare_rock": 0.5,
    "cliff": 0.5, "dune": 0.5, "hill": 0.5, "peak": 0.5, "ridge": 0.5,
    "rock": 0.5, "saddle": 0.5, "sand": 0.5, "scree": 0.5, "stone": 0.5,
    "valley": 0.5
}


def add_travel_time(graph) -> None:
    """compute travel times of edges in seconds (different for different "highway" types)"""
    # default speeds in km/h by osm road type
    SPEEDS_BY_TYPE = {
        "motorway": 100,
        "trunk": 90,
        "primary": 80,
        "secondary": 65,
        "tertiary": 55,
        "residential": 40,
        "service": 30,
        "unclassified": 35
    }
    
    # used if highway type is not in the dict above
    DEFAULT_KPH = 35.0

    for _, _, data in graph.edges(data=True):
        #cases where highway might be a list
        highway = data.get("highway")
        if isinstance(highway, list):
            highway = highway[0]
        #if no road type is found
        speed_kph = SPEEDS_BY_TYPE.get(highway, DEFAULT_KPH)
        speed_mps = speed_kph * 1000 / 3600  # convert to m/s
        #osm edge length attributes
        length_m = float(data.get("length", 0.0) or 0.0)
        # travel time in seconds
        travel_time = length_m / max(speed_mps, 1e-3)
        # attach travel time to the edge
        data["travel_time"] = travel_time


def add_scenic_weights(graph, scenic_by_type: Optional[Dict[str, float]] = None, natural_by_type: Optional[Dict[str, Any]] = None) -> None:
    """compute edge['scenic_score'] in [0,1] based on road type (and optional bonuses based off short (local) roads).

    Accepts optional overrides for scenic_by_type and natural_by_type. If not provided,
    default mappings are used (kept for backwards compatibility).
    """

    # use module-level defaults unless overrides were provided
    SCENIC = scenic_by_type if scenic_by_type is not None else DEFAULT_SCENIC_BY_TYPE
    NATURAL = natural_by_type if natural_by_type is not None else DEFAULT_NATURAL_BY_TYPE

    for u, v, data in graph.edges(data=True):
        hwy = data.get("highway")
        if isinstance(hwy, (list, tuple)):
            hwy = hwy[0]
        base = float(SCENIC.get(hwy, 0.5))

    
        naturals = []
        naturals += graph.nodes[u].get("natural_types", []) or []
        naturals += graph.nodes[v].get("natural_types", []) or []

        nat_sum = 0.0
        for nat in naturals:
            if nat in NATURAL:
                val = NATURAL[nat]
                if val is not None:
                    nat_sum += float(val)

        total = base + nat_sum

        data["scenic_score"] = total

    # ------ NORMALIZATION (z-score  min/max) ------
    vals: list[float] = []
    edges = []
    for _, _, d in graph.edges(data=True):
        if "scenic_score" in d:
            edges.append(d)
            vals.append(float(d["scenic_score"]))

    if not vals:
        return

    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = var ** 0.5

    if std > 0:
        zscores = [(v - mean) / std for v in vals]
    else:
        zscores = [0.0 for _ in vals]

    minz = min(zscores)
    maxz = max(zscores)

    if maxz > minz:
        scaled = [(z - minz) / (maxz - minz) for z in zscores]
    else:
        # all identical -> everything becomes 0.5
        scaled = [0.5 for _ in zscores]

    for d, val in zip(edges, scaled):
        d["scenic_score"] = float(val)

def add_composite_cost(graph, alpha: float = 0.5) -> None:
    # First find a rough scale factor for travel times
    times = [
        float(data.get("travel_time", 0.0))
        for _, _, data in graph.edges(data=True)
    ]
    if not times:
        return

    max_time = max(times) or 1.0  

    for _, _, data in graph.edges(data=True):
        travel_time = float(data.get("travel_time", 0.0))
        scenic = float(data.get("scenic_score", 0.5))

        # Normalize time to [0,1] by dividing by max_time
        norm_time = travel_time / max_time  # ~ 0–1

        # Now both terms are ~ 0–1
        data["scenic_cost"] = alpha * norm_time + (1 - alpha) * (1 - scenic)


# graph = load_graph()
# add_scenic_weights(graph)