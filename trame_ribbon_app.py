import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
import threading
from typing import Dict, List, Optional, Tuple

import vtk
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk as vtk_widgets
from trame.widgets import vuetify, html

from trajectory_adapter import get_adapter

# -----------------------------------------------------------------------------
# Data loading helpers
# -----------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.dirname(__file__))
VIEWER_DIR = os.path.join(ROOT, "viewer")

HOTSPOTS_RES_PATH = os.environ.get(
    "ASVS_HOTSPOTS_RES",
    os.path.join(VIEWER_DIR, "hotspots_residue.json"),
)
ANOMALY_PATH = os.environ.get(
    "ASVS_ANOMALY",
    os.path.join(VIEWER_DIR, "anomaly_residue.json"),
)
RMSF_PATH = os.environ.get(
    "ASVS_RMSF",
    os.path.join(VIEWER_DIR, "rmsf_residue.json"),
)
TICA_PATH = os.environ.get(
    "ASVS_TICA",
    os.path.join(VIEWER_DIR, "tica_importance.json"),
)
CONTACTS_PATH = os.environ.get(
    "ASVS_CONTACTS",
    os.path.join(VIEWER_DIR, "contacts.json"),
)


def _load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[trame-ribbon] Missing optional data file: {path}")
    except Exception as exc:  # pragma: no cover - best effort logging
        print(f"[trame-ribbon] Failed to load {path}: {exc}")
    return default


def _normalized_payload(payload: Dict) -> Dict:
    if isinstance(payload, dict) and "normalized" in payload:
        return payload["normalized"]
    return payload or {}


HOTSPOTS = _load_json(HOTSPOTS_RES_PATH, {})
ANOMALY = _load_json(ANOMALY_PATH, {})
RMSF = _normalized_payload(_load_json(RMSF_PATH, {}))
TICA = _normalized_payload(_load_json(TICA_PATH, {}))
CONTACTS_DATA = _load_json(CONTACTS_PATH, {"contacts": []})

# -----------------------------------------------------------------------------
# Metric explanations for info panel
# -----------------------------------------------------------------------------
METRIC_EXPLANATIONS = {
    "hotspot": "How significant this residue is in current kinetic hotspot mapping",
    "anomaly": "How rare this residue's behaviour is in the kinetic model",
    "rmsf": "How flexible or stable this residue is across the trajectory",
    "tica": "How much this residue contributes to slow collective motions",
}

METRIC_CONFIG = {
    "hotspot": {
        "label": "Dynamic Hotspot",
        "description": "Per-frame ML hotspot intensity",
        "frame_dependent": True,
        "source": HOTSPOTS,
    },
    "anomaly": {
        "label": "Dynamic Anomaly",
        "description": "Rare-conformation anomaly score",
        "frame_dependent": True,
        "source": ANOMALY,
    },
    "rmsf": {
        "label": "RMSF (Flexibility)",
        "description": "Frame-independent RMSF",
        "frame_dependent": False,
        "source": RMSF,
    },
    "tica": {
        "label": "tICA Importance",
        "description": "Residue contribution to slow modes",
        "frame_dependent": False,
        "source": TICA,
    },
}

DEFAULT_METRIC = "hotspot"
DEFAULT_COLORMAP = "viridis"

# -----------------------------------------------------------------------------
# Metric-specific color maps (Task 5: Improved hotspot color gradients)
# Each metric has its own distinct color scheme for better differentiation
# -----------------------------------------------------------------------------
METRIC_COLORMAPS = {
    "hotspot": "viridis",  # Default scientific colormap
    "anomaly": "anomaly_gradient",  # purple → white → orange
    "rmsf": "rmsf_gradient",  # navy → light blue → white
    "tica": "tica_gradient",  # green → yellow
}

COLORMAP_PRESETS = {
    "viridis": [
        (0.0, "#440154"),
        (0.25, "#3e4a89"),
        (0.5, "#26828e"),
        (0.75, "#6ece58"),
        (1.0, "#fde725"),
    ],
    "plasma": [
        (0.0, "#0d0887"),
        (0.25, "#7c02a8"),
        (0.5, "#cc4778"),
        (0.75, "#f89740"),
        (1.0, "#f0f921"),
    ],
    "coolwarm": [
        (0.0, "#3b4cc0"),
        (0.25, "#6b8de3"),
        (0.5, "#dddddd"),
        (0.75, "#f7895c"),
        (1.0, "#b40426"),
    ],
    "rainbow": [
        (0.0, "#0000ff"),
        (0.25, "#00ffff"),
        (0.5, "#00ff00"),
        (0.75, "#ffff00"),
        (1.0, "#ff0000"),
    ],
    "bwr": [
        (0.0, "#0000ff"),
        (0.5, "#ffffff"),
        (1.0, "#8b0000"),
    ],
    # Task 5: Metric-specific gradient color schemes
    "anomaly_gradient": [
        (0.0, "#6b21a8"),  # Purple (low anomaly)
        (0.5, "#ffffff"),  # White (mid)
        (1.0, "#f97316"),  # Orange (high anomaly)
    ],
    "rmsf_gradient": [
        (0.0, "#1e3a5f"),  # Navy (low flexibility)
        (0.5, "#60a5fa"),  # Light blue (mid)
        (1.0, "#ffffff"),  # White (high flexibility)
    ],
    "tica_gradient": [
        (0.0, "#166534"),  # Green (low importance)
        (0.5, "#86efac"),  # Light green (mid)
        (1.0, "#fde047"),  # Yellow (high importance)
    ],
}


