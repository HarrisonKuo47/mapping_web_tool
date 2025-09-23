import ezdxf
import os
from typing import List
import matplotlib.pyplot as plot

def extract_dxf_layers(dxf_file_path: str) -> List[str]:
    """Extract all available layers from DXF file"""
    try:
        doc = ezdxf.readfile(dxf_file_path)
        layers = []
        for layer in doc.layers:
            layer_name = layer.dxf.name
            layers.append(layer_name)
        return sorted(layers)

    except Exception as e:
        print(f"Error extracting layers: {e}")
        return []
    
def create_dynamic_layer_file(selected_layers: List[str], output_path: str):
    """Create a temporary layer file with selected layers"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            for layer in selected_layers:
                f.write(f"{layer}\n")
            f.write("0")  # End marker
        return True
    except Exception as e:
        print(f"Error creating layer file: {e}")
        return False
    
if __name__ == "__main__":
    extract_dxf_layers(r'C:\Users\a1246807\Mapping_Tool_webapp\uploads\leadframes\TITL_TSSOP_HYDE_Strip_Tooling.dxf')