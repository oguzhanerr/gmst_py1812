# P1812 Output Implementation - Smart Naming with Version Tracking

## Summary

Successfully implemented smart filename generation for P1812 batch processor outputs, matching the input profile CSV metadata structure.

## Implementation

### Smart Filename Format

Both input and output files follow the same naming convention:

```
[type]_TX_ID_PROFILESp_AZIMUTHSaz_DISTANCEkm_vTIMESTAMP_HASH.ext
```

**Components:**
- `type`: `profiles` (input) or `results` (output)
- `TX_ID`: Transmitter identifier (e.g., TX_0001)
- `PROFILES`: Total profile count with 'p' suffix (e.g., 432p)
- `AZIMUTHS`: Number of azimuths with 'az' suffix (e.g., 36az)
- `DISTANCE`: Maximum distance with 'km' suffix (e.g., 11km)
- `TIMESTAMP`: Generation timestamp YYYYMMDD_HHMMSS (e.g., 20260209_094148)
- `HASH`: 8-character MD5 hash for version control (e.g., 6e44e765)
- `ext`: File extension (csv, xlsx)

### Example

**Input CSV:**
```
profiles_TX_0001_432p_36az_11km_v20260209_094148_6e44e765.csv
```

**Output Files:**
```
results_TX_0001_432p_36az_11km_v20260209_094148_6e44e765.csv    (CSV)
results_TX_0001_432p_36az_11km_v20260209_094148_6e44e765.xlsx   (Excel)
```

## Files Modified

### New Files
- `src/mst_gis/propagation/batch_processor_v2.py` - Enhanced batch processor with:
  - Smart output filename generation
  - CSV and Excel export
  - Profile filtering and validation
  - Results tracking with azimuth and distance_ring

### Updated Files
- `src/mst_gis/propagation/batch_processor.py` - Now imports from v2
- `src/mst_gis/propagation/profile_parser.py` - Added `return_path` parameter
- `scripts/test_p1812_batch_processor.py` - Test script for new functionality

## Output Formats

### CSV Output
Columns (in order):
- `index`: Profile sequence number
- `tx_id`: Transmitter ID
- `azimuth`: Azimuth angle (degrees)
- `distance_ring`: Distance ring endpoint (km)
- `distance_km`: Actual distance of last point (km)
- `frequency_ghz`: Frequency (GHz)
- `Lb`: Basic transmission loss (dB)
- `Ep`: Electric field strength (dBμV/m)
- `elapsed_s`: Computation time (seconds)

### Excel Output
Same columns as CSV with:
- Auto-adjusted column widths
- Professional formatting
- Single sheet named "P1812 Results"

## Usage

```python
from mst_gis.propagation import batch_processor_v2

# Run batch processor
result = batch_processor_v2.main(
    profiles_dir="data/input/profiles",
    output_dir="data/output/spreadsheets"
)

# Access results
print(f"CSV:  {result['csv_path']}")
print(f"Excel: {result['xlsx_path']}")
print(f"Results: {len(result['results'])} profiles processed")
```

## Sample Output Structure

For 432 profiles with 36 azimuths and 11 km max distance:

```
Profile Index | TX ID | Azimuth | Ring | Distance | Lb     | Ep
              |       | (°)     | (km) | (km)     | (dB)   | (dBμV/m)
1             | TX_0001 | 0.0  | 1    | 0.30     | 145.32 | -45.21
2             | TX_0001 | 0.0  | 2    | 0.60     | 142.15 | -48.37
...
432           | TX_0001 | 350.0| 11   | 11.00    | 89.45  | -101.18
```

## Version Tracking Benefits

The smart filename includes:

1. **Input-Output Traceability**: Output filename directly references input metadata
2. **Version Control**: Timestamp and hash allow tracking of multiple runs
3. **Self-Documenting**: Filename clearly shows dataset configuration (azimuths, distance, etc.)
4. **Collision Avoidance**: Timestamp + hash prevent accidental overwrites
5. **Reproducibility**: Can regenerate exact same output if timestamp/input match

## Example Version History

```
profiles_TX_0001_432p_36az_11km_v20260209_094130_a7f2c3e1.csv  (first run)
profiles_TX_0001_432p_36az_11km_v20260209_094148_6e44e765.csv  (second run)
results_TX_0001_432p_36az_11km_v20260209_094148_6e44e765.csv   (output from 2nd run)
results_TX_0001_432p_36az_11km_v20260209_094148_6e44e765.xlsx  (output from 2nd run)
```

Different hashes (a7f2c3e1 vs 6e44e765) indicate the input data changed between runs.

## Output Directory Structure

```
data/output/spreadsheets/
├── results_TX_0001_432p_36az_11km_v20260209_094130_a7f2c3e1.csv
├── results_TX_0001_432p_36az_11km_v20260209_094130_a7f2c3e1.xlsx
├── results_TX_0001_432p_36az_11km_v20260209_094148_6e44e765.csv
└── results_TX_0001_432p_36az_11km_v20260209_094148_6e44e765.xlsx
```

## Next Steps

1. **Profile Validation**: Add minimum point check (P1812 requires >4 points)
2. **Distance Ring Optimization**: Ensure each ring has sufficient points
3. **Batch Statistics**: Add summary statistics (min/max Lb, Ep, etc.)
4. **Multi-TX Support**: Extend for multiple transmitters in single run
5. **Performance Reporting**: Add execution time analysis and optimization metrics

## Known Issues

1. **Short Distance Rings**: 1-2 km rings may have insufficient points for P1812 minimum (5 points)
   - Solution: Filter profiles with < 5 points or adjust distance step size

2. **File Size**: 432 profiles × ~5 KB/profile = ~2 MB (acceptable but could optimize)

## References

- Input profile format: `profiles_TX_ID_PROFILESp_AZIMUTHSaz_DISTANCEkm_vTIMESTAMP_HASH.csv`
- Output location: `/Users/oz/Documents/mst_gis/data/output/spreadsheets/`
- Batch processor: `src/mst_gis/propagation/batch_processor_v2.py`
