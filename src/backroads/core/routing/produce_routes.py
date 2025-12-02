# #!/usr/bin/env python3
from typing import List, Tuple
import networkx as nx
import osmnx as ox

from backroads.core.data.graph import load_graph
from backroads.core.routing.weighting import add_travel_time, add_scenic_weights, add_composite_cost
from backroads.core.routing.pathfinding import find_route, _nearest_node, _haversine_distance
from backroads.core.utils.streets import get_street_distances_from_path, print_route_street_names


'''
Produce Routes: 
    - Finds k-shortest routes
    - Ranks k routes
    - Returns top routes with directions and street names of the top route 
'''
def compute_route(graph, origin, destination, extra_minutes, scenic_by_type, natural_by_type, profile="default"):
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
        routes = k_candidate_routes(graph, origin, destination,
                                    weight="scenic_cost", k=10)

        if not routes:
            # fallback to fastest if something weird happens
            chosen_nodes = fastest_nodes
            chosen_cost = fastest_result["cost"]
            chosen_weight = "travel_time"
        else:
            allowed_time = fastest_time + extra_minutes * 60.0
            time_budget_factor = allowed_time / fastest_time

            ranked = rank_routes(graph, routes,
                                 time_budget_factor=time_budget_factor)

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

    # street_breakdown (same logic)
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
        "start": list(origin),
        "end": list(destination),
        "extra_minutes": extra_minutes,
        "profile": profile,
        "weights_used": {
            "scenic_by_type": scenic_by_type,
            "natural_by_type": natural_by_type,
        },
    }
# NOT kth shortest paths algo, this is literally returning more than 1 (k) routes
def k_candidate_routes(
    graph: nx.MultiDiGraph,
    origin: Tuple[float, float],
    destination: Tuple[float, float],
    weight: str = "scenic_cost",
    k: int = 10,  # number of routes generated
) -> List[List[int]]:
    """
    return up to k simple paths (lists of node ids) from origin→destination
    ordered by total 'weight'
    """
    # nearest_nodes expects (x=lon, y=lat)
    o = ox.nearest_nodes(graph, origin[1], origin[0])
    d = ox.nearest_nodes(graph, destination[1], destination[0])

    # Convert MultiDiGraph -> DiGraph for this weight
    simple = _to_simple_digraph(graph, weight=weight)

    gen = nx.shortest_simple_paths(simple, o, d, weight=weight)

    routes: List[List[int]] = []
    for i, path in enumerate(gen):
        if i >= k:
            break
        routes.append(path)
    return routes

def path_time(graph: nx.MultiDiGraph, path: List[int]) -> float:
    """sum edge['travel_time'] along a node path (total time for route)"""
    total = 0.0
    for u, v in zip(path[:-1], path[1:]):
        total += _edge_attr(graph, u, v, "travel_time", 0.0)
    return total

def path_scenic_avg(graph: nx.MultiDiGraph, path: List[int]) -> float:
    """avg edge['scenic_score'] along a node path"""
    vals: List[float] = []
    for u, v in zip(path[:-1], path[1:]):
        vals.append(_edge_attr(graph, u, v, "scenic_score", 0.5))
    return (sum(vals) / len(vals)) if vals else 0.0

# takes routes generated by k paths function at top
# IMPORTANT: look at time_budget_factor
def rank_routes(
    graph: nx.MultiDiGraph,
    routes: List[List[int]],
    time_budget_factor: float = 2.00,  # 1.30 means willing to allow times slower by up to 30%
) -> List[Tuple[List[int], float, float]]:
    """
    keeps routes with total time less than or equal to fastest_time times budget factor
    sort those routes by scenic average in descending order

    Returns:
        List of tuples: (path, scenic_avg, time_seconds)
    """
    if not routes:
        return []

    times = [path_time(graph, r) for r in routes]
    fastest_time = min(times)

    kept: List[Tuple[List[int], float, float]] = []
    for r, t in zip(routes, times):
        if t <= fastest_time * time_budget_factor:
            kept.append((r, path_scenic_avg(graph, r), t))

    kept.sort(key=lambda x: x[1], reverse=True)  # scenic desc
    return kept

def find_and_show_ranked_routes(origin, destination, k=5, time_budget_factor=1.5):
    """
    Use k_shortest_routes and rank_routes, then print street names for each.
    
    Args:
        origin: (lat, lon) tuple for starting point
        destination: (lat, lon) tuple for ending point
        k: Number of route alternatives to find
        time_budget_factor: Max time multiplier (1.5 = 50% longer than fastest)
    """
    # Load and prepare the graph with all weight types
    print("Loading road network...")
    graph = load_graph()
    add_travel_time(graph)
    add_scenic_weights(graph)
    add_composite_cost(graph)
    
    print(f"Finding routes from {origin} to {destination}...")
    
    # Step 1: k_shortest_routes
    routes = k_candidate_routes(graph, origin, destination, weight="scenic_cost", k=k)
    print(f"k_candidate_routes found: {len(routes)} routes")
 
    # Step 2: rank_routes  
    ranked_routes = rank_routes(graph, routes, time_budget_factor=time_budget_factor)
    print(f"rank_routes kept: {len(ranked_routes)} routes within time budget")
    
    # Step 3: Show summary for all candidates, then detailed streets for top route
    if ranked_routes:
        # Show summary for all candidates
        print("\nAll candidate routes:")
        for i, (path, scenic_avg, time_seconds) in enumerate(ranked_routes, 1):
            print(f"ROUTE {i} - Scenic: {scenic_avg:.3f} | Time: {time_seconds/60:.1f} min")
        
        # Show detailed street names for top route only
        top_path, scenic_avg, time_seconds = ranked_routes[0]
        print(f"\nTOP ROUTE - Scenic: {scenic_avg:.3f} | Time: {time_seconds/60:.1f} min")
        print_route_street_names(graph, top_path)

        # visualize_route(
        #     graph, 
        #     top_path, 
        #     save_path="outputs/top_route.png",  
        #     show=True
        # )
    else:
        print("No routes found within time budget!")
    
    return ranked_routes


# --- Helpers ---
def _to_simple_digraph(G: nx.MultiDiGraph, weight: str) -> nx.DiGraph:
    """
    Collapse parallel edges to a single DiGraph edge per (u,v),
    keeping the edge with the MINIMUM value of `weight`.
    """
    H = nx.DiGraph()
    H.add_nodes_from(G.nodes(data=True))
    for u, v, key, data in G.edges(keys=True, data=True):
        w = float(data.get(weight, float("inf")))
        if H.has_edge(u, v):
            if w < float(H[u][v].get(weight, float("inf"))):
                H[u][v].clear()
                H[u][v].update(data)
        else:
            H.add_edge(u, v, **data)
    return H

def _edge_attr(G, u, v, attr: str, default: float) -> float:
    """
    Get an edge attribute for either a DiGraph (single edge) or
    a MultiDiGraph (parallel edges). For MultiDiGraph, we take the
    first edge’s attr; tweak if you prefer a different tie-breaker.
    """
    ed = G.get_edge_data(u, v)
    if ed is None:
        return default

    # DiGraph: ed is a flat attr dict
    if isinstance(ed, dict) and attr in ed:
        return float(ed.get(attr, default))

    # MultiDiGraph: ed is {key: {attrs}}
    if isinstance(ed, dict):
        first = next(iter(ed.values()))
        return float(first.get(attr, default))

    return default