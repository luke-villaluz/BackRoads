#!/usr/bin/env python3
"""
Produce Routes
This module handles finding and displaying ranked routes with street names.
"""

from backroads.core.data.graph import load_graph
from backroads.core.routing.candidates import k_shortest_routes, rank_routes
from backroads.core.routing.weighting import add_travel_time, add_scenic_weights, add_composite_cost
from backroads.core.utils.streets import print_route_street_names
from backroads.core.utils.visualize_route import visualize_route


def find_and_show_ranked_routes(origin, destination, k=5, time_budget_factor=1.5):
    """
    Use k_shortest_routes and rank_routes, then print street names for each.
    
    Args:
        origin: (lat, lon) tuple for starting point
        destination: (lat, lon) tuple for ending point
        k: Number of route alternatives to find
        time_budget_factor: Max time multiplier (1.5 = 50% longer than fastest)
    """
    # Load and prepare the graph with all weight types
    print("Loading road network...")
    graph = load_graph()
    add_travel_time(graph)
    add_scenic_weights(graph)
    add_composite_cost(graph)
    
    print(f"Finding routes from {origin} to {destination}...")
    
    # Step 1: k_shortest_routes
    routes = k_shortest_routes(graph, origin, destination, weight="scenic_cost", k=k)
    print(f"k_shortest_routes found: {len(routes)} routes")
 
    # Step 2: rank_routes  
    ranked_routes = rank_routes(graph, routes, time_budget_factor=time_budget_factor)
    print(f"rank_routes kept: {len(ranked_routes)} routes within time budget")
    
    # Step 3: Show summary for all candidates, then detailed streets for top route
    if ranked_routes:
        # Show summary for all candidates
        print("\nAll candidate routes:")
        for i, (path, scenic_avg, time_seconds) in enumerate(ranked_routes, 1):
            print(f"ROUTE {i} - Scenic: {scenic_avg:.3f} | Time: {time_seconds/60:.1f} min")
        
        # Show detailed street names for top route only
        top_path, scenic_avg, time_seconds = ranked_routes[0]
        print(f"\nTOP ROUTE - Scenic: {scenic_avg:.3f} | Time: {time_seconds/60:.1f} min")
        print_route_street_names(graph, top_path)

        visualize_route(
            graph, 
            top_path, 
            save_path="outputs/top_route.png",  
            show=True
        )
    else:
        print("No routes found within time budget!")
    
    return ranked_routes
