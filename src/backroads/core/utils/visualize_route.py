import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

def visualize_route(graph: nx.Graph, route_nodes: list, save_path: str | Path = None, show: bool = True):

    if not route_nodes:
        raise ValueError("Route nodes list is empty!")

    # Draw the entire network lightly in gray
    fig, ax = ox.plot_graph(
        graph, 
        node_size=0, 
        edge_color="#cccccc", 
        edge_linewidth=0.5, 
        bgcolor="white",
        show=False,
        close=False
    )

    # Extract edges along the route
    route_edges = list(zip(route_nodes[:-1], route_nodes[1:]))
    
    # Draw the route in red with thicker edges
    nx.draw_networkx_edges(
        graph,
        pos={n: (data['x'], data['y']) for n, data in graph.nodes(data=True)},
        edgelist=route_edges,
        edge_color="red",
        width=2.5,
        ax=ax
    )
    
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Route visualization saved to {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()
