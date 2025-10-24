# --- Visualization (replace your current try/except block) ---
import os
import math
import matplotlib.pyplot as plt

def _midpoint_of_linestring(geom):
    try:
        # geom is usually a shapely LineString
        # interpolate(0.5, normalized=True) -> midpoint
        return geom.interpolate(0.5, normalized=True).coords[0]
    except Exception:
        return None

def _label_route_streets(ax, G, path, fontsize=8):
    """
    Annotate the plot with street names roughly at segment midpoints.
    Keeps labels sparse by skipping repeats.
    """
    seen = set()
    for u, v in zip(path[:-1], path[1:]):
        ed = G.get_edge_data(u, v)
        data = ed if ("length" in ed) else next(iter(ed.values()))  # DiGraph or MultiDiGraph
        name = data.get("name")
        if isinstance(name, list):
            name = name[0] if name else None
        if not name or name in seen:
            continue
        seen.add(name)

        geom = data.get("geometry")
        pt = _midpoint_of_linestring(geom) if geom is not None else None
        if pt is None:
            # fallback: average the node xy
            x1, y1 = G.nodes[u]["x"], G.nodes[u]["y"]
            x2, y2 = G.nodes[v]["x"], G.nodes[v]["y"]
            pt = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

        ax.text(
            pt[0], pt[1], name,
            fontsize=fontsize,
            ha="center", va="center",
            alpha=0.7, rotation=0,
            bbox=dict(facecolor="white", alpha=0.5, linewidth=0)
        )

try:
    os.makedirs("outputs", exist_ok=True)

    # Plot up to top 3 routes; get fig/ax and save explicitly
    top_n = min(3, len(ranked))
    fig, ax = ox.plot_graph_routes(
        G,
        [p for p, _, _ in ranked[:top_n]],
        route_linewidth=3,
        node_size=0,
        bgcolor="white",
        show=False,
        close=False,
    )

    # Optional: label street names for the top route only (keeps clutter down)
    label_names = True  # set to False if you don't want labels
    if label_names and top_n >= 1:
        top_path = ranked[0][0]
        _label_route_streets(ax, G, top_path, fontsize=8)

    out_path = "outputs/routes.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"\n🗺  Saved route visualization: {out_path}")

except Exception as e:
    print(f"\n(Visualization skipped: {e})")
