#!/usr/bin/env python3
"""
Main script for showing scenic routes with street names.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.backroads.core.routing.produce_routes import find_and_show_ranked_routes

def main():    
    # Example route: SLODOCO to Target
    origin = (35.293683, -120.672025)      
    destination = (35.252955, -120.684900) 

    find_and_show_ranked_routes(origin, destination, k=5, time_budget_factor=100)

if __name__ == "__main__":
    main()
