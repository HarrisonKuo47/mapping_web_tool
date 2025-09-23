"""
Simple Vacuum Scanning Visualization
Date: 2025-09-04 03:58:11 UTC
User: HarrisonKuo47

Simple matplotlib visualization for vacuum scanning results, similar to dxf_vacuum_check.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from typing import Dict, Any, Optional, List

def visualize_vacuum_scanning_simple(dxf_file_path: str, layer_names_file: str,
                                   scan_result: Dict[str, Any], profile_info: Dict[str, Any],
                                   output_path: Optional[str] = None,
                                   dxf_bg: str = 'black') -> str:
    """
    Create simple visualization of vacuum scanning results on DXF leadframe
    
    Args:
        dxf_file_path: Path to DXF file
        layer_names_file: Path to layer names file
        scan_result: Vacuum scanning results
        profile_info: Profile information
        output_path: Output image path
        dxf_bg: Background color
        
    Returns:
        Path to saved image
    """
    
    print(f"🎨 [VIZ] Creating simple vacuum scanning visualization...")
    print(f"🎨 [VIZ] DXF file: {dxf_file_path}")
    print(f"🎨 [VIZ] Found {scan_result['positions_found']} valid positions")
    
    try:
        # 1. Read layer names
        with open(layer_names_file, 'r', encoding='utf-8') as f:
            layer_names = [line.strip() for line in f if line.strip()]
        print(f"🎨 [VIZ] Using layers: {layer_names}")
        
        # 2. Load DXF file
        doc = ezdxf.readfile(dxf_file_path)
        msp = doc.modelspace()
        
        # 3. Create display figure
        fig_display = plt.figure(figsize=(12, 10), dpi=300)
        ax_display = fig_display.add_axes([0, 0, 1, 1])
        fig_display.patch.set_facecolor(dxf_bg)
        ax_display.set_facecolor(dxf_bg)
        
        # 4. Configure layers (turn off all, then enable selected)
        for layer in doc.layers:
            layer.off()
        
        enabled_layers = []
        for layer_name in layer_names:
            if layer_name in doc.layers:
                doc.layers.get(layer_name).on()
                enabled_layers.append(layer_name)
                print(f"🎨 [VIZ] Enabled layer: {layer_name}")
        
        # 5. Render DXF to display
        ctx_display = RenderContext(doc)
        out_display = MatplotlibBackend(ax_display)
        Frontend(ctx_display, out_display).draw_layout(msp, finalize=True)
        print(f"🎨 [VIZ] DXF rendered successfully")
        
        # 6. Set boundary limits from profile info
        boundary_coords = profile_info['original_boundary_coords']
        min_x = boundary_coords['x_min']
        max_x = boundary_coords['x_max']
        min_y = boundary_coords['y_min']
        max_y = boundary_coords['y_max']
        
        ax_display.set_xlim(min_x, max_x)
        ax_display.set_ylim(min_y, max_y)
        ax_display.set_aspect('equal')
        ax_display.set_axis_off()
        
        print(f"🎨 [VIZ] Set boundaries: x=[{min_x:.1f}, {max_x:.1f}], y=[{min_y:.1f}, {max_y:.1f}]")
        
        # 7. Draw vacuum positions
        valid_positions = scan_result.get('valid_positions', [])
        vacuum_diameter = scan_result.get('vacuum_diameter_mm_adjusted', 3.6)
        
        print(f"🎨 [VIZ] Drawing {len(valid_positions)} vacuum positions...")
        print(f"🎨 [VIZ] Vacuum diameter: {vacuum_diameter:.2f} mm")
        
        for i, pos in enumerate(valid_positions):
            x = pos['x_mm_original']
            y = pos['y_mm_original']
            cup_id = pos['position_number']
            
            # Draw vacuum cup circle (green for valid positions)
            circle = Circle((x, y), radius=vacuum_diameter/2, 
                          edgecolor='green', facecolor='none', 
                          linewidth=2, zorder=11)
            ax_display.add_patch(circle)
            
            # Add position number
            ax_display.text(x, y, str(cup_id), color='white', fontsize=10, 
                          ha='center', va='center', zorder=12, 
                          bbox=dict(boxstyle="round,pad=0.2", facecolor='green', alpha=0.7))
            
            print(f"🎨 [VIZ] Position #{cup_id}: ({x:.1f}, {y:.1f}) mm")
        
        # 8. Add legend
        status_color = 'green' if scan_result['status'] == 'PASS' else 'red'
        legend_elements = [
            Line2D([0], [0], color='green', lw=3, label=f'Valid Vacuum Positions ({len(valid_positions)})'),
            Line2D([0], [0], color=status_color, lw=3, 
                   label=f'Status: {scan_result["status"]} ({scan_result["positions_found"]}/{scan_result["required_positions"]})')
        ]
        ax_display.legend(handles=legend_elements, loc='upper right', 
                         facecolor='white', edgecolor='black')
        
        # 9. Add title
        title = f'Vacuum Position Scanning - {os.path.basename(dxf_file_path)}'
        subtitle = f'Found {scan_result["positions_found"]}/{scan_result["required_positions"]} positions - Status: {scan_result["status"]}'
        
        fig_display.suptitle(title, fontsize=14, fontweight='bold', color='white' if dxf_bg == 'black' else 'black')
        ax_display.set_title(subtitle, fontsize=12, color='white' if dxf_bg == 'black' else 'black', pad=20)
        
        # 10. Save image
        if not output_path:
            timestamp = "2025-09-04_03-58-11"
            base_name = os.path.splitext(os.path.basename(dxf_file_path))[0]
            output_path = f"{base_name}_vacuum_result_{timestamp}.png"
        
        plt.tight_layout()
        plt.savefig(output_path, facecolor=dxf_bg, bbox_inches='tight', dpi=300)
        print(f"🎨 [VIZ] Visualization saved: {output_path}")
        
        # Show plot (optional - comment out for production)
        plt.show()
        
        plt.close(fig_display)
        
        return output_path
        
    except Exception as e:
        print(f"❌ [VIZ] Visualization failed: {e}")
        print(f"❌ [VIZ] Error type: {type(e)}")
        raise

def create_vacuum_result_overlay(dxf_file_path: str, layer_names_file: str,
                                scan_result: Dict[str, Any], profile_info: Dict[str, Any],
                                show_all_scans: bool = False,
                                output_path: Optional[str] = None) -> str:
    """
    Create vacuum result overlay similar to your dxf_vacuum_check.py style
    
    Args:
        dxf_file_path: Path to DXF file
        layer_names_file: Path to layer names file
        scan_result: Vacuum scanning results
        profile_info: Profile information
        show_all_scans: Whether to show all scanned positions or just valid ones
        output_path: Output image path
        
    Returns:
        Path to saved image
    """
    
    print(f"🎨 [OVERLAY] Creating vacuum result overlay...")
    
    try:
        # Read layer names
        with open(layer_names_file, 'r', encoding='utf-8') as f:
            layer_names = [line.strip() for line in f if line.strip()]
        
        # Load DXF
        doc = ezdxf.readfile(dxf_file_path)
        msp = doc.modelspace()
        
        # Create figure
        fig = plt.figure(figsize=(16, 12), dpi=300)
        ax = fig.add_axes([0, 0, 1, 1])
        fig.patch.set_facecolor('black')
        ax.set_facecolor('black')
        
        # Configure layers
        for layer in doc.layers:
            layer.off()
        for layer_name in layer_names:
            if layer_name in doc.layers:
                doc.layers.get(layer_name).on()
        
        # Render DXF
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)
        
        # Set boundaries
        boundary_coords = profile_info['original_boundary_coords']
        ax.set_xlim(boundary_coords['x_min'], boundary_coords['x_max'])
        ax.set_ylim(boundary_coords['y_min'], boundary_coords['y_max'])
        ax.set_aspect('equal')
        ax.set_axis_off()
        
        # Draw scanning results
        vacuum_diameter = scan_result.get('vacuum_diameter_mm_adjusted', 3.6)
        
        # Option 1: Show all scanned positions (like overlap detection)
        if show_all_scans and 'scan_positions' in scan_result:
            print(f"🎨 [OVERLAY] Drawing all {len(scan_result['scan_positions'])} scanned positions...")
            
            for pos in scan_result['scan_positions']:
                x = pos['x_mm_original']
                y = pos['y_mm_original']
                
                # Color based on overlap status
                color = 'red' if pos['is_overlapped'] else 'green'
                edge_width = 3 if pos['is_overlapped'] else 1
                alpha = 0.8 if pos['is_overlapped'] else 0.4
                
                circle = Circle((x, y), radius=vacuum_diameter/2, 
                              edgecolor=color, facecolor='none', 
                              linewidth=edge_width, alpha=alpha, zorder=10)
                ax.add_patch(circle)
        
        # Option 2: Show only valid positions (cleaner)
        valid_positions = scan_result.get('valid_positions', [])
        print(f"🎨 [OVERLAY] Drawing {len(valid_positions)} valid vacuum positions...")
        
        for pos in valid_positions:
            x = pos['x_mm_original']
            y = pos['y_mm_original']
            cup_id = pos['position_number']
            
            # Draw vacuum cup
            circle = Circle((x, y), radius=vacuum_diameter/2, 
                          edgecolor='deepskyblue', facecolor='none', 
                          linewidth=3, zorder=11)
            ax.add_patch(circle)
            
            # Add ID label
            ax.text(x, y, str(cup_id), color='white', fontsize=12, 
                   ha='center', va='center', zorder=12, fontweight='bold',
                   bbox=dict(boxstyle="circle,pad=0.3", facecolor='deepskyblue', alpha=0.8))
        
        # Add legend
        if show_all_scans:
            legend_elements = [
                Line2D([0], [0], color='green', lw=3, label='Valid Positions'),
                Line2D([0], [0], color='red', lw=3, label='Overlapped Positions'),
                Line2D([0], [0], color='deepskyblue', lw=3, label='Selected Vacuum Cups')
            ]
        else:
            legend_elements = [
                Line2D([0], [0], color='deepskyblue', lw=3, 
                       label=f'Vacuum Cups ({len(valid_positions)}/{scan_result["required_positions"]})')
            ]
        
        ax.legend(handles=legend_elements, loc='upper right', 
                 facecolor='white', edgecolor='black')
        
        # Add status text
        status_text = f"""Vacuum Scanning Results:
Status: {scan_result['status']}
Positions Found: {scan_result['positions_found']}/{scan_result['required_positions']}
Vacuum Diameter: {vacuum_diameter:.1f} mm
Adjustment Factor: {scan_result['adjustment_factor']:.2f}
Leadframe: {profile_info['width_mm']:.1f} × {profile_info['height_mm']:.1f} mm"""
        
        ax.text(0.02, 0.98, status_text, transform=ax.transAxes, 
               fontsize=11, verticalalignment='top', color='white',
               bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
        
        # Save
        if not output_path:
            timestamp = "2025-09-04_03-58-11"
            base_name = os.path.splitext(os.path.basename(dxf_file_path))[0]
            output_path = f"{base_name}_vacuum_overlay_{timestamp}.png"
        
        plt.tight_layout()
        plt.savefig(output_path, facecolor='black', bbox_inches='tight', dpi=300)
        print(f"🎨 [OVERLAY] Overlay saved: {output_path}")
        
        plt.show()
        plt.close(fig)
        
        return output_path
        
    except Exception as e:
        print(f"❌ [OVERLAY] Overlay creation failed: {e}")
        raise

def test_simple_visualization():
    """Test the simple visualization with sample data"""
    
    print("="*60)
    print("🎨 TESTING SIMPLE VACUUM VISUALIZATION")
    print(f"👤 User: HarrisonKuo47")
    print(f"📅 Date: 2025-09-04 03:58:11 UTC")
    print("="*60)
    
    # Test paths
    base_path = r"C:\Users\a1246807\Mapping_Tool_webapp\uploads"
    leadframe_name = "16DW_Tooling_6mil_Finalized"
    
    dxf_path = os.path.join(base_path, "leadframes", f"{leadframe_name}.dxf")
    layer_file = os.path.join(base_path, "layers", "layer.txt")
    
    # Sample data (you would get this from actual vacuum scanning)
    sample_scan_result = {
        "status": "PASS",
        "positions_found": 12,
        "required_positions": 10,
        "vacuum_diameter_mm_adjusted": 7.2,
        "adjustment_factor": 0.5,
        "valid_positions": [
            {"position_number": 1, "x_mm_original": 200.0, "y_mm_original": 350.0},
            {"position_number": 2, "x_mm_original": 180.0, "y_mm_original": 350.0},
            {"position_number": 3, "x_mm_original": 160.0, "y_mm_original": 350.0},
            {"position_number": 4, "x_mm_original": 140.0, "y_mm_original": 350.0},
            {"position_number": 5, "x_mm_original": 120.0, "y_mm_original": 350.0},
        ]
    }
    
    sample_profile_info = {
        "width_mm": 600.0,
        "height_mm": 190.0,
        "original_boundary_coords": {
            "x_min": 102.91,
            "x_max": 702.91,
            "y_min": 279.25,
            "y_max": 469.25
        }
    }
    
    try:
        # Test simple visualization
        print("\n🔍 TEST 1: Simple Visualization")
        viz_path = visualize_vacuum_scanning_simple(
            dxf_path, layer_file, sample_scan_result, sample_profile_info
        )
        print(f"✅ Simple visualization created: {viz_path}")
        
        # Test overlay visualization
        print("\n🔍 TEST 2: Overlay Visualization")
        overlay_path = create_vacuum_result_overlay(
            dxf_path, layer_file, sample_scan_result, sample_profile_info
        )
        print(f"✅ Overlay visualization created: {overlay_path}")
        
        print(f"\n🎉 VISUALIZATION TESTS COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"❌ VISUALIZATION TEST FAILED: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_simple_visualization()