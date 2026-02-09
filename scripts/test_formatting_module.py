#!/usr/bin/env python3
"""
Quick test of formatting.py module to verify smart filename generation.

Creates sample Phase 3 GeoDataFrame and tests:
1. Profile formatting logic
2. Smart filename generation with metadata
3. CSV export and structure validation
"""

import sys
import hashlib
import math
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mst_gis.pipeline.formatting import format_and_export_profiles


def create_sample_gdf():
    """Create a sample Phase 3 GeoDataFrame with elevation/landcover/zone data.
    
    Uses production-realistic parameters:
    - 36 azimuths (10° spacing)
    - 0.03 km (30m) distance steps from 0-11 km
    """
    
    print("\n" + "="*70)
    print("CREATING SAMPLE GEODATAFRAME (PRODUCTION REALISTIC)")
    print("="*70)
    
    # Load all parameters from config
    import json
    config_path = Path(__file__).parent.parent / 'config_example.json'
    with open(config_path) as f:
        config = json.load(f)
    
    # Transmitter config
    tx_config = config['TRANSMITTER']
    tx_lat = tx_config['latitude']
    tx_lon = tx_config['longitude']
    tx_id = tx_config['tx_id']
    tx_antenna_height = tx_config['antenna_height_tx']
    rx_antenna_height = tx_config['antenna_height_rx']
    
    # P1812 config
    p1812_config = config['P1812']
    frequency_ghz = p1812_config['frequency_ghz']
    time_percentage = p1812_config['time_percentage']
    polarization = p1812_config['polarization']
    
    # Receiver generation config
    rx_config = config['RECEIVER_GENERATION']
    num_azimuths = int(360 / rx_config['azimuth_step'])  # e.g., 360/10 = 36
    distance_step_km = rx_config['distance_step']
    max_distance_km = rx_config['max_distance_km']
    
    print(f"  Loading config from: {config_path.name}")
    print(f"  TX ID: {tx_id}")
    print(f"  TX Location: ({tx_lat}, {tx_lon})")
    print(f"  TX Antenna Height: {tx_antenna_height}m, RX: {rx_antenna_height}m")
    print(f"  Frequency: {frequency_ghz} GHz, Time%: {time_percentage}%, Polarization: {polarization}")
    
    # Generate azimuths
    azimuths = np.linspace(0, 360 - (360/num_azimuths), num_azimuths).tolist()
    
    # Generate distances
    distances = np.arange(0, max_distance_km + distance_step_km/2, distance_step_km).tolist()
    distances = [d for d in distances if d <= max_distance_km + 1e-6]  # Exclude TX point (0 is added later)
    
    print(f"  Parameters:")
    print(f"    Azimuths: {num_azimuths} (0-360°)")
    print(f"    Distance step: {distance_step_km} km (30m)")
    print(f"    Max distance: {max_distance_km} km")
    print(f"    Distance points: {len(distances)}")
    print(f"    Expected profiles: {num_azimuths} × 12 distance rings = 432 profiles")
    
    data = []
    rx_id = 0
    
    for az in azimuths:
        for dist in distances:
            if dist == 0:  # Skip TX point, added in formatting
                continue
                
            # Convert to radians for proper offset calculation
            az_rad = math.radians(az)
            
            # Calculate lat/lon offset (1° ≈ 111 km)
            lat_offset = (dist / 111.0) * math.cos(az_rad)
            lon_offset = (dist / 111.0 / math.cos(math.radians(tx_lat))) * math.sin(az_rad)
            
            rx_lat = tx_lat + lat_offset
            rx_lon = tx_lon + lon_offset
            
            # Elevation: starts at 16m, increases gradually
            h = 16 + dist * 10
            
            # Landcover (Ct): simplified - mostly class 4
            ct = 4
            r = 15  # Resistance (ohms)
            
            # Zone: simplified - zone 3 (coastal)
            zone = 3
            
            data.append({
                'geometry': Point(rx_lon, rx_lat),
                'azimuth_deg': float(az),
                'distance_km': float(dist),
                'h': float(h),
                'Ct': int(ct),
                'R': float(r),
                'zone': int(zone),
                'tx_id': tx_id,  # From config
            })
            rx_id += 1
    
    gdf = gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    print(f"\n✓ Created GeoDataFrame with {len(gdf)} points")
    print(f"  Azimuths: {len(gdf['azimuth_deg'].unique())}")
    print(f"  Distance values: {len(gdf['distance_km'].unique())}")
    print(f"  Bounds: {gdf.total_bounds}")
    
    return gdf


