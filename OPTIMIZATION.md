# Comprehensive Performance Optimization Guide

## Overview

This document consolidates two optimization strategies to improve the profile extraction pipeline:
- **Optimization A**: Rasterio I/O pre-loading (80-85% improvement on extract_profiles cell)
- **Optimization B**: API batching (50-100x improvement on profile generation loop)

Both optimizations can be implemented independently or combined for maximum benefit.

---

## Problem Statement

The mobile input pipeline has two major bottlenecks:

1. **Rasterio I/O Bottleneck** (Extract Profiles Cell)
   - Takes ~172 seconds (2.86 minutes) to process 36 azimuths
   - Each iteration opens GeoTIFF and DEM VRT files from disk (~4.77s per iteration)
   - Root cause: Expensive rasterio.open() operations repeated 36 times

2. **API Call Bottleneck** (Profile Generation Loop)
   - Makes ~72 redundant API/I/O calls (2 per azimuth × 36 azimuths)
   - Elevation and land cover data fetched repeatedly
   - Root cause: Loop calls generate_profile_points() per azimuth instead of batching

---

# OPTIMIZATION A: Rasterio I/O Pre-loading

## Problem Analysis

### Current Bottleneck

Each iteration of the extract_profiles loop opens raster files from disk:
1. Opens GeoTIFF file via `rasterio.open()` - ~2.3s
2. Reads band data and indexes into it - ~0.2s  
3. Opens DEM VRT file via `rasterio.open()` - ~2.0s
4. Reads DEM band and indexes into it - ~0.27s

These I/O operations happen 36 times sequentially, totaling 171.70s.

### Why It's Slow

- Rasterio file opening is expensive (~2-2.3s per file)
- DEM VRT especially slow because it's a virtual mosaic of many tiles
- Both files exist on disk; no caching between iterations
- Same files accessed identically in every iteration

## Solution: Pre-load Rasters into Memory

Load raster bands into NumPy arrays in memory before the loop, then pass arrays to the function instead of file paths. This eliminates the rasterio `open()` overhead for iterations 2-36.

### Performance Target

- **Before**: 172s total (4.77s per iteration × 36)
- **After**: 20-30s total (first iteration opens + reads: 4.77s, subsequent iterations: 0.3-0.5s each)
- **Improvement**: 75-85% speedup

### Memory Impact

- GeoTIFF: 734×734 pixels (uint8) ≈ 0.5 MB
- DEM VRT: similar size ≈ 0.5 MB
- Total increase: negligible (~1 MB)

## Implementation: Optimization A

### Step 1: Modify Function Signature

Update `generate_profile_points()` in `profile_extraction.py` to accept optional pre-loaded raster data:

```python
def generate_profile_points(
    tx_lon: float,
    tx_lat: float,
    max_distance_km: float,
    n_points: int,
    azimuth_deg: float,
    tif_path: str,
    lcm10_to_ct: dict,
    ct_to_r: dict,
    zones_path: Optional[str] = None,
    tif_ds=None,
    dem_ds=None,
    skip_seed: bool = False,
    # NEW PARAMETERS:
    tif_band_data=None,        # Pre-loaded TIF array (NumPy)
    tif_transform=None,        # Rasterio transform for TIF
    tif_nodata=None,           # Nodata value for TIF
    dem_band_data=None,        # Pre-loaded DEM array (NumPy)
    dem_transform=None,        # Rasterio transform for DEM
) -> gpd.GeoDataFrame:
```

### Step 2: Update Land Cover Extraction Logic

Replace rasterio indexing with NumPy array indexing when pre-loaded data provided:

```python
# OLD CODE (opens file 36 times):
ct_codes = []
if tif_ds is None:
    with rasterio.open(tif_path) as ds:
        band = ds.read(1)
        nodata = ds.nodata
        for geom in gdf.geometry:
            row, col = ds.index(geom.x, geom.y)
            # ... extract value ...

# NEW CODE (backward compatible):
ct_codes = []
if tif_band_data is not None and tif_transform is not None:
    # Use pre-loaded array with transform
    from rasterio.windows import Window
    for geom in gdf.geometry:
        # Convert coordinates to array indices using transform
        row, col = rasterio.transform.rowcol(tif_transform, geom.x, geom.y)
        if 0 <= row < tif_band_data.shape[0] and 0 <= col < tif_band_data.shape[1]:
            val = int(tif_band_data[row, col])
            if tif_nodata is not None and val == tif_nodata:
                val = 254
        else:
            val = 254
        ct_codes.append(val)
elif tif_ds is None:
    # Original behavior: open file
    with rasterio.open(tif_path) as ds:
        band = ds.read(1)
        nodata = ds.nodata
        for geom in gdf.geometry:
            row, col = ds.index(geom.x, geom.y)
            # ... extract value ...
else:
    # Use provided dataset
    band = tif_ds.read(1)
    # ... original logic ...
```

