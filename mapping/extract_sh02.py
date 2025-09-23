import ezdxf
import matplotlib.pyplot as plt
from typing import List, Optional, Tuple

def extract_layers_from_dxf(dxf_path: str) -> List[str]:
    """Extract all layer names from a DXF file."""
    doc = ezdxf.readfile(dxf_path)
    layers = [layer.dxf.name for layer in doc.layers]
    return layers

def plot_dxf_layers(
    dxf_path: str, 
    layers_to_plot: Optional[List[str]] = None, 
    figsize: Tuple[int, int] = (10, 10),
    save_path: Optional[str] = None,
    show_plot: bool = False
):
    """
    Plot designated layers of a DXF file using matplotlib.
    - dxf_path: path to the DXF file.
    - layers_to_plot: list of layer names to plot. If None, plot all layers.
    - figsize: figure size for matplotlib.
    - save_path: if set, save the plot to this path.
    - show_plot: if True, display the plot window.
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Collect all geometry by layer
    layer_entities = {}
    for e in msp:
        layer = e.dxf.layer
        if (layers_to_plot is None) or (layer in layers_to_plot):
            layer_entities.setdefault(layer, []).append(e)

    colors = [
        "#d32f2f", "#1976d2", "#3A9C3E", "#fbc02d", "#7b1fa2",
        "#0288d1", "#c2185b", "#ffa000", "#00796b", "#afb42b", "#303f9f"
    ]
    layer_color_map = {layer: colors[i % len(colors)] for i, layer in enumerate(layer_entities)}

    plt.figure(figsize=figsize)
    ax = plt.gca()
    plotted_any = False

    for i, (layer, entities) in enumerate(layer_entities.items()):
        color = layer_color_map[layer]
        for e in entities:
            try:
                if e.dxftype() == "LINE":
                    x = [e.dxf.start[0], e.dxf.end[0]]
                    y = [e.dxf.start[1], e.dxf.end[1]]
                    ax.plot(x, y, color=color, lw=1, label=layer if i == 0 else "")
                    plotted_any = True
                elif e.dxftype() == "CIRCLE":
                    circle = plt.Circle((e.dxf.center[0], e.dxf.center[1]), e.dxf.radius, color=color, fill=False, lw=1)
                    ax.add_patch(circle)
                    plotted_any = True
                elif e.dxftype() == "ARC":
                    from matplotlib.patches import Arc
                    start_angle = e.dxf.start_angle
                    end_angle = e.dxf.end_angle
                    arc = Arc(
                        (e.dxf.center[0], e.dxf.center[1]),
                        width=2*e.dxf.radius,
                        height=2*e.dxf.radius,
                        angle=0,
                        theta1=start_angle,
                        theta2=end_angle,
                        color=color,
                        lw=1
                    )
                    ax.add_patch(arc)
                    plotted_any = True
                elif e.dxftype() == "LWPOLYLINE" or e.dxftype() == "POLYLINE":
                    points = e.get_points("xy") if hasattr(e, 'get_points') else e.points()
                    x, y = zip(*[(p[0], p[1]) for p in points])
                    ax.plot(x, y, color=color, lw=1)
                    plotted_any = True
                # Add more DXF entity types as needed
            except Exception as ex:
                print(f"Error plotting entity {e.dxftype()} on layer {layer}: {ex}")

    if not plotted_any:
        print("No geometry plotted. Check your layer names and DXF content.")

    ax.set_aspect('equal')
    ax.autoscale(enable=True)
    ax.set_title("DXF Layer Visualization")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Layer plot saved to {save_path}")
    if show_plot:
        plt.show()
    plt.close()

if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extract_dxf_layers_matplot.py <dxf_path> [layer1 layer2 ...]")
        sys.exit(1)
    dxf_path = sys.argv[1]
    layers = sys.argv[2:] if len(sys.argv) > 2 else None
    print("Available layers in DXF:", extract_layers_from_dxf(dxf_path))
    plot_dxf_layers(dxf_path, layers_to_plot=layers, show_plot=True)