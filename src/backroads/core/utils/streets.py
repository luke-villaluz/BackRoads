"""
Street and Path Utilities for BackRoads
This module provides functions to extract street names, distances, and directions
from routing paths using a NetworkX graph.
"""

import networkx as nx
from typing import List, Tuple, Optional, Union
from .geo import calculate_bearing, get_cardinal_direction


def get_street_name_by_osmid(graph: nx.MultiDiGraph, osmid: Union[int, str]) -> Optional[str]:
    osmid_str = str(osmid)
    for u, v, key, data in graph.edges(keys=True, data=True):
        edge_osmid = data.get("osmid")

        if edge_osmid is not None:
            if isinstance(edge_osmid, list):
                if osmid_str in [str(oid) for oid in edge_osmid]:
                    name = data.get("name")
                    if isinstance(name, list):
                        return name[0] if name else None
                    return name
            else:
                if str(edge_osmid) == osmid_str:
                    name = data.get("name")
                    if isinstance(name, list):
                        return name[0] if name else None
                    return name
    return None


def get_street_names_from_path(graph: nx.MultiDiGraph, path: List[int]) -> List[Tuple[str, Optional[str]]]:
    street_names = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = graph.get_edge_data(u, v)
        if edge_data is None:
            street_names.append((f"{u} -> {v}", "Unknown"))
            continue

        if isinstance(edge_data, dict) and not any(k in edge_data for k in ["name", "highway", "length"]):
            first_edge = next(iter(edge_data.values()))
            name = first_edge.get("name")
        else:
            name = edge_data.get("name")

        if isinstance(name, list):
            street_name = name[0] if name else "Unnamed"
        elif name:
            street_name = name
        else:
            street_name = "Unnamed"

        edge_desc = f"{u} -> {v}"
        street_names.append((edge_desc, street_name))
    return street_names


def get_street_distances_from_path(graph: nx.MultiDiGraph, path: List[int]) -> List[Tuple[str, float, str]]:
    if len(path) < 2:
        return []

    street_distances = []
    current_street = None
    current_distance_meters = 0.0
    street_bearings = []

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = graph.get_edge_data(u, v)
        if edge_data is None:
            continue

        if isinstance(edge_data, dict) and not any(k in edge_data for k in ["name", "highway", "length"]):
            first_edge = next(iter(edge_data.values()))
            name = first_edge.get("name")
            length = first_edge.get("length", 0)
        else:
            name = edge_data.get("name")
            length = edge_data.get("length", 0)

        if isinstance(name, list):
            street_name = name[0] if name else "Unnamed"
        elif name:
            street_name = name
        else:
            street_name = "Unnamed"

        try:
            length_meters = float(length) if length else 0.0
        except (ValueError, TypeError):
            length_meters = 0.0

        u_lat, u_lon = graph.nodes[u].get('y'), graph.nodes[u].get('x')
        v_lat, v_lon = graph.nodes[v].get('y'), graph.nodes[v].get('x')
        current_bearing = calculate_bearing(u_lat, u_lon, v_lat, v_lon) if all([u_lat, u_lon, v_lat, v_lon]) else None

        if street_name != current_street:
            if current_street is not None:
                distance_miles = current_distance_meters * 0.000621371
                cardinal_direction = ""
                if street_bearings:
                    avg_bearing = sum(street_bearings) / len(street_bearings)
                    cardinal_direction = get_cardinal_direction(avg_bearing)
                street_distances.append((current_street, distance_miles, cardinal_direction))

            current_street = street_name
            current_distance_meters = length_meters
            street_bearings = [current_bearing] if current_bearing else []
        else:
            current_distance_meters += length_meters
            if current_bearing:
                street_bearings.append(current_bearing)

    if current_street is not None:
        distance_miles = current_distance_meters * 0.000621371
        cardinal_direction = ""
        if street_bearings:
            avg_bearing = sum(street_bearings) / len(street_bearings)
            cardinal_direction = get_cardinal_direction(avg_bearing)
        street_distances.append((current_street, distance_miles, cardinal_direction))

    return street_distances


def print_route_street_names(graph: nx.MultiDiGraph, path: List[int]) -> None:
    street_distances = get_street_distances_from_path(graph, path)

    print(f"\n🛣️  Route Street Names:")
    print("=" * 60)

    total_miles = 0.0
    for i, (street_name, distance_miles, cardinal_direction) in enumerate(street_distances, 1):
        total_miles += distance_miles

        direction_symbols = {
            'N': "↑ ", 'S': "↓ ", 'E': "→ ", 'W': "← ",
            'NE': "↗ ", 'NW': "↖ ", 'SE': "↘ ", 'SW': "↙ "
        }
        direction_symbol = direction_symbols.get(cardinal_direction, "")

        if cardinal_direction:
            print(f"{i:2d}. {direction_symbol}{cardinal_direction} {street_name} - {distance_miles:.2f} miles")
        else:
            print(f"{i:2d}. {street_name} - {distance_miles:.2f} miles")

    print("=" * 60)
    print(f"Total distance: {total_miles:.2f} miles")


def get_osmids_from_path(graph: nx.MultiDiGraph, path: List[int]) -> List[Tuple[str, Union[int, str, List], Optional[str]]]:
    osmid_info = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = graph.get_edge_data(u, v)
        if edge_data is None:
            osmid_info.append((f"{u} -> {v}", None, "Unknown"))
            continue

        if isinstance(edge_data, dict) and not any(k in edge_data for k in ["name", "highway", "length"]):
            first_edge = next(iter(edge_data.values()))
            osmid = first_edge.get("osmid")
            name = first_edge.get("name")
        else:
            osmid = edge_data.get("osmid")
            name = edge_data.get("name")

        if isinstance(name, list):
            street_name = name[0] if name else "Unnamed"
        elif name:
            street_name = name
        else:
            street_name = "Unnamed"

        edge_desc = f"{u} -> {v}"
        osmid_info.append((edge_desc, osmid, street_name))
    return osmid_info