def _hex_to_rgb(color: str) -> Tuple[float, float, float]:
    color = color.lstrip("#")
    return tuple(int(color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def _interpolate_color(stops, t: float) -> Tuple[float, float, float]:
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        t0, c0 = stops[i - 1]
        t1, c1 = stops[i]
        if t <= t1:
            span = (t1 - t0) or 1.0
            local = (t - t0) / span
            return tuple(c0[j] + (c1[j] - c0[j]) * local for j in range(3))
    return stops[-1][1]


_lut_cache: Dict[str, vtk.vtkLookupTable] = {}


def _build_lookup_table(name: str) -> vtk.vtkLookupTable:
    preset = COLORMAP_PRESETS.get(name, COLORMAP_PRESETS[DEFAULT_COLORMAP])
    rgb_stops = [(pos, _hex_to_rgb(hex_col)) for pos, hex_col in preset]

    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(256)
    lut.Build()
    for i in range(256):
        t = i / 255.0
        r, g, b = _interpolate_color(rgb_stops, t)
        lut.SetTableValue(i, r, g, b, 1.0)
    return lut


def _get_lookup_table(name: str) -> vtk.vtkLookupTable:
    if name not in _lut_cache:
        _lut_cache[name] = _build_lookup_table(name)
    return _lut_cache[name]

# -----------------------------------------------------------------------------
# Trajectory + residue metadata
# -----------------------------------------------------------------------------
adapter = get_adapter()
META = adapter.get_meta()
RESIDUES = adapter.get_residue_table()
NUM_RESIDUES = len(RESIDUES)
NUM_FRAMES = META.get("n_frames", 1)

# -----------------------------------------------------------------------------
# VTK pipeline setup (polyline + ribbon filter)
# -----------------------------------------------------------------------------
points = vtk.vtkPoints()
polydata = vtk.vtkPolyData()
lines = vtk.vtkCellArray()
scalars = vtk.vtkFloatArray()
scalars.SetName("metric")
scalars.SetNumberOfValues(max(1, NUM_RESIDUES))
polydata.SetPoints(points)
polydata.SetLines(lines)
polydata.GetPointData().SetScalars(scalars)

spline_filter = vtk.vtkSplineFilter()
spline_filter.SetInputData(polydata)
spline_filter.SetSubdivideToLength()
spline_filter.SetLength(1.5)

ribbon_filter = vtk.vtkRibbonFilter()
ribbon_filter.SetInputConnection(spline_filter.GetOutputPort())
ribbon_filter.SetWidth(0.3)
ribbon_filter.SetAngle(0.0)
# Older VTK builds do not expose SetGenerateTCoordsToUseWidth
if hasattr(ribbon_filter, "SetGenerateTCoordsToUseWidth"):
    ribbon_filter.SetGenerateTCoordsToUseWidth()
else:
    ribbon_filter.SetGenerateTCoordsToUseLength()
# OrientToYAxisOff is missing in some versions
if hasattr(ribbon_filter, "OrientToYAxisOff"):
    ribbon_filter.OrientToYAxisOff()

mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(ribbon_filter.GetOutputPort())
mapper.SetScalarRange(0.0, 1.0)
mapper.ScalarVisibilityOn()
mapper.SetLookupTable(_get_lookup_table(DEFAULT_COLORMAP))

actor = vtk.vtkActor()
actor.SetMapper(mapper)
actor.GetProperty().SetSpecular(0.1)
actor.GetProperty().SetSpecularPower(10.0)

renderer = vtk.vtkRenderer()
renderer.SetBackground(0.05, 0.06, 0.10)
renderer.AddActor(actor)

render_window = vtk.vtkRenderWindow()
render_window.AddRenderer(renderer)
render_window.SetSize(1280, 720)

# -----------------------------------------------------------------------------
# VTK Interactor and Picker setup for click interactions
# -----------------------------------------------------------------------------
interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(render_window)
interactor_style = vtk.vtkInteractorStyleTrackballCamera()
interactor.SetInteractorStyle(interactor_style)

# Cell picker for selecting ribbon cells (maps to residues)
cell_picker = vtk.vtkCellPicker()
cell_picker.SetTolerance(0.005)

# Point picker as backup for more precise picking
point_picker = vtk.vtkPointPicker()
point_picker.SetTolerance(0.01)

# Track whether camera has been reset once
_scene_initialized = False

# Track last pick for interaction state
_last_pick_cell_id = -1
_last_pick_point_id = -1

# -----------------------------------------------------------------------------
# Task 1: Clipping plane setup
# -----------------------------------------------------------------------------
clip_plane = vtk.vtkPlane()
clip_plane.SetOrigin(0, 0, 0)
clip_plane.SetNormal(1, 0, 0)  # Default X-axis

# Store bounds for clipping calculation
_ribbon_bounds = [0.0] * 6  # [xmin, xmax, ymin, ymax, zmin, zmax]

def _update_clip_bounds():
    """Update ribbon bounds for clipping plane positioning."""
    global _ribbon_bounds
    ribbon_filter.Update()
    ribbon_output = ribbon_filter.GetOutput()
    if ribbon_output and ribbon_output.GetNumberOfPoints() > 0:
        _ribbon_bounds = list(ribbon_output.GetBounds())


def _pick_position_to_residue(pick_pos: Tuple[float, float, float]) -> int:
    """Convert a 3D pick position to the nearest residue index.
    
    Uses the cached CA positions to find the closest residue to the pick point.
    Returns -1 if no valid residue found.
    """
    if not _ca_positions_cache or not pick_pos:
        return -1
    
    min_dist = float('inf')
    closest_idx = -1
    
    for idx, ca_pos in enumerate(_ca_positions_cache):
        dist_sq = sum((a - b) ** 2 for a, b in zip(pick_pos, ca_pos))
        if dist_sq < min_dist:
            min_dist = dist_sq
            closest_idx = idx
    
    # Only accept picks within a reasonable distance (e.g., 5 Angstroms)
    MAX_PICK_DISTANCE = 5.0
    if math.sqrt(min_dist) > MAX_PICK_DISTANCE:
        return -1
    
    return closest_idx


def _perform_pick(x: int, y: int) -> int:
    """Perform a VTK pick at screen coordinates and return residue index.
    
    Uses cell picker first, falls back to point picker if needed.
    Returns -1 if no valid pick.
    """
    # Try cell picker first
    if cell_picker.Pick(x, y, 0, renderer):
        pick_pos = cell_picker.GetPickPosition()
        if pick_pos and pick_pos != (0, 0, 0):
            return _pick_position_to_residue(pick_pos)
    
    # Fall back to point picker
    if point_picker.Pick(x, y, 0, renderer):
        pick_pos = point_picker.GetPickPosition()
        if pick_pos and pick_pos != (0, 0, 0):
            return _pick_position_to_residue(pick_pos)
    
    return -1

# -----------------------------------------------------------------------------
# Task 2: Contact line visualization setup
# -----------------------------------------------------------------------------
contact_actors: List[vtk.vtkActor] = []
_contacts_visible = False
_ca_positions_cache: List[Tuple[float, float, float]] = []

# Constants for contact visualization
MIN_CONTACT_RESIDUE_SEPARATION = 3  # Skip close neighbors (backbone)
CONTACT_COLOR_MIN_GREEN = 0.3  # Min green component for low frequency
CONTACT_COLOR_GREEN_RANGE = 0.4  # Green range for frequency gradient
NUMERICAL_EPSILON = 1e-10  # Tolerance for floating point comparisons

def _get_top_contacts(n: int = 50) -> List[Dict]:
    """Get top N contacts sorted by frequency."""
    contacts = CONTACTS_DATA.get("contacts", [])
    # Sort by frequency (descending)
    sorted_contacts = sorted(contacts, key=lambda c: c.get("frequency", 0), reverse=True)
    return sorted_contacts[:n]

def _create_contact_line_actor(pos1: Tuple[float, float, float], 
                                pos2: Tuple[float, float, float],
                                color: Tuple[float, float, float] = (1.0, 0.5, 0.0)) -> vtk.vtkActor:
    """Create a VTK actor for a contact line between two positions."""
    line_source = vtk.vtkLineSource()
    line_source.SetPoint1(*pos1)
    line_source.SetPoint2(*pos2)
    
    # Create tube filter for better visibility
    tube_filter = vtk.vtkTubeFilter()
    tube_filter.SetInputConnection(line_source.GetOutputPort())
    tube_filter.SetRadius(0.15)
    tube_filter.SetNumberOfSides(8)
    
    line_mapper = vtk.vtkPolyDataMapper()
    line_mapper.SetInputConnection(tube_filter.GetOutputPort())
    
    line_actor = vtk.vtkActor()
    line_actor.SetMapper(line_mapper)
    line_actor.GetProperty().SetColor(*color)
    line_actor.GetProperty().SetOpacity(0.7)
    
    return line_actor

def _build_contact_actors():
    """Build contact line actors based on current CA positions."""
    global contact_actors
    
    # Clear existing contact actors
    for actor in contact_actors:
        renderer.RemoveActor(actor)
    contact_actors.clear()
    
    if len(_ca_positions_cache) == 0:
        return
    
    top_contacts = _get_top_contacts(50)
    
    for contact in top_contacts:
        res1 = contact.get("residue1", -1)
        res2 = contact.get("residue2", -1)
        
        # Skip invalid or sequential residues (backbone connections)
        if res1 < 0 or res2 < 0:
            continue
        if res1 >= len(_ca_positions_cache) or res2 >= len(_ca_positions_cache):
            continue
        if abs(res1 - res2) <= MIN_CONTACT_RESIDUE_SEPARATION:
            continue
            
        pos1 = _ca_positions_cache[res1]
        pos2 = _ca_positions_cache[res2]
        
        # Color based on frequency (orange gradient)
        freq = contact.get("frequency", 0.5)
        green_component = CONTACT_COLOR_MIN_GREEN + CONTACT_COLOR_GREEN_RANGE * (1 - freq)
        color = (1.0, green_component, 0.0)
        
        actor = _create_contact_line_actor(pos1, pos2, color)
        contact_actors.append(actor)

def _show_contacts(visible: bool):
    """Show or hide contact line actors."""
    global _contacts_visible
    _contacts_visible = visible
    
    if visible:
        _build_contact_actors()
        for actor in contact_actors:
            renderer.AddActor(actor)
    else:
        for actor in contact_actors:
            renderer.RemoveActor(actor)

# -----------------------------------------------------------------------------
# Task 3: Distance/Angle measurement infrastructure
# -----------------------------------------------------------------------------
_measurement_mode: Optional[str] = None  # "distance" or "angle"
_measurement_picks: List[int] = []  # Residue indices for measurement
_measurement_result: str = ""
measurement_actors: List[vtk.vtkActor] = []

def _calculate_distance(idx1: int, idx2: int) -> float:
    """Calculate distance between two residue CA atoms in Angstroms."""
    if idx1 >= len(_ca_positions_cache) or idx2 >= len(_ca_positions_cache):
        return 0.0
    p1 = _ca_positions_cache[idx1]
    p2 = _ca_positions_cache[idx2]
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

def _calculate_angle(idx1: int, idx2: int, idx3: int) -> float:
    """Calculate angle at residue idx2 (A-B-C) in degrees."""
    if any(idx >= len(_ca_positions_cache) for idx in [idx1, idx2, idx3]):
        return 0.0
    
    p1 = _ca_positions_cache[idx1]
    p2 = _ca_positions_cache[idx2]
    p3 = _ca_positions_cache[idx3]
    
    # Vectors from B to A and B to C
    v1 = tuple(p1[i] - p2[i] for i in range(3))
    v2 = tuple(p3[i] - p2[i] for i in range(3))
    
    # Dot product and magnitudes
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a ** 2 for a in v1))
    mag2 = math.sqrt(sum(a ** 2 for a in v2))
    
    # Use epsilon for numerical stability with floating point comparisons
    if mag1 < NUMERICAL_EPSILON or mag2 < NUMERICAL_EPSILON:
        return 0.0
    
    cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cos_angle))

