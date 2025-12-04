import argparse
import asyncio
import json
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

# Track whether camera has been reset once
_scene_initialized = False


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
    global _scene_initialized

    frame = max(0, min(NUM_FRAMES - 1, int(frame)))
    points_data = adapter.get_ca_xyz(frame)
    n_points = len(points_data)
    if n_points == 0:
        return

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


def _apply_colormap(name: str):
    lut = _get_lookup_table(name or DEFAULT_COLORMAP)
    mapper.SetLookupTable(lut)
    mapper.Modified()


@state.change("current_frame", "current_metric", "current_colormap")
def _on_state_change(current_frame, current_metric, current_colormap, **_):
    metric = current_metric or DEFAULT_METRIC
    _apply_colormap(current_colormap)
    update_ribbon_geometry(current_frame or 0, metric)
    state.status_message = (
        f"Frame {current_frame} · Metric: {METRIC_CONFIG[metric]['label']} · Colormap: {(current_colormap or DEFAULT_COLORMAP).title()}"
    )
    ctrl.update_view()


with SinglePageLayout(server) as layout:
    layout.title.set_text("Protein Ribbon · Trame")

    with layout.toolbar:
        vuetify.VSpacer()
        vuetify.VSelect(
            label="Metric",
            dense=True,
            hide_details=True,
            items=("metric_options", []),
            v_model=("current_metric", DEFAULT_METRIC),
            style="max-width: 220px;",
        )
        vuetify.VSelect(
            label="Colormap",
            dense=True,
            hide_details=True,
            items=("colormap_options", []),
            v_model=("current_colormap", DEFAULT_COLORMAP),
            style="max-width: 220px; margin-left: 16px;",
        )
        vuetify.VSlider(
            min=0,
            max=("frame_max", 0),
            step=1,
            dense=True,
            hide_details=True,
            v_model=("current_frame", 0),
            style="max-width: 320px; margin-left: 24px;",
        )
        html.Div("Frame: {{ current_frame }}", classes="ml-4 subtitle-2")

    with layout.content:
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
            view = vtk_widgets.VtkLocalView(render_window, ref="ribbonView")
            html.Div(
                "{{ status_message }}",
                classes="caption mt-2 grey--text",
            )

ctrl.update_view = view.update

# Bootstrap once to populate data before serving
_apply_colormap(state.current_colormap)
update_ribbon_geometry(state.current_frame, state.current_metric)
state.status_message = (
    f"Frame {state.current_frame} · Metric: {METRIC_CONFIG[state.current_metric]['label']} · Colormap: {state.current_colormap.title()}"
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
