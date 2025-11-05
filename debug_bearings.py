#!/usr/bin/env python3
"""
Debug version to check turn direction calculations
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from backroads.core.data.graph import load_graph
from backroads.core.routing.weighting import add_travel_time, add_scenic_weights, add_composite_cost
from backroads.core.routing.candidates import k_shortest_routes, rank_routes
from main import calculate_bearing, get_turn_direction

def debug_route_bearings(graph, path):
    """Debug function to show bearings and turn calculations."""
    print("\n🔍 DEBUG: Bearings and Turn Calculations")
    print("=" * 70)
    
    bearings = []
    street_names = []
    
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        
        # Get node coordinates
        u_data = graph.nodes[u]
        v_data = graph.nodes[v]
        u_lat, u_lon = u_data.get('y'), u_data.get('x')
        v_lat, v_lon = v_data.get('y'), v_data.get('x')
        
        # Get street name
        edge_data = graph.get_edge_data(u, v)
        if edge_data:
            if isinstance(edge_data, dict) and not any(key in edge_data for key in ["name", "highway"]):
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
        else:
            street_name = "Unknown"
        
        # Calculate bearing
        if u_lat and u_lon and v_lat and v_lon:
            bearing = calculate_bearing(u_lat, u_lon, v_lat, v_lon)
            bearings.append(bearing)
            street_names.append(street_name)
            
            print(f"Segment {i+1:2d}: {street_name}")
            print(f"    From: ({u_lat:.6f}, {u_lon:.6f}) to ({v_lat:.6f}, {v_lon:.6f})")
            print(f"    Bearing: {bearing:.1f}°")
            
            if i > 0:
                prev_bearing = bearings[i-1]
                turn = get_turn_direction(prev_bearing, bearing)
                diff = (bearing - prev_bearing + 360) % 360
                print(f"    Turn from previous: {turn} (diff: {diff:.1f}°)")
            print()

def main():
    # Load graph
    print("Loading road network...")
    graph = load_graph()
    add_travel_time(graph)
    add_scenic_weights(graph)
    add_composite_cost(graph)
    
    # Same coordinates as scenic_routes.py
    origin = (35.293683, -120.672025)      
    destination = (35.252955, -120.684900)
    
    # Get the top route
    routes = k_shortest_routes(graph, origin, destination, weight="scenic_cost", k=5)
    ranked_routes = rank_routes(graph, routes, time_budget_factor=1.5)
    
    if ranked_routes:
        top_path = ranked_routes[0][0]
        debug_route_bearings(graph, top_path)

if __name__ == "__main__":
    main()