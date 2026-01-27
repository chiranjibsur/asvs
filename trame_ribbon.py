import os
import sys
import vtk
import json
import math

# Trame imports
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vuetify, html
# Use trame_vtklocal for WASM-based rendering
from trame_vtklocal.widgets import vtklocal

# -------------------------------------------------------------------------
# Configuration Constants
# -------------------------------------------------------------------------
# Ribbon geometry
POINTS_PER_RESIDUE = 10  # Approximate points per residue in ribbon geometry

# Hotspot thresholds and color mapping
LOW_HOTSPOT_THRESHOLD = 0.15    # Below this is "low" hotspot (blue)
HIGH_HOTSPOT_THRESHOLD = 0.25   # Above this is "high" hotspot (red)
HOTSPOT_MARKER_THRESHOLD = 0.25 # Show marker spheres above this value

# Color scaling factors
LOW_COLOR_SCALE = 1000   # Scaling for low hotspot colors
HIGH_COLOR_SCALE = 400   # Scaling for high hotspot colors

# Picking parameters
PICKING_THRESHOLD_ANGSTROMS = 5.0  # Maximum distance for residue selection

# Render window dimensions
RENDER_WINDOW_WIDTH = 1000
RENDER_WINDOW_HEIGHT = 800

# -------------------------------------------------------------------------
# Global state for interactivity
# -------------------------------------------------------------------------
hotspot_data = {}
ca_positions = []
residue_info_list = []
selected_residue_idx = -1
measurement_mode = ""  # "", "distance", "angle"
measurement_points = []
hotspot_spheres = []

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
# Load Hotspot Data
# -------------------------------------------------------------------------
def load_hotspot_data():
    """Load hotspot data from JSON file if available."""
    global hotspot_data
    hotspot_file = "viewer/hotspots_residue.json"
    
    if os.path.exists(hotspot_file):
        try:
            with open(hotspot_file, 'r') as f:
                data = json.load(f)
                # Get frame 0 data
                if "0" in data:
                    hotspot_data = data["0"]
                    print(f"Loaded hotspot data for {len(hotspot_data)} residues")
                    return True
        except Exception as e:
            print(f"Error loading hotspot data: {e}")
    
    return False

# -------------------------------------------------------------------------
# Extract CA Positions and Residue Info
# -------------------------------------------------------------------------
def extract_residue_info(pdb_reader):
    """Extract CA positions and residue information from PDB."""
    global ca_positions, residue_info_list
    
    ca_positions = []
    residue_info_list = []
    
    output = pdb_reader.GetOutput()
    
    for i in range(output.GetNumberOfPoints()):
        point = output.GetPoint(i)
        ca_positions.append(point)
        
        # Extract residue info (simplified)
        residue_info_list.append({
            'index': i,
            'resnum': i + 1,
            'resname': 'RES',  # PDB reader doesn't easily expose this
            'chain': 'A'
        })
    
    print(f"Extracted {len(ca_positions)} CA positions")

# -------------------------------------------------------------------------
# VTK Pipeline with Hotspot Coloring
# -------------------------------------------------------------------------
def build_vtk_pipeline(pdb_path):
    """Build VTK pipeline with interactive protein ribbon and hotspot visualization."""
    print(f"Loading PDB: {pdb_path}")
    
    # Read PDB
    reader = vtk.vtkPDBReader()
    reader.SetFileName(pdb_path)
    reader.Update()
    
    # Extract residue information
    extract_residue_info(reader)
    
    # Create protein ribbon
    ribbon = vtk.vtkProteinRibbonFilter()
    ribbon.SetInputConnection(reader.GetOutputPort())
    ribbon.Update()
    
    # Create color array for hotspots
    colors = vtk.vtkUnsignedCharArray()
    colors.SetNumberOfComponents(3)
    colors.SetName("Colors")
    
    num_points = ribbon.GetOutput().GetNumberOfPoints()
    
    # Color based on hotspot data
    for i in range(num_points):
        # Map point index to residue index (ribbon has ~POINTS_PER_RESIDUE points per residue)
        residue_idx = min(i // POINTS_PER_RESIDUE, len(ca_positions) - 1)
        
        hotspot_value = 0.0
        if str(residue_idx) in hotspot_data:
            hotspot_value = float(hotspot_data[str(residue_idx)])
        
        # Color gradient: Blue (low) -> White (medium) -> Red (high)
        if hotspot_value < LOW_HOTSPOT_THRESHOLD:
            # Low: Blue
            r = int(100 + hotspot_value * LOW_COLOR_SCALE)
            g = int(100 + hotspot_value * LOW_COLOR_SCALE)
            b = 255
        elif hotspot_value > HIGH_HOTSPOT_THRESHOLD:
            # High: Red
            excess = hotspot_value - HIGH_HOTSPOT_THRESHOLD
            r = 255
            g = int(255 - excess * HIGH_COLOR_SCALE)
            b = int(255 - excess * HIGH_COLOR_SCALE)
        else:
            # Medium: White
            r, g, b = 255, 255, 255
        
        colors.InsertNextTuple3(r, g, b)
    
    ribbon.GetOutput().GetPointData().SetScalars(colors)
    
    # Mapper for ribbon
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(ribbon.GetOutputPort())
    mapper.SetScalarModeToUsePointData()
    
    # Actor for ribbon
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    
    # Create renderer
    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.SetBackground(0.1, 0.2, 0.4)
    
    # Add hotspot sphere markers for high-hotspot residues
    add_hotspot_markers(renderer)
    
    renderer.ResetCamera()
    
    # Create render window
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.SetSize(RENDER_WINDOW_WIDTH, RENDER_WINDOW_HEIGHT)
    
    return render_window, renderer

# -------------------------------------------------------------------------
# Add Hotspot Markers (Interactive Spheres)
# -------------------------------------------------------------------------
def add_hotspot_markers(renderer):
    """Add sphere markers at high-hotspot residues for visual emphasis."""
    global hotspot_spheres
    
    for i, pos in enumerate(ca_positions):
        if str(i) in hotspot_data:
            hotspot_value = float(hotspot_data[str(i)])
            
            if hotspot_value > HOTSPOT_MARKER_THRESHOLD:
                # Create sphere at high-hotspot position
                sphere = vtk.vtkSphereSource()
                sphere.SetCenter(pos)
                sphere.SetRadius(0.8)  # Visible but not overwhelming
                sphere.SetThetaResolution(16)
                sphere.SetPhiResolution(16)
                
                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputConnection(sphere.GetOutputPort())
                
                actor = vtk.vtkActor()
                actor.SetMapper(mapper)
                
                # Color intensity based on hotspot value
                intensity = min(1.0, (hotspot_value - HOTSPOT_MARKER_THRESHOLD) * 3)
                actor.GetProperty().SetColor(1.0, 0.5 - intensity * 0.5, 0.0)  # Orange to red
                actor.GetProperty().SetOpacity(0.6)
                
                renderer.AddActor(actor)
                hotspot_spheres.append((actor, i, hotspot_value))

# -------------------------------------------------------------------------
# Picking and Interaction
# -------------------------------------------------------------------------
def pick_residue_at_position(renderer, x, y, width, height):
    """Pick a residue at the given screen coordinates."""
    global selected_residue_idx, ca_positions
    
    # Create picker
    picker = vtk.vtkCellPicker()
    picker.SetTolerance(0.005)
    
    # Perform pick
    picker.Pick(x, height - y, 0, renderer)
    
    if picker.GetCellId() >= 0:
        picked_pos = picker.GetPickPosition()
        
        # Find nearest CA position
        min_dist = float('inf')
        nearest_idx = -1
        
        for i, ca_pos in enumerate(ca_positions):
            dist = math.sqrt(
                (picked_pos[0] - ca_pos[0])**2 +
                (picked_pos[1] - ca_pos[1])**2 +
                (picked_pos[2] - ca_pos[2])**2
            )
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i
        
        # Only select if within reasonable distance threshold
        if min_dist < PICKING_THRESHOLD_ANGSTROMS:
            selected_residue_idx = nearest_idx
            return nearest_idx
    
    return -1

def create_selection_sphere(renderer, position):
    """Create a yellow sphere to highlight selected residue."""
    sphere = vtk.vtkSphereSource()
    sphere.SetCenter(position)
    sphere.SetRadius(1.2)
    sphere.SetThetaResolution(20)
    sphere.SetPhiResolution(20)
    
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())
    
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(1.0, 1.0, 0.0)  # Yellow
    actor.GetProperty().SetOpacity(0.7)
    
    renderer.AddActor(actor)
    return actor

# -------------------------------------------------------------------------
# Measurement Tools
# -------------------------------------------------------------------------
def calculate_distance(pos1, pos2):
    """Calculate distance between two positions."""
    return math.sqrt(
        (pos1[0] - pos2[0])**2 +
        (pos1[1] - pos2[1])**2 +
        (pos1[2] - pos2[2])**2
    )

def calculate_angle(pos1, pos2, pos3):
    """Calculate angle at pos2 formed by pos1-pos2-pos3."""
    # Vectors from pos2 to pos1 and pos3
    v1 = [pos1[i] - pos2[i] for i in range(3)]
    v2 = [pos3[i] - pos2[i] for i in range(3)]
    
    # Dot product and magnitudes
    dot = sum(v1[i] * v2[i] for i in range(3))
    mag1 = math.sqrt(sum(v1[i]**2 for i in range(3)))
    mag2 = math.sqrt(sum(v2[i]**2 for i in range(3)))
    
    # Angle in degrees
    if mag1 * mag2 == 0:
        return 0.0
    
    cos_angle = dot / (mag1 * mag2)
    cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to [-1, 1]
    
    return math.degrees(math.acos(cos_angle))

# -------------------------------------------------------------------------
# Trame App Setup
# -------------------------------------------------------------------------
def main():
    # Path to your PDB file
    target_pdb = "/mnt/c/Users/KIIT0001/OneDrive/Desktop/WebSites/asvs/static/examples/1cbs.pdb"
    
    # Try multiple possible paths
    pdb_paths = [
        target_pdb,
        "static/examples/1cbs.pdb",
        "viewer/topology.pdb"
    ]
    
    pdb_file = None
    for path in pdb_paths:
        if os.path.exists(path):
            pdb_file = path
            break
    
    if not pdb_file:
        pdb_file = get_pdb_file(target_pdb)
    
    if not pdb_file:
        print("Error: Could not find a PDB file to load.")
        return
    
    # Load hotspot data
    load_hotspot_data()

    # Initialize Trame Server with trame-vtklocal support
    server = get_server(client_type="vue2")
    state, ctrl = server.state, server.controller
    
    # Initialize state
    state.selected_residue = ""
    state.hotspot_info = ""
    state.measurement_result = ""
    state.status_message = "Click on the ribbon to select a residue"
    
    # Build VTK pipeline
    render_window, renderer = build_vtk_pipeline(pdb_file)
    
    # Selection tracking
    selection_actor = None
    
    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------
    
    @ctrl.add("on_click")
    def handle_click(event):
        """Handle click events on the 3D view."""
        global selected_residue_idx, selection_actor, measurement_mode, measurement_points
        
        # Extract coordinates from event
        x = event.get("x", 0)
        y = event.get("y", 0)
        
        # Use configured window dimensions
        width = RENDER_WINDOW_WIDTH
        height = RENDER_WINDOW_HEIGHT
        
        print(f"Click at ({x}, {y})")
        
        # Pick residue
        residue_idx = pick_residue_at_position(renderer, x, y, width, height)
        
        if residue_idx >= 0:
            # Remove old selection sphere
            if selection_actor:
                renderer.RemoveActor(selection_actor)
            
            # Create new selection sphere
            selection_actor = create_selection_sphere(renderer, ca_positions[residue_idx])
            
            # Get hotspot value
            hotspot_value = 0.0
            if str(residue_idx) in hotspot_data:
                hotspot_value = float(hotspot_data[str(residue_idx)])
            
            # Update state
            residue = residue_info_list[residue_idx]
            state.selected_residue = f"{residue['resname']}{residue['resnum']} (Chain {residue['chain']})"
            state.hotspot_info = f"Hotspot Score: {hotspot_value:.3f}"
            
            # Measurement mode handling
            if measurement_mode == "distance":
                measurement_points.append(residue_idx)
                if len(measurement_points) == 2:
                    dist = calculate_distance(
                        ca_positions[measurement_points[0]],
                        ca_positions[measurement_points[1]]
                    )
                    state.measurement_result = f"Distance: {dist:.2f} Å"
                    state.status_message = f"Distance measured: {dist:.2f} Å"
                    measurement_mode = ""
                    measurement_points = []
                else:
                    state.status_message = "Select second residue for distance measurement"
            
            elif measurement_mode == "angle":
                measurement_points.append(residue_idx)
                if len(measurement_points) == 3:
                    angle = calculate_angle(
                        ca_positions[measurement_points[0]],
                        ca_positions[measurement_points[1]],
                        ca_positions[measurement_points[2]]
                    )
                    state.measurement_result = f"Angle: {angle:.1f}°"
                    state.status_message = f"Angle measured: {angle:.1f}°"
                    measurement_mode = ""
                    measurement_points = []
                else:
                    state.status_message = f"Select residue {len(measurement_points) + 1} of 3 for angle"
            
            else:
                # Provide guidance based on hotspot value
                if hotspot_value > 0.25:
                    state.status_message = f"High hotspot detected! Use measurement tools to analyze this residue."
                elif hotspot_value > 0.15:
                    state.status_message = f"Moderate hotspot. Click 'Distance' or 'Angle' to measure."
                else:
                    state.status_message = f"Low hotspot region. Selected residue {residue_idx + 1}."
            
            # Force update
            ctrl.view_update()
    
    @ctrl.add("measure_distance")
    def start_distance_measurement():
        """Start distance measurement mode."""
        global measurement_mode, measurement_points
        measurement_mode = "distance"
        measurement_points = []
        state.status_message = "Select two residues to measure distance"
        state.measurement_result = ""
    
    @ctrl.add("measure_angle")
    def start_angle_measurement():
        """Start angle measurement mode."""
        global measurement_mode, measurement_points
        measurement_mode = "angle"
        measurement_points = []
        state.status_message = "Select three residues to measure angle"
        state.measurement_result = ""
    
    @ctrl.add("clear_measurement")
    def clear_measurement():
        """Clear measurement mode."""
        global measurement_mode, measurement_points
        measurement_mode = ""
        measurement_points = []
        state.measurement_result = ""
        state.status_message = "Measurement cleared"

    # --- UI Layout ---
    with SinglePageLayout(server) as layout:
        layout.title.set_text("Interactive Trame Ribbon Viewer with Dynamic Hotspots")
        
        # Toolbar
        with layout.toolbar:
            vuetify.VSpacer()
            vuetify.VBtn(
                "Distance",
                click=ctrl.measure_distance,
                small=True,
                classes="mx-1"
            )
            vuetify.VBtn(
                "Angle",
                click=ctrl.measure_angle,
                small=True,
                classes="mx-1"
            )
            vuetify.VBtn(
                "Clear",
                click=ctrl.clear_measurement,
                small=True,
                classes="mx-1",
                outlined=True
            )

        # Main content
        with layout.content:
            with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
                with vuetify.VRow(no_gutters=True, classes="fill-height"):
                    # 3D View (75% width)
                    with vuetify.VCol(cols=9, classes="pa-0"):
                        html.Div(
                            style="width: 100%; height: 100%; position: relative;",
                            children=[
                                vtklocal.LocalView(
                                    render_window,
                                    ref="view",
                                    namespace="ribbonNS",
                                    style="width: 100%; height: 100%;",
                                    on_click=ctrl.on_click
                                )
                            ],
                        )
                    
                    # Info Panel (25% width)
                    with vuetify.VCol(cols=3, classes="pa-2"):
                        with vuetify.VCard(classes="fill-height"):
                            vuetify.VCardTitle("Residue Information")
                            
                            with vuetify.VCardText():
                                html.Div([
                                    html.H4("Selected Residue:"),
                                    html.P("{{ selected_residue }}", style="font-weight: bold;"),
                                    
                                    html.H4("Hotspot Score:"),
                                    html.P("{{ hotspot_info }}", style="color: #d32f2f;"),
                                    
                                    html.Hr(),
                                    
                                    html.H4("Measurement:"),
                                    html.P("{{ measurement_result }}", style="color: #1976d2;"),
                                    
                                    html.Hr(),
                                    
                                    html.H4("Legend:"),
                                    html.Ul([
                                        html.Li("Blue: Low hotspot (< 0.15)"),
                                        html.Li("White: Medium hotspot (0.15 - 0.25)"),
                                        html.Li("Red: High hotspot (> 0.25)"),
                                        html.Li("Orange Spheres: Major hotspot sites")
                                    ])
                                ])
        
        # Footer
        with layout.footer:
            html.Div(
                "{{ status_message }}",
                style="padding: 10px; font-size: 14px; color: #666;"
            )

    # Start server
    print("Starting server on http://localhost:8787")
    server.start(port=8787, address="0.0.0.0")

if __name__ == "__main__":
    main()
