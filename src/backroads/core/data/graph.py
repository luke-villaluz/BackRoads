import osmnx as ox
from backroads.config import GRAPH_PATH, ensure_directories


"""
graph.py

Downloads the graph of SLO county from OpenStreetMaps

"""
def load_graph():
    ensure_directories()
    if GRAPH_PATH.exists():
        print("loading cached graph from %s", GRAPH_PATH)
        return ox.load_graphml(GRAPH_PATH)
    print("downloading SLO county grpah")
    graph = ox.graph_from_place(
        "San Luis Obispo County, California, USA",
        network_type="drive",
    )
    ox.save_graphml(graph, GRAPH_PATH)
    print("saved graph to %s", GRAPH_PATH)
    return graph
