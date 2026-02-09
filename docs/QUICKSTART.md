# Quick Start Guide

## Installation

```bash
# Clone repository
cd /Users/oz/Documents/gmst_py1812

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ./github_Py1812/Py1812
```

## Running the Pipeline

### Full Pipeline (Recommended)
```bash
python scripts/run_full_pipeline.py --config config.json
```

### Individual Phases
```bash
# Phase 0: Setup
python scripts/run_phase0_setup.py

# Phase 1: Data Preparation
python scripts/run_phase1_dataprep.py --config config.json

# Custom project root
python scripts/run_full_pipeline.py --config config.json --project-root /path/to/project
```

## Configuration

Edit `config_sentinel_hub.py` with your Sentinel Hub credentials:
```python
SH_CLIENT_ID = "your_client_id"
SH_CLIENT_SECRET = "your_client_secret"
```

## Output

- **CSV Profiles:** `data/input/profiles/paths_oneTx_manyRx_*.csv`
- **GeoJSON Results:** `data/output/geojson/*.geojson`

## Next Steps

1. Read `PIPELINE.md` for detailed usage
2. Check `FINAL_STRUCTURE.md` for directory layout
3. See `WEEK3_SUMMARY.md` for project overview

## Help

```bash
python scripts/run_full_pipeline.py --help
python scripts/run_phase0_setup.py --help
python scripts/run_phase1_dataprep.py --help
```
