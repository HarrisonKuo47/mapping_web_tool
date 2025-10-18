import cv2
import numpy as np
import json
import os
import glob
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from scipy.spatial.distance import euclidean

# 導入現有模組
from extract_axis import extract_axis_labels
from template_matcher import multi_scale_match
from filter import filter_page
from vacuum_cup_detector import (
    GeometricVacuumCupDetector,
    ContourVacuumCupDetector, 
    AdaptiveVacuumCupDetector,
    HybridVacuumCupDetector
)
import fitz

@dataclass
class CoordinateLabel:
    """座標標註資料結構"""
    value: str
    x: int
    y: int
    axis: str
    rotation: int
    original_x: int
    original_y: int

@dataclass
class VacuumCup:
    """Vacuum Cup 資料結構"""
    id: int
    center_x: int
    center_y: int
    bbox: Tuple[int, int, int, int]
    detection_method: str = "template"  # 新增：記錄偵測方法
    nearest_x_coord: Optional[CoordinateLabel] = None
    nearest_y_coord: Optional[CoordinateLabel] = None
    
    @property
    def coordinates(self) -> Tuple[Optional[str], Optional[str]]:
        x_val = self.nearest_x_coord.value if self.nearest_x_coord else None
        y_val = self.nearest_y_coord.value if self.nearest_y_coord else None
        return (x_val, y_val)

