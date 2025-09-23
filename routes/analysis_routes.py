"""
Fixed Analysis Routes - Updated to handle user dimensions in existing endpoint
Date: 2025-09-05 01:11:50 UTC
User: HarrisonKuo47
"""

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import time
import os

from config.settings import settings
from models.data_models import AnalysisRequest, convert_numpy_types, analysis_results, handler_kit_metadata_cache
from services.mapping_service import mapping_service
from mapping.handler_kit_metadata import filter_handler_kits_by_types
from mapping.mapping import plot_dxf_and_vacuum_cups_with_overlap_detection
from mapping.mapping_chamber import plot_dxf_and_vacuum_chambers_with_overlap_detection

router = APIRouter()

@router.post("/run_column_filtered_mapping")
async def run_column_filtered_mapping(
    dxf_filename: str = Form(...),
    pkg_type: str = Form("ALL"),
    lf_type: str = Form("ALL"),
    early_termination: bool = Form(False),
    selected_layers: str = Form(""),
    # ADDED: User dimension parameters to existing endpoint
    user_width: float = Form(270.0),   # Default to 270 if not provided
    user_height: float = Form(90.0)    # Default to 90 if not provided
):
    """Enhanced existing endpoint to handle user dimensions"""
    try:
        start_time = time.time()
        
        print(f"🚀 [ANALYSIS] Analysis started by {settings.CURRENT_USER}")
        print(f"📅 [ANALYSIS] Date: 2025-09-05 01:11:50 UTC")
        print(f"📊 [ANALYSIS] User dimensions: {user_width} x {user_height} mm")
        print(f"📁 [ANALYSIS] Lead frame: {dxf_filename}")
        print(f"🎨 [ANALYSIS] Selected layers: {selected_layers}")
        print(f"🔍 [ANALYSIS] Filters: PKG={pkg_type}, LF={lf_type}")
        print(f"⚡ [ANALYSIS] Early termination: {early_termination}")
        
        # Validate user dimensions
        is_valid, error_msg = settings.validate_dimensions(user_width, user_height)
        if not is_valid:
            print(f"❌ [ANALYSIS] Invalid dimensions: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Invalid dimensions: {error_msg}")
        
        print(f"✅ [ANALYSIS] User dimensions validated: {user_width} x {user_height}")
        
        # Create analysis request
        request = AnalysisRequest(
            dxf_filename=dxf_filename,
            pkg_type=pkg_type,
            lf_type=lf_type,
            early_termination=early_termination,
            selected_layers=selected_layers
        )
        
        # Validate Lead Frame
        lf_path, exists = mapping_service.validate_leadframe(request.dxf_filename)
        if not exists:
            raise HTTPException(status_code=404, detail=f"Lead Frame file '{request.dxf_filename}' not found")
        
        # Parse and validate selected layers
        valid_layers, invalid_layers = mapping_service.validate_layers(lf_path, request.selected_layers)
        
        if invalid_layers:
            print(f"⚠️ [ANALYSIS] These layers don't exist in DXF: {invalid_layers}")
        
        if not valid_layers:
            raise HTTPException(status_code=400, detail="No valid layers selected for analysis")
        
        print(f"✅ [ANALYSIS] Using valid layers: {valid_layers}")
        
        # Create dynamic layer file for this analysis
        dxf_name = os.path.splitext(request.dxf_filename)[0]
        analysis_id = f"{dxf_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        dynamic_layer_file = mapping_service.create_dynamic_layer_file(analysis_id, valid_layers)
        
        # Get boundary info
        boundary_data = mapping_service.load_boundary_info(dxf_name)
        print(f"📊 [ANALYSIS] Lead frame boundary: {boundary_data.width:.2f} x {boundary_data.height:.2f} mm")
        
        # Set user dimensions as current ratio base
        settings.set_current_ratio_base(user_width, user_height)
        print(f"📊 [ANALYSIS] Set ratio base to user input: {user_width} x {user_height}")
        
        # Get transformation summary
        transform_summary = mapping_service.get_transformation_summary(boundary_data, user_width, user_height)
        print(f"📊 [ANALYSIS] Transformation ratios: W={transform_summary['transformation_ratios']['width_ratio']:.3f}, H={transform_summary['transformation_ratios']['height_ratio']:.3f}")
        
        # Apply PKG and LF type filtering
        print(f"🔍 [ANALYSIS] Filtering Handler Kits (PKG: {request.pkg_type}, LF: {request.lf_type})...")
        filtering_start = time.time()
        
        filtered_kits = filter_handler_kits_by_types(
            pkg_type_filter=request.pkg_type if request.pkg_type != "ALL" else None,
            lf_type_filter=request.lf_type if request.lf_type != "ALL" else None
        )
        
        filtering_time = time.time() - filtering_start
        
        print(f"✅ [ANALYSIS] Column-based filtering: {len(filtered_kits)}/{len(handler_kit_metadata_cache)} Handler Kits passed ({filtering_time:.2f}s)")
        
        if not filtered_kits:
            # Clean up dynamic layer file
            if os.path.exists(dynamic_layer_file):
                os.remove(dynamic_layer_file)
                
            print(f"❌ [ANALYSIS] No kits matched filtering criteria for user {settings.CURRENT_USER}")
            
            return JSONResponse({
                "status": "success",
                "analysis_id": analysis_id,
                "message": "No Handler Kits matched the PKG/LF column filtering criteria",
                "leadframe": request.dxf_filename,
                "user_dimensions": {"width": user_width, "height": user_height},
                "selected_layers": valid_layers,
                "filters_applied": {"pkg_type": request.pkg_type, "lf_type": request.lf_type},
                "total_kits_in_database": len(handler_kit_metadata_cache),
                "kits_after_filtering": 0,
                "suitable_kits_found": 0,
                "processing_time": time.time() - start_time,
            })
        
        # Run analysis on filtered kits
        print(f"🔧 [ANALYSIS] Analyzing {len(filtered_kits)} Handler Kits with user dimensions...")
        analysis_start = time.time()
        
        results = []
        suitable_kits = []
        
        hk_dir = os.path.join(settings.UPLOAD_DIR, "handlerkits")
        
        for kit_filename in filtered_kits:
            kit_path = os.path.join(hk_dir, kit_filename)
            if not os.path.exists(kit_path):
                continue
                
            base_name = f"{dxf_name}_{os.path.splitext(kit_filename)[0]}"
            
            try:
                # Get cached metadata
                kit_metadata = handler_kit_metadata_cache.get(kit_filename, {})
                
                # Parse coordinates using unified parser from service
                print(f"🔧 [ANALYSIS] Parsing {kit_filename} with unified parser...")
                df_parsed, pkg_type_parsed, lf_type_parsed, handler_type = mapping_service.parse_handler_kit_excel_unified(kit_path)
                
                if df_parsed is None:
                    print(f"❌ [ANALYSIS] Failed to parse {kit_filename} - {handler_type} data")
                    results.append({
                        "handlerkit": kit_filename,
                        "handlerkit_name": os.path.splitext(kit_filename)[0],
                        "error": f"Could not parse Handler Kit {handler_type} data",
                        "is_suitable": False,
                        "pkg_type": kit_metadata.get('pkg_type', 'OTHER'),
                        "lf_type": kit_metadata.get('lf_type', 'OTHER'),
                        "handler_type": handler_type
                    })
                    continue
                
                print(f"✅ [ANALYSIS] Successfully parsed {kit_filename} - {handler_type} with {len(df_parsed)} elements")
                
                # Transform coordinates based on type using user dimensions
                if handler_type == 'chamber':
                    df_transformed = mapping_service.transform_vacuum_chambers_with_user_input(
                        df_parsed, boundary_data, user_width, user_height
                    )
                    shapes_for_analysis = mapping_service.convert_chambers_to_shapes(df_transformed)
                    element_count = len(df_parsed)
                    
                else:  # handler_type == 'cup'
                    df_transformed = mapping_service.transform_handler_kit_coordinates_with_user_input(
                        df_parsed, boundary_data, user_width, user_height
                    )
                    shapes_for_analysis = df_transformed
                    element_count = len(df_parsed)
                
                # Save transformed data
                transformed_hk_path = os.path.join(settings.RESULTS_DIR, f"{base_name}_transformed.xlsx")
                shapes_for_analysis.to_excel(transformed_hk_path, index=False)
                
                output_png = os.path.join(settings.RESULTS_DIR, f"{base_name}_mapping.png")
                overlap_report = os.path.join(settings.RESULTS_DIR, f"{base_name}_overlap.xlsx")
                
                # Run overlap detection with dynamic layer file
                print(f"🔧 [ANALYSIS] Running overlap detection for {kit_filename}...")
                if handler_type == 'chamber':
                    df_overlap = plot_dxf_and_vacuum_chambers_with_overlap_detection(
                        dxf_file=str(lf_path),
                        layer_names_file=dynamic_layer_file,
                        chamber_excel_file=transformed_hk_path,
                        output_png=output_png,
                        overlap_report_file=overlap_report,
                        enable_overlap_detection=True
                    )
                else:
                    df_overlap = plot_dxf_and_vacuum_cups_with_overlap_detection(
                        dxf_file=str(lf_path),
                        layer_names_file=dynamic_layer_file,
                        vacuum_excel_file=transformed_hk_path,
                        output_png=output_png,
                        overlap_report_file=overlap_report,
                        enable_overlap_detection=True
                    )
                
                # Analyze results
                is_suitable = False
                overlap_count = 0
                
                if df_overlap is not None and not df_overlap.empty:
                    overlap_mask = df_overlap['Is_Overlapping'] == False
                    is_suitable = bool(overlap_mask.all())
                    overlap_count = int(df_overlap['Is_Overlapping'].sum())
                    
                    if is_suitable:
                        suitable_kits.append({
                            "name": os.path.splitext(kit_filename)[0],
                            "file": kit_filename,
                            "total_elements": element_count,
                            "total_cups": element_count,
                            "overlap_count": 0,
                            "pkg_type": kit_metadata.get('pkg_type', 'OTHER'),
                            "lf_type": kit_metadata.get('lf_type', 'OTHER'),
                            "device_type": kit_metadata.get('device_type', ''),
                            "handler_type": handler_type,
                            "user_dimensions_used": f"{user_width}x{user_height}mm"
                        })
                        print(f"✅ [ANALYSIS] {kit_filename} is suitable - no overlaps!")
                    else:
                        print(f"❌ [ANALYSIS] {kit_filename} has {overlap_count} overlaps")
                
                results.append({
                    "handlerkit": kit_filename,
                    "handlerkit_name": os.path.splitext(kit_filename)[0],
                    "output_image": os.path.basename(output_png) if os.path.exists(output_png) else None,
                    "output_image_path": f"/static/{os.path.basename(output_png)}" if os.path.exists(output_png) else None,
                    "overlap_report": os.path.basename(overlap_report) if os.path.exists(overlap_report) else None,
                    "overlap_report_path": f"/static/{os.path.basename(overlap_report)}" if os.path.exists(overlap_report) else None,
                    "is_suitable": is_suitable,
                    "total_elements": element_count,
                    "total_cups": element_count,
                    "overlap_count": overlap_count,
                    "overlap_rate": round((overlap_count / element_count * 100) if element_count > 0 else 0, 2),
                    "pkg_type": kit_metadata.get('pkg_type', 'OTHER'),
                    "lf_type": kit_metadata.get('lf_type', 'OTHER'),
                    "device_type": kit_metadata.get('device_type', ''),
                    "handler_type": handler_type,
                    "user_dimensions_used": f"{user_width}x{user_height}mm"
                })
                
                # Clean up
                if os.path.exists(transformed_hk_path):
                    os.remove(transformed_hk_path)
                
                # Early termination
                if request.early_termination and len(suitable_kits) >= 1:
                    print(f"⚡ [ANALYSIS] Early termination: Found {len(suitable_kits)} suitable kits")
                    break
                    
            except Exception as e:
                print(f"❌ [ANALYSIS] Error processing {kit_filename}: {str(e)}")
                kit_metadata = handler_kit_metadata_cache.get(kit_filename, {})
                results.append({
                    "handlerkit": kit_filename,
                    "handlerkit_name": os.path.splitext(kit_filename)[0],
                    "error": str(e),
                    "is_suitable": False,
                    "pkg_type": kit_metadata.get('pkg_type', 'OTHER'),
                    "lf_type": kit_metadata.get('lf_type', 'OTHER'),
                    "handler_type": kit_metadata.get('handler_type', 'cup')
                })
        
        # Clean up dynamic layer file
        if os.path.exists(dynamic_layer_file):
            os.remove(dynamic_layer_file)
        
        analysis_time = time.time() - analysis_start
        total_time = time.time() - start_time
        
        # Store results with layer information
        analysis_results[analysis_id] = convert_numpy_types({
            "leadframe": request.dxf_filename,
            "leadframe_name": dxf_name,
            "user_dimensions": {"width": user_width, "height": user_height},
            "total_kits_tested": len(filtered_kits),
            "total_kits_in_database": len(handler_kit_metadata_cache),
            "suitable_kits": suitable_kits,
            "all_results": results,
            "selected_layers": valid_layers,
            "invalid_layers": invalid_layers,
            "filters_applied": {
                "pkg_type": request.pkg_type,
                "lf_type": request.lf_type,
                "selected_layers": valid_layers,
                "early_termination": request.early_termination,
                "filter_method": "column_based_unified_with_custom_layers_and_user_dimensions"
            },
            "performance_metrics": {
                "filtering_time": round(filtering_time, 2),
                "analysis_time": round(analysis_time, 2),
                "total_time": round(total_time, 2),
                "efficiency_gain": round((1 - len(filtered_kits) / len(handler_kit_metadata_cache)) * 100, 1) if handler_kit_metadata_cache else 0
            },
            "summary": {
                "suitable_count": len(suitable_kits),
                "total_tested": len(filtered_kits),
                "success_rate": round((len(suitable_kits) / len(filtered_kits) * 100) if filtered_kits else 0, 1)
            }
        })

        print(f"🎉 [ANALYSIS] Analysis completed with user dimensions: {len(suitable_kits)}/{len(filtered_kits)} suitable kits found in {total_time:.2f}s")
        print(f"👤 [ANALYSIS] Analysis performed by: {settings.CURRENT_USER}")
        
        return convert_numpy_types({
            "status": "success",
            "analysis_id": analysis_id,
            "leadframe": request.dxf_filename,
            "user_dimensions": {"width": user_width, "height": user_height},
            "selected_layers": valid_layers,
            "invalid_layers": invalid_layers,
            "suitable_kits_found": len(suitable_kits),
            "suitable_kits": suitable_kits,
            "performance_summary": {
                "total_time": round(total_time, 2),
                "filtering_time": round(filtering_time, 2),
                "analysis_time": round(analysis_time, 2),
                "kits_filtered_out": len(handler_kit_metadata_cache) - len(filtered_kits),
                "efficiency_gain": f"{round((1 - len(filtered_kits) / len(handler_kit_metadata_cache)) * 100, 1)}%" if handler_kit_metadata_cache else "0%"
            },
            "filters_applied": {
                "pkg_type": request.pkg_type,
                "lf_type": request.lf_type,
                "selected_layers": valid_layers,
                "filter_method": "PKG & LF columns + Custom Layers + User Dimensions"
            },
            "view_results_url": f"/results/{analysis_id}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [ANALYSIS] Unified mapping error: {e}")
        print(f"❌ [ANALYSIS] Error occurred for user: {settings.CURRENT_USER}")
        raise HTTPException(status_code=500, detail=f"Unified analysis failed: {str(e)}")