# Visualizer Architecture Extraction
## ASVS — Molecular Dynamics Visualization System

*Precise architectural reference for thesis documentation. All claims are grounded in the actual source files referenced.*

---

## 1. Visualization Stack

### Frameworks Used

The system employs **two distinct rendering paths** that operate simultaneously:

| Component | Technology | Entry Point |
|-----------|-----------|-------------|
| Primary ribbon viewer (Flask routes) | Three.js (WebGL) | `static/js/ribbon_viewer.js` |
| Trame ribbon viewer (VTK/WASM) | Trame + trame-vtklocal + Vue 2 + Vuetify | `trame_ribbon_app.py` |
| Ball-and-stick viewer | Three.js (WebGL) | `static/js/ballstick_viewer.js` |
| Hotspot/points viewer | Three.js (WebGL) | `templates/hotspot_viewer.html` |
| Legacy PDB viewer | Three.js + Vue + Vuetify | `static/js/3d_visualizer.js` |
| HTTP server | Flask 2.0+ | `app.py` |
| Trajectory I/O | MDAnalysis | `trajectory_adapter.py` |

### Rendering Engine

- **Three.js / WebGL** — used in all Flask-served viewers (`ribbon_viewer.js`, `ballstick_viewer.js`, `hotspot_viewer.html`). Renders directly in the browser via the WebGL API.
- **VTK (server-side, WASM-streamed)** — used exclusively by the Trame server (`trame_ribbon_app.py`). VTK pipeline runs on the Python server; `trame-vtklocal` (≥ 0.6.0) compiles VTK to WebAssembly and executes the render client-side, removing the need to stream pixel buffers over the network.

### VTK Usage

VTK is used **directly** in `trame_ribbon.py` and `trame_ribbon_app.py`:

```python
# trame_ribbon_app.py lines 193–238
points = vtk.vtkPoints()
polydata = vtk.vtkPolyData()
spline_filter = vtk.vtkSplineFilter()
ribbon_filter = vtk.vtkRibbonFilter()
mapper = vtk.vtkPolyDataMapper()
actor = vtk.vtkActor()
renderer = vtk.vtkRenderer()
render_window = vtk.vtkRenderWindow()
```

VTK is **not** wrapped exclusively by Trame — it is instantiated directly through the `vtk` Python package. Trame's role is to expose the `vtkRenderWindow` to a browser widget (`vtklocal.LocalView`).

The legacy `App.py` also uses VTK directly for a standalone PDB viewer (`vtkPDBReader`, `vtkProteinRibbonFilter`) with no Trame.

### NGL

**NGL is not present.** There are no references to NGL (NGL.Stage, NGL.Structure, or the NGL JavaScript library) anywhere in the codebase. All molecular visualization is implemented with Three.js or direct VTK.

---

## 2. Structural Rendering Details

### Structure Loading

Structures are loaded via **MDAnalysis** from two files:

| File | Format | Role |
|------|--------|------|
| `viewer/topology.pdb` | PDB | Atomic connectivity, residue/chain assignment |
| `viewer/trajectory.xtc` | Gromacs XTC (binary) | Frame-by-frame coordinates |

Loading occurs in `trajectory_adapter.py` (`TrajectoryAdapter.__init__`, line 52):

```python
self.universe = mda.Universe(topology_path, trajectory_path)
```

The topology PDB is **not** a multi-model PDB. It defines a single reference structure; all motion data comes from the XTC trajectory.

### Frame Handling

Frames are handled via **separate XTC file** (not MODEL blocks):

- MDAnalysis stores frame byte-offsets in `.trajectory.xtc_offsets.npz` for O(1) random access.
- The adapter exposes `get_frame_xyz(frame)` (`trajectory_adapter.py`, line 127), which seeks to the requested frame and returns all atom positions as a Python list.
- The Flask API serves per-frame coordinates at `/api/trajectory/frame/<frame>`.
- The frontend uses an **HTML `<input type="range">` slider** (`slider` element in `templates/hotspot_viewer.html` and `static/js/ribbon_viewer.js`) to select the frame index.
- The Trame viewer uses a Vuetify `VSlider` bound to `state.current_frame` (`trame_ribbon_app.py`, line 682).

