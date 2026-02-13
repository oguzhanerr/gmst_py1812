#!/usr/bin/env python3
"""
Test script to visualize pipeline results with Plotly and deck.gl maps.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import geopandas as gpd

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from utils.visualization import (
    create_loss_distribution_chart,
    create_field_strength_chart,
    create_loss_vs_distance_scatter,
    create_azimuth_heatmap,
    create_receiver_map,
    create_statistics_summary,
    print_summary,
)

print("\n" + "="*70)
print("PIPELINE RESULTS VISUALIZATION")
print("="*70)

# Load results
output_dir = project_root / 'data' / 'output'
results_files = list(output_dir.glob('results_*.csv'))

if not results_files:
    print("\n⚠ No results found in data/output/")
    sys.exit(1)

latest_results = sorted(results_files, key=lambda p: p.stat().st_mtime)[-1]
print(f"\nLoading results from: {latest_results.name}")

results_df = pd.read_csv(latest_results)
print(f"✓ Loaded {len(results_df)} profile results")

# Generate statistics
summary = create_statistics_summary(results_df)
print_summary(summary)

# Create visualizations
print("\n" + "="*70)
print("GENERATING VISUALIZATIONS")
print("="*70)

# Chart 1: Lb distribution
print("\n1. Lb (Basic Transmission Loss) Distribution")
fig_lb = create_loss_distribution_chart(results_df)
if fig_lb:
    fig_lb.show()
    print("   ✓ Displayed histogram")

# Chart 2: Ep distribution
print("\n2. Ep (Electric Field Strength) Distribution")
fig_ep = create_field_strength_chart(results_df)
if fig_ep:
    fig_ep.show()
    print("   ✓ Displayed histogram")

# Chart 3: Lb vs Distance scatter
print("\n3. Lb vs Distance Scatter Plot")
fig_scatter = create_loss_vs_distance_scatter(results_df)
if fig_scatter:
    fig_scatter.show()
    print("   ✓ Displayed scatter plot")

# Chart 4: Azimuth heatmap
print("\n4. Azimuth-Distance Heatmap")
fig_heatmap = create_azimuth_heatmap(results_df)
if fig_heatmap:
    fig_heatmap.show()
    print("   ✓ Displayed heatmap")

# Load receiver points for map
print("\n5. Interactive Map (deck.gl)")
try:
    # Recreate receivers_gdf from config
    from pipeline.config import ConfigManager, get_transmitter_info, get_receiver_generation_params
    from pipeline.point_generation import Transmitter, generate_receiver_grid
    
    config_path = project_root / 'config_example.json'
    config_mgr = ConfigManager.from_file(config_path)
    CONFIG = config_mgr.config
    
    tx_info = get_transmitter_info(CONFIG)
    rx_gen_params = get_receiver_generation_params(CONFIG)
    
    tx = Transmitter(
        tx_id=tx_info['tx_id'],
        lon=tx_info['longitude'],
        lat=tx_info['latitude'],
        htg=tx_info['antenna_height_tx'],
        f=CONFIG['P1812']['frequency_ghz'],
        pol=CONFIG['P1812']['polarization'],
        p=CONFIG['P1812']['time_percentage'],
        hrg=tx_info['antenna_height_rx'],
    )
    
    receivers_gdf = generate_receiver_grid(
        tx=tx,
        max_distance_km=rx_gen_params['max_distance_km'],
        sampling_resolution_m=rx_gen_params['sampling_resolution'],
        num_azimuths=int(360 / rx_gen_params['azimuth_step']),
        include_tx_point=True,
    )
    
    print("   Generating deck.gl map...")
    output_map_path = project_root / 'data' / 'output' / 'receiver_map.html'
    deck_map, map_html_path = create_receiver_map(receivers_gdf, results_df, output_path=output_map_path)
    if deck_map:
        print(f"   ✓ Interactive map created")
        print(f"   Open in browser: {map_html_path}")
    
except Exception as e:
    print(f"   ⚠ Could not generate map: {str(e)[:100]}")

print("\n" + "="*70)
print("✓ VISUALIZATION COMPLETE")
print("="*70)
print("\nVisualization outputs:")
print("  • Lb histogram: Distribution of basic transmission loss")
print("  • Ep histogram: Distribution of field strength")
print("  • Scatter plot: Loss vs distance relationship by azimuth")
print("  • Heatmap: Azimuth and distance dependency patterns")
print("  • Interactive map: Receiver locations with loss color coding")
