"""
Vacuum Position Scanner - FINAL FIX with Comprehensive Visualization
Date: 2025-09-05 06:59:28 UTC
User: HarrisonKuo47

FINAL FIX: Scan at the correct Y coordinate where lead frame pads actually exist
ADDED: Comprehensive matplotlib visualization to verify functionality
"""

import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Circle
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import logging
import json

# Configure logging
logger = logging.getLogger(__name__)

def read_selected_layers(layer_names_file: str) -> List[str]:
    """Read layer names from layer.txt file"""
    try:
        if not os.path.exists(layer_names_file):
            return []
        with open(layer_names_file, 'r', encoding='utf-8') as file:
            layers = [line.strip() for line in file if line.strip()]
        return layers
    except Exception as e:
        print(f"❌ [DEBUG] Failed to read layer file: {e}")
        return []

def read_boundary_data_from_excel(boundary_file_path: str) -> Dict[str, float]:
    """Read boundary data from Excel file"""
    try:
        if not os.path.exists(boundary_file_path):
            raise FileNotFoundError(f"Boundary file not found: {boundary_file_path}")
        df = pd.read_excel(boundary_file_path)
        boundary_data = {}
        for _, row in df.iterrows():
            item = str(row['Item']).strip()
            value = float(row['Value'])
            boundary_data[item] = value
        return boundary_data
    except Exception as e:
        print(f"❌ [DEBUG] Failed to read boundary data: {e}")
        raise

def world_to_pixel(world_x, world_y, ax, canvas):
    """Convert world coordinates to pixel coordinates"""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    width, height = canvas.get_width_height()
    pixel_x = int((world_x - xlim[0]) / (xlim[1] - xlim[0]) * width)
    pixel_y = int(height - (world_y - ylim[0]) / (ylim[1] - ylim[0]) * height)
    return pixel_x, pixel_y

def create_vacuum_cup_mask(pixel_x: int, pixel_y: int, shape: str, size: str, 
                         mask_shape: Tuple[int, int], ax, canvas) -> np.ndarray:
    """Create vacuum cup mask"""
    try:
        height, width = mask_shape
        mask = np.zeros((height, width), dtype=np.uint8)
        
        if shape == 'circle':
            diameter = float(size)
            _, canvas_width = canvas.get_width_height()
            x_min, x_max = ax.get_xlim()
            pixels_per_mm = canvas_width / (x_max - x_min)
            radius_pixels = int(diameter / 2 * pixels_per_mm)
            cv2.circle(mask, (pixel_x, pixel_y), radius_pixels, 255, -1)
        return mask
    except Exception as e:
        print(f"❌ [DEBUG] Vacuum cup mask creation failed: {e}")
        return np.zeros(mask_shape, dtype=np.uint8)

