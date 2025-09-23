"""
Complete Enhanced Mapping Service with Direct User Input Support
Date: 2025-09-04 09:33:12 UTC
User: HarrisonKuo47
"""

import os
import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any, Optional
from config.settings import settings
from models.data_models import BoundaryData
from mapping.extract_layers import extract_dxf_layers, create_dynamic_layer_file

class MappingService:
    """Complete enhanced mapping service with direct user input for ratio base dimensions"""
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.results_dir = settings.RESULTS_DIR
    
    def validate_leadframe(self, dxf_filename: str) -> Tuple[str, bool]:
        """Validate lead frame file exists"""
        lf_path = os.path.join(self.upload_dir, "leadframes", dxf_filename)
        return lf_path, os.path.exists(lf_path)
    
    def validate_layers(self, lf_path: str, selected_layers: str) -> Tuple[List[str], List[str]]:
        """Validate selected layers against DXF file"""
        if selected_layers:
            layers_list = [layer.strip() for layer in selected_layers.split(',') if layer.strip()]
        else:
            layers_list = settings.DEFAULT_LAYERS
        
        available_layers = extract_dxf_layers(lf_path)
        valid_layers = [layer for layer in layers_list if layer in available_layers]
        invalid_layers = [layer for layer in layers_list if layer not in available_layers]
        
        return valid_layers, invalid_layers
    
    def create_dynamic_layer_file(self, analysis_id: str, valid_layers: List[str]) -> str:
        """Create dynamic layer file for analysis"""
        dynamic_layer_file = os.path.join(self.upload_dir, "temp_layers", f"{analysis_id}_layers.txt")
        
        if not create_dynamic_layer_file(valid_layers, dynamic_layer_file):
            raise Exception("Failed to create layer configuration")
        
        return dynamic_layer_file
    
    def load_boundary_info(self, dxf_name: str) -> BoundaryData:
        """Load boundary information from Excel file"""
        boundary_info_file = os.path.join(self.upload_dir, "temp_analysis", dxf_name, f"{dxf_name}_boundary.xlsx")
        
        if not os.path.exists(boundary_info_file):
            raise FileNotFoundError(f"Boundary info not found. Please re-upload the Lead Frame.")
        
        boundary_df = pd.read_excel(boundary_info_file)
        return BoundaryData(
            mid_x=float(boundary_df[boundary_df['Item'] == 'mid_x']['Value'].iloc[0]),
            mid_y=float(boundary_df[boundary_df['Item'] == 'mid_y']['Value'].iloc[0]),
            x_min=float(boundary_df[boundary_df['Item'] == 'x_min']['Value'].iloc[0]),
            x_max=float(boundary_df[boundary_df['Item'] == 'x_max']['Value'].iloc[0]),
            y_min=float(boundary_df[boundary_df['Item'] == 'y_min']['Value'].iloc[0]),
            y_max=float(boundary_df[boundary_df['Item'] == 'y_max']['Value'].iloc[0])
        )
    
    def extract_pkg_type_from_column(self, pkg_value: str) -> str:
        """Extract package type from PKG column value"""
        if pd.isna(pkg_value) or str(pkg_value).strip() == '':
            return 'OTHER'
        
        pkg_upper = str(pkg_value).upper().strip()
        
        # Direct match first
        for pkg_type in settings.PACKAGE_TYPES.keys():
            if pkg_type == pkg_upper:
                return pkg_type
        
        # Keyword matching
        for pkg_type, keywords in settings.PACKAGE_TYPES.items():
            for keyword in keywords:
                if keyword in pkg_upper:
                    return pkg_type
        
        return 'OTHER'

    def extract_lf_type_from_column(self, lf_value: str) -> str:
        """Extract LF type from LF column value"""
        if pd.isna(lf_value) or str(lf_value).strip() == '':
            return 'OTHER'
        
        lf_upper = str(lf_value).upper().strip()
        
        # Direct match first
        for lf_type in settings.LF_TYPES.keys():
            if lf_type == lf_upper:
                return lf_type
        
        # Keyword matching
        for lf_type, keywords in settings.LF_TYPES.items():
            for keyword in keywords:
                if keyword in lf_upper:
                    return lf_type
        
        return 'OTHER'

    def extract_lf_type_from_filename(self, filename: str) -> str:
        """Extract Lead Frame type from filename as fallback"""
        filename_upper = str(filename).upper()
        
        for lf_type, keywords in settings.LF_TYPES.items():
            for keyword in keywords:
                if keyword in filename_upper:
                    return lf_type
        
        return 'OTHER'

    def detect_handler_kit_type(self, file_path: str) -> str:
        """Detect if Excel file contains vacuum cups or vacuum chambers"""
        try:
            df = pd.read_excel(file_path, header=1, nrows=5)
            
            # Check for vacuum chamber indicators
            if any(col for col in df.columns if 'chamber' in str(col).lower()):
                return 'chamber'
            
            # Check for chamber naming pattern in first column
            first_col_values = df.iloc[:, 0].astype(str).str.lower()
            if any('_tl' in val or '_bl' in val or '_br' in val or '_tr' in val 
                   for val in first_col_values if pd.notna(val)):
                return 'chamber'
            
            # Default to vacuum cup
            return 'cup'
            
        except Exception:
            return 'cup'

    def parse_handler_kit_excel_with_pkg_lf(self, file_path: str) -> tuple:
        """
        Enhanced parser for Handler Kit Excel files with PKG and LF columns
        Returns: (DataFrame, pkg_type, lf_type)
        """
        try:
            print(f"🔧 [MAPPING] Parsing Handler Kit file: {os.path.basename(file_path)} at 2025-09-04 09:33:12")
            
            # Read with header at row 1 (second row)
            df = pd.read_excel(file_path, header=1)
            
            print(f"🔧 [MAPPING] File structure: Shape={df.shape}, Columns={list(df.columns)}")
            
            # Clean up the data
            df_clean = df.dropna(how='all').copy()
            
            # Find column mapping for coordinates
            required_columns = ['X', 'Y', 'Vacuum size', 'Shape', 'PKG', 'LF']
            available_columns = list(df_clean.columns)
            
            column_mapping = {}
            for req_col in required_columns:
                for avail_col in available_columns:
                    if str(avail_col).strip().upper() == req_col.upper():
                        column_mapping[req_col] = avail_col
                        break
            
            print(f"🗺️ [MAPPING] Column mapping: {column_mapping}")
            
            # Extract PKG and LF types from first data row
            pkg_type = 'OTHER'
            lf_type = 'OTHER'
            
            if 'PKG' in column_mapping and len(df_clean) > 0:
                # Look for first non-empty PKG value
                pkg_col = column_mapping['PKG']
                for idx, row in df_clean.iterrows():
                    pkg_value = row.get(pkg_col)
                    if pd.notna(pkg_value) and str(pkg_value).strip():
                        pkg_type = self.extract_pkg_type_from_column(pkg_value)
                        print(f"📊 [MAPPING] Found PKG type: {pkg_value} -> {pkg_type}")
                        break
            
            if 'LF' in column_mapping and len(df_clean) > 0:
                # Look for first non-empty LF value
                lf_col = column_mapping['LF']
                for idx, row in df_clean.iterrows():
                    lf_value = row.get(lf_col)
                    if pd.notna(lf_value) and str(lf_value).strip():
                        lf_type = self.extract_lf_type_from_column(lf_value)
                        print(f"📊 [MAPPING] Found LF type: {lf_value} -> {lf_type}")
                        break
            
            # Extract coordinate data
            result_data = []
            for idx, row in df_clean.iterrows():
                try:
                    x_col = column_mapping.get('X')
                    y_col = column_mapping.get('Y')
                    
                    if not x_col or not y_col or pd.isna(row.get(x_col)) or pd.isna(row.get(y_col)):
                        continue
                    
                    x_val = float(row[x_col])
                    y_val = float(row[y_col])
                    
                    # Get shape and vacuum size
                    shape_col = column_mapping.get('Shape')
                    size_col = column_mapping.get('Vacuum size')
                    
                    shape = str(row.get(shape_col, 'circle')).lower() if shape_col else 'circle'
                    if shape in ['nan', 'none', '']:
                        shape = 'circle'
                    
                    vacuum_size = str(row.get(size_col, '3.0')) if size_col else '3.0'
                    if vacuum_size in ['nan', 'none', '']:
                        vacuum_size = '3.0'
                    
                    result_data.append({
                        'X': x_val,
                        'Y': y_val,
                        'Shape': shape,
                        'Vacuum size': vacuum_size
                    })
                    
                except (ValueError, TypeError) as e:
                    print(f"⚠️ [MAPPING] Skipping row {idx}: {e}")
                    continue
            
            if not result_data:
                print("❌ [MAPPING] No valid coordinate data found")
                return None, pkg_type, lf_type
            
            result_df = pd.DataFrame(result_data)
            print(f"✅ [MAPPING] Successfully parsed {len(result_df)} vacuum cup coordinates")
            print(f"📊 [MAPPING] PKG Type: {pkg_type}, LF Type: {lf_type}")
            
            return result_df, pkg_type, lf_type
            
        except Exception as e:
            print(f"❌ [MAPPING] Error parsing Handler Kit file: {str(e)}")
            return None, 'OTHER', 'OTHER'

    def parse_vacuum_chamber_excel(self, file_path: str) -> tuple:
        """
        Parse vacuum chamber data from Excel file with four-corner definitions
        Returns: (DataFrame with rectangles, pkg_type, lf_type)
        """
        try:
            print(f"🔧 [MAPPING] Parsing Vacuum Chamber file: {os.path.basename(file_path)} at 2025-09-04 09:33:12")
            
            # Read with header at row 1 (second row)
            df = pd.read_excel(file_path, header=1)
            df_clean = df.dropna(how='all').copy()
            
            # Find column mapping
            required_columns = ['Vacuum Chamber', 'X', 'Y', 'Chamber thickness', 'PKG', 'LF']
            column_mapping = {}
            for req_col in required_columns:
                for avail_col in df_clean.columns:
                    if str(avail_col).strip().upper() == req_col.upper():
                        column_mapping[req_col] = avail_col
                        break
            
            # Extract PKG and LF types from first data row
            pkg_type = 'OTHER'
            lf_type = 'OTHER'
            
            if 'PKG' in column_mapping and len(df_clean) > 0:
                pkg_col = column_mapping['PKG']
                for idx, row in df_clean.iterrows():
                    pkg_value = row.get(pkg_col)
                    if pd.notna(pkg_value) and str(pkg_value).strip():
                        pkg_type = self.extract_pkg_type_from_column(pkg_value)
                        break
            
            if 'LF' in column_mapping and len(df_clean) > 0:
                lf_col = column_mapping['LF']
                for idx, row in df_clean.iterrows():
                    lf_value = row.get(lf_col)
                    if pd.notna(lf_value) and str(lf_value).strip():
                        lf_type = self.extract_lf_type_from_column(lf_value)
                        break
            
            # Group chamber corners into rectangles
            chambers = {}
            for idx, row in df_clean.iterrows():
                chamber_name = str(row.get(column_mapping.get('Vacuum Chamber', ''), ''))
                if pd.isna(row.get(column_mapping.get('X'))) or pd.isna(row.get(column_mapping.get('Y'))):
                    continue
                    
                # Extract chamber number and corner type
                if '_TL' in chamber_name or '_BL' in chamber_name or '_BR' in chamber_name or '_TR' in chamber_name:
                    chamber_base = chamber_name.rsplit('_', 1)[0]  # e.g., "Vacuum 1"
                    corner_type = chamber_name.rsplit('_', 1)[1]   # e.g., "TL"
                    
                    if chamber_base not in chambers:
                        chambers[chamber_base] = {}
                    
                    chambers[chamber_base][corner_type] = {
                        'X': float(row[column_mapping['X']]),
                        'Y': float(row[column_mapping['Y']]),
                        'thickness': float(row.get(column_mapping.get('Chamber thickness', ''), 2))
                    }
            
            # Convert to rectangle data
            result_data = []
            for chamber_name, corners in chambers.items():
                # Ensure we have all four corners
                if all(corner in corners for corner in ['TL', 'BL', 'BR', 'TR']):
                    result_data.append({
                        'Chamber': chamber_name,
                        'TL_X': corners['TL']['X'], 'TL_Y': corners['TL']['Y'],
                        'BL_X': corners['BL']['X'], 'BL_Y': corners['BL']['Y'],
                        'BR_X': corners['BR']['X'], 'BR_Y': corners['BR']['Y'],
                        'TR_X': corners['TR']['X'], 'TR_Y': corners['TR']['Y'],
                        'thickness': corners['TL']['thickness']
                    })
            
            if not result_data:
                print("❌ [MAPPING] No valid chamber rectangle data found")
                return None, pkg_type, lf_type
                
            result_df = pd.DataFrame(result_data)
            print(f"✅ [MAPPING] Successfully parsed {len(result_df)} vacuum chambers")
            print(f"📊 [MAPPING] PKG Type: {pkg_type}, LF Type: {lf_type}")
            
            return result_df, pkg_type, lf_type
            
        except Exception as e:
            print(f"❌ [MAPPING] Error parsing Vacuum Chamber file: {str(e)}")
            return None, 'OTHER', 'OTHER'

    def parse_handler_kit_excel_unified(self, file_path: str) -> tuple:
        """
        Unified parser that handles both vacuum cups and chambers
        Returns: (DataFrame, pkg_type, lf_type, handler_type)
        """
        print(f"🔧 [MAPPING] Running unified parser for {os.path.basename(file_path)} at 2025-09-04 09:33:12")
        
        handler_type = self.detect_handler_kit_type(file_path)
        print(f"🔍 [MAPPING] Detected handler type: {handler_type}")
        
        if handler_type == 'chamber':
            df, pkg_type, lf_type = self.parse_vacuum_chamber_excel(file_path)
            return df, pkg_type, lf_type, 'chamber'
        else:
            df, pkg_type, lf_type = self.parse_handler_kit_excel_with_pkg_lf(file_path)
            return df, pkg_type, lf_type, 'cup'
    
    def validate_and_set_user_dimensions(self, width: float, height: float) -> Tuple[bool, str, Tuple[float, float]]:
        """
        Validate user input dimensions and set as ratio base
        
        Returns:
            (is_valid, message, (width, height))
        """
        
        print(f"🔍 [MAPPING] Validating user input dimensions: {width} x {height}")
        
        # Validate using settings
        is_valid, error_msg = settings.validate_dimensions(width, height)
        
        if not is_valid:
            print(f"❌ [MAPPING] Validation failed: {error_msg}")
            return False, error_msg, (0, 0)
        
        # Set as current ratio base
        success = settings.set_current_ratio_base(width, height)
        
        if success:
            print(f"✅ [MAPPING] User dimensions validated and set: {width} x {height}")
            return True, f"Using dimensions: {width} x {height} mm", (width, height)
        else:
            return False, "Failed to set dimensions", (0, 0)
    
    def transform_handler_kit_coordinates_with_user_input(self, df_hk: pd.DataFrame, 
                                                        boundary: BoundaryData,
                                                        user_width: float,
                                                        user_height: float) -> pd.DataFrame:
        """
        Transform coordinates using user-specified dimensions as ratio base
        """
        
        print(f"🔧 [MAPPING] Transforming with user input dimensions...")
        print(f"  📊 User input ratio base: {user_width} x {user_height} mm")
        print(f"  📊 Lead frame boundary: {boundary.width:.1f} x {boundary.height:.1f} mm")
        print(f"  📊 Input data points: {len(df_hk)}")
        
        # Validate user input first
        is_valid, error_msg, validated_dims = self.validate_and_set_user_dimensions(user_width, user_height)
        
        if not is_valid:
            raise ValueError(f"Invalid user dimensions: {error_msg}")
        
        df_transformed = df_hk.copy()
        
        # Calculate transformation ratios using user input
        relative_ratio_width = boundary.width / user_width
        relative_ratio_height = boundary.height / user_height
        
        print(f"  📊 Transformation ratios: W={relative_ratio_width:.3f}, H={relative_ratio_height:.3f}")
        
        # Apply transformation
        df_transformed['X_LF'] = boundary.mid_x + df_hk['X'] * relative_ratio_width
        df_transformed['Y_LF'] = boundary.mid_y + df_hk['Y'] * relative_ratio_height
        
        # Boundary validation
        x_min_actual = df_transformed['X_LF'].min()
        x_max_actual = df_transformed['X_LF'].max()
        y_min_actual = df_transformed['Y_LF'].min()
        y_max_actual = df_transformed['Y_LF'].max()
        
        print(f"  📊 Transformed coordinate ranges:")
        print(f"    X: [{x_min_actual:.1f}, {x_max_actual:.1f}] (boundary: [{boundary.x_min:.1f}, {boundary.x_max:.1f}])")
        print(f"    Y: [{y_min_actual:.1f}, {y_max_actual:.1f}] (boundary: [{boundary.y_min:.1f}, {boundary.y_max:.1f}])")
        
        # Check for out-of-bounds points
        x_out_of_bounds = ((df_transformed['X_LF'] < boundary.x_min) | 
                          (df_transformed['X_LF'] > boundary.x_max)).sum()
        y_out_of_bounds = ((df_transformed['Y_LF'] < boundary.y_min) | 
                          (df_transformed['Y_LF'] > boundary.y_max)).sum()
        
        if x_out_of_bounds > 0 or y_out_of_bounds > 0:
            print(f"⚠️ [MAPPING] Points outside boundary: X={x_out_of_bounds}, Y={y_out_of_bounds}")
            
            # Optional: Clamp to boundaries with warning
            df_transformed['X_LF'] = df_transformed['X_LF'].clip(boundary.x_min, boundary.x_max)
            df_transformed['Y_LF'] = df_transformed['Y_LF'].clip(boundary.y_min, boundary.y_max)
            print(f"✅ [MAPPING] Clamped out-of-bounds points to boundary")
        
        print(f"✅ [MAPPING] Transformation completed successfully: {len(df_transformed)} points")
        
        return df_transformed
    
    def transform_vacuum_chambers_with_user_input(self, df_chambers: pd.DataFrame, 
                                                boundary: BoundaryData,
                                                user_width: float,
                                                user_height: float) -> pd.DataFrame:
        """
        Transform vacuum chambers using user-specified dimensions
        """
        
        print(f"🔧 [MAPPING] Transforming vacuum chambers with user input...")
        print(f"  📊 Chambers: {len(df_chambers)}")
        print(f"  📊 User ratio base: {user_width} x {user_height} mm")
        
        # Validate user input
        is_valid, error_msg, validated_dims = self.validate_and_set_user_dimensions(user_width, user_height)
        
        if not is_valid:
            raise ValueError(f"Invalid user dimensions: {error_msg}")
        
        df_transformed = df_chambers.copy()
        
        relative_ratio_width = boundary.width / user_width
        relative_ratio_height = boundary.height / user_height
        
        # Transform all four corners
        for corner in ['TL', 'BL', 'BR', 'TR']:
            df_transformed[f'{corner}_X_LF'] = boundary.mid_x + df_chambers[f'{corner}_X'] * relative_ratio_width
            df_transformed[f'{corner}_Y_LF'] = boundary.mid_y + df_chambers[f'{corner}_Y'] * relative_ratio_height
        
        print(f"✅ [MAPPING] Chamber transformation completed successfully")
        
        return df_transformed
    
    def convert_chambers_to_shapes(self, df_chambers: pd.DataFrame) -> pd.DataFrame:
        """Convert chamber coordinates to shapes for overlap analysis"""
        shapes_data = []
        
        for idx, row in df_chambers.iterrows():
            # Create rectangle from four corners
            corners = [
                (row['TL_X_LF'], row['TL_Y_LF']),  # Top Left
                (row['TR_X_LF'], row['TR_Y_LF']),  # Top Right  
                (row['BR_X_LF'], row['BR_Y_LF']),  # Bottom Right
                (row['BL_X_LF'], row['BL_Y_LF'])   # Bottom Left
            ]
            
            # Calculate center and dimensions
            center_x = (row['TL_X_LF'] + row['BR_X_LF']) / 2
            center_y = (row['TL_Y_LF'] + row['BR_Y_LF']) / 2
            width = abs(row['TR_X_LF'] - row['TL_X_LF'])
            height = abs(row['TL_Y_LF'] - row['BL_Y_LF'])
            
            # Use width as "vacuum size" equivalent for compatibility
            vacuum_size_equivalent = max(width, height)
            
            shapes_data.append({
                'Chamber': row['Chamber'],
                'X_LF': center_x,
                'Y_LF': center_y,
                'Shape': 'rectangle',
                'Vacuum size': vacuum_size_equivalent,
                'thickness': row['thickness'],
                'corners': corners,
                'width': width,
                'height': height
            })
        
        return pd.DataFrame(shapes_data)
    
    def get_transformation_summary(self, boundary: BoundaryData, 
                                 user_width: float, user_height: float) -> Dict[str, Any]:
        """
        Get summary of transformation parameters for reporting
        """
        
        relative_ratio_width = boundary.width / user_width
        relative_ratio_height = boundary.height / user_height
        
        return {
            "user_input_dimensions": {
                "width": float(user_width),
                "height": float(user_height)
            },
            "leadframe_dimensions": {
                "width": float(boundary.width),
                "height": float(boundary.height)
            },
            "transformation_ratios": {
                "width_ratio": float(relative_ratio_width),
                "height_ratio": float(relative_ratio_height)
            },
            "scale_factors": {
                "x_scale": float(relative_ratio_width),
                "y_scale": float(relative_ratio_height),
                "avg_scale": float((relative_ratio_width + relative_ratio_height) / 2)
            },
            "analysis_metadata": {
                "transformation_method": "user_specified_dimensions",
                "analysis_date": "2025-09-04",
                "analysis_time": "09:33:12 UTC",
                "analyzed_by": "HarrisonKuo47"
            }
        }
    
    # Legacy compatibility methods (with deprecation warnings)
    def transform_handler_kit_coordinates(self, df_hk: pd.DataFrame, boundary: BoundaryData) -> pd.DataFrame:
        """Legacy method - use user input methods for new analyses"""
        print(f"⚠️ [DEPRECATED] Using legacy transformation - consider using user input method")
        
        # Use current settings as fallback
        current_width, current_height = settings.get_current_ratio_base()
        return self.transform_handler_kit_coordinates_with_user_input(df_hk, boundary, current_width, current_height)
    
    def transform_vacuum_chambers(self, df_chambers: pd.DataFrame, boundary: BoundaryData) -> pd.DataFrame:
        """Legacy method - use user input methods for new analyses"""
        print(f"⚠️ [DEPRECATED] Using legacy chamber transformation - consider using user input method")
        
        # Use current settings as fallback
        current_width, current_height = settings.get_current_ratio_base()
        return self.transform_vacuum_chambers_with_user_input(df_chambers, boundary, current_width, current_height)

# Global service instance
mapping_service = MappingService()