"""
Complete Handler Kit Parser Service - Updated
Date: 2025-08-28 02:20:41 UTC
User: HarrisonKuo47
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from config.settings import settings

class HandlerKitParser:
    """Complete parser for handler kit files with all required functions"""
    
    def __init__(self):
        self.current_time = "2025-08-28 02:20:41"
        self.current_user = "HarrisonKuo47"
    
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
            print(f"🔍 Parsing Handler Kit file: {file_path} at {self.current_time} by {self.current_user}")
            
            # Read with header at row 1 (second row)
            df = pd.read_excel(file_path, header=1)
            
            print(f"📊 File structure: Shape={df.shape}, Columns={list(df.columns)}")
            
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
            
            print(f"🗺️ Column mapping: {column_mapping}")
            
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
                        print(f"📦 Found PKG type: {pkg_value} -> {pkg_type}")
                        break
            
            if 'LF' in column_mapping and len(df_clean) > 0:
                # Look for first non-empty LF value
                lf_col = column_mapping['LF']
                for idx, row in df_clean.iterrows():
                    lf_value = row.get(lf_col)
                    if pd.notna(lf_value) and str(lf_value).strip():
                        lf_type = self.extract_lf_type_from_column(lf_value)
                        print(f"🔗 Found LF type: {lf_value} -> {lf_type}")
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
                    print(f"⚠️ Skipping row {idx}: {e}")
                    continue
            
            if not result_data:
                print("❌ No valid coordinate data found")
                return None, pkg_type, lf_type
            
            result_df = pd.DataFrame(result_data)
            print(f"✅ Successfully parsed {len(result_df)} vacuum cup coordinates")
            print(f"📦 PKG Type: {pkg_type}, 🔗 LF Type: {lf_type}")
            
            return result_df, pkg_type, lf_type
            
        except Exception as e:
            print(f"❌ Error parsing Handler Kit file: {str(e)}")
            return None, 'OTHER', 'OTHER'

    def parse_vacuum_chamber_excel(self, file_path: str) -> tuple:
        """
        Parse vacuum chamber data from Excel file with four-corner definitions
        Returns: (DataFrame with rectangles, pkg_type, lf_type)
        """
        try:
            print(f"🔧 Parsing Vacuum Chamber file: {file_path} at {self.current_time} by {self.current_user}")
            
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
                print("❌ No valid chamber rectangle data found")
                return None, pkg_type, lf_type
                
            result_df = pd.DataFrame(result_data)
            print(f"✅ Successfully parsed {len(result_df)} vacuum chambers")
            print(f"📦 PKG Type: {pkg_type}, 🔗 LF Type: {lf_type}")
            
            return result_df, pkg_type, lf_type
            
        except Exception as e:
            print(f"❌ Error parsing Vacuum Chamber file: {str(e)}")
            return None, 'OTHER', 'OTHER'

    def parse_handler_kit_excel_unified(self, file_path: str) -> tuple:
        """
        Unified parser that handles both vacuum cups and chambers
        Returns: (DataFrame, pkg_type, lf_type, handler_type)
        """
        print(f"🔄 Running unified parser for {file_path} at {self.current_time}")
        
        handler_type = self.detect_handler_kit_type(file_path)
        print(f"📋 Detected handler type: {handler_type}")
        
        if handler_type == 'chamber':
            df, pkg_type, lf_type = self.parse_vacuum_chamber_excel(file_path)
            return df, pkg_type, lf_type, 'chamber'
        else:
            df, pkg_type, lf_type = self.parse_handler_kit_excel_with_pkg_lf(file_path)
            return df, pkg_type, lf_type, 'cup'

# Global parser instance
handler_kit_parser = HandlerKitParser()

# ✅ ONLY EXPORT THE FUNCTIONS WE ACTUALLY USE
def parse_handler_kit_excel_unified(file_path: str) -> tuple:
    """Main function - handles all file types automatically"""
    return handler_kit_parser.parse_handler_kit_excel_unified(file_path)

def extract_lf_type_from_filename(filename: str) -> str:
    """Only needed for Lead Frame filenames"""
    return handler_kit_parser.extract_lf_type_from_filename(filename)