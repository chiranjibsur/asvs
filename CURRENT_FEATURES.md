# Current Features and Capabilities

**Last Updated:** November 11, 2025

## Overview

The Molecular Visualizer is a web-based platform for visualizing molecular dynamics (MD) trajectories and protein structures. It combines traditional PDB file visualization with advanced trajectory-based visualization and dynamic hotspot coloring capabilities.

## Current Implementation Status

### ✅ Fully Implemented Features

#### 1. **Three Visualization Modes**

The viewer offers three distinct rendering modes accessible via the navigation bar:

##### a) **Points Viewer** (`/viewer` or `/`)
- **Purpose**: Rapid visualization of trajectory frames using point cloud rendering
- **Technology**: Three.js point cloud rendering
- **Features**:
  - Fast rendering suitable for large molecular systems (374 atoms)
  - Real-time frame scrubbing with timeline slider
  - Play/pause animation controls with configurable FPS
  - Dynamic per-residue hotspot coloring
  - Blue → White → Red gradient mapping based on hotspot values
  - Interactive tooltips showing:
    - Residue name and number
    - Chain identifier
    - Hotspot value for current frame
    - Atom coordinates
  - Legend showing min/max hotspot values
  - Clickable atom information panel with detailed data
  - 194 frames of trajectory data available
  - **Advanced Features**:
    - **Show RMSF**: Display Root Mean Square Fluctuation data

##### b) **Ball-and-Stick Viewer** (`/viewer/ballstick`)
- **Purpose**: Traditional molecular representation with atoms as spheres and bonds as cylinders
- **Technology**: Three.js sphere + cylinder geometry
- **Features**:
  - Atomic spheres with element-based sizing using covalent radii
  - Automatic bond detection algorithm:
    - Uses covalent radii lookup table (H, C, N, O, F, P, S, Cl)
    - Distance-based heuristic: bond exists if distance < (r1 + r2) × 1.3
    - Minimum distance threshold: 0.4 Å
  - Dynamic hotspot coloring per atom
  - Frame animation support (194 frames)
  - Interactive picking and tooltips
  - Camera controls (rotate, zoom, pan)
  - Residue-level coloring mapped to atoms
  - **Advanced Features**:
    - **Show RMSF**: Display Root Mean Square Fluctuation data
    - **Show Contacts**: Visualize residue-residue contacts network
    - **Top Contacts**: Panel showing most frequent contacts
    - **Enable Clipping**: Clipping plane for cross-section views
    - **Measure Distance**: Interactive distance measurement tool
    - **Export**: Export options for visualization

##### c) **Ribbon Viewer** (`/viewer/ribbon`)
- **Purpose**: Protein backbone visualization for secondary structure emphasis
- **Technology**: Three.js CatmullRomCurve3 with tube geometry
- **Features**:
  - Smooth protein backbone visualization
  - Spline interpolation between C-alpha (CA) atoms
  - Falls back to backbone atoms if CA not found
  - Dynamic hotspot coloring along the ribbon
  - Frame animation support
  - Camera controls with OrbitControls
  - Continuous tube geometry for smooth appearance
  - **Advanced Features**:
    - **Show RMSF**: Display Root Mean Square Fluctuation data
    - **Enable Clipping**: Clipping plane for cross-section views
    - **Export PNG**: Export current view as PNG image

#### 2. **RESTful API Backend**

The Flask backend (`app.py`) provides comprehensive API endpoints:

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `/api/trajectory/meta` | Basic trajectory info | Frame count (194), atom count (374), residue count (374) |
| `/api/trajectory/frame/<frame>` | 3D coordinates | Array of [x, y, z] positions for all atoms |
| `/api/trajectory/residue_map` | Atom-to-residue mapping | Array mapping each atom to its residue number |
| `/api/trajectory/residue_meta` | Residue information | Table with index, resnum, resname, chain |
| `/api/trajectory/atoms` | Atom metadata | Element symbols, residue numbers, covalent radii |
| `/api/trajectory/ca/<frame>` | C-alpha positions | Coordinates for ribbon visualization |
| `/api/hotspots/<frame>` | Hotspot values | Per-residue hotspot values for coloring |
| `/api/rmsf` | RMSF data | Per-residue Root Mean Square Fluctuation |
| `/api/contacts` | Contact network | Residue-residue contact information |

#### 3. **Dynamic Hotspot Visualization**

