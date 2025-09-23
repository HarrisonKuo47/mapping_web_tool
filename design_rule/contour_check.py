"""
Design Rule Checker - Fixed Missing Function
Date: 2025-09-04 01:59:39 UTC
User: HarrisonKuo47
"""

import os
import pandas as pd
import numpy as np
import json
from typing import List, Dict, Any, Optional
import logging

from datetime import datetime, timezone, timedelta
from .vacuum_scanner import run_vacuum_position_scan

# Configure logging
logger = logging.getLogger(__name__)

# Design rule configuration
DESIGN_RULES = {
    "length_width_rules": {
        "min_length": 76.2,     
        "max_length": 300,     
        "min_width": 25.6,      
        "max_width": 102      
    },
    "vacuum_position_rules": {
        "vacuum_diameter_mm": 3.6,
        "default_positions_per_side": 10,
        "scan_unit_mm": 0.1,
        "min_positions_per_side": 5,
        "max_positions_per_side": 20,
        "resolution_dpi": 300
    }
}

def get_current_time_utc8():
    """Get current time in UTC+8 format for server-side rendering"""
    utc8 = timezone(timedelta(hours=8))
    now_utc8 = datetime.now(utc8)
    return now_utc8.strftime("%Y-%m-%d %H:%M:%S")

def get_design_rules() -> Dict[str, Any]:
    """Get current design rules configuration"""
    logger.info(f"Design rules requested by HarrisonKuo47 at {get_current_time_utc8()}")
    return DESIGN_RULES

def find_dxf_file_for_leadframe(upload_dir: str, leadframe_folder: str) -> Optional[str]:
    leadframes_dir = os.path.join(upload_dir, "leadframes")
        # Get all DXF files in leadframes directory
    dxf_files = []
    for file in os.listdir(leadframes_dir):
        if file.lower().endswith('.dxf'):
            dxf_files.append(file)
    return None

def check_dimension_rules(original_width: float, original_height: float, 
                         size_adjustment_factor: float) -> Dict[str, Any]:
    """
    Check basic length and width dimension rules
    
    Args:
        original_width: Original boundary width
        original_height: Original boundary height
        size_adjustment_factor: Factor to adjust size
        
    Returns:
        Dimension check results
    """
    
    rules = DESIGN_RULES["length_width_rules"]
    
    # Apply size adjustment
    adjusted_width = original_width * size_adjustment_factor
    adjusted_height = original_height * size_adjustment_factor
    
    length = max(adjusted_width, adjusted_height)
    width_dim = min(adjusted_width, adjusted_height)
    
    violations = []
    
    # Check length constraints
    if length < rules["min_length"]:
        violations.append(f"Adjusted length {length:.1f}mm is below minimum {rules['min_length']}mm")
    elif length > rules["max_length"]:
        violations.append(f"Adjusted length {length:.1f}mm exceeds maximum {rules['max_length']}mm")
    
    # Check width constraints
    if width_dim < rules["min_width"]:
        violations.append(f"Adjusted width {width_dim:.1f}mm is below minimum {rules['min_width']}mm")
    elif width_dim > rules["max_width"]:
        violations.append(f"Adjusted width {width_dim:.1f}mm exceeds maximum {rules['max_width']}mm")
    
    status = "PASS" if not violations else "FAIL"
    
    return {
        "status": status,
        "violations": violations,
        "rules_applied": rules,
        "adjusted_dimensions": {
            "width": round(adjusted_width, 1),
            "height": round(adjusted_height, 1),
            "length": round(length, 1),
            "width_dim": round(width_dim, 1)
        }
    }