### Representations Implemented

| Representation | Implementation | File |
|---------------|---------------|------|
| **Ribbon / cartoon** | Three.js `CatmullRomCurve3` + `TubeGeometry` with secondary structure widths, OR VTK `vtkSplineFilter` + `vtkRibbonFilter` | `static/js/ribbon_viewer.js`, `static/js/utils/spline.js`, `trame_ribbon_app.py` |
| **Ball-and-stick** | Three.js spheres (atoms) + cylinders (bonds, distance-based) | `static/js/ballstick_viewer.js` |
| **Point cloud** | Three.js `THREE.Points` | `templates/hotspot_viewer.html` (inline JS) |
| **Lines** | VTK `vtkLineSource` + `vtkTubeFilter` used for contact arcs and measurements | `trame_ribbon_app.py` (lines 348–370, 463–491) |

No space-filling (CPK) or surface representation is implemented.

### Anomaly Score Mapping

Anomaly scores are mapped as **custom per-residue scalar arrays**:

1. Scores are read from `viewer/anomaly_residue.json` (structure: `{"frame": {"residue_idx": float}}`).
2. For the Three.js ribbon: scores are fetched via `/api/metrics/anomaly/<frame>` and applied as vertex colors — one color per ring of `TubeGeometry` (`ribbon_viewer.js`, lines 480–509).
3. For the VTK ribbon: scores populate a `vtkFloatArray` named `"metric"` attached to `polydata.GetPointData().SetScalars(scalars)` (`trame_ribbon_app.py`, lines 197–200, 649–654). A `vtkLookupTable` maps the [0, 1] scalar range to RGB.

The mapping happens in:
- **Three.js path**: `ribbon_viewer.js` → `loadRibbon()` → `colorFromScore()` (lines 257–267), called once per residue ring.
- **VTK path**: `trame_ribbon_app.py` → `update_ribbon_geometry()` (line 622) → `_metric_values()` (line 586).

B-factor is **not** used for anomaly mapping. A separate `BFactorColorMapper` exists in `colormappers/bfactor.py` for the legacy PDB viewer only.

---

## 3. Scalar Channel Handling

### Available Scalar Channels

| Channel | Description | Frame-Dependent | Source File |
|---------|-------------|-----------------|-------------|
| `hotspot` | Dynamic kinetic hotspot intensity (Markov state model) | Yes | `viewer/hotspots_residue.json` |
| `anomaly` | Per-frame rare-conformation anomaly score (ensemble-anomaly-maps ML pipeline) | Yes | `viewer/anomaly_residue.json` |
| `rmsf` | Root Mean Square Fluctuation (trajectory-global flexibility) | No | `viewer/rmsf_residue.json` |
| `tica` | tICA importance (contribution to slow collective motions) | No | `viewer/tica_importance.json` |

Contacts (`viewer/contacts.json`) are visualized as lines, not as a scalar channel.

### Channel Switching

**Three.js ribbon viewer** (`ribbon_viewer.js`):
- An HTML `<select id="metricSelect">` element lists the four channels.
- On change, `currentMetric` is updated and `loadRibbon(currentFrame)` is called, which fetches the new metric data and rebuilds vertex colors (lines 787–793).
- Static channels (RMSF, tICA) are loaded once and cached in `metricsCache`; frame-dependent channels are cached per frame.

**VTK / Trame ribbon viewer** (`trame_ribbon_app.py`):
- A Vuetify `VSelect` bound to `state.current_metric` triggers the `update_metric` controller method, which calls `update_ribbon_geometry(state.current_frame, metric)`.

### Scalar Range and Normalization

- **All scalar channels are pre-normalized to [0, 1]** before storage in JSON. Normalization is performed **in the backend** (i.e., in the ML/preprocessing pipeline that generates the JSON files), not at render time.
- The `rmsf_residue.json` and `tica_importance.json` files include explicit `"min"`, `"max"`, and `"normalized"` keys, confirming that normalization happened upstream.
- No auto-scaling or percentile scaling is applied at visualization time. The viewer reads the pre-normalized values directly.
- No manual scalar range control is exposed to the user.
- The VTK mapper is fixed at `mapper.SetScalarRange(0.0, 1.0)` (`trame_ribbon_app.py`, line 223).