- **Data Source**: `viewer/hotspots_residue.json`
- **Format**: Per-residue, per-frame hotspot values (0.0 to 1.0)
- **Color Mapping**:
  - 0.0 → Blue (#0b5cff) - Low hotspot
  - 0.5 → White (#ffffff) - Medium hotspot
  - 1.0 → Red (#ff2b2b) - High hotspot
- **Applications**:
  - Visualizing binding sites
  - Highlighting flexible regions
  - Showing computed properties (e.g., RMSF, contacts)

#### 4. **Trajectory Processing System**

- **Technology**: MDAnalysis library
- **Implementation**: Singleton pattern in `trajectory_adapter.py`
- **Capabilities**:
  - Lazy loading of trajectory data
  - Automatic element detection and normalization
  - Frame-based coordinate retrieval with clamping
  - Residue mapping and metadata extraction
  - C-alpha extraction for ribbon mode
  - Cached frame offsets for fast seeking (`.trajectory.xtc_offsets.npz`)

#### 5. **Interactive Controls**

All viewers feature:
- **Mouse Controls**:
  - Left-click + drag: Rotate view
  - Right-click + drag: Pan view
  - Scroll wheel: Zoom in/out
- **Timeline Controls**:
  - Play/Pause button
  - Frame slider for manual scrubbing
  - Frame counter display
  - Animation speed control (implied by slider)
- **Tooltips**:
  - Hover over atoms for instant information
  - Click for detailed atom/residue panel

#### 6. **Responsive Dark Theme UI**

- Modern dark theme (#0f1012 background)
- Clean, minimalist design
- Mode navigation bar with active state
- Metadata display panel
- Floating legend for color scale
- Semi-transparent panels with backdrop blur
- Mobile-responsive layout (viewport-based sizing)

#### 7. **Data Files Included**

The `viewer/` directory contains:
- `topology.pdb` - Molecular topology (374 atoms, auto-generated)
- `trajectory.xtc` - MD trajectory (194 frames, Gromacs XTC format)
- `hotspots_residue.json` - Per-residue hotspot values for each frame
- `hotspots.json` - Alternative hotspot data format
- `rmsf_residue.json` - Root Mean Square Fluctuation data
- `contacts.json` - Residue-residue contact network
- `.trajectory.xtc_offsets.npz` - MDAnalysis cache for fast frame access

### 🔧 Legacy Components (Still Present)

#### 1. **Legacy PDB Viewer** (`App.py` and `templates/index.html`)
- Original VTK-based visualization server
- Supports Ball-and-Stick and Protein Ribbon styles via VTK
- Multiple color mapping schemes:
  - CPK (element-based) coloring
  - B-factor (temperature) coloring
  - Residue-based coloring
- File upload capability for custom PDB files
- 2D projections (top/side views)
- Example file: `static/examples/1cbs.pdb`

#### 2. **Color Mapper Classes** (`colormappers/`)
- Strategy pattern implementation for different coloring schemes
- Base class (`base.py`): Abstract interface
- Atom Mapper (`atom.py`): CPK coloring
- B-factor Mapper (`bfactor.py`): Temperature factor coloring
- Residue Mapper (`residue.py`): Residue type-based coloring

#### 3. **VTK Visualizers** (`visualizers/`)
- Base class (`base.py`): Abstract visualizer interface
- Ball and Stick (`ball_and_stick.py`): VTK-based rendering
- Protein Ribbon (`protein_ribbon.py`): VTK-based ribbon

#### 4. **Utility Modules** (`utils/`)
- Molecule Data (`molecule_data.py`): PDB parsing
- Visualization (`visualization.py`): VTK rendering helpers

#### 5. **UI Components** (`ui/`)
- Drawer (`drawer.py`): Interactive control panel (Trame-based)
- Viewer (`viewer.py`): Trame-based viewer wrapper

## Technical Architecture

### Backend Stack
- **Flask** 2.0.1+ - Web framework and REST API
- **NumPy** 1.21.0+ - Numerical processing and array operations
- **MDAnalysis** - MD trajectory analysis and parsing
- **VTK** - Legacy visualization toolkit (for App.py)
- **Biopython** - PDB parsing (legacy components)

### Frontend Stack
- **Three.js** - WebGL-based 3D rendering engine
- **Vue.js** - UI framework (legacy PDB viewer)
- **Vuetify** - Material Design components (legacy)
- **OrbitControls** - Three.js camera control extension

### Data Flow

```
User Interaction → Flask Route → TrajectoryAdapter → MDAnalysis → 
  → NumPy Processing → JSON Response → JavaScript → Three.js → 
    → WebGL Rendering → Browser Canvas
```

### Design Patterns Used
1. **Singleton Pattern**: TrajectoryAdapter caches MDAnalysis Universe
2. **Strategy Pattern**: Color mappers implement different coloring strategies
3. **Adapter Pattern**: TrajectoryAdapter adapts MDAnalysis to REST API
4. **Factory Pattern**: Visualizer creation based on style selection

## Performance Optimizations

1. **Lazy Loading**: MDAnalysis Universe loaded once on server startup
2. **Client-side Caching**: Atom metadata fetched once and cached in browser
3. **Frame Offsets**: MDAnalysis caches frame positions for fast seeking
4. **Minimal Data Transfer**: Only coordinates sent per frame, not full atom data
5. **WebGL Acceleration**: Three.js leverages GPU for rendering
6. **Singleton Pattern**: Prevents redundant trajectory loading

## Data Specifications

### Coordinate System
- **Units**: Ångströms (Å)
- **Format**: Arrays of [x, y, z] floating-point values
- **Origin**: As defined in PDB/XTC files

### Indexing Conventions
- **Frames**: 0-indexed (0 to 193 in current data)
- **Atoms**: 0-indexed (0 to 373 in current data)
- **Residues (index)**: 0-indexed
- **Residues (resnum)**: 1-indexed (PDB numbering convention)

### Current Dataset
- **Frames**: 194
- **Atoms**: 374
- **Residues**: 374 (one atom per residue in current topology)
- **Trajectory Format**: Gromacs XTC (compressed)
- **Topology Format**: PDB

## Known Limitations

1. **Topology Quality**: Current `topology.pdb` is auto-generated with all atoms as CA (C-alpha), lacking proper atom types and bonds
2. **Memory Usage**: Full trajectory held in memory by MDAnalysis
3. **Bond Detection**: Distance-based heuristic may miss or add incorrect bonds
4. **Browser Requirements**: Requires WebGL-capable modern browser
5. **Performance**: May degrade with very large trajectories (>1000 atoms or >10000 frames)
6. **Element Detection**: Heuristic-based element detection may misidentify some atoms
7. **No Multi-chain Support**: Current implementation treats all atoms as single chain

## Usage Examples

### Starting the Viewer

**Windows:**
```bash
run.bat
```

**Mac/Linux:**
```bash
chmod +x run.sh
./run.sh
```

**Manual Start:**
```bash
pip install -e .
pip install MDAnalysis
python app.py
```

Then open http://localhost:5000 in your browser.

### Navigating Between Modes

- **Points Viewer**: Click "Points" in the navigation bar or visit http://localhost:5000/viewer
- **Ball-and-Stick**: Click "Ball-and-Stick" or visit http://localhost:5000/viewer/ballstick
- **Ribbon Viewer**: Click "Ribbon" or visit http://localhost:5000/viewer/ribbon

### Using Animation Controls

1. Click the **Play** button to start automatic frame progression
2. Use the **slider** to manually scrub through frames
3. **Hover** over atoms to see tooltips with residue information
4. **Click** on atoms to open detailed information panel
5. **Drag** with mouse to rotate, pan, or zoom the view

### API Usage Example

```javascript
// Fetch trajectory metadata
const meta = await fetch('/api/trajectory/meta').then(r => r.json());
console.log(`Frames: ${meta.n_frames}, Atoms: ${meta.n_atoms}`);

// Get coordinates for frame 0
const { xyz } = await fetch('/api/trajectory/frame/0').then(r => r.json());
console.log(`First atom position: ${xyz[0]}`);

// Get hotspot values for frame 0
const hotspots = await fetch('/api/hotspots/0').then(r => r.json());
console.log(`Hotspot for residue 0: ${hotspots[0]}`);
```

## Future Enhancement Opportunities

Based on the current implementation, potential areas for enhancement include:

1. **Topology Improvement**: Replace auto-generated topology with proper atom types and bonds
2. **Additional Rendering Modes**: Space-filling (van der Waals), wireframe, surface rendering
3. **Measurement Tools**: Distance, angle, and dihedral measurement capabilities
4. **Selection Tools**: Click-to-select atoms/residues, selection highlighting
5. **Export Features**: Screenshot capture, animation export, 3D model export
6. **Ligand Support**: Automatic ligand detection and highlighting
7. **Multiple Trajectory Support**: Load and compare multiple trajectories
8. **Server-side Caching**: Reduce memory usage with frame-level caching
9. **Advanced Coloring**: Support for custom color schemes, property-based coloring
10. **Performance Scaling**: Optimize for large systems (>10,000 atoms)

## Summary

The Molecular Visualizer is a fully functional, modern web-based platform for MD trajectory visualization with:
- ✅ Three distinct visualization modes (Points, Ball-and-Stick, Ribbon)
- ✅ Dynamic hotspot coloring system
- ✅ Interactive frame animation (194 frames)
- ✅ Comprehensive REST API
- ✅ Real-time tooltips and information panels
- ✅ Professional dark theme UI
- ✅ Responsive design for various screen sizes
- ✅ MDAnalysis-powered trajectory processing
- ✅ Three.js WebGL rendering for performance

The viewer successfully combines trajectory analysis capabilities with intuitive interactive visualization, making it suitable for research, education, and molecular dynamics analysis workflows.
