# Molecular Visualizer - System Architecture

## Overview

This project is a web-based molecular visualization platform that combines traditional PDB file visualization with advanced trajectory-based visualization and dynamic hotspot coloring capabilities.

## System Components

### 1. Backend (Flask Application)

#### Main Application (`app.py`)
- **Purpose**: Serves as the primary Flask server for trajectory-based visualization
- **Key Features**:
  - RESTful API endpoints for trajectory data
  - Dynamic hotspot visualization support
  - Multiple viewer modes (Points, Ball-and-Stick, Ribbon)
- **API Endpoints**:
  - `/api/trajectory/meta` - Metadata (frames, atoms, residues count)
  - `/api/trajectory/frame/<frame>` - 3D coordinates for specific frame
  - `/api/trajectory/residue_map` - Atom to residue mapping
  - `/api/trajectory/residue_meta` - Residue information table
  - `/api/trajectory/atoms` - Atom metadata with covalent radii
  - `/api/trajectory/ca/<frame>` - C-alpha positions for ribbon view
  - `/api/hotspots/<frame>` - Per-residue hotspot values
- **Routes**:
  - `/viewer` - Main hotspot viewer (points visualization)
  - `/viewer/ballstick` - Ball-and-stick molecular viewer
  - `/viewer/ribbon` - Protein ribbon viewer

#### Trajectory Adapter (`trajectory_adapter.py`)
- **Purpose**: Interfaces with MDAnalysis to load and process molecular dynamics trajectories
- **Data Sources** (in order of priority):
  1. Environment variables: `ASVS_PDB`, `ASVS_XTC`
  2. `viewer/topology.pdb` and `viewer/trajectory.xtc`
  3. `data/md/topology.pdb` and `data/md/trajectory.xtc`
- **Key Features**:
  - Lazy loading with singleton pattern
  - Residue mapping and metadata extraction
  - Frame-based coordinate retrieval
  - C-alpha extraction for ribbon visualization
  - Automatic element detection and normalization

#### Legacy Application (`App.py`)
- **Purpose**: Original PDB-only visualization server
- **Features**:
  - VTK-based visualization
  - Support for Ball-and-Stick and Protein Ribbon styles
  - Multiple color mapping schemes
  - File upload capability

### 2. Frontend

#### Visualization Modes

##### 1. Hotspot Viewer (`templates/hotspot_viewer.html`, JavaScript inline)
- **Technology**: Three.js point cloud rendering
- **Features**:
  - Dynamic per-residue hotspot coloring
  - Blue → White → Red gradient mapping
  - Real-time frame scrubbing
  - Play/pause animation controls
  - Interactive tooltips with residue information
  - Legend with min/max hotspot values

##### 2. Ball-and-Stick Viewer (`static/js/ballstick_viewer.js`)
- **Technology**: Three.js sphere + cylinder rendering
- **Features**:
  - Atomic spheres with element-based sizing
  - Automatic bond detection using covalent radii
  - Dynamic hotspot coloring per atom
  - Frame animation support
  - Interactive picking and tooltips

##### 3. Ribbon Viewer (`static/js/ribbon_viewer.js`)
- **Technology**: Three.js CatmullRomCurve3 with tube geometry
- **Features**:
  - Smooth protein backbone visualization
  - Spline interpolation between C-alpha atoms
  - Dynamic hotspot coloring along the ribbon
  - Camera controls and animation

##### 4. Legacy 3D Visualizer (`static/js/3d_visualizer.js`)
- **Technology**: Three.js with Vue.js/Vuetify UI
- **Features**:
  - Full-featured PDB visualization
  - Multiple rendering styles
  - Color mapping options (CPK, B-factor, Residue)
  - 2D projections (top/side views)
  - File upload and example loading

### 3. Supporting Modules

#### Color Mappers (`colormappers/`)
- **Base Class** (`base.py`): Abstract interface for color mapping strategies
- **Atom Mapper** (`atom.py`): CPK (element-based) coloring
- **B-factor Mapper** (`bfactor.py`): Temperature factor coloring
- **Residue Mapper** (`residue.py`): Residue type-based coloring

