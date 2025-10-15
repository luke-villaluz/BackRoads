#!/usr/bin/env python3
"""
Graph Visualization Script for San Luis Obispo County Road Network

This script provides multiple ways to visualize the GraphML road network data,
including basic network plots, interactive maps, and statistical visualizations.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx
import osmnx as ox
from collections import Counter

# Add src to path so we can import backroads modules
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def setup_logging(level='INFO'):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def load_graph_from_file(filepath):
    """Load the GraphML file using OSMnx."""
    try:
        logging.info(f"Loading graph from {filepath}")
        graph = ox.load_graphml(filepath)
        logging.info(f"Successfully loaded graph with {graph.number_of_nodes():,} nodes and {graph.number_of_edges():,} edges")
        return graph
    except Exception as e:
        logging.error(f"Failed to load graph: {e}")
        return None

def basic_network_plot(graph, save_path=None, show=True, figsize=(15, 15)):
    """Create a basic network visualization using OSMnx."""
    logging.info("Creating basic network plot...")
    
    fig, ax = ox.plot_graph(
        graph, 
        node_size=0,  # Hide nodes for cleaner look
        edge_color='blue',
        edge_alpha=0.6,
        edge_linewidth=0.5,
        bgcolor='white',
        figsize=figsize,
        show=False,
        close=False
    )
    
    plt.title("San Luis Obispo County Road Network", fontsize=16, fontweight='bold')
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logging.info(f"Saved basic plot to {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()

def colored_highway_plot(graph, save_path=None, show=True, figsize=(15, 15)):
    """Create a visualization with different colors for different highway types."""
    logging.info("Creating colored highway plot...")
    
    # Define color mapping for different highway types
    highway_colors = {
        'motorway': '#e41a1c',      # Red
        'trunk': '#ff7f00',         # Orange  
        'primary': '#4daf4a',       # Green
        'secondary': '#377eb8',     # Blue
        'tertiary': '#984ea3',      # Purple
        'residential': '#999999',   # Gray
        'unclassified': '#ffff33',  # Yellow
        'service': '#a65628',       # Brown
        'footway': '#f781bf',       # Pink
        'path': '#999999'           # Light gray
    }
    
    # Get edge colors based on highway type
    edge_colors = []
    edge_widths = []
    
    for u, v, data in graph.edges(data=True):
        highway = data.get('highway', 'unclassified')
        if isinstance(highway, list):
            highway = highway[0]  # Take first highway type if multiple
        
        edge_colors.append(highway_colors.get(highway, '#cccccc'))
        
        # Set width based on highway importance
        if highway in ['motorway', 'trunk']:
            edge_widths.append(2.0)
        elif highway in ['primary', 'secondary']:
            edge_widths.append(1.5)
        elif highway == 'tertiary':
            edge_widths.append(1.0)
        else:
            edge_widths.append(0.5)
    
    fig, ax = ox.plot_graph(
        graph,
        node_size=0,
        edge_color=edge_colors,
        edge_linewidth=edge_widths,
        bgcolor='white',
        figsize=figsize,
        show=False,
        close=False
    )
    
    plt.title("San Luis Obispo County Road Network\n(Colored by Highway Type)", 
              fontsize=16, fontweight='bold')
    
    # Create legend
    legend_elements = []
    for highway_type, color in highway_colors.items():
        legend_elements.append(patches.Patch(color=color, label=highway_type.title()))
    
    plt.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logging.info(f"Saved colored highway plot to {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()

def network_statistics_plot(graph, save_path=None, show=True):
    """Create visualizations showing network statistics."""
    logging.info("Creating network statistics plots...")
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Degree distribution
    degrees = [graph.degree(n) for n in graph.nodes()]
    ax1.hist(degrees, bins=50, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Node Degree')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Node Degree Distribution')
    ax1.grid(True, alpha=0.3)
    
    # 2. Highway type distribution
    highway_types = []
    edge_lengths = []
    
    for u, v, data in graph.edges(data=True):
        highway = data.get('highway', 'unclassified')
        if isinstance(highway, list):
            highway = highway[0]
        highway_types.append(highway)
        
        length = data.get('length', 0)
        if isinstance(length, str):
            try:
                length = float(length)
            except:
                length = 0
        edge_lengths.append(length)
    
    highway_counts = Counter(highway_types)
    ax2.bar(range(len(highway_counts)), list(highway_counts.values()))
    ax2.set_xlabel('Highway Type')
    ax2.set_ylabel('Number of Edges')
    ax2.set_title('Highway Type Distribution')
    ax2.set_xticks(range(len(highway_counts)))
    ax2.set_xticklabels(list(highway_counts.keys()), rotation=45, ha='right')
    ax2.grid(True, alpha=0.3)
    
    # 3. Edge length distribution
    edge_lengths = [l for l in edge_lengths if l > 0 and l < 5000]  # Filter outliers
    ax3.hist(edge_lengths, bins=50, alpha=0.7, edgecolor='black')
    ax3.set_xlabel('Edge Length (meters)')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Edge Length Distribution')
    ax3.grid(True, alpha=0.3)
    
    # 4. Basic network stats
    stats_text = f"""
    Network Statistics:
    
    Nodes: {graph.number_of_nodes():,}
    Edges: {graph.number_of_edges():,}
    
    Average Degree: {sum(degrees)/len(degrees):.2f}
    Max Degree: {max(degrees)}
    
    Is Connected: {nx.is_connected(graph.to_undirected())}
    
    Most Common Highway Types:
    """
    
    for highway_type, count in highway_counts.most_common(5):
        stats_text += f"    {highway_type}: {count:,}\n"
    
    ax4.text(0.05, 0.95, stats_text, transform=ax4.transAxes, 
             fontsize=10, verticalalignment='top', fontfamily='monospace')
    ax4.set_xlim(0, 1)
    ax4.set_ylim(0, 1)
    ax4.axis('off')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logging.info(f"Saved statistics plot to {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()

def focused_area_plot(graph, center_point=None, radius=5000, save_path=None, show=True):
    """Create a focused plot of a specific area."""
    logging.info("Creating focused area plot...")
    
    if center_point is None:
        # Default to approximate center of San Luis Obispo city
        center_point = (35.2828, -120.6596)
    
    # Create a subgraph within the specified radius
    center_node = ox.distance.nearest_nodes(graph, center_point[1], center_point[0])
    subgraph = nx.ego_graph(graph, center_node, radius=10)  # Start with node-based radius
    
    # If subgraph is too small, try a larger radius
    if subgraph.number_of_nodes() < 50:
        subgraph = nx.ego_graph(graph, center_node, radius=20)
    
    logging.info(f"Focused area has {subgraph.number_of_nodes()} nodes and {subgraph.number_of_edges()} edges")
    
    fig, ax = ox.plot_graph(
        subgraph,
        node_size=20,
        node_color='red',
        edge_color='blue',
        edge_alpha=0.8,
        edge_linewidth=1,
        bgcolor='white',
        figsize=(12, 12),
        show=False,
        close=False
    )
    
    plt.title(f"Focused View Around ({center_point[0]:.3f}, {center_point[1]:.3f})", 
              fontsize=14, fontweight='bold')
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logging.info(f"Saved focused plot to {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()

def main():
    """Main function to run the visualization."""
    parser = argparse.ArgumentParser(description='Visualize San Luis Obispo County road network')
    parser.add_argument('--graphml', default='data_cache/slo_drive.graphml',
                       help='Path to GraphML file')
    parser.add_argument('--output-dir', default='outputs',
                       help='Directory to save visualization outputs')
    parser.add_argument('--plot-type', choices=['basic', 'colored', 'stats', 'focused', 'all'],
                       default='all', help='Type of plot to generate')
    parser.add_argument('--no-show', action='store_true',
                       help='Don\'t display plots, only save them')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Load the graph
    graph = load_graph_from_file(args.graphml)
    if graph is None:
        return 1
    
    show_plots = not args.no_show
    
    try:
        if args.plot_type in ['basic', 'all']:
            basic_network_plot(
                graph, 
                save_path=output_dir / 'basic_network.png',
                show=show_plots
            )
        
        if args.plot_type in ['colored', 'all']:
            colored_highway_plot(
                graph,
                save_path=output_dir / 'colored_highways.png', 
                show=show_plots
            )
        
        if args.plot_type in ['stats', 'all']:
            network_statistics_plot(
                graph,
                save_path=output_dir / 'network_statistics.png',
                show=show_plots
            )
        
        if args.plot_type in ['focused', 'all']:
            focused_area_plot(
                graph,
                save_path=output_dir / 'focused_area.png',
                show=show_plots
            )
        
        logging.info("Visualization complete!")
        
    except Exception as e:
        logging.error(f"Error during visualization: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())

"""
how to run:
# Generate all visualizations
python visualize_graph.py --plot-type all

# Generate specific visualization types
python visualize_graph.py --plot-type basic
python visualize_graph.py --plot-type colored
python visualize_graph.py --plot-type stats
python visualize_graph.py --plot-type focused

"""