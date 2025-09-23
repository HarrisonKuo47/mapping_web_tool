import os
import ezdxf
import pytesseract
import pandas as pd
import numpy as np
from shapely import wkt
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, Ellipse
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
from shapely.geometry import LineString, Polygon, Point
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.math import Matrix44
import cv2

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\a1246807\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def read_layer_names(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def _apply_matrix_to_shape(geom, mtx):
    """把DXF Matrix44套到shapely物件（只做2D X/Y）"""
    try:
        coords = np.array(geom.coords)
        t_coords = [mtx.transform((x, y, 0))[:2] for x, y in coords]
        if geom.geom_type == "LineString":
            return LineString(t_coords)
        elif geom.geom_type == "Polygon":
            return Polygon(t_coords)
    except Exception:
        pass
    return geom

def extract_shapes_from_entity(e, mtx, layer_names, doc, shapes, parent_layer=None):
    """遞迴展開DXF實體，抓Polygon/LineString，含INSERT（block reference）"""
    if e.dxftype() == "INSERT":
        block_name = e.dxf.name
        if block_name not in doc.blocks:
            return
        block = doc.blocks[block_name]
        insert_mtx = Matrix44.chain(
            Matrix44.scale(
                getattr(e.dxf, 'xscale', 1),
                getattr(e.dxf, 'yscale', 1),
                getattr(e.dxf, 'zscale', 1)),
            Matrix44.z_rotate(np.radians(getattr(e.dxf, 'rotation', 0))),
            Matrix44.translate(*e.dxf.insert)
        )
        new_mtx = mtx @ insert_mtx
        print(f"展開 block: {block_name} at {e.dxf.insert}")
        for be in block:
            extract_shapes_from_entity(be, new_mtx, layer_names, doc, shapes, parent_layer=e.dxf.layer)
        return
    elif e.dxftype() == 'LWPOLYLINE':
        raw_layer = e.dxf.layer
        use_layer = parent_layer if raw_layer == '0' and parent_layer else raw_layer
        if use_layer not in layer_names:
            return
        points = [(p[0], p[1]) for p in e.get_points()]
        closed = getattr(e, 'closed', False)
        if closed:
            geom = Polygon(points)
        else:
            geom = LineString(points)
        geom = _apply_matrix_to_shape(geom, mtx)
        shapes.append({
            "ShapeID": e.dxf.handle,
            "Layer": e.dxf.layer,
            "Type": geom.geom_type,
            "WKT": geom.wkt
        })
    elif e.dxftype() == 'POLYLINE':
        if e.dxf.layer not in layer_names:
            return
        points = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
        closed = getattr(e, 'is_closed', False)
        if closed:
            geom = Polygon(points)
        else:
            geom = LineString(points)
        geom = _apply_matrix_to_shape(geom, mtx)
        shapes.append({
            "ShapeID": e.dxf.handle,
            "Layer": e.dxf.layer,
            "Type": geom.geom_type,
            "WKT": geom.wkt
        })
    elif e.dxftype() == "LINE":
        if e.dxf.layer not in layer_names:
            return
        start = (e.dxf.start.x, e.dxf.start.y)
        end = (e.dxf.end.x, e.dxf.end.y)
        geom = LineString([start, end])
        geom = _apply_matrix_to_shape(geom, mtx)
        shapes.append({
            "ShapeID": e.dxf.handle,
            "Layer": e.dxf.layer,
            "Type": geom.geom_type,
            "WKT": geom.wkt
        })
    elif e.dxftype() == "CIRCLE":
        if e.dxf.layer not in layer_names:
            return
        center = (e.dxf.center.x, e.dxf.center.y)
        radius = e.dxf.radius
        geom = Point(center).buffer(radius)
        geom = _apply_matrix_to_shape(geom, mtx)
        shapes.append({
            "ShapeID": e.dxf.handle,
            "Layer": e.dxf.layer,
            "Type": geom.geom_type,
            "WKT": geom.wkt
        })
    elif e.dxftype() == "ARC":
        if e.dxf.layer not in layer_names:
            return
        center = (e.dxf.center.x, e.dxf.center.y)
        radius = e.dxf.radius
        start_angle = e.dxf.start_angle
        end_angle = e.dxf.end_angle
        theta = np.linspace(np.radians(start_angle), np.radians(end_angle), num=30)
        arc_points = [
            (center[0] + radius * np.cos(a), center[1] + radius * np.sin(a)) for a in theta
        ]
        geom = LineString(arc_points)
        geom = _apply_matrix_to_shape(geom, mtx)
        shapes.append({
            "ShapeID": e.dxf.handle,
            "Layer": e.dxf.layer,
            "Type": geom.geom_type,
            "WKT": geom.wkt
        })
    elif e.dxftype() == "DIMENSION":
        if e.dxf.layer not in layer_names:
            return
        text = getattr(e.dxf, "text", "")
        defpoint1 = getattr(e.dxf, "defpoint", None)
        defpoint2 = getattr(e.dxf, "defpoint2", None)
        if defpoint1 and defpoint2:
            p1 = (defpoint1[0], defpoint1[1])
            p2 = (defpoint2[0], defpoint2[1])
            geom = LineString([p1, p2])
            geom = _apply_matrix_to_shape(geom, mtx)
            shapes.append({
                "ShapeID": e.dxf.handle,
                "Layer": e.dxf.layer,
                "Type": "Dimension",
                "WKT": geom.wkt,
                "DimText": text
            })
        else:
            shapes.append({
                "ShapeID": e.dxf.handle,
                "Layer": e.dxf.layer,
                "Type": "Dimension",
                "WKT": "",
                "DimText": text
            })

def extract_all_shapes(doc, layer_names):
    shapes = []
    msp = doc.modelspace()
    mtx_identity = Matrix44()  # 單位矩陣
    for e in msp:
        extract_shapes_from_entity(e, mtx_identity, layer_names, doc, shapes)
    return shapes

def world_to_pixel(world_x, world_y, ax, canvas):
    # 取得座標軸範圍
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    width, height = canvas.get_width_height()
    
    # 轉換座標
    pixel_x = int((world_x - xlim[0]) / (xlim[1] - xlim[0]) * width)
    pixel_y = int(height - (world_y - ylim[0]) / (ylim[1] - ylim[0]) * height)  # Y軸翻轉
    
    return pixel_x, pixel_y

def create_vacuum_cup_mask(pixel_x, pixel_y, shape, size, image_shape, ax, canvas):
    """建立真空杯的像素遮罩"""
    mask = np.zeros(image_shape[:2], dtype=np.uint8)
    
    try:
        if shape == 'circle':
            diameter = float(size)
            # 將世界座標尺寸轉換為像素尺寸
            xlim = ax.get_xlim()
            width = canvas.get_width_height()[0]
            pixel_radius = int(diameter / (xlim[1] - xlim[0]) * width / 2)  # Adjustable Threshold
            
            cv2.circle(mask, (pixel_x, pixel_y), pixel_radius, 255, -1)
            
        elif shape == 'oval':
            d, l, angle = size.split('_')
            d = float(d)
            l = float(l)
            angle = int(angle)
            
            # 轉換尺寸到像素
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            width, height = canvas.get_width_height()
            
            pixel_width = int(l / (xlim[1] - xlim[0]) * width)
            pixel_height = int(d / (ylim[1] - ylim[0]) * height)
            
            # 建立橢圓
            ellipse_angle = 90 if angle == 0 else 0
            cv2.ellipse(mask, (pixel_x, pixel_y), 
                       (pixel_width//2, pixel_height//2), 
                       ellipse_angle, 0, 360, 255, -1)
    
    except Exception as e:
        print(f"An error occurred while creating vacuum cup masks: {e}")
    
    return mask

def plot_dxf_and_vacuum_cups_with_overlap_detection(
    dxf_file,
    layer_names_file,
    vacuum_excel_file,
    output_png,
    overlap_report_file=None,
    dxf_bbox=None,
    dxf_bg='black',
    dxf_theme='dark',
    overlap_tolerance_pixels=2,
    enable_overlap_detection=True
):
    """
    Map both LF and vacuum cups
    
    Parameters:
    - enable_overlap_detection: True=啟用重疊檢測，False=僅可視化
    - overlap_report_file: 重疊報告輸出檔案路徑
    - overlap_tolerance_pixels: 像素容差
    """
    
    # 1. 讀取圖層和 DXF
    layer_names = read_layer_names(layer_names_file)
    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()
    
    overlap_results = []
    dxf_mask = None
    
    # 2. If enavle overlap detection, create high resolution checker
    if enable_overlap_detection:
        print(" 啟用重疊檢測模式...")
        
        fig_detect = plt.figure(figsize=(20, 16), dpi=300)
        ax_detect = fig_detect.add_axes([0, 0, 1, 1])
        fig_detect.patch.set_facecolor('black')
        ax_detect.set_facecolor('black')
        
        # Open specified layers
        for layer in doc.layers:
            layer.off()
        for lname in layer_names:
            if lname in doc.layers:
                doc.layers.get(lname).on()
        
        ctx = RenderContext(doc)
        out_detect = MatplotlibBackend(ax_detect)
        Frontend(ctx, out_detect).draw_layout(msp, finalize=True)
        
        # Define contour
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
        
        # 轉換為灰階並建立 DXF mask
        dxf_gray = cv2.cvtColor(dxf_image, cv2.COLOR_RGB2GRAY)
        dxf_mask = (dxf_gray > 10).astype(np.uint8) * 255
        
        print(f" DXF 遮罩已建立，尺寸: {dxf_mask.shape}")
    
    # 3. read vacuum cups location
    df = pd.read_excel(vacuum_excel_file, header=0)
    df['CupID'] = range(1, len(df) + 1)
    print(f" load {len(df)} vacuum cups")
    print(df[['X_LF', 'Y_LF']].head())
    
    # 4. 建立顯示用圖
    fig_display = plt.figure(figsize=(12, 10), dpi=300)
    ax_display = fig_display.add_axes([0, 0, 1, 1])
    fig_display.patch.set_facecolor(dxf_bg)
    ax_display.set_facecolor(dxf_bg)
    
    # 重新設定圖層（可顯示的layer）
    for layer in doc.layers:
        layer.off()
    for lname in layer_names:
        if lname in doc.layers:
            doc.layers.get(lname).on()
    
    # 渲染 DXF 到顯示圖形
    ctx_display = RenderContext(doc)
    out_display = MatplotlibBackend(ax_display)
    Frontend(ctx_display, out_display).draw_layout(msp, finalize=True)
    
    # 5. 處理vacuum cups
    for idx, row in df.iterrows():
        x, y = row['X_LF'], row['Y_LF']
        shape = str(row['Shape']).lower()
        size = str(row['Vacuum size'])
        cupid = row['CupID']
        
        is_overlapping = False
        overlap_count = 0
        
        # 5.1 overlap detection
        if enable_overlap_detection and dxf_mask is not None:
            try:
                # coordinate transform
                pixel_x, pixel_y = world_to_pixel(x, y, ax_detect, canvas_detect)
                
                # create vacuum cups mask
                cup_mask = create_vacuum_cup_mask(
                    pixel_x, pixel_y, shape, size, 
                    dxf_mask.shape, ax_detect, canvas_detect
                )
                
                # overlap detection
                overlap_pixels = np.logical_and(dxf_mask > 0, cup_mask > 0)
                overlap_count = np.sum(overlap_pixels)
                is_overlapping = overlap_count > overlap_tolerance_pixels
                
            except Exception as e:
                print(f" 真空杯 {cupid} 重疊檢測錯誤: {e}")
                is_overlapping = False
                overlap_count = 0
        
        # 5.2 record results
        if enable_overlap_detection:
            overlap_results.append({
                'CupID': cupid,
                'X_LF': x,
                'Y_LF': y,
                'Shape': shape,
                'Size': size,
                'Overlap_Pixels': overlap_count,
                'Is_Overlapping': is_overlapping
            })
        
        # 5.3 redraw vacuum cups
        if enable_overlap_detection:
            color = 'red' if is_overlapping else 'green'
            edge_width = 3 if is_overlapping else 2
        else:
            color = 'deepskyblue' if shape == 'circle' else 'yellow'
            edge_width = 2
        
        if shape == 'circle':
            diameter = float(size)
            c = Circle((x, y), radius=diameter/2, 
                      edgecolor=color, facecolor='none', 
                      linewidth=edge_width, zorder=11)
            ax_display.add_patch(c)
        elif shape == 'oval':
            d, l, angle = size.split('_')
            d = float(d)
            l = float(l)
            angle = int(angle)
            
            ellipse = Ellipse((x, y), width=l, height=d, 
                            angle=90 if angle==0 else 0,
                            edgecolor=color, facecolor='none', 
                            linewidth=edge_width, zorder=11)
            ax_display.add_patch(ellipse)
        
        # 5.4 If overlapped, mark ID
        if enable_overlap_detection and is_overlapping:
            ax_display.text(x, y, str(cupid), color='white', fontsize=10, 
                          ha='center', va='center', zorder=12, 
                          bbox=dict(boxstyle="round,pad=0.2", facecolor='red', alpha=0.7))
    
    # 6. 設定顯示圖 Contour
    if dxf_bbox and len(dxf_bbox) == 4:
        min_x, min_y, max_x, max_y = dxf_bbox
        ax_display.set_xlim(min_x, max_x)
        ax_display.set_ylim(min_y, max_y)
    
    ax_display.set_aspect('equal')
    ax_display.set_axis_off()
    
    # 7. upper right keys
    if enable_overlap_detection:
        legend_elements = [
            Line2D([0], [0], color='green', lw=3, label='Normal Vacuum Cup'),
            Line2D([0], [0], color='red', lw=3, label='Violate DR Vaccum Cup')
        ]
        ax_display.legend(handles=legend_elements, loc='upper right')
    else:
        legend_elements = [
            Line2D([0], [0], color='deepskyblue', lw=3, label='Circle Vacuum Cup'),
            Line2D([0], [0], color='yellow', lw=3, label='Oval Vacuum cup')
        ]
        ax_display.legend(handles=legend_elements, loc='upper right')
    
    # 8. Save Images
    plt.tight_layout()
    plt.savefig(output_png, facecolor=dxf_bg, bbox_inches='tight', dpi=300)
    #plt.show()
    plt.close(fig_display)
    
    if enable_overlap_detection:
        plt.close(fig_detect)
    
    # 9. 生成Overlap報告
    if enable_overlap_detection and overlap_results:
        df_overlap = pd.DataFrame(overlap_results)
        overlapping_count = df_overlap['Is_Overlapping'].sum()
        total_count = len(df_overlap)
        
        if overlap_report_file:
            with pd.ExcelWriter(overlap_report_file) as writer:
                df_overlap.to_excel(writer, sheet_name='Overlap_Details', index=False)
                
                # 摘要統計
                summary = pd.DataFrame({
                    'Metric': ['Total Vacuum Cups', 'Overlapping Cups', 'Non-overlapping Cups', 'Overlap Rate (%)'],
                    'Value': [total_count, overlapping_count, total_count - overlapping_count, 
                             round(overlapping_count / total_count * 100, 2)]
                })
                summary.to_excel(writer, sheet_name='Summary', index=False)
                
                # 重疊清單
                overlapping_cups = df_overlap[df_overlap['Is_Overlapping'] == True]
                overlapping_cups.to_excel(writer, sheet_name='Overlapping_Cups', index=False)
        
        # 控制台輸出結果(Debug 用)
        print("=" * 60)
        print(" Automated overlap detection")
        print("=" * 60)
        print(f"Total vacuum cups: {total_count}")
        print(f"Overlapped vacuum cups: {overlapping_count}")
        print(f"Overlap rate: {overlapping_count / total_count * 100:.2f}%")
        
        if overlapping_count > 0:
            overlapping_cups = df_overlap[df_overlap['Is_Overlapping'] == True]
            print("Overlapped vacuum cups ID:", overlapping_cups['CupID'].tolist())
        else:
            print("\n There are no overlapped vacuum cups")
        
        if overlap_report_file:
            print(f" Overlap reoport path: {overlap_report_file}")
    
    print(f" Visualize output: {output_png}")
    
    return df_overlap if enable_overlap_detection and overlap_results else None

def plot_dxf_and_vacuum_cups(
    dxf_file,
    layer_names_file,
    vacuum_excel_file,
    output_png,
    dxf_bbox=None,
    dxf_bg='black',
    dxf_theme='dark',
):
    """
    向後相容 (銜接)
    """
    return plot_dxf_and_vacuum_cups_with_overlap_detection(
        dxf_file=dxf_file,
        layer_names_file=layer_names_file,
        vacuum_excel_file=vacuum_excel_file,
        output_png=output_png,
        dxf_bbox=dxf_bbox,
        dxf_bg=dxf_bg,
        dxf_theme=dxf_theme,
        enable_overlap_detection=False
    )

def process_dxf_files(folder_path, layer_names_file):
    layer_names = read_layer_names(layer_names_file)
    shape_dict = {}
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.dxf'):
            dxf_file = os.path.join(folder_path, filename)
            try:
                doc = ezdxf.readfile(dxf_file)
                shapes = extract_all_shapes(doc, layer_names)
                shape_dict[filename] = shapes
            except Exception as e:
                print(f"Error occurs while {filename}: {str(e)}")
    return shape_dict

def process_dxf_files_and_draw(folder_path, layer_names_file, output_folder, dxf_bbox):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    layer_names = read_layer_names(layer_names_file)
    shape_dict = {}

    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.dxf'):
            dxf_file = os.path.join(folder_path, filename)
            output_file = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_layers.png")

            try:
                doc = ezdxf.readfile(dxf_file)
                shapes = extract_all_shapes(doc, layer_names)
                shape_dict[filename] = shapes

                fig = plt.figure(figsize=(10, 8), dpi=300)
                ax = fig.add_axes([0, 0, 1, 1])
                fig.patch.set_facecolor('black')
                ax.set_facecolor('black')
                ctx = RenderContext(doc)
                out = MatplotlibBackend(ax)

                for layer in doc.layers:
                    layer.off()

                found_layers = []
                for layer_name in layer_names:
                    if layer_name in doc.layers:
                        doc.layers.get(layer_name).on()
                        found_layers.append(layer_name)
                    else:
                        print(f"Warning: Can't found {layer_name} layers in {filename} ")

                if not found_layers:
                    print(f"Warning: Can't found any specific layers in {filename}")
                    plt.close(fig)
                    continue

                Frontend(ctx, out).draw_layout(doc.modelspace(), finalize=True)
                ax.set_axis_off()
                ax.autoscale_view()

                min_x, min_y, max_x, max_y = dxf_bbox
                ax.plot([min_x, max_x, max_x, min_x, min_x], [min_y, min_y, max_y, max_y, min_y], color="white", lw=1)
                ax.set_xlim(min_x - 1, max_x + 1)
                ax.set_ylim(min_y - 1, max_y + 1)

                plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='black')
                plt.show(fig)
                plt.close(fig)

            except Exception as e:
                print(f"Error occurs while execute {filename}: {str(e)}")
    return shape_dict

def export_shapes_txt_xlsx(shape_dict, txt_path="shapes_summary_1.txt", xlsx_path="shapes_summary_1.xlsx"):
    # txt
    with open(txt_path, "w", encoding="utf-8") as f:
        for fname, shapes in shape_dict.items():
            f.write(f"File: {fname}\n")
            for i, s in enumerate(shapes):
                f.write(f"  [{i}] Handle: {s['ShapeID']}, Layer: {s['Layer']}, Type: {s['Type']}, WKT: {s['WKT']}\n")
            f.write("\n")
    print(f"已輸出TXT: {txt_path}")

    data = []
    for fname, shapes in shape_dict.items():
        for s in shapes:
            data.append({
                "File": fname,
                "ShapeID": s["ShapeID"],
                "Layer": s["Layer"],
                "Type": s["Type"],
                "WKT": s["WKT"]
            })
    df = pd.DataFrame(data)
    df.to_excel(xlsx_path, index=False)
    print(f"已輸出XLSX: {xlsx_path}")

def draw_shapes_from_xlsx(xlsx_path, save_path=None):
    df = pd.read_excel(xlsx_path)
    fig, ax = plt.subplots(figsize=(10, 8))
    for idx, row in df.iterrows():
        wkt_str = str(row["WKT"]).strip()
        if not wkt_str or wkt_str.lower() == "none":
            continue
        try:
            geom = wkt.loads(wkt_str)
        except Exception as e:
            print(f"第{idx}行 WKT extracting error: {wkt_str}，Wrong message:{e}")
            continue
        if geom.geom_type == "LineString":
            x, y = geom.xy
            ax.plot(x, y, color='cyan', lw=2, label='LineString' if idx == 0 else "")
        elif geom.geom_type == "Polygon":
            x, y = geom.exterior.xy
            ax.plot(x, y, color='yellow', lw=2, label='Polygon' if idx == 0 else "")
    ax.set_title("LineString & Polygon from WKT")
    ax.set_aspect('equal')
    ax.set_facecolor("black")
    plt.legend()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='black')
    #plt.show()