---

## 4. Interactivity

### Frame Scrubbing Mechanism

**Three.js viewers:**
- HTML `<input type="range" id="slider">` element.
- `slider.oninput` handler triggers `loadRibbon(+e.target.value)` (`ribbon_viewer.js`, line 725).
- Animation playback uses `requestAnimationFrame` loop with configurable speed (`playbackSpeed` variable, line 728).
- A canvas-based timeline heatmap (`heatmapCanvas`) lets users click to jump to a frame (lines 795–803).

**VTK / Trame viewer:**
- Vuetify `VSlider` bound to reactive state variable `state.current_frame`.
- State change triggers `update_frame` controller, which calls `update_ribbon_geometry()` and `ctrl.view_update()`.
- Animation uses `asyncio` / threading with configurable FPS (`state.animation_speed`, line 733).

### Residue Selection

**Three.js ribbon viewer:**
- **Click** on the ribbon canvas fires `onRibbonClick` (line 521), which casts a `THREE.Raycaster` ray against the tube mesh.
- The hit point is matched to the nearest CA position by Euclidean distance (lines 543–556).
- Selection displays a floating `<div id="infoPanel">` with all four metric values and scientific interpretations.
- **Hover**: `mousemove` updates `mouse` coordinates in normalized device coordinates (lines 104–108); hover tooltip is not rendered separately—only click triggers the info panel.

**VTK / Trame viewer:**
- **Click** on the VTK render window fires a `vtkCellPicker` + `vtkPointPicker` pick sequence (`trame_ribbon_app.py`, lines 308–326).
- The 3D pick position is matched to the nearest cached CA coordinate.
- A **dropdown** (`VSelect` with `state.residue_options`) also allows selecting residues by name/number (first 100 residues listed for performance).
- **Residue search** (`state.search_query`, `_search_residues()`, line 793) matches by residue name, number, or chain.

### Threshold, Top-K, and Highlighting

- **Threshold slider**: Not implemented. There is no UI element exposing a cutoff for hiding low-score residues.
- **Top-K filtering**: Implemented only for contacts (`_get_top_contacts(n=50)`, `trame_ribbon_app.py`, line 341), not for metric channels.
- **Residue highlighting**:
  - Three.js: No geometric highlight mesh is added on selection; information is shown in the side panel only.
  - VTK (`trame_ribbon.py`): A yellow `vtkSphereSource` actor (`create_selection_sphere`, line 268) is added at the selected CA position. In `trame_ribbon_app.py`, residue info is shown in the Trame UI panel.

### User Interaction State Storage

State is stored in:
- **Trame server**: Trame reactive state (`state.*` variables, lines 677–779) — persists for the lifetime of the server session.
- **Three.js**: Module-level JavaScript variables (`selectedResidue`, `metricsCache`, `caPositions`, `currentMetric`, `currentColormap`) — in-memory, reset on page reload.
- No persistent storage (database, localStorage, or cookies) is used.

---

## 5. Backend Architecture

### Server Type

The system runs **two concurrent Python servers**:

1. **Flask** (`app.py`) — classical HTTP/REST server on port 5000. Stateless; handles all API calls and serves HTML templates.
2. **Trame** (`trame_ribbon_app.py`) — WebSocket + HTTP server on port 9887 (default). Stateful; manages VTK pipeline and reactive state. Flask launches and monitors this server as a subprocess via `trame_ribbon_app.ensure_ribbon_server()`.

The Trame server URL is embedded in the Flask-rendered `ribbon_viewer.html` template as an iframe `src`.

### API Endpoints (Flask)

All endpoints are defined in `app.py`:

| Endpoint | Method | Description | Return Format |
|----------|--------|-------------|---------------|
| `/api/trajectory/meta` | GET | Frame/atom/residue counts, backbone flag | JSON object |
| `/api/trajectory/frame/<frame>` | GET | All atom XYZ for one frame | `{frame, xyz: [[x,y,z],...]}` |
| `/api/trajectory/residue_map` | GET | Atom-to-resnum mapping | `{resnos: [int,...]}` |
| `/api/trajectory/residue_meta` | GET | Residue table (index, resnum, resname, chain) | `{residues: [...]}` |
| `/api/trajectory/atoms` | GET | Atom metadata + covalent radii | `{atoms:[...], covalent_radii:{...}, has_full_backbone}` |
| `/api/trajectory/atoms_full/<frame>` | GET | All atoms with positions for one frame | `{frame, atoms:[...], has_full_backbone}` |
| `/api/trajectory/ca/<frame>` | GET | C-alpha positions for one frame | `{frame, ca: [[x,y,z],...]}` |
| `/api/trajectory/backbone/<frame>` | GET | N/CA/C backbone atoms per residue | `{frame, residues:[{N,CA,C},...]}` |
| `/api/trajectory/secondary_structure/<frame>` | GET | Geometry-inferred SS assignment (H/E/C) | `{frame, residues:[{ss},...]}` |
| `/api/hotspots/<frame>` | GET | Per-residue hotspot values for one frame | `{"resnum": float, ...}` |
| `/api/metrics/anomaly/<frame>` | GET | Per-residue anomaly scores for one frame | `{"residue_idx": float, ...}` |
| `/api/metrics/tica_importance` | GET | Per-residue tICA importance (static) | JSON from `tica_importance.json` |
| `/api/rmsf` | GET | Per-residue RMSF (static) | JSON from `rmsf_residue.json` |
| `/api/contacts` | GET | Residue-residue contact network | JSON from `contacts.json` |
| `/api/trajectory/atom_residue_index` | GET | Atom-to-residue 0-based index mapping | JSON array |

### Backend Computation

The backend **does not compute ML scores**. It serves pre-computed JSON files directly. The only computation performed server-side is:

- Secondary structure inference from CA trace geometry (`_assign_secondary_structure_from_ca`, `trajectory_adapter.py`, line 414) — a heuristic based on local curvature and CA-CA distances.
- Backbone reconstruction from CA-only topologies (`_reconstruct_backbone_from_ca`, line 242) — places synthetic N and C atoms along the backbone tangent using standard bond lengths.
- Hotspot aggregate fallback: if `hotspots_residue.json` has fewer than 50% non-zero values, the backend computes `hotspot = anomaly × 0.4 + rmsf × 0.3 + tica × 0.3` (`trame_ribbon_app.py`, line 598–608).

---

## 6. Data Contracts

### Expected Input Files

| File | Path | Format | Schema |
|------|------|--------|--------|
| Topology | `viewer/topology.pdb` | PDB | Standard PDB; full backbone preferred (N, CA, C, O per residue) |
| Trajectory | `viewer/trajectory.xtc` | Gromacs XTC | Must match topology atom count; 194 frames in shipped data |
| Hotspots | `viewer/hotspots_residue.json` | JSON | `{"frame_idx": {"residue_idx": float_0_to_1}}` |
| Anomaly | `viewer/anomaly_residue.json` | JSON | Same as hotspots; optional `"description"` key ignored |
| RMSF | `viewer/rmsf_residue.json` | JSON | `{"min": float, "max": float, "normalized": {"residue_idx": float_0_to_1}}` |
| tICA | `viewer/tica_importance.json` | JSON | Same as RMSF |
| Contacts | `viewer/contacts.json` | JSON | `{"contacts": [{"residue1": int, "residue2": int, "frequency": float},...]}` |

Paths can be overridden via environment variables:
`ASVS_PDB`, `ASVS_XTC`, `ASVS_HOTSPOTS_RES`, `ASVS_ANOMALY`, `ASVS_RMSF`, `ASVS_TICA`, `ASVS_CONTACTS`.

The files `hotspots_unified.json`, `residue_scores_dynamic.json`, and `multi_model_anomaly.pdb` referenced in some pipeline documentation **do not exist** in this repository and are not expected by the current visualizer code.

### Schema Enforcement and Validation

**No formal schema validation** (JSON Schema, Pydantic, etc.) is applied. File loading is wrapped in `try/except` blocks in `_load_json()` (`trame_ribbon_app.py`, line 49):

```python
def _load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[trame-ribbon] Missing optional data file: {path}")
    ...
    return default
```

Missing files silently return defaults (`{}` or `{"contacts": []}`). Malformed JSON raises an unhandled exception that will crash the server. There is no frame-count cross-validation between JSON metrics and the XTC trajectory.

