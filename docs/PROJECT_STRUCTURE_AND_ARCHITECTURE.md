# MST-GIS Project Structure and Architecture

This document consolidates all project structure, data flow, and developer guidance for the MST-GIS radio propagation prediction system.

## Table of Contents
1. [Project Overview](#project-overview)
2. [Quick Start](#quick-start)
3. [Directory Structure](#directory-structure)
4. [Data Flow](#data-flow)
5. [Key Components](#key-components)
6. [File Classification](#file-classification)
7. [Data Organization](#data-organization)

---

## Project Overview

MST-GIS implements radio propagation prediction using **ITU-R P.1812-6** for point-to-area terrestrial services (30 MHz to 6 GHz). It processes terrain path profiles to calculate basic transmission loss and electric field strength, outputting results as GeoJSON for GIS visualization.

### Workflow Summary

```
1. PREPARATION (Jupyter Notebook)
   └─ mobile_get_input.ipynb → Generates terrain profiles

2. PROPAGATION (Batch Processor)
   └─ batch_processor.py → Applies ITU-R P.1812-6 model

3. ANALYSIS (Jupyter Notebook)
   └─ read_geojson.ipynb → Visualizes and analyzes results
```

---

## Quick Start

### Build & Run Commands

```bash
# Create/activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install numpy geojson psutil matplotlib

# Install Py1812 from local source (required)
pip install -e ./github_Py1812/Py1812

# Run main batch processor
# (processes profiles from data/input/profiles/, outputs to data/output/geojson/)
python scripts/run_batch_processor.py

# Generate uniformly distributed receiver points using phyllotaxis pattern
python scripts/generate_receiver_points.py <lat> <lon> <num_points> --scale <meters> --geojson --output <file>
```

### Validation

```bash
# Run P1812 validation tests (requires validation_profiles/ data)
cd github_Py1812/Py1812/tests
python validateP1812.py
```

### ITU Digital Maps Setup

The Py1812 library requires ITU digital products (not redistributable). Before first use:

1. Download `DN50.TXT` and `N050.TXT` from ITU-R P.1812 recommendation
2. Place in `github_Py1812/Py1812/src/Py1812/maps/`
3. Run: `python github_Py1812/Py1812/src/Py1812/initiate_digital_maps.py`
4. This generates `P1812.npz` required by the model

---

## Directory Structure

```
gmst_py1812/
├── src/gmst_py1812/                 # Library code (Python packages)
│   ├── __init__.py
│   ├── propagation/             # P1812 propagation logic
│   │   ├── __init__.py
│   │   ├── profile_parser.py    # CSV profile parsing
│   │   ├── batch_processor.py   # Main processing workflow
│   │   └── point_generator.py   # Phyllotaxis point generation
│   └── gis/                     # GeoJSON generation
│       ├── __init__.py
│       └── geojson_builder.py   # GeoJSON FeatureCollection generation
│
├── data/                        # All data (input, intermediate, output)
│   ├── input/                   # Input data (true inputs + references)
│   │   ├── profiles/            # Ready-to-process terrain profiles
│   │   │   ├── paths_oneTx_manyRx_1km.csv    (PRIMARY INPUT)
│   │   │   └── reference/
│   │   │       └── validation_profiles/      (For P1812 validation)
│   │   └── reference/           # Static reference data
│   │       └── zones_map_BR.json             (Radio-climatic zones)
│   │
│   ├── intermediate/            # Regenerable intermediate data
│   │   ├── api_data/            # Cached from Sentinel Hub
│   │   │   └── lcm10_*.tif      (CACHED - can be deleted)
│   │   └── workflow/            # Generated during processing
│   │       └── rx_rings_*.csv   (INTERMEDIATE - can be deleted)
│   │
│   ├── notebooks/               # All Jupyter workflows
│   │   ├── mobile_get_input.ipynb              (GENERATES profiles)
│   │   ├── read_geojson.ipynb                  (ANALYZES results)
│   │   └── mobile_get_input_backup.ipynb       (BACKUP)
│   │
│   └── output/                  # Final results
│       ├── geojson/             # P1812 propagation results
│       │   ├── points_*.geojson        (TX/RX points with loss/field strength)
│       │   ├── lines_*.geojson         (TX→RX link lines)
│       │   └── polygon_*.geojson       (Coverage area boundary)
│       └── spreadsheets/        # Supporting/metadata files
│           ├── paths_oneTx_manyRx.csv
│           └── path_profile_points.xlsx
│
├── scripts/                     # Entry point scripts
│   ├── run_batch_processor.py
│   └── generate_receiver_points.py
│
├── tests/                       # Unit tests
├── docs/                        # Documentation
│
├── .gitignore
├── AGENTS.md                    # Agent guidance (keep for tool context)
└── github_Py1812/              # External P1812 implementation
    └── Py1812/
        ├── src/Py1812/P1812.py          # Core propagation model
        └── tests/validateP1812.py       # Validation tests
```

---

## Data Flow

### Complete Workflow

```
External APIs (Sentinel Hub, SRTM)
    ↓ fetch & cache
data/intermediate/api_data/lcm10_*.tif
    ↓ used by
data/notebooks/mobile_get_input.ipynb
    ├─ Reads: zones_map_BR.json (data/input/reference/)
    ├─ Generates: rx_rings_*.csv → data/intermediate/workflow/
    └─ Outputs: paths_oneTx_manyRx_*.csv → data/input/profiles/
    ↓ INPUT TO
src/gmst_py1812/propagation/batch_processor.py
    ├─ Reads: paths_oneTx_manyRx_*.csv (data/input/profiles/)
    └─ Outputs: *.geojson → data/output/geojson/
    ↓ INPUT TO
data/notebooks/read_geojson.ipynb
    ├─ Reads: *.geojson (data/output/geojson/)
    └─ Generates: visualizations, statistics
```

### Three-Phase Workflow

#### Phase 1: Preparation (mobile_get_input.ipynb)

**Input:**
- Transmitter configuration (lat, lon, frequency, height, polarization)
- Reference data: `zones_map_BR.json`

**Processing:**
1. Fetch land cover from Sentinel Hub
2. Fetch elevation from SRTM
3. Generate receiver points (radial pattern)
4. Extract terrain profiles along TX→RX paths
5. Extract land cover and zone information

**Outputs:**
- `paths_oneTx_manyRx_*.csv` → `data/input/profiles/` (ready for P1812)
- `lcm10_*.tif` → `data/intermediate/api_data/` (cached from API)
- `rx_rings_*.csv` → `data/intermediate/workflow/` (intermediate)

**Duration:** ~5-10 minutes (including API calls)

#### Phase 2: Propagation (batch_processor.py)

**Input:**
- `paths_oneTx_manyRx_*.csv` from `data/input/profiles/`

**Processing:**
- Apply ITU-R P.1812-6 model via `Py1812.bt_loss()`
- Calculate basic transmission loss (Lb) and electric field strength (Ep)
- Generate GeoJSON output files

**Outputs:**
- `points_*.geojson` - TX/RX points with loss/field strength properties
- `lines_*.geojson` - TX→RX link lines
- `polygon_*.geojson` - Coverage area boundary
- All saved to `data/output/geojson/`

#### Phase 3: Analysis (read_geojson.ipynb)

**Input:**
- GeoJSON files from `data/output/geojson/`

**Processing:**
- Extract coverage statistics
- Generate analysis visualizations
- Create summary reports

**Outputs:**
- Visualizations and analysis (saved in notebook or exported)

---

## Key Components

### Scripts (Entry Points)

**`scripts/run_batch_processor.py`**
- Entry point for batch processing
- Reads terrain profiles from `data/input/profiles/`
- Outputs GeoJSON files to `data/output/geojson/`
- Usage: `python scripts/run_batch_processor.py`

**`scripts/generate_receiver_points.py`**
- Generates uniformly distributed receiver points
- Uses golden-angle phyllotaxis pattern
- Outputs as CSV or GeoJSON
- Usage: `python scripts/generate_receiver_points.py <lat> <lon> <num_points> --scale <meters> --geojson --output <file>`

### Source Modules

**`src/gmst_py1812/propagation/batch_processor.py`**
- Core batch processing logic
- Function: `main(profiles_dir=None, output_dir=None)`
- Smart path handling for default input/output directories
- Integrates with Py1812 propagation model

**`src/gmst_py1812/propagation/profile_parser.py`**
- CSV profile parsing
- Function: `load_profiles(profiles_dir)` - Loads all CSV profiles
- Function: `process_loss_parameters(profile)` - Processes profile data

**`src/gmst_py1812/propagation/point_generator.py`**
- Phyllotaxis point generation
- Function: `generate_phyllotaxis(lat0, lon0, num_points, scale=1.0)`
- Generates uniformly distributed points in a circular pattern

**`src/gmst_py1812/gis/geojson_builder.py`**
- GeoJSON generation utilities
- Functions for creating points, lines, and polygons
- Outputs valid GeoJSON FeatureCollections

### External Dependencies

**`github_Py1812/Py1812/src/Py1812/P1812.py`**
- Core ITU-R P.1812-6 propagation model
- Main function: `bt_loss(f, p, d, h, htg, hrg, pol, zone, R, Ct)`
- Returns:
  - `Lb`: Basic transmission loss (dB)
  - `Ep`: Electric field strength (dBμV/m)

---

## File Classification

### File Types and Locations

| File Type | Example | Location | Deletable? | Notes |
|-----------|---------|----------|-----------|-------|
| **Primary Input** | `paths_oneTx_manyRx_1km.csv` | `data/input/profiles/` | ❌ No | Source of truth for profiles |
| **Static Reference** | `zones_map_BR.json` | `data/input/reference/` | ❌ No | Required for processing |
| **Cached from API** | `lcm10_*.tif` | `data/intermediate/api_data/` | ✅ Yes | Regenerable from APIs |
| **Intermediate** | `rx_rings_*.csv` | `data/intermediate/workflow/` | ✅ Yes | Generated during workflows |
| **Final Output** | `points_*.geojson` | `data/output/geojson/` | ⚠️ Archive as needed | P1812 results |
| **Generated Metadata** | `paths_oneTx_manyRx.csv` | `data/output/spreadsheets/` | ✅ Yes | Regenerable |

### Directory Purposes

**`data/input/`** - True inputs needed for processing
- **`profiles/`**: Terrain profiles ready for batch processing
- **`reference/`**: Static reference data (zones, validation data)

**`data/intermediate/`** - Regenerable data (can be safely deleted)
- **`api_data/`**: Cached data fetched from external APIs
- **`workflow/`**: Intermediate files generated during workflows

**`data/notebooks/`** - All Jupyter workflows
- Mobile data acquisition workflow
- Analysis and visualization workflows
- Backup files

**`data/output/`** - Final processing results
- **`geojson/`**: P1812 propagation model outputs (ready for GIS)
- **`spreadsheets/`**: Supporting data tables and metadata

---

## Data Organization

### Profile CSV Format

Input terrain profiles use semicolon-separated CSV format:

**Columns:** `frequency, time_percentage, distances[], heights[], R[], Ct[], zone[], htg, hrg, pol, tx_lat, rx_lat, tx_lon, rx_lon`

- Arrays (distances, heights, etc.) encoded as Python list literals
- Each row represents a complete TX→RX path
- Ready to pass to `Py1812.bt_loss()`

### Output GeoJSON Format

**Points GeoJSON** (`points_*.geojson`)
- FeatureCollection of Point features
- TX point (1 feature) + RX points (N features)
- Properties: `Lb` (loss in dB), `Ep` (field strength in dBμV/m), coordinates, parameters

**Lines GeoJSON** (`lines_*.geojson`)
- FeatureCollection of LineString features
- One line per TX→RX link
- Properties: `rx_id`, `distance_km`, coordinates

**Polygon GeoJSON** (`polygon_*.geojson`)
- FeatureCollection with single Polygon
- Coverage area boundary
- Properties: `name: "Coverage area"`

### Key P1812 Parameters

| Parameter | Description | Range |
|-----------|-------------|-------|
| `f` | Frequency | 0.03-6 GHz |
| `p` | Time percentage | 1-50% |
| `d` | Distance profile array | km |
| `h` | Height profile array | m above sea level |
| `htg/hrg` | TX/RX antenna height | m above ground |
| `pol` | Polarization | 1=horizontal, 2=vertical |
| `zone` | Radio-climatic zone | 1=Sea, 3=Coastal, 4=Inland |

---

## Developer Notes

### Module Imports

Entry point scripts add `src/` to Python path:
```python
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from gmst_py1812.propagation import batch_process
```

### Path Handling

Batch processor uses smart default paths based on `__file__` location:
```python
default_profiles_dir = Path(__file__).parent.parent.parent.parent / "data" / "input" / "profiles"
default_output_dir = Path(__file__).parent.parent.parent.parent / "data" / "output" / "geojson"
```

### Testing

All Python modules compile without syntax errors. Run validation tests:
```bash
cd github_Py1812/Py1812/tests
python validateP1812.py
```

---

## Structure Benefits

✅ **Clear Separation of Concerns**
- Source code organized in `src/`
- Data organized by purpose in `data/`
- Entry points in `scripts/`

✅ **Easy Workflow Discovery**
- All notebooks in `data/notebooks/`
- Clear naming reflects purpose

✅ **Input vs Output Distinction**
- `data/input/` for sources of truth
- `data/output/` for results
- `data/intermediate/` for regenerable data

✅ **Follows Python Standards**
- Proper package structure with `__init__.py`
- Modules with clear responsibilities
- Entry point scripts in `scripts/`

✅ **Scalable and Maintainable**
- Easy to add new workflows
- Easy to add new analysis scripts
- Clear data dependencies

---

## Related Files

- **AGENTS.md** - AI agent guidance (links to this document and command examples)
- **.gitignore** - Excludes output/, intermediate/ generated data
- **tests/** - Unit test directory (for future tests)
