"""
Visualization utilities for pipeline results.

Provides functions to create interactive maps and charts using Plotly and deck.gl.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np


def create_loss_distribution_chart(results_df: pd.DataFrame):
    """
    Create histogram of Lb (Basic Transmission Loss) distribution.
    
    Args:
        results_df: DataFrame with results including 'Lb' column
        
    Returns:
        Plotly Figure object
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("Warning: plotly not installed. Run: pip install plotly")
        return None
    
    fig = go.Figure()
    
    # Filter out NaN values
    lb_values = results_df['Lb'].dropna()
    
    fig.add_trace(go.Histogram(
        x=lb_values,
        nbinsx=50,
        name='Lb Distribution',
        marker_color='rgba(0, 100, 200, 0.7)',
    ))
    
    fig.update_layout(
        title='Distribution of Basic Transmission Loss (Lb)',
        xaxis_title='Lb (dB)',
        yaxis_title='Count',
        hovermode='x unified',
        template='plotly_white',
        height=500,
    )
    
    return fig


def create_field_strength_chart(results_df: pd.DataFrame):
    """
    Create histogram of Ep (Electric Field Strength) distribution.
    
    Args:
        results_df: DataFrame with results including 'Ep' column
        
    Returns:
        Plotly Figure object
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("Warning: plotly not installed. Run: pip install plotly")
        return None
    
    fig = go.Figure()
    
    # Filter out NaN values
    ep_values = results_df['Ep'].dropna()
    
    fig.add_trace(go.Histogram(
        x=ep_values,
        nbinsx=50,
        name='Ep Distribution',
        marker_color='rgba(200, 100, 0, 0.7)',
    ))
    
    fig.update_layout(
        title='Distribution of Electric Field Strength (Ep)',
        xaxis_title='Ep (dBμV/m)',
        yaxis_title='Count',
        hovermode='x unified',
        template='plotly_white',
        height=500,
    )
    
    return fig


def create_loss_vs_distance_scatter(results_df: pd.DataFrame):
    """
    Create scatter plot of Lb vs distance.
    
    Args:
        results_df: DataFrame with results including 'Lb' and 'distance_km' columns
        
    Returns:
        Plotly Figure object
    """
    try:
        import plotly.express as px
    except ImportError:
        print("Warning: plotly not installed. Run: pip install plotly")
        return None
    
    # Filter out NaN values
    df_clean = results_df[['distance_km', 'Lb', 'azimuth']].dropna()
    
    fig = px.scatter(
        df_clean,
        x='distance_km',
        y='Lb',
        color='azimuth',
        title='Basic Transmission Loss vs Distance',
        labels={
            'distance_km': 'Distance (km)',
            'Lb': 'Lb (dB)',
            'azimuth': 'Azimuth (°)'
        },
        hover_data=['distance_km', 'Lb', 'azimuth'],
        color_continuous_scale='Viridis',
    )
    
    fig.update_layout(
        height=600,
        template='plotly_white',
        hovermode='closest',
    )
    
    return fig


def create_azimuth_heatmap(results_df: pd.DataFrame):
    """
    Create heatmap of Lb by azimuth and distance.
    
    Args:
        results_df: DataFrame with results including 'azimuth', 'distance_km', 'Lb' columns
        
    Returns:
        Plotly Figure object
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("Warning: plotly not installed. Run: pip install plotly")
        return None
    
    # Create pivot table
    df_clean = results_df[['azimuth', 'distance_km', 'Lb']].dropna()
    pivot_data = df_clean.pivot_table(
        index='azimuth',
        columns='distance_km',
        values='Lb',
        aggfunc='mean'
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=pivot_data.index,
        colorscale='RdYlBu_r',
    ))
    
    fig.update_layout(
        title='Basic Transmission Loss Heatmap (Azimuth vs Distance)',
        xaxis_title='Distance (km)',
        yaxis_title='Azimuth (°)',
        height=600,
        template='plotly_white',
    )
    
    return fig


