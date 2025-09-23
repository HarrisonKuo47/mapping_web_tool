import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cv2
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import os

def read_layer_names(file_path):
    """Read layer names from text file"""
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def world_to_pixel(world_x, world_y, ax, canvas):
    """Convert world coordinates to pixel coordinates"""
    try:
        # Get axis limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        # Get canvas size
        width, height = canvas.get_width_height()
        
        # Convert to pixel coordinates
        pixel_x = int((world_x - xlim[0]) / (xlim[1] - xlim[0]) * width)
        pixel_y = int((1 - (world_y - ylim[0]) / (ylim[1] - ylim[0])) * height)
        
        return pixel_x, pixel_y
    except Exception as e:
        print(f"座標轉換錯誤: {e}")
        return 0, 0

def create_vacuum_chamber_contour_mask(corners_pixel, mask_shape, wall_thickness_pixels=3):
    """
    Create hollow rectangular mask for vacuum chamber contour only (walls/borders)
    
    Parameters:
    - corners_pixel: List of 4 corner coordinates in pixel space [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
    - mask_shape: Shape of the output mask (height, width)
    - wall_thickness_pixels: Thickness of the chamber walls in pixels (default 3 for ~2mm)
    
    Returns:
    - Binary mask with only chamber contour/walls filled (hollow rectangle)
    """
    try:
        mask = np.zeros(mask_shape, dtype=np.uint8)
        
        # Convert corners to numpy array for cv2
        corners_array = np.array(corners_pixel, dtype=np.int32)
        
        # Create outer rectangle (filled)
        outer_mask = np.zeros(mask_shape, dtype=np.uint8)
        cv2.fillPoly(outer_mask, [corners_array], 255)
        
        # Create inner rectangle (hollow part) by shrinking corners inward
        # Calculate the center of the rectangle
        center_x = np.mean([corner[0] for corner in corners_pixel])
        center_y = np.mean([corner[1] for corner in corners_pixel])
        
        # Create inner corners by moving each corner toward center by wall_thickness_pixels
        inner_corners = []
        for corner in corners_pixel:
            # Vector from corner to center
            dx = center_x - corner[0]
            dy = center_y - corner[1]
            
            # Normalize and scale by wall thickness
            dist = np.sqrt(dx*dx + dy*dy)
            if dist > 0:
                norm_dx = dx / dist
                norm_dy = dy / dist
                
                # Move corner inward by wall thickness
                inner_x = corner[0] + norm_dx * wall_thickness_pixels
                inner_y = corner[1] + norm_dy * wall_thickness_pixels
                inner_corners.append((int(inner_x), int(inner_y)))
            else:
                inner_corners.append(corner)
        
        # Create inner mask (to subtract from outer)
        inner_mask = np.zeros(mask_shape, dtype=np.uint8)
        inner_corners_array = np.array(inner_corners, dtype=np.int32)
        cv2.fillPoly(inner_mask, [inner_corners_array], 255)
        
        # Create contour mask = outer - inner (hollow rectangle)
        mask = cv2.subtract(outer_mask, inner_mask)
        
        return mask
        
    except Exception as e:
        print(f"腔室輪廓遮罩建立錯誤: {e}")
        # Fallback: create thin border using cv2.polylines
        try:
            mask = np.zeros(mask_shape, dtype=np.uint8)
            corners_array = np.array(corners_pixel, dtype=np.int32)
            cv2.polylines(mask, [corners_array], True, 255, thickness=wall_thickness_pixels)
            return mask
        except:
            return np.zeros(mask_shape, dtype=np.uint8)

def calculate_wall_thickness_pixels(thickness_mm, ax, canvas):
    """
    Convert wall thickness from mm to pixels based on current scale
    
    Parameters:
    - thickness_mm: Wall thickness in millimeters (e.g., 2.0)
    - ax: Matplotlib axis object
    - canvas: Matplotlib canvas object
    
    Returns:
    - Wall thickness in pixels
    """
    try:
        # Get axis limits and canvas size
        xlim = ax.get_xlim()
        width, height = canvas.get_width_height()
        
        # Calculate scale (pixels per unit in world coordinates)
        world_width = xlim[1] - xlim[0]
        pixels_per_unit = width / world_width
        
        # Convert thickness to pixels
        thickness_pixels = int(thickness_mm * pixels_per_unit)
        
        # Ensure minimum thickness of 2 pixels for visibility
        thickness_pixels = max(thickness_pixels, 2)
        
        return thickness_pixels
        
    except Exception as e:
        print(f"壁厚轉換錯誤: {e}")
        return 3  # Default fallback