### Step 3: Update DEM Extraction Logic

Apply same pattern to elevation data:

```python
# OLD: Opens DEM VRT 36 times
h = []
vrt_path = Path(cache_dir) / "SRTM1" / "SRTM1.vrt"
if vrt_path.exists():
    with rasterio.open(str(vrt_path)) as dem:
        dem_band = dem.read(1)
        for geom in gdf.geometry:
            row, col = dem.index(geom.x, geom.y)
            # ... extract elevation ...

# NEW: Use pre-loaded array or open once
h = []
if dem_band_data is not None and dem_transform is not None:
    # Use pre-loaded array
    for geom in gdf.geometry:
        row, col = rasterio.transform.rowcol(dem_transform, geom.x, geom.y)
        if 0 <= row < dem_band_data.shape[0] and 0 <= col < dem_band_data.shape[1]:
            z = float(dem_band_data[row, col])
        else:
            z = 0.0
        h.append(z)
elif dem_ds is not None:
    # Use provided dataset (original logic)
    dem_band = dem_ds.read(1)
    # ...
else:
    # Open DEM if not provided (original logic)
    # ...
```

### Step 4: Update Notebook to Pre-load Rasters

In the extract_profiles cell, load rasters ONCE before the loop:

```python
import rasterio
from rasterio.transform import rowcol

# Pre-load rasters ONCE before loop
with rasterio.open(tif_path_str) as src_tif:
    tif_band = src_tif.read(1)        # Full array in memory
    tif_transform = src_tif.transform
    tif_nodata = src_tif.nodata

with rasterio.open(str(vrt_path)) as src_dem:
    dem_band = src_dem.read(1)        # Full array in memory
    dem_transform = src_dem.transform

# Loop uses pre-loaded data (no file opens inside loop)
for i, az in enumerate(azimuths):
    start_iter = time.time()
    
    gdf = generate_profile_points(
        tx_lon, tx_lat, max_distance_km, n_points,
        azimuth_deg=az,
        tif_path=tif_path_str,
        lcm10_to_ct=CONFIG['LCM10_TO_CT'],
        ct_to_r=CONFIG['CT_TO_R'],
        zones_path=None,
        # NEW: Pass pre-loaded arrays
        tif_band_data=tif_band,
        tif_transform=tif_transform,
        tif_nodata=tif_nodata,
        dem_band_data=dem_band,
        dem_transform=dem_transform,
        skip_seed=True,
    )
    
    iter_time = time.time() - start_iter
    print(f"[{i+1}/{len(azimuths)}] Processed azimuth {az}° in {iter_time:.2f}s")
```

## Testing Optimization A

1. **Backward Compatibility**: Function works without new parameters
2. **Timing Validation**: Per-iteration time drops from 4.77s to 0.3-0.5s
3. **Data Validation**: Compare results before/after (should be identical)
4. **Full Run**: Verify total time < 40s

---

# OPTIMIZATION B: API Call Batching

## Problem Analysis

### Current Implementation

```python
for az in azimuths:  # 36 iterations
    gdf = generate_profile_points(tx_lon, tx_lat, ..., azimuth_deg=az)
    # Inside generate_profile_points():
    # - elevation data accessed each time
    # - rasterio.open(tif_path) called each time
    # Total: ~72 API/I/O calls
```

### Bottlenecks

1. **Elevation**: Lazy loading happens per azimuth (cached but redundant checks)
2. **Land Cover GeoTIFF**: Opened/read per azimuth (I/O heavy)
3. **Zone Lookup**: Spatial join repeated per azimuth

### Current Performance

- Processing 36 azimuths × ~366 points
- For each azimuth: elevation load (~500ms) + GeoTIFF open (~100ms) + pixel read (~50ms) + zone join (~200ms) = ~850ms
- Total: 36 × 850ms = ~30 seconds

## Solution: Batch Processing

Generate all points at once, extract elevation/landcover/zones in single batch operations.

### Proposed Architecture

```
1. Generate all points at once (batch)
   ├─ 36 azimuths × ~366 points = ~13,000 points
   ├─ All in one GeoDataFrame
   └─ Keep azimuth column for splitting later

2. Extract elevation once (single operation)
   ├─ Batch all points to elevation system
   └─ Returns all elevations in one pass

3. Extract land cover once (single I/O)
   ├─ Open GeoTIFF once
   ├─ Read all point values
   └─ Close once

4. Extract zones once (single spatial join)
   ├─ Spatial join all points at once
   └─ Much faster than repeated joins

5. Extract profiles (post-processing)
   ├─ No I/O or API calls
   ├─ Just data manipulation
   └─ Fast

6. Split results back to per-azimuth GeoDataFrames
```