def create_receiver_map(receivers_gdf, results_df: Optional[pd.DataFrame] = None, output_path: Optional[Path] = None):
    """
    Create interactive map of receiver points using pydeck (deck.gl).
    
    Args:
        receivers_gdf: GeoDataFrame with receiver locations
        results_df: Optional DataFrame with results to color points by Lb
        output_path: Optional path to save HTML map file
        
    Returns:
        tuple of (pydeck Deck object, path to HTML file) or (None, None) if pydeck not available
    """
    try:
        import pydeck as pdk
    except ImportError:
        print("Warning: pydeck not installed. Run: pip install pydeck")
        return None, None
    
    # Prepare data
    data = None
    
    # Add results if provided
    if results_df is not None and len(results_df) > 0:
        try:
            # Aggregate results by location (average Lb per point)
            results_agg = results_df.groupby(['rx_lon', 'rx_lat']).agg({
                'Lb': 'mean',
                'Ep': 'mean',
                'azimuth': 'first',
                'distance_km': 'first'
            }).reset_index()
            
            # Rename for pydeck
            results_agg['lon'] = results_agg['rx_lon']
            results_agg['lat'] = results_agg['rx_lat']
            
            data = results_agg[['lon', 'lat', 'Lb', 'Ep']].copy()
            color_col = 'Lb'
        except Exception as e:
            print(f"Note: Could not aggregate results - {str(e)[:50]}")
    
    # Fallback to receiver points if no results
    if data is None or len(data) == 0:
        receivers_gdf_copy = receivers_gdf.copy()
        data = pd.DataFrame({
            'lon': receivers_gdf_copy.geometry.x,
            'lat': receivers_gdf_copy.geometry.y,
            'Lb': [100] * len(receivers_gdf_copy)  # Default value
        })
        color_col = 'Lb'
    
    # Normalize color values for visualization
    if len(data) > 0 and color_col in data.columns:
        min_val = data[color_col].min()
        max_val = data[color_col].max()
        if max_val > min_val:
            data['color_r'] = ((data[color_col] - min_val) / (max_val - min_val) * 255).astype(int)
        else:
            data['color_r'] = 128
    else:
        data['color_r'] = 128
    
    data['color_g'] = 100
    data['color_b'] = 150
    data['color_a'] = 200
    
    # Calculate center point
    center_lat = data['lat'].mean()
    center_lon = data['lon'].mean()
    
    # Create layer with proper color array
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=data,
        get_position='[lon, lat]',
        get_fill_color='[color_r, color_g, color_b, color_a]',
        get_radius=500,
        pickable=True,
        auto_highlight=True,
    )
    
    # Create deck with tooltip
    tooltip = {
        "html": "<b>Location</b><br/>Lat: {lat:.4f}<br/>Lon: {lon:.4f}<br/>Lb: {Lb:.2f} dB",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }
    
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=8,
            pitch=0,
        ),
        tooltip=tooltip,
    )
    
    # Save HTML if output path provided
    html_path = None
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html_path = output_path
        deck.to_html(str(html_path))
        print(f"   Map saved to: {html_path}")
    
    return deck, html_path


def create_statistics_summary(results_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Create summary statistics from results.
    
    Args:
        results_df: DataFrame with results
        
    Returns:
        Dictionary with summary statistics
    """
    lb_values = results_df['Lb'].dropna()
    ep_values = results_df['Ep'].dropna()
    
    summary = {
        'total_profiles': len(results_df),
        'successful_profiles': len(lb_values),
        'failed_profiles': len(results_df) - len(lb_values),
        'lb_mean': float(lb_values.mean()) if len(lb_values) > 0 else None,
        'lb_median': float(lb_values.median()) if len(lb_values) > 0 else None,
        'lb_std': float(lb_values.std()) if len(lb_values) > 0 else None,
        'lb_min': float(lb_values.min()) if len(lb_values) > 0 else None,
        'lb_max': float(lb_values.max()) if len(lb_values) > 0 else None,
        'ep_mean': float(ep_values.mean()) if len(ep_values) > 0 else None,
        'ep_median': float(ep_values.median()) if len(ep_values) > 0 else None,
        'ep_std': float(ep_values.std()) if len(ep_values) > 0 else None,
        'ep_min': float(ep_values.min()) if len(ep_values) > 0 else None,
        'ep_max': float(ep_values.max()) if len(ep_values) > 0 else None,
    }
    
    return summary


def print_summary(summary: Dict[str, Any]):
    """Print summary statistics in a formatted table."""
    print("\n" + "="*70)
    print("RESULTS SUMMARY STATISTICS")
    print("="*70)
    print(f"\nProfile Statistics:")
    print(f"  Total profiles: {summary['total_profiles']}")
    print(f"  Successful: {summary['successful_profiles']}")
    print(f"  Failed: {summary['failed_profiles']}")
    
    if summary['lb_mean'] is not None:
        print(f"\nBasic Transmission Loss (Lb) Statistics (dB):")
        print(f"  Mean: {summary['lb_mean']:.2f}")
        print(f"  Median: {summary['lb_median']:.2f}")
        print(f"  Std Dev: {summary['lb_std']:.2f}")
        print(f"  Min: {summary['lb_min']:.2f}")
        print(f"  Max: {summary['lb_max']:.2f}")
    
    if summary['ep_mean'] is not None:
        print(f"\nElectric Field Strength (Ep) Statistics (dBμV/m):")
        print(f"  Mean: {summary['ep_mean']:.2f}")
        print(f"  Median: {summary['ep_median']:.2f}")
        print(f"  Std Dev: {summary['ep_std']:.2f}")
        print(f"  Min: {summary['ep_min']:.2f}")
        print(f"  Max: {summary['ep_max']:.2f}")
    
    print("\n" + "="*70)
