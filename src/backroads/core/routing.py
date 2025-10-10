import networkx as nx
import osmnx as ox

from backroads.core.graph_io import load_graph


def _edge_travel_time(data, default_speed_kph: float = 35.0) -> float:
    speed_kph = data.get("speed_kph") or data.get("maxspeed")
    if isinstance(speed_kph, (list, tuple)):
        speed_kph = speed_kph[0]
    speed_kph = float(speed_kph) if speed_kph else default_speed_kph
    speed_mps = max(speed_kph * 1000 / 3600, 1e-3)
    length_m = data.get("length", 0.0)
    return length_m / speed_mps if length_m else 0.0


def prepare_graph():
    graph = load_graph()
    for _, _, data in graph.edges(data=True):
        if "travel_time" not in data:
            data["travel_time"] = _edge_travel_time(data)
    return graph

def find_fastest_route(origin, destination, graph=None):
    """Return shortest path (by travel time) between two (lat, lon) points."""
    if graph is None:
        graph = prepare_graph()
    # logic to come
