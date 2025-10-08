"""
Handles loading and caching of the San Luis Obispo County OpenStreetMap graph.

TODO:
- Implement download + caching
- Implement load from cache if file exists
"""

from pathlib import Path
import osmnx as ox  # already installed

GRAPH_PATH = Path("data_cache/slo_drive.graphml")

def load_graph():
    """Load (and later, download) the SLO County graph."""
    pass
