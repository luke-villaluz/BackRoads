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
        "motorway": 0.05,
        "trunk": 0.25,
        "primary": 0.40,
        "secondary": 0.55,
        "tertiary": 0.70,
        "residential": 0.85,
        "service": 0.70,
        "unclassified": 0.90
        # you can add more if you find them later
    }

    NATURAL_BY_TYPE = {
        # Land & vegetation related
        "grassland": None,
        "heath": None,
        "scrub": None,
        "tree": None,
        "tree_row": None,
        "wood": None,

        # Water related
        "bay": None,
        "beach": None,
        "cape": None,
        "coastline": None,

        "hot_spring": None,
        "spring": None,
        "water": None,
        "wetland": None,

        # Geology related
        "arch": None,
        "bare_rock": None,
        "cliff": None,
        "dune": None,
        "hill": None,
        "peak": None,
        "ridge": None,
        "rock": None,
        "saddle": None,
        "sand": None,
        "scree": None,
        "stone": None,
        "valley": None
    }


    # loop through every edge in graph
    count = 0

    for t, s, data in graph.edges(data=True):
        count += 1
        print(f"Processing edge {count}: {t} -> {s}")
        if count == 10:
            break

        # get highway type (sometimes list)
        hwy = data.get("highway")
        if isinstance(hwy, (list, tuple)):
            hwy = hwy[0]

        # assign a base scenic score, default to 0.5
        base_score = SCENIC_BY_TYPE.get(hwy, 0.5)

        target = graph.nodes[t]
        source = graph.nodes[s]
        print(target)
        print(source)
        
        for i in range(len(target.get("natural_types"))):
            base_score += 0.05
        
        for i in range(len(source.get("natural_types"))):
            base_score += 0.05

        # short road bonus (likely a local road)
        length_m = float(data.get("length", 0.0) or 0.0)
        if length_m < 120.0:
            base_score += 0.05  # short, likely local road

        # possible curve bonus later
        # wiggle = ...
        # base_score += 0.15 * wiggle

        # clamp between 0 and 1
       
        data["scenic_score"] = base_score

    # simple standardization (z-score) across all edges' scenic_score
    vals = []
    edge_datas = []
    for u, v, data in graph.edges(data=True):
        if "scenic_score" in data:
            edge_datas.append(data)
            try:
                vals.append(float(data["scenic_score"]))
            except Exception:
                vals.append(0.0)
    print("\t\t VALS:",vals)

    if vals:
        mean = sum(vals) / len(vals)
        # population std
        var = sum((x - mean) ** 2 for x in vals) / len(vals)
        std = var ** 0.5
        print(f"Standardizing scenic_score: mean={mean:.6f}, std={std:.6f}")
        # compute z-scores
        if std > 0:
            zscores = [ (orig - mean) / std for orig in vals ]
        else:
            zscores = [0.0 for _ in vals]

        # min-max scale z-scores into [0,1]
        minz = min(zscores)
        maxz = max(zscores)
        if maxz > minz:
            scaled01 = [ (z - minz) / (maxz - minz) for z in zscores ]
        else:
            # all equal -> map to 0.5
            scaled01 = [0.5 for _ in zscores]

        print(f"Mapping z-scores to [0,1]: minz={minz:.6f}, maxz={maxz:.6f}")

        for data, val in zip(edge_datas, scaled01):
            data["scenic_score"] = float(val)
            print(float(val))

def add_composite_cost(graph, alpha: float = 0.6) -> None:
    """blend time and scenic into edge['scenic_cost']"""
    for _, _, data in graph.edges(data=True):
        travel_time = float(data.get("travel_time", 0.0))
        scenic = float(data.get("scenic_score", 0.5))
        # lower scenic_score should increase cost (less beautiful)
        data["scenic_cost"] = alpha * travel_time + (1 - alpha) * (1 - scenic)

# graph = load_graph()
# add_scenic_weights(graph)