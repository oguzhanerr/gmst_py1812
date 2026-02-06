"""Batch processor for P1812 radio propagation calculations."""

import time
from pathlib import Path

from .profile_parser import load_profiles, process_loss_parameters


def main(profiles_dir=None):
    """Main batch processor function.
    
    Loads profiles from CSV and calculates P1812 propagation loss/field strength.
    Results are printed to console with tx_id tracking.
    
    Parameters:
    -----------
    profiles_dir : Path or str, optional
        Directory containing profile CSV files. Defaults to data/input/profiles/
    """
    # Import Py1812 at runtime (not available in all environments)
    try:
        import Py1812.P1812
    except ImportError:
        raise ImportError("Py1812 module not found. Install with: pip install -e ./github_Py1812/Py1812")
    
    # Default path relative to project root
    if profiles_dir is None:
        profiles_dir = Path(__file__).parent.parent.parent.parent / "data" / "input" / "profiles"
    else:
        profiles_dir = Path(profiles_dir)
    
    profiles = load_profiles(profiles_dir)
    
    print(f"\n{'='*70}")
    print(f"P1812 BATCH PROCESSOR - Processing {len(profiles)} profiles")
    print(f"{'='*70}\n")
    
    results = []
    total_time = 0.0
    
    for index, profile in enumerate(profiles):
        parameters, tx_id = process_loss_parameters(profile)
        
        # Calculate propagation loss
        start_time = time.perf_counter()
        Lb, Ep = Py1812.P1812.bt_loss(*parameters)
        elapsed = time.perf_counter() - start_time
        total_time += elapsed
        
        # Extract key info
        distance_km = float(parameters[2][-1])
        frequency_ghz = float(parameters[0])
        
        # Store result
        result = {
            'index': index + 1,
            'tx_id': tx_id,
            'distance_km': distance_km,
            'frequency_ghz': frequency_ghz,
            'Lb': Lb,
            'Ep': Ep,
            'elapsed_s': elapsed,
        }
        results.append(result)
        
        # Print result
        print(f"Profile {index+1:4d}: TX={tx_id:8} | D={distance_km:6.2f}km | F={frequency_ghz:.2f}GHz | Lb={Lb:7.2f}dB | Ep={Ep:7.2f}dBμV/m ({elapsed:.3f}s)")
    
    print(f"\n{'='*70}")
    print(f"✅ PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"  Total profiles: {len(results)}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Average time per profile: {total_time/len(results):.3f}s")
    print(f"\nResults available in console output above.")
    
    return results


if __name__ == "__main__":
    main()
