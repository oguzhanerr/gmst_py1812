# GMST-Py1812 Radio Propagation Prediction Pipeline

## Project Overview
GMST-Py1812 implements ITU-R P.1812-6 radio propagation prediction for terrestrial point-to-area services (30 MHz to 6 GHz). The system processes terrain profiles from elevation and landcover data sources to calculate basic transmission loss (Lb) and electric field strength (Ep) around a transmitter. Results are exported as CSV and GeoJSON for GIS visualization and analysis.

The pipeline automates a complex 5-phase workflow: setup and elevation caching, landcover data acquisition from Sentinel Hub, receiver point generation, terrain profile extraction, and P.1812 propagation calculations. All data flows through a centralized orchestrator with intelligent error handling and performance optimization.

---

## Pipeline Architecture

### Data Flow
```
config.json → Phase 0 (Setup) → Phase 1 (Landcover) → Phase 2 (Point Gen) → 
Phase 3 (Extract Profiles) → Phase 4 (Format & Export) → results_TX_XXXX_*.csv
                                         ↓
                                   GeoJSON outputs
```

### Phase Breakdown

**Phase 0: Setup & Configuration**
- Creates project directories (data/input, data/output, data/landcover, data/srtm, etc.)
- Validates configuration parameters
- Pre-downloads and caches SRTM elevation data for the transmitter location
- Initializes raster data handlers

**Phase 1: Landcover Data Preparation**
- Authenticates with Sentinel Hub using OAuth credentials
- Downloads ESA WorldCover 10m resolution GeoTIFFs for transmitter buffer area
- Caches GeoTIFFs to avoid re-downloading (indexed by lat/lon/year/buffer/resolution)
- Returns path to cached landcover raster

**Phase 2: Receiver Point Generation**
- Generates uniformly distributed receiver points at multiple distances and azimuths around transmitter
- Creates rings at distances 0km to max_distance_km in sampling_resolution_m increments
- Distributes azimuth_step equally around compass (default: 36 azimuths = 10° spacing)
- Outputs GeoDataFrame with tx_id, rx_id, distance_km, azimuth_deg, geometry (WGS84)

**Phase 3: Data Extraction**
- Extracts elevation values from pre-loaded SRTM DEM (30m resolution)
- Extracts landcover class codes from cached Sentinel Hub GeoTIFF (10m resolution)
- Extracts radio-climatic zones (Sea/Coastal/Inland) via spatial join with GeoJSON reference
- Uses vectorized batch processing with pre-loaded raster arrays for 5-8x speedup
- Returns enriched GeoDataFrame with elevation, landcover, zone columns

**Phase 4: Profile Formatting & CSV Export**
- Samples elevation along 360+ terrain profiles (one per azimuth direction) from TX to receiver rings
- Calculates profile-specific land cover resistivity arrays using LCM10 classification rules
- Formats data into P.1812-compatible parameter arrays: [frequency, time_pct, distance[], height[], R[], Ct[], zone[], htg, hrg, pol, ...]
- Exports as CSV with smart naming: `profiles_TX_XXXX_NNNp_MNaz_XXkm_vYYYYMMDD_HHMMSS_HASH.csv`

**Phase 5: P.1812 Propagation Calculation**
- Loads formatted CSV profile data
- Calls Py1812 `P1812.bt_loss()` for each profile
- Returns basic transmission loss (Lb in dB) and electric field strength (Ep in dBμV/m)
- Exports results as CSV: `results_TX_XXXX_NNNp_MNaz_XXkm_vYYYYMMDD_HHMMSS_HASH.csv`
- Optional: generates GeoJSON features for visualization

---

## Directory Structure

