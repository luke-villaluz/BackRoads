"""
Street Name Functions for BackRoads
This module provides functions to extract street names from routing paths.
"""
import networkx as nx
import math
from typing import List, Tuple, Optional, Union


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing between two GPS coordinates.
    
    Args:
        lat1, lon1: Starting point coordinates
        lat2, lon2: Ending point coordinates
        
    Returns:
        Bearing in degrees (0-360)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon_rad = math.radians(lon2 - lon1)
    
    y = math.sin(dlon_rad) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
    
    bearing_rad = math.atan2(y, x)
    bearing_deg = math.degrees(bearing_rad)
    
    # Normalize to 0-360 degrees
    return (bearing_deg + 360) % 360


def get_cardinal_direction(bearing: float) -> str:
    """
    Convert bearing to cardinal direction.
    
    Args:
        bearing: Bearing in degrees (0-360)
        
    Returns:
        Cardinal direction: 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'
    """
    # Normalize bearing to 0-360
    bearing = bearing % 360
    
    # Define cardinal directions with 45-degree segments
    if bearing < 22.5 or bearing >= 337.5:
        return 'N'
    elif bearing < 67.5:
        return 'NE'
    elif bearing < 112.5:
        return 'E'
    elif bearing < 157.5:
        return 'SE'
    elif bearing < 202.5:
        return 'S'
    elif bearing < 247.5:
        return 'SW'
    elif bearing < 292.5:
        return 'W'
    else:
        return 'NW'


def get_street_name_by_osmid(graph: nx.MultiDiGraph, osmid: Union[int, str]) -> Optional[str]:
    """
    Get street name by OSM ID from graph edges.
    
    Args:
        graph: NetworkX MultiDiGraph with OSM data
        osmid: OSM ID to search for (can be int or string)
        
    Returns:
        Street name if found, None otherwise
    """
    osmid_str = str(osmid)
    
    for u, v, key, data in graph.edges(keys=True, data=True):
        edge_osmid = data.get("osmid")
        
        # Handle different osmid formats (single ID, list of IDs)
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
    """
    Get street names for each segment in a path.
    
    Args:
        graph: NetworkX MultiDiGraph with OSM data
        path: List of node IDs representing the route
        
    Returns:
        List of tuples: (edge_description, street_name)
        edge_description format: "from_node -> to_node"
    """
    street_names = []
    
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        
        # Get edge data (handling MultiDiGraph)
        edge_data = graph.get_edge_data(u, v)
        if edge_data is None:
            street_names.append((f"{u} -> {v}", "Unknown"))
            continue
            
        # For MultiDiGraph, edge_data is a dict of {key: data}
        # Take the first edge's data
        if isinstance(edge_data, dict) and not any(key in edge_data for key in ["name", "highway", "length"]):
            # This is a MultiDiGraph format: {0: {data}, 1: {data}, ...}
            first_edge = next(iter(edge_data.values()))
            name = first_edge.get("name")
        else:
            # This is a DiGraph format: {data}
            name = edge_data.get("name")
            
        # Handle name format (can be string or list)
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
    """
    Get street names, distances, and cardinal directions for each continuous street section.
    
    Args:
        graph: NetworkX MultiDiGraph with OSM data
        path: List of node IDs representing the route
        
    Returns:
        List of tuples: (street_name, distance_miles, cardinal_direction)
    """
    if len(path) < 2:
        return []
    
    street_distances = []
    current_street = None
    current_distance_meters = 0.0
    street_bearings = []  # Store bearings for each street segment
    
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        
        # Get edge data (handling MultiDiGraph)
        edge_data = graph.get_edge_data(u, v)
        if edge_data is None:
            continue
            
        # For MultiDiGraph, edge_data is a dict of {key: data}
        # Take the first edge's data
        if isinstance(edge_data, dict) and not any(key in edge_data for key in ["name", "highway", "length"]):
            # This is a MultiDiGraph format: {0: {data}, 1: {data}, ...}
            first_edge = next(iter(edge_data.values()))
            name = first_edge.get("name")
            length = first_edge.get("length", 0)
        else:
            # This is a DiGraph format: {data}
            name = edge_data.get("name")
            length = edge_data.get("length", 0)
        
        # Handle name format (can be string or list)
        if isinstance(name, list):
            street_name = name[0] if name else "Unnamed"
        elif name:
            street_name = name
        else:
            street_name = "Unnamed"
        
        # Get length in meters
        try:
            length_meters = float(length) if length else 0.0
        except (ValueError, TypeError):
            length_meters = 0.0
        
        # Calculate bearing for this segment
        u_data = graph.nodes[u]
        v_data = graph.nodes[v]
        u_lat, u_lon = u_data.get('y'), u_data.get('x')
        v_lat, v_lon = v_data.get('y'), v_data.get('x')
        
        if u_lat and u_lon and v_lat and v_lon:
            current_bearing = calculate_bearing(u_lat, u_lon, v_lat, v_lon)
        else:
            current_bearing = None
        
        # If this is a new street, save the previous one and start new
        if street_name != current_street:
            if current_street is not None:
                # Convert meters to miles (1 meter = 0.000621371 miles)
                distance_miles = current_distance_meters * 0.000621371
                
                # Calculate average cardinal direction for the street
                cardinal_direction = ""
                if street_bearings:
                    # Use the average bearing for the street
                    avg_bearing = sum(street_bearings) / len(street_bearings)
                    cardinal_direction = get_cardinal_direction(avg_bearing)
                
                street_distances.append((current_street, distance_miles, cardinal_direction))
            
            current_street = street_name
            current_distance_meters = length_meters
            street_bearings = [current_bearing] if current_bearing is not None else []
        else:
            # Same street, add to distance and bearings
            current_distance_meters += length_meters
            if current_bearing is not None:
                street_bearings.append(current_bearing)
    
    # Don't forget the last street
    if current_street is not None:
        distance_miles = current_distance_meters * 0.000621371
        cardinal_direction = ""
        if street_bearings:
            avg_bearing = sum(street_bearings) / len(street_bearings)
            cardinal_direction = get_cardinal_direction(avg_bearing)
        street_distances.append((current_street, distance_miles, cardinal_direction))
    
    return street_distances


