# Configuration Guide - Single Source of Truth

## Overview
All pipeline configuration is now centralized in a **single file**: `config_example.json`

This file is used by:
- ✅ Python modules (via `src/gmst_py1812/pipeline/config.py`)
- ✅ All CLI scripts (production pipeline)
- ⏳ Phase 0 notebook (to be updated - currently still has hardcoded CONFIG)

---

## The Single Source of Truth

**File**: `/config_example.json`

This JSON file contains ALL configuration parameters:
- Transmitter location and antenna heights
- P.1812 parameters (frequency, polarization, time percentage)
- Receiver grid generation settings
- Sentinel Hub API parameters
- Land cover mappings

---

## How to Change Configuration

### For Python Scripts / Production Pipeline
All scripts automatically load from `config_example.json`:

```bash
# Edit the config file directly
vi config_example.json

# Run scripts - they will use the updated values
python scripts/run_full_pipeline.py

# Or explicitly pass a different config if needed
python scripts/run_full_pipeline.py --config custom_config.json
```

### For Notebooks (Phase 0-5)
⏳ **TODO**: Phase 0 notebook currently still has hardcoded CONFIG dict.

**Temporary workaround** until Phase 0 is updated:

1. **Edit Phase 0 notebook**: `notebooks/phase0_setup.ipynb`
2. Find the "config" cell (lines 204-232)
3. Update the `CONFIG` dictionary values manually
4. Run the notebook

**After update**, notebooks will load from `config_example.json` automatically.

---

## Configuration Structure

```json
{
  "TRANSMITTER": {
    "tx_id": "TX_0001",                    // Transmitter identifier
    "longitude": -13.40694,                // Transmitter longitude (deg)
    "latitude": 9.345,                     // Transmitter latitude (deg)
    "antenna_height_tx": 57,               // TX antenna height above ground (m)
    "antenna_height_rx": 10                // RX antenna height above ground (m)
  },
  "P1812": {
    "frequency_ghz": 0.9,                  // Frequency (0.03-6 GHz)
    "time_percentage": 50,                 // Time percentage (1-50%)
    "polarization": 1                      // 1=horizontal, 2=vertical
  },
  "RECEIVER_GENERATION": {
    "max_distance_km": 11,                 // Maximum radius (km)
    "azimuth_step": 10,                    // Azimuth spacing (degrees)
    "distance_step": 0.03,                 // Distance spacing (km) ← THIS IS WHAT YOU WANTED TO CHANGE!
    "sampling_resolution": 30              // Terrain sampling (m)
  },
  "SENTINEL_HUB": {
    "buffer_m": 11000,                     // Search buffer (m)
    "chip_px": 734,                        // Chip size (pixels)
    "year": 2020                           // Land cover year
  },
  "LCM10_TO_CT": {
    // Mapping: Land Cover Class → P.1812 Category
    "100": 1, ...                          // Water/Sea → Class 1
    "20": 3, ...                           // Shrubland → Class 3
    "10": 4, ...                           // Forest → Class 4
  },
  "CT_TO_R": {
    // Mapping: P.1812 Category → Resistance (ohms)
    "1": 0,                                // Class 1 → 0 ohms
    "3": 10,                               // Class 3 → 10 ohms
    "4": 15                                // Class 4 → 15 ohms
  }
}
```

---

## Example: Change Number of Distance Points

**Before**: 368 points (0.03 km step = ~30 m)

**Goal**: 110 points (0.1 km step = ~100 m)

### Solution:
1. Edit `config_example.json`
2. Change `"distance_step": 0.03` → `"distance_step": 0.1`
3. Save file
4. Run pipeline:

```bash
python scripts/run_full_pipeline.py
```

✅ All phases will now use 0.1 km spacing instead of 0.03 km

---

## Example: Change Transmitter Location

**Goal**: Move transmitter to latitude 10.5, longitude -14.0

### Solution:
1. Edit `config_example.json`
2. Update:
   - `"latitude": 10.5`
   - `"longitude": -14.0`
3. Save file
4. Run pipeline

✅ All receiver points will be generated around the new TX location

---

## Advanced: Load Custom Config

To use a different config file without editing the default:

```bash
# Create custom config
cp config_example.json config_senegal_case2.json
vi config_senegal_case2.json

# Run with custom config
python scripts/run_full_pipeline.py --config config_senegal_case2.json
```

---

## Technical Details

### How Python Modules Load Config
**File**: `src/gmst_py1812/pipeline/config.py`

```python
def _load_default_config() -> Dict[str, Any]:
    """Load default configuration from config_example.json."""
    config_path = Path(__file__).parent.parent.parent / 'config_example.json'
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    raise ConfigError(f"Default config file not found: {config_path}")

DEFAULT_CONFIG: Dict[str, Any] = _load_default_config()
```

On module import:
1. Looks for `config_example.json` in project root
2. Loads JSON into `DEFAULT_CONFIG` dictionary
3. All functions use this loaded config
4. If `--config <path>` is passed to scripts, that file is used instead

### Configuration Manager
```python
# Load default config
config_mgr = ConfigManager.from_defaults()

# Or load from file
config_mgr = ConfigManager.from_file(Path('my_config.json'))

# Access values
freq = config_mgr.get('P1812', 'frequency_ghz')
```

---

## What Gets Fixed When Phase 0 Is Updated

Currently, Phase 0 notebook has its own hardcoded `CONFIG` dict.

**When updated** to load from `config_example.json`:
- ✅ Notebooks will use same values as scripts
- ✅ No more confusion about which config is being used
- ✅ Single place to edit for all phases
- ✅ Easy to create multiple experiment configs

---

## Validation

When config is loaded, it's automatically validated for:
- Required fields present
- Value types correct (int, float, dict, etc.)
- Frequency in range [0.03, 6] GHz
- Distance values non-negative
- Required sections present

If validation fails, you'll get a clear error message indicating what's wrong.

---

## Summary

| What | Where | Loads From | Status |
|------|-------|-----------|--------|
| Python Scripts | `src/gmst_py1812/pipeline/config.py` | `config_example.json` | ✅ Done |
| Phase 0-5 Notebooks | `notebooks/phase0_setup.ipynb` | Hardcoded CONFIG dict | ⏳ TODO |

**Next**: Update Phase 0 notebook to load from `config_example.json` instead of hardcoded CONFIG
