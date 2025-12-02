import logging
from pathlib import Path
import json

import osmnx as ox
from backroads.config import GRAPH_PATH, ensure_directories
from backroads.core.utils.geo import set_graph_bounds


try:
    import geopandas as gpd
    from shapely.geometry import Point
except Exception:
    gpd = None

LOGGER = logging.getLogger(__name__)


"""
graph.py

Loads the graph of SLO county from OpenStreetMaps and annotates
each node with nearby 'natural' features using osmnx.features.features_from_place
when available. Node attributes added:
  - near_natural: bool
  - natural_types: comma-separated string of natural tag values (if any)

The annotated graph is saved next to the original as `<stem>_with_features.graphml`.
"""


def _fetch_natural_features(place_name: str):
    """Try to obtain 'natural' features for the place using osmnx.

    Tries several osmnx helper names for compatibility. Returns a GeoDataFrame
    or raises an exception if none are available.
    """
    tags = {"natural": True}

    # NOTE: retained for compatibility but not used below; prefer point-based fetch
    features_mod = getattr(ox, "features", None)
    if features_mod is None:
        raise AttributeError("osmnx.features module not available; required: osmnx.features.features_from_place")

    fetcher = getattr(features_mod, "features_from_place", None)
    if fetcher is None:
        raise AttributeError("osmnx.features.features_from_place is not available; please upgrade osmnx")

    # Call the modern fetcher with tags
    gdf = fetcher(place_name, tags=tags)
    return gdf


def _fetch_natural_features_from_point(center: tuple, dist_meters: float):
    """Fetch 'natural' features using osmnx.features.features_from_point.

    center: (lat, lon) tuple
    dist_meters: search radius in meters
    """
    features_mod = getattr(ox, "features", None)
    if features_mod is None:
        raise AttributeError("osmnx.features module not available; required: osmnx.features.features_from_point")

    fetcher = getattr(features_mod, "features_from_point", None)
    if fetcher is None:
        raise AttributeError("osmnx.features.features_from_point is not available; please upgrade osmnx")

    tags = {"natural": True}
    # features_from_point expects (lat, lon)
    lat, lon = center
    gdf = fetcher((lat, lon), dist=dist_meters, tags=tags)
    return gdf


