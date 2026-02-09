"""Batch processor for P1812 radio propagation calculations with smart output naming."""

import time
import hashlib
from pathlib import Path
from datetime import datetime

import pandas as pd

from .profile_parser import load_profiles, process_loss_parameters


def _generate_smart_filename(results, input_csv_path, output_format='xlsx'):
    """
    Generate smart output filename matching input CSV metadata.
    
    Format: results_{TX_ID}_{PROFILES}p_{AZIMUTHS}az_{DISTANCE}km_v{TIMESTAMP}_{HASH}.{ext}
    """
    if not results:
        return None
    
    # Extract metadata from input filename
    input_name = input_csv_path.stem  # Remove .csv
    
    # Parse input filename: profiles_TX_0001_432p_36az_11km_vYYYYMMDD_HHMMSS_HASH
    parts = input_name.split('_')
    
    # Reconstruct: results_{TX_ID}_{PROFILES}p_{AZIMUTHS}az_{DISTANCE}km_v{TIMESTAMP}_{HASH}
    try:
        # Skip 'profiles' prefix and get the rest
        tx_id = parts[1]  # TX_0001
        profiles_count = parts[2]  # 432p
        azimuths = parts[3]  # 36az
        distance = parts[4]  # 11km
        # Remaining: v{TIMESTAMP}_{HASH}
        version_hash = '_'.join(parts[5:])  # v20260209_094148_6e44e765
    except IndexError:
        # Fallback if parsing fails
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        content_hash = hashlib.md5(str(results).encode()).hexdigest()[:8]
        version_hash = f"v{timestamp}_{content_hash}"
        tx_id = results[0].get('tx_id', 'TX0')
        profiles_count = f"{len(results)}p"
        azimuths = "36az"
        distance = "11km"
    
    ext = 'xlsx' if output_format == 'xlsx' else 'csv'
    filename = f"results_{tx_id}_{profiles_count}_{azimuths}_{distance}_{version_hash}.{ext}"
    
    return filename


