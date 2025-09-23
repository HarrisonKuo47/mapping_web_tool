"""
JSON API Routes
Date: 2025-08-27 02:41:32 UTC
User: HarrisonKuo47
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime
import os

from config.settings import settings
from models.data_models import analysis_results, handler_kit_metadata_cache, convert_numpy_types
from mapping.extract_layers import extract_dxf_layers
from mapping.handler_kit_metadata import update_handler_kit_metadata, save_handler_kit_metadata_cache

router = APIRouter(prefix="/api")

@router.get("/leadframe/{dxf_filename}/layers")
async def get_leadframe_layers(dxf_filename: str):
    """Get available layers for a specific DXF file at mapping time"""
    try:
        lf_path = os.path.join(settings.UPLOAD_DIR, "leadframes", dxf_filename)
        if not os.path.exists(lf_path):
            raise HTTPException(status_code=404, detail=f"Lead Frame file '{dxf_filename}' not found")
        
        # Extract layers directly from DXF
        available_layers = extract_dxf_layers(lf_path)
        
        # Define common default layers
        default_layers = settings.DEFAULT_LAYERS
        
        # Filter defaults to only include existing layers
        existing_defaults = [layer for layer in default_layers if layer in available_layers]
        
        return JSONResponse({
            "status": "success",
            "dxf_file": dxf_filename,
            "available_layers": available_layers,
            "default_layers": existing_defaults,
            "total_layers": len(available_layers)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving layers: {str(e)}")

@router.get("/metadata/refresh")
async def refresh_metadata_cache():
    """Refresh the metadata cache for all Handler Kits"""
    try:
        hk_dir = os.path.join(settings.UPLOAD_DIR, "handlerkits")
        if not os.path.exists(hk_dir):
            return JSONResponse({"message": "No Handler Kit directory found", "refreshed_count": 0})
        
        refreshed_count = 0
        for file_path in os.listdir(hk_dir):
            if file_path.endswith(('.xlsx', '.xls')):
                full_path = os.path.join(hk_dir, file_path)
                update_handler_kit_metadata(full_path, force_update=True)
                refreshed_count += 1
        
        save_handler_kit_metadata_cache()
        
        return JSONResponse({
            "message": f"Metadata cache refreshed successfully",
            "refreshed_count": refreshed_count,
            "total_cached": len(handler_kit_metadata_cache),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return JSONResponse({
            "error": f"Error refreshing cache: {str(e)}"
        }, status_code=500)

@router.get("/results")
async def get_results_json():
    """Get all analysis results in JSON format"""
    return convert_numpy_types(analysis_results)

@router.get("/results/{analysis_id}")
async def get_specific_results_json(analysis_id: str):
    """Get specific analysis results in JSON format"""
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis results not found")
    return convert_numpy_types(analysis_results[analysis_id])

@router.delete("/results/clear")
async def clear_analysis_results():
    """Clear all analysis results and compatible kits"""
    global analysis_results
    
    try:
        # Count results before clearing
        total_analyses = len(analysis_results)
        total_compatible_kits = sum(len(data['suitable_kits']) for data in analysis_results.values())
        
        # Clear the results
        analysis_results.clear()
        
        # Optionally clean up result files
        cleanup_count = 0
        try:
            for file in os.listdir(settings.RESULTS_DIR):
                if file.endswith(('.png', '.xlsx')) and ('mapping' in file or 'overlap' in file):
                    os.remove(os.path.join(settings.RESULTS_DIR, file))
                    cleanup_count += 1
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up some result files: {e}")
        
        print(f"✅ Cleared {total_analyses} analyses with {total_compatible_kits} compatible kits and {cleanup_count} files")
        
        return JSONResponse({
            "status": "success",
            "message": "Analysis results cleared successfully",
            "cleared_analyses": total_analyses,
            "cleared_compatible_kits": total_compatible_kits,
            "cleaned_files": cleanup_count,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Error clearing results: {str(e)}"
        }, status_code=500)

@router.delete("/results/{analysis_id}")
async def clear_specific_analysis(analysis_id: str):
    """Clear a specific analysis result"""
    global analysis_results
    
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        # Remove the specific analysis
        removed_data = analysis_results.pop(analysis_id)
        
        return JSONResponse({
            "status": "success",
            "message": f"Analysis '{analysis_id}' cleared successfully",
            "removed_analysis": analysis_id,
            "removed_leadframe": removed_data.get('leadframe_name', ''),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Error clearing analysis: {str(e)}"
        }, status_code=500)

@router.get("/image/{filename}")
async def get_image(filename: str):
    """Serve visualization images"""
    image_path = os.path.join(settings.RESULTS_DIR, filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)

@router.get("/report/{filename}")
async def get_report(filename: str):
    """Serve Excel reports"""
    report_path = os.path.join(settings.RESULTS_DIR, filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_path)