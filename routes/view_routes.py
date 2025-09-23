"""
Fixed View Routes with Proper Template Handling
Date: 2025-08-29 01:31:34 UTC
User: HarrisonKuo47
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pytz
import json
import os
from datetime import datetime
import logging

from config.settings import settings
from models.data_models import analysis_results, handler_kit_metadata_cache

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_current_taiwan_time():
    """Get current time in Taiwan timezone (UTC+8)"""
    utc_time = datetime(2025, 8, 29, 1, 31, 34, tzinfo=pytz.UTC)
    taiwan_tz = pytz.timezone('Asia/Taipei')
    taiwan_time = utc_time.astimezone(taiwan_tz)
    return taiwan_time.strftime("%Y-%m-%d %H:%M:%S")

def format_file_size(file_size: int) -> str:
    """Format file size in human readable format"""
    if file_size > 1024*1024:
        return f"{file_size/(1024*1024):.1f} MB"
    elif file_size > 1024:
        return f"{file_size/1024:.1f} KB"
    else:
        return f"{file_size} B"

def load_handler_kit_cache_from_file():
    """Load handler kit cache directly from JSON file"""
    cache_file = os.path.join(settings.CACHE_DIR, "handler_kit_metadata.json")
    
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"✅ Loaded {len(data)} handler kits from cache file at 2025-08-29 01:31:34")
            return data
        else:
            logger.warning(f"❌ Cache file not found: {cache_file}")
            return {}
    except Exception as e:
        logger.error(f"❌ Error loading cache file: {e}")
        return {}

def calculate_time_ago(analysis_time_str):
    """Calculate time ago for analysis results"""
    try:
        if 'Z' in analysis_time_str:
            utc_time = datetime.fromisoformat(analysis_time_str.replace('Z', '+00:00'))
        else:
            utc_time = datetime.fromisoformat(analysis_time_str)
        
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=pytz.UTC)
        
        # Use current time: 2025-08-29 01:31:34 UTC
        now_utc = datetime(2025, 8, 29, 1, 31, 34, tzinfo=pytz.UTC)
        time_diff = now_utc - utc_time
        
        if time_diff.days > 0:
            return f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    except Exception as e:
        logger.error(f"⚠️ Error calculating time ago: {e}")
        return ""

@router.get("/results", response_class=HTMLResponse)
async def view_all_results(request: Request):
    """Display analysis results using results.html template"""
    logger.info(f"📊 HarrisonKuo47 accessing results page at 2025-08-29 01:31:34")
    
    try:
        # Check if analysis_results exists and has data
        if not analysis_results or len(analysis_results) == 0:
            logger.info(f"📊 No analysis results found for HarrisonKuo47")
            
            # ✅ FIX: Use results.html template with no_results flag instead of missing no_results.html
            return templates.TemplateResponse("results.html", {
                "request": request,
                "current_user": "HarrisonKuo47",
                "current_time": get_current_taiwan_time(),
                "sorted_analysis_results": [],
                "no_results": True,
                "app_version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
                "calculate_time_ago": calculate_time_ago
            })
        
        # Sort analysis results by execution time (newest first)
        def get_analysis_time(item):
            analysis_id, data = item
            try:
                analysis_time_str = data.get('analysis_time', '1970-01-01T00:00:00')
                if 'Z' in analysis_time_str:
                    utc_time = datetime.fromisoformat(analysis_time_str.replace('Z', '+00:00'))
                else:
                    utc_time = datetime.fromisoformat(analysis_time_str)
                if utc_time.tzinfo is None:
                    utc_time = utc_time.replace(tzinfo=pytz.UTC)
                return utc_time
            except Exception as e:
                logger.error(f"⚠️ Error parsing analysis time for {analysis_id}: {e}")
                return datetime(1970, 1, 1, tzinfo=pytz.UTC)
        
        sorted_analysis_results = sorted(
            analysis_results.items(), 
            key=get_analysis_time, 
            reverse=True
        )
        
        current_time = get_current_taiwan_time()
        logger.info(f"📊 Displaying {len(sorted_analysis_results)} analysis results for HarrisonKuo47")
        
        return templates.TemplateResponse("results.html", {
            "request": request,
            "sorted_analysis_results": sorted_analysis_results,
            "current_time": current_time,
            "current_user": "HarrisonKuo47",
            "no_results": False,
            "app_version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
            "calculate_time_ago": calculate_time_ago
        })
        
    except Exception as e:
        logger.error(f"❌ Error rendering results page for HarrisonKuo47: {str(e)}")
        
        # ✅ FIX: Return error state using results.html template
        return templates.TemplateResponse("results.html", {
            "request": request,
            "current_user": "HarrisonKuo47",
            "current_time": get_current_taiwan_time(),
            "sorted_analysis_results": [],
            "no_results": True,
            "error_message": f"Error loading results: {str(e)}",
            "app_version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
            "calculate_time_ago": calculate_time_ago
        })

@router.get("/compatible_kits", response_class=HTMLResponse)
async def view_compatible_kits(request: Request):
    """Display compatible kits using compatible_kits.html template"""
    logger.info(f"✅ HarrisonKuo47 accessing compatible kits page at 2025-08-29 01:31:34")
    
    try:
        # Check if analysis_results exists and has data
        if not analysis_results or len(analysis_results) == 0:
            logger.info(f"✅ No compatible kits found for HarrisonKuo47")
            
            # ✅ FIX: Use compatible_kits.html with no_results flag
            return templates.TemplateResponse("compatible_kits.html", {
                "request": request,
                "current_user": "HarrisonKuo47",
                "current_time": get_current_taiwan_time(),
                "sorted_analysis_results": [],
                "no_results": True,
                "total_compatible": 0,
                "message": "Run a column-filtered analysis first to see compatible handler kits.",
                "app_version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
                "calculate_time_ago": calculate_time_ago
            })
        
        # Sort analysis results by execution time (newest first)
        def get_analysis_time(item):
            analysis_id, data = item
            try:
                analysis_time_str = data.get('analysis_time', '1970-01-01T00:00:00')
                if 'Z' in analysis_time_str:
                    utc_time = datetime.fromisoformat(analysis_time_str.replace('Z', '+00:00'))
                else:
                    utc_time = datetime.fromisoformat(analysis_time_str)
                if utc_time.tzinfo is None:
                    utc_time = utc_time.replace(tzinfo=pytz.UTC)
                return utc_time
            except Exception as e:
                return datetime(1970, 1, 1, tzinfo=pytz.UTC)
        
        sorted_analysis_results = sorted(
            analysis_results.items(), 
            key=get_analysis_time, 
            reverse=True
        )
        
        current_time = get_current_taiwan_time()
        total_compatible = sum(len(data.get('suitable_kits', [])) for data in analysis_results.values())
        
        logger.info(f"✅ Displaying {total_compatible} compatible kits from {len(sorted_analysis_results)} analyses for HarrisonKuo47")
        
        return templates.TemplateResponse("compatible_kits.html", {
            "request": request,
            "sorted_analysis_results": sorted_analysis_results,
            "current_time": current_time,
            "current_user": "HarrisonKuo47",
            "total_compatible": total_compatible,
            "no_results": False,
            "app_version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
            "calculate_time_ago": calculate_time_ago
        })
        
    except Exception as e:
        logger.error(f"❌ Error rendering compatible kits page for HarrisonKuo47: {str(e)}")
        
        # ✅ FIX: Return error state using compatible_kits.html template
        return templates.TemplateResponse("compatible_kits.html", {
            "request": request,
            "current_user": "HarrisonKuo47",
            "current_time": get_current_taiwan_time(),
            "sorted_analysis_results": [],
            "no_results": True,
            "total_compatible": 0,
            "error_message": f"Error loading compatible kits: {str(e)}",
            "app_version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
            "calculate_time_ago": calculate_time_ago
        })

@router.get("/handler_kit_database", response_class=HTMLResponse)
async def view_handler_kit_database(request: Request):
    """Display Handler Kit database using handler_kit_database.html template"""
    logger.info(f"📋 HarrisonKuo47 accessing handler kit database at 2025-08-29 01:31:34")
    
    current_time = get_current_taiwan_time()
    
    # Load cache data from file
    cache_data = load_handler_kit_cache_from_file()
    total_kits = len(cache_data)
    
    logger.info(f"🔍 DEBUG: Loaded {total_kits} items from cache file")
    logger.info(f"🔍 DEBUG: Cache keys: {list(cache_data.keys())}")
    
    # Calculate PKG and LF type statistics
    pkg_stats = {}
    lf_stats = {}
    
    # Process handler kit data
    handler_kit_data = []
    
    # ✅ FIXED: Use cache_data instead of handler_kit_metadata_cache
    for filename, metadata in cache_data.items():
        logger.info(f"🔍 DEBUG: Processing {filename}")
        
        if 'error' not in metadata:
            pkg_type = metadata.get('pkg_type', 'OTHER')
            lf_type = metadata.get('lf_type', 'OTHER')
            
            # Update statistics
            pkg_stats[pkg_type] = pkg_stats.get(pkg_type, 0) + 1
            lf_stats[lf_type] = lf_stats.get(lf_type, 0) + 1
            
            # Prepare data for template
            device_type = metadata.get('device_type', '')
            if len(device_type) > 15:
                device_type = device_type[:15] + "..."
            
            handler_kit_data.append({
                'filename': filename,
                'pkg_type': pkg_type,
                'lf_type': lf_type,
                'device_type': device_type,
                'part_number': metadata.get('part_number', ''),
                'cup_count': metadata.get('vacuum_cup_count', 0),
                'element_count': metadata.get('element_count', 0),
                'handler_type': metadata.get('handler_type', 'cup'),
                'file_size': metadata.get('file_size', 0),
                'file_size_formatted': format_file_size(metadata.get('file_size', 0))
            })
            
            logger.info(f"✅ Added to display: {filename} - {pkg_type}/{lf_type} - {metadata.get('element_count', 0)} elements")
        else:
            logger.warning(f"⚠️ DEBUG: Skipping {filename} due to error: {metadata.get('error')}")
    
    logger.info(f"📋 DEBUG: Final results - {len(handler_kit_data)} valid handler kits")
    logger.info(f"📊 DEBUG: PKG stats: {pkg_stats}")
    logger.info(f"🔗 DEBUG: LF stats: {lf_stats}")
    
    return templates.TemplateResponse("handler_kit_database.html", {
        "request": request,
        "current_time": current_time,
        "current_user": "HarrisonKuo47",
        "total_kits": total_kits,
        "pkg_stats": pkg_stats,
        "lf_stats": lf_stats,
        "handler_kit_data": handler_kit_data,
        "app_version": settings.APP_VERSION if hasattr(settings, 'APP_VERSION') else "1.0.0",
        "build_date": settings.BUILD_DATE if hasattr(settings, 'BUILD_DATE') else "2025-08-29",
        "build_time": settings.BUILD_TIME if hasattr(settings, 'BUILD_TIME') else "01:31:34"
    })