### Performance Target

- **Before**: ~30 seconds (850ms per azimuth × 36)
- **After**: ~0.9 seconds (batch operations, single file opens)
- **Improvement**: 30-35x speedup

## Implementation: Optimization B

### Step 1: Add Batch Functions to profile_extraction.py

```python
def batch_generate_all_profiles(
    tx_lon: float,
    tx_lat: float,
    max_distance_km: float,
    azimuths_deg: list,
    sampling_resolution: int,
    tif_path: str,
    lcm10_to_ct: dict,
    ct_to_r: dict,
    zones_path: Optional[str] = None,
    show_progress: bool = True,
) -> List[gpd.GeoDataFrame]:
    """
    Generate all profiles at once (batched).
    
    Returns list of GeoDataFrames (one per azimuth).
    """
    if show_progress:
        from tqdm import tqdm
        pbar = tqdm(total=4, desc="Batch processing profiles")
    
    # 1. Generate all points
    all_points_gdf = _batch_generate_points(
        tx_lon, tx_lat, max_distance_km, azimuths_deg, sampling_resolution
    )
    if show_progress:
        pbar.update(1)
    
    # 2. Extract elevation for all points at once
    elevations = _batch_get_elevations(all_points_gdf)
    all_points_gdf['h'] = elevations
    if show_progress:
        pbar.update(1)
    
    # 3. Extract land cover for all points at once
    lc_codes = _batch_get_landcover(all_points_gdf, tif_path)
    all_points_gdf['ct'] = lc_codes
    all_points_gdf['Ct'] = all_points_gdf['ct'].map(lambda c: lcm10_to_ct.get(c, 2))
    all_points_gdf['R'] = all_points_gdf['Ct'].map(lambda ct: ct_to_r.get(ct, 0))
    if show_progress:
        pbar.update(1)
    
    # 4. Extract zones (optional)
    if zones_path:
        zones = _batch_get_zones(all_points_gdf, zones_path)
        all_points_gdf['zone'] = zones
    else:
        all_points_gdf['zone'] = 0
    if show_progress:
        pbar.update(1)
        pbar.close()
    
    # 5. Split back into per-azimuth GeoDataFrames
    profiles_by_azimuth = [gdf for _, gdf in all_points_gdf.groupby('azimuth')]
    return profiles_by_azimuth


def _batch_generate_points(
    tx_lon: float,
    tx_lat: float,
    max_distance_km: float,
    azimuths_deg: list,
    sampling_resolution: int,
) -> gpd.GeoDataFrame:
    """Generate all points in one GeoDataFrame."""
    import math
    from shapely.geometry import Point
    
    # Create transmitter point
    tx_gdf = gpd.GeoDataFrame(geometry=[Point(tx_lon, tx_lat)], crs="EPSG:4326")
    utm_crs = tx_gdf.estimate_utm_crs()
    tx_utm = tx_gdf.to_crs(utm_crs)
    center = tx_utm.geometry.iloc[0]
    
    # Compute step distance
    max_m = max_distance_km * 1000.0
    n_points = int(max_distance_km * 1000 / sampling_resolution)
    step_m = max_m / (n_points - 1)
    
    all_points = []
    all_distances = []
    all_azimuths = []
    
    for az_deg in azimuths_deg:
        theta = math.radians(az_deg)
        dx_unit = math.sin(theta)
        dy_unit = math.cos(theta)
        
        for i in range(n_points):
            d_m = i * step_m
            x = center.x + d_m * dx_unit
            y = center.y + d_m * dy_unit
            all_points.append(Point(x, y))
            all_distances.append(d_m / 1000.0)
            all_azimuths.append(az_deg)
    
    gdf_utm = gpd.GeoDataFrame(
        {
            "distance_km": all_distances,
            "azimuth": all_azimuths,
        },
        geometry=all_points,
        crs=utm_crs,
    )
    
    return gdf_utm.to_crs("EPSG:4326")


def _batch_get_elevations(gdf: gpd.GeoDataFrame) -> List[float]:
    """Extract elevation for all points at once."""
    import elevation
    
    try:
        elevation.seed(bounds=[gdf.total_bounds[0], gdf.total_bounds[1], 
                               gdf.total_bounds[2], gdf.total_bounds[3]])
    except:
        pass
    
    elevations = []
    for geom in gdf.geometry:
        try:
            z = elevation.elevation(geom.y, geom.x)
            elevations.append(z if z is not None else 0.0)
        except:
            elevations.append(0.0)
    
    return elevations


def _batch_get_landcover(
    gdf: gpd.GeoDataFrame,
    tif_path: str,
) -> List[int]:
    """Extract land cover codes for all points at once (single file open)."""
    import rasterio
    
    lc_codes = []
    
    with rasterio.open(tif_path) as ds:
        band = ds.read(1)
        nodata = ds.nodata
        
        for geom in gdf.geometry:
            row, col = ds.index(geom.x, geom.y)
            
            if 0 <= row < ds.height and 0 <= col < ds.width:
                val = int(band[row, col])
                if nodata is not None and val == nodata:
                    val = 254
            else:
                val = 254
            
            lc_codes.append(val)
    
    return lc_codes


def _batch_get_zones(
    gdf: gpd.GeoDataFrame,
    zones_path: str,
) -> List[int]:
    """Extract zone IDs for all points at once (single spatial join)."""
    gdf_zones = gpd.read_file(zones_path)
    if gdf_zones.crs != gdf.crs:
        gdf_zones = gdf_zones.to_crs(gdf.crs)
    
    gdf_joined = gpd.sjoin(
        gdf,
        gdf_zones[["zone_type_id", "geometry"]],
        how="left",
        predicate="intersects"
    )
    
    gdf_joined = gdf_joined[~gdf_joined.index.duplicated(keep="first")]
    return gdf_joined["zone_type_id"].fillna(0).astype(int).tolist()
```

