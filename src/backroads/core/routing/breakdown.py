"""
Compute the scenic score and travel time for a given route.
"""
def get_scenic_breakdown(graph, nodes):
    total_scenic = 0.0
    total_time = 0.0

    for u, v in zip(nodes, nodes[1:]):
        data = graph.get_edge_data(u, v, default={})

        # handle MultiDiGraph edge format
        if isinstance(data, dict) and 0 in data:
            data = data[0]

        total_scenic += float(data.get("scenic_score", 0.0))
        total_time += float(data.get("travel_time", 0.0))

    return {
        "total_scenic_score": total_scenic,
        "total_travel_time_seconds": total_time
    }