def _create_measurement_line(idx1: int, idx2: int, color: Tuple[float, float, float] = (0.0, 1.0, 1.0)) -> Optional[vtk.vtkActor]:
    """Create a line actor for measurement visualization.
    
    Returns None if indices are out of bounds.
    """
    if idx1 >= len(_ca_positions_cache) or idx2 >= len(_ca_positions_cache):
        return None
    
    p1 = _ca_positions_cache[idx1]
    p2 = _ca_positions_cache[idx2]
    
    line_source = vtk.vtkLineSource()
    line_source.SetPoint1(*p1)
    line_source.SetPoint2(*p2)
    
    tube_filter = vtk.vtkTubeFilter()
    tube_filter.SetInputConnection(line_source.GetOutputPort())
    tube_filter.SetRadius(0.1)
    tube_filter.SetNumberOfSides(6)
    
    line_mapper = vtk.vtkPolyDataMapper()
    line_mapper.SetInputConnection(tube_filter.GetOutputPort())
    
    line_actor = vtk.vtkActor()
    line_actor.SetMapper(line_mapper)
    line_actor.GetProperty().SetColor(*color)
    line_actor.GetProperty().SetOpacity(0.9)
    
    return line_actor

def _clear_measurement_actors():
    """Clear measurement visualization actors."""
    global measurement_actors
    for actor in measurement_actors:
        renderer.RemoveActor(actor)
    measurement_actors.clear()

