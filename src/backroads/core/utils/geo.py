"""
Geographic Utility Functions for BackRoads
This module provides geographic helpers like bearing and direction calculation.
"""

import math

GRAPH_BOUNDS = {
    "min_lat": None,
    "max_lat": None,
    "min_lon": None,
    "max_lon": None,
}

def set_graph_bounds(min_lat: float, max_lat: float, min_lon: float, max_lon: float):
    GRAPH_BOUNDS["min_lat"] = min_lat
    GRAPH_BOUNDS["max_lat"] = max_lat
    GRAPH_BOUNDS["min_lon"] = min_lon
    GRAPH_BOUNDS["max_lon"] = max_lon

def validate_coord_in_bounds(lat: float, lon: float, label: str = "coordinate") -> None:
    """
    Validate that (lat, lon) lies inside the graph's bounding box.
    Raises ValueError if out of bounds.
    """
    if GRAPH_BOUNDS["min_lat"] is None:
        raise RuntimeError("GRAPH_BOUNDS not initialized. Call set_graph_bounds().")

    if not (
        GRAPH_BOUNDS["min_lat"] <= lat <= GRAPH_BOUNDS["max_lat"]
        and GRAPH_BOUNDS["min_lon"] <= lon <= GRAPH_BOUNDS["max_lon"]
    ):
        raise ValueError(
            f"{label} ({lat:.6f}, {lon:.6f}) is outside the supported routing area. "
            f"Bounds: lat[{GRAPH_BOUNDS['min_lat']}, {GRAPH_BOUNDS['max_lat']}], "
            f"lon[{GRAPH_BOUNDS['min_lon']}, {GRAPH_BOUNDS['max_lon']}]"
        )

def parse_coord(coord):
    if hasattr(coord, "lat") and hasattr(coord, "lon"):
        return coord.lat, coord.lon

    if isinstance(coord, dict) and "lat" in coord and "lon" in coord:
        return coord["lat"], coord["lon"]

    # Fallback to the old list behavior
    if isinstance(coord, (list, tuple)) and len(coord) == 2:
        return coord[0], coord[1]

    raise ValueError("Coordinate must be a list [lat, lon] or an object with lat/lon")



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
    bearing = bearing % 360

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