def check_adjusted_dimensions(original_width: float, original_height: float, size_adjustment_factor: float = 0.5) -> Dict[str, Any]:
    """
    Check dimensions after applying size adjustment factor
    
    Args:
        original_width: Original boundary width
        original_height: Original boundary height
        size_adjustment_factor: Factor to adjust size (default 0.5 = divide by 2)
        
    Returns:
        Validation result with pass/fail status
    """
    current_time = get_current_time_utc8()
    logger.info(f"Checking adjusted dimensions: {original_width}x{original_height} with factor {size_adjustment_factor} by HarrisonKuo47")
    
    rules = DESIGN_RULES["length_width_rules"]
    
    # Apply size adjustment factor
    adjusted_width = original_width * size_adjustment_factor
    adjusted_height = original_height * size_adjustment_factor
    
    # Determine which is length (longer) and width (shorter)
    length = max(adjusted_width, adjusted_height)
    width_dim = min(adjusted_width, adjusted_height)
    
    violations = []
    
    # Check length constraints
    if length < rules["min_length"]:
        violations.append(f"Adjusted length {length:.1f}mm is below minimum {rules['min_length']}mm")
    elif length > rules["max_length"]:
        violations.append(f"Adjusted length {length:.1f}mm exceeds maximum {rules['max_length']}mm")
    
    # Check width constraints
    if width_dim < rules["min_width"]:
        violations.append(f"Adjusted width {width_dim:.1f}mm is below minimum {rules['min_width']}mm")
    elif width_dim > rules["max_width"]:
        violations.append(f"Adjusted width {width_dim:.1f}mm exceeds maximum {rules['max_width']}mm")
    
    # Determine status
    status = "PASS" if not violations else "FAIL"
    
    result = {
        "status": status,
        "original_dimensions": {
            "width": round(original_width, 1),
            "height": round(original_height, 1)
        },
        "adjusted_dimensions": {
            "width": round(adjusted_width, 1),
            "height": round(adjusted_height, 1),
            "length": round(length, 1),
            "width_dim": round(width_dim, 1)
        },
        "size_adjustment_factor": size_adjustment_factor,
        "adjustment_description": f"1:{1/size_adjustment_factor:.1f} (divide by {1/size_adjustment_factor:.1f})",
        "violations": violations,
        "rules_applied": rules,
        "check_timestamp": current_time
    }
    
    logger.info(f"Size adjustment check completed: {status} - {len(violations)} violations")
    return result