#### Visualizers (`visualizers/`)
- **Base Class** (`base.py`): Abstract visualizer interface
- **Ball and Stick** (`ball_and_stick.py`): VTK-based ball-and-stick rendering
- **Protein Ribbon** (`protein_ribbon.py`): VTK-based ribbon rendering

#### Utilities (`utils/`)
- **Molecule Data** (`molecule_data.py`): PDB parsing and data extraction
- **Visualization** (`visualization.py`): Helper functions for VTK rendering

#### UI Components (`ui/`)
- **Drawer** (`drawer.py`): Interactive control panel
- **Viewer** (`viewer.py`): Trame-based viewer wrapper

### 4. Data Files

#### Trajectory Data (`viewer/`)
- `topology.pdb` - Molecular topology (374 atoms, generated to match trajectory)
- `trajectory.xtc` - Molecular dynamics trajectory (194 frames, 374 atoms)
- `hotspots_residue.json` - Per-residue hotspot values for each frame
- `hotspots.json` - Alternative hotspot data format
- `.trajectory.xtc_offsets.npz` - MDAnalysis cache for fast frame access

#### Example Data (`static/examples/`)
- `1cbs.pdb` - Example protein structure (Cellular Retinoic Acid Binding Protein II)

## Data Flow

### Trajectory Visualization Flow
```
User Request → Flask Route → Trajectory Adapter → MDAnalysis → 
  → NumPy Processing → JSON Response → JavaScript Renderer → 
    → Three.js Visualization
```

### Hotspot Coloring Flow
```
Frame Selection → /api/hotspots/<frame> → hotspots_residue.json → 
  → Per-residue values → Atom mapping → Color interpolation → 
    → Visual update
```

## Technologies Used

### Backend
- **Flask** 2.0.1+ - Web framework
- **NumPy** 1.21.0+ - Numerical processing
- **MDAnalysis** - Molecular dynamics trajectory analysis
- **VTK** - Legacy visualization (Visualization Toolkit)
- **Biopython** - PDB parsing (legacy components)

### Frontend
- **Three.js** - WebGL-based 3D rendering
- **Vue.js** - UI framework (legacy viewer)
- **Vuetify** - Material Design components (legacy viewer)
- **OrbitControls** - Camera controls

## Key Design Patterns

1. **Singleton Pattern**: TrajectoryAdapter uses singleton to cache loaded Universe
2. **Strategy Pattern**: Color mappers implement different coloring strategies
3. **Adapter Pattern**: TrajectoryAdapter adapts MDAnalysis to REST API
4. **Factory Pattern**: Visualizer creation based on style selection

## Performance Optimizations

1. **Lazy Loading**: MDAnalysis Universe loaded once on server startup
2. **Client-side Caching**: Atom metadata fetched once and cached
3. **Frame Offsets**: MDAnalysis caches frame positions for fast seeking
4. **Minimal Data Transfer**: Only coordinates sent per frame, not full atom data
5. **WebGL Acceleration**: Three.js uses GPU for rendering

## Deployment

### Development
```bash
python app.py  # Starts on http://127.0.0.1:5000
```

### Docker
```bash
docker build -t molecular-visualizer .
docker run -p 5000:5000 molecular-visualizer
```

## Known Limitations

1. **Topology Generation**: Current topology.pdb is auto-generated with all atoms as CA (C-alpha), lacking proper atom types and bonds
2. **Memory Usage**: Full trajectory held in memory by MDAnalysis
3. **Bond Detection**: Distance-based heuristic may miss or add incorrect bonds
4. **Browser Support**: Requires WebGL-capable browser
5. **Large Files**: Performance degrades with very large trajectories

## Future Enhancements

- Proper topology file with correct atom types and residues
- Server-side frame caching to reduce memory usage
- Support for multiple trajectory formats
- Advanced rendering modes (space-filling, surface)
- Measurement tools (distances, angles)
- Export capabilities (images, videos, 3D models)
- Ligand highlighting and binding site visualization
