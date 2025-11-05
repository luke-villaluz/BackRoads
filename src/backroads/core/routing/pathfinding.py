import networkx as nx
import osmnx as ox
from math import radians, sin, cos, sqrt, atan2

# default weight is travel time, essentially just takes fastest route
def find_route(origin, destination, graph, weight="scenic_cost"):
    """return shortest path between two (lat, lon) points (by travel time) """
    origin_node = _nearest_node(graph, origin)
    destination_node = _nearest_node(graph, destination)
    path = nx.shortest_path(
        graph, 
        source=origin_node, 
        target=destination_node, 
        weight=weight
    )
    cost = nx.shortest_path_length(
        graph,
        source=origin_node,
        target=destination_node,
        weight=weight
    )
    return {
        "nodes": path,
        "cost": cost,
    }

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

# shout out cursor
def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in meters between two lat/lon points."""
    r = 6371000  # mean Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)

    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c