def check_adjusted_dimensions_with_vacuum_scanning(
    original_width: float, original_height: float, 
    size_adjustment_factor: float = 0.5,
    boundary_data: Optional[Dict[str, float]] = None,
    required_vacuum_positions: int = 10,
    dxf_file_path: Optional[str] = None,
    layer_names_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Enhanced design rule check using the separated vacuum_scanner module
    """
    
    logger.info(f"Enhanced design rule check: {original_width}x{original_height}mm, factor={size_adjustment_factor}")
    
    vacuum_rules = DESIGN_RULES["vacuum_position_rules"]
    
    # 1. Basic dimension check
    dimension_check = check_dimension_rules(original_width, original_height, size_adjustment_factor)
    
    # 2. Vacuum position check using separated vacuum_scanner module
    vacuum_check_result = None
    if boundary_data and dxf_file_path and layer_names_file:
        try:
            logger.info("Calling separated vacuum_scanner module")
            
            # Use the separated vacuum scanner module
            scan_complete_result = run_vacuum_position_scan(
                dxf_file_path=dxf_file_path,
                layer_names_file=layer_names_file,
                boundary_data=boundary_data,
                adjustment_factor=size_adjustment_factor,
                vacuum_diameter_mm=vacuum_rules["vacuum_diameter_mm"],
                required_positions=required_vacuum_positions,
                scan_unit_mm=vacuum_rules["scan_unit_mm"],
                resolution_dpi=vacuum_rules["resolution_dpi"]
            )
            
            # Extract scan result from vacuum scanner
            vacuum_check_result = scan_complete_result["scan_result"]
            vacuum_check_result["profile_info"] = scan_complete_result["profile_info"]
            vacuum_check_result["scanning_parameters"] = scan_complete_result["scanning_parameters"]
            
            logger.info(f"Vacuum scanner module completed: {vacuum_check_result['status']}")
            
        except Exception as e:
            logger.error(f"Vacuum scanner module failed: {e}")
            vacuum_check_result = {
                "status": "ERROR",
                "error": str(e),
                "positions_found": 0,
                "required_positions": required_vacuum_positions
            }
    
    # 3. Overall status determination
    if dimension_check["status"] == "FAIL":
        overall_status = "FAIL"
    elif vacuum_check_result and vacuum_check_result["status"] == "FAIL":
        overall_status = "FAIL"
    elif vacuum_check_result and vacuum_check_result["status"] == "ERROR":
        overall_status = "WARNING"
    else:
        overall_status = "PASS"
    
    # 4. Compile final results
    result = {
        "status": overall_status,
        "check_timestamp": get_current_time_utc8(),
        "checked_by": "HarrisonKuo47",
        "original_dimensions": {
            "width": round(original_width, 1),
            "height": round(original_height, 1)
        },
        "adjusted_dimensions": dimension_check["adjusted_dimensions"],
        "size_adjustment_factor": size_adjustment_factor,
        "adjustment_description": f"1:{1/size_adjustment_factor:.1f} (divide by {1/size_adjustment_factor:.1f})",
        
        # Results from different modules
        "dimension_check": dimension_check,
        "vacuum_position_check": vacuum_check_result,
        
        # Summary violations
        "all_violations": dimension_check["violations"] + (
            [f"Insufficient vacuum positions: {vacuum_check_result['positions_found']}/{required_vacuum_positions}"] 
            if vacuum_check_result and vacuum_check_result["status"] == "FAIL" 
            else []
        )
    }
    
    logger.info(f"Enhanced design rule check completed: {overall_status}")
    return result

# Backward compatibility functions
def check_adjusted_dimensions_with_vacuum(original_width: float, original_height: float, 
                                        size_adjustment_factor: float = 0.5,
                                        boundary_data: Optional[Dict[str, float]] = None,
                                        required_vacuum_positions: int = 10) -> Dict[str, Any]:
    """Backward compatibility wrapper"""
    return check_adjusted_dimensions_with_vacuum_scanning(
        original_width, original_height, size_adjustment_factor, 
        boundary_data, required_vacuum_positions
    )

def make_json_serializable(obj):
    """
    Convert object to JSON serializable format
    Fixed for all numpy and boolean types
    """
    if isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, bool):
        return obj  # Python bool is already JSON serializable
    elif obj is None:
        return None
    else:
        return obj

def save_design_check_results(analysis_folder: str, leadframe_folder: str, check_results: Dict[str, Any]) -> str:
    """Save design check results to JSON file"""
    
    try:
        design_check_file = os.path.join(analysis_folder, f"{leadframe_folder}_design_check.json")
        
        # Add metadata
        check_results.update({
            "leadframe_folder": leadframe_folder,
            "analysis_folder": analysis_folder,
            "save_timestamp": get_current_time_utc8(),
        })
        
        with open(design_check_file, 'w') as f:
            json.dump(check_results, f, indent=2)
        
        logger.info(f"Design check results saved: {design_check_file}")
        return design_check_file
        
    except Exception as e:
        logger.error(f"Failed to save design check results: {e}")
        raise

def load_design_check_results(analysis_folder: str, leadframe_folder: str) -> Optional[Dict[str, Any]]:
    """Load design check results from JSON file"""
    
    try:
        design_check_file = os.path.join(analysis_folder, f"{leadframe_folder}_design_check.json")
        
        if not os.path.exists(design_check_file):
            logger.info(f"No design check results found for {leadframe_folder}")
            return None
        
        with open(design_check_file, 'r') as f:
            results = json.load(f)
        
        logger.info(f"Design check results loaded for {leadframe_folder}")
        return results
        
    except Exception as e:
        logger.error(f"Failed to load design check results: {e}")
        return None