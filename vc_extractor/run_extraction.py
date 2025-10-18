from coordinate_matcher import VacuumCupCoordinateExtractor
import os
import glob

def run_extraction(detection_method="hybrid"):
    """
    執行座標擷取
    Args:
        detection_method: 偵測方法 ("template", "geometric", "contour", "adaptive", "hybrid")
    """

    pdf_dir = r"C:\Users\a1246807\Plunger_extraction\pdf"
    template_dir = r"C:\Users\a1246807\Plunger_extraction\templates"
    template_paths = glob.glob(os.path.join(template_dir, "*.png"))
    output_dir = f"extraction_results_{detection_method}"
    pdf_paths = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    
    # 建立並執行擷取器
    extractor = VacuumCupCoordinateExtractor(
        template_paths=template_paths,
        detection_method=detection_method
    )
    all_results = []
    for pdf_path in pdf_paths:
        result = extractor.process_pdf_page(pdf_path, output_dir=output_dir)
        all_results.append((pdf_path, result))
    
    return all_results


if __name__ == "__main__":
    method = "geometric"  # 可改為 "template", "geometric", "contour", "adaptive"
    results = run_extraction(method)
    for pdf_path, result in results:
        print(f"\n{method} 方法總共找到 {result['total_vacuum_cups']} 個vacuum cup:")
        for cup in result['vacuum_cups']:
            print(f"  Cup {cup['id']}: X={cup['coordinates']['x']}, Y={cup['coordinates']['y']}")