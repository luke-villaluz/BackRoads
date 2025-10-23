# weighting.py

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


def add_scenic_weights(graph) -> None:
    """compute edge['scenic_score'] in [0,1] based on road type (and optional bonuses based off short (local) roads)"""

    # base scenic values for different highway types
    SCENIC_BY_TYPE = {
        "motorway": 0.15,
        "trunk": 0.25,
        "primary": 0.40,
        "secondary": 0.55,
        "tertiary": 0.70,
        "residential": 0.85,
        "service": 0.70,
        "unclassified": 0.90
        # you can add more if you find them later
    }

    # loop through every edge in graph
    for _, _, data in graph.edges(data=True):

        # get highway type (sometimes list)
        hwy = data.get("highway")
        if isinstance(hwy, (list, tuple)):
            hwy = hwy[0]

        # assign a base scenic score, default to 0.5
        base_score = SCENIC_BY_TYPE.get(hwy, 0.5)

        # short road bonus (likely a local road)
        length_m = float(data.get("length", 0.0) or 0.0)
        if length_m < 120.0:
            base_score += 0.05  # short, likely local road

        # possible curve bonus later
        # wiggle = ...
        # base_score += 0.15 * wiggle

        # clamp between 0 and 1
        scenic = max(0.0, min(1.0, base_score))
        data["scenic_score"] = scenic

def add_composite_cost(graph, alpha: float = 0.6) -> None:
    """blend time and scenic into edge['scenic_cost']"""
    for _, _, data in graph.edges(data=True):
        travel_time = float(data.get("travel_time", 0.0))
        scenic = float(data.get("scenic_score", 0.5))
        # lower scenic_score should increase cost (less beautiful)
        data["scenic_cost"] = alpha * travel_time + (1 - alpha) * (1 - scenic)