def plot_dxf_and_vacuum_chambers_with_overlap_detection(
    dxf_file,
    layer_names_file,
    chamber_excel_file,
    output_png,
    overlap_report_file=None,
    dxf_bbox=None,
    dxf_bg='black',
    dxf_theme='dark',
    overlap_tolerance_pixels=5,
    enable_overlap_detection=True,
    wall_thickness_mm=2.0  # New parameter for wall thickness in mm
):
    """
    Map both LF and vacuum chambers with contour-only overlap detection
    
    Parameters:
    - enable_overlap_detection: True=啟用重疊檢測，False=僅可視化
    - overlap_report_file: 重疊報告輸出檔案路徑
    - overlap_tolerance_pixels: 像素容差
    - wall_thickness_mm: 腔室壁厚度(毫米)，只檢測此部分的重疊
    """
    
    # 1. 讀取圖層和 DXF
    layer_names = read_layer_names(layer_names_file)
    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()
    
    overlap_results = []
    dxf_mask = None
    
    # 2. If enable overlap detection, use high resolution method
    if enable_overlap_detection:
        print(f"🔍 啟用真空腔室輪廓重疊檢測模式 (壁厚: {wall_thickness_mm}mm)...")
        
        # High resolution detection
        fig_detect = plt.figure(figsize=(20, 16), dpi=300)
        ax_detect = fig_detect.add_axes([0, 0, 1, 1])
        fig_detect.patch.set_facecolor('black')
        ax_detect.set_facecolor('black')
        
        # 設定圖層可見性
        for layer in doc.layers:
            layer.off()
        for lname in layer_names:
            if lname in doc.layers:
                doc.layers.get(lname).on()
        
        # 渲染 DXF 到檢測用圖形
        ctx = RenderContext(doc)
        out_detect = MatplotlibBackend(ax_detect)
        Frontend(ctx, out_detect).draw_layout(msp, finalize=True)
        
        # 設定邊界
        if dxf_bbox and len(dxf_bbox) == 4:
            min_x, min_y, max_x, max_y = dxf_bbox
            ax_detect.set_xlim(min_x, max_x)
            ax_detect.set_ylim(min_y, max_y)
        
        ax_detect.set_aspect('equal')
        ax_detect.set_axis_off()
        
        # 將 DXF 圖形轉換為像素陣列
        canvas_detect = FigureCanvasAgg(fig_detect)
        canvas_detect.draw()
        dxf_image = np.frombuffer(canvas_detect.tostring_rgb(), dtype=np.uint8)
        dxf_image = dxf_image.reshape(canvas_detect.get_width_height()[::-1] + (3,))
        
        # 轉換為灰階並建立 DXF 遮罩
        dxf_gray = cv2.cvtColor(dxf_image, cv2.COLOR_RGB2GRAY)
        dxf_mask = (dxf_gray > 10).astype(np.uint8) * 255
        
        # Calculate wall thickness in pixels
        wall_thickness_pixels = calculate_wall_thickness_pixels(wall_thickness_mm, ax_detect, canvas_detect)
        print(f"💡 壁厚度: {wall_thickness_mm}mm = {wall_thickness_pixels} pixels")
        
        print(f"📏 DXF mask size: {dxf_mask.shape}")
    
    # 3. 讀取真空腔室數據
    df = pd.read_excel(chamber_excel_file, header=0)
    df['ChamberID'] = range(1, len(df) + 1)
    print(f"📂 載入 {len(df)} 個真空腔室")
    print("腔室欄位:", list(df.columns))
    print("腔室數據樣本:")
    print(df[['X_LF', 'Y_LF']].head())
    
    # 4. 建立顯示用圖形
    fig_display = plt.figure(figsize=(12, 10), dpi=300)
    ax_display = fig_display.add_axes([0, 0, 1, 1])
    fig_display.patch.set_facecolor(dxf_bg)
    ax_display.set_facecolor(dxf_bg)
    
    # 重新設定圖層可見性（為顯示圖形）
    for layer in doc.layers:
        layer.off()
    for lname in layer_names:
        if lname in doc.layers:
            doc.layers.get(lname).on()
    
    # 渲染 DXF 到顯示圖形
    ctx_display = RenderContext(doc)
    out_display = MatplotlibBackend(ax_display)
    Frontend(ctx_display, out_display).draw_layout(msp, finalize=True)
    
    # 5. 處理每個真空腔室
    for idx, row in df.iterrows():
        x, y = row['X_LF'], row['Y_LF']
        shape = str(row.get('Shape', 'rectangle')).lower()
        thickness = row.get('thickness', row.get('Vacuum size', 2))
        chamber_id = row['ChamberID']
        width = row.get('width', 10)
        height = row.get('height', 10)
        
        is_overlapping = False
        overlap_count = 0
        
        # 5.1 輪廓重疊檢測（如果啟用）
        if enable_overlap_detection and dxf_mask is not None:
            try:
                # 處理角落座標
                corners_world = []

                if 'corners' in row and row['corners'] is not None:
                    try:
                        corners_data = row['corners']
                        print(f"🔍 Debug corners data for chamber {chamber_id}: {corners_data}, type: {type(corners_data)}")
                        
                        # Handle different corner data formats
                        if isinstance(corners_data, str):
                            # If corners are stored as string, evaluate them
                            import ast
                            corners_world = ast.literal_eval(corners_data)
                        elif isinstance(corners_data, list):
                            corners_world = corners_data
                        elif hasattr(corners_data, '__iter__'):
                            # Convert to list if it's some other iterable
                            corners_world = list(corners_data)
                        else:
                            print(f"⚠️  Unexpected corners format: {type(corners_data)}")
                            raise ValueError("Invalid corners format")
                            
                        # Validate that we have 4 corners with 2 coordinates each
                        if len(corners_world) != 4:
                            raise ValueError(f"Expected 4 corners, got {len(corners_world)}")
                        
                        # Ensure each corner has 2 coordinates
                        for i, corner in enumerate(corners_world):
                            if not isinstance(corner, (tuple, list)) or len(corner) != 2:
                                raise ValueError(f"Corner {i} should have 2 coordinates, got {corner}")
                                
                    except Exception as e:
                        print(f"⚠️  Error parsing corners for chamber {chamber_id}: {e}")
                        corners_world = []

                # If corners parsing failed or no corners available, calculate from center and dimensions
                if not corners_world:
                    print(f"📐 Calculating corners from center for chamber {chamber_id}")
                    half_width = width / 2
                    half_height = height / 2
                    corners_world = [
                        (x - half_width, y + half_height),  # TL
                        (x + half_width, y + half_height),  # TR
                        (x + half_width, y - half_height),  # BR
                        (x - half_width, y - half_height)   # BL
                    ]

                print(f"📍 Final corners for chamber {chamber_id}: {corners_world}")

                # Convert corner coordinates to pixel space
                corners_pixel = []
                for i, corner in enumerate(corners_world):
                    try:
                        corner_x, corner_y = corner
                        pixel_x, pixel_y = world_to_pixel(corner_x, corner_y, ax_detect, canvas_detect)
                        corners_pixel.append((pixel_x, pixel_y))
                    except Exception as e:
                        print(f"⚠️ Error converting corner {i} to pixels: {e}")
                        # Skip this chamber if coordinate conversion fails
                        break

                # Only proceed if we have all 4 pixel corners
                if len(corners_pixel) != 4:
                    print(f"⚠️ Failed to convert all corners to pixels for chamber {chamber_id}")
                    is_overlapping = False
                    overlap_count = 0
                else:
                    # Create contour-only mask instead of filled mask
                    chamber_contour_mask = create_vacuum_chamber_contour_mask(
                        corners_pixel, 
                        dxf_mask.shape, 
                        wall_thickness_pixels
                    )
                    
                    # 檢測輪廓重疊
                    overlap_pixels = np.logical_and(dxf_mask > 0, chamber_contour_mask > 0)
                    overlap_count = np.sum(overlap_pixels)
                    is_overlapping = overlap_count > overlap_tolerance_pixels
                    
                    print(f"🔍 腔室 {chamber_id} 輪廓重疊檢測: {overlap_count} 像素 {'(重疊)' if is_overlapping else '(正常)'}")
                
            except Exception as e:
                print(f"⚠️ 真空腔室 {chamber_id} 輪廓重疊檢測錯誤: {e}")
                is_overlapping = False
                overlap_count = 0
        
        # 5.2 Record overlap result
        if enable_overlap_detection:
            overlap_results.append({
                'ChamberID': chamber_id,
                'Chamber': row.get('Chamber', f'Chamber_{chamber_id}'),
                'X_LF': x,
                'Y_LF': y,
                'Shape': shape,
                'Thickness': thickness,
                'Width': width,
                'Height': height,
                'Wall_Thickness_mm': wall_thickness_mm,
                'Overlap_Pixels': overlap_count,
                'Is_Overlapping': is_overlapping
            })
        
        # 5.3 Draw overlap chamber
        if enable_overlap_detection:
            color = 'red' if is_overlapping else 'cyan'
            edge_width = 4 if is_overlapping else 2
            alpha = 0.8 if is_overlapping else 0.6
        else:
            color = 'cyan'
            edge_width = 2
            alpha = 0.6
        
        # Draw chamber (顯示為空心矩形,只檢測輪廓)
        half_width = width / 2
        half_height = height / 2
        
        rect = Rectangle(
            (x - half_width, y - half_height),
            width, height,
            edgecolor=color,
            facecolor='none',  # 保持空心以強調只檢測輪廓
            linewidth=edge_width,
            alpha=alpha,
            zorder=11
        )
        ax_display.add_patch(rect)
        
        # 5.4 Display vacuum chamber
        if enable_overlap_detection and is_overlapping:
            ax_display.text(x, y, str(chamber_id), color='white', fontsize=12, 
                          ha='center', va='center', zorder=12, 
                          bbox=dict(boxstyle="round,pad=0.3", facecolor='red', alpha=0.9))
        else:
            # Display ID
            ax_display.text(x, y, str(chamber_id), color='yellow', fontsize=10, 
                          ha='center', va='center', zorder=12)
    
    # 6. Set contour
    if dxf_bbox and len(dxf_bbox) == 4:
        min_x, min_y, max_x, max_y = dxf_bbox
        ax_display.set_xlim(min_x, max_x)
        ax_display.set_ylim(min_y, max_y)
    
    ax_display.set_aspect('equal')
    ax_display.set_axis_off()
    
    # 7. 添加圖例
    if enable_overlap_detection:
        legend_elements = [
            Line2D([0], [0], color='cyan', lw=3, label=f'Normal Chamber'),
            Line2D([0], [0], color='red', lw=4, label=f'Overlapping Chamber Wall')
        ]
        ax_display.legend(handles=legend_elements, loc='upper right')
    else:
        legend_elements = [
            Line2D([0], [0], color='cyan', lw=3, label='Vacuum Chamber')
        ]
        ax_display.legend(handles=legend_elements, loc='upper right')
    
    # 8. 儲存圖片
    plt.tight_layout()
    plt.savefig(output_png, facecolor=dxf_bg, bbox_inches='tight', dpi=300)
    plt.close(fig_display)
    
    # 清理檢測用圖形
    if enable_overlap_detection:
        plt.close(fig_detect)
    
    # 9. 生成重疊報告
    if enable_overlap_detection and overlap_results:
        df_overlap = pd.DataFrame(overlap_results)
        overlapping_count = df_overlap['Is_Overlapping'].sum()
        total_count = len(df_overlap)
        
        # 儲存詳細報告
        if overlap_report_file:
            with pd.ExcelWriter(overlap_report_file) as writer:
                df_overlap.to_excel(writer, sheet_name='Contour_Overlap_Details', index=False)
                
                # 摘要統計
                summary = pd.DataFrame({
                    'Metric': [
                        'Total Vacuum Chambers', 
                        'Overlapping Chambers (Contour)', 
                        'Non-overlapping Chambers', 
                        'Contour Overlap Rate (%)',
                        'Wall Thickness (mm)',
                        'Detection Method'
                    ],
                    'Value': [
                        total_count, 
                        overlapping_count, 
                        total_count - overlapping_count, 
                        round(overlapping_count / total_count * 100, 2),
                        wall_thickness_mm,
                        'Contour/Wall Only'
                    ]
                })
                summary.to_excel(writer, sheet_name='Summary', index=False)
                
                # 重疊的腔室清單
                overlapping_chambers = df_overlap[df_overlap['Is_Overlapping'] == True]
                overlapping_chambers.to_excel(writer, sheet_name='Overlapping_Chambers', index=False)
        
        # 控制台輸出結果
        print("=" * 70)
        print(f" Vacuum Chamber overlap detection results (wall thickness: {wall_thickness_mm}mm)")
        print("=" * 70)
        print(f" {total_count} Vacuum Chambers")
        print(f"Overlapping count: {overlapping_count}")
        print(f"Overlapping rate: {overlapping_count / total_count * 100:.2f}%")
        print(f"Chamber Thickness: ({wall_thickness_mm}mm)")
        
        if overlap_report_file:
            print(f"Overlap report file: {overlap_report_file}")
    
    print(f"Visualization pic: {output_png}")
    
    return df_overlap if enable_overlap_detection and overlap_results else None