def test_formatting(gdf):
    """Test format_and_export_profiles function."""
    
    print("\n" + "="*70)
    print("TESTING FORMATTING MODULE")
    print("="*70)
    
    profiles_dir = project_root / 'data/input/profiles'
    profiles_dir.mkdir(parents=True, exist_ok=True)
    
    # Use a placeholder output path - the function will generate the actual filename
    output_path = profiles_dir / "profiles_TX0_placeholder.csv"
    
    print(f"\nExporting profiles to: {profiles_dir}")
    
    try:
        df_profiles, csv_path = format_and_export_profiles(
            receivers_gdf=gdf,
            output_path=output_path,
            frequency_ghz=0.9,
            time_percentage=50,
            polarization=1,  # Horizontal
            htg=57,  # TX antenna height
            hrg=10,  # RX antenna height
            verbose=True,
        )
        
        return csv_path, df_profiles
    
    except Exception as e:
        print(f"✗ Formatting failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def validate_csv(csv_path, df_profiles):
    """Validate the generated CSV."""
    
    print("\n" + "="*70)
    print("VALIDATING CSV OUTPUT")
    print("="*70)
    
    # Check file exists
    if not csv_path.exists():
        print(f"✗ CSV file not found: {csv_path}")
        return False
    
    print(f"\n✓ File exists: {csv_path.name}")
    file_size = csv_path.stat().st_size / 1024
    print(f"  Size: {file_size:.1f} KB")
    
    # Validate filename format
    import re
    pattern = r'profiles_\w+_\d+p_\d+az_\d+km_v\d{8}_\d{6}_\w{8}\.csv'
    if re.match(pattern, csv_path.name):
        print(f"  ✓ Filename matches smart format")
        
        # Parse filename components
        parts = csv_path.stem.split('_')
        print(f"\n  Filename components:")
        print(f"    TX_ID: {parts[0]}")
        print(f"    Profiles: {parts[1]}")
        print(f"    Azimuths: {parts[2]}")
        print(f"    Distance: {parts[3]}")
        print(f"    Version: v{parts[4]}_{parts[5]}")
        print(f"    Hash: {parts[6]}")
    else:
        print(f"  ✗ Filename does not match expected format")
        print(f"    Got: {csv_path.name}")
        print(f"    Expected: profiles_{{TX_ID}}_{{PROFILES}}p_{{AZIMUTHS}}az_{{DISTANCE}}km_v{{TIMESTAMP}}_{{HASH}}.csv")
        return False
    
    # Validate CSV structure
    print(f"\n✓ CSV Structure:")
    print(f"  Rows: {len(df_profiles)}")
    print(f"  Columns: {len(df_profiles.columns)}")
    print(f"  Column names: {list(df_profiles.columns)}")
    
    # Check required columns
    required_cols = ['f', 'p', 'd', 'h', 'R', 'Ct', 'zone', 'htg', 'hrg', 'pol', 'phi_t', 'phi_r', 'lam_t', 'lam_r', 'azimuth']
    missing = [col for col in required_cols if col not in df_profiles.columns]
    
    if missing:
        print(f"  ✗ Missing columns: {missing}")
        return False
    else:
        print(f"  ✓ All required columns present")
    
    # Validate sample row
    print(f"\n✓ Sample Profile (row 0):")
    sample = df_profiles.iloc[0]
    print(f"  Frequency: {sample['f']} GHz")
    print(f"  Time %: {sample['p']}%")
    print(f"  Polarization: {sample['pol']}")
    print(f"  Antenna heights: TX={sample['htg']}m, RX={sample['hrg']}m")
    print(f"  TX: ({sample['phi_t']:.4f}, {sample['lam_t']:.4f})")
    print(f"  RX: ({sample['phi_r']:.4f}, {sample['lam_r']:.4f})")
    print(f"  Distance array length: {len(sample['d'])}")
    print(f"  Azimuth: {sample['azimuth']:.1f}°")
    
    # Verify by re-reading the CSV
    print(f"\n✓ Re-reading CSV to verify integrity...")
    df_check = pd.read_csv(csv_path, sep=';')
    print(f"  Re-read {len(df_check)} rows, {len(df_check.columns)} columns")
    
    if len(df_check) == len(df_profiles):
        print(f"  ✓ Row count matches")
    else:
        print(f"  ✗ Row count mismatch: {len(df_check)} vs {len(df_profiles)}")
        return False
    
    return True


def compare_with_notebook_structure():
    """Show what the notebook would generate for comparison."""
    
    print("\n" + "="*70)
    print("NOTEBOOK vs PYTHON COMPARISON")
    print("="*70)
    
    print("\nBoth notebook and Python module should generate:")
    print("  • Same profile count (azimuths × distance rings)")
    print("  • Same distance array structure (0 to endpoint)")
    print("  • Same columns in same order")
    print("  • Same parameter values (f, p, htg, hrg, pol)")
    print("  • Same smart filename format with metadata")
    print("\nOnly difference expected:")
    print("  • Timestamp (execution time)")
    print("  • Content hash (may differ if timestamp differs)")


def main():
    print("\n" + "="*70)
    print("FORMATTING MODULE TEST")
    print("="*70)
    
    # Create sample data
    gdf = create_sample_gdf()
    
    # Test formatting
    csv_path, df_profiles = test_formatting(gdf)
    
    if csv_path and df_profiles is not None:
        # Validate
        if validate_csv(csv_path, df_profiles):
            print("\n✅ CSV validation PASSED")
        else:
            print("\n⚠️ CSV validation FAILED")
        
        # Show comparison info
        compare_with_notebook_structure()
        
        print("\n" + "="*70)
        print("TEST COMPLETE")
        print("="*70)
        print(f"\nGenerated CSV: {csv_path}")
        print(f"Ready for Phase 5 P1812 batch processing")
    else:
        print("\n✗ Test FAILED")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