---

## 7. Performance Handling

### Memory Loading Strategy

**The entire trajectory is held in memory** by MDAnalysis:

```python
# trajectory_adapter.py line 52
self.universe = mda.Universe(topology_path, trajectory_path)
```

MDAnalysis reads the XTC index (`.xtc_offsets.npz`) into memory, enabling O(1) frame seeks without sequential scanning. However, the full coordinate array for any given frame is loaded on demand by the `get_frame_xyz()` call — not pre-loaded into RAM for all frames simultaneously. The shipped trajectory (194 frames × 374 atoms × 3 floats × 4 bytes) occupies approximately 865 KB on disk; RAM usage from MDAnalysis's internal representation is larger but manageable.

All four metric JSON files are loaded entirely into memory at startup (`trame_ribbon_app.py`, lines 66–70) to enable synchronous frame scrubbing without disk I/O.

### Rendering Strategy

**Per-frame rendering** (not batched):

- Three.js: `loadRibbon(frame)` fetches CA coordinates via HTTP, rebuilds `TubeGeometry`, disposes of the previous geometry, and re-renders (lines 390–516). This is a complete geometry rebuild per frame.
- VTK: `update_ribbon_geometry(frame, metric)` updates `vtkPoints` and `vtkFloatArray` scalars in place (lines 622–668), then calls `ctrl.view_update()` which re-renders the existing VTK pipeline without reconstructing the full pipeline.

### Optimization Techniques

| Technique | Location | Description |
|-----------|----------|-------------|
| MDAnalysis frame offset caching | `trajectory_adapter.py` (MDAnalysis internal) | `.xtc_offsets.npz` enables O(1) frame access |
| Singleton adapter | `trajectory_adapter.py`, line 559 | MDAnalysis Universe initialized once per process |
| Metric data in-memory cache | `trame_ribbon_app.py`, lines 66–70 | All JSON loaded at startup |
| Client-side geometry cache | `ribbon_viewer.js`, `metricsCache` object | Static metrics (RMSF, tICA) fetched once |
| WebGL GPU rendering | Three.js | All vertex buffers resident on GPU after upload |
| trame-vtklocal WASM | `trame_ribbon_app.py` | VTK runs client-side via WebAssembly; no pixel streaming |
| Atom metadata cached once | `ribbon_viewer.js` (ball-stick viewer) | `/api/trajectory/atoms` fetched once on load |
| Frame offset file | `.trajectory.xtc_offsets.lock` / `.npz` | MDAnalysis creates on first run; reused on restart |

---

## 8. Deployment Mode

### Available Deployment Options

| Mode | Description | Command |
|------|-------------|---------|
| **Local (development)** | Flask dev server on localhost:5000 | `python app.py` |
| **Dockerized** | Single container via `Dockerfile` | `docker build -t molecular-visualizer . && docker run -p 5000:5000 molecular-visualizer` |
| **pip-installable** | `setup.py` defines `molecular-visualizer` package | `pip install -e .` |

There is **no static site** option — the visualizer requires a running Python server (Flask + MDAnalysis).

### Dockerfile

`Dockerfile` uses `python:3.9-slim`, installs via `pip install -e .`, downloads `1CBS.pdb` from RCSB at build time (saved to `static/examples/1cbs.pdb` for use by the legacy `App.py` PDB viewer), and exposes port 5000. This demo PDB is **unrelated** to `viewer/topology.pdb`, which is the CA-only topology for the trajectory-based visualization and must be supplied by the user alongside `viewer/trajectory.xtc`. The Dockerfile does **not** bundle trajectory or metric JSON data files. The Trame ribbon server (`trame_ribbon_app.py`) would need to be started separately inside the container; the current `Dockerfile` only launches `app.py`.

### Run Scripts

- `run.sh` / `run.bat` — convenience scripts for local startup.
- `run_ribbon_viewer.py` — launches the Trame ribbon server standalone.

---

## 9. Structured Summary

### Rendering Stack

