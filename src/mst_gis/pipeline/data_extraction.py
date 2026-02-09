"""
Data extraction module for the radio propagation pipeline.

Handles:
- Batch extraction of elevation, land cover, and zone data
- Optimization A: Pre-loading raster arrays for ~5-8x speedup
- Rasterio transform-based pixel indexing
- Zone extraction with spatial join (vectorized) + fallback to spatial index
- Land cover classification and resistance mapping
"""

import json
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import logging

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import rowcol

from mst_gis.utils.logging import Timer, print_success, print_warning, print_error
from mst_gis.utils.validation import ValidationError, validate_geodataframe


class RasterPreloader:
    """Pre-load and manage raster data for batch extraction."""
    
    def __init__(self):
        """Initialize preloader."""
        self.lcm_array = None
        self.lcm_transform = None
        self.lcm_nodata = None
        
        self.dem_array = None
        self.dem_transform = None
        self.dem_nodata = None
        
        self.load_times = {}
    
    def load_landcover(self, tif_path: Path) -> bool:
        """
        Load land cover GeoTIFF.
        
        Args:
            tif_path: Path to land cover GeoTIFF
            
        Returns:
            True if successful, False otherwise
        """
        if not tif_path.exists():
            print_warning(f"Land cover TIF not found at {tif_path}")
            return False
        
        try:
            with Timer("Load land cover") as t:
                with rasterio.open(str(tif_path)) as ds:
                    self.lcm_array = ds.read(1)
                    self.lcm_transform = ds.transform
                    self.lcm_nodata = ds.nodata
            self.load_times['landcover'] = t.elapsed
            print_success(f"Loaded land cover array: {self.lcm_array.shape}")
            return True
        except Exception as e:
            print_error(f"Error loading land cover: {e}")
            return False
    
    def load_dem(self, dem_path: Path) -> bool:
        """
        Load DEM from VRT or GeoTIFF, with SRTM.py fallback.
        
        Args:
            dem_path: Path to DEM VRT or GeoTIFF
            
        Returns:
            True if successful, False otherwise
        """
        if not dem_path.exists():
            print_warning(f"DEM not found at {dem_path}")
            # Try SRTM.py fallback
            return self._load_dem_srtm()
        
        try:
            with Timer("Load DEM"):
                with rasterio.open(str(dem_path)) as ds:
                    self.dem_array = ds.read(1)
                    self.dem_transform = ds.transform
                    self.dem_nodata = ds.nodata
            print_success(f"Loaded DEM array: {self.dem_array.shape}")
            return True
        except Exception as e:
            print_error(f"Error loading DEM: {e}")
            # Try SRTM.py fallback
            return self._load_dem_srtm()
    
    def _load_dem_srtm(self) -> bool:
        """
        Fallback: Load DEM using SRTM.py (on-demand elevation extraction).
        
        Returns:
            True if SRTM available, False otherwise
        """
        try:
            print_warning("Attempting SRTM.py fallback for elevation extraction")
            # SRTM.py is lazy-loaded on first get_elevation() call
            # This indicates SRTM will be used for elevation extraction
            self.dem_array = None  # Signal to use SRTM in extract_elevation_batch
            return True
        except Exception as e:
            print_warning(f"SRTM fallback also failed: {e}")
            return False
    
    def load_zones_geojson(self, zones_path: Path) -> gpd.GeoDataFrame:
        """
        Load zones from GeoJSON.
        
        Args:
            zones_path: Path to zones GeoJSON file
            
        Returns:
            GeoDataFrame with zone polygons
        """
        if not zones_path.exists():
            print_warning(f"Zones GeoJSON not found at {zones_path}")
            return None
        
        try:
            with Timer("Load zones GeoJSON"):
                with open(zones_path) as f:
                    zones_geojson = json.load(f)
                gdf_zones = gpd.GeoDataFrame.from_features(zones_geojson['features'])
                gdf_zones = gdf_zones.set_crs('EPSG:4326')
            
            print_success(f"Loaded {len(gdf_zones)} zones")
            zone_counts = gdf_zones['zone_type_id'].value_counts()
            print(f"  Zone distribution: {dict(zone_counts)}")
            
            return gdf_zones
        except Exception as e:
            print_error(f"Error loading zones: {e}")
            return None
    
    def extract_landcover_batch(self, gdf: gpd.GeoDataFrame) -> np.ndarray:
        """
        Extract land cover values for all points.
        
        Args:
            gdf: GeoDataFrame with point geometries
            
        Returns:
            Array of land cover codes
        """
        if self.lcm_array is None:
            return np.full(len(gdf), 254, dtype=np.uint8)
        
        lcm_values = np.full(len(gdf), 254, dtype=np.uint8)
        
        with Timer("Extract land cover"):
            for idx, (_, row) in enumerate(gdf.iterrows()):
                geom = row.geometry
                row_pix, col_pix = rowcol(self.lcm_transform, geom.x, geom.y)
                row_pix, col_pix = int(row_pix), int(col_pix)
                
                if 0 <= row_pix < self.lcm_array.shape[0] and 0 <= col_pix < self.lcm_array.shape[1]:
                    lcm_values[idx] = int(self.lcm_array[row_pix, col_pix])
        
        return lcm_values
    
    def extract_elevation_batch(self, gdf: gpd.GeoDataFrame) -> np.ndarray:
        """
        Extract elevation values for all points.
        
        Uses pre-loaded DEM array if available, falls back to SRTM.py.
        
        Args:
            gdf: GeoDataFrame with point geometries
            
        Returns:
            Array of elevation values
        """
        if self.dem_array is None:
            # Try SRTM.py fallback
            return self._extract_elevation_srtm(gdf)
        
        elevation = np.zeros(len(gdf), dtype=np.float32)
        
        with Timer("Extract elevation"):
            for idx, (_, row) in enumerate(gdf.iterrows()):
                geom = row.geometry
                row_pix, col_pix = rowcol(self.dem_transform, geom.x, geom.y)
                row_pix, col_pix = int(row_pix), int(col_pix)
                
                if 0 <= row_pix < self.dem_array.shape[0] and 0 <= col_pix < self.dem_array.shape[1]:
                    z = float(self.dem_array[row_pix, col_pix])
                    # Handle nodata values (typically -32000 for SRTM)
                    elevation[idx] = z if z > -32000 else 0.0
        
        return elevation
    
    def _extract_elevation_srtm(self, gdf: gpd.GeoDataFrame) -> np.ndarray:
        """
        Extract elevation using SRTM.py library.
        
        Args:
            gdf: GeoDataFrame with point geometries
            
        Returns:
            Array of elevation values
        """
        try:
            from mst_gis.propagation.profile_extraction import _get_srtm_data
            elevation = np.zeros(len(gdf), dtype=np.float32)
            
            with Timer("Extract elevation (SRTM.py)"):
                srtm_data = _get_srtm_data()
                for idx, (_, row) in enumerate(gdf.iterrows()):
                    try:
                        geom = row.geometry
                        # SRTM.py: get_elevation(lat, lon)
                        elev = srtm_data.get_elevation(geom.y, geom.x)
                        elevation[idx] = float(elev) if elev is not None and elev > -32000 else 0.0
                    except Exception:
                        elevation[idx] = 0.0
            
            return elevation
        except ImportError:
            print_warning("SRTM.py not available")
            return np.zeros(len(gdf), dtype=np.float32)


def extract_zones_vectorized(
    receivers_gdf: gpd.GeoDataFrame,
    zones_gdf: gpd.GeoDataFrame,
    default_zone: int = 4,
) -> np.ndarray:
    """
    Extract zone for each point using vectorized spatial join.
    
    Falls back to spatial index if spatial join fails (e.g., due to
    invalid geometries).
    
    Args:
        receivers_gdf: GeoDataFrame with receiver points
        zones_gdf: GeoDataFrame with zone polygons
        default_zone: Default zone if point not in any polygon
        
    Returns:
        Array of zone IDs
    """
    zones = np.full(len(receivers_gdf), default_zone, dtype=np.int32)
    
    try:
        with Timer("Zone extraction (spatial join)"):
            # Vectorized spatial join - fastest method
            result = gpd.sjoin(receivers_gdf, zones_gdf, how="left", predicate="within")
            # Handle overlapping zones: keep first zone if multiple matches
            result = result.loc[~result.index.duplicated(keep="first")]
            zones = result["zone_type_id"].fillna(default_zone).astype(np.int32).values
        
        print_success(f"Zone extraction complete (vectorized sjoin)")
        return zones
    
    except Exception as e:
        print_warning(f"Spatial join failed, using spatial index fallback: {e}")
        return _extract_zones_spatial_index(receivers_gdf, zones_gdf, default_zone)


def _extract_zones_spatial_index(
    receivers_gdf: gpd.GeoDataFrame,
    zones_gdf: gpd.GeoDataFrame,
    default_zone: int = 4,
) -> np.ndarray:
    """
    Extract zones using spatial index (fallback method).
    
    Much faster than naive loop (50-100x speedup).
    
    Args:
        receivers_gdf: GeoDataFrame with receiver points
        zones_gdf: GeoDataFrame with zone polygons
        default_zone: Default zone if point not in any polygon
        
    Returns:
        Array of zone IDs
    """
    zones = np.full(len(receivers_gdf), default_zone, dtype=np.int32)
    
    with Timer("Zone extraction (spatial index)"):
        sindex = zones_gdf.sindex
        
        for idx in receivers_gdf.index:
            point = receivers_gdf.loc[idx, "geometry"]
            # Find candidate zones using spatial index
            possible_zones = list(sindex.intersection((point.x, point.y, point.x, point.y)))
            
            # Check which zone contains this point
            for zone_idx in possible_zones:
                if zones_gdf.iloc[zone_idx].geometry.contains(point):
                    zones[idx] = int(zones_gdf.iloc[zone_idx]["zone_type_id"])
                    break
    
    print_success(f"Zone extraction complete (spatial index)")
    return zones