def _update_measurement_display():
    """Update measurement visualization based on current picks."""
    _clear_measurement_actors()
    
    if len(_measurement_picks) >= 2:
        # Draw line between first two picks
        actor = _create_measurement_line(_measurement_picks[0], _measurement_picks[1], (0.0, 1.0, 1.0))
        if actor:
            measurement_actors.append(actor)
            renderer.AddActor(actor)
    
    if len(_measurement_picks) >= 3:
        # Draw line for angle measurement (second to third)
        actor = _create_measurement_line(_measurement_picks[1], _measurement_picks[2], (0.0, 1.0, 0.5))
        if actor:
            measurement_actors.append(actor)
            renderer.AddActor(actor)

# -----------------------------------------------------------------------------
# Task 4: Residue info helper functions
# -----------------------------------------------------------------------------
def _get_residue_metrics(residue_idx: int, frame: int) -> Dict:
    """Get all metric values for a specific residue."""
    result = {}
    for metric_name, config in METRIC_CONFIG.items():
        source = config["source"]
        if config["frame_dependent"]:
            frame_blob = source.get(str(frame), {}) if isinstance(source, dict) else {}
            value = _residue_value(frame_blob, residue_idx)
        else:
            value = float(source.get(str(residue_idx), 0.0)) if isinstance(source, dict) else 0.0
        result[metric_name] = value
    return result

def _format_residue_info(residue_idx: int, frame: int) -> Dict:
    """Format residue information for display."""
    if residue_idx < 0 or residue_idx >= NUM_RESIDUES:
        return {}
    
    residue = RESIDUES[residue_idx]
    metrics = _get_residue_metrics(residue_idx, frame)
    
    return {
        "index": residue_idx,
        "resnum": residue.get("resnum", residue_idx + 1),
        "resname": residue.get("resname", "UNK"),
        "chain": residue.get("chain", "A"),
        "metrics": metrics,
        "explanations": METRIC_EXPLANATIONS,
    }


# -----------------------------------------------------------------------------
# Metric helpers
# -----------------------------------------------------------------------------
def _residue_value(frame_blob: Dict, residue_idx: int) -> float:
    """Try multiple keys when looking up residue associated scores."""
    residue = RESIDUES[residue_idx]
    fallbacks = (
        str(residue.get("resnum")),
        str(residue_idx + 1),
        str(residue_idx),
    )
    for key in fallbacks:
        if frame_blob and key in frame_blob:
            try:
                return float(frame_blob[key])
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _metric_values(metric_name: str, frame: int) -> List[float]:
    config = METRIC_CONFIG.get(metric_name) or METRIC_CONFIG[DEFAULT_METRIC]
    source = config["source"]

    if config["frame_dependent"]:
        frame_blob = source.get(str(frame), {}) if isinstance(source, dict) else {}
        return [_residue_value(frame_blob, idx) for idx in range(NUM_RESIDUES)]

    # Static metrics (already normalized dicts)
    return [
        float(source.get(str(idx), 0.0)) if isinstance(source, dict) else 0.0
        for idx in range(NUM_RESIDUES)
    ]


# -----------------------------------------------------------------------------
# Geometry updates
# -----------------------------------------------------------------------------
def update_ribbon_geometry(frame: int, metric: str) -> None:
    global _scene_initialized, _ca_positions_cache

    frame = max(0, min(NUM_FRAMES - 1, int(frame)))
    points_data = adapter.get_ca_xyz(frame)
    n_points = len(points_data)
    if n_points == 0:
        return

    # Cache CA positions for contact visualization and measurements
    _ca_positions_cache = [tuple(p) for p in points_data]

    # Update points array
    points.SetNumberOfPoints(n_points)
    for idx, (x, y, z) in enumerate(points_data):
        points.SetPoint(idx, float(x), float(y), float(z))
    points.Modified()

    # Rebuild polyline connectivity so ribbon filter has a clean input
    lines.Reset()
    lines.InsertNextCell(n_points)
    for idx in range(n_points):
        lines.InsertCellPoint(idx)
    polydata.SetLines(lines)
    lines.Modified()

    # Update scalar values for coloring
    values = _metric_values(metric, frame)
    if scalars.GetNumberOfValues() != n_points:
        scalars.SetNumberOfValues(n_points)

    for idx in range(n_points):
        scalars.SetValue(idx, float(values[idx] if idx < len(values) else 0.0))
    scalars.Modified()

    polydata.Modified()
    
    # Update clipping bounds after geometry change
    _update_clip_bounds()
    
    # Rebuild contact actors if contacts are visible
    if _contacts_visible:
        _show_contacts(True)

    if not _scene_initialized:
        renderer.ResetCamera()
        _scene_initialized = True