```
Browser
  ├── Three.js (WebGL)
  │     ├── ribbon_viewer.js       — CatmullRomCurve3 + TubeGeometry, vertex colors
  │     ├── ballstick_viewer.js    — SphereGeometry + CylinderGeometry, element colors
  │     └── hotspot_viewer.html   — THREE.Points (point cloud)
  └── trame-vtklocal (WebAssembly)
        └── trame_ribbon_app.py   — vtkSplineFilter → vtkRibbonFilter → vtkPolyDataMapper
                                    rendered client-side via WASM
```

### Data Flow

```
viewer/topology.pdb + viewer/trajectory.xtc
    │
    └─► MDAnalysis Universe (trajectory_adapter.py)
            │
            ├─► Flask REST API (app.py) ──► HTTP JSON responses
            │       │
            │       └─► Browser (Three.js)
            │               ├─► CA coords per frame → TubeGeometry
            │               ├─► Metric scores → vertex colors
            │               └─► Residue metadata → tooltip panel
            │
            └─► Trame App (trame_ribbon_app.py)
                    │
                    ├─► vtkPoints ← CA coords
                    ├─► vtkFloatArray ← metric values
                    └─► vtkRibbonFilter → vtkPolyDataMapper → vtkRenderWindow
                                                → trame-vtklocal (WASM) → Browser canvas

viewer/anomaly_residue.json   ─┐
viewer/hotspots_residue.json  ─┤ (in-memory at startup)
viewer/rmsf_residue.json      ─┤─► _metric_values() → scalar array → LUT → ribbon color
viewer/tica_importance.json   ─┘
```

### Structural Mapping

| Aspect | Implementation |
|--------|---------------|
| Structure source | PDB topology + XTC trajectory via MDAnalysis |
| Frame access | XTC with `.npz` offset cache; O(1) random seek |
| Residue backbone | Full N/CA/C if present; synthetic reconstruction from CA trace if absent (`_reconstruct_backbone_from_ca`) |
| Secondary structure | Geometry-based inference from CA-CA distances and curvature (`_assign_secondary_structure_from_ca`) — not DSSP |
| Ribbon geometry | Three.js: `CatmullRomCurve3` spline through CA atoms, extruded as `TubeGeometry` with width variation by SS type; VTK: `vtkSplineFilter` → `vtkRibbonFilter` |
| Score-to-color | Pre-normalized [0,1] float → colormap lookup. Three.js: Viridis/Plasma/CoolWarm/BWR; VTK: Red-White-Blue LUT |

### Scalar Handling

| Metric | Source | Frame-dep. | Normalization | Where Applied |
|--------|--------|-----------|---------------|---------------|
| Dynamic Hotspot | `hotspots_residue.json` | Yes (per frame) | Pre-normalized [0,1] | Vertex color per residue ring |
| Dynamic Anomaly | `anomaly_residue.json` | Yes (per frame) | Pre-normalized [0,1] | Vertex color per residue ring |
| RMSF | `rmsf_residue.json` | No | Pre-normalized [0,1] (stored under `"normalized"` key) | Vertex color per residue ring |
| tICA Importance | `tica_importance.json` | No | Pre-normalized [0,1] (stored under `"normalized"` key) | Vertex color per residue ring |

Normalization is done **upstream** (in the ML pipeline). The visualizer applies values directly without rescaling.

### Interaction Model

| Interaction | Three.js Viewer | VTK/Trame Viewer |
|------------|----------------|-----------------|
| Frame scrubbing | HTML `<input range>` slider → `loadRibbon()` | Vuetify `VSlider` → `state.current_frame` → `update_ribbon_geometry()` |
| Metric switching | HTML `<select>` → re-fetch + re-render | Vuetify `VSelect` → `state.current_metric` → re-render |
| Residue selection | Click → Raycaster → nearest CA → side panel | Click → vtkCellPicker → nearest CA → Trame state panel; also dropdown |
| Hover tooltip | Mousemove updates mouse coords; click required to show info panel | `state.hover_tooltip_text` updated on mouse events |
| Animation playback | `requestAnimationFrame` loop with speed control | `asyncio`-based server loop with FPS control |
| Clipping planes | Three.js `THREE.Plane` on material | `vtkPlane` → `mapper.AddClippingPlane()` |
| Contacts | Not shown in Three.js viewers | VTK line actors from `contacts.json`; top-50 by frequency |
| Measurements | Not implemented in Three.js ribbon | Click two/three residues → distance (Å) or angle (°) via CA distances |
| Bookmarks | Not implemented | `state.bookmarks` list with camera state snapshots |
| Export | `canvas.toDataURL()` → PNG download | Not implemented in current Trame build |

