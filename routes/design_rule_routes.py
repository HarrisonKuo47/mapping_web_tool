"""
Design Rule Checker Routes - Clean & Concise
Date: 2025-09-04 09:02:46 UTC+8
User: HarrisonKuo47

Following the pattern of existing route files with minimal but complete functionality.
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
import logging

from config.settings import settings
from design_rule.contour_check import (
    get_design_rules,
    check_adjusted_dimensions,
    check_adjusted_dimensions_with_vacuum_scanning,
    save_design_check_results,
    load_design_check_results,
    get_current_time_utc8
)
from design_rule.contour_data import (
    get_processed_leadframes,
    read_boundary_data,
    calculate_leadframe_dimensions,
    get_design_rule_summary,
    export_design_rule_report
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

# ========================================
# HTML PAGES
# ========================================

@router.get("/design_rule_checker", response_class=HTMLResponse)
async def design_rule_checker_page(request: Request):
    """Design Rule Checker main page"""
    
    current_time = get_current_time_utc8()
    logger.info(f"Design Rule Checker accessed by HarrisonKuo47 at {current_time}")
    
    try:
        processed_files = get_processed_leadframes(settings.UPLOAD_DIR)
        design_rules = get_design_rules()
        
        return templates.TemplateResponse("design_rule_checker.html", {
            "request": request,
            "processed_files": processed_files,
            "design_rules": design_rules,
            "current_user": "HarrisonKuo47",
            "current_time": current_time,
            "total_files": len(processed_files)
        })
        
    except Exception as e:
        logger.error(f"Error loading design rule checker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/design_rules_summary", response_class=HTMLResponse)
async def design_rules_summary_page(request: Request):
    """Design rules summary page"""
    
    current_time = get_current_time_utc8()
    
    try:
        summary = get_design_rule_summary(settings.UPLOAD_DIR)
        design_rules = get_design_rules()
        
        return templates.TemplateResponse("design_rules_summary.html", {
            "request": request,
            "summary": summary,
            "design_rules": design_rules,
            "current_user": "HarrisonKuo47",
            "current_time": current_time
        })
        
    except Exception as e:
        logger.error(f"Error loading summary page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# API ENDPOINTS
# ========================================

@router.post("/check_design_rules")
async def check_design_rules_api(
    leadframe_folder: str = Form(...),
    size_adjustment_factor: float = Form(0.5),
    required_vacuum_positions: int = Form(10),
    enable_vacuum_scanning: bool = Form(True)
):
    """Enhanced design rule check API"""
    
    current_time = get_current_time_utc8()
    logger.info(f"Design rule check for {leadframe_folder} by HarrisonKuo47 at {current_time}")
    
    try:
        # Validate parameters
        if not (0.01 <= size_adjustment_factor <= 10):
            return JSONResponse({
                "status": "error",
                "message": f"Invalid adjustment factor: {size_adjustment_factor}. Must be 0.01-10",
                "timestamp": current_time
            }, status_code=400)
        
        if not (5 <= required_vacuum_positions <= 20):
            return JSONResponse({
                "status": "error", 
                "message": f"Invalid vacuum positions: {required_vacuum_positions}. Must be 5-20",
                "timestamp": current_time
            }, status_code=400)
        
        # Get file paths
        analysis_folder = os.path.join(settings.UPLOAD_DIR, "temp_analysis", leadframe_folder)
        boundary_file = os.path.join(analysis_folder, f"{leadframe_folder}_boundary.xlsx")
        
        if not os.path.exists(boundary_file):
            return JSONResponse({
                "status": "error",
                "message": f"Boundary file not found for {leadframe_folder}",
                "timestamp": current_time
            }, status_code=404)
        
        # Read dimensions
        boundary_data = read_boundary_data(boundary_file)
        dimensions = calculate_leadframe_dimensions(boundary_data)
        
        # Find DXF and layer files for vacuum scanning
        dxf_file_path = None
        layer_names_file = None
        
        if enable_vacuum_scanning:
            # Find DXF file
            leadframes_dir = os.path.join(settings.UPLOAD_DIR, "leadframes")
            if os.path.exists(leadframes_dir):
                for file in os.listdir(leadframes_dir):  # Now looking in leadframes folder
                    if file.endswith('.dxf') and (
                        file.startswith(leadframe_folder.split('_')[0]) or 
                        leadframe_folder.startswith(file.replace('.dxf', ''))
                    ):
                        dxf_file_path = os.path.join(leadframes_dir, file)  # Use leadframes_dir
                        break
            
            layer_names_file = os.path.join(settings.UPLOAD_DIR, "layers", "layer.txt")
            
            # Disable if files not found
            if not dxf_file_path or not os.path.exists(dxf_file_path) or not os.path.exists(layer_names_file):
                enable_vacuum_scanning = False
                logger.warning(f"Vacuum scanning disabled - missing files for {leadframe_folder}")
        
        # Run appropriate check
        if enable_vacuum_scanning:
            check_result = check_adjusted_dimensions_with_vacuum_scanning(
                original_width=dimensions["width"],
                original_height=dimensions["height"],
                size_adjustment_factor=size_adjustment_factor,
                boundary_data=boundary_data,
                required_vacuum_positions=required_vacuum_positions,
                dxf_file_path=dxf_file_path,
                layer_names_file=layer_names_file
            )
        else:
            check_result = check_adjusted_dimensions(
                original_width=dimensions["width"],
                original_height=dimensions["height"],
                size_adjustment_factor=size_adjustment_factor
            )
            
            # Add vacuum info for consistency
            check_result["vacuum_position_check"] = {
                "status": "SKIPPED",
                "reason": "Files not available or disabled",
                "positions_found": 0,
                "required_positions": required_vacuum_positions
            }
        
        # Prepare response
        response_result = {
            "enhanced_check": check_result,
            "original_dimensions": dimensions,
            "leadframe_folder": leadframe_folder,
            "overall_status": check_result["status"],
            "vacuum_scanning_performed": enable_vacuum_scanning,
            "check_timestamp": current_time,
            "checked_by": "HarrisonKuo47"
        }
        
        # Save results
        try:
            saved_file = save_design_check_results(analysis_folder, leadframe_folder, response_result)
            response_result["saved_file"] = saved_file
        except Exception as save_error:
            logger.warning(f"Failed to save results: {save_error}")
        
        logger.info(f"Design rule check completed: {check_result['status']}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Design rule check completed for {leadframe_folder}",
            "check_result": response_result,
            "timestamp": current_time
        })
        
    except Exception as e:
        logger.error(f"Design rule check error: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error in design rules check: {str(e)}",
            "leadframe_folder": leadframe_folder,
            "timestamp": current_time
        }, status_code=500)

@router.get("/api/design_rules_summary")
async def get_design_rules_summary_api():
    """Get design rules summary API"""
    
    current_time = get_current_time_utc8()
    
    try:
        summary = get_design_rule_summary(settings.UPLOAD_DIR)
        return JSONResponse({
            "status": "success",
            "summary": summary,
            "timestamp": current_time
        })
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "timestamp": current_time
        }, status_code=500)

@router.get("/api/design_rule_results/{leadframe_folder}")
async def get_design_rule_results_api(leadframe_folder: str):
    """Get specific design rule results API"""
    
    current_time = get_current_time_utc8()
    
    try:
        analysis_folder = os.path.join(settings.UPLOAD_DIR, "temp_analysis", leadframe_folder)
        results = load_design_check_results(analysis_folder, leadframe_folder)
        
        if results is None:
            return JSONResponse({
                "status": "error",
                "message": f"No results found for {leadframe_folder}",
                "timestamp": current_time
            }, status_code=404)
        
        return JSONResponse({
            "status": "success",
            "results": results,
            "leadframe_folder": leadframe_folder,
            "timestamp": current_time
        })
        
    except Exception as e:
        logger.error(f"Error getting results: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "timestamp": current_time
        }, status_code=500)

@router.get("/api/processed_leadframes")
async def get_processed_leadframes_api():
    """Get list of processed lead frames API"""
    
    current_time = get_current_time_utc8()
    
    try:
        processed_files = get_processed_leadframes(settings.UPLOAD_DIR)
        return JSONResponse({
            "status": "success",
            "processed_files": processed_files,
            "total_count": len(processed_files),
            "timestamp": current_time
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "timestamp": current_time
        }, status_code=500)

# ========================================
# EXPORT & BATCH OPERATIONS
# ========================================

@router.get("/export/design_rules_report")
async def export_design_rules_report_api():
    """Export design rules report as Excel"""
    
    current_time = get_current_time_utc8()
    
    try:
        timestamp_str = current_time.replace(" ", "_").replace(":", "-")
        export_filename = f"design_rules_report_{timestamp_str}.xlsx"
        export_path = os.path.join(settings.UPLOAD_DIR, "exports", export_filename)
        
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        exported_file = export_design_rule_report(settings.UPLOAD_DIR, export_path)
        
        return FileResponse(
            path=exported_file,
            filename=export_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "timestamp": current_time
        }, status_code=500)

@router.post("/batch/check_all_leadframes")
async def batch_check_all_leadframes(
    size_adjustment_factor: float = Form(0.5),
    required_vacuum_positions: int = Form(10),
    enable_vacuum_scanning: bool = Form(True)
):
    """Batch check all processed lead frames"""
    
    current_time = get_current_time_utc8()
    logger.info(f"Batch check started by HarrisonKuo47 at {current_time}")
    
    try:
        processed_files = get_processed_leadframes(settings.UPLOAD_DIR)
        
        if not processed_files:
            return JSONResponse({
                "status": "error",
                "message": "No processed lead frames found",
                "timestamp": current_time
            }, status_code=404)
        
        batch_results = []
        success_count = 0
        error_count = 0
        
        for file_info in processed_files:
            leadframe_folder = file_info["folder_name"]
            
            try:
                dimensions = calculate_leadframe_dimensions(file_info["boundary_data"])
                
                # Determine vacuum scanning availability
                dxf_file_path = None
                layer_names_file = None
                vacuum_enabled = enable_vacuum_scanning
                
                if vacuum_enabled:
                    for file in os.listdir(settings.UPLOAD_DIR):
                        if file.endswith('.dxf') and (
                            file.startswith(leadframe_folder.split('_')[0]) or 
                            file.startswith(leadframe_folder)
                        ):
                            dxf_file_path = os.path.join(settings.UPLOAD_DIR, file)
                            break
                    
                    layer_names_file = os.path.join(settings.UPLOAD_DIR, "layers", "layer.txt")
                    
                    if not dxf_file_path or not os.path.exists(dxf_file_path) or not os.path.exists(layer_names_file):
                        vacuum_enabled = False
                
                # Run check
                if vacuum_enabled:
                    check_result = check_adjusted_dimensions_with_vacuum_scanning(
                        original_width=dimensions["width"],
                        original_height=dimensions["height"],
                        size_adjustment_factor=size_adjustment_factor,
                        boundary_data=file_info["boundary_data"],
                        required_vacuum_positions=required_vacuum_positions,
                        dxf_file_path=dxf_file_path,
                        layer_names_file=layer_names_file
                    )
                else:
                    check_result = check_adjusted_dimensions(
                        original_width=dimensions["width"],
                        original_height=dimensions["height"],
                        size_adjustment_factor=size_adjustment_factor
                    )
                
                # Save results
                save_design_check_results(file_info["folder_path"], leadframe_folder, {
                    "enhanced_check": check_result,
                    "original_dimensions": dimensions,
                    "leadframe_folder": leadframe_folder,
                    "overall_status": check_result["status"],
                    "vacuum_scanning_performed": vacuum_enabled,
                    "batch_processed": True,
                    "batch_timestamp": current_time
                })
                
                batch_results.append({
                    "leadframe_folder": leadframe_folder,
                    "status": "success",
                    "check_status": check_result["status"],
                    "vacuum_scanning_performed": vacuum_enabled
                })
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"Batch error for {leadframe_folder}: {e}")
                batch_results.append({
                    "leadframe_folder": leadframe_folder,
                    "status": "error",
                    "error": str(e)
                })
                error_count += 1
        
        logger.info(f"Batch completed: {success_count} success, {error_count} errors")
        
        return JSONResponse({
            "status": "success",
            "message": f"Batch completed: {success_count} success, {error_count} errors",
            "summary": {
                "total_processed": len(processed_files),
                "success_count": success_count,
                "error_count": error_count
            },
            "results": batch_results,
            "timestamp": current_time
        })
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "timestamp": current_time
        }, status_code=500)