def load_graph(annotate: bool = True, place_name: str = "San Luis Obispo County, California, USA", save_annotated: bool = True):
    """Load the SLO drive graph and optionally annotate nodes with nearby natural features.

    Args:
        annotate: whether to fetch features and annotate nodes
        place_name: place name passed to osmnx features fetcher
        save_annotated: if True, write an annotated GraphML next to the original

    Returns:
        networkx.MultiDiGraph with added node attributes when annotate=True
    """
    ensure_directories()
    if GRAPH_PATH.exists():
        LOGGER.info("loading cached graph from %s", GRAPH_PATH)
        graph = ox.load_graphml(GRAPH_PATH)
    else:
        LOGGER.info("downloading SLO county graph")
        graph = ox.graph_from_place(place_name, network_type="drive")
        try:
            ox.save_graphml(graph, GRAPH_PATH)
            LOGGER.info("saved graph to %s", GRAPH_PATH)
        except Exception:
            LOGGER.warning("Failed to save graph to %s", GRAPH_PATH)

    node_lats = [data["y"] for _, data in graph.nodes(data=True)]
    node_lons = [data["x"] for _, data in graph.nodes(data=True)]

    set_graph_bounds(
        min(node_lats),
        max(node_lats),
        min(node_lons),
        max(node_lons)
    )
    LOGGER.info(
        "Graph bounds initialized: lat[%f, %f], lon[%f, %f]",
        min(node_lats),
        max(node_lats),
        min(node_lons),
        max(node_lons),
    )

    if not annotate:
        return graph

    # If geopandas is not available, we cannot spatial-join; raise with guidance
    if gpd is None:
        LOGGER.warning("geopandas not installed; cannot annotate nodes with features. Install geopandas to enable annotation.")
        return graph

    # Annotate every node by fetching natural features within `dist_m` of that node.
    # To avoid duplicated Overpass queries, group nodes into a coarse grid of cells
    # sized by `cell_deg` so nearby nodes reuse the same fetched feature set.
    try:
        nodes = [(nid, data.get("x"), data.get("y")) for nid, data in graph.nodes(data=True) if data.get("x") is not None and data.get("y") is not None]
        if not nodes:
            LOGGER.warning("no node coordinates found in graph; cannot annotate")
            return graph

        # 2 miles in meters
        dist_m = 2.0 * 1609.344
        # convert meters to degrees (approx) for grid cell size (latitude-based)
        cell_deg = dist_m / 111320.0

        # map cell_key -> list of node ids in that cell
        cells = {}
        for nid, x, y in nodes:
            # x is longitude, y is latitude
            lon = x
            lat = y
            ix = int(round(lat / cell_deg))
            iy = int(round(lon / cell_deg))
            key = (ix, iy)
            cells.setdefault(key, []).append((nid, lat, lon))

        LOGGER.info("Will fetch features for %d cells (approx) to cover %d nodes", len(cells), len(nodes))

        cache = {}
        natural_by_node = {}
        cell_index = 0
        for key, node_list in cells.items():
            cell_index += 1
            ix, iy = key
            # compute center lat/lon of the cell
            center_lat = ix * cell_deg
            center_lon = iy * cell_deg
            # fetch once per cell
            #print(f"[cell {cell_index}/{len(cells)}] cell_key={key} nodes_in_cell={len(node_list)} center=({center_lat:.6f},{center_lon:.6f})")
            try:
                LOGGER.info("fetching features for cell %d/%d at center=(%f,%f)", cell_index, len(cells), center_lat, center_lon)
                gdf = _fetch_natural_features_from_point((center_lat, center_lon), dist_m)
                #print(f"[cell {cell_index}] fetched features: rows=" + str(len(gdf) if gdf is not None else 0))
            except Exception as exc:
                LOGGER.warning("cell fetch failed for key %s: %s", key, exc)
                #print(f"[cell {cell_index}] fetch failed: {exc}")
                gdf = None

            # extract natural type values from gdf
            types = []
            if gdf is not None and not gdf.empty:
                # prefer 'natural' column
                if "natural" in gdf.columns:
                    types = [str(v) for v in gdf["natural"].dropna().unique() if v != ""]
                else:
                    # try tags dict if present
                    vals = []
                    for _, r in gdf.iterrows():
                        tags = r.get("tags") if "tags" in r.index else None
                        if isinstance(tags, dict) and tags.get("natural"):
                            vals.append(str(tags.get("natural")))
                    types = list(sorted(set(vals)))

            for nid, lat, lon in node_list:
                natural_by_node[nid] = types.copy() if types else []
    
            #print(f"[cell {cell_index}] assigned types to {len(node_list)} nodes (types_count={len(types)})")

        # Write attributes back into graph nodes
        annotated_count = 0
        for nid, data in graph.nodes(data=True):
            vals = natural_by_node.get(nid, [])
            near = bool(vals)
            if near:
                annotated_count += 1
            data["near_natural"] = str(near)
            data["natural_types"] = ",".join(sorted(set(vals))) if vals else ""
        
        print("Finished Loading Graph....")
        LOGGER.info("Annotated %d nodes with nearby natural features", annotated_count)

    except Exception as exc:
        LOGGER.warning("Failed during per-node annotation: %s", exc)
        return graph

    LOGGER.info("Annotated %d nodes with nearby natural features", annotated_count)

    if save_annotated:
        orig = Path(GRAPH_PATH)
        target = orig.with_name(orig.stem + "_with_features.graphml")
        try:
            ox.save_graphml(graph, target)
            LOGGER.info("Saved annotated graph to %s", target)
        except Exception as exc:
            LOGGER.warning("Failed to save annotated graph: %s", exc)

    return graph