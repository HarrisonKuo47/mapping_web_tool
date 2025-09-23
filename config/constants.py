"""
Constants and Type Definitions
Date: 2025-08-27 02:01:26 UTC
User: HarrisonKuo47
"""

# Package Type Definitions
PACKAGE_TYPES = {
    'TSSOP': ['TSSOP', 'TSOP'],
    'SOIC': ['SOIC', 'SOP', 'SSOP'],
    'QFP': ['QFP', 'LQFP', 'TQFP'],
    'QFN': ['QFN', 'VQFN'],
    'VSON': ['VSON'],
    'BGA': ['BGA', 'FBGA'],
    'OTHER': ['OTHER', 'UNKNOWN']
}

# Lead Frame Type Definitions
LF_TYPES = {
    'WLF': ['WLF', 'WAFER', 'WAFER LEVEL'],
    'HYDE': ['HYDE', 'HY-DE'],
    'SUHD': ['SUHD', 'SU-HD'],
    'SUHD_WLF': ['SUHD WLF', 'SUHD-WLF'],
    'RLF': ['RLF'],
    'SLF': ['SLF'],
    'OTHER': ['OTHER', 'UNKNOWN', 'CUSTOM']
}

# CSS Badge Classes
PKG_BADGE_CLASSES = {
    'TSSOP': 'pkg-TSSOP',
    'QFN': 'pkg-QFN',
    'SOIC': 'pkg-SOIC',
    'QFP': 'pkg-QFP',
    'VSON': 'pkg-VSON',
    'BGA': 'pkg-BGA',
    'OTHER': 'pkg-OTHER'
}

LF_BADGE_CLASSES = {
    'WLF': 'lf-WLF',
    'HYDE': 'lf-HYDE',
    'SUHD': 'lf-SUHD',
    'SUHD_WLF': 'lf-SUHD_WLF',
    'RLF': 'lf-RLF',
    'SLF': 'lf-SLF',
    'OTHER': 'lf-OTHER'
}

# File Type Mappings
ACCEPTED_DXF_EXTENSIONS = [".dxf"]
ACCEPTED_EXCEL_EXTENSIONS = [".xlsx", ".xls"]