User interaction state is stored in Trame reactive state (server-side, in-memory only). No persistent storage.

### Backend Role

| Responsibility | Flask (`app.py`) | Trame (`trame_ribbon_app.py`) |
|---------------|-----------------|-------------------------------|
| Serve HTML templates | ✓ | — |
| Serve static JS/CSS | ✓ | — |
| Trajectory API (REST) | ✓ | — |
| Metric API (REST) | ✓ | — |
| VTK pipeline management | — | ✓ |
| Reactive UI state | — | ✓ |
| Animation control | — | ✓ |
| Measurement tools | — | ✓ |
| Secondary structure inference | ✓ (via adapter) | — |
| Backbone reconstruction | ✓ (via adapter) | — |
| ML computation | ✗ (not present) | ✗ (not present) |

The backend is a **file server + lightweight geometry processor**. All ML scores are pre-computed externally and consumed as static JSON.

### Reproducibility / Contracts

**Required files for full functionality:**

```
viewer/
  topology.pdb           # PDB format, full backbone recommended
  trajectory.xtc         # Gromacs XTC, atom count must match topology
  hotspots_residue.json  # {"frame": {"residue_idx": float}}
  anomaly_residue.json   # {"frame": {"residue_idx": float}}
  rmsf_residue.json      # {"min": f, "max": f, "normalized": {"idx": f}}
  tica_importance.json   # {"min": f, "max": f, "normalized": {"idx": f}}
  contacts.json          # {"contacts": [{"residue1":i, "residue2":j, "frequency":f}]}
```

**Key constraints:**
- Frame count in JSON files must match XTC frame count (no validation enforced; mismatches cause silent 404 errors from metric endpoints).
- Residue indices in JSON files are **zero-based** (`"0"`, `"1"`, ...); PDB residue numbers (one-based) serve as fallback keys.
- No schema validation is performed at startup. Corrupt JSON crashes the server; missing JSON files return empty defaults.

### Limitations

1. **CA-only topology**: The shipped `viewer/topology.pdb` is a manually pre-generated CA-only file created as demo/sample data for this repository — it was not auto-generated by the visualizer itself. Each atom is written as a CA atom with no sidechain or bond information. N and C backbone atoms are synthetically reconstructed at render time via `_reconstruct_backbone_from_ca()` (`trajectory_adapter.py`, line 242) using simplified geometry. This degrades ribbon orientation fidelity. Users who supply their own full-atom PDB topology (with N, CA, C, O per residue) will get physically accurate ribbon rendering.
2. **No schema validation**: Missing or malformed data files produce no user-facing error — metrics silently default to zero.
3. **No frame-count cross-validation**: Mismatches between XTC frames and JSON frame keys are not detected at startup.
4. **Full trajectory in memory**: MDAnalysis holds all frame offsets in RAM. For very large trajectories (>10,000 frames), startup may be slow and memory footprint significant.
5. **Complete geometry rebuild per frame** (Three.js path): Every frame change rebuilds `TubeGeometry` and re-uploads buffers to the GPU. This limits smooth real-time playback at high atom counts.
6. **No manual scalar range control**: Users cannot adjust the display range of any metric; all values must be pre-normalized to [0, 1] upstream.
7. **No percentile or auto-scaling**: Outliers dominate the color range if upstream normalization is not done carefully.
8. **Trame server as subprocess**: Flask launches `trame_ribbon_app.py` as a subprocess; if it fails to start, the ribbon viewer silently shows an error iframe with no automatic retry.
9. **Single-session state**: Trame state is shared across all browser tabs connected to the same server. Multiple simultaneous users would conflict.
10. **No NGL, no surface rendering, no ligand-specific views**: Only ribbon, ball-and-stick, and point cloud representations are implemented.
11. **Dockerfile incomplete for Trame**: The container image launches only Flask (`app.py`); the Trame ribbon server must be started separately.
