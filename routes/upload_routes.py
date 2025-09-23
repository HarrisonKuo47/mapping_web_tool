"""
Enhanced Upload Routes with Scaling Ratio Support
Date: 2025-09-03 01:12:12 UTC
User: HarrisonKuo47
"""

from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
import os
import shutil
import pandas as pd
from datetime import datetime
import logging

from config.settings import settings
from mapping.handler_kit_metadata import (
    update_handler_kit_metadata, 
    save_handler_kit_metadata_cache,
    extract_lf_type_from_filename
)
from mapping.extract_layers import extract_dxf_layers, create_dynamic_layer_file
from mapping.extract_dxf_v2 import extract_dxf_shapes_for_file
from mapping.analyze_origin import coordinate_trans_single

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload_handlerkit")
async def upload_handlerkit(file: UploadFile = File(...)):
    """Upload Handler Kit with PKG & LF column metadata extraction"""
    
    logger.info(f"Handler Kit upload started: {file.filename} by HarrisonKuo47 at 2025-09-03 01:12:12")
    
    hk_dir = os.path.join(settings.UPLOAD_DIR, "handlerkits")
    os.makedirs(hk_dir, exist_ok=True)
    file_path = os.path.join(hk_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Extract and cache metadata using the complete parser
        metadata = update_handler_kit_metadata(file_path, force_update=True)
        save_handler_kit_metadata_cache()
        
        if 'error' in metadata:
            logger.error(f"Handler Kit upload failed: {metadata['error']}")
            return JSONResponse({
                "status": "error",
                "message": f"Error parsing Handler Kit '{file.filename}': {metadata['error']}",
                "filename": file.filename,
                "timestamp": "2025-09-03T01:12:12Z"
            }, status_code=400)
        
        logger.info(f"Handler Kit uploaded successfully: {file.filename}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Handler Kit '{file.filename}' uploaded successfully",
            "filename": file.filename,
            "metadata": {
                "pkg_type": metadata.get('pkg_type', 'OTHER'),
                "lf_type": metadata.get('lf_type', 'OTHER'),
                "device_type": metadata.get('device_type', ''),
                "part_number": metadata.get('part_number', ''),
                "handler_type": metadata.get('handler_type', 'cup'),
                "element_count": metadata.get('element_count', 0),
                "element_type": metadata.get('element_type', 'vacuum_cups')
            },
            "user": "HarrisonKuo47",
            "timestamp": "2025-09-03T01:12:12Z"
        })
        
    except Exception as e:
        logger.error(f"Handler Kit upload error: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": f"Error processing Handler Kit '{file.filename}': {str(e)}",
            "filename": file.filename,
            "timestamp": "2025-09-03T01:12:12Z"
        }, status_code=500)

