"""
Geographic Utility Functions for BackRoads
This module provides geographic helpers like bearing and direction calculation.
"""

import math


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