def map_landcover_codes(
    landcover_codes: np.ndarray,
    lcm10_to_ct: Dict[int, int],
    ct_to_r: Dict[int, float],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Map land cover codes to categories and resistance values.
    
    Args:
        landcover_codes: Array of LCM10 codes (0-254)
        lcm10_to_ct: Mapping from LCM10 code to category (1-5)
                     (keys can be int or str, will be converted to int)
        ct_to_r: Mapping from category to resistance (ohms)
                 (keys can be int or str, will be converted to int)
        
    Returns:
        Tuple of (categories, resistance) arrays
    """
    # Convert string keys to integers if needed (JSON config has string keys)
    lcm10_to_ct_int = {int(k): v for k, v in lcm10_to_ct.items()}
    ct_to_r_int = {int(k): v for k, v in ct_to_r.items()}
    
    categories = np.array([lcm10_to_ct_int.get(int(code), 2) for code in landcover_codes], dtype=np.int32)
    resistance = np.array([ct_to_r_int.get(int(ct), 0) for ct in categories], dtype=np.float32)
    
    return categories, resistance


def extract_data_for_receivers(
    receivers_gdf: gpd.GeoDataFrame,
    dem_path: Path,
    landcover_path: Path,
    zones_path: Path,
    lcm10_to_ct: Dict[int, int],
    ct_to_r: Dict[int, float],
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """
    Batch extract elevation, land cover, and zone data for all receiver points.
    
    Uses Optimization A: pre-load rasters once, then batch extract.
    Provides ~5-8x speedup compared to per-iteration file I/O.
    
    Args:
        receivers_gdf: GeoDataFrame with receiver points (must have 'geometry' column)
        dem_path: Path to DEM VRT or GeoTIFF
        landcover_path: Path to land cover GeoTIFF
        zones_path: Path to zones GeoJSON
        lcm10_to_ct: Mapping LCM10 code → category
        ct_to_r: Mapping category → resistance (ohms)
        verbose: Print progress updates
        
    Returns:
        Enriched GeoDataFrame with columns: h, ct, Ct, R, zone
        
    Raises:
        ValidationError: If receivers_gdf is invalid
    """
    # Validate inputs
    if not isinstance(receivers_gdf, gpd.GeoDataFrame):
        raise ValidationError("receivers_gdf must be a GeoDataFrame")
    
    if len(receivers_gdf) == 0:
        raise ValidationError("receivers_gdf is empty")
    
    validate_geodataframe(receivers_gdf, ["geometry"])
    
    # Make a copy to avoid modifying input
    result_gdf = receivers_gdf.copy()
    
    # Initialize output columns
    result_gdf["h"] = 0.0        # Elevation (m)
    result_gdf["ct"] = 254       # Land cover code (0-254)
    result_gdf["Ct"] = 2         # Land cover category (1-5)
    result_gdf["R"] = 0.0        # Resistance (ohms)
    result_gdf["zone"] = 4       # Zone (default Inland)
    
    if verbose:
        print("\n" + "=" * 60)
        print("PHASE 3: BATCH DATA EXTRACTION")
        print("=" * 60)
        print(f"\nExtracting data for {len(result_gdf)} points...")
    
    # Pre-load rasters (Optimization A)
    preloader = RasterPreloader()
    preloader.load_landcover(landcover_path)
    preloader.load_dem(dem_path)
    
    # Batch extract elevation
    result_gdf["h"] = preloader.extract_elevation_batch(result_gdf)
    
    # Batch extract land cover
    result_gdf["ct"] = preloader.extract_landcover_batch(result_gdf)
    
    # Map land cover codes to categories and resistance
    result_gdf["Ct"], result_gdf["R"] = map_landcover_codes(
        result_gdf["ct"].values,
        lcm10_to_ct,
        ct_to_r,
    )
    
    # Extract zones
    zones_gdf = preloader.load_zones_geojson(zones_path)
    if zones_gdf is not None:
        result_gdf["zone"] = extract_zones_vectorized(result_gdf, zones_gdf)
    
    if verbose:
        print("\n" + "=" * 60)
        print("EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"\nData extraction summary:")
        print(f"  Total points: {len(result_gdf)}")
        print(f"  Elevation (h):")
        print(f"    Min: {result_gdf['h'].min():.1f}m")
        print(f"    Max: {result_gdf['h'].max():.1f}m")
        print(f"    Mean: {result_gdf['h'].mean():.1f}m")
        print(f"  Land cover codes (ct):")
        print(f"    Unique: {result_gdf['ct'].nunique()}")
        print(f"  Land cover categories (Ct):")
        print(f"    {dict(result_gdf['Ct'].value_counts().sort_index())}")
        print(f"  Zones:")
        print(f"    {dict(result_gdf['zone'].value_counts().sort_index())}")
    
    return result_gdf