# -----------------------------------------------------------------------------
# Trame server + UI
# -----------------------------------------------------------------------------
server = get_server(name="asvs-ribbon", client_type="vue2")
state, ctrl = server.state, server.controller

state.trame__title = "ASVS · Ribbon Viewer"
state.current_frame = 0
state.current_metric = DEFAULT_METRIC
state.current_colormap = DEFAULT_COLORMAP
state.status_message = "Initializing ribbon scene..."
state.frame_max = max(0, NUM_FRAMES - 1)
state.metric_options = [
    {"text": cfg["label"], "value": key} for key, cfg in METRIC_CONFIG.items()
]
state.colormap_options = [
    {"text": name.title(), "value": name} for name in COLORMAP_PRESETS.keys()
]

# Task 1: Clipping state
state.clip_enabled = False
state.clip_axis = "X"
state.clip_position = 50  # 0-100 percent along axis
state.axis_options = [
    {"text": "X Axis", "value": "X"},
    {"text": "Y Axis", "value": "Y"},
    {"text": "Z Axis", "value": "Z"},
]

# Task 2: Contacts state
state.show_contacts = False
state.top_contacts_list = []

# Task 3: Measurement state
state.measurement_mode = ""  # "", "distance", "angle"
state.measurement_result = ""
state.measurement_picks_display = ""

# Task 4: Residue info state
state.selected_residue_idx = -1
state.residue_info = {}
state.show_residue_info = False

# Task 5: Color bar state
state.color_bar_min = 0.0
state.color_bar_max = 1.0
state.color_bar_label = "Value"


def _apply_colormap(name: str):
    lut = _get_lookup_table(name or DEFAULT_COLORMAP)
    mapper.SetLookupTable(lut)
    mapper.Modified()


def _get_metric_colormap(metric: str) -> str:
    """Get the appropriate colormap for a metric, or use default."""
    return METRIC_COLORMAPS.get(metric, DEFAULT_COLORMAP)


def _update_clipping(enabled: bool, axis: str, position: float):
    """Update clipping plane based on current settings."""
    if not enabled:
        mapper.RemoveAllClippingPlanes()
        return
    
    # Get axis index and bounds
    axis_map = {"X": 0, "Y": 1, "Z": 2}
    axis_idx = axis_map.get(axis, 0)
    
    if _ribbon_bounds[0] == _ribbon_bounds[1] == 0:
        _update_clip_bounds()
    
    # Calculate clip position based on bounds
    min_val = _ribbon_bounds[axis_idx * 2]
    max_val = _ribbon_bounds[axis_idx * 2 + 1]
    clip_pos = min_val + (position / 100.0) * (max_val - min_val)
    
    # Set plane normal and origin
    normal = [0, 0, 0]
    normal[axis_idx] = 1.0
    
    origin = [0, 0, 0]
    origin[axis_idx] = clip_pos
    
    clip_plane.SetNormal(*normal)
    clip_plane.SetOrigin(*origin)
    
    # Apply to mapper
    mapper.RemoveAllClippingPlanes()
    mapper.AddClippingPlane(clip_plane)


def _update_contacts_list():
    """Update the top contacts list for side panel display."""
    top_contacts = _get_top_contacts(50)
    contacts_display = []
    
    for contact in top_contacts[:20]:  # Show top 20 in panel
        res1 = contact.get("residue1", -1)
        res2 = contact.get("residue2", -1)
        freq = contact.get("frequency", 0)
        
        if res1 >= 0 and res2 >= 0 and abs(res1 - res2) > 3:
            # Get residue names
            name1 = RESIDUES[res1].get("resname", "?") if res1 < NUM_RESIDUES else "?"
            name2 = RESIDUES[res2].get("resname", "?") if res2 < NUM_RESIDUES else "?"
            num1 = RESIDUES[res1].get("resnum", res1) if res1 < NUM_RESIDUES else res1
            num2 = RESIDUES[res2].get("resnum", res2) if res2 < NUM_RESIDUES else res2
            
            contacts_display.append({
                "text": f"{name1}{num1} ↔ {name2}{num2}",
                "freq": f"{freq:.2f}",
            })
    
    state.top_contacts_list = contacts_display


def _handle_residue_pick(residue_idx: int):
    """Handle picking a residue (for measurement or info display)."""
    global _measurement_picks, _measurement_result, _measurement_mode
    
    if _measurement_mode == "distance":
        _measurement_picks.append(residue_idx)
        
        if len(_measurement_picks) == 2:
            dist = _calculate_distance(_measurement_picks[0], _measurement_picks[1])
            res1 = RESIDUES[_measurement_picks[0]] if _measurement_picks[0] < NUM_RESIDUES else {}
            res2 = RESIDUES[_measurement_picks[1]] if _measurement_picks[1] < NUM_RESIDUES else {}
            name1 = f"{res1.get('resname', '?')}{res1.get('resnum', _measurement_picks[0])}"
            name2 = f"{res2.get('resname', '?')}{res2.get('resnum', _measurement_picks[1])}"
            _measurement_result = f"Distance: {dist:.2f} Å between {name1} and {name2}"
            state.measurement_result = _measurement_result
            _update_measurement_display()
            ctrl.update_view()
        
        _update_picks_display()
    
    elif _measurement_mode == "angle":
        _measurement_picks.append(residue_idx)
        
        if len(_measurement_picks) == 3:
            angle = _calculate_angle(_measurement_picks[0], _measurement_picks[1], _measurement_picks[2])
            res1 = RESIDUES[_measurement_picks[0]] if _measurement_picks[0] < NUM_RESIDUES else {}
            res2 = RESIDUES[_measurement_picks[1]] if _measurement_picks[1] < NUM_RESIDUES else {}
            res3 = RESIDUES[_measurement_picks[2]] if _measurement_picks[2] < NUM_RESIDUES else {}
            name1 = f"{res1.get('resname', '?')}{res1.get('resnum', _measurement_picks[0])}"
            name2 = f"{res2.get('resname', '?')}{res2.get('resnum', _measurement_picks[1])}"
            name3 = f"{res3.get('resname', '?')}{res3.get('resnum', _measurement_picks[2])}"
            _measurement_result = f"Angle: {angle:.1f}° at {name2} ({name1}-{name2}-{name3})"
            state.measurement_result = _measurement_result
            _update_measurement_display()
            ctrl.update_view()
        
        _update_picks_display()
    
    else:
        # Just show residue info
        state.selected_residue_idx = residue_idx
        state.residue_info = _format_residue_info(residue_idx, state.current_frame)
        state.show_residue_info = True


def _update_picks_display():
    """Update display of current measurement picks."""
    if not _measurement_picks:
        state.measurement_picks_display = ""
        return
    
    names = []
    for idx in _measurement_picks:
        if idx < NUM_RESIDUES:
            res = RESIDUES[idx]
            names.append(f"{res.get('resname', '?')}{res.get('resnum', idx)}")
        else:
            names.append(f"?{idx}")
    
    if _measurement_mode == "distance":
        needed = 2 - len(_measurement_picks)
        state.measurement_picks_display = f"Selected: {', '.join(names)} (need {needed} more)"
    elif _measurement_mode == "angle":
        needed = 3 - len(_measurement_picks)
        state.measurement_picks_display = f"Selected: {', '.join(names)} (need {needed} more)"


@state.change("current_frame", "current_metric", "current_colormap")
def _on_state_change(current_frame, current_metric, current_colormap, **_):
    metric = current_metric or DEFAULT_METRIC
    
    # Task 5: Use metric-specific colormap if colormap is set to "auto" or match metric
    colormap = current_colormap or DEFAULT_COLORMAP
    if colormap == "auto":
        colormap = _get_metric_colormap(metric)
    
    _apply_colormap(colormap)
    update_ribbon_geometry(current_frame or 0, metric)
    
    # Update color bar info
    state.color_bar_label = METRIC_CONFIG.get(metric, {}).get("label", "Value")
    
    state.status_message = (
        f"Frame {current_frame} · Metric: {METRIC_CONFIG[metric]['label']} · Colormap: {colormap.replace('_', ' ').title()}"
    )
    
    # Update residue info if one is selected
    if state.selected_residue_idx >= 0:
        state.residue_info = _format_residue_info(state.selected_residue_idx, current_frame)
    
    ctrl.update_view()


@state.change("clip_enabled", "clip_axis", "clip_position")
def _on_clip_change(clip_enabled, clip_axis, clip_position, **_):
    _update_clipping(clip_enabled, clip_axis, clip_position)
    ctrl.update_view()


@state.change("show_contacts")
def _on_contacts_change(show_contacts, **_):
    _show_contacts(show_contacts)
    if show_contacts:
        _update_contacts_list()
    ctrl.update_view()


@state.change("measurement_mode")
def _on_measurement_mode_change(measurement_mode, **_):
    global _measurement_picks, _measurement_result, _measurement_mode
    _measurement_mode = measurement_mode
    _measurement_picks = []
    _measurement_result = ""
    state.measurement_result = ""
    state.measurement_picks_display = ""
    _clear_measurement_actors()
    
    if measurement_mode:
        state.status_message = f"Measurement mode: {measurement_mode.title()}. Click residues to measure."
    
    ctrl.update_view()


# Controller functions for measurement
@ctrl.add("pick_residue")
def pick_residue(residue_idx):
    """Called when user picks a residue (from JS interaction)."""
    if residue_idx >= 0:
        _handle_residue_pick(residue_idx)


@ctrl.add("clear_measurement")
def clear_measurement():
    """Clear current measurement."""
    global _measurement_picks, _measurement_result
    _measurement_picks = []
    _measurement_result = ""
    state.measurement_result = ""
    state.measurement_picks_display = ""
    _clear_measurement_actors()
    ctrl.update_view()


@ctrl.add("close_residue_info")
def close_residue_info():
    """Close residue info panel."""
    state.show_residue_info = False
    state.selected_residue_idx = -1


@ctrl.add("on_vtk_click")
def on_vtk_click(event):
    """Handle click events on the VTK view for residue picking.
    
    The event contains screen coordinates that we use to perform VTK picking.
    This connects user mouse clicks to the measurement and info display system.
    """
    if not event:
        return
    
    # Get click position from event
    # VtkLocalView sends position as { x, y, ... }
    x = event.get("x", event.get("position", {}).get("x", 0))
    y = event.get("y", event.get("position", {}).get("y", 0))
    
    if x is None or y is None:
        return
    
    # Convert to integers (screen coordinates)
    try:
        x = int(x)
        y = int(y)
    except (ValueError, TypeError):
        return
    
    # Perform VTK picking to find residue
    residue_idx = _perform_pick(x, y)
    
    if residue_idx >= 0:
        _handle_residue_pick(residue_idx)
        ctrl.update_view()


