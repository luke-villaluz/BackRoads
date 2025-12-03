import osmnx as ox
import networkx as nx
from pathlib import Path
import io
import matplotlib
matplotlib.use("Agg") 

import matplotlib.pyplot as plt

def visualize(graph: nx.Graph, route_nodes: list | Path = None, show: bool = True):
    if not route_nodes:
        raise ValueError("Route nodes list is empty!")

    fig, ax = ox.plot_graph(
        graph, 
        node_size=0, 
        edge_color="#cccccc", 
        edge_linewidth=0.5, 
        bgcolor="white",
        show=False,
        close=False,
    )

    route_edges = list(zip(route_nodes[:-1], route_nodes[1:]))
    pos = {n: (data["x"], data["y"]) for n, data in graph.nodes(data=True)}

    nx.draw_networkx_edges(
        graph,
        pos=pos,
        edgelist=route_edges,
        edge_color="red",
        width=1.0,
        arrowsize=4,
        ax=ax,
    )
    # zoom into route
    route_x = [pos[n][0] for n in route_nodes]
    route_y = [pos[n][1] for n in route_nodes]

    pad = 0.01  # Adjust if needed
    xmin, xmax = min(route_x) - pad, max(route_x) + pad
    ymin, ymax = min(route_y) - pad, max(route_y) + pad

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    if show:
        plt.show()
        plt.close(fig)
        return None

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
