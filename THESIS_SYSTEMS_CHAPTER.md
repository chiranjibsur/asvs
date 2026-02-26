# System Architecture and Implementation Analysis
## Molecular Visualization Framework with ML-Derived Signal Integration

**Computer Science Capstone Thesis - Systems Chapter**  
**Project:** ASVS (Animated Structure Visualization System)  
**Repository:** chiranjibsur/asvs

---

## Table of Contents

1. [Overall Architecture](#1-overall-architecture)
2. [Backend: Trame + VTK Pipeline](#2-backend-trame--vtk)
3. [Frontend: Three.js and vtklocal WebAssembly](#3-frontend-threejs-and-vtklocal-webassembly)
4. [Signal Abstraction and Extensibility](#4-signal-abstraction-and-extensibility)
5. [Performance and Scalability](#5-performance-and-scalability)
6. [Engineering Constraints and Tradeoffs](#6-engineering-constraints-and-tradeoffs)

---

## 1. Overall Architecture

### 1.1 High-Level Architecture: Backend vs Frontend

The ASVS system implements a **hybrid client-server architecture** that combines traditional web application patterns with modern WebAssembly-powered rendering. The architecture can be conceptualized as three distinct tiers:

**Backend Tier (Python):**
- **Trajectory Adapter** (`trajectory_adapter.py`): Singleton pattern adapter wrapping MDAnalysis for molecular dynamics trajectory access
- **Flask REST API** (`app.py`): Stateless HTTP endpoints serving coordinate data and metrics
- **Trame Application** (`trame_ribbon_app.py`): WebSocket-based reactive application with VTK rendering pipeline

**Middle Tier (Data Layer):**
- **Topology File**: `viewer/topology.pdb` (374 atoms, protein backbone structure)
- **Trajectory File**: `viewer/trajectory.xtc` (194 frames, compressed binary Gromacs format)
- **Signal Files**: JSON-formatted per-frame or per-residue scalar metrics (hotspots, anomaly, RMSF, tICA)
- **Contact Network**: JSON-encoded residue-residue proximity relationships

**Frontend Tier (JavaScript/WebAssembly):**
- **Three.js Renderer** (`static/js/ribbon_viewer.js`, `ballstick_viewer.js`): Classical client-side WebGL rendering for Flask endpoints
- **vtklocal WebAssembly** (via `trame-vtklocal`): Client-side VTK execution for Trame application, eliminating server-side rendering overhead
- **Vue.js/Vuetify UI**: Reactive component framework for control panels, sliders, and information displays

This architecture deliberately **decouples visualization from ML computation**—the backend never imports ML libraries (scikit-learn, PyEMMA), consuming only pre-computed JSON exports from the ensemble-anomaly-maps pipeline. This separation enables independent development, facilitates reproducibility, and prevents visualization code from inheriting ML dependencies.

### 1.2 Data Flow Architecture

The complete data flow from file storage to rendered pixels follows this pipeline:

```
Disk Files (PDB + XTC + JSON)
    ↓
TrajectoryAdapter (MDAnalysis singleton, Line 46-135 in trajectory_adapter.py)
    ↓ [Lazy load Universe on first access]
    ↓ [Cache frame offsets for O(1) random access]
    ↓
Backend State Layer (Trame state variables, Lines 677-779 in trame_ribbon_app.py)
    ↓ [current_frame, current_metric, selected_residue_idx]
    ↓
VTK Pipeline (Lines 193-238 in trame_ribbon_app.py)
    ↓ [vtkPoints ← coordinates]
    ↓ [vtkFloatArray ← metric scalars]
    ↓ [vtkSplineFilter ← smooth interpolation]
    ↓ [vtkRibbonFilter ← 3D ribbon geometry]
    ↓ [vtkPolyDataMapper ← color mapping via LUT]
    ↓
vtklocal WebAssembly (Lines 1722-1730)
    ↓ [Serialize VTK scene to WebAssembly heap]
    ↓ [Client-side rendering via WebGL]
    ↓
Browser Display (60 FPS interactive rendering)
```

**Key Architectural Pattern**: The system employs **reactive state management** where any change to `state.current_frame` or `state.current_metric` triggers cascading updates through decorated `@state.change()` watchers (Lines 1060-1124), which invoke VTK pipeline updates and signal frontend re-renders via `ctrl.view_update()`.

### 1.3 Main Components and Responsibilities

#### Backend Components

| Component | File/Class | Primary Responsibility | Key Design Pattern |
|-----------|-----------|----------------------|-------------------|
| **TrajectoryAdapter** | `trajectory_adapter.py:46-565` | Wraps MDAnalysis; provides frame coordinate extraction, residue metadata, C-alpha filtering | Singleton (via `get_adapter()` factory) |
| **Flask REST Server** | `app.py:1-343` | Serves `/api/trajectory/*` endpoints for coordinates, residues, hotspots | RESTful API |
| **Trame Application** | `trame_ribbon_app.py:1-2099` | Reactive state management, VTK pipeline construction, UI layout definition | Observer (reactive state) |
| **VTK Pipeline Builder** | `trame_ribbon_app.py:180-238` | Constructs and connects vtkPoints → vtkSplineFilter → vtkRibbonFilter → vtkMapper → vtkActor chain | Pipeline (GoF pattern) |
| **Metric Loader** | `trame_ribbon_app.py:49-70` | Loads JSON signal files into memory dicts at application startup | Eager loading |
| **Colormap Builder** | `trame_ribbon_app.py:162-179` | Creates VTK lookup tables (LUT) from hex color presets with caching | Factory + Cache |

#### Frontend Components

| Component | File | Primary Responsibility | Rendering Technology |
|-----------|------|----------------------|---------------------|
| **Ribbon Viewer** | `static/js/ribbon_viewer.js` | Three.js ribbon rendering via CatmullRom splines, client-side metric fetching | Three.js WebGL |
| **Ball-and-Stick Viewer** | `static/js/ballstick_viewer.js` | Atomistic representation with sphere glyphs and cylinder bonds | Three.js WebGL |
| **vtklocal View** | `trame_ribbon_app.py:1722-1730` | WebAssembly VTK execution, event routing (click/hover) | VTK.wasm + WebGL |
| **Vue.js UI** | `trame_ribbon_app.py:1500-2000` | Reactive control panels (sliders, dropdowns, buttons), data binding | Vue 2 + Vuetify |

### 1.4 State Management Architecture

The Trame application maintains **centralized reactive state** through the `server.state` object, eliminating prop-drilling and ensuring single source of truth. State is organized into functional domains:

**Visualization State** (Lines 677-690):
```python
state.current_frame = 0              # Active trajectory frame [0, NUM_FRAMES-1]
state.current_metric = "hotspot"      # Active signal channel
state.current_colormap = "red_white_blue"  # Active color preset
```

**Interaction State** (Lines 711-727):
```python
state.selected_residue_idx = -1       # Currently selected residue (-1 = none)
state.measurement_mode = ""           # "", "distance", or "angle"
state.measurement_picks = []          # List of picked residue indices
```

**Animation State** (Lines 729-737):
```python
state.animation_playing = False       # Playback active flag
state.animation_speed = 10            # Target FPS (frames per second)
```

**Clipping State** (Lines 691-699):
```python
state.clip_enabled = False            # Clipping plane active
state.clip_axis = "X"                 # Normal direction: X, Y, or Z
state.clip_position = 50              # Position along axis [0-100%]
```

**State Change Propagation**:  
When `state.current_frame = 89` executes, the following cascade occurs:

1. **Watcher Invocation**: `@state.change("current_frame")` decorator triggers `_on_state_change()` (Line 1060)
2. **Geometry Update**: `update_ribbon_geometry(89, metric)` extracts CA positions for frame 89 via `adapter.get_ca_frame(89)` (Line 631), updates `vtkPoints` object (Line 646), fetches metric values (Line 649), updates `vtkFloatArray` scalars (Line 654)
3. **VTK Modified Flags**: `scalars.Modified()` signals that scalar array changed (Line 655), triggering mapper re-evaluation
4. **Frontend Sync**: `ctrl.view_update()` sends WebSocket message to client instructing VTK.wasm to re-render (Line 1083)
5. **UI Update**: Vue reactivity updates status message, frame slider position, and residue info panel if residue is selected (Lines 1074-1081)

This architecture ensures **declarative updates**—developers modify state variables, and the framework handles all downstream consequences. No manual DOM manipulation or explicit render calls are required.

---

## 2. Backend: Trame + VTK

### 2.1 Molecular Trajectory Loading

#### File Format Support

The system supports **two primary trajectory formats** through MDAnalysis:

1. **Topology (Structure) Files**:
   - **PDB** (Protein Data Bank): Primary format, defines atom types, residue assignments, chain IDs
   - Path resolution order (Lines 14-42 in `trajectory_adapter.py`):
     1. Environment variables: `ASVS_PDB` / `ASVS_XTC`
     2. `viewer/topology.pdb` + `viewer/trajectory.xtc`
     3. `data/md/topology.pdb` + `data/md/trajectory.xtc`

2. **Trajectory (Coordinate) Files**:
   - **XTC** (Gromacs compressed trajectory): Binary format with lossy compression, ~10:1 reduction vs raw coordinates
   - MDAnalysis transparently decompresses on read
   - Frame offsets cached in `.trajectory.xtc_offsets.npz` for O(1) random access (bypassing sequential decompression)

#### In-Memory Representation

**MDAnalysis Universe Object** (`trajectory_adapter.py:52`):
```python
self.universe = mda.Universe(topology_path, trajectory_path)
```

This creates:
- **AtomGroup**: Lazy-evaluated collection of all atoms with properties (position, element, residue)
- **Trajectory Iterator**: On-disk streaming interface; coordinates loaded only when accessed
- **Residue Hierarchy**: Linked residue → atoms mapping for topology traversal

**Key Data Structures**:

| Structure | Type | Purpose | Line |
|-----------|------|---------|------|
| `_meta` | `Dict[str, int]` | `{n_frames, n_atoms, n_residues}` metadata | 55-59 |
| `_resnos` | `List[int]` | Atom index → residue number mapping (PDB numbering) | 62-67 |
| `_res_table` | `List[Dict]` | Residue metadata: `{index, resnum, resname, chain}` | 70-83 |
| `_ca_positions_cache` | `List[Tuple[float, float, float]]` | Most recent frame's C-alpha (x,y,z) coordinates | 333 (trame_ribbon_app.py) |

**C-Alpha Extraction** (Line 184-186 in `trajectory_adapter.py`):
```python
ca_atoms = self.universe.select_atoms("name CA")
self.universe.trajectory[frame]  # Seek to frame
positions = ca_atoms.positions   # NumPy array shape (NUM_RESIDUES, 3)
```

The `select_atoms("name CA")` query uses MDAnalysis's selection language, filtering to backbone C-alpha atoms only (one per residue). This reduces point count from ~374 atoms to ~47 residues for typical proteins, enabling real-time rendering.

**Coordinate Format**:  
MDAnalysis returns positions as NumPy `ndarray[float32, (N, 3)]` in Ångströms. The adapter converts to Python lists for JSON serialization (Line 184+):
```python
return [tuple(p) for p in positions]  # [(x1,y1,z1), (x2,y2,z2), ...]
```

### 2.2 ML-Derived Signal Ingestion

#### Expected Input Formats

ML signals are exported as **JSON dictionaries** with strict normalization contracts:

**Frame-Dependent Signals** (Hotspot, Anomaly):
```json
{
  "0": {"0": 0.234, "1": 0.456, "2": 0.123, ...},  // Frame 0
  "1": {"0": 0.245, "1": 0.467, "2": 0.134, ...},  // Frame 1
  ...
}
```
- **Outer keys**: Frame indices as strings (0-based)
- **Inner keys**: Residue indices as strings (0-based, matching topology residue order)
- **Values**: Pre-normalized floats in [0, 1]

**Frame-Independent Signals** (RMSF, tICA):
```json
{
  "description": "Root mean square fluctuation per residue",
  "min": 0.0001,
  "max": 3.4567,
  "normalized": {
    "0": 0.0234,
    "1": 0.0512,
    ...
  }
}
```
- **normalized** sub-dict contains [0, 1] values
- **min/max** preserve original units for scientific interpretation

#### Loading and Caching

**Eager Loading at Startup** (Lines 66-70 in `trame_ribbon_app.py`):
```python
HOTSPOTS = _load_json(HOTSPOTS_RES_PATH, {})
ANOMALY = _load_json(ANOMALY_PATH, {})
RMSF = _normalized_payload(_load_json(RMSF_PATH, {}))  # Extracts "normalized" key
TICA = _normalized_payload(_load_json(TICA_PATH, {}))
CONTACTS_DATA = _load_json(CONTACTS_PATH, {"contacts": []})
```

All JSON files load into Python `dict` objects in RAM. For a typical dataset (194 frames × 47 residues = 9,118 values per metric × 4 metrics × 8 bytes/float ≈ **290 KB total**), this is negligible. However, microsecond-timescale trajectories (100K frames) would require ~150 MB, motivating lazy-loading strategies for production.

#### Alignment with Trajectory Frames

**Frame Count Validation**:  
The system expects exact frame count matches between trajectory and metric files. If `trajectory.xtc` contains 194 frames, `hotspots_residue.json` **must** have keys "0" through "193". Mismatches manifest as:
- **Missing frames**: Metric lookup returns empty dict `{}`, all residues colored blue (value 0.0)
- **Extra frames**: Ignored silently (never accessed if beyond trajectory length)

**Residue Index Alignment** (Lines 564-583 in `trame_ribbon_app.py`):
```python
def _residue_value(frame_blob: Dict, residue_idx: int) -> float:
    residue = RESIDUES[residue_idx]
    fallbacks = (
        str(residue_idx),              # Primary: 0-based index
        str(residue.get("resnum")),    # Fallback: PDB residue number
        str(residue_idx + 1),          # Fallback: 1-based index
    )
    for key in fallbacks:
        if frame_blob and key in frame_blob:
            return float(frame_blob[key])
    return 0.0  # Default: no signal
```

This **fallback strategy** tolerates minor indexing inconsistencies. If the ML pipeline exports using PDB residue numbers (e.g., "145", "146") instead of 0-based indices ("0", "1"), the lookup gracefully degrades to secondary keys. However, **systematic misalignment** (all indices off by one) produces visibly incorrect colorings, serving as a validation mechanism.

### 2.3 Backend Data Exposure to Frontend

#### Flask REST API Endpoints

**Metadata Endpoint** (`app.py:58-66`):
```python
@app.route("/api/trajectory/meta")
def api_meta():
    return jsonify(adapter.get_meta())
    # Returns: {"n_frames": 194, "n_atoms": 374, "n_residues": 47}
```

**Frame Coordinates** (`app.py:119-129`):
```python
@app.route("/api/trajectory/ca/<int:frame>")
def api_ca_frame(frame):
    ca_positions = adapter.get_ca_frame(frame)
    return jsonify({"positions": ca_positions})
    # Returns: {"positions": [[x1,y1,z1], [x2,y2,z2], ...]}
```

**Hotspot Metrics** (`app.py:157-169`):
```python
@app.route("/api/hotspots/<int:frame>")
def api_hotspots_frame(frame):
    hotspots = _load_json(HOTSPOTS_RES_PATH, {})
    frame_data = hotspots.get(str(frame), {})
    return jsonify(frame_data)
    # Returns: {"0": 0.234, "1": 0.456, ...}
```

These endpoints enable **stateless coordinate fetching** for Three.js-based viewers, which poll new coordinates on frame changes via `fetch('/api/trajectory/ca/${frame}')`.

#### Trame Reactive State Exposure

**WebSocket-Based State Sync**:  
Unlike REST APIs, Trame uses **bidirectional WebSocket communication** (via `wslink` protocol). When backend updates `state.current_frame`, the change propagates to all connected clients automatically. Frontend Vue templates bind directly to state:

```html
<v-slider v-model="current_frame" :max="n_frames - 1"></v-slider>
```

Moving the slider sends a WebSocket message updating backend `state.current_frame`, triggering `@state.change("current_frame")` watchers, which update VTK geometry and send render commands back to the client.

#### Event Handling Mechanisms

**Controller Methods** (Lines 1197-1475 in `trame_ribbon_app.py`):
```python
@ctrl.add("on_vtk_click")
def on_vtk_click(event):
    x, y = int(event.get("x")), int(event.get("y"))
    residue_idx = _perform_pick(x, y)  # VTK picking via cell_picker
    if residue_idx >= 0:
        state.selected_residue_idx = residue_idx
        state.residue_info = _format_residue_info(residue_idx, state.current_frame)
        ctrl.view_update()
```

The `@ctrl.add()` decorator registers RPC-style methods callable from frontend. When a user clicks the VTK view, the frontend emits:
```javascript
LeftButtonPress=(ctrl.on_vtk_click, "[$event]")
```

This invokes the backend method with a dictionary containing click coordinates, enabling server-side VTK picking logic (Lines 282-305).

**Reactive Update Flow**:
```
Frontend Action (click slider)
    ↓ WebSocket
Backend state.current_frame = 89
    ↓ @state.change decorator
update_ribbon_geometry(89, metric)
    ↓ VTK pipeline modification
ctrl.view_update()
    ↓ WebSocket
Frontend vtklocal.LocalView re-renders
```

No polling or manual synchronization required—the framework handles bidirectional state consistency.

---

## 3. Frontend: Three.js and vtklocal WebAssembly

### 3.1 Molecular Geometry Representation

The frontend employs **two distinct rendering approaches** depending on the viewer:

#### Three.js Ribbon Viewer (`static/js/ribbon_viewer.js`)

**Spline-Based Ribbon Construction** (Lines 380-450):
```javascript
async function loadRibbon(frame) {
  const data = await fetch(`/api/trajectory/ca/${frame}`).then(r => r.json());
  const positions = data.positions;  // [[x,y,z], ...]
  
  // Create smooth curve through CA positions
  const points = positions.map(p => new THREE.Vector3(p[0], p[1], p[2]));
  const curve = new THREE.CatmullRomCurve3(points);
  curve.type = 'centripetal';  // Prevents self-intersections
  
  // Generate tube geometry along curve
  const geometry = new THREE.TubeGeometry(
    curve,
    tubularSegments: positions.length * 10,  // Smoothness
    radius: 0.3,                              // Ribbon width
    radialSegments: 8,                        // Circular cross-section resolution
    closed: false
  );
  
  // Fetch metric values and assign colors
  const metricData = await fetchMetricData(currentMetric, frame);
  const colors = new Float32Array(geometry.attributes.position.count * 3);
  
  for (let i = 0; i < geometry.attributes.position.count; i++) {
    const segmentIdx = Math.floor(i / radialSegments);  // Map vertex to residue
    const residueIdx = Math.floor(segmentIdx * positions.length / tubularSegments);
    const value = metricData[String(residueIdx)] || 0.0;
    const color = colorFromScore(value);  // LUT lookup (Lines 256-267)
    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;
  }
  
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  
  const material = new THREE.MeshPhongMaterial({ 
    vertexColors: true,
    shininess: 30 
  });
  const mesh = new THREE.Mesh(geometry, material);
  scene.add(mesh);
}
```

**Key Design Choices**:
- **Catmull-Rom splines**: Interpolate smooth curves through CA positions without requiring control points
- **Centripetal parameterization**: Prevents loops/cusps when consecutive points are close
- **Vertex coloring**: Each tube vertex inherits color from its parent residue's metric value
- **Per-frame fetch**: Coordinates and metrics fetched separately, enabling metric switching without re-fetching positions

#### vtklocal WebAssembly Viewer (`trame_ribbon_app.py:1722-1730`)

**VTK Pipeline in WebAssembly**:
```python
view = vtklocal.LocalView(
    render_window,                    # VTK render window from backend
    ref="ribbonView",
    namespace="ribbonNS",
    interactor_events=("events", ["LeftButtonPress", "MouseMove"]),
    LeftButtonPress=(ctrl.on_vtk_click, "[$event]"),
    MouseMove=(ctrl.on_vtk_hover, "[$event]"),
)
```

The `vtklocal.LocalView` widget serializes the entire VTK pipeline (`render_window` + all contained actors, mappers, filters) into a binary format, transfers it to the browser, and **reconstructs the pipeline in WebAssembly**. The VTK C++ code (compiled to WASM via Emscripten) executes natively in the browser, using WebGL for rendering.

**Geometry Pipeline**:
1. **vtkPoints** (Line 193): NumPy-like array of (x,y,z) coordinates
2. **vtkCellArray** (Line 195): Polyline connecting points in residue order
3. **vtkSplineFilter** (Line 203-206): Subdivides polyline into smooth spline with `SetLength(1.5)` Ångström subdivision
4. **vtkRibbonFilter** (Line 208-219): Extrudes spline into flat ribbon with `SetWidth(0.3)`, computes vertex normals for shading
5. **vtkPolyDataMapper** (Line 221-225): Converts ribbon polydata to rendering primitives, applies LUT coloring

**Rendering Output**:  
The final ribbon consists of:
- **Vertices**: ~5000-10000 depending on spline subdivision density
- **Triangles**: ~10000-20000 for ribbon surface tessellation
- **Normals**: Per-vertex normals for Phong shading
- **Colors**: Per-vertex RGB triplets from LUT sampling

### 3.2 Scalar Value to Color Mapping

#### Colormap Implementation

**Backend VTK LUT Construction** (Lines 162-173 in `trame_ribbon_app.py`):
```python
def _build_lookup_table(name: str) -> vtk.vtkLookupTable:
    preset = COLORMAP_PRESETS.get(name, COLORMAP_PRESETS[DEFAULT_COLORMAP])
    rgb_stops = [(pos, _hex_to_rgb(hex_col)) for pos, hex_col in preset]
    
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(256)  # 8-bit color resolution
    lut.Build()
    
    for i in range(256):
        t = i / 255.0
        r, g, b = _interpolate_color(rgb_stops, t)  # Linear interpolation
        lut.SetTableValue(i, r, g, b, 1.0)  # RGB + alpha
    
    return lut
```

**Color Preset Definition** (Lines 125-138):
```python
COLORMAP_PRESETS = {
    "red_white_blue": [
        (0.0, "#08306b"),   # Dark blue (low values)
        (0.2, "#4292c6"),   # Light blue
        (0.5, "#ffffff"),   # White (midpoint)
        (0.7, "#fcbba1"),   # Light red
        (1.0, "#67000d"),   # Dark red (high values)
    ],
    # Additional presets: viridis, plasma, coolwarm
}
```

**Perceptual Design**: The red-white-blue diverging colormap is **asymmetric**—the transition from white to red begins at 0.5 but saturates by 0.7, allocating 50% of the LUT range to high-value differentiation. This amplifies visibility of rare-event anomalies (typically 0.7-1.0).

#### Where Color Mapping Occurs

**Backend (VTK Pipeline)**:
- **Scalar Range**: `mapper.SetScalarRange(0.0, 1.0)` (Line 223)
- **LUT Assignment**: `mapper.SetLookupTable(_get_lookup_table("red_white_blue"))` (Line 225)
- **Per-Vertex Coloring**: During rendering, VTK samples the LUT for each vertex's scalar value, retrieving RGB from the 256-entry table

**Frontend (Three.js)**:
- **Colormap Functions** (Lines 170-267 in `ribbon_viewer.js`):
```javascript
function colorViridis(t) {
  const stops = [
    {t: 0.0, r: 0x44/255, g: 0x01/255, b: 0x54/255},
    {t: 0.5, r: 0x21/255, g: 0x82/255, b: 0x8e/255},
    {t: 1.0, r: 0xfd/255, g: 0xe7/255, b: 0x25/255},
  ];
  // Linear interpolation between stops
}
```

- **Application**: For each tube vertex, `colorFromScore(value)` computes RGB triplet, stored in `geometry.attributes.color`

#### Color Recomputation Frequency

**Trame/vtklocal**:  
Colors recompute when:
1. **Metric changes**: New scalar array values (Line 654), triggers `scalars.Modified()` → mapper re-samples LUT
2. **Frame changes**: New coordinates AND new scalars, full geometry rebuild (Line 622-670)
3. **Colormap changes**: New LUT applied to mapper (Line 924-927), existing scalars re-mapped to new colors

**Cost**: Negligible—LUT lookup is O(1) per vertex, total ~10ms for 10K vertices

**Three.js**:  
Colors recompute when:
1. **Metric changes** (same frame): Fetch new metric data, recompute vertex colors, update `geometry.attributes.color.needsUpdate = true`
2. **Frame changes**: Full geometry rebuild (new spline, new colors)

**Cost**: ~20-50ms for color recomputation + GPU buffer upload

### 3.3 Rendering Loop and Update Strategy

#### Three.js Rendering Loop (`ribbon_viewer.js:750-780`)

```javascript
function animate() {
  requestAnimationFrame(animate);  // 60 FPS browser sync
  
  controls.update();  // OrbitControls camera movement
  
  // Update FPS counter
  updateFPS();
  
  // Raycasting for hover tooltips (throttled to 50ms)
  if (hoverEnabled && Date.now() - lastHoverTime > 50) {
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(scene.children);
    if (intersects.length > 0) {
      // Display tooltip with residue info
    }
  }
  
  renderer.render(scene, camera);
}
animate();  // Start loop
```

**Update Strategy**:
- **Continuous rendering**: Loop runs at 60 FPS regardless of scene changes
- **Conditional updates**: Geometry only rebuilds on frame/metric changes, not every frame
- **Throttling**: Raycasting limited to 20 Hz to prevent performance degradation

#### vtklocal Rendering Loop

**Event-Driven Rendering**:  
Unlike Three.js, vtklocal uses **demand rendering**—no continuous loop. Renders occur only when:
1. **State changes**: `ctrl.view_update()` sends WebSocket render command
2. **User interaction**: Camera rotation, pan, zoom (handled by VTK interactor in WASM)

**Rendering Trigger**:
```python
@state.change("current_frame")
def _on_state_change(...):
    update_ribbon_geometry(...)  # Modify VTK objects
    ctrl.view_update()           # Signal render
```

The `view_update()` call serializes VTK scene delta (changed objects only), sends to client, and WASM VTK executes `render_window.Render()`.

**Performance Benefit**: Eliminates redundant 60 FPS rendering when scene is static, reducing CPU/GPU load by >90%.

### 3.4 User Interaction Implementation

#### Time Scrubbing

**Trame Slider** (Lines 1577-1592 in `trame_ribbon_app.py`):
```python
vuetify.VSlider(
    v_model=("current_frame", 0),
    min=0,
    max=("n_frames - 1",),
    step=1,
    thumb_label="always",
    hide_details=True,
)
```

**Interaction Flow**:
1. User drags slider → Frontend updates `state.current_frame` via two-way binding
2. WebSocket sends new value to backend
3. `@state.change("current_frame")` watcher triggers
4. `update_ribbon_geometry(new_frame, metric)` extracts new coordinates, updates `vtkPoints`
5. `ctrl.view_update()` signals client to re-render
6. WASM VTK renders updated geometry at 60 FPS

**Latency**: ~10-30ms from drag to visible update (imperceptible to users)

#### Residue Selection

**VTK Cell Picking** (Lines 282-305 in `trame_ribbon_app.py`):
```python
def _perform_pick(x: int, y: int) -> int:
    """Perform VTK picking to find clicked residue."""
    cell_picker.Pick(x, y, 0, renderer)  # Cast ray into 3D scene
    
    if cell_picker.GetCellId() < 0:
        return -1  # No intersection
    
    pick_pos = cell_picker.GetPickPosition()  # 3D world coordinates
    
    # Find nearest CA position to pick point
    min_dist, best_idx = float('inf'), -1
    for idx, ca_pos in enumerate(_ca_positions_cache):
        dist = math.sqrt(sum((p - q)**2 for p, q in zip(pick_pos, ca_pos)))
        if dist < min_dist:
            min_dist, best_idx = dist, idx
    
    return best_idx if min_dist < 5.0 else -1  # 5 Å threshold
```

**Why Spatial Snapping?**  
Ribbon geometry is interpolated—clicking on the ribbon surface may not coincide with any CA position. The spatial search finds the closest residue center, ensuring clicks anywhere on the ribbon region select the intended residue.

#### Signal Toggling

**Metric Dropdown** (Lines 1560-1575):
```python
vuetify.VSelect(
    label="Metric",
    v_model=("current_metric", "hotspot"),
    items=("metric_items",),  # ["hotspot", "anomaly", "rmsf", "tica"]
    dense=True,
    hide_details=True,
)
```

**Update Flow**:
1. User selects "anomaly" → `state.current_metric = "anomaly"`
2. `@state.change("current_metric")` watcher triggers
3. `_metric_values("anomaly", frame)` fetches new scalar array
4. VTK `scalars.SetValue(i, value)` updates each residue's value
5. `scalars.Modified()` marks array dirty
6. `ctrl.view_update()` triggers re-render with new colors

**Cost**: ~5-10ms (metric lookup + scalar array update), **no geometry rebuild**

---

## 4. Signal Abstraction and Extensibility

### 4.1 Signal Definition and Structure

A "signal" in this codebase is any **per-residue scalar field** that can be visualized via color mapping. Signals are abstracted through the `METRIC_CONFIG` dictionary (Lines 82-109 in `trame_ribbon_app.py`):

```python
METRIC_CONFIG = {
    "hotspot": {
        "label": "Dynamic Hotspot",
        "description": "Per-frame ML hotspot intensity",
        "frame_dependent": True,
        "source": HOTSPOTS,  # Dict loaded from JSON
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
        "description": "Contribution to slow collective motions",
        "frame_dependent": False,
        "source": TICA,
    },
}
```

### 4.2 Required Fields for New Signals

To add a new signal (e.g., "binding_affinity"), follow this pattern:

1. **Create JSON file** (`viewer/binding_affinity.json`):
```json
{
  "description": "Ligand binding affinity per residue",
  "min": -15.0,
  "max": 0.0,
  "normalized": {
    "0": 0.234,
    "1": 0.567,
    ...
  }
}
```

2. **Load at startup** (add to Line 66-70):
```python
BINDING = _normalized_payload(_load_json("viewer/binding_affinity.json", {}))
```

3. **Register in config** (add to `METRIC_CONFIG`):
```python
"binding_affinity": {
    "label": "Binding Affinity",
    "description": "Predicted ligand binding strength",
    "frame_dependent": False,  # Static metric
    "source": BINDING,
}
```

4. **Add to UI dropdown** (Line 1560-1575):
```python
items=[
    {"text": "Dynamic Hotspot", "value": "hotspot"},
    {"text": "Dynamic Anomaly", "value": "anomaly"},
    {"text": "RMSF", "value": "rmsf"},
    {"text": "tICA", "value": "tica"},
    {"text": "Binding Affinity", "value": "binding_affinity"},  # NEW
]
```

**No code changes required** beyond configuration—the metric loading, color mapping, and UI integration are generic.

### 4.3 Semantic Agnosticism

The system treats all signals identically:
- **Normalization**: Assumes [0, 1] range, no unit awareness
- **Color mapping**: Same LUT applied regardless of metric meaning
- **Visualization**: Identical ribbon representation, no metric-specific geometry

**Benefits**:
- **Extensibility**: Add ML models (e.g., AlphaFold confidence, ESM embeddings) without modifying visualization code
- **Comparison**: Switch between metrics to visually correlate patterns (high RMSF + high anomaly = flexible + rare = functionally interesting)

**Limitations**:
- **Semantic loss**: A value of 0.8 means "high" but loses physical units (e.g., 2.5 Å RMSF vs 0.8 normalized RMSF)
- **Workaround**: Store original units in JSON metadata (`"min": 0.0001, "max": 3.4567`), display in tooltips

---

## 5. Performance and Scalability

### 5.1 Performance-Aware Design Choices

#### Caching Strategies

| Cache | Scope | Invalidation | Benefit |
|-------|-------|-------------|---------|
| **LUT Cache** (Line 159) | Session-wide | Never | Avoids 256-entry interpolation per colormap switch (~0.5ms saved) |
| **CA Position Cache** (Line 333) | Per-frame | On frame change | Prevents redundant MDAnalysis reads for picking (~5ms per pick) |
| **MDAnalysis Offset Cache** (`.trajectory.xtc_offsets.npz`) | Disk-persisted | On trajectory change | Transforms O(n) sequential read to O(1) random access (~100-500ms saved per frame) |
| **Metric JSON In-Memory** (Line 66-70) | Application lifetime | Never | Eliminates disk I/O on metric switches (~10-50ms saved) |

#### Throttling

**Hover Event Throttling** (Line 1458):
```python
HOVER_THROTTLE_MS = 50  # 20 Hz max
current_time = time.time() * 1000
if current_time - _last_hover_time < HOVER_THROTTLE_MS:
    return  # Ignore event
```

**Rationale**: Mouse move events fire at 100+ Hz. Raycasting + tooltip updates at this rate would consume 30-50% CPU. Throttling to 20 Hz maintains responsiveness while reducing CPU load by 80%.

#### Partial Updates

**Scalar-Only Updates** (Lines 648-655):
```python
def update_ribbon_geometry(frame: int, metric: str):
    # ... fetch coordinates ...
    
    # Update scalars WITHOUT rebuilding geometry
    values = _metric_values(metric, frame)
    for idx in range(n_points):
        scalars.SetValue(idx, values[idx])
    scalars.Modified()  # Incremental update
```

When switching metrics (same frame), only scalar values change—geometry (points, splines, ribbon) remains identical. VTK's `Modified()` flag system propagates changes through the pipeline without full reconstruction, reducing update time from ~50ms to ~5ms.

### 5.2 Known Limitations

#### Trajectory Length

**Current Capacity**: 194 frames × 47 residues = 9,118 points  
**Memory Footprint**: 
- Trajectory in RAM: ~5 MB (MDAnalysis Universe)
- Metric JSONs: ~300 KB (4 metrics × 9,118 values × 8 bytes)
- VTK geometry: ~2 MB (10K vertices × 200 bytes/vertex overhead)

**Scaling Projections**:
- **1,000 frames**: 47K points, 15 MB total → **Feasible**
- **10,000 frames**: 470K points, 150 MB JSON + 50 MB VTK → **Marginal** (browser 2GB limit)
- **100,000 frames**: 4.7M points, 1.5 GB JSON → **Infeasible** without streaming

**Mitigation Strategy**:  
Implement **frame windowing**:
```python
visible_frames = range(state.current_frame - 50, state.current_frame + 50)
loaded_metrics = {f: fetch_from_disk(f) for f in visible_frames}
```

Load only 100-frame window around active frame, LRU cache for sliding window.

#### Large Molecular Systems

**Current Capacity**: 374 atoms → 47 C-alpha atoms  
**Full-Atom Trajectory**: 10,000 atoms → 5,000 C-alphas (typical protein)

**Scaling**:
- **100 residues**: 10K-15K ribbon vertices → **Smooth 60 FPS**
- **500 residues**: 50K-75K vertices → **30-40 FPS**, noticeable lag
- **2,000 residues** (e.g., ribosome): 200K-300K vertices → **<10 FPS**, unusable

**Mitigation**:
- **Level-of-Detail (LOD)**: Reduce spline subdivision density based on camera distance
- **Frustum culling**: Only render visible portions (requires spatial indexing)
- **GPU instancing**: For ball-and-stick mode, use instanced rendering (1 draw call for all spheres)

### 5.3 Tradeoffs: Responsiveness vs Fidelity

| Decision | Responsiveness | Fidelity | Rationale |
|----------|---------------|----------|-----------|
| **CA-only rendering** | ✅ 60 FPS | ❌ No side chains | 10x fewer points, maintain interactive frame rate |
| **Spline subdivision `SetLength(1.5)`** | ✅ Smooth | ❌ Not atomically precise | 1.5 Å steps balance smoothness vs vertex count |
| **Colormap 256 entries** | ✅ Fast LUT lookup | ❌ Visible banding in gradients | 8-bit color sufficient for scientific perception |
| **Eager JSON loading** | ✅ Instant metric switch | ❌ High memory for long trajectories | Prioritizes interactivity over memory efficiency |
| **Client-side rendering (vtklocal)** | ✅ Zero network latency | ❌ Limited to WebGL capabilities | Eliminates 100-300ms server round-trips |

---

## 6. Engineering Constraints and Tradeoffs

### 6.1 Consciously Made Design Decisions

#### Decoupling Visualization from ML

**Decision**: Consume JSON exports, never import ML libraries  
**Why**: 
- **Reproducibility**: JSON files are immutable records, enabling archival and sharing
- **Development velocity**: Visualization and ML teams work independently
- **Deployment simplicity**: Visualization server requires only Python + VTK, not PyTorch/TensorFlow/PyEMMA

**Limitation**: Prevents on-the-fly metric computation (e.g., "compute RMSF for residues 10-20 only")

#### WebAssembly Rendering (vtklocal)

**Decision**: Migrate from server-side VTK rendering to client-side WASM  
**Why**:
- **Latency**: Eliminates 100-300ms round-trip for every frame change
- **Scalability**: Server CPU load becomes O(1) per user (just state sync), not O(renders)
- **Reliability**: Picking and interaction work consistently across browsers

**Tradeoff**:
- **Download size**: 60 MB VTK.wasm initial download (one-time, cached)
- **Browser compatibility**: Requires WebAssembly support (Chrome 90+, Firefox 89+)

#### CA-Only Rendering

**Decision**: Filter to C-alpha atoms only, discard side chains  
**Why**:
- **Performance**: 10x reduction in point count (374 → 47 atoms)
- **Scientific relevance**: Backbone captures overall fold; ML metrics are per-residue, not per-atom

**Tradeoff**:
- **Loss of detail**: Cannot visualize side chain conformations, ligand binding pockets
- **Workaround**: Provide ball-and-stick mode for full-atom viewing (separate viewer)

### 6.2 Current Architecture Limitations

#### Lack of Lazy Loading

**Problem**: All metric JSONs load into RAM at startup  
**Impact**: 
- 194-frame trajectory: 300 KB → negligible
- 10,000-frame trajectory: 15 MB → acceptable
- 100,000-frame trajectory: 150 MB → problematic

**Redesign Needed**:
```python
class LazyMetricLoader:
    def __init__(self, path):
        self.path = path
        self._index = self._build_index()  # {frame: byte_offset}
    
    def get_frame(self, frame):
        if frame not in self._cache:
            self._cache[frame] = self._read_at_offset(self._index[frame])
        return self._cache[frame]
```

Store metrics in binary format (e.g., HDF5) with indexing for O(1) random access.

#### Single-Threaded Animation

**Problem**: Animation loop runs in main thread, blocking UI updates  
**Current Code** (Lines 1330-1372):
```python
def _start_animation_loop():
    while _animation_running:
        time.sleep(1.0 / state.animation_speed)
        state.current_frame = (state.current_frame + 1) % NUM_FRAMES
```

**Impact**: High-FPS animation (30+ FPS) starves Trame event loop, delaying button clicks

**Redesign**:
```python
async def _animation_loop():
    while _animation_running:
        await asyncio.sleep(1.0 / state.animation_speed)
        state.current_frame = (state.current_frame + 1) % NUM_FRAMES
```

Use `asyncio` instead of `threading` to yield control during sleep.

### 6.3 Scalability Bottlenecks for Production

#### Server-Side State Management

**Problem**: Each connected client maintains separate Trame state on server  
**Impact**: 100 concurrent users = 100 × 15 MB JSON = 1.5 GB RAM

**Production Redesign**:
- **Shared read-only cache**: Single JSON copy, all users reference same data
- **Stateless API**: Move to REST endpoints (`/api/metric/{metric}/{frame}`) instead of WebSocket state

#### Frontend Browser Limits

**Problem**: WebAssembly heap limited to 2-4 GB per browser tab  
**Impact**: Large trajectories (10K residues × 10K frames) exceed heap limit

**Production Redesign**:
- **Server-side rendering fallback**: Detect heap exhaustion, switch to image streaming
- **Progressive loading**: Render visible frames only, unload distant frames from WASM heap

---

## Conclusion

The ASVS molecular visualization system demonstrates a **carefully architected balance** between scientific rigor, interactive performance, and extensibility. By decoupling ML computation from visualization through file-based interfaces, the system achieves reproducibility and independent development velocity. The adoption of WebAssembly (vtklocal) for client-side rendering eliminates latency bottlenecks, enabling real-time frame scrubbing and metric switching critical for scientific validation.

However, the architecture's current limitations—eager JSON loading, CA-only rendering, and single-threaded animation—constrain scalability to microsecond-timescale trajectories and multi-user production deployments. Future iterations would require:

1. **Lazy metric loading** with HDF5 or similar indexed formats
2. **Level-of-detail rendering** for large molecular systems (500+ residues)
3. **Async animation loops** to prevent UI blocking
4. **Shared server-side caching** for multi-user scenarios

Despite these constraints, the system successfully operationalizes **visualization as validation**—exposing ML pipeline failures, trajectory artifacts, and indexing errors through spatial and temporal incoherence that numerical summaries would miss. This positions the visualizer not as a publication tool, but as a **critical instrument in the scientific method**, interrogating algorithmic outputs before they inform biological interpretation.

---

## References

**Code Files Analyzed:**
- `trame_ribbon_app.py` (2,099 lines): Main Trame application with VTK pipeline
- `trajectory_adapter.py` (565 lines): MDAnalysis wrapper for trajectory access
- `app.py` (343 lines): Flask REST API server
- `static/js/ribbon_viewer.js` (863 lines): Three.js ribbon renderer
- `static/js/ballstick_viewer.js` (1,705 lines): Three.js ball-and-stick renderer

**External Dependencies:**
- Trame 3.0+: Reactive web framework for scientific visualization
- VTK 9.2+: Visualization Toolkit for 3D rendering pipelines
- MDAnalysis 2.0+: Molecular dynamics trajectory analysis
- Three.js r148+: WebGL-based 3D graphics library
- Vuetify 2.x: Material Design component framework for Vue.js

**Related Documentation:**
- `ARCHITECTURE.md`: System overview and component descriptions
- `THESIS_VISUALIZATION_ANALYSIS.md`: Scientific validation philosophy
- `VTKLOCAL_MIGRATION.md`: WebAssembly migration technical details
- `ML_PIPELINE_INTEGRATION.md`: Integration with ensemble-anomaly-maps ML pipeline
