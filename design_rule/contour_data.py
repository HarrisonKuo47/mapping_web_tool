"""
Design Rule Data Processing Functions
Date: 2025-08-29 01:49:46 UTC

"""

import os
import pandas as pd
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def get_processed_leadframes(upload_dir: str) -> List[Dict]:
    """Get list of processed lead frames from temp_analysis folder"""
    
    temp_analysis_dir = os.path.join(upload_dir, "temp_analysis")
    processed_files = []
    
    logger.info(f"Scanning for processed lead frames in: {temp_analysis_dir}")
    
    if not os.path.exists(temp_analysis_dir):
        logger.warning(f"Temp analysis directory not found: {temp_analysis_dir}")
        return processed_files
    
    for folder_name in os.listdir(temp_analysis_dir):
        folder_path = os.path.join(temp_analysis_dir, folder_name)
        if os.path.isdir(folder_path):
            # Check for boundary file
            boundary_file = os.path.join(folder_path, f"{folder_name}_boundary.xlsx")
            shapes_file = os.path.join(folder_path, f"{folder_name}_shapes_summary.xlsx")
            
            if os.path.exists(boundary_file) and os.path.exists(shapes_file):
                try:
                    # Read boundary data
                    boundary_df = pd.read_excel(boundary_file)
                    boundary_data = {}
                    for _, row in boundary_df.iterrows():
                        boundary_data[row['Item']] = row['Value']
                    
                    width = boundary_data.get('x_max', 0) - boundary_data.get('x_min', 0)
                    height = boundary_data.get('y_max', 0) - boundary_data.get('y_min', 0)
                    
                    # Read shapes count
                    shapes_df = pd.read_excel(shapes_file)
                    shapes_count = len(shapes_df)
                    
                    # Check if design check exists
                    design_check_file = os.path.join(folder_path, f"{folder_name}_design_check.json")
                    has_design_check = os.path.exists(design_check_file)
                    
                    processed_files.append({
                        "folder_name": folder_name,
                        "folder_path": folder_path,
                        "boundary_file": boundary_file,
                        "shapes_file": shapes_file,
                        "design_check_file": design_check_file if has_design_check else None,
                        "width": round(width, 3),
                        "height": round(height, 3),
                        "shapes_count": shapes_count,
                        "has_design_check": has_design_check,
                        "boundary_data": boundary_data
                    })
                    
                    logger.info(f"Found processed lead frame: {folder_name} ({width:.3f}x{height:.3f}mm, {shapes_count} shapes)")
                    
                except Exception as e:
                    logger.error(f"Error reading data for {folder_name}: {e}")
    
    logger.info(f"Found {len(processed_files)} processed lead frames")
    return sorted(processed_files, key=lambda x: x['folder_name'])

def read_boundary_data(boundary_file: str) -> Dict[str, float]:
    """Read boundary data from Excel file"""
    
    try:
        logger.info(f"Reading boundary data from: {boundary_file}")
        
        boundary_df = pd.read_excel(boundary_file)
        boundary_data = {}
        
        for _, row in boundary_df.iterrows():
            boundary_data[row['Item']] = float(row['Value'])
        
        logger.info(f"Boundary data loaded: {len(boundary_data)} items")
        return boundary_data
        
    except Exception as e:
        logger.error(f"Failed to read boundary data from {boundary_file}: {e}")
        raise

def read_shapes_data(shapes_file: str) -> List[Dict]:
    """Read shapes data from Excel file"""
    
    try:
        logger.info(f"Reading shapes data from: {shapes_file}")
        
        shapes_df = pd.read_excel(shapes_file)
        shapes_data = shapes_df.to_dict('records')
        
        logger.info(f"Shapes data loaded: {len(shapes_data)} shapes")
        return shapes_data
        
    except Exception as e:
        logger.error(f"Failed to read shapes data from {shapes_file}: {e}")
        raise

def calculate_leadframe_dimensions(boundary_data: Dict[str, float]) -> Dict[str, float]:
    """Calculate lead frame dimensions from boundary data"""
    
    try:
        width = boundary_data.get('x_max', 0) - boundary_data.get('x_min', 0)
        height = boundary_data.get('y_max', 0) - boundary_data.get('y_min', 0)
        mid_x = boundary_data.get('mid_x', 0)
        mid_y = boundary_data.get('mid_y', 0)
        
        dimensions = {
            "width": round(width, 3),
            "height": round(height, 3),
            "length": round(max(width, height), 3),
            "width_dim": round(min(width, height), 3),
            "mid_x": round(mid_x, 3),
            "mid_y": round(mid_y, 3),
            "area": round(width * height, 3),
            "aspect_ratio": round(min(width, height) / max(width, height), 3) if max(width, height) > 0 else 0
        }
        
        logger.info(f"Calculated dimensions: {dimensions['width']}x{dimensions['height']}mm")
        return dimensions
        
    except Exception as e:
        logger.error(f"Failed to calculate dimensions: {e}")
        raise

def get_design_rule_summary(upload_dir: str) -> Dict[str, Any]:
    """Get summary of all design rule checks"""
    
    processed_files = get_processed_leadframes(upload_dir)
    summary = {
        "total_files": len(processed_files),
        "checked_files": 0,
        "passed": 0,
        "warnings": 0,
        "failed": 0,
        "unchecked": 0,
        "details": [],
        "timestamp": "2025-08-29T01:49:46Z",
        "generated_by": "HarrisonKuo47"
    }
    
    for file_info in processed_files:
        if file_info["has_design_check"]:
            summary["checked_files"] += 1
            
            try:
                with open(file_info["design_check_file"], 'r') as f:
                    import json
                    check_data = json.load(f)
                
                status = check_data.get("status", "UNKNOWN")
                if status == "PASS":
                    summary["passed"] += 1
                elif status == "WARNING":
                    summary["warnings"] += 1
                elif status == "FAIL":
                    summary["failed"] += 1
                
                summary["details"].append({
                    "folder_name": file_info["folder_name"],
                    "status": status,
                    "length": check_data.get("length", 0),
                    "width": check_data.get("width", 0),
                    "violations": len(check_data.get("violations", [])),
                    "warnings_count": len(check_data.get("warnings", [])),
                    "lf_type": check_data.get("lf_type", "GENERAL"),
                    "check_timestamp": check_data.get("check_timestamp", "")
                })
                
            except Exception as e:
                logger.error(f"Error reading design check for {file_info['folder_name']}: {e}")
        else:
            summary["unchecked"] += 1
    
    logger.info(f"Design rule summary: {summary['checked_files']}/{summary['total_files']} checked")
    return summary

def export_design_rule_report(upload_dir: str, output_file: str) -> str:
    """Export design rule check report to Excel"""
    
    try:
        logger.info(f"Exporting design rule report to: {output_file}")
        
        summary = get_design_rule_summary(upload_dir)
        
        # Create DataFrame from summary details
        df = pd.DataFrame(summary["details"])
        
        # Add summary sheet
        summary_data = {
            "Metric": ["Total Files", "Checked Files", "Passed", "Warnings", "Failed", "Unchecked"],
            "Count": [
                summary["total_files"], 
                summary["checked_files"], 
                summary["passed"], 
                summary["warnings"], 
                summary["failed"], 
                summary["unchecked"]
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        # Write to Excel with multiple sheets
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            if not df.empty:
                df.to_excel(writer, sheet_name='Details', index=False)
        
        logger.info(f"Design rule report exported successfully: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Failed to export design rule report: {e}")
        raise