import os
import pandas as pd

OUTPUT_FOLDER = r"C:\Users\a1246807\Plunger_extraction\Mapping_Tool\output"

def check_suitable_handler_kits_from_reports():
    # For each LF (DXF output subfolder)
    for dxf_name in os.listdir(OUTPUT_FOLDER):
        subfolder = os.path.join(OUTPUT_FOLDER, dxf_name)
        if not os.path.isdir(subfolder):
            continue

        # Find all overlap analysis report files in this subfolder
        reports = [
            f for f in os.listdir(subfolder)
            if f.endswith('_overlap_analysis_report.xlsx')
        ]
        if not reports:
            print(f"[{dxf_name}] No overlap report files found, skipping.")
            continue

        suitable_kits = []
        for report in reports:
            report_path = os.path.join(subfolder, report)
            try:
                # Read overlap report, sheet 'Overlap_Details' (mapping.py uses this)
                df = pd.read_excel(report_path, sheet_name='Overlap_Details')
                # Suitable if all cups are non-overlapping
                if (df['Is_Overlapping'] == False).all():
                    # Extract handler kit name from report file name
                    # e.g., "abc_plunger_vac_cups_overlap_analysis_report.xlsx" -> "plunger_vac_cups"
                    kit_name = report.replace(f"{dxf_name}_", "").replace("_overlap_analysis_report.xlsx", "")
                    suitable_kits.append(kit_name)
            except Exception as e:
                print(f"  [Warning] Failed to read {report}: {e}")

        # Report result for this DXF
        if suitable_kits:
            print(f"\n[L.F.: {dxf_name}] Suitable Handler Kit designs found:")
            for kit in suitable_kits:
                print(f"  - {kit}")
        else:
            print(f"\n[L.F.: {dxf_name}] None of the Handler Kit designs are suitable for {dxf_name}")

if __name__ == "__main__":
    check_suitable_handler_kits_from_reports()