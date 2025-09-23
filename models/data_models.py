"""
Data Models - Updated
Date: 2025-08-28 02:35:26 UTC
User: HarrisonKuo47
"""

import numpy as np
from typing import Dict, List, Any
from dataclasses import dataclass

# Global storage - imported by routes
analysis_results = {}
handler_kit_metadata_cache = {}

@dataclass
class BoundaryData:
    """Boundary data for lead frame analysis"""
    mid_x: float
    mid_y: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    
    @property
    def width(self) -> float:
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        return self.y_max - self.y_min

@dataclass
class AnalysisRequest:
    """Analysis request parameters"""
    dxf_filename: str
    pkg_type: str = "ALL"
    lf_type: str = "ALL"
    early_termination: bool = False
    selected_layers: str = ""

def convert_numpy_types(obj):
    """Convert NumPy types to Python native types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj