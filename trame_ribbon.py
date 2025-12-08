import os
import sys
import vtk

# Trame imports
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import html
# Use trame_vtklocal for WASM-based rendering
from trame_vtklocal.widgets import vtklocal

# -------------------------------------------------------------------------
# Helper: Download a sample PDB if your file doesn't exist
# -------------------------------------------------------------------------
def get_pdb_file(filepath):
    if os.path.exists(filepath):
        return filepath
    
    sample_path = "1crn.pdb"
    if not os.path.exists(sample_path):
        print("Input PDB not found. Downloading sample 1CRN.pdb...")
        try:
            import urllib.request
            url = "https://files.rcsb.org/download/1CRN.pdb"
            urllib.request.urlretrieve(url, sample_path)
            return sample_path
        except Exception as e:
            print(f"Failed to download sample: {e}")
            return None
    return sample_path

# -------------------------------------------------------------------------
# VTK Pipeline
# -------------------------------------------------------------------------
def build_vtk_pipeline(pdb_path):
    print(f"Loading PDB: {pdb_path}")
    reader = vtk.vtkPDBReader()
    reader.SetFileName(pdb_path)
    reader.Update()

    ribbon = vtk.vtkProteinRibbonFilter()
    ribbon.SetInputConnection(reader.GetOutputPort())
    ribbon.Update()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(ribbon.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.SetBackground(0.1, 0.2, 0.4)
    renderer.ResetCamera()

    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.SetSize(1000, 800)  # IMPORTANT

    return render_window

# -------------------------------------------------------------------------
# Trame App Setup
# -------------------------------------------------------------------------
def main():
    # Path to your PDB file
    target_pdb = "/mnt/c/Users/KIIT0001/OneDrive/Desktop/WebSites/asvs/static/examples/1cbs.pdb"
    pdb_file = get_pdb_file(target_pdb)

    if not pdb_file:
        print("Error: Could not find a PDB file to load.")
        return

    # Initialize Trame Server with trame-vtklocal support
    server = get_server(client_type="vue2")
    state, ctrl = server.state, server.controller

    render_window = build_vtk_pipeline(pdb_file)

    # --- UI Layout ---
    with SinglePageLayout(server) as layout:
        layout.title.set_text("Trame Ribbon Viewer")

        # IMPORTANT: Explicit container with full height
        with layout.content:
            html.Div(
                style="width: 100%; height: 100%; position: relative;",
                children=[
                    vtklocal.LocalView(
                        render_window,
                        ref="view",
                        namespace="ribbonNS",
                        style="width: 100%; height: 100%;"
                    )
                ],
            )

    # Start server
    print("Starting server on http://localhost:8787")
    server.start(port=8787, address="0.0.0.0")

if __name__ == "__main__":
    main()