def print_route_street_names(graph: nx.MultiDiGraph, path: List[int]) -> None:
    """
    Print street names for a route with distances in miles and cardinal directions.
    
    Args:
        graph: NetworkX MultiDiGraph with OSM data
        path: List of node IDs representing the route
    """
    street_distances = get_street_distances_from_path(graph, path)
    
    print(f"\n🛣️  Route Street Names:")
    print("=" * 60)
    
    total_miles = 0.0
    for i, (street_name, distance_miles, cardinal_direction) in enumerate(street_distances, 1):
        total_miles += distance_miles
        
        # Show cardinal direction if available
        direction_symbol = ""
        if cardinal_direction == 'N':
            direction_symbol = "↑ "
        elif cardinal_direction == 'S':
            direction_symbol = "↓ "
        elif cardinal_direction == 'E':
            direction_symbol = "→ "
        elif cardinal_direction == 'W':
            direction_symbol = "← "
        elif cardinal_direction == 'NE':
            direction_symbol = "↗ "
        elif cardinal_direction == 'NW':
            direction_symbol = "↖ "
        elif cardinal_direction == 'SE':
            direction_symbol = "↘ "
        elif cardinal_direction == 'SW':
            direction_symbol = "↙ "
        
        if cardinal_direction:
            print(f"{i:2d}. {direction_symbol}{cardinal_direction} {street_name} - {distance_miles:.2f} miles")
        else:
            print(f"{i:2d}. {street_name} - {distance_miles:.2f} miles")
    
    print("=" * 60)
    print(f"Total distance: {total_miles:.2f} miles")


def get_osmids_from_path(graph: nx.MultiDiGraph, path: List[int]) -> List[Tuple[str, Union[int, str, List], Optional[str]]]:
    """
    Get OSM IDs and street names for each segment in a path.
    
    Args:
        graph: NetworkX MultiDiGraph with OSM data
        path: List of node IDs representing the route
        
    Returns:
        List of tuples: (edge_description, osmid, street_name)
    """
    osmid_info = []
    
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        
        # Get edge data (handling MultiDiGraph)
        edge_data = graph.get_edge_data(u, v)
        if edge_data is None:
            osmid_info.append((f"{u} -> {v}", None, "Unknown"))
            continue
            
        # For MultiDiGraph, edge_data is a dict of {key: data}
        # Take the first edge's data
        if isinstance(edge_data, dict) and not any(key in edge_data for key in ["name", "highway", "length"]):
            # This is a MultiDiGraph format: {0: {data}, 1: {data}, ...}
            first_edge = next(iter(edge_data.values()))
            osmid = first_edge.get("osmid")
            name = first_edge.get("name")
        else:
            # This is a DiGraph format: {data}
            osmid = edge_data.get("osmid")
            name = edge_data.get("name")
            
        # Handle name format (can be string or list)
        if isinstance(name, list):
            street_name = name[0] if name else "Unnamed"
        elif name:
            street_name = name
        else:
            street_name = "Unnamed"
            
        edge_desc = f"{u} -> {v}"
        osmid_info.append((edge_desc, osmid, street_name))
    
    return osmid_info