```
gmst_py1812/
├── src/                          # Main source code
│   ├── pipeline/                 # 5-phase pipeline modules
│   │   ├── config.py             # Configuration loading and validation
│   │   ├── data_preparation.py   # Sentinel Hub landcover acquisition
│   │   ├── point_generation.py   # Receiver point generation
│   │   ├── data_extraction.py    # Batch raster extraction (elevation, landcover, zones)
│   │   ├── formatting.py         # Profile formatting for P.1812
│   │   └── orchestration.py      # Unified phase orchestrator
│   ├── propagation/              # P.1812 propagation calculation
│   │   ├── propagation_calculator.py   # Batch P.1812 calculations
│   │   ├── profile_parser.py     # CSV profile parsing
│   │   └── profile_extraction.py # Terrain profile utilities (elevation sampling, credentialing)
│   └── utils/                    # Utilities
│       ├── logging.py            # Timer, ProgressTracker, formatted output
│       └── validation.py         # Config and GeoDataFrame validation
├── Py1812_lib/                   # ITU-R P.1812-6 library
│   └── src/Py1812/               # Main propagation model
│       ├── P1812.py              # Core bt_loss() function
│       └── maps/                 # Digital maps (DN50.TXT, N050.TXT, P1812.npz)
├── data/                         # Data directory structure
│   ├── input/                    # Input profile CSVs
│   │   └── profiles/             # Pre-formatted terrain profiles
│   ├── output/                   # Final outputs
│   │   └── [results CSVs, GeoJSON files]
│   ├── landcover/                # Cached Sentinel Hub GeoTIFFs
│   │   └── [LC_XXXX_YYYY_HASH.tif, LC_XXXX_YYYY_HASH.json]
│   ├── srtm/                     # Cached SRTM 30m HGT tiles
│   │   └── [N09W014.hgt, etc.]
│   ├── brzones/                  # ITU radio-climatic zone reference (GeoJSON)
│   │   └── zones_reference.geojson
│   └── notebooks/                # Jupyter notebooks (development/testing)
├── scripts/                      # Entry point scripts
│   ├── run_propagation_calculator.py   # Phase 5 batch processor
│   └── test_full_pipeline_e2e.py       # End-to-end test
├── tests/                        # Unit tests (if present)
├── config_example.json           # Default configuration template
├── config_sentinel_hub.py        # Sentinel Hub credentials (create this file)
├── requirements.txt              # Python dependencies
├── README.md                     # Quick start guide
└── DOCUMENTATION.md              # This file
```

---

## Core Components

### src/pipeline/config.py
**Purpose**: Load, validate, and manage pipeline configuration.

**Key Classes**:
- `ConfigManager`: Main configuration handler
  - `load(path)`: Load config from JSON/YAML file
  - `get(section, key)`: Retrieve config value
  - `validate()`: Validate all parameters
  - `to_file(path)`: Save config to disk

**Key Functions**:
- `_load_default_config()`: Load defaults from config_example.json
- `_load_sentinel_hub_credentials(config)`: Auto-load SH credentials from config_sentinel_hub.py

**Configuration Sections**:
```json
{
  "TRANSMITTER": {
    "tx_id": "TX_0001",
    "latitude": 9.0,
    "longitude": -14.0,
    "antenna_height_tx": 50,
    "antenna_height_rx": 1.5
  },
  "P1812": {
    "frequency_ghz": 0.8,
    "time_percentage": 50,
    "polarization": 1
  },
  "RECEIVER_GENERATION": {
    "max_distance_km": 11.0,
    "azimuth_step": 10,
    "distance_step": 0.03,
    "sampling_resolution": 30
  },
  "SENTINEL_HUB": {
    "client_id": "...",
    "client_secret": "...",
    "collection_id": "...",
    "year": 2020,
    "buffer_m": 11000,
    "chip_px": 734
  }
}
```

---

### src/pipeline/data_preparation.py
**Purpose**: Acquire landcover data from Sentinel Hub with intelligent caching.

**Key Classes**:
- `SentinelHubClient`: OAuth client for Sentinel Hub API
  - `get_token()`: Obtain/refresh access token
  - `get_landcover(lat, lon, collection_id, year, buffer_m, chip_px)`: Download landcover GeoTIFF
  
- `LandCoverProcessor`: Caching layer for landcover data
  - `has_cached(lat, lon, year, buffer_m, chip_px)`: Check if data already cached
  - `get_cache_path(...)`: Get path to cached GeoTIFF
  - `process(...)`: Download or retrieve from cache

**Key Functions**:
- `prepare_landcover(config, landcover_dir)`: Phase 1 entry point

**Output**:
- GeoTIFF files cached as: `LC_{lat}_{lon}_{year}_{hash}.tif`
- Metadata JSON: `LC_{lat}_{lon}_{year}_{hash}.json` (stores parameters for cache validation)

---

