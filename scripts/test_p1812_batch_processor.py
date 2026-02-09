#!/usr/bin/env python3
"""
Test the P1812 batch processor with smart naming and spreadsheet export.

This script tests the updated batch processor that:
1. Reads 432 profiles from the generated CSV
2. Runs P1812 calculations
3. Saves results with smart naming matching input CSV metadata
4. Exports to both CSV and Excel formats
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from mst_gis.propagation import batch_processor_v2


def main():
    print("\n" + "="*70)
    print("P1812 BATCH PROCESSOR TEST")
    print("="*70)
    
    # Paths
    profiles_dir = project_root / "data/input/profiles"
    output_dir = project_root / "data/output/spreadsheets"
    
    # Check if profiles exist
    csv_files = list(profiles_dir.glob("profiles_*.csv"))
    if not csv_files:
        print("\n✗ No profile CSV files found!")
        print(f"  Expected: {profiles_dir}/*.csv")
        return 1
    
    latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
    print(f"\n✓ Found profile CSV: {latest_csv.name}")
    print(f"  Size: {latest_csv.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Run batch processor
    print("\n" + "="*70)
    print("Running P1812 calculations...")
    print("="*70)
    
    try:
        result = batch_processor_v2.main(
            profiles_dir=profiles_dir,
            output_dir=output_dir
        )
        
        print("\n" + "="*70)
        print("✅ BATCH PROCESSOR TEST PASSED")
        print("="*70)
        
        # Show output files
        print(f"\n📁 Output files:")
        print(f"  CSV:   {result['csv_path']}")
        print(f"  Excel: {result['xlsx_path']}")
        
        # Show sample results
        if result['results']:
            print(f"\n📊 Sample results (first 3):")
            for res in result['results'][:3]:
                print(f"  {res['index']:3d}: TX={res['tx_id']:8} | Az={res['azimuth']:5.1f}° | Ring={res['distance_ring']:4.0f}km | "
                      f"D={res['distance_km']:6.2f}km | Lb={res['Lb']:7.2f}dB | Ep={res['Ep']:7.2f}dBμV/m")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Batch processor failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