class VacuumCupCoordinateExtractor:
    """整合的 Vacuum Cup 座標擷取器"""
    
    def __init__(self, template_paths: List[str] = None, detection_method: str = "hybrid"):
        """
        初始化
        Args:
            template_paths: 模板路徑列表（用於傳統模板匹配）
            detection_method: 偵測方法 ("template", "geometric", "contour", "adaptive", "hybrid")
        """
        self.template_paths = template_paths or []
        self.detection_method = detection_method
        self.coordinate_labels: List[CoordinateLabel] = []
        self.vacuum_cups: List[VacuumCup] = []
        self.original_img_shape = None
        
        # 初始化偵測器
        self._init_detectors()
    
    def _init_detectors(self):
        """初始化各種偵測器"""
        self.geometric_detector = GeometricVacuumCupDetector()
        self.contour_detector = ContourVacuumCupDetector()
        self.adaptive_detector = AdaptiveVacuumCupDetector()
        self.hybrid_detector = HybridVacuumCupDetector()
    
    def _detect_vacuum_cups(self, image_path: str):
        """根據選擇的方法偵測vacuum cup位置"""
        print(f"使用 {self.detection_method} 方法偵測vacuum cup...")
        
        all_matches = []
        
        if self.detection_method == "template":
            # 原有的模板匹配方法
            for template_path in self.template_paths:
                if not os.path.exists(template_path):
                    print(f"警告: 模板檔案不存在: {template_path}")
                    continue
                    
                matches = multi_scale_match(
                    image_path, 
                    template_path, 
                    threshold=0.8,
                    scales=[0.9, 1.0, 1.1]
                )
                all_matches.extend(matches)
            detection_method_name = "template"
            
        elif self.detection_method == "geometric":
            all_matches = self.geometric_detector.detect_vacuum_cups(image_path)
            detection_method_name = "geometric"
            
        elif self.detection_method == "contour":
            all_matches = self.contour_detector.detect_vacuum_cups(image_path)
            detection_method_name = "contour"
            
        elif self.detection_method == "adaptive":
            all_matches = self.adaptive_detector.detect_vacuum_cups(image_path)
            detection_method_name = "adaptive"
            
        elif self.detection_method == "hybrid":
            all_matches = self.hybrid_detector.detect_vacuum_cups(image_path)
            detection_method_name = "hybrid"
            
        else:
            print(f"未知的偵測方法: {self.detection_method}，使用模板匹配")
            # 退回到模板匹配
            for template_path in self.template_paths:
                if os.path.exists(template_path):
                    matches = multi_scale_match(image_path, template_path, threshold=0.8)
                    all_matches.extend(matches)
            detection_method_name = "template_fallback"
        
        # 去除重複的匹配（NMS）
        all_matches = self._remove_duplicate_matches(all_matches)
        
        # 建立VacuumCup物件
        self.vacuum_cups = []
        for i, (x, y, w, h) in enumerate(all_matches):
            center_x = x + w // 2
            center_y = y + h // 2
            
            vacuum_cup = VacuumCup(
                id=i + 1,
                center_x=center_x,
                center_y=center_y,
                bbox=(x, y, w, h),
                detection_method=detection_method_name
            )
            self.vacuum_cups.append(vacuum_cup)
        
        print(f"偵測到 {len(self.vacuum_cups)} 個vacuum cup (方法: {detection_method_name})")
    
    # ... 其他方法保持不變 ...
    def _transform_coordinates_back(self, x: int, y: int, rotation: int, 
                                  img_width: int, img_height: int) -> Tuple[int, int]:
        if rotation == 90:
            orig_x = y
            orig_y = img_height - x  
        elif rotation == 180:
            orig_x = img_width - 1 - x
            orig_y = img_height - 1 - y
        elif rotation == 270:
            orig_x = img_width - y
            orig_y = x
        else:
            orig_x = x
            orig_y = y
        return orig_x, orig_y
    
    def process_pdf_page(self, pdf_path: str, page_num: int = 0, 
                        output_dir: str = "temp") -> Dict:
        os.makedirs(output_dir, exist_ok=True)

        doc = fitz.open(pdf_path)
        page = doc[page_num]
        cleaned_img_path = filter_page(page, output_dir)
        doc.close()
        
        if not cleaned_img_path:
            raise ValueError("PDF頁面處理失敗")
        
        #取得input pdf檔名
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        origin_img = os.path.join(
            r'C:\Users\a1246807\Plunger_extraction\png',
            f"{pdf_basename}.png"
        )

        img = cv2.imread(cleaned_img_path)
        self.original_img_shape = img.shape[:2]
        
        self._extract_coordinate_labels(origin_img)
        self._detect_vacuum_cups(cleaned_img_path)
        self._match_nearest_coordinates()
        results = self._generate_results()

        self._save_visualization(cleaned_img_path, output_dir, pdf_basename)
        
        return results
    
    def _extract_coordinate_labels(self, image_path: str):
        self.coordinate_labels = []
        img_height, img_width = self.original_img_shape
        
        print("擷取X軸座標標註...")
        x_labels = extract_axis_labels(image_path, rotate_angle=180, axis='x')
        
        for label in x_labels:
            orig_x, orig_y = self._transform_coordinates_back(
                label['x'], label['y'], 180, img_width, img_height
            )
            coord = CoordinateLabel(
                value=label['value'], x=orig_x, y=orig_y, axis='x',
                rotation=180, original_x=label['x'], original_y=label['y']
            )
            self.coordinate_labels.append(coord)
        
        print("擷取Y軸座標標註...")
        y_labels = extract_axis_labels(image_path, rotate_angle=90, axis='y')
        
        for label in y_labels:
            orig_x, orig_y = self._transform_coordinates_back(
                label['x'], label['y'], 90, img_width, img_height
            )
            coord = CoordinateLabel(
                value=label['value'], x=orig_x, y=orig_y, axis='y',
                rotation=90, original_x=label['x'], original_y=label['y']
            )
            self.coordinate_labels.append(coord)
        
        print(f"共擷取到 {len([c for c in self.coordinate_labels if c.axis == 'x'])} 個X軸座標")
        print(f"共擷取到 {len([c for c in self.coordinate_labels if c.axis == 'y'])} 個Y軸座標")
    
    def _remove_duplicate_matches(self, matches: List[Tuple], iou_threshold: float = 0.3) -> List[Tuple]:
        if len(matches) == 0:
            return []
        
        boxes = np.array(matches)
        areas = boxes[:, 2] * boxes[:, 3]
        indices = np.argsort(boxes[:, 1] + boxes[:, 3])
        
        keep = []
        while len(indices) > 0:
            last = len(indices) - 1
            i = indices[last]
            keep.append(i)
            
            xx1 = np.maximum(boxes[i, 0], boxes[indices[:last], 0])
            yy1 = np.maximum(boxes[i, 1], boxes[indices[:last], 1])
            xx2 = np.minimum(boxes[i, 0] + boxes[i, 2], 
                           boxes[indices[:last], 0] + boxes[indices[:last], 2])
            yy2 = np.minimum(boxes[i, 1] + boxes[i, 3], 
                           boxes[indices[:last], 1] + boxes[indices[:last], 3])
            
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            
            intersection = w * h
            union = areas[i] + areas[indices[:last]] - intersection
            iou = intersection / union
            
            indices = np.delete(indices, np.concatenate(([last], 
                              np.where(iou > iou_threshold)[0])))
        
        return [matches[i] for i in keep]
    
    def _match_nearest_coordinates(self):
        x_coords = [c for c in self.coordinate_labels if c.axis == 'x']
        y_coords = [c for c in self.coordinate_labels if c.axis == 'y']
        
        img_height, img_width = self.original_img_shape
        
        for cup in self.vacuum_cups:
            if y_coords:
                cup_rotated_90_y = cup.center_x
                y_distances = [(coord, abs(coord.original_y - cup_rotated_90_y)) for coord in y_coords]
                if y_distances:
                    nearest_y, min_y_diff = min(y_distances, key=lambda x: x[1])
                    cup.nearest_y_coord = nearest_y
            
            if x_coords:
                cup_rotated_180_y = img_height - 1 - cup.center_y
                x_distances = [(coord, abs(coord.original_y - cup_rotated_180_y)) for coord in x_coords]
                if x_distances:
                    nearest_x, min_x_diff = min(x_distances, key=lambda x: x[1])
                    cup.nearest_x_coord = nearest_x
    
    def _generate_results(self) -> Dict:
        results = {
            "detection_method": self.detection_method,
            "total_vacuum_cups": len(self.vacuum_cups),
            "total_coordinates": len(self.coordinate_labels),
            "vacuum_cups": [],
            "coordinate_labels": []
        }
        
        for cup in self.vacuum_cups:
            x_val, y_val = cup.coordinates
            cup_data = {
                "id": cup.id,
                "detection_method": cup.detection_method,
                "center_position": {"x": cup.center_x, "y": cup.center_y},
                "bounding_box": {"x": cup.bbox[0], "y": cup.bbox[1], 
                               "width": cup.bbox[2], "height": cup.bbox[3]},
                "coordinates": {"x": x_val, "y": y_val}
            }
            results["vacuum_cups"].append(cup_data)
        
        for coord in self.coordinate_labels:
            coord_data = {
                "value": coord.value,
                "position": {"x": coord.x, "y": coord.y},
                "axis": coord.axis,
                "rotation": coord.rotation
            }
            results["coordinate_labels"].append(coord_data)
        
        return results
    
    def _save_visualization(self, image_path: str, output_dir: str, basename: str):
        img = cv2.imread(image_path)
        if img is None:
            return
        
        # 根據偵測方法選擇不同顏色
        method_colors = {
            "template": (0, 0, 255),     # 紅色
            "geometric": (255, 0, 0),    # 藍色
            "contour": (0, 255, 0),      # 綠色
            "adaptive": (255, 255, 0),   # 青色
            "hybrid": (255, 0, 255)      # 洋紅色
        }
        
        for cup in self.vacuum_cups:
            x, y, w, h = cup.bbox
            color = method_colors.get(cup.detection_method, (0, 0, 255))
            
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
            cv2.circle(img, (cup.center_x, cup.center_y), 3, color, -1)
            
            x_val, y_val = cup.coordinates
            label = f"({x_val or '?'}, {y_val or '?'})"
            cv2.putText(img, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, color, 1)
            
            # 標示偵測方法
            method_label = cup.detection_method[:3]  # 縮寫
            cv2.putText(img, method_label, (x, y + h + 15), cv2.FONT_HERSHEY_SIMPLEX,
                       0.4, color, 1)
        
        # 畫座標標註點
        for coord in self.coordinate_labels:
            color = (255, 0, 0) if coord.axis == 'x' else (0, 255, 0)
            
            if 0 <= coord.x < img.shape[1] and 0 <= coord.y < img.shape[0]:
                cv2.circle(img, (coord.x, coord.y), 5, color, -1)
                cv2.putText(img, f"{coord.axis}:{coord.value}", 
                           (coord.x + 10, coord.y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        output_path = os.path.join(
            output_dir,
            f"visualization_result_{basename}_{self.detection_method}.png"
        )
        cv2.imwrite(output_path, img)
        print(f"視覺化結果已儲存至: {output_path}")