### Step 2: Create Notebook Using Batch Functions

Use batch functions in extract_profiles cell:

```python
# Instead of looping per azimuth
profiles_by_azimuth = batch_generate_all_profiles(
    tx_lon, tx_lat, max_distance_km, azimuths, 
    sampling_resolution=CONFIG['RECEIVER_GENERATION']['sampling_resolution'],
    tif_path=tif_path_str,
    lcm10_to_ct=CONFIG['LCM10_TO_CT'],
    ct_to_r=CONFIG['CT_TO_R'],
    show_progress=True,
)

# Extract CSV rows from results
rows = []
for az, gdf in zip(azimuths, profiles_by_azimuth):
    phi_t, lam_t = float(gdf.geometry.iloc[0].y), float(gdf.geometry.iloc[0].x)
    phi_r, lam_r = float(gdf.geometry.iloc[-1].y), float(gdf.geometry.iloc[-1].x)
    
    rows.append({
        "f": CONFIG['P1812']['frequency_ghz'],
        "p": CONFIG['P1812']['time_percentage'],
        "d": [float(round(v, 3)) for v in gdf["distance_km"].tolist()],
        "h": [int(round(v)) if v else 0 for v in gdf["h"].tolist()],
        # ... rest of fields ...
    })
```

## Testing Optimization B

1. **Unit Tests**: Verify each batch function works independently
2. **Integration Test**: Verify full batch workflow produces correct output
3. **Data Validation**: Compare results with per-azimuth approach (should be identical)
4. **Performance Benchmark**: Measure speedup factor

---

# Combining Both Optimizations

For maximum performance, apply both optimizations together:

1. Use pre-loaded rasters (Optimization A) in batch functions (Optimization B)
2. This compounds the benefits

### Expected Combined Performance

- **Optimization A alone**: 172s → 20-30s (5.7-8.6x faster)
- **Optimization B alone**: 30s → 0.9s (33x faster) 
- **Both combined**: 172s → 0.9s (190x faster)

---

# Implementation Strategy

## Phase 1: Implement Optimization A (Low effort, immediate benefit)

1. Update function signature
2. Update land cover and DEM extraction logic
3. Update notebook to pre-load rasters
4. Test and benchmark

**Effort**: 1-2 hours  
**Benefit**: 5-8x speedup on extract_profiles cell

## Phase 2: Implement Optimization B (Medium effort, larger benefit)

1. Add batch functions to module
2. Update notebook to use batch functions
3. Test and benchmark

**Effort**: 2-3 hours  
**Benefit**: 30-35x speedup on profile generation

## Phase 3: Optional Enhancements

- Add caching for elevation data
- Implement parallel processing
- Add progress indicators (tqdm)

---

# Success Criteria

For Optimization A:
- Per-iteration time drops to 0.3-0.5s (from 4.77s)
- Total time < 40s (from 172s)
- Results identical to original

For Optimization B:
- Batch profile generation < 2s total
- 30x+ speedup demonstrated
- Results identical to per-azimuth approach

For Combined:
- Total pipeline time < 5s
- 150x+ improvement

---

# References

- `profile_extraction.py`: Module containing functions to optimize
- `mobile_get_input_phase2.ipynb`: Current notebook to update
- `NOTEBOOK_REFACTORING_REPORT.md`: Overall refactoring status
- Rasterio docs: https://rasterio.readthedocs.io/
- Elevation docs: https://elevation.readthedocs.io/