def create_leadframe_profile_from_dxf(dxf_file_path: str, layer_names_file: str, 
                                    boundary_data: Dict[str, float], 
                                    resolution_dpi: int = 300) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Create leadframe profile mask"""
    try:
        layer_names = read_selected_layers(layer_names_file)
        if not layer_names:
            raise ValueError("No layer names found")
        
        doc = ezdxf.readfile(dxf_file_path)
        msp = doc.modelspace()
        
        x_min = boundary_data.get('x_min', 0)
        x_max = boundary_data.get('x_max', 0)
        y_min = boundary_data.get('y_min', 0)
        y_max = boundary_data.get('y_max', 0)
        
        # High resolution figure
        fig_detect = plt.figure(figsize=(24, 20), dpi=400)
        ax_detect = fig_detect.add_axes([0, 0, 1, 1])
        fig_detect.patch.set_facecolor('black')
        ax_detect.set_facecolor('black')
        
        # Configure layers
        for layer in doc.layers:
            layer.off()
        found_layers = []
        for lname in layer_names:
            if lname in doc.layers:
                doc.layers.get(lname).on()
                found_layers.append(lname)
        
        # Render DXF
        ctx = RenderContext(doc)
        out_detect = MatplotlibBackend(ax_detect)
        Frontend(ctx, out_detect).draw_layout(msp, finalize=True)
        
        ax_detect.set_xlim(x_min, x_max)
        ax_detect.set_ylim(y_min, y_max)
        ax_detect.set_aspect('equal')
        ax_detect.set_axis_off()
        
        # Convert to image
        canvas_detect = FigureCanvasAgg(fig_detect)
        canvas_detect.draw()
        dxf_image = np.frombuffer(canvas_detect.tostring_rgb(), dtype=np.uint8)
        dxf_image = dxf_image.reshape(canvas_detect.get_width_height()[::-1] + (3,))
        
        # Create mask
        dxf_gray = cv2.cvtColor(dxf_image, cv2.COLOR_RGB2GRAY)
        dxf_mask = (dxf_gray > 1).astype(np.uint8) * 255
        
        # Calculate metrics
        width_pixels, height_pixels = canvas_detect.get_width_height()
        width_mm = x_max - x_min
        height_mm = y_max - y_min
        pixels_per_mm = (width_pixels/width_mm + height_pixels/height_mm) / 2
        coverage_percent = (np.sum(dxf_mask > 0) / (dxf_mask.shape[0] * dxf_mask.shape[1])) * 100
        
        profile_info = {
            "width_mm": round(float(width_mm), 2),
            "height_mm": round(float(height_mm), 2),
            "width_pixels": int(width_pixels),
            "height_pixels": int(height_pixels),
            "pixels_per_mm": round(float(pixels_per_mm), 2),
            "white_pixel_coverage": round(float(coverage_percent), 2),
            "rendered_layers": found_layers,
            "resolution_dpi": int(400),
            "ax_detect": ax_detect,
            "canvas_detect": canvas_detect,
            "original_boundary_coords": {
                "x_min": round(float(x_min), 2),
                "x_max": round(float(x_max), 2),
                "y_min": round(float(y_min), 2),
                "y_max": round(float(y_max), 2)
            }
        }
        
        return dxf_mask, profile_info
        
    except Exception as e:
        print(f"❌ [DEBUG] Profile creation failed: {e}")
        raise

def find_optimal_scan_y_coordinate(profile_mask: np.ndarray, profile_info: Dict[str, Any]) -> float:
    """CRITICAL FIX: Find the Y coordinate where lead frame pads actually exist"""
    print(f"🔍 [CRITICAL] Finding optimal scan Y coordinate...")
    
    try:
        # Get boundary coordinates
        coords = profile_info["original_boundary_coords"]
        y_min_mm = coords["y_min"]
        y_max_mm = coords["y_max"]
        height_pixels = profile_info["height_pixels"]
        
        # Analyze profile mask row by row to find where geometry exists
        row_coverage = []
        for y_pixel in range(height_pixels):
            row = profile_mask[y_pixel, :]
            coverage = np.sum(row > 0) / len(row) * 100
            row_coverage.append(coverage)
        
        # Convert pixel Y to world Y coordinates
        y_world_coords = []
        optimal_coverages = []
        
        for y_pixel, coverage in enumerate(row_coverage):
            # Convert pixel Y to world Y
            y_world = y_max_mm - (y_pixel / height_pixels) * (y_max_mm - y_min_mm)
            y_world_coords.append(y_world)
            
            # Look for significant coverage (indicating lead frame geometry)
            if coverage > 1.0:  # At least 1% coverage in this row
                optimal_coverages.append((y_world, coverage, y_pixel))
        
        if optimal_coverages:
            # Sort by coverage and pick the row with highest coverage
            optimal_coverages.sort(key=lambda x: x[1], reverse=True)
            best_y_world, best_coverage, best_y_pixel = optimal_coverages[0]
            
            print(f"✅ [CRITICAL] Optimal scan Y found:")
            print(f"    🎯 World Y: {best_y_world:.1f}mm")
            print(f"    🎯 Coverage: {best_coverage:.2f}%") 
            print(f"    🎯 Pixel Y: {best_y_pixel}")
            
            # Show top 5 candidates
            print(f"📊 [CRITICAL] Top Y coordinate candidates:")
            for i, (y_world, coverage, y_pixel) in enumerate(optimal_coverages[:5]):
                print(f"    #{i+1}: y={y_world:.1f}mm (coverage={coverage:.2f}%, pixel={y_pixel})")
            
            return best_y_world
        else:
            # Fallback to upper area
            fallback_y = y_max_mm - 2.7
            print(f"⚠️ [CRITICAL] No optimal Y found, using fallback: {fallback_y:.1f}mm")
            return fallback_y
            
    except Exception as e:
        print(f"❌ [CRITICAL] Error finding optimal scan Y: {e}")
        return y_max_mm - 2.7  # Fallback

def scan_vacuum_positions_with_optimal_y(profile_mask: np.ndarray, profile_info: Dict[str, Any], 
                                        vacuum_diameter_mm: float, required_positions: int,
                                        adjustment_factor: float,
                                        scan_unit_mm: float = 0.5,
                                        overlap_tolerance_pixels: int = 0,
                                        min_vacuum_spacing_mm: float = 3.0) -> Dict[str, Any]:
    """CRITICAL FIX: Scan at the optimal Y coordinate where lead frame pads exist"""
    
    print(f"🔍 [CRITICAL] ===== Scanning at OPTIMAL Y Coordinate =====")
    print(f"🔍 [CRITICAL] User: HarrisonKuo47")
    print(f"🔍 [CRITICAL] Date: 2025-09-05 06:59:28 UTC")
    
    try:
        adjusted_vacuum_diameter = vacuum_diameter_mm / adjustment_factor
        pixels_per_mm = profile_info["pixels_per_mm"]
        scan_unit_pixels = max(1, int(scan_unit_mm * pixels_per_mm))
        min_spacing_pixels = int(min_vacuum_spacing_mm * pixels_per_mm)
        
        # Get references for coordinate conversion
        ax_detect = profile_info["ax_detect"]
        canvas_detect = profile_info["canvas_detect"]
        
        # Get boundary coordinates
        original_coords = profile_info["original_boundary_coords"]
        x_min_mm = original_coords["x_min"]
        x_max_mm = original_coords["x_max"]
        y_min_mm = original_coords["y_min"]
        y_max_mm = original_coords["y_max"]
        
        # CRITICAL FIX: Find the optimal Y coordinate where geometry actually exists
        optimal_scan_y_mm = find_optimal_scan_y_coordinate(profile_mask, profile_info)
        
        print(f"✅ [CRITICAL] Using OPTIMAL scan Y: {optimal_scan_y_mm:.1f}mm")
        print(f"✅ [CRITICAL] Profile coverage: {profile_info['white_pixel_coverage']:.1f}%")
        print(f"✅ [CRITICAL] Overlap tolerance: {overlap_tolerance_pixels} pixels (ZERO = reject ANY overlap)")
        
        # Linear scanning from right to left at OPTIMAL Y
        x_start_mm = x_max_mm
        x_end_mm = x_min_mm
        
        valid_positions = []
        scan_positions = []
        counter = 0
        scan_counter = 0
        
        current_x_mm = x_start_mm
        
        while current_x_mm >= x_end_mm and counter < required_positions:
            scan_counter += 1
            
            # Check spacing to existing positions
            too_close_to_existing = False
            if valid_positions:
                for existing_pos in valid_positions:
                    existing_x_mm = existing_pos["x_mm_original"]
                    existing_y_mm = existing_pos["y_mm_original"]
                    
                    distance_mm = np.sqrt((current_x_mm - existing_x_mm)**2 + (optimal_scan_y_mm - existing_y_mm)**2)
                    
                    if distance_mm < min_vacuum_spacing_mm:
                        too_close_to_existing = True
                        break
            
            if too_close_to_existing:
                current_x_mm -= scan_unit_mm
                continue
            
            # CRITICAL: Overlap detection at OPTIMAL Y coordinate
            is_overlapping = False
            overlap_count = 0
            
            try:
                # Convert world to pixel
                pixel_x, pixel_y = world_to_pixel(current_x_mm, optimal_scan_y_mm, ax_detect, canvas_detect)
                
                # Create vacuum cup mask
                cup_mask = create_vacuum_cup_mask(
                    pixel_x, pixel_y, 'circle', str(adjusted_vacuum_diameter), 
                    profile_mask.shape, ax_detect, canvas_detect
                )
                
                # CRITICAL: Overlap detection using SAME logic as successful function
                overlap_pixels = np.logical_and(profile_mask > 0, cup_mask > 0)
                overlap_count = np.sum(overlap_pixels)
                is_overlapping = overlap_count > overlap_tolerance_pixels
                
                # Debug for first few positions
                if scan_counter <= 10:
                    cup_mask_pixels = np.sum(cup_mask > 0)
                    profile_pixels_in_region = np.sum(profile_mask[cup_mask > 0] > 0) if np.any(cup_mask > 0) else 0
                    
                    print(f"    🔍 [CRITICAL] Scan #{scan_counter} at ({current_x_mm:.1f}, {optimal_scan_y_mm:.1f})mm:")
                    print(f"        Pixel: ({pixel_x}, {pixel_y})")
                    print(f"        Vacuum mask: {cup_mask_pixels} pixels")
                    print(f"        Profile pixels in region: {profile_pixels_in_region}")
                    print(f"        Overlap pixels: {overlap_count}")
                    print(f"        Is overlapping: {is_overlapping}")
                
            except Exception as e:
                print(f"  ❌ [CRITICAL] Overlap detection error at x={current_x_mm:.1f}mm: {e}")
                is_overlapping = True
                overlap_count = 999
            
            # Calculate adjusted coordinates
            x_mm_adjusted = current_x_mm * adjustment_factor
            y_mm_adjusted = optimal_scan_y_mm * adjustment_factor
            
            # Record scan position
            scan_positions.append({
                "x_mm_original": round(float(current_x_mm), 2),
                "y_mm_original": round(float(optimal_scan_y_mm), 2),
                "x_mm_adjusted": round(float(x_mm_adjusted), 2),
                "y_mm_adjusted": round(float(y_mm_adjusted), 2),
                "overlap_count": int(overlap_count),
                "is_overlapping": bool(is_overlapping),
                "too_close_to_existing": bool(too_close_to_existing)
            })
            
            # Check if valid position
            if is_overlapping:
                # OVERLAPS - reject and continue
                if scan_counter <= 20:
                    print(f"    ❌ [CRITICAL] Position x={current_x_mm:.1f}mm REJECTED: {overlap_count} overlap pixels > {overlap_tolerance_pixels}")
            else:
                # VALID position found!
                counter += 1
                valid_positions.append({
                    "position_number": int(counter),
                    "x_mm_original": round(float(current_x_mm), 2),
                    "y_mm_original": round(float(optimal_scan_y_mm), 2),
                    "x_mm_adjusted": round(float(x_mm_adjusted), 2),
                    "y_mm_adjusted": round(float(y_mm_adjusted), 2),
                    "vacuum_diameter_mm": round(float(adjusted_vacuum_diameter), 2),
                    "overlap_count": int(overlap_count)
                })
                
                print(f"🎯 [CRITICAL] VALID position #{counter}: x={current_x_mm:.1f}mm → ({x_mm_adjusted:.1f}, {y_mm_adjusted:.1f})mm adjusted, overlap={overlap_count} pixels")
            
            # Move left
            current_x_mm -= scan_unit_mm
        
        # Final results
        positions_found = len(valid_positions)
        status = "PASS" if positions_found >= required_positions else "FAIL"
        overlapped_count = len([p for p in scan_positions if p["is_overlapping"]])
        
        print(f"✅ [CRITICAL] OPTIMAL Y scan completed:")
        print(f"  📊 [CRITICAL] Scan Y coordinate: {optimal_scan_y_mm:.1f}mm")
        print(f"  📊 [CRITICAL] Total scans: {scan_counter}")
        print(f"  📊 [CRITICAL] Valid positions: {positions_found}/{required_positions}")
        print(f"  📊 [CRITICAL] Overlapped (rejected): {overlapped_count}")
        print(f"  📊 [CRITICAL] Status: {status}")
        
        result = {
            "status": str(status),
            "positions_found": int(positions_found),
            "required_positions": int(required_positions),
            "valid_positions": valid_positions,
            "scan_positions": scan_positions,
            "vacuum_diameter_mm_base": float(vacuum_diameter_mm),
            "vacuum_diameter_mm_adjusted": round(float(adjusted_vacuum_diameter), 2),
            "adjustment_factor": float(adjustment_factor),
            "overlap_tolerance_pixels": int(overlap_tolerance_pixels),
            "min_vacuum_spacing_mm": float(min_vacuum_spacing_mm),
            "scan_summary": {
                "total_scanned": int(len(scan_positions)),
                "overlapped_with_profile": int(overlapped_count),
                "valid_clear_positions": int(positions_found)
            },
            "scan_method": "CRITICAL_FIX_optimal_Y_coordinate",
            "optimal_scan_y_mm": round(float(optimal_scan_y_mm), 2),
            "scan_range_x_mm": [round(float(x_end_mm), 2), round(float(x_start_mm), 2)]
        }
        
        return result
        
    except Exception as e:
        print(f"❌ [CRITICAL] OPTIMAL Y scanning failed: {e}")
        raise

def create_comprehensive_visualization(dxf_file_path: str, layer_names_file: str,
                                     profile_info: Dict[str, Any], scan_result: Dict[str, Any], 
                                     boundary_data: Dict[str, float], 
                                     profile_mask: np.ndarray) -> None:
    """
    ADDED: Comprehensive matplotlib visualization to verify functionality
    Creates multiple visualization panels to show the scanning process
    """
    
    print(f"📊 [VISUAL] Creating comprehensive visualization...")
    print(f"📊 [VISUAL] User: HarrisonKuo47")
    print(f"📊 [VISUAL] Date: 2025-09-05 06:59:28 UTC")
    
    try:
        # Get boundary coordinates
        x_min = boundary_data.get('x_min', 0)
        x_max = boundary_data.get('x_max', 0)
        y_min = boundary_data.get('y_min', 0)
        y_max = boundary_data.get('y_max', 0)
        
        # Read layer names and DXF
        layer_names = read_selected_layers(layer_names_file)
        doc = ezdxf.readfile(dxf_file_path)
        
        # Create figure with multiple subplots
        fig = plt.figure(figsize=(20, 12), dpi=150)
        fig.patch.set_facecolor('white')
        
        # Define subplot layout
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # Panel 1: DXF Rendering with Vacuum Positions
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor('black')
        ax1.set_title('DXF + Vacuum Positions', fontsize=14, fontweight='bold', color='darkblue')
        
        # Configure and render DXF
        for layer in doc.layers:
            layer.off()
        for lname in layer_names:
            if lname in doc.layers:
                doc.layers.get(lname).on()
        
        ctx_display = RenderContext(doc)
        out_display = MatplotlibBackend(ax1)
        Frontend(ctx_display, out_display).draw_layout(doc.modelspace(), finalize=True)
        
        ax1.set_xlim(x_min, x_max)
        ax1.set_ylim(y_min, y_max)
        ax1.set_aspect('equal')
        
        # Draw vacuum positions
        valid_positions = scan_result.get("valid_positions", [])
        rejected_positions = [p for p in scan_result.get("scan_positions", []) if p.get("is_overlapping", False)]
        
        # Valid positions (GREEN)
        for pos in valid_positions:
            x, y = pos["x_mm_original"], pos["y_mm_original"]
            diameter = pos["vacuum_diameter_mm"]
            
            circle = Circle((x, y), radius=diameter/2, 
                          edgecolor='lime', facecolor='none', 
                          linewidth=3, zorder=10, alpha=0.8)
            ax1.add_patch(circle)
            
            ax1.text(x, y, str(pos["position_number"]), 
                    color='white', fontsize=10, fontweight='bold',
                    ha='center', va='center', zorder=11, 
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='green', alpha=0.9))
        
        # Sample rejected positions (RED X)
        sample_rejected = rejected_positions[::max(1, len(rejected_positions)//20)] if rejected_positions else []
        for pos in sample_rejected:
            x, y = pos["x_mm_original"], pos["y_mm_original"]
            ax1.plot(x, y, 'rx', markersize=8, markeredgewidth=3, alpha=0.7)
        
        # Draw optimal scan line
        if scan_result.get("optimal_scan_y_mm"):
            scan_y = scan_result["optimal_scan_y_mm"]
            scan_range = scan_result.get("scan_range_x_mm", [x_min, x_max])
            ax1.axhline(y=scan_y, color='yellow', linewidth=2, linestyle='--', alpha=0.8, zorder=5)
            ax1.text((x_min + x_max)/2, scan_y + 2, f'Optimal Scan Y: {scan_y:.1f}mm', 
                    ha='center', va='bottom', color='yellow', fontweight='bold', fontsize=9)
        
        ax1.grid(True, alpha=0.3)
        ax1.set_xlabel('X (mm)')
        ax1.set_ylabel('Y (mm)')
        
        # Panel 2: Profile Mask Visualization
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_title('Lead Frame Profile Mask', fontsize=14, fontweight='bold', color='darkblue')
        
        # Show profile mask
        im2 = ax2.imshow(profile_mask, cmap='gray', aspect='equal', 
                        extent=[x_min, x_max, y_min, y_max], origin='upper')
        ax2.set_xlabel('X (mm)')
        ax2.set_ylabel('Y (mm)')
        
        # Add colorbar
        cbar2 = plt.colorbar(im2, ax=ax2, shrink=0.6)
        cbar2.set_label('Mask Value', fontsize=10)
        
        # Overlay scan line and vacuum positions
        if scan_result.get("optimal_scan_y_mm"):
            scan_y = scan_result["optimal_scan_y_mm"]
            ax2.axhline(y=scan_y, color='red', linewidth=2, linestyle='-', alpha=0.8)
        
        for pos in valid_positions:
            x, y = pos["x_mm_original"], pos["y_mm_original"]
            ax2.plot(x, y, 'ro', markersize=6, markerfacecolor='none', 
                    markeredgecolor='red', markeredgewidth=2)
        
        # Panel 3: Y Coverage Analysis
        ax3 = fig.add_subplot(gs[0, 2])
        ax3.set_title('Y-Direction Coverage Analysis', fontsize=14, fontweight='bold', color='darkblue')
        
        # Calculate row coverage
        height_pixels = profile_mask.shape[0]
        row_coverage = []
        y_coordinates = []
        
        for y_pixel in range(height_pixels):
            row = profile_mask[y_pixel, :]
            coverage = np.sum(row > 0) / len(row) * 100
            row_coverage.append(coverage)
            
            # Convert pixel Y to world Y
            y_world = y_max - (y_pixel / height_pixels) * (y_max - y_min)
            y_coordinates.append(y_world)
        
        ax3.plot(row_coverage, y_coordinates, 'b-', linewidth=2, label='Coverage %')
        ax3.fill_betweenx(y_coordinates, row_coverage, alpha=0.3, color='blue')
        
        # Mark optimal scan Y
        if scan_result.get("optimal_scan_y_mm"):
            scan_y = scan_result["optimal_scan_y_mm"]
            ax3.axhline(y=scan_y, color='red', linewidth=3, linestyle='--', 
                       label=f'Optimal Y: {scan_y:.1f}mm')
        
        ax3.set_xlabel('Coverage (%)')
        ax3.set_ylabel('Y (mm)')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        
        # Panel 4: Overlap Detection Analysis
        ax4 = fig.add_subplot(gs[1, :2])
        ax4.set_title('Overlap Detection Analysis', fontsize=14, fontweight='bold', color='darkblue')
        
        # Analyze overlap counts
        scan_positions = scan_result.get("scan_positions", [])
        if scan_positions:
            x_coords = [p["x_mm_original"] for p in scan_positions]
            overlap_counts = [p["overlap_count"] for p in scan_positions]
            is_overlapping_list = [p["is_overlapping"] for p in scan_positions]
            
            # Color code by overlap status
            colors = ['red' if is_overlapping else 'green' for is_overlapping in is_overlapping_list]
            
            scatter = ax4.scatter(x_coords, overlap_counts, c=colors, alpha=0.6, s=30)
            ax4.axhline(y=scan_result.get("overlap_tolerance_pixels", 0), 
                       color='orange', linewidth=2, linestyle='--', 
                       label=f'Tolerance: {scan_result.get("overlap_tolerance_pixels", 0)} pixels')
            
            ax4.set_xlabel('X Position (mm)')
            ax4.set_ylabel('Overlap Pixel Count')
            ax4.grid(True, alpha=0.3)
            ax4.legend()
            
            # Add statistics text
            total_scans = len(scan_positions)
            overlapped = len([p for p in scan_positions if p["is_overlapping"]])
            valid = len(valid_positions)
            
            stats_text = f"Total Scans: {total_scans}\n"
            stats_text += f"Overlapped: {overlapped}\n"
            stats_text += f"Valid Positions: {valid}\n"
            stats_text += f"Success Rate: {(valid/total_scans*100):.1f}%"
            
            ax4.text(0.02, 0.98, stats_text, transform=ax4.transAxes,
                    verticalalignment='top', fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        # Panel 5: Summary Information
        ax5 = fig.add_subplot(gs[1, 2])
        ax5.set_title('Scan Summary', fontsize=14, fontweight='bold', color='darkblue')
        ax5.axis('off')
        
        # Create summary text
        status = scan_result["status"]
        found = scan_result["positions_found"]
        required = scan_result["required_positions"]
        coverage = profile_info["white_pixel_coverage"]
        optimal_y = scan_result.get("optimal_scan_y_mm", "N/A")
        
        summary_text = f"""