### src/pipeline/point_generation.py
**Purpose**: Generate uniformly distributed receiver points around transmitter.

**Key Classes**:
- `Transmitter`: NamedTuple containing tx_id, lon, lat, htg, f, pol, p, hrg

**Key Functions**:
- `generate_receivers_radial_multi(tx, distances_km, azimuths_deg, include_tx_point)`: Create receiver GeoDataFrame
  - Inputs: Transmitter, list of distances (km), list of azimuths (degrees)
  - Outputs: GeoDataFrame with tx_id, rx_id, distance_km, azimuth_deg, geometry (WGS84)
  - Uses UTM projection internally for accurate azimuth/distance calculations
  
- `generate_distance_array(min_km, max_km, step_km)`: Create distance array
  - Returns numpy array of distances in km
  
- `generate_azimuth_array(num_azimuths, start_deg)`: Create azimuth array
  - Returns numpy array of azimuths in degrees [0, 360)
  
- `generate_receiver_grid(tx, max_distance_km, sampling_resolution_m, num_azimuths)`: Phase 2 entry point
  - Combines distance and azimuth generation
  - Returns full receiver GeoDataFrame

---

### src/pipeline/data_extraction.py
**Purpose**: Extract elevation, landcover, and zone data in batch with pre-loaded rasters.

**Key Classes**:
- `RasterPreloader`: Load and cache raster arrays in memory
  - `load_landcover(tif_path)`: Pre-load landcover GeoTIFF
  - `load_dem(dem_path)`: Pre-load DEM (VRT or GeoTIFF), with SRTM.py fallback
  - `load_zones_geojson(zones_path)`: Load zone polygons
  - `extract_landcover_batch(gdf)`: Get land cover codes for all points (5-8x faster via pre-loading)
  - `extract_elevation_batch(gdf)`: Get elevation values for all points
  - `extract_zones_batch(gdf)`: Perform spatial join to get radio-climatic zones

**Key Functions**:
- `extract_data_for_receivers(receivers_gdf, config, phase0_paths)`: Phase 3 entry point
  - Coordinates RasterPreloader to extract all data in batch
  - Returns enriched GeoDataFrame with elevation, landcover, zone columns

**Performance Optimization**:
- Pre-loads raster arrays once, indexes all points efficiently
- Vectorized spatial joins for zone assignment
- Fallback to SRTM.py for elevation when DEM VRT unavailable
- ~5-8x speedup vs. per-point queries

---

### src/pipeline/formatting.py
**Purpose**: Convert enriched receiver points to P.1812-compatible terrain profile format.

**Key Classes**:
- `ProfileFormatter`: Format and export profiles
  - `format_profiles(enriched_gdf, config)`: Convert to profile format
  - `export_profiles_csv(profiles, output_path)`: Save to CSV with smart naming

**Key Functions**:
- `_sample_terrain_profile(tx, rx_list, elevation_dict, landcover_dict, ...)`: Extract terrain samples along ray path
  - Performs line-of-sight sampling from TX to each RX
  - Interpolates elevation at regular intervals
  - Looks up land cover and zone at each point
  
- `_create_p1812_parameters(profile_data, config)`: Format into P.1812 parameter arrays
  - Returns: [f, p, d[], h[], R[], Ct[], zone[], htg, hrg, pol, ...]
  
- `format_and_export_profiles(enriched_gdf, config, phase0_paths)`: Phase 4 entry point
  - Generates all terrain profiles
  - Exports as CSV: `profiles_TX_XXXX_NNNp_MNaz_XXkm_vYYYYMMDD_HHMMSS_HASH.csv`

**Output CSV Format**:
- Semicolon-delimited
- Columns: frequency, time_percentage, distances[], heights[], R[], Ct[], zone[], htg, hrg, pol, phi_t, phi_r, lam_t, lam_r, azimuth, distance_ring, tx_id
- One row per terrain profile (one per azimuth direction at each distance ring)

---

### src/pipeline/orchestration.py
**Purpose**: Unified orchestrator coordinating all 5 pipeline phases.

