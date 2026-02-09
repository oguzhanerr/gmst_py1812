"""Terrain profile parsing from CSV files."""

import ast
import csv
from pathlib import Path
import numpy as np


def load_profiles(profiles_dir, return_path=False):
    """Load all CSV profile files from a directory.
    
    Parameters:
    -----------
    profiles_dir : Path or str
        Directory containing profile CSV files
    return_path : bool, optional
        If True, return tuple (profiles, path_to_csv)
        If False, return just profiles list
        
    Returns:
    --------
    list or tuple
        If return_path=False: list of parsed profile rows
        If return_path=True: (list of profiles, Path to CSV file)
    """
    folder = Path(profiles_dir)
    profiles = []
    csv_path = None
    
    # Load only the most recent CSV file (or all if return_path=False for backward compatibility)
    csv_files = sorted(folder.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if csv_files:
        # Always use the most recent file
        latest_file = csv_files[0]
        with latest_file.open(newline="", encoding="utf-8") as f:
            profiles = list(csv.reader(f, delimiter=";"))[1:]
        csv_path = latest_file
    
    if return_path:
        return profiles, csv_path
    return profiles


def process_loss_parameters(profile, tx_id_default=None):
    """Process and convert profile row to P1812 function parameters.
    
    Parameters:
    -----------
    profile : list
        Raw profile row from CSV:
        Columns 0-14: f, p, d, h, R, Ct, zone, htg, hrg, pol, phi_t, phi_r, lam_t, lam_r, azimuth (P1812 input)
        Column 15: distance_ring (metadata for output)
        Column 16: tx_id (optional metadata, not used by P1812)
    tx_id_default : str, optional
        Default TX ID to use if not found in CSV column 16.
        
    Returns:
    --------
    tuple
        (parameters_list, tx_id) where parameters_list is ready for P1812.bt_loss()
        and tx_id tracks which transmitter generated this profile
    """
    parameters = [ast.literal_eval(parameter) for parameter in profile[0:15]]
    
    # Extract tx_id from column 16 (0-indexed) if present
    tx_id = tx_id_default
    if len(profile) > 16:
        try:
            tx_id_value = profile[16].strip() if isinstance(profile[16], str) else str(profile[16])
            if tx_id_value and tx_id_value != 'None':
                tx_id = tx_id_value
        except (IndexError, ValueError, AttributeError):
            pass
    
    params_list = [
        float(parameters[0]),   # f (frequency)
        float(parameters[1]),   # p (time percentage)
        np.array([float(value) for value in parameters[2]]),  # d (distances)
        np.array([float(value) for value in parameters[3]]),  # h (heights)
        np.array([float(value) for value in parameters[4]]),  # R (clutter)
        np.array([int(value) for value in parameters[5]]),    # Ct (clutter type)
        np.array([int(value) for value in parameters[6]]),    # zone
        float(parameters[7]),   # htg (TX height)
        float(parameters[8]),   # hrg (RX height)
        int(parameters[9]),     # pol (polarization)
        float(parameters[10]),  # phi_t (TX latitude)
        float(parameters[11]),  # phi_r (RX latitude)
        float(parameters[12]),  # lam_t (TX longitude)
        float(parameters[13]),  # lam_r (RX longitude)
    ]
    
    return params_list, tx_id