@router.post("/upload_leadframe")
async def upload_leadframe(
    request: Request = None, 
    file: UploadFile = File(...), 
    response_format: str = Form("redirect"),
    scaling_ratio: float = Form(0.5)  # ✅ New parameter with default 1:2 ratio
):
    """Upload Lead Frame with configurable scaling ratio"""
    
    logger.info(f"Lead Frame upload started: {file.filename} by HarrisonKuo47 at 2025-09-03 01:12:12")
    logger.info(f"Using scaling ratio: {scaling_ratio} (DXF:{1/scaling_ratio:.1f} = Actual:1)")
    
    # Validate file type
    if not file.filename.lower().endswith('.dxf'):
        error_msg = "Invalid file type. Only DXF files are supported."
        logger.error(f"Invalid file type for Lead Frame: {file.filename}")
        
        if response_format == "json":
            return JSONResponse({
                "status": "error",
                "message": error_msg,
                "filename": file.filename,
                "timestamp": "2025-09-03T01:12:12Z"
            }, status_code=400)
        else:
            return RedirectResponse(url=f"/?error={error_msg}", status_code=302)
    
    # Validate scaling ratio
    if scaling_ratio <= 0 or scaling_ratio > 10:
        error_msg = f"Invalid scaling ratio: {scaling_ratio}. Must be between 0 and 10."
        logger.error(error_msg)
        
        if response_format == "json":
            return JSONResponse({
                "status": "error",
                "message": error_msg,
                "filename": file.filename,
                "timestamp": "2025-09-03T01:12:12Z"
            }, status_code=400)
        else:
            return RedirectResponse(url=f"/?error={error_msg}", status_code=302)
    
    # Save DXF file
    lf_dir = os.path.join(settings.UPLOAD_DIR, "leadframes")
    os.makedirs(lf_dir, exist_ok=True)
    file_path = os.path.join(lf_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Extract LF type from filename
        detected_lf_type = extract_lf_type_from_filename(file.filename)
        logger.info(f"Detected LF type: {detected_lf_type}")
        
        # Create layer file (simple default)
        layer_file = os.path.join(settings.UPLOAD_DIR, "layers", "layer.txt")
        if not os.path.exists(layer_file):
            os.makedirs(os.path.dirname(layer_file), exist_ok=True)
            with open(layer_file, 'w') as f:
                f.write("SH-01_OBJECT\nSH-01_DIM\nSH-01_PKG\n0")
        
        logger.info(f"Using layer file: {layer_file}")
        
        # Extract DXF shapes and run coordinate analysis
        summary_dir = os.path.join(settings.UPLOAD_DIR, "results", "shapes_summary")
        os.makedirs(summary_dir, exist_ok=True)
        summary_excel = extract_dxf_shapes_for_file(file_path, layer_file, summary_dir)
        
        logger.info(f"Shapes extracted to: {summary_excel}")
        
        # Create temp analysis structure
        dxf_name = os.path.splitext(file.filename)[0]
        temp_output_folder = os.path.join(settings.UPLOAD_DIR, "temp_analysis", dxf_name)
        os.makedirs(temp_output_folder, exist_ok=True)
        
        temp_shapes_file = os.path.join(temp_output_folder, f"{dxf_name}_shapes_summary.xlsx")
        shutil.copy2(summary_excel, temp_shapes_file)
        
        logger.info(f"Shapes file copied to: {temp_shapes_file}")
        
        # ✅ Run coordinate transformation with scaling ratio
        boundary_file = coordinate_trans_single(
            temp_shapes_file, 
            temp_output_folder, 
            dxf_name,
            scaling_ratio=scaling_ratio  # Pass the scaling ratio
        )
        
        logger.info(f"Boundary analysis completed with scaling ratio {scaling_ratio}: {boundary_file}")
        
        # Read boundary data for response
        try:
            boundary_df = pd.read_excel(boundary_file)
            boundary_data = {}
            for _, row in boundary_df.iterrows():
                boundary_data[row['Item']] = row['Value']
            
            # Use scaled dimensions
            width = round(boundary_data.get('x_max', 0) - boundary_data.get('x_min', 0), 2)
            height = round(boundary_data.get('y_max', 0) - boundary_data.get('y_min', 0), 2)
            
            # Also get raw dimensions for reference
            raw_width = round(boundary_data.get('raw_x_max', 0) - boundary_data.get('raw_x_min', 0), 2)
            raw_height = round(boundary_data.get('raw_y_max', 0) - boundary_data.get('raw_y_min', 0), 2)
            used_scaling_ratio = boundary_data.get('scaling_ratio', scaling_ratio)
            
            logger.info(f"DXF dimensions: {raw_width}x{raw_height}")
            logger.info(f"Actual dimensions: {width}x{height} (ratio: {used_scaling_ratio})")
            
        except Exception as e:
            logger.warning(f"Could not read boundary data: {e}")
            width, height = 0, 0
            raw_width, raw_height = 0, 0
            used_scaling_ratio = scaling_ratio
        
        # Prepare response
        response_data = {
            "status": "success",
            "message": f"Lead Frame '{file.filename}' uploaded and processed successfully",
            "filename": file.filename,
            "metadata": {
                "detected_lf_type": detected_lf_type,
                "boundary_analysis": "completed_with_scaling"
            },
            "processing_summary": {
                "actual_width": width,
                "actual_height": height,
                "dxf_width": raw_width,
                "dxf_height": raw_height,
                "scaling_ratio": used_scaling_ratio,
                "ratio_description": f"1:{1/used_scaling_ratio:.1f} (DXF:Actual)",
                "boundary_calculated": True
            },
            "user": "HarrisonKuo47",
            "timestamp": "2025-09-03T01:12:12Z"
        }
        
        if response_format == "json":
            return JSONResponse(response_data)
        else:
            success_msg = f"Lead Frame '{file.filename}' processed successfully! Actual size: {width}x{height}mm (DXF: {raw_width}x{raw_height}, ratio: 1:{1/used_scaling_ratio:.1f})"
            return RedirectResponse(url=f"/?success={success_msg}", status_code=302)
        
    except Exception as e:
        error_msg = f"Error processing Lead Frame: {str(e)}"
        logger.error(f"Lead Frame processing error: {str(e)}")
        
        if response_format == "json":
            return JSONResponse({
                "status": "error",
                "message": error_msg,
                "filename": file.filename,
                "timestamp": "2025-09-03T01:12:12Z"
            }, status_code=500)
        else:
            return RedirectResponse(url=f"/?error={error_msg}", status_code=302)

# API-only endpoints for compatibility
@router.post("/api/upload_handlerkit")
async def api_upload_handlerkit(file: UploadFile = File(...)):
    """API-only Handler Kit upload endpoint"""
    return await upload_handlerkit(file)

@router.post("/api/upload_leadframe")
async def api_upload_leadframe(file: UploadFile = File(...), scaling_ratio: float = Form(0.5)):
    """API-only Lead Frame upload endpoint with scaling ratio"""
    return await upload_leadframe(None, file, "json", scaling_ratio)