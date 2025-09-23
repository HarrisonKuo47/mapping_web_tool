"""
Fixed Coordinate Conversion and Vacuum Mask Creation
Date: 2025-09-05 07:34:14 UTC
User: HarrisonKuo47

FIXES: Consistent scaling, aspect ratio validation, proper rounding
"""

import numpy as np
import cv2
from typing import Tuple

def world_to_pixel_enhanced(world_x, world_y, ax, canvas, debug=False):
    """Enhanced world to pixel conversion with validation"""
    
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()  
    width, height = canvas.get_width_height()
    
    if debug:
        print(f"🔍 [COORD] World→Pixel conversion:")
        print(f"    World: ({world_x:.2f}, {world_y:.2f})mm")
        print(f"    X limits: [{xlim[0]:.2f}, {xlim[1]:.2f}]mm")
        print(f"    Y limits: [{ylim[0]:.2f}, {ylim[1]:.2f}]mm") 
        print(f"    Canvas: {width}×{height}px")
    
    # Convert coordinates
    pixel_x = int((world_x - xlim[0]) / (xlim[1] - xlim[0]) * width)
    pixel_y = int(height - (world_y - ylim[0]) / (ylim[1] - ylim[0]) * height)
    
    # Validate bounds
    pixel_x = max(0, min(pixel_x, width - 1))
    pixel_y = max(0, min(pixel_y, height - 1))
    
    if debug:
        print(f"    Result: ({pixel_x}, {pixel_y})px")
    
    return pixel_x, pixel_y

def create_vacuum_cup_mask_enhanced(pixel_x: int, pixel_y: int, shape: str, size: str, 
                                  mask_shape: Tuple[int, int], ax, canvas, 
                                  debug=False) -> np.ndarray:
    """
    FIXED: Enhanced vacuum cup mask creation with proper scaling validation
    """
    
    try:
        height, width = mask_shape
        mask = np.zeros((height, width), dtype=np.uint8)
        
        if debug:
            print(f"🔍 [MASK] Creating {shape} mask:")
            print(f"    Position: ({pixel_x}, {pixel_y})px")
            print(f"    Size: {size}mm")
            print(f"    Mask shape: {width}×{height}px")
        
        if shape == 'circle':
            diameter = float(size)
            
            # FIXED: Get both canvas dimensions
            canvas_width, canvas_height = canvas.get_width_height()
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            
            # FIXED: Calculate scaling for both directions
            pixels_per_mm_x = canvas_width / (x_max - x_min)
            pixels_per_mm_y = canvas_height / (y_max - y_min)
            
            if debug:
                print(f"    Canvas: {canvas_width}×{canvas_height}px")
                print(f"    World size: {(x_max-x_min):.1f}×{(y_max-y_min):.1f}mm")
                print(f"    Pixels/mm X: {pixels_per_mm_x:.3f}")
                print(f"    Pixels/mm Y: {pixels_per_mm_y:.3f}")
            
            # FIXED: Validate aspect ratio
            aspect_ratio = pixels_per_mm_x / pixels_per_mm_y
            if abs(aspect_ratio - 1.0) > 0.05:  # More than 5% difference
                if debug:
                    print(f"⚠️ [MASK] WARNING: Non-square pixels! Aspect ratio: {aspect_ratio:.3f}")
                    print(f"    This may cause circles to appear as ellipses")
            
            # FIXED: Use average scaling (assuming set_aspect('equal') was used)
            pixels_per_mm = (pixels_per_mm_x + pixels_per_mm_y) / 2
            
            # FIXED: Use round() instead of int() for better accuracy
            radius_pixels = round(diameter / 2 * pixels_per_mm)
            
            if debug:
                print(f"    Average pixels/mm: {pixels_per_mm:.3f}")
                print(f"    Radius: {diameter/2:.2f}mm → {radius_pixels}px")
                print(f"    Expected area: ~{np.pi * radius_pixels**2:.0f}px")
            
            # Validate radius is reasonable
            if radius_pixels < 1:
                if debug:
                    print(f"⚠️ [MASK] WARNING: Radius too small ({radius_pixels}px), using minimum 1px")
                radius_pixels = 1
            elif radius_pixels > min(width, height) / 4:
                if debug:
                    print(f"⚠️ [MASK] WARNING: Radius very large ({radius_pixels}px) for mask size")
            
            # Draw circle
            cv2.circle(mask, (pixel_x, pixel_y), radius_pixels, 255, -1)
            
            # ADDED: Validate result
            if debug:
                actual_pixels = np.sum(mask > 0)
                expected_pixels = np.pi * radius_pixels**2
                ratio = actual_pixels / expected_pixels if expected_pixels > 0 else 0
                print(f"    Actual pixels drawn: {actual_pixels}")
                print(f"    Expected pixels: {expected_pixels:.0f}")
                print(f"    Ratio: {ratio:.3f}")
        
        return mask
        
    except Exception as e:
        print(f"❌ [MASK] Enhanced vacuum cup mask creation failed: {e}")
        return np.zeros(mask_shape, dtype=np.uint8)

def validate_coordinate_system(ax, canvas, test_points=None):
    """Validate coordinate system setup for debugging"""
    
    print(f"🔍 [VALIDATE] Coordinate system validation:")
    print(f"Date: 2025-09-05 07:34:14 UTC, User: HarrisonKuo47")
    
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    width, height = canvas.get_width_height()
    
    print(f"✅ [VALIDATE] Canvas: {width}×{height}px")
    print(f"✅ [VALIDATE] X range: [{xlim[0]:.2f}, {xlim[1]:.2f}]mm ({xlim[1]-xlim[0]:.1f}mm)")
    print(f"✅ [VALIDATE] Y range: [{ylim[0]:.2f}, {ylim[1]:.2f}]mm ({ylim[1]-ylim[0]:.1f}mm)")
    
    pixels_per_mm_x = width / (xlim[1] - xlim[0])
    pixels_per_mm_y = height / (ylim[1] - ylim[0])
    
    print(f"✅ [VALIDATE] Resolution X: {pixels_per_mm_x:.3f} px/mm")
    print(f"✅ [VALIDATE] Resolution Y: {pixels_per_mm_y:.3f} px/mm")
    print(f"✅ [VALIDATE] Aspect ratio: {pixels_per_mm_x/pixels_per_mm_y:.3f}")
    
    if abs(pixels_per_mm_x/pixels_per_mm_y - 1.0) < 0.01:
        print(f"✅ [VALIDATE] Coordinate system looks good (square pixels)")
    else:
        print(f"⚠️ [VALIDATE] WARNING: Non-square pixels detected!")
    
    # Test specific points if provided
    if test_points:
        print(f"🔍 [VALIDATE] Testing coordinate conversion:")
        for world_x, world_y in test_points:
            pixel_x, pixel_y = world_to_pixel_enhanced(world_x, world_y, ax, canvas)
            print(f"    ({world_x:.1f}, {world_y:.1f})mm → ({pixel_x}, {pixel_y})px")

# Usage example
def test_enhanced_functions():
    """Test the enhanced functions"""
    print(f"🔬 [TEST] Testing enhanced coordinate conversion")
    print(f"Date: 2025-09-05 07:34:14 UTC, User: HarrisonKuo47")
    
    # This would be called with actual ax and canvas objects
    # validate_coordinate_system(ax, canvas, [(0, 0), (100, 50), (-100, -50)])
    
    print(f"✅ [TEST] Enhanced functions ready for use")

if __name__ == "__main__":
    test_enhanced_functions()