**Key Classes**:
- `PipelineOrchestrator`: Main orchestrator
  - `__init__(config_path, config_dict)`: Initialize with config
  - `run_phase0_setup(project_root)`: Phase 0 execution
  - `run_phase1_dataprep(landcover_cache_dir)`: Phase 1 execution
  - `run_phase2_generation(max_distance, num_azimuths)`: Phase 2 execution
  - `run_phase3_extraction()`: Phase 3 execution
  - `run_phase4_formatting()`: Phase 4 execution
  - `run_all_phases(project_root)`: Execute all phases sequentially

**State Tracking**:
- Tracks completion of each phase
- Stores intermediate outputs (GeoDataFrames, paths)
- Validates phase dependencies (e.g., Phase 1 requires Phase 0)

**Usage Example**:
```python
from pipeline.orchestration import PipelineOrchestrator

orchestrator = PipelineOrchestrator(config_path="config.json")
paths = orchestrator.run_phase0_setup()
lc_path = orchestrator.run_phase1_dataprep()
receivers = orchestrator.run_phase2_generation()
enriched = orchestrator.run_phase3_extraction()
profiles = orchestrator.run_phase4_formatting()
```

---

### src/propagation/propagation_calculator.py
**Purpose**: Batch P.1812 propagation loss calculations.

**Key Functions**:
- `main(profiles_dir, output_dir)`: Phase 5 entry point
  - Loads profile CSV from Phase 4
  - Calls `Py1812.P1812.bt_loss()` for each profile
  - Returns basic transmission loss (Lb in dB) and electric field strength (Ep in dBμV/m)
  - Exports results CSV with smart naming: `results_TX_XXXX_NNNp_MNaz_XXkm_vYYYYMMDD_HHMMSS_HASH.csv`
  
- `load_profiles(profiles_dir, return_path=True)`: Parse CSV profiles
  - Handles semicolon-delimited format
  - Returns list of parameter tuples
  
- `process_loss_parameters(profile, tx_id_default)`: Extract P.1812 parameters from CSV row
  - Parses [f, p, d[], h[], R[], Ct[], zone[], htg, hrg, pol, ...] 
  - Returns tuple (f, p, d, h, R, Ct, zone, htg, hrg, pol) and tx_id
  
- `_save_results(results, input_csv_path, output_dir)`: Save results with smart naming
  - Extracts metadata from input filename
  - Generates output filename matching input format

**Output CSV Columns**:
```
index, tx_id, azimuth, distance_ring, distance_km, num_distance_points,
frequency_ghz, time_percentage, polarization,
antenna_height_tx_m, antenna_height_rx_m,
tx_lat, tx_lon, rx_lat, rx_lon,
Lb, Ep, elapsed_s
```

---

### src/propagation/profile_parser.py
**Purpose**: Parse and validate terrain profile CSV data.

**Key Functions**:
- `load_profiles(profiles_dir, return_path=True)`: Load all profiles from directory
  - Reads semicolon-delimited CSV
  - Validates each profile (>4 points required for P.1812)
  - Returns list of parsed profiles
  
- `process_loss_parameters(profile, tx_id_default)`: Extract P.1812 parameters
  - Converts CSV row to parameter arrays
  - Extracts tx_id from column 17 (index 16)

---

### src/propagation/profile_extraction.py
**Purpose**: Utilities for terrain profile extraction and elevation sampling.

**Key Functions**:
- `set_srtm_cache_dir(cache_dir)`: Configure custom SRTM cache directory
  - Sets global cache path
  - Clears cached data to force re-initialization
  
- `_get_srtm_data()`: Lazy-load SRTM.py handler
  - Imports srtm module on first call
  - Uses custom cache dir if set
  - Caches handler for subsequent calls
  
- `meters_to_deg(lat, meters)`: Convert meters to lat/lon degrees
  - Returns (dlat, dlon) at given latitude
  
- `get_token(client_id, client_secret, token_url, verbose)`: Obtain Sentinel Hub OAuth token
  - Makes POST request to token endpoint
  - Handles token refresh and expiry
  
- `resolve_credentials(env_var_id, env_var_secret, fallback_id, fallback_secret)`: Get Sentinel Hub credentials
  - Checks environment variables first
  - Falls back to provided constants
  - Validates credentials are not placeholders

---

### src/utils/logging.py
**Purpose**: Logging utilities with formatted output and timing.

**Key Classes**:
- `Timer`: Context manager for measuring elapsed time
  - `__enter__()`, `__exit__()`: Automatic timing
  - `.elapsed`: Get elapsed seconds
  
