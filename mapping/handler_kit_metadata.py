"""
Clean Handler Kit Metadata - No Redundant Functions
Date: 2025-08-28 02:20:41 UTC
User: HarrisonKuo47
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List

# ✅ ONLY IMPORT WHAT WE ACTUALLY USE
from services.handler_kit_parser import (
    parse_handler_kit_excel_unified,  # Main parser function
    extract_lf_type_from_filename     # Only for Lead Frame filenames
)

from config.settings import settings

# Global storage
handler_kit_metadata_cache = {}

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

def extract_handler_kit_metadata(file_path: str) -> Dict:
    """Extract metadata using ONLY the unified parser"""
    try:
        filename = os.path.basename(file_path)
        file_stats = os.stat(file_path)
        
        print(f"🔄 Extracting metadata for {filename} at 2025-08-28 02:20:41 by HarrisonKuo47")
        
        # Extract basic device info from first row
        df_info = pd.read_excel(file_path, header=None, nrows=1)
        part_number = str(df_info.iloc[0, 1]) if len(df_info.columns) > 1 and pd.notna(df_info.iloc[0, 1]) else ''
        device_type = str(df_info.iloc[0, 3]) if len(df_info.columns) > 3 and pd.notna(df_info.iloc[0, 3]) else ''
        
        # ✅ ONE FUNCTION CALL - HANDLES EVERYTHING
        df_coords, pkg_type, lf_type, handler_type = parse_handler_kit_excel_unified(file_path)
        
        # Calculate element count based on type
        element_count = len(df_coords) if df_coords is not None else 0
        element_type = 'vacuum_chambers' if handler_type == 'chamber' else 'vacuum_cups'
        
        metadata = {
            'filename': filename,
            'file_path': file_path,
            'file_size': file_stats.st_size,
            'last_modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            'part_number': part_number,
            'device_type': device_type,
            'pkg_type': pkg_type,
            'lf_type': lf_type,
            'handler_type': handler_type,
            'element_count': element_count,
            'element_type': element_type,
            'vacuum_cup_count': element_count if handler_type == 'cup' else 0,
            'extraction_time': "2025-08-28T02:20:41Z",
            'cache_version': '2.3',
            'extracted_by': 'HarrisonKuo47'
        }
        
        print(f"✅ Successfully extracted metadata for {filename}: {handler_type} with {element_count} elements")
        return convert_numpy_types(metadata)
        
    except Exception as e:
        print(f"❌ Error extracting metadata for {filename}: {str(e)}")
        return {
            'filename': os.path.basename(file_path),
            'error': str(e),
            'extraction_time': "2025-08-28T02:20:41Z",
            'extracted_by': 'HarrisonKuo47'
        }

def load_handler_kit_metadata_cache():
    """Load metadata cache from disk"""
    global handler_kit_metadata_cache
    cache_file = os.path.join(settings.CACHE_DIR, "handler_kit_metadata.json")
    
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                handler_kit_metadata_cache = json.load(f)
            print(f"💾 Loaded metadata cache with {len(handler_kit_metadata_cache)} Handler Kits at 2025-08-28 02:20:41")
        else:
            handler_kit_metadata_cache = {}
            print(f"📦 No metadata cache found, starting fresh at 2025-08-28 02:20:41")
    except Exception as e:
        print(f"❌ Error loading metadata cache: {e}")
        handler_kit_metadata_cache = {}

def save_handler_kit_metadata_cache():
    """Save metadata cache to disk"""
    cache_file = os.path.join(settings.CACHE_DIR, "handler_kit_metadata.json")
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(handler_kit_metadata_cache, f, indent=2)
        print(f"💾 Saved metadata cache with {len(handler_kit_metadata_cache)} Handler Kits at 2025-08-28 02:20:41")
    except Exception as e:
        print(f"❌ Error saving metadata cache: {e}")

def update_handler_kit_metadata(file_path: str, force_update: bool = False):
    """Update metadata for a single Handler Kit"""
    filename = os.path.basename(file_path)
    
    # Check if update needed (smart caching)
    if not force_update and filename in handler_kit_metadata_cache:
        cached_metadata = handler_kit_metadata_cache[filename]
        file_mtime = os.path.getmtime(file_path)
        try:
            cached_mtime = datetime.fromisoformat(cached_metadata.get('last_modified', '1970-01-01')).timestamp()
            if file_mtime <= cached_mtime:
                print(f"⚡ Using cached metadata for {filename}")
                return cached_metadata
        except:
            pass
    
    # Extract fresh metadata
    print(f"🔄 Extracting fresh metadata for {filename} by HarrisonKuo47...")
    metadata = extract_handler_kit_metadata(file_path)
    handler_kit_metadata_cache[filename] = metadata
    
    return metadata

def filter_handler_kits_by_types(pkg_type_filter: str = None, lf_type_filter: str = None) -> List[str]:
    """Filter Handler Kits based on PKG and LF types from columns"""
    filtered_kits = []
    
    print(f"🔍 Filtering {len(handler_kit_metadata_cache)} kits: PKG={pkg_type_filter}, LF={lf_type_filter}")
    
    for filename, metadata in handler_kit_metadata_cache.items():
        # Skip if extraction error
        if 'error' in metadata:
            continue
        
        # PKG type filter
        if pkg_type_filter and pkg_type_filter != 'ALL':
            if metadata.get('pkg_type') != pkg_type_filter:
                continue
        
        # LF type filter
        if lf_type_filter and lf_type_filter != 'ALL':
            if metadata.get('lf_type') != lf_type_filter:
                continue
        
        filtered_kits.append(filename)
    
    print(f"✅ Filtered down to {len(filtered_kits)} matching kits")
    return filtered_kits
