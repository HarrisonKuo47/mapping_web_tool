"""
DXF Processing Service for Lead Frame Analysis
Date: 2025-08-28 07:50:12 UTC
User: HarrisonKuo47
"""

import ezdxf
import pandas as pd
from typing import List, Dict, Any

def process_dxf_file(file_path: str) -> List[Dict]:
    """Process DXF file and extract all shapes"""
    try:
        doc = ezdxf.readfile(file_path)
        modelspace = doc.modelspace()
        
        shapes_data = []
        
        for entity in modelspace:
            shape_info = {
                'entity_type': entity.dxftype(),
                'layer': entity.dxf.layer,
                'color': getattr(entity.dxf, 'color', 0),
            }
            
            # Extract coordinates based on entity type
            if entity.dxftype() == 'LINE':
                shape_info.update({
                    'start_x': entity.dxf.start.x,
                    'start_y': entity.dxf.start.y,
                    'end_x': entity.dxf.end.x,
                    'end_y': entity.dxf.end.y
                })
            elif entity.dxftype() == 'CIRCLE':
                shape_info.update({
                    'center_x': entity.dxf.center.x,
                    'center_y': entity.dxf.center.y,
                    'radius': entity.dxf.radius
                })
            elif entity.dxftype() == 'ARC':
                shape_info.update({
                    'center_x': entity.dxf.center.x,
                    'center_y': entity.dxf.center.y,
                    'radius': entity.dxf.radius,
                    'start_angle': entity.dxf.start_angle,
                    'end_angle': entity.dxf.end_angle
                })
            
            shapes_data.append(shape_info)
        
        print(f"✅ Processed {len(shapes_data)} shapes from DXF")
        return shapes_data
        
    except Exception as e:
        print(f"❌ Error processing DXF file: {e}")
        return []

def extract_shapes_summary(shapes_data: List[Dict]) -> List[Dict]:
    """Create shapes summary for Excel export"""
    summary = []
    
    # Group by entity type and layer
    type_layer_counts = {}
    
    for shape in shapes_data:
        entity_type = shape['entity_type']
        layer = shape['layer']
        key = f"{entity_type}_{layer}"
        
        if key not in type_layer_counts:
            type_layer_counts[key] = {
                'entity_type': entity_type,
                'layer': layer,
                'count': 0
            }
        type_layer_counts[key]['count'] += 1
    
    summary = list(type_layer_counts.values())
    print(f"✅ Generated shapes summary with {len(summary)} groups")
    return summary

def calculate_boundary_data(shapes_data: List[Dict]) -> Dict:
    """Calculate boundary data for all shapes"""
    if not shapes_data:
        return {
            'mid_x': 0, 'mid_y': 0,
            'x_min': 0, 'x_max': 0,
            'y_min': 0, 'y_max': 0,
            'width': 0, 'height': 0
        }
    
    x_coords = []
    y_coords = []
    
    for shape in shapes_data:
        entity_type = shape['entity_type']
        
        if entity_type == 'LINE':
            x_coords.extend([shape.get('start_x', 0), shape.get('end_x', 0)])
            y_coords.extend([shape.get('start_y', 0), shape.get('end_y', 0)])
        elif entity_type in ['CIRCLE', 'ARC']:
            center_x = shape.get('center_x', 0)
            center_y = shape.get('center_y', 0)
            radius = shape.get('radius', 0)
            
            x_coords.extend([center_x - radius, center_x + radius])
            y_coords.extend([center_y - radius, center_y + radius])
    
    if x_coords and y_coords:
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        boundary_data = {
            'mid_x': (x_min + x_max) / 2,
            'mid_y': (y_min + y_max) / 2,
            'x_min': x_min,
            'x_max': x_max,
            'y_min': y_min,
            'y_max': y_max,
            'width': x_max - x_min,
            'height': y_max - y_min
        }
    else:
        boundary_data = {
            'mid_x': 0, 'mid_y': 0,
            'x_min': 0, 'x_max': 0,
            'y_min': 0, 'y_max': 0,
            'width': 0, 'height': 0
        }
    
    print(f"✅ Calculated boundary: ({boundary_data['width']:.2f} x {boundary_data['height']:.2f})")
    return boundary_data