- `ProgressTracker`: Track progress across batch operations
  - `.update(current, total)`: Update progress
  - `.log_summary()`: Print summary statistics

**Key Functions**:
- `print_success(msg)`: Print green success message
- `print_warning(msg)`: Print yellow warning message
- `print_error(msg)`: Print red error message

---

### src/utils/validation.py
**Purpose**: Configuration and data validation.

**Key Functions**:
- `validate_config(config)`: Validate entire config dictionary
  - Checks required sections and keys
  - Validates value ranges and types
  - Raises ValidationError if invalid
  
- `validate_geodataframe(gdf, required_columns)`: Validate GeoDataFrame structure
  - Checks column existence
  - Validates CRS
  
- `validate_path_exists(path)`: Check if file/directory exists

---

## Usage Examples

### Quick Start: Full Pipeline

```python
from pathlib import Path
from pipeline.orchestration import PipelineOrchestrator

# Initialize with config
orchestrator = PipelineOrchestrator(config_path="config.json")

# Run all phases
project_root = Path.cwd()
orchestrator.run_phase0_setup(project_root)
orchestrator.run_phase1_dataprep()
orchestrator.run_phase2_generation()
orchestrator.run_phase3_extraction()
orchestrator.run_phase4_formatting()

# Phase 5: Run P.1812 calculations
from propagation.propagation_calculator import main
results_path = main(
    profiles_dir=project_root / "data" / "output" / "profiles",
    output_dir=project_root / "data" / "output"
)
print(f"Results saved to: {results_path}")
```

### Individual Phase Example

```python
from pipeline.config import ConfigManager
from pipeline.point_generation import generate_receiver_grid, Transmitter

# Load config
config_manager = ConfigManager.from_file("config.json")
config = config_manager.config

# Create transmitter
tx = Transmitter(
    tx_id="TX_0001",
    lon=config['TRANSMITTER']['longitude'],
    lat=config['TRANSMITTER']['latitude'],
    htg=config['TRANSMITTER']['antenna_height_tx'],
    f=config['P1812']['frequency_ghz'],
    pol=config['P1812']['polarization'],
    p=config['P1812']['time_percentage'],
    hrg=config['TRANSMITTER']['antenna_height_rx']
)

# Generate receivers (Phase 2)
receivers_gdf = generate_receiver_grid(
    tx=tx,
    max_distance_km=config['RECEIVER_GENERATION']['max_distance_km'],
    sampling_resolution_m=config['RECEIVER_GENERATION']['sampling_resolution'],
    num_azimuths=int(360 / config['RECEIVER_GENERATION']['azimuth_step'])
)

print(f"Generated {len(receivers_gdf)} receiver points")
print(receivers_gdf.head())
```

### Data Extraction Example

```python
from pipeline.data_extraction import extract_data_for_receivers
from pipeline.orchestration import PipelineOrchestrator

orchestrator = PipelineOrchestrator(config_path="config.json")
paths = orchestrator.run_phase0_setup()

# Assuming Phase 2 completed and receivers_gdf available
enriched_gdf = extract_data_for_receivers(receivers_gdf, config, paths)

print(enriched_gdf[['distance_km', 'azimuth_deg', 'elevation_m', 'landcover_code', 'zone']].head())
```

---

## Configuration Reference

### config_example.json Structure

```json
{
  "TRANSMITTER": {
    "tx_id": "TX_0001",
    "latitude": 9.0,
    "longitude": -14.0,
    "antenna_height_tx": 50.0,
    "antenna_height_rx": 1.5
  },
  "P1812": {
    "frequency_ghz": 0.8,
    "time_percentage": 50,
    "polarization": 1
  },
  "RECEIVER_GENERATION": {
    "max_distance_km": 11.0,
    "azimuth_step": 10.0,
    "distance_step": 0.03,
    "sampling_resolution": 30.0
  },
  "SENTINEL_HUB": {
    "client_id": "",
    "client_secret": "",
    "collection_id": "",
    "token_url": "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    "process_url": "https://sh.dataspace.copernicus.eu/api/v1/process",
    "year": 2020,
    "buffer_m": 11000.0,
    "chip_px": 734
  }
}
```

