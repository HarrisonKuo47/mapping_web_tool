import os
import ezdxf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon, Point
from ezdxf.math import Matrix44


def _apply_matrix_to_shape(geom, mtx):
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

def _is_closed_polyline(e, points):
    if hasattr(e, 'is_closed'):
        val = getattr(e, 'is_closed')
        if callable(val):
            if val():
                return True
        else:
            if val:
                return True
    if hasattr(e, 'closed'):
        val = getattr(e, 'closed')
        if callable(val):
            if val():
                return True
        else:
            if val:
                return True
    # 如果屬性沒設，再看點集
    if len(points) > 2 and (points[0] == points[-1]):
        return True
    return False

def _extract_shapes_from_entity(e, mtx, layer_names, doc, shapes):
    """
    遞迴萃取 entity 幾何與 INSERT 點，將結果 append 到 shapes。
    """
    # 處理 INSERT
    if e.dxftype() == "INSERT":
        if e.dxf.layer in layer_names:
            ins_pt = e.dxf.insert
            shapes.append({
                "ShapeID": e.dxf.handle,
                "Layer": e.dxf.layer,
                "Type": "INSERT",
                "BlockName": e.dxf.name,
                "InsertX": ins_pt[0],
                "InsertY": ins_pt[1],
                "InsertZ": ins_pt[2] if len(ins_pt) > 2 else 0,
                "Rotation": getattr(e.dxf, 'rotation', 0),
                "ScaleX": getattr(e.dxf, 'xscale', 1),
                "ScaleY": getattr(e.dxf, 'yscale', 1),
                "WKT": ""
            })
        # 若 block 存在，遞迴展開
            block_name = e.dxf.name
            if block_name in doc.blocks:
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
            for be in block:
                _extract_shapes_from_entity(be, insert_mtx, layer_names, doc, shapes)
        return  # INSERT 不需再往下處理其他型態

    # 處理 LWPOLYLINE
    if e.dxftype() == 'LWPOLYLINE':
        if e.dxf.layer not in layer_names:
            return
        points = [(p[0], p[1]) for p in e.get_points()]
        closed = _is_closed_polyline(e, points)
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
        closed = _is_closed_polyline(e, points)
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

def plot_insert_points(insert_points):
    if insert_points:
        x = [pt[0] for pt in insert_points]
        y = [pt[1] for pt in insert_points]
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 8))
        plt.scatter(x, y, c='red', label="INSERT Points")
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('Block INSERT Points (散點圖)')
        plt.legend()
        plt.gca().set_aspect('equal', adjustable='box')
        plt.grid(True)
        plt.xlim(min(x) - 10, max(x) + 10)
        plt.ylim(min(y) - 10, max(y) + 10)
        plt.show()
    else:
        print("沒有任何 INSERT 點")
    

def extract_dxf_shapes(doc, target_layers):
    shapes = []
    msp = doc.modelspace()
    identity_mtx = Matrix44()
    for e in msp:
        _extract_shapes_from_entity(e, identity_mtx, target_layers, doc, shapes)
    return pd.DataFrame(shapes)

def extract_dxf_shapes_for_file(
    dxf_file: str,
    layer_file: str,
    output_folder: str
) -> str:
    """Extracts shapes from a DXF file and saves a summary Excel in output_folder."""
    target_layers = []
    with open(layer_file, 'r') as file:
        target_layers = [line.strip() for line in file if line.strip()]
    doc = ezdxf.readfile(dxf_file)
    df_shapes = extract_dxf_shapes(doc, target_layers)
    if df_shapes.empty:
        return ""
    filename = os.path.basename(dxf_file)
    df_shapes['SourceFile'] = filename
    os.makedirs(output_folder, exist_ok=True)
    output_excel = os.path.join(
        output_folder, f"{os.path.splitext(filename)[0]}_shapes_summary.xlsx"
    )
    df_shapes.to_excel(output_excel, index=False)
    return output_excel


def print_anonymous_blocks(doc):
    """列出所有匿名 block（*UXXX）"""
    anonymous_blocks = set()
    for blk in doc.blocks:
        if blk.name.startswith('*U'):
            anonymous_blocks.add(blk.name)
            print(f"Block {blk.name}, entities: {len(list(blk))}")
            for ent in blk:
                print(f"  {ent.dxftype()} at layer {ent.dxf.layer}")

    records = []
    for e in doc.modelspace().query('INSERT'):
        if e.dxf.name in anonymous_blocks:
            ins_pt = e.dxf.insert
            rec = {
                "BlockName": e.dxf.name,
                "InsertX": ins_pt[0],
                "InsertY": ins_pt[1],
                "InsertZ": ins_pt[2] if len(ins_pt) > 2 else 0,
                "Rotation": getattr(e.dxf, 'rotation', 0),
                "ScaleX": getattr(e.dxf, 'xscale', 1),
                "ScaleY": getattr(e.dxf, 'yscale', 1),
                "Handle": e.dxf.handle,
            }
            records.append(rec)
    df = pd.DataFrame(records)
    df.to_excel("anonymous_block_inserts.xlsx", index=False)
    print("generated anonymous_block_inserts.xlsx")

def log_anonymous_blocks_to_txt(doc, output_path="anonymous_blocks_log.txt"):
    with open(output_path, "w", encoding="utf-8") as f:
        for blk in doc.blocks:
            if blk.name.startswith('*U'):
                f.write(f"Block {blk.name}, entities: {len(list(blk))}\n")
                for ent in blk:
                    f.write(f"  {ent.dxftype()} at layer {ent.dxf.layer}\n")
    print(f"已生成 txt log: {output_path}")

def print_used_anonymous_blocks(doc):
    """列出 modelspace 內所有被 INSERT 用到的匿名 block 名稱。"""
    used_blocks = set()
    for e in doc.modelspace().query('INSERT'):
        if e.dxf.name.startswith('*U'):
            used_blocks.add(e.dxf.name)
    print("Used anonymous blocks:", used_blocks)

if __name__ == "__main__":
    dxf_path = r"C:\Users\a1246807\Plunger_extraction\dxf\16DW_Tooling_6mil_Finalized.dxf"
    doc = ezdxf.readfile(dxf_path)
    shapes = []
    print("=== 匿名 block 結構分析 ===")
    print_anonymous_blocks(doc)
    print("=== 有被用到的匿名 block ===")
    print_used_anonymous_blocks(doc)
    print("=== 生成LOG檔案 ===")
    log_anonymous_blocks_to_txt(doc)
    plot_insert_points(shapes)


