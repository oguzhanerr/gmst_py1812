# Python API Reference

## Main Orchestration

### Run Full Pipeline
```python
from gmst_py1812.pipeline.orchestration import run_pipeline

result = run_pipeline(
    config_path='config.json',
    project_root=None,
    skip_phase1=False
)

print(result['csv_path'])      # Output CSV file path
print(result['total_time'])    # Execution time in seconds
print(result['enriched_gdf'])  # Enriched GeoDataFrame
```

## Individual Phase Execution

### Using PipelineOrchestrator
```python
from gmst_py1812.pipeline.orchestration import PipelineOrchestrator

orchestrator = PipelineOrchestrator(config_path='config.json')

# Run each phase independently
paths = orchestrator.run_phase0_setup(project_root=None)
lc_path = orchestrator.run_phase1_dataprep()
receivers_gdf = orchestrator.run_phase2_generation()
enriched_gdf = orchestrator.run_phase3_extraction()
df_profiles, csv_path = orchestrator.run_phase4_export()
```

## Point Generation

```python
from gmst_py1812.pipeline.point_generation import (
    generate_receiver_grid, 
    Transmitter
)

tx = Transmitter(
    tx_id='TX_0001',
    lon=-13.40694,
    lat=9.345,
    htg=57,
    f=0.9,
    pol=1,
    p=50,
    hrg=10
)

receivers_gdf = generate_receiver_grid(
    tx=tx,
    max_distance_km=11.0,
    distance_step_km=0.03,
    num_azimuths=36,
    include_tx_point=True
)
```

## Data Extraction

```python
from gmst_py1812.pipeline.data_extraction import extract_data_for_receivers

enriched_gdf = extract_data_for_receivers(
    receivers_gdf=receivers_gdf,
    dem_path=Path('/path/to/dem.vrt'),
    landcover_path=Path('/path/to/landcover.tif'),
    zones_path=Path('/path/to/zones.json'),
    lcm10_to_ct={10: 1, 20: 2, ...},
    ct_to_r={1: 0, 2: 10, ...},
    verbose=True
)
```

## Formatting & Export

```python
from gmst_py1812.pipeline.formatting import format_and_export_profiles

df_profiles, csv_path = format_and_export_profiles(
    receivers_gdf=enriched_gdf,
    output_path=Path('output.csv'),
    frequency_ghz=0.9,
    time_percentage=50,
    polarization=1,
    htg=57,
    hrg=10,
    verbose=True
)
```

## Configuration

```python
from gmst_py1812.pipeline.config import ConfigManager

config_mgr = ConfigManager()
config_mgr.load('config.json')

# Access values
freq = config_mgr.get('P1812', 'frequency_ghz')
lat = config_mgr.get('TRANSMITTER', 'latitude')

# Update and save
config_mgr.set('P1812', 'frequency_ghz', 1.0)
config_mgr.save('new_config.json')
```

## Utilities

### Logging
```python
from gmst_py1812.utils.logging import Timer, ProgressTracker, Logger

# Timing
with Timer("My operation"):
    # do something

# Progress tracking
tracker = ProgressTracker(total=1000)
for i in range(1000):
    tracker.update(1)

# Logging
logger = Logger(__name__)
logger.info("Message")
logger.error("Error message")
```

### Validation
```python
from gmst_py1812.utils.validation import (
    ValidationError,
    validate_config,
    validate_receiver_points,
    validate_extracted_data
)

try:
    validate_config(config)
    validate_receiver_points(receivers_gdf)
    validate_extracted_data(enriched_gdf)
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Error Handling

```python
from gmst_py1812.utils.validation import ValidationError

try:
    result = run_pipeline(config_path='config.json')
except ValidationError as e:
    print(f"Configuration error: {e}")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Data Structures

### Receiver GeoDataFrame
```python
# Columns after generation:
receivers_gdf.columns
# Index(['tx_id', 'rx_id', 'distance_km', 'azimuth_deg', 'geometry'])

# Columns after extraction:
enriched_gdf.columns
# Index(['tx_id', 'rx_id', 'distance_km', 'azimuth_deg', 'geometry',
#        'h', 'ct', 'Ct', 'R', 'zone'])
```

### Output Profile Format
```python
# Each row represents one azimuth profile
df_profiles.columns
# ['f', 'p', 'd', 'h', 'R', 'Ct', 'zone', 'htg', 'hrg', 'pol',
#  'phi_t', 'phi_r', 'lam_t', 'lam_r', 'azimuth']

# Example: access first profile
profile = df_profiles.iloc[0]
distances = profile['d']  # list of distances
heights = profile['h']    # list of heights
resistance = profile['R'] # list of resistance values
```