def _save_results(results, input_csv_path, output_dir):
    """
    Save P1812 results to both CSV and Excel formats with smart naming.
    
    Parameters:
    -----------
    results : list of dict
        P1812 calculation results
    input_csv_path : Path
        Path to input profiles CSV (for metadata extraction)
    output_dir : Path
        Output directory for results
    
    Returns:
    --------
    dict with 'csv_path' and 'xlsx_path' keys
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate smart filenames
    csv_filename = _generate_smart_filename(results, input_csv_path, 'csv')
    xlsx_filename = _generate_smart_filename(results, input_csv_path, 'xlsx')
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Reorder columns for better readability
    column_order = [
        'index', 'tx_id', 'azimuth', 'distance_ring', 'distance_km', 'num_distance_points',
        'frequency_ghz', 'time_percentage', 'polarization',
        'antenna_height_tx_m', 'antenna_height_rx_m',
        'tx_lat', 'tx_lon', 'rx_lat', 'rx_lon',
        'Lb', 'Ep', 'elapsed_s'
    ]
    # Only include columns that exist
    column_order = [col for col in column_order if col in df.columns]
    df = df[column_order]
    
    # Save CSV
    csv_path = output_dir / csv_filename
    df.to_csv(csv_path, index=False)
    
    # Save Excel with formatting
    xlsx_path = output_dir / xlsx_filename
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='P1812 Results', index=False)
        
        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['P1812 Results']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return {
        'csv_path': csv_path,
        'xlsx_path': xlsx_path,
        'filename_base': csv_filename.replace('.csv', ''),
    }


def main(profiles_dir=None, output_dir=None):
    """Main batch processor function with smart file naming and spreadsheet export.
    
    Loads profiles from CSV and calculates P1812 propagation loss/field strength.
    Results are saved to spreadsheets with smart naming matching input CSV.
    
    Parameters:
    -----------
    profiles_dir : Path or str, optional
        Directory containing profile CSV files. Defaults to data/input/profiles/
    output_dir : Path or str, optional
        Output directory for results. Defaults to data/output/spreadsheets/
    
    Returns:
    --------
    dict with results and file paths
    """
    # Import Py1812 at runtime (not available in all environments)
    try:
        import Py1812.P1812
    except ImportError:
        raise ImportError("Py1812 module not found. Install with: pip install -e ./github_Py1812/Py1812")
    
    # Default paths relative to project root
    project_root = Path(__file__).parent.parent.parent.parent
    
    if profiles_dir is None:
        profiles_dir = project_root / "data" / "input" / "profiles"
    else:
        profiles_dir = Path(profiles_dir)
    
    if output_dir is None:
        output_dir = project_root / "data" / "output" / "spreadsheets"
    else:
        output_dir = Path(output_dir)
    
    # Load profiles
    profiles, input_csv_path = load_profiles(profiles_dir, return_path=True)
    
    print(f"\n{'='*70}")
    print(f"P1812 BATCH PROCESSOR - Processing {len(profiles)} profiles")
    print(f"{'='*70}")
    print(f"Input:  {input_csv_path}")
    print(f"Output: {output_dir}")
    print(f"Note:   TX ID will be extracted from CSV column 17 for each profile")
    print(f"{'='*70}\n")
    
    results = []
    skipped_profiles = []
    total_time = 0.0
    first_tx_id = None  # Track first TX ID for logging
    
    for index, profile in enumerate(profiles):
        # TX ID is extracted from CSV column 17 (index 16)
        parameters, tx_id = process_loss_parameters(profile, tx_id_default='UNKNOWN_TX')
        
        # Log first TX ID found
        if first_tx_id is None and tx_id:
            first_tx_id = tx_id
            if first_tx_id != 'UNKNOWN_TX':
                print(f"Detected TX ID: {first_tx_id}\n")
        
        # Validate: P1812 requires > 4 points in profile
        num_points = len(parameters[2])  # distance array
        if num_points <= 4:
            skipped_profiles.append({
                'index': index + 1,
                'reason': f'Insufficient points: {num_points} (need > 4)',
            })
            continue
        
        # Calculate propagation loss
        start_time = time.perf_counter()
        Lb, Ep = Py1812.P1812.bt_loss(*parameters)
        elapsed = time.perf_counter() - start_time
        total_time += elapsed
        
        # Extract key info
        distance_km = float(parameters[2][-1])
        frequency_ghz = float(parameters[0])
        
        # Extract additional metadata from profile (CSV columns 15-16 if present)
        # Profile is a list: [f, p, d, h, R, Ct, zone, htg, hrg, pol, phi_t, phi_r, lam_t, lam_r, azimuth, distance_ring, tx_id]
        azimuth = None
        distance_ring = None
        try:
            if len(profile) > 14:
                azimuth = float(profile[14])  # azimuth column
            if len(profile) > 15:
                distance_ring = float(profile[15])  # distance_ring column
        except (IndexError, ValueError, TypeError):
            pass
        
        # Store result with all metadata
        result = {
            'index': index + 1,
            'tx_id': tx_id,
            'azimuth': azimuth,
            'distance_ring': distance_ring,
            'distance_km': distance_km,
            'num_distance_points': num_points,
            'frequency_ghz': frequency_ghz,
            'time_percentage': int(parameters[1]),
            'polarization': int(parameters[9]),
            'antenna_height_tx_m': float(parameters[7]),
            'antenna_height_rx_m': float(parameters[8]),
            'tx_lat': float(parameters[10]),
            'tx_lon': float(parameters[12]),
            'rx_lat': float(parameters[11]),
            'rx_lon': float(parameters[13]),
            'Lb': Lb,
            'Ep': Ep,
            'elapsed_s': elapsed,
        }
        results.append(result)
        
        # Print result
        az_str = f"{azimuth:5.1f}°" if azimuth is not None else "    --"
        ring_str = f"{distance_ring:4.0f}km" if distance_ring is not None else "   --"
        print(f"Profile {index+1:4d}: TX={tx_id:8} | Az={az_str} | Ring={ring_str} | D={distance_km:6.2f}km | F={frequency_ghz:.2f}GHz | Lb={Lb:7.2f}dB | Ep={Ep:7.2f}dBμV/m ({elapsed:.3f}s)")
    
    print(f"\n{'='*70}")
    print(f"✅ P1812 CALCULATIONS COMPLETE")
    print(f"{'='*70}")
    print(f"  Processed: {len(results)} profiles")
    print(f"  Skipped: {len(skipped_profiles)} profiles (insufficient points)")
    print(f"  Total time: {total_time:.2f}s")
    if results:
        print(f"  Average time per profile: {total_time/len(results):.3f}s")
    
    if skipped_profiles:
        print(f"\n⚠️ Skipped profiles (P1812 requires > 4 points):")
        for skipped in skipped_profiles[:10]:  # Show first 10
            print(f"  Profile {skipped['index']}: {skipped['reason']}")
        if len(skipped_profiles) > 10:
            print(f"  ... and {len(skipped_profiles)-10} more")
    
    # Save results
    print(f"\n{'='*70}")
    print(f"💾 SAVING RESULTS")
    print(f"{'='*70}")
    
    saved_files = _save_results(results, input_csv_path, output_dir)
    
    print(f"\n✓ Saved CSV:  {saved_files['csv_path'].name}")
    print(f"  Size: {saved_files['csv_path'].stat().st_size / 1024:.1f} KB")
    print(f"\n✓ Saved Excel: {saved_files['xlsx_path'].name}")
    print(f"  Size: {saved_files['xlsx_path'].stat().st_size / 1024:.1f} KB")
    
    print(f"\n📊 Filename format: results_{{TX_ID}}_{{PROFILES}}p_{{AZIMUTHS}}az_{{DISTANCE}}km_v{{TIMESTAMP}}_{{HASH}}.{{ext}}")
    
    print(f"\n{'='*70}")
    print(f"✅ BATCH PROCESSING COMPLETE")
    print(f"{'='*70}")
    
    return {
        'results': results,
        'csv_path': saved_files['csv_path'],
        'xlsx_path': saved_files['xlsx_path'],
        'input_csv': input_csv_path,
    }


# Alias for backward compatibility
batch_process = main


if __name__ == "__main__":
    main()
