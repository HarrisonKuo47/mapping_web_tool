"""
Application Configuration - Enhanced for Direct User Input
Date: 2025-09-04 09:24:16 UTC
User: HarrisonKuo47
"""

import os
from pathlib import Path
from typing import Dict, Tuple, Optional

class Settings:
    # App Information with current date/time
    APP_TITLE = "Automated Lead Frame Mapping Tool"
    APP_VERSION = "2.2.0"
    BUILD_DATE = "2025-09-04"
    BUILD_TIME = "09:24:16 UTC"
    CURRENT_USER = "HarrisonKuo47"
    
    # Directory Configuration
    UPLOAD_DIR = "uploads"
    RESULTS_DIR = os.path.join(UPLOAD_DIR, "results")
    CACHE_DIR = os.path.join(UPLOAD_DIR, "cache")
    
    # ENHANCED: Configurable Base Dimensions with Validation
    DEFAULT_RATIO_BASE_WIDTH = 270
    DEFAULT_RATIO_BASE_HEIGHT = 90
    
    # Validation ranges for user input
    MIN_DIMENSION = 10.0      # Minimum 10mm
    MAX_DIMENSION = 2000.0    # Maximum 2000mm
    
    DEFAULT_LAYERS = ["SH-01_OBJECT", "SH-01_DIM", "SH-01_PKG"]
    
    # Package and LF Type Definitions (unchanged)
    PACKAGE_TYPES = {
        'TSSOP': ['TSSOP', 'TSOP'],
        'SOIC': ['SOIC', 'SOP', 'SSOP'],
        'QFP': ['QFP', 'LQFP', 'TQFP'],
        'QFN': ['QFN', 'VQFN'],
        'VSON': ['VSON'],
        'BGA': ['BGA', 'FBGA'],
        'OTHER': ['OTHER', 'UNKNOWN']
    }

    LF_TYPES = {
        'WLF': ['WLF', 'WAFER', 'WAFER LEVEL'],
        'HYDE': ['HYDE', 'HY-DE'],
        'SUHD': ['SUHD', 'SU-HD'],
        'SUHD_WLF': ['SUHD WLF', 'SUHD-WLF'],
        'RLF': ['RLF'],
        'SLF': ['SLF'],
        'OTHER': ['OTHER', 'UNKNOWN', 'CUSTOM']
    }
    
    def __init__(self):
        """Create necessary directories"""
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.RESULTS_DIR, exist_ok=True)
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        
        # Current analysis configuration (can be updated per analysis)
        self.current_ratio_base_width = self.DEFAULT_RATIO_BASE_WIDTH
        self.current_ratio_base_height = self.DEFAULT_RATIO_BASE_HEIGHT
    
    def validate_dimensions(self, width: float, height: float) -> Tuple[bool, str]:
        """
        Validate user input dimensions
        
        Returns:
            (is_valid, error_message)
        """
        
        try:
            width = float(width)
            height = float(height)
        except (ValueError, TypeError):
            return False, "Width and height must be valid numbers"
        
        if width <= 0 or height <= 0:
            return False, "Width and height must be positive numbers"
        
        if width < self.MIN_DIMENSION or height < self.MIN_DIMENSION:
            return False, f"Dimensions must be at least {self.MIN_DIMENSION}mm"
        
        if width > self.MAX_DIMENSION or height > self.MAX_DIMENSION:
            return False, f"Dimensions must not exceed {self.MAX_DIMENSION}mm"
        
        # Check for unusual aspect ratios
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio > 20:
            return False, f"Unusual aspect ratio detected ({aspect_ratio:.1f}:1). Please verify dimensions."
        
        return True, ""
    
    def set_current_ratio_base(self, width: float, height: float) -> bool:
        """
        Set current ratio base dimensions with validation
        
        Returns:
            True if successful, False if invalid
        """
        is_valid, error_msg = self.validate_dimensions(width, height)
        
        if not is_valid:
            print(f"❌ [SETTINGS] Invalid dimensions: {error_msg}")
            return False
        
        self.current_ratio_base_width = float(width)
        self.current_ratio_base_height = float(height)
        print(f"📊 [SETTINGS] Set ratio base dimensions: {width} x {height} mm")
        return True
    
    def get_current_ratio_base(self) -> Tuple[float, float]:
        """Get current ratio base dimensions"""
        return self.current_ratio_base_width, self.current_ratio_base_height
    
    def reset_ratio_base_to_default(self):
        """Reset ratio base to default values"""
        self.current_ratio_base_width = self.DEFAULT_RATIO_BASE_WIDTH
        self.current_ratio_base_height = self.DEFAULT_RATIO_BASE_HEIGHT
        print(f"🔄 [SETTINGS] Reset ratio base to default: {self.DEFAULT_RATIO_BASE_WIDTH} x {self.DEFAULT_RATIO_BASE_HEIGHT}")
    
    def get_dimension_suggestions(self, pkg_type: str = None) -> Dict[str, Tuple[float, float]]:
        """
        Get dimension suggestions based on package type (optional feature)
        """
        suggestions = {
            "Standard Small": (270, 90),
            "Standard Medium": (300, 95),
            "16DW Type": (600, 190),
            "Medium Size": (400, 150),
            "Large BGA": (800, 250),
            "Custom Small": (250, 85),
            "Custom Large": (700, 200)
        }
        
        return suggestions

# Global settings instance
settings = Settings()