import networkx as nx
import osmnx as ox
from math import radians, sin, cos, sqrt, atan2

'''
Pathfinding: 
Finds a route between two coordinates using OpenStreetMap and NetworkX
Uses the edge weights assigned by the weighting module 

Algorithm: 
    - nx.shortest_path defaults to Dijkstra’s
'''

# default weight is travel time, essentially just takes fastest route
import networkx as nx
import osmnx as ox
from math import radians, sin, cos, sqrt, atan2

'''
Pathfinding: 
Finds a route between two coordinates using OpenStreetMap and NetworkX
Uses the edge weights assigned by the weighting module 

Algorithm: 
    - A* with straight-line (haversine) distance as heuristic
'''

# default weight is "scenic_cost", but can be any edge attribute
def find_route(origin, destination, graph, weight="scenic_cost"):
    """Return shortest path between two (lat, lon) points, using A*."""
    origin_node = _nearest_node(graph, origin)
    destination_node = _nearest_node(graph, destination)

    # A* path
    path = nx.astar_path(
        graph,
        source=origin_node,
        target=destination_node,
        heuristic=lambda u, v=destination_node: _node_distance_heuristic(graph, u, v),
        weight=weight,
    )

    # A* total path cost
    cost = nx.astar_path_length(
        graph,
        source=origin_node,
        target=destination_node,
        heuristic=lambda u, v=destination_node: _node_distance_heuristic(graph, u, v),
        weight=weight,
    )

    return {
        "nodes": path,
        "cost": cost,
    }

def _node_distance_heuristic(graph, u, v):
    """
    Heuristic for A*: straight-line distance between nodes u and v,
    based on their lat/lon stored as node attributes "y" (lat), "x" (lon).
    """
    lat1 = graph.nodes[u].get("y")
    lon1 = graph.nodes[u].get("x")
    lat2 = graph.nodes[v].get("y")
    lon2 = graph.nodes[v].get("x")

    # fallback if coords are missing (avoid breaking A*)
    if None in (lat1, lon1, lat2, lon2):
        return 0.0

    return _haversine_distance(lat1, lon1, lat2, lon2)

def _nearest_node(graph, point):
    lat, lon = point
    try:
        return ox.nearest_nodes(graph, lon, lat)
    except ImportError:
        # fall back to manual search
        closest = None
        best_dist = float("inf")
        for node_id, data in graph.nodes(data=True):
            node_lat = data.get("y")
            node_lon = data.get("x")
            if node_lat is None or node_lon is None:
                continue
            dist = _haversine_distance(lat, lon, node_lat, node_lon)
            if dist < best_dist:
                best_dist = dist
                closest = node_id
        if closest is None:
            raise ValueError("graph has no other nodes to connect to")
        return closest

def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in meters between two lat/lon points."""
    r = 6371000  # mean Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)

    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c
