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

def _node_naturals(graph, node_id):
    raw = graph.nodes[node_id].get("natural_types", [])
    if not raw:
        return []

    if isinstance(raw, str):
        # split "beach,cliff,coastline" -> ["beach", "cliff", "coastline"]
        return [s.strip() for s in raw.split(",") if s.strip()]

    # assume it is already a list/iterable
    return list(raw)


def add_scenic_weights(
    graph,
    scenic_by_type: Optional[Dict[str, float]] = None,
    natural_by_type: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Compute a raw scenic_score per edge based on:
      - road type (SCENIC)
      - natural features at its endpoints (NATURAL)

    scenic_score is NOT normalized here; add_composite_cost will normalize.
    """

    SCENIC = scenic_by_type if scenic_by_type is not None else DEFAULT_SCENIC_BY_TYPE
    NATURAL = natural_by_type if natural_by_type is not None else DEFAULT_NATURAL_BY_TYPE

    for u, v, data in graph.edges(data=True):

        hwy = data.get("highway")
        if isinstance(hwy, (list, tuple)):
            hwy = hwy[0]
        base = float(SCENIC.get(hwy, 0.5))


        naturals = _node_naturals(graph, u) + _node_naturals(graph, v)

        nat_sum = 0.0
        for nat in naturals:
            if nat in NATURAL:
                val = NATURAL[nat]
                if val is not None:
                    nat_sum += float(val)
        print(naturals, nat_sum)

        BOOST = 1.5   # natural dominance factor (tune 1.0–3.0)
        total = base * (1.0 + nat_sum)**BOOST
        data["scenic_score"] = total


# def add_composite_cost(graph, alpha: float = 0.5) -> None:
#     """
#     Compute edge['scenic_cost'] as a composite of normalized travel_time and
#     normalized scenic_score:

#         scenic_cost = alpha * norm_time + (1 - alpha) * (1 - norm_scenic)

#     where:
#         - norm_time   ∈ [0,1], higher = slower
#         - norm_scenic ∈ [0,1], higher = more scenic

#     Lower scenic_cost is better for routing.
#     """
#     # Collect time and scenic values for normalization
#     times: list[float] = []
#     scenics: list[float] = []

#     for _, _, data in graph.edges(data=True):
#         times.append(float(data.get("travel_time", 0.0)))
#         scenics.append(float(data.get("scenic_score", 0.0)))

#     if not times or not scenics:
#         return

#     max_time = max(times) or 1.0

#     scenic_min = min(scenics)
#     scenic_max = max(scenics)

#     # Avoid division by zero if all scenic_scores are identical
#     scenic_range = scenic_max - scenic_min if scenic_max > scenic_min else None

#     for _, _, data in graph.edges(data=True):
#         travel_time = float(data.get("travel_time", 0.0))
#         scenic = float(data.get("scenic_score", 0.0))

#         # Normalize time to [0,1]
#         norm_time = travel_time / max_time  # larger = slower

#         # Normalize scenic_score to [0,1] across this graph
#         if scenic_range is not None:
#             norm_scenic = (scenic - scenic_min) / scenic_range
#         else:
#             norm_scenic = 0.5  # everything same → treat as neutral

#         # Composite cost: smaller is better
#         data["scenic_cost"] = alpha * norm_time + (1.0 - alpha) * (1.0 - norm_scenic)
def add_composite_cost(graph) -> None:
    """
    Define a purely scenic cost:

        scenic_cost = length / (scenic_score + ε)

    So:
      - higher scenic_score → smaller scenic_cost
      - longer edges are still a bit more expensive
    """
    for _, _, data in graph.edges(data=True):
        length = float(data.get("length", 0.0))
        scenic = float(data.get("scenic_score", 0.0))

        data["scenic_cost"] = length / (scenic + 1e-6)



# graph = load_graph()
# add_scenic_weights(graph)