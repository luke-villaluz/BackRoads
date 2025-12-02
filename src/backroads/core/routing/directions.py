from backroads.core.utils.streets import get_street_distances_from_path

DIRECTION_SYMBOLS = {
    'N': '↑', 'S': '↓',
    'E': '→', 'W': '←',
    'NE': '↗', 'NW': '↖',
    'SE': '↘', 'SW': '↙'
}
"""
Produces turn-by-turn street breakdown for a route.
Input:
    graph: networkx MultiDiGraph
    nodes: List[int] node ids for the chosen route
Output:
    List of segments with street names, directions, and distance
"""
def get_directions(graph, nodes):
    street_segments = get_street_distances_from_path(graph, nodes)
    directions = []

    for name, miles, direction in street_segments:
        symbol = DIRECTION_SYMBOLS.get(direction, '')
        directions.append({
            "direction": direction,
            "direction_symbol": symbol,
            "street": name,
            "miles": round(miles, 2)
        })

    return directions