### Configuration Parameters

| Parameter | Section | Type | Description |
|-----------|---------|------|-------------|
| `tx_id` | TRANSMITTER | str | Transmitter ID (e.g., TX_0001) |
| `latitude` | TRANSMITTER | float | TX latitude (WGS84) |
| `longitude` | TRANSMITTER | float | TX longitude (WGS84) |
| `antenna_height_tx` | TRANSMITTER | float | TX antenna height above ground (m) |
| `antenna_height_rx` | TRANSMITTER | float | RX antenna height above ground (m) |
| `frequency_ghz` | P1812 | float | Frequency (GHz), 0.03-6 |
| `time_percentage` | P1812 | int | Time percentage (%), 1-50 |
| `polarization` | P1812 | int | 1=horizontal, 2=vertical |
| `max_distance_km` | RECEIVER_GENERATION | float | Maximum distance to receivers (km) |
| `azimuth_step` | RECEIVER_GENERATION | float | Azimuth spacing (degrees, e.g., 10 = 36 azimuths) |
| `distance_step` | RECEIVER_GENERATION | float | Distance sampling in profile extraction (km) |
| `sampling_resolution` | RECEIVER_GENERATION | float | Distance between receiver rings (m) |
| `client_id` | SENTINEL_HUB | str | Sentinel Hub OAuth client ID |
| `client_secret` | SENTINEL_HUB | str | Sentinel Hub OAuth client secret |
| `collection_id` | SENTINEL_HUB | str | BYOC collection ID for landcover |
| `year` | SENTINEL_HUB | int | Year to query (e.g., 2020) |
| `buffer_m` | SENTINEL_HUB | float | Buffer radius around TX (m) |
| `chip_px` | SENTINEL_HUB | int | Output chip size (pixels) |

### Sentinel Hub Credentials Setup

1. Create file: `config_sentinel_hub.py` in project root
2. Add your credentials:

```python
# config_sentinel_hub.py
SH_CLIENT_ID = "your_client_id"
SH_CLIENT_SECRET = "your_client_secret"
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
COLLECTION_ID = "your_collection_id"
```

Alternatively, set environment variables:
```bash
export SH_CLIENT_ID="your_client_id"
export SH_CLIENT_SECRET="your_client_secret"
```

---

## API Reference: P.1812.bt_loss()

The core propagation function from Py1812_lib:

```python
Lb, Ep = Py1812.P1812.bt_loss(f, p, d, h, R, Ct, zone, htg, hrg, pol)
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `f` | float | Frequency (GHz), valid range 0.03-6 |
| `p` | float | Time percentage (%), valid range 1-50 |
| `d` | ndarray | Distance profile (km), length > 4 |
| `h` | ndarray | Height profile (m above sea level) |
| `R` | ndarray | Land cover resistance (dB/km) |
| `Ct` | ndarray | Clutter transmission loss (dB/m) |
| `zone` | ndarray | Radio-climatic zones: 1=Sea, 3=Coastal, 4=Inland |
| `htg` | float | TX antenna height above ground (m) |
| `hrg` | float | RX antenna height above ground (m) |
| `pol` | int | Polarization: 1=horizontal, 2=vertical |

### Returns

| Return | Type | Description |
|--------|------|-------------|
| `Lb` | float | Basic transmission loss (dB) |
| `Ep` | float | Electric field strength (dBμV/m) at RX |

### Example

```python
import Py1812.P1812
import numpy as np

# Define terrain profile
frequencies = np.array([0.8])  # 0.8 GHz
d = np.array([0, 2, 4, 6, 8, 10, 11])  # km
h = np.array([100, 150, 200, 180, 160, 140, 120])  # m asl
R = np.array([0, 5, 5, 5, 5, 5, 5])  # dB/km land cover resistance
Ct = np.array([0, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01])  # dB/m clutter loss

Lb, Ep = Py1812.P1812.bt_loss(
    f=0.8,
    p=50,
    d=d,
    h=h,
    R=R,
    Ct=Ct,
    zone=np.array([1, 3, 4, 4, 4, 4, 4]),  # Sea, coastal, inland
    htg=50,  # TX height above ground
    hrg=1.5,  # RX height above ground
    pol=1  # Horizontal polarization
)