OUTPUT_FOLDER = r"C:\Users\a1246807\Plunger_extraction\Mapping_Tool\output"
DXF_FOLDER = r"C:\Users\a1246807\Plunger_extraction\dxf"
LAYER_FILE = r"C:\Users\a1246807\Plunger_extraction\layers\layer.txt"

def get_dxf_bbox(subfolder, dxf_name):
    boundary_info_file = os.path.join(subfolder, f"{dxf_name}_boundary.xlsx")
    if not os.path.exists(boundary_info_file):
        return None
    df = pd.read_excel(boundary_info_file)
    try:
        min_x = float(df[df['Item'] == 'x_min']['Value'].iloc[0])
        max_x = float(df[df['Item'] == 'x_max']['Value'].iloc[0])
        min_y = float(df[df['Item'] == 'y_min']['Value'].iloc[0])
        max_y = float(df[df['Item'] == 'y_max']['Value'].iloc[0])
        return (min_x, min_y, max_x, max_y)
    except Exception:
        return None
    
def map_all():
    # Loop over all DXF result subfolders
    for subfolder in os.listdir(OUTPUT_FOLDER):
        subfolder_path = os.path.join(OUTPUT_FOLDER, subfolder)
        if not os.path.isdir(subfolder_path):
            continue
        dxf_name = subfolder
        dxf_file = os.path.join(DXF_FOLDER, f"{dxf_name}.dxf")
        if not os.path.exists(dxf_file):
            print(f"[{dxf_name}] DXF file not found: {dxf_file}, skipping")
            continue

        dxf_bbox = get_dxf_bbox(subfolder_path, dxf_name)
        if dxf_bbox is None:
            print(f"[{dxf_name}] No bbox info, using default axis limits.")
        print(f"\nProcessing Lead Frame: {dxf_name}")

        # Search for all *_vac_cups.xlsx files in subfolder
        for vac_excel in os.listdir(subfolder_path):
            if not vac_excel.endswith('_vac_cups.xlsx'):
                continue
            vacuum_excel_file = os.path.join(subfolder_path, vac_excel)
            vac_base = os.path.splitext(vac_excel)[0]

            # Output file naming
            output_png_overlap = os.path.join(subfolder_path, f"{dxf_name}_{vac_base}_with_overlap_detection.png")
            output_png_vis = os.path.join(subfolder_path, f"{dxf_name}_{vac_base}_visualization_only.png")
            overlap_report_file = os.path.join(subfolder_path, f"{dxf_name}_{vac_base}_overlap_analysis_report.xlsx")

            print(f"  Vacuum cups: {vac_excel}")

            # Visualization only
            plot_dxf_and_vacuum_cups(
                dxf_file,
                LAYER_FILE,
                vacuum_excel_file,
                output_png_vis,
                dxf_bbox=dxf_bbox,
                dxf_bg='black',
                dxf_theme='dark'
            )
            # Visualization + overlap detection
            plot_dxf_and_vacuum_cups_with_overlap_detection(
                dxf_file=dxf_file,
                layer_names_file=LAYER_FILE,
                vacuum_excel_file=vacuum_excel_file,
                output_png=output_png_overlap,
                overlap_report_file=overlap_report_file,
                dxf_bbox=dxf_bbox,
                dxf_bg='black',
                dxf_theme='dark',
                overlap_tolerance_pixels=5,
                enable_overlap_detection=True
            )
            print(f"    Outputs: {output_png_vis}, {output_png_overlap}, {overlap_report_file}")


if __name__ == "__main__":
    map_all()
