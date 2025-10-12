import networkx as nx
import osmnx as ox

from math import radians, sin, cos, sqrt, atan2

from backroads.core.graph_io import load_graph


def _resolve_speed_kph(value, default: float) -> float:
    """Normalize OSM speed values (including strings like '45 mph')."""
    if value is None:
        return default

    if isinstance(value, (list, tuple)):
        for candidate in value:
            resolved = _resolve_speed_kph(candidate, None)
            if resolved:
                return resolved
        return default

    if isinstance(value, str):
        text = value.strip().lower()
        multiplier = 1.0
        if text.endswith("mph"):
            multiplier = 1.60934
            text = text[:-3]
        elif text.endswith("km/h"):
            text = text[:-4]
        digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        if digits:
            try:
                return float(digits) * multiplier
            except ValueError:
                return default
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _edge_travel_time(data, default_speed_kph: float = 35.0) -> float:
    speed_value = data.get("speed_kph") or data.get("maxspeed")
    speed_kph = _resolve_speed_kph(speed_value, default_speed_kph)
    speed_mps = max(speed_kph * 1000 / 3600, 1e-3)
    length_m = float(data.get("length", 0.0) or 0.0)
    return length_m / speed_mps if length_m else 0.0


def prepare_graph():
    graph = load_graph()
    for _, _, data in graph.edges(data=True):
        if "travel_time" not in data:
            data["travel_time"] = _edge_travel_time(data)
    return graph

def _nearest_node(graph, point):
    lat, lon = point
    try:
        return ox.nearest_nodes(graph, lon, lat)
    except ImportError:
        # Fall back to manual search (slower but keeps dependency surface tiny).
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
            raise ValueError("Graph has no geolocated nodes to snap against.")
        return closest


def find_fastest_route(origin, destination, graph=None):
    """Return shortest path (by travel time) between two (lat, lon) points."""
    if graph is None:
        graph = prepare_graph()
    
    origin_node = _nearest_node(graph, origin)
    destination_node = _nearest_node(graph, destination)

    path = nx.shortest_path(
        graph, 
        source=origin_node, 
        target=destination_node, 
        weight="travel_time"
    )
    travel_time = nx.shortest_path_length(
        graph,
        source=origin_node,
        target=destination_node,
        weight="travel_time"
    )

    return {
        "nodes": path,
        "travel_time_seconds": travel_time,
    }
def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in meters between two lat/lon points."""
    r = 6371000  # mean Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)

    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c
