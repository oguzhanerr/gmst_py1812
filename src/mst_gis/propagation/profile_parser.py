"""Terrain profile parsing from CSV files."""

import ast
import csv
from pathlib import Path
import numpy as np


def load_profiles(profiles_dir):
    """Load all CSV profile files from a directory.
    
    Parameters:
    -----------
    profiles_dir : Path or str
        Directory containing profile CSV files
        
    Returns:
    --------
    list
        List of parsed profile rows
    """
    folder = Path(profiles_dir)
    profiles = []
    for file in folder.glob("*.csv"):
        with file.open(newline="", encoding="utf-8") as f:
            profiles += list(csv.reader(f, delimiter=";"))[1:]
    
    return profiles


def process_loss_parameters(profile):
    """Process and convert profile row to P1812 function parameters.
    
    Parameters:
    -----------
    profile : list
        Raw profile row from CSV
        
    Returns:
    --------
    tuple
        (parameters_list, tx_id) where parameters_list is ready for P1812.bt_loss()
        and tx_id tracks which transmitter generated this profile
    """
    parameters = [ast.literal_eval(parameter) for parameter in profile[0:15]]
    
    # Extract tx_id if present (column 16 in CSV, index 15)
    tx_id = None
    if len(profile) > 15:
        try:
            tx_id = profile[15]
        except (IndexError, ValueError):
            tx_id = None
    
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
