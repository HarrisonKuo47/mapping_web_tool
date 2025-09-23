import os
import pandas as pd
import glob
import re
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def parse_wkt_linestring(wkt_str):
    coords = re.findall(r'[-+]?\d*\.\d+|\d+', wkt_str)
    if len(coords) < 4:
        return None
    x1, y1, x2, y2 = map(float, coords[:4])
    return (x1, y1, x2, y2)

def midpoint(val1, val2):
    return (val1 + val2) / 2

def coordinate_trans(output_folder):
    input_files = glob.glob(os.path.join(output_folder, "*_shapes_summary.xlsx"))
    for input_excel in input_files:
        base = os.path.basename(input_excel)
        if not base.endswith("_shapes_summary.xlsx"):
            continue
        dxf_name = base.replace("_shapes_summary.xlsx", "")
        subfolder = os.path.join(output_folder, dxf_name)
        os.makedirs(subfolder, exist_ok=True)

        output_excel = os.path.join(subfolder, f"{dxf_name}_with_origin.xlsx")
        df = pd.read_excel(input_excel)

        df_dim = df[df['Type'] == 'Dimension'].copy()
        df_dim = df_dim[df_dim['WKT'].notnull() & df_dim['WKT'].str.contains("LINESTRING")]

        df_dim[['x1', 'y1', 'x2', 'y2']] = df_dim['WKT'].apply(
            lambda wkt_str: pd.Series(parse_wkt_linestring(wkt_str)))
        df_dim['delta_x'] = (df_dim['x2'] - df_dim['x1']).abs()
        df_dim['delta_y'] = (df_dim['y2'] - df_dim['y1']).abs()
        df_dim['max_delta'] = df_dim[['delta_x', 'delta_y']].max(axis=1)

        df_dim = df_dim[df_dim['max_delta'] > 2]  # threshold

        width_row = df_dim.loc[df_dim['delta_x'].idxmax()]
        height_row = df_dim.loc[df_dim['delta_y'].idxmax()]

        mid_x = midpoint(width_row['x1'], width_row['x2'])
        mid_y = midpoint(height_row['y1'], height_row['y2'])
        new_origin = (mid_x, mid_y)

        x_min, x_max = sorted([width_row['x1'], width_row['x2']])
        y_min, y_max = sorted([height_row['y1'], height_row['y2']])

        boundary_info = pd.DataFrame({
            'Item': ['x_min', 'x_max', 'y_min', 'y_max', 'mid_x', 'mid_y'],
            'Value': [x_min, x_max, y_min, y_max, mid_x, mid_y]
        })
        boundary_info_file = os.path.join(subfolder, f"{dxf_name}_boundary.xlsx")
        boundary_info.to_excel(boundary_info_file, index=False)

        with pd.ExcelWriter(output_excel) as writer:
            df.to_excel(writer, index=False, sheet_name='AllShapes')
            df_dim.to_excel(writer, index=False, sheet_name='FilteredDimensions')
            summary = pd.DataFrame({
                'Item': ['Width ShapeID', 'Height ShapeID', 'Width Midpoint X', 'Height Midpoint Y', 'New Origin (mid_x, mid_y)'],
                'Value': [
                    width_row['ShapeID'],
                    height_row['ShapeID'],
                    mid_x,
                    mid_y,
                    new_origin
                ]
            })
            summary.to_excel(writer, index=False, sheet_name='OriginSummary')


