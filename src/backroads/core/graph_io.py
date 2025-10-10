"""
Handles loading and caching of the San Luis Obispo County OpenStreetMap graph.

TODO:
- Implement download + caching
- Implement load from cache if file exists
"""

import logging
import osmnx as ox
from backroads.config import GRAPH_PATH, ensure_directories, LOG_LEVEL

_logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

def load_graph():
    """Load (and later, download) the SLO County graph."""
    ensure_directories()
    if GRAPH_PATH.exists():
        _logger.info("Loading cached graph from %s", GRAPH_PATH)
        return ox.load_graphml(GRAPH_PATH)
    _logger.info("Downloading graph for San Luis Obispo County")
    graph = ox.graph_from_place(
        "San Luis Obispo County, California, USA",
        network_type="drive",
    )
    ox.save_graphml(graph, GRAPH_PATH)
    _logger.info("Saved graph to %s", GRAPH_PATH)
    return graph
