"""
Additional utility functions needed for analysis routes
Date: 2025-08-27 02:41:32 UTC
User: HarrisonKuo47
"""

import pandas as pd
from config.settings import settings

def extract_pkg_type_from_column(pkg_value: str) -> str:
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

def extract_lf_type_from_column(lf_value: str) -> str:
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

def extract_lf_type_from_filename(filename: str) -> str:
    """Extract Lead Frame type from filename as fallback"""
    filename_upper = str(filename).upper()
    
    for lf_type, keywords in settings.LF_TYPES.items():
        for keyword in keywords:
            if keyword in filename_upper:
                return lf_type
    
    return 'OTHER'

def detect_handler_kit_type(file_path: str) -> str:
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