CRITICAL FIX RESULTS:

Status: {status}
Positions Found: {found}/{required}
Profile Coverage: {coverage:.1f}%
Optimal Scan Y: {optimal_y}mm

Profile Info:
• Size: {profile_info['width_mm']}×{profile_info['height_mm']}mm
• Resolution: {profile_info['pixels_per_mm']:.1f}px/mm
• Layers: {len(profile_info['rendered_layers'])}

Scanning Parameters:
• Vacuum Diameter: {scan_result['vacuum_diameter_mm_adjusted']:.1f}mm
• Adjustment Factor: {scan_result['adjustment_factor']}
• Tolerance: {scan_result['overlap_tolerance_pixels']} pixels
• Min Spacing: {scan_result['min_vacuum_spacing_mm']}mm

Scan Method:
{scan_result.get('scan_method', 'Standard')}

User: HarrisonKuo47
Date: 2025-09-05 06:59:28 UTC
        """
        
        ax5.text(0.05, 0.95, summary_text.strip(), transform=ax5.transAxes,
                verticalalignment='top', fontsize=10, fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
        
        # Overall title
        overall_title = f"Vacuum Scanner Critical Fix - {status} ({found}/{required}) - Coverage: {coverage:.1f}%"
        fig.suptitle(overall_title, fontsize=16, fontweight='bold', color='darkblue')
        
        plt.tight_layout()
        plt.show()
        
        print(f"✅ [VISUAL] Comprehensive visualization completed successfully!")
        print(f"📊 [VISUAL] Shows: DXF + positions, profile mask, Y-coverage, overlap analysis, summary")
        
    except Exception as e:
        print(f"❌ [VISUAL] Visualization failed: {e}")

def run_vacuum_position_scan(dxf_file_path: str, layer_names_file: str, 
                           boundary_data: Dict[str, float], 
                           adjustment_factor: float,
                           vacuum_diameter_mm: float, 
                           required_positions: int,
                           scan_unit_mm: float = 0.1,
                           resolution_dpi: int = 300) -> Dict[str, Any]:
    """CRITICAL FIX: Main function with optimal Y coordinate scanning and comprehensive visualization"""
    
    print(f"🚀 [CRITICAL] ===== CRITICAL FIX with Comprehensive Visualization =====")
    print(f"🔍 [CRITICAL] User: HarrisonKuo47")
    print(f"🔍 [CRITICAL] Date: 2025-09-05 06:59:28 UTC")
    print(f"🔍 [CRITICAL] CRITICAL FIX: Scan at Y coordinate where geometry actually exists")
    print(f"📊 [VISUAL] ADDED: Comprehensive matplotlib visualization")
    
    try:
        # Phase 1: Create profile
        print(f"🔍 [CRITICAL] === PHASE 1: Profile Creation ===")
        profile_mask, profile_info = create_leadframe_profile_from_dxf(
            dxf_file_path, layer_names_file, boundary_data, resolution_dpi
        )
        
        # Phase 2: CRITICAL FIX - scan at optimal Y coordinate
        print(f"🔍 [CRITICAL] === PHASE 2: CRITICAL FIX - Optimal Y Scanning ===")
        scan_result = scan_vacuum_positions_with_optimal_y(
            profile_mask, profile_info, vacuum_diameter_mm, 
            required_positions, adjustment_factor, scan_unit_mm
        )
        
        # Phase 3: ADDED - Comprehensive Visualization
        print(f"🔍 [VISUAL] === PHASE 3: Comprehensive Visualization ===")
        try:
            create_comprehensive_visualization(
                dxf_file_path, layer_names_file, profile_info, 
                scan_result, boundary_data, profile_mask
            )
        except Exception as e:
            print(f"⚠️ [VISUAL] Visualization failed but continuing: {e}")
        
        # Clean up
        if 'ax_detect' in profile_info:
            plt.close('all')
        
        # Results
        complete_result = {
            "scan_result": scan_result,
            "profile_info": {
                k: v for k, v in profile_info.items() 
                if k not in ['ax_detect', 'canvas_detect']
            },
            "scanning_parameters": {
                "dxf_file": str(os.path.basename(dxf_file_path)),
                "adjustment_factor": float(adjustment_factor),
                "base_vacuum_diameter_mm": float(vacuum_diameter_mm),
                "adjusted_vacuum_diameter_mm": float(scan_result["vacuum_diameter_mm_adjusted"]),
                "resolution_dpi": int(resolution_dpi),
                "scan_method": "CRITICAL_FIX_optimal_Y_coordinate_with_visualization",
                "optimal_scan_y_mm": scan_result.get("optimal_scan_y_mm", 0),
                "scan_timestamp": "2025-09-05 06:59:28",
                "scanned_by": "HarrisonKuo47"
            }
        }
        
        print(f"🎉 [CRITICAL] ===== CRITICAL FIX with Visualization COMPLETED =====")
        print(f"📊 [SUMMARY] Status: {scan_result['status']}")
        print(f"📊 [SUMMARY] Found: {scan_result['positions_found']}/{scan_result['required_positions']}")
        print(f"📊 [SUMMARY] Optimal scan Y: {scan_result.get('optimal_scan_y_mm', 'N/A')}mm")
        print(f"📊 [SUMMARY] Profile coverage: {profile_info['white_pixel_coverage']:.1f}%")
        print(f"📊 [VISUAL] Comprehensive visualization displayed with 5 analysis panels")
        
        return complete_result
        
    except Exception as e:
        print(f"❌ [CRITICAL] ===== CRITICAL FIX FAILED =====")
        print(f"❌ [CRITICAL] Error: {e}")
        raise

def main():
    """Test the CRITICAL FIX vacuum scanner with comprehensive visualization"""
    print("🔬 TESTING CRITICAL FIX VACUUM SCANNER with Comprehensive Visualization")
    print(f"👤 User: HarrisonKuo47")
    print(f"📅 Date: 2025-09-05 06:59:28 UTC")
    print("🎯 CRITICAL FIX: Scan at Y coordinate where lead frame geometry exists")
    print("📊 ADDED: 5-panel comprehensive visualization")

if __name__ == "__main__":
    main()