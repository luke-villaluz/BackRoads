#!/usr/bin/env python3
"""
Main script for showing scenic routes with street names.

TO RUN: 
    cd src 
    python3 -m backroads.core.main

TO KILL:
    ctrl + c 
"""

from backroads.core.routing.produce_routes import find_and_show_ranked_routes

def main():    
    # Example route: SLODOCO to Target
    origin = (35.293683, -120.672025)      
    destination = (35.252955, -120.684900) 

    find_and_show_ranked_routes(origin, destination, k=5, time_budget_factor=100)

if __name__ == "__main__":
    main()
