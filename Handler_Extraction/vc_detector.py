import cv2
import numpy as np
from typing import List, Tuple, Dict
import os

class GeometricVacuumCupDetector:
    """基於幾何特徵的vacuum cup偵測器"""
    
    def __init__(self, min_radius=14, max_radius=25, min_dist=20):
        self.min_circle_radius = min_radius
        self.max_circle_radius = max_radius
        self.min_dist = min_dist
        
    def detect_vacuum_cups(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """使用圓形偵測找vacuum cup"""
        img = cv2.imread(image_path)
        if img is None:
            return []
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 霍夫圓偵測
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=self.min_dist,
            param1=50,
            param2=30,
            minRadius=self.min_circle_radius,
            maxRadius=self.max_circle_radius
        )
        
        if circles is None:
            return []
        
        circles = np.round(circles[0, :]).astype("int")
        vacuum_cups = []
        
        for (x, y, r) in circles:
            if self._validate_vacuum_cup(gray, x, y, r):
                bbox = (x - r, y - r, 2 * r, 2 * r)
                vacuum_cups.append(bbox)
        
        print(f"幾何偵測找到 {len(vacuum_cups)} 個vacuum cup")
        return vacuum_cups
    
    def _validate_vacuum_cup(self, gray_img: np.ndarray, cx: int, cy: int, radius: int) -> bool:
        """驗證圓是否為vacuum cup"""
        roi_size = radius * 2
        x1 = max(0, cx - roi_size // 2)
        y1 = max(0, cy - roi_size // 2)
        x2 = min(gray_img.shape[1], cx + roi_size // 2)
        y2 = min(gray_img.shape[0], cy + roi_size // 2)
        
        roi = gray_img[y1:y2, x1:x2]
        if roi.size == 0:
            return False
        
        # 檢查中心區域是否有結構
        roi_cx = cx - x1
        roi_cy = cy - y1
        center_size = max(3, radius // 3)
        
        center_x1 = max(0, roi_cx - center_size)
        center_y1 = max(0, roi_cy - center_size)
        center_x2 = min(roi.shape[1], roi_cx + center_size)
        center_y2 = min(roi.shape[0], roi_cy + center_size)
        
        center_roi = roi[center_y1:center_y2, center_x1:center_x2]
        center_edges = cv2.Canny(center_roi, 50, 150)
        center_edge_ratio = np.sum(center_edges > 0) / center_edges.size if center_edges.size > 0 else 0
        
        return center_edge_ratio > 0.1

class ContourVacuumCupDetector:
    """基於輪廓特徵的vacuum cup偵測器"""
    
    def __init__(self, min_area=200, max_area=2000, circularity_threshold=0.6):
        self.min_area = min_area
        self.max_area = max_area
        self.circularity_threshold = circularity_threshold
        
    def detect_vacuum_cups(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """使用輪廓分析偵測vacuum cup"""
        img = cv2.imread(image_path)
        if img is None:
            return []
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 形態學操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        vacuum_cups = []
        for contour in contours:
            if self._is_vacuum_cup_contour(contour):
                x, y, w, h = cv2.boundingRect(contour)
                vacuum_cups.append((x, y, w, h))
        
        print(f"輪廓偵測找到 {len(vacuum_cups)} 個vacuum cup")
        return vacuum_cups
    
    def _is_vacuum_cup_contour(self, contour) -> bool:
        """判斷輪廓是否為vacuum cup"""
        area = cv2.contourArea(contour)
        
        if area < self.min_area or area > self.max_area:
            return False
        
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return False
        
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else float('inf')
        
        return circularity > self.circularity_threshold and aspect_ratio < 1.5

class AdaptiveTemplateGenerator:
    """自動生成vacuum cup模板"""
    
    def __init__(self):
        self.template_sizes = [16, 20, 24, 28, 32]
        
    def generate_synthetic_templates(self) -> Dict[str, np.ndarray]:
        """生成合成的vacuum cup模板"""
        templates = {}
        
        for size in self.template_sizes:
            templates[f"circle_{size}"] = self._create_circle_template(size)
            templates[f"cross_{size}"] = self._create_cross_template(size)
            templates[f"dot_{size}"] = self._create_dot_template(size)
        
        return templates
    
    def _create_circle_template(self, size: int) -> np.ndarray:
        """創建圓形模板"""
        template = np.ones((size, size), dtype=np.uint8) * 255
        center = size // 2
        radius = size // 2 - 2
        cv2.circle(template, (center, center), radius, 0, 2)
        return template
    
    def _create_cross_template(self, size: int) -> np.ndarray:
        """創建帶十字的圓形模板"""
        template = self._create_circle_template(size)
        center = size // 2
        cv2.line(template, (center - 4, center), (center + 4, center), 0, 1)
        cv2.line(template, (center, center - 4), (center, center + 4), 0, 1)
        return template
    
    def _create_dot_template(self, size: int) -> np.ndarray:
        """創建帶中心點的圓形模板"""
        template = self._create_circle_template(size)
        center = size // 2
        cv2.circle(template, (center, center), 2, 0, -1)
        return template

class AdaptiveVacuumCupDetector:
    """使用多模板的自適應偵測器"""
    
    def __init__(self, threshold=0.5):
        self.template_generator = AdaptiveTemplateGenerator()
        self.templates = self.template_generator.generate_synthetic_templates()
        self.threshold = threshold
        
    def detect_vacuum_cups(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """使用多個合成模板偵測vacuum cup"""
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return []
        
        all_matches = []
        
        for template_name, template in self.templates.items():
            matches = self._match_template(img, template)
            all_matches.extend(matches)
        
        final_matches = self._remove_overlapping_matches(all_matches)
        print(f"自適應模板偵測找到 {len(final_matches)} 個vacuum cup")
        return final_matches
    
    def _match_template(self, img: np.ndarray, template: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """單一模板匹配"""
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= self.threshold)
        
        matches = []
        h, w = template.shape
        for pt in zip(*locations[::-1]):
            matches.append((pt[0], pt[1], w, h))
        
        return matches
    
    def _remove_overlapping_matches(self, matches: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """移除重疊的匹配結果"""
        if not matches:
            return []
        
        from template_matcher import _non_max_suppression
        return _non_max_suppression(np.array(matches), 0.3)

class HybridVacuumCupDetector:
    """結合多種方法的混合偵測器"""
    
    def __init__(self):
        self.geometric_detector = GeometricVacuumCupDetector()
        self.contour_detector = ContourVacuumCupDetector()
        self.adaptive_detector = AdaptiveVacuumCupDetector()
        
    def detect_vacuum_cups(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """使用多種方法綜合偵測"""
        print(f"開始混合偵測: {os.path.basename(image_path)}")
        
        # 各種方法偵測
        geometric_results = self.geometric_detector.detect_vacuum_cups(image_path)
        contour_results = self.contour_detector.detect_vacuum_cups(image_path)
        adaptive_results = self.adaptive_detector.detect_vacuum_cups(image_path)
        
        # 融合結果
        all_detections = {
            'geometric': geometric_results,
            'contour': contour_results,
            'adaptive': adaptive_results
        }
        
        final_results = self._fusion_vote(all_detections)
        print(f"混合偵測最終結果: {len(final_results)} 個vacuum cup")
        
        return final_results
    
    def _fusion_vote(self, detections: Dict[str, List]) -> List[Tuple[int, int, int, int]]:
        """投票融合多種偵測結果"""
        all_boxes = []
        for method, boxes in detections.items():
            for box in boxes:
                all_boxes.append((box, method))
        
        if not all_boxes:
            return []
        
        clusters = self._cluster_detections(all_boxes)
        
        final_results = []
        for cluster in clusters:
            if len(cluster) >= 1:  # 至少一種方法同意（可調整為2要求更嚴格）
                center_box = self._get_cluster_center([item[0] for item in cluster])
                final_results.append(center_box)
        
        return final_results
    
    def _cluster_detections(self, detections: List) -> List[List]:
        """將相近的偵測結果分群"""
        clusters = []
        threshold_distance = 25
        
        for box, method in detections:
            x, y, w, h = box
            center_x, center_y = x + w//2, y + h//2
            
            assigned = False
            for cluster in clusters:
                if cluster:
                    cluster_center = self._get_cluster_center([item[0] for item in cluster])
                    cluster_x = cluster_center[0] + cluster_center[2]//2
                    cluster_y = cluster_center[1] + cluster_center[3]//2
                    
                    distance = np.sqrt((center_x - cluster_x)**2 + (center_y - cluster_y)**2)
                    if distance < threshold_distance:
                        cluster.append((box, method))
                        assigned = True
                        break
            
            if not assigned:
                clusters.append([(box, method)])
        
        return clusters
    
    def _get_cluster_center(self, boxes: List) -> Tuple[int, int, int, int]:
        """計算群集的中心box"""
        if not boxes:
            return (0, 0, 0, 0)
        
        xs = [box[0] for box in boxes]
        ys = [box[1] for box in boxes]
        ws = [box[2] for box in boxes]
        hs = [box[3] for box in boxes]
        
        return (int(np.mean(xs)), int(np.mean(ys)), int(np.mean(ws)), int(np.mean(hs)))