def coordinate_trans_single(input_excel, output_folder, dxf_name):
    """Coordinate transformation with enhanced error handling for problematic geometries"""
    
    THRESHOLD = 2
    
    def safe_parse_wkt_linestring(wkt_str):
        """Safely parse WKT linestring with validation"""
        try:
            if pd.isnull(wkt_str) or not isinstance(wkt_str, str):
                return None
            
            coords = re.findall(r'[-+]?\d*\.\d+|\d+', str(wkt_str))
            if len(coords) < 4:
                logger.warning(f"Insufficient coordinates in WKT: {wkt_str[:50]}... (found {len(coords)} coords)")
                return None
            
            x1, y1, x2, y2 = map(float, coords[:4])
        
            return (x1, y1, x2, y2)
            
        except Exception as e:
            logger.warning(f"Error parsing WKT linestring: {e}")
            return None

    def midpoint(val1, val2):
        return (val1 + val2) / 2

    try:
        df = pd.read_excel(input_excel)
        logger.info(f"Loaded {len(df)} rows from {input_excel}")
        
        # Log available layers for debugging
        if 'Layer' in df.columns:
            unique_layers = df['Layer'].unique()
            logger.info(f"Available layers: {list(unique_layers)}")
            
            # Check if SH-01_DIM layer exists
            dim_layers = [layer for layer in unique_layers if 'SH-01_DIM' in str(layer)]
            logger.info(f"SH-01_DIM layers found: {dim_layers}")
        else:
            logger.warning("No 'Layer' column found in data")
        
        # Try SH-01_DIM first, then fallback to other methods
        boundary_data = None
        
        try:
            df_dim = df[(df['Type'] == 'Dimension') & (df['Layer'] == 'SH-01_DIM')].copy()
            logger.info(f"Found {len(df_dim)} dimension shapes in SH-01_DIM layer")
            
            if len(df_dim) > 0:
                df_dim = df_dim[df_dim['WKT'].notnull() & df_dim['WKT'].str.contains("LINESTRING", na=False)]
                logger.info(f"Found {len(df_dim)} linestring dimensions in SH-01_DIM layer")
                
                if len(df_dim) > 0:
                    # Parse coordinates with safe method
                    valid_coords = []
                    for idx, row in df_dim.iterrows():
                        coords = safe_parse_wkt_linestring(row['WKT'])
                        if coords is not None:
                            valid_coords.append({
                                'index': idx,
                                'x1': coords[0], 'y1': coords[1], 
                                'x2': coords[2], 'y2': coords[3]
                            })
                    
                    logger.info(f"Successfully parsed {len(valid_coords)} coordinate sets from SH-01_DIM")
                    
                    if len(valid_coords) > 0:
                        # Convert to DataFrame for processing
                        coords_df = pd.DataFrame(valid_coords)
                        coords_df['delta_x'] = (coords_df['x2'] - coords_df['x1']).abs()
                        coords_df['delta_y'] = (coords_df['y2'] - coords_df['y1']).abs()
                        coords_df['max_delta'] = coords_df[['delta_x', 'delta_y']].max(axis=1)
                        
                        # Apply threshold
                        coords_df = coords_df[coords_df['max_delta'] > THRESHOLD]
                        logger.info(f"Found {len(coords_df)} coordinate sets above threshold ({THRESHOLD})")
                        
                        if len(coords_df) > 0:
                            width_row = coords_df.loc[coords_df['delta_x'].idxmax()]
                            height_row = coords_df.loc[coords_df['delta_y'].idxmax()]
                            
                            mid_x = midpoint(width_row['x1'], width_row['x2'])
                            mid_y = midpoint(height_row['y1'], height_row['y2'])
                            
                            x_min, x_max = sorted([width_row['x1'], width_row['x2']])
                            y_min, y_max = sorted([height_row['y1'], height_row['y2']])
                            
                            boundary_data = {
                                'x_min': x_min, 'x_max': x_max,
                                'y_min': y_min, 'y_max': y_max,
                                'mid_x': mid_x, 'mid_y': mid_y
                            }
                            
                            logger.info(f"✅ Boundary extracted from SH-01_DIM: ({x_min:.3f},{y_min:.3f}) to ({x_max:.3f},{y_max:.3f})")
        
        except Exception as sh01_error:
            logger.warning(f"SH-01_DIM method failed: {sh01_error}")
        
        # Create and save boundary file
        boundary_info = pd.DataFrame({
            'Item': ['x_min', 'x_max', 'y_min', 'y_max', 'mid_x', 'mid_y'],
            'Value': [
                boundary_data['x_min'], boundary_data['x_max'], 
                boundary_data['y_min'], boundary_data['y_max'], 
                boundary_data['mid_x'], boundary_data['mid_y']
            ]
        })
        
        boundary_info_file = os.path.join(output_folder, f"{dxf_name}_boundary.xlsx")
        
    except Exception as e:
        logger.error(f"❌ Critical error in coordinate analysis for {dxf_name}: {e}")
        
    
def transform_vacuum_cups(dxf_subfolder, dxf_name, mid_x, mid_y, height_value, width_value, vacuum_cup_source_folder, ratio_base_height=90, ratio_base_width=270):
    vac_files = glob.glob(os.path.join(vacuum_cup_source_folder, "*.xlsx"))
    for vac_file in vac_files:
        vac_base = os.path.splitext(os.path.basename(vac_file))[0]
        vac_output = os.path.join(dxf_subfolder, f"{dxf_name}_{vac_base}_vac_cups.xlsx")
        try:
            df_vac = pd.read_excel(vac_file, header=1)
            df_vac = df_vac[['Vacuum cup', 'X', 'Y', 'Vacuum size', 'Shape']].dropna(subset=['X', 'Y'])
            relative_ratio_height = height_value / ratio_base_height
            relative_ratio_width = width_value / ratio_base_width
            df_vac['X_LF'] = mid_x + df_vac['X'] * relative_ratio_width
            df_vac['Y_LF'] = mid_y + df_vac['Y'] * relative_ratio_height
            df_vac_out = df_vac[['X', 'Y', 'X_LF', 'Y_LF', 'Vacuum size', 'Shape']]
            df_vac_out.to_excel(vac_output, index=False)
        except Exception as e:
            print(f"[{dxf_name}] Failed to process {vac_base}: {e}")

def batch_vacuum_cup_transform(output_folder, vacuum_cup_source_folder):
    dxf_subfolders = [os.path.join(output_folder, name)
                      for name in os.listdir(output_folder)
                      if os.path.isdir(os.path.join(output_folder, name))]
    for dxf_subfolder in dxf_subfolders:
        dxf_name = os.path.basename(dxf_subfolder)
        boundary_info_file = os.path.join(dxf_subfolder, f"{dxf_name}_boundary.xlsx")
        if not os.path.exists(boundary_info_file):
            print(f"[{dxf_name}] No boundary info found: {boundary_info_file}, skipping.")
            continue
        boundary_info = pd.read_excel(boundary_info_file)
        mid_x = float(boundary_info[boundary_info['Item'] == 'mid_x']['Value'].iloc[0])
        mid_y = float(boundary_info[boundary_info['Item'] == 'mid_y']['Value'].iloc[0])
        height_value = float(boundary_info[boundary_info['Item'] == 'y_max']['Value'].iloc[0]) - \
                       float(boundary_info[boundary_info['Item'] == 'y_min']['Value'].iloc[0])
        width_value = float(boundary_info[boundary_info['Item'] == 'x_max']['Value'].iloc[0]) - \
                      float(boundary_info[boundary_info['Item'] == 'x_min']['Value'].iloc[0])
        transform_vacuum_cups(
            dxf_subfolder, dxf_name,
            mid_x, mid_y, height_value, width_value, vacuum_cup_source_folder
        )