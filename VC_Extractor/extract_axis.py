import cv2
import pytesseract
import numpy as np
import re
import os

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_axis_labels_by_contours(image_path, rotate_angle=0, axis='x', params=None):
    if params is None:
        params = {}
    
    img = cv2.imread(image_path)
    if img is None:
        return []

    # --- 關鍵參數讀取 ---
    ADAPTIVE_BLOCK_SIZE = params.get('block', 31)
    ADAPTIVE_C_VALUE = params.get('c', 10)
    MORPH_KERNEL_W = params.get('k_w', 0)
    MORPH_KERNEL_H = params.get('k_h', 0)
    
    # 輪廓過濾參數
    MIN_H, MAX_H = params.get('h_range', (15, 50))
    MIN_W, MAX_W = params.get('w_range', (20, 300))
    MIN_AR, MAX_AR = params.get('ar_range', (1.0, 10.0))

    if ADAPTIVE_BLOCK_SIZE % 2 == 0:
        ADAPTIVE_BLOCK_SIZE += 1

    # --- 流程 ---
    img_rotated = cv2.rotate(img, {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}.get(rotate_angle, None)) if rotate_angle != 0 else img
    gray = cv2.cvtColor(img_rotated, cv2.COLOR_BGR2GRAY)
    
    binary_for_contour = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, ADAPTIVE_BLOCK_SIZE, ADAPTIVE_C_VALUE
    )

    if MORPH_KERNEL_W > 0 and MORPH_KERNEL_H > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (MORPH_KERNEL_W, MORPH_KERNEL_H))
        binary_for_contour = cv2.morphologyEx(binary_for_contour, cv2.MORPH_CLOSE, kernel)
    
    debug_contour_input_path = f'debug_contour_input_{axis}.png'
    cv2.imwrite(debug_contour_input_path, binary_for_contour)
    print(f"軸 [{axis}]: 二值圖已儲存: {debug_contour_input_path}")

    contours, _ = cv2.findContours(binary_for_contour, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"軸 [{axis}]: 找到 {len(contours)} 個初始輪廓。")

    results = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h if h > 0 else 0

        if not (MIN_H < h < MAX_H and MIN_W < w < MAX_W and MIN_AR < aspect_ratio < MAX_AR):
            continue
        
        roi = gray[y:y+h, x:x+w]
        raw_text = pytesseract.image_to_string(
            roi, config='--psm 7 -c tessedit_char_whitelist=0123456789.,+-±'
        ).strip()
        
        value = None
        m_full = re.match(r'^(\d{1,4}[.,]\d{1,3})', raw_text)
        m_simple = re.match(r'^(\d{1,4}[.,]?\d{1,3})', raw_text)
        
        if m_full: value = m_full.group(1)
        elif m_simple: value = m_simple.group(1)
        
        if value:
            results.append({'value': value, 'x': x + w // 2, 'y': y + h // 2, 'rot': rotate_angle})

    return results

def transform_coordinates_back(x, y, rotation, img_width, img_height):
    if rotation == 90: orig_x, orig_y = y, img_height - x
    elif rotation == 180: orig_x, orig_y = img_width - 1 - x, img_height - 1 - y
    elif rotation == 270: orig_x, orig_y = img_width - y, x
    else: orig_x, orig_y = x, y
    return orig_x, orig_y

def draw_labels_on_image(image_path, x_labels, y_labels, out_path):
    img = cv2.imread(image_path)
    if img is None: return
    img_height, img_width = img.shape[:2]
    
    for item in x_labels:
        orig_x, orig_y = transform_coordinates_back(item['x'], item['y'], 180, img_width, img_height)
        cv2.putText(img, str(item['value']), (orig_x, orig_y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    for item in y_labels:
        orig_x, orig_y = transform_coordinates_back(item['x'], item['y'], 90, img_width, img_height)
        cv2.putText(img, str(item['value']), (orig_x + 15, orig_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    cv2.imwrite(out_path, img)
    print(f"標註圖已儲存：{out_path}")

if __name__ == "__main__":
    test_path = r'C:\Users\harri\Downloads\Mapping_tool\302132426.png'
    out_img_path = test_path.replace('.png', '_labels_tuned.png')

    # ==================================================================
    # ===            請在這裡集中進行參數調校 (Tuning)             ===
    # ==================================================================
    
    # --- 預處理參數 ---
    # 建議從一個較小的值開始，目的是先分離所有輪廓
    PREPROCESS_PARAMS = {
        'block': 51,        # adaptiveThreshold 的區塊大小 (必須是奇數)
        'c': 20,            # adaptiveThreshold 的常數C (值越大，文字線條越細)
        'k_w': 0,           # 閉運算核心的寬度 (設為0則不做閉運算)
        'k_h': 0,           # 閉運算核心的高度 (設為0則不做閉運算)
    }

    # --- 輪廓幾何過濾參數 ---
    # 根據您期望的文字大小來設定
    CONTOUR_FILTERS = {
        'h_range': (0, 100),    # 高度範圍
        'w_range': (0, 250),   # 寬度範圍
        'ar_range': (0.5, 100)  # 寬高比範圍
    }

    # 合併所有參數
    ALL_PARAMS = {**PREPROCESS_PARAMS, **CONTOUR_FILTERS}

    # ==================================================================

    print("--- 開始使用輪廓分割策略進行辨識 ---")
    x_labels = extract_axis_labels_by_contours(test_path, rotate_angle=180, axis='x', params=ALL_PARAMS)
    y_labels = extract_axis_labels_by_contours(test_path, rotate_angle=90, axis='y', params=ALL_PARAMS)
    
    # --- 對結果進行去重 ---
    final_x_labels = [dict(t) for t in {tuple(d.items()) for d in x_labels}]
    final_y_labels = [dict(t) for t in {tuple(d.items()) for d in y_labels}]
    
    print("\n--- 最終結果 ---")
    print(f"X軸找到 {len(final_x_labels)} 個獨特座標: {[label['value'] for label in final_x_labels]}")
    print(f"Y軸找到 {len(final_y_labels)} 個獨特座標: {[label['value'] for label in final_y_labels]}")

    draw_labels_on_image(test_path, final_x_labels, final_y_labels, out_img_path)