@ctrl.add("on_vtk_select")
def on_vtk_select(selection_info):
    """Handle selection events from VTK view.
    
    This is called when user selects geometry in the 3D view.
    """
    if not selection_info:
        return
    
    # Try to extract residue information from selection
    # Selection info format depends on VTK widget configuration
    if isinstance(selection_info, dict):
        # Check for point ID or cell ID
        point_id = selection_info.get("pointId", selection_info.get("point_id", -1))
        cell_id = selection_info.get("cellId", selection_info.get("cell_id", -1))
        
        # Map point/cell ID to residue (approximate based on spline subdivision)
        if point_id >= 0 and NUM_RESIDUES > 0:
            # The spline filter subdivides, so we need to map back
            # Rough approximation: point_id / subdivision_factor
            residue_idx = min(point_id // 3, NUM_RESIDUES - 1)  # Assuming ~3x subdivision
            if 0 <= residue_idx < NUM_RESIDUES:
                _handle_residue_pick(residue_idx)
                ctrl.update_view()


with SinglePageLayout(server) as layout:
    layout.title.set_text("Protein Ribbon · Trame (Interactive)")

    with layout.toolbar:
        vuetify.VSpacer()
        vuetify.VSelect(
            label="Metric",
            dense=True,
            hide_details=True,
            items=("metric_options", []),
            v_model=("current_metric", DEFAULT_METRIC),
            style="max-width: 180px;",
        )
        vuetify.VSelect(
            label="Colormap",
            dense=True,
            hide_details=True,
            items=("colormap_options", []),
            v_model=("current_colormap", DEFAULT_COLORMAP),
            style="max-width: 180px; margin-left: 8px;",
        )
        vuetify.VSlider(
            label="Frame",
            min=0,
            max=("frame_max", 0),
            step=1,
            dense=True,
            hide_details=True,
            v_model=("current_frame", 0),
            style="max-width: 200px; margin-left: 16px;",
        )
        html.Div("{{ current_frame }}", classes="ml-2 subtitle-2")

    with layout.content:
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
            with vuetify.VRow(no_gutters=True, classes="fill-height"):
                # Main 3D view area
                with vuetify.VCol(cols=9, classes="fill-height pa-0"):
                    with vuetify.VCard(flat=True, classes="fill-height d-flex flex-column"):
                        # Toolbar with clipping and measurement controls
                        with vuetify.VToolbar(dense=True, flat=True, classes="flex-grow-0"):
                            # Task 1: Clipping controls
                            vuetify.VCheckbox(
                                label="Clip",
                                dense=True,
                                hide_details=True,
                                v_model=("clip_enabled", False),
                                classes="mr-2",
                            )
                            vuetify.VSelect(
                                label="Axis",
                                dense=True,
                                hide_details=True,
                                items=("axis_options", []),
                                v_model=("clip_axis", "X"),
                                style="max-width: 100px;",
                                disabled=("!clip_enabled",),
                            )
                            vuetify.VSlider(
                                min=0,
                                max=100,
                                step=1,
                                dense=True,
                                hide_details=True,
                                v_model=("clip_position", 50),
                                style="max-width: 150px; margin-left: 8px;",
                                disabled=("!clip_enabled",),
                            )
                            
                            vuetify.VDivider(vertical=True, classes="mx-2")
                            
                            # Task 2: Contacts toggle
                            vuetify.VCheckbox(
                                label="Contacts",
                                dense=True,
                                hide_details=True,
                                v_model=("show_contacts", False),
                                classes="mr-2",
                            )
                            
                            vuetify.VDivider(vertical=True, classes="mx-2")
                            
                            # Task 3: Measurement buttons
                            vuetify.VBtnToggle(
                                v_model=("measurement_mode", ""),
                                dense=True,
                                borderless=True,
                                children=[
                                    vuetify.VBtn(
                                        children=["Distance"],
                                        small=True,
                                        value="distance",
                                    ),
                                    vuetify.VBtn(
                                        children=["Angle"],
                                        small=True,
                                        value="angle",
                                    ),
                                ],
                            )
                            vuetify.VBtn(
                                children=["Clear"],
                                small=True,
                                text=True,
                                click=ctrl.clear_measurement,
                                classes="ml-2",
                            )
                        
                        # VTK View with click interaction support
                        with vuetify.VCardText(classes="flex-grow-1 pa-0"):
                            # Use VtkRemoteView for better interaction support
                            # Enable picking and selection for residue interaction
                            view = vtk_widgets.VtkRemoteView(
                                render_window,
                                ref="ribbonView",
                                interactor_events=("events", ["LeftButtonPress"]),
                                LeftButtonPress=(ctrl.on_vtk_click, "[$event]"),
                            )
                        
                        # Status bar with measurement result
                        with vuetify.VCardActions(classes="flex-grow-0"):
                            html.Div("{{ status_message }}", classes="caption grey--text")
                            vuetify.VSpacer()
                            html.Div(
                                "{{ measurement_picks_display }}",
                                classes="caption blue--text mr-4",
                                v_if="measurement_mode",
                            )
                            html.Div(
                                "{{ measurement_result }}",
                                classes="caption green--text font-weight-bold",
                                v_if="measurement_result",
                            )
                
                # Right side panel
                with vuetify.VCol(cols=3, classes="fill-height pa-0"):
                    with vuetify.VCard(flat=True, tile=True, classes="fill-height overflow-y-auto", style="background: #1e1e1e;"):
                        # Task 5: Color bar legend
                        with vuetify.VCardText(classes="pa-2"):
                            html.Div("{{ color_bar_label }}", classes="subtitle-2 white--text mb-1")
                            with html.Div(style="height: 20px; background: linear-gradient(to right, #440154, #26828e, #fde725); border-radius: 4px;"):
                                pass
                            with html.Div(classes="d-flex justify-space-between caption grey--text mt-1"):
                                html.Span("0.0")
                                html.Span("0.5")
                                html.Span("1.0")
                        
                        vuetify.VDivider()
                        
                        # Task 2: Contacts panel
                        with vuetify.VExpansionPanels(accordion=True, flat=True, v_if="show_contacts"):
                            with vuetify.VExpansionPanel():
                                vuetify.VExpansionPanelHeader(children=["Top Contacts"], classes="py-0")
                                with vuetify.VExpansionPanelContent():
                                    with vuetify.VList(dense=True, classes="pa-0"):
                                        with vuetify.VListItem(
                                            v_for="(contact, i) in top_contacts_list",
                                            key="i",
                                            dense=True,
                                        ):
                                            vuetify.VListItemContent(
                                                children=[
                                                    html.Span("{{ contact.text }}", classes="body-2"),
                                                    html.Span(" ({{ contact.freq }})", classes="caption grey--text"),
                                                ]
                                            )
                        
                        vuetify.VDivider(v_if="show_contacts")
                        
                        # Task 4: Residue info card
                        with vuetify.VCard(flat=True, classes="ma-2", v_if="show_residue_info", style="background: #2d2d2d;"):
                            with vuetify.VCardTitle(classes="py-2"):
                                html.Span("Residue Info", classes="subtitle-1")
                                vuetify.VSpacer()
                                vuetify.VBtn(icon=True, small=True, click=ctrl.close_residue_info, children=[
                                    vuetify.VIcon("mdi-close", small=True)
                                ])
                            with vuetify.VCardText(classes="py-1"):
                                html.Div([
                                    html.Strong("Chain: "),
                                    html.Span("{{ residue_info.chain }}"),
                                ], classes="body-2")
                                html.Div([
                                    html.Strong("Residue: "),
                                    html.Span("{{ residue_info.resname }} {{ residue_info.resnum }}"),
                                ], classes="body-2")
                                html.Div([
                                    html.Strong("Index: "),
                                    html.Span("{{ residue_info.index }}"),
                                ], classes="body-2 mb-2")
                                
                                vuetify.VDivider(classes="my-2")
                                
                                # ML Metrics
                                html.Div("ML Metrics", classes="subtitle-2 mb-1")
                                
                                # Hotspot
                                with html.Div(classes="mb-2"):
                                    html.Div([
                                        html.Strong("Hotspot: "),
                                        html.Span("{{ residue_info.metrics?.hotspot?.toFixed(3) || 'N/A' }}"),
                                    ], classes="body-2")
                                    html.Div("{{ residue_info.explanations?.hotspot }}", classes="caption grey--text")
                                
                                # Anomaly
                                with html.Div(classes="mb-2"):
                                    html.Div([
                                        html.Strong("Anomaly: "),
                                        html.Span("{{ residue_info.metrics?.anomaly?.toFixed(3) || 'N/A' }}"),
                                    ], classes="body-2")
                                    html.Div("{{ residue_info.explanations?.anomaly }}", classes="caption grey--text")
                                
                                # RMSF
                                with html.Div(classes="mb-2"):
                                    html.Div([
                                        html.Strong("RMSF: "),
                                        html.Span("{{ residue_info.metrics?.rmsf?.toFixed(3) || 'N/A' }}"),
                                    ], classes="body-2")
                                    html.Div("{{ residue_info.explanations?.rmsf }}", classes="caption grey--text")
                                
                                # tICA
                                with html.Div(classes="mb-2"):
                                    html.Div([
                                        html.Strong("tICA Importance: "),
                                        html.Span("{{ residue_info.metrics?.tica?.toFixed(3) || 'N/A' }}"),
                                    ], classes="body-2")
                                    html.Div("{{ residue_info.explanations?.tica }}", classes="caption grey--text")
                        
                        # Instructions when no residue selected
                        with vuetify.VCardText(v_if="!show_residue_info", classes="caption grey--text"):
                            html.Div("Click on a residue in the ribbon to view its details and ML metrics.", classes="mb-2")
                            html.Div("Use the measurement tools to calculate distances and angles between residues.")

ctrl.update_view = view.update

# Bootstrap once to populate data before serving
_apply_colormap(state.current_colormap)
update_ribbon_geometry(state.current_frame, state.current_metric)
state.color_bar_label = METRIC_CONFIG.get(state.current_metric, {}).get("label", "Value")
state.status_message = (
    f"Frame {state.current_frame} · Metric: {METRIC_CONFIG[state.current_metric]['label']} · Colormap: {state.current_colormap.replace('_', ' ').title()}"
)
ctrl.update_view()


DEFAULT_TRAME_HOST = os.environ.get("ASVS_TRAME_RIBBON_HOST", "127.0.0.1")
DEFAULT_TRAME_PORT = int(os.environ.get("ASVS_TRAME_RIBBON_PORT", "9887"))
_server_process: Optional[subprocess.Popen] = None
_server_process_lock = threading.Lock()


def start_ribbon_server(address: str = DEFAULT_TRAME_HOST, port: int = DEFAULT_TRAME_PORT,
                        background: bool = False) -> Tuple[str, int]:
    """Start the Trame ribbon server.

    Parameters
    ----------
    address : str
        IP/interface to bind.
    port : int
        Port to listen on.
    background : bool
        If True, launch server in a daemon thread (non-blocking).

    Returns
    -------
    Tuple[str, int]
        (address, port) where the server is listening.
    """

    def _serve_foreground():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            server.start(address=address, port=port, open_browser=False)
        finally:
            try:
                loop.stop()
            finally:
                asyncio.set_event_loop(None)

    if background:
        global _server_process
        with _server_process_lock:
            if _server_process and _server_process.poll() is None:
                return address, port

            cmd = [
                sys.executable,
                os.path.abspath(__file__),
                "--address", address,
                "--port", str(port),
            ]
            env = os.environ.copy()
            env.setdefault("TRAME_DISABLE_SIGNALS", "1")
            _server_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return address, port

    _serve_foreground()
    return address, port


def ensure_ribbon_server(address: Optional[str] = None, port: Optional[int] = None) -> Tuple[str, int]:
    """Ensure the Trame ribbon server is running in the background."""

    return start_ribbon_server(address or DEFAULT_TRAME_HOST, port or DEFAULT_TRAME_PORT, background=True)


def ribbon_server_url(address: Optional[str] = None, port: Optional[int] = None) -> str:
    host = address or DEFAULT_TRAME_HOST
    listen_port = port or DEFAULT_TRAME_PORT
    return f"http://{host}:{listen_port}"


def _parse_cli():
    parser = argparse.ArgumentParser(description="Run the Trame ribbon server")
    parser.add_argument("--address", default=DEFAULT_TRAME_HOST, help="Bind address")
    parser.add_argument("--port", type=int, default=DEFAULT_TRAME_PORT, help="Bind port")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_cli()
    start_ribbon_server(address=args.address, port=args.port, background=False)