print(f"Transmission loss: {Lb:.2f} dB")
print(f"Electric field: {Ep:.2f} dBμV/m")
```

---

## Land Cover Classification

The pipeline uses ESA WorldCover 10m resolution classes mapped to P.1812 resistance (R) and clutter transmission loss (Ct):

| Class | Description | R (dB/km) | Ct (dB/m) |
|-------|-------------|-----------|-----------|
| 10 | Trees | 8 | 0.02 |
| 20 | Shrubland | 5 | 0.01 |
| 30 | Grassland | 2 | 0.005 |
| 40 | Cropland | 3 | 0.008 |
| 50 | Built-up | 5 | 0.01 |
| 60 | Barren land | 1 | 0.002 |
| 70 | Snow/Ice | 0 | 0 |
| 80 | Water bodies | 0 | 0 |
| 90 | Herbaceous wetland | 2 | 0.005 |
| 95 | Mangrove | 8 | 0.02 |
| 254 | Unknown/Nodata | 0 | 0 |

---

## Troubleshooting

### Issue: Sentinel Hub authentication fails
**Cause**: Invalid credentials or network connectivity
**Solution**:
1. Verify `config_sentinel_hub.py` contains correct credentials
2. Check internet connectivity
3. Ensure SH_CLIENT_ID and SH_CLIENT_SECRET are not empty strings
4. Test credentials with: `python -c "from pipeline.data_preparation import SentinelHubClient; client = SentinelHubClient('ID', 'SECRET'); print(client.get_token())"`

### Issue: SRTM download timeout
**Cause**: Large tile download (30-45 seconds) or slow connection
**Solution**:
1. Ensure stable internet connection
2. SRTM caches automatically; subsequent runs reuse cached tiles
3. Manually pre-download tiles to data/srtm/ if needed

### Issue: GeoDataFrame has wrong CRS
**Cause**: Coordinate transformation error during point generation
**Solution**:
1. Verify transmitter coordinates are in WGS84 (lon, lat)
2. Check latitude is in [-90, 90], longitude in [-180, 180]

### Issue: P.1812 profile validation fails (< 5 points)
**Cause**: Terrain profile has insufficient elevation samples
**Solution**:
1. Increase max_distance_km or decrease distance_step
2. Reduce sampling_resolution (closer receiver rings)
3. Check elevation data has valid values (not all nodata)

### Issue: Memory error with large receiver grids
**Cause**: Too many receiver points (> 100k)
**Solution**:
1. Reduce max_distance_km
2. Increase azimuth_step (fewer azimuths)
3. Increase sampling_resolution (fewer distance rings)

---

## Performance Notes

- **Phase 0**: 30-45 seconds (SRTM download on first run, cached thereafter)
- **Phase 1**: 20-60 seconds (Sentinel Hub API call, cached by default)
- **Phase 2**: < 1 second (point generation is very fast)
- **Phase 3**: 2-5 seconds (batch raster extraction with pre-loading optimization)
- **Phase 4**: 10-30 seconds (profile sampling and formatting)
- **Phase 5**: 10-20 seconds (1500+ P.1812 calculations)

**Total**: ~1-2 minutes for full pipeline on typical hardware

**Optimization**: Pre-loading raster arrays in Phase 3 provides 5-8x speedup vs. per-point queries. Phase 4 profile sampling is I/O bound; performance scales with disk speed.

---

## Development & Testing

### Run End-to-End Pipeline Test

```bash
python scripts/test_full_pipeline_e2e.py
```

This script:
1. Validates config.json
2. Runs all 5 phases sequentially
3. Generates test profiles and results
4. Compares outputs with expected schema

### Run Unit Tests (if available)

```bash
pytest tests/
```

### Debug Configuration

Add debug output to config.json:

```json
{
  "DEBUG": {
    "verbose": true,
    "save_intermediate_gdf": true,
    "profile_sampling_step": 0.1
  }
}
```

---

## References

- **ITU-R P.1812-6**: Radio propagation prediction method for point-to-area terrestrial services
- **ESA WorldCover**: Land cover classification at 10m resolution
- **SRTM**: Shuttle Radar Topography Mission 30m DEM
- **Sentinel Hub**: Copernicus Data Space Ecosystem API
- **Py1812**: Python implementation of ITU-R P.1812-6 (included)
