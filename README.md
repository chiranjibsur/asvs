# Molecular Visualizer - 3D Interactive Structure Viewer

**Muskan Aneja's Capstone Project**

## Project Overview

Molecular Visualizer is an interactive web-based platform for visualizing protein structures from Protein Data Bank (PDB) files. This tool allows researchers, students, and molecular biology enthusiasts to explore molecular structures in both 2D and 3D representations with various visualization styles and color mapping options.

## Key Features

- **3D Interactive Visualization**: Rotate, zoom, and pan to explore molecular structures from any angle
- **WebAssembly-Powered Rendering**: Using VTK.wasm + trame-vtklocal for client-side rendering
  - Fast, responsive interactions with no server lag
  - Reliable click-to-select and picking
  - Instant metric switching and recoloring
  - Stable animation playback
- **Multiple Visualization Styles**: 
  - Ball and Stick model 
  - Protein Ribbon model with smooth tube geometry
- **Diverse Color Mapping Options**:
  - Element-based coloring (CPK coloring)
  - B-factor (temperature) coloring
  - Residue-based coloring
  - ML-based dynamic hotspot coloring
- **Interactive Features**:
  - Click-to-select residues with detailed info panels
  - Distance and angle measurement tools
  - Contact visualization between residues
  - Clipping planes for structure exploration
  - Frame-by-frame animation with playback controls
- **Interactive Atom Information**: Hover over atoms to view detailed information (element, residue, chain, B-factor, coordinates)
- **2D Projections**: Top view (X-Y plane) and side view (X-Z plane) for complementary visualization
- **File Upload**: Upload and visualize your own PDB files
- **Responsive Design**: Works on desktop and mobile devices

## Technologies Used

- **Backend**: Flask (Python) + Trame Framework
- **Frontend**: 
  - VTK.wasm for WebAssembly-powered 3D rendering
  - trame-vtklocal for client-side VTK visualization
  - Three.js for additional 3D rendering
  - Vue.js and Vuetify for UI components
  - HTML5 Canvas for 2D visualization
- **Data Processing**: 
  - MDAnalysis for trajectory handling
  - Custom PDB file parsing algorithms
  - VTK for molecular visualization pipelines
- **Containerization**: Docker for easy deployment

## System Requirements

### Prerequisites
- **Python**: 3.6 or higher (3.8+ recommended)
- **Operating System**: Windows, macOS, or Linux
- **RAM**: Minimum 4GB (8GB+ recommended for large structures)
- **Browser**: Modern browser with WebAssembly support
  - Chrome 90+
  - Firefox 89+
  - Safari 14+
  - Edge 90+

### Required Python Packages

The following packages are required for the ribbon viewer with VTK.wasm support:

```
flask>=2.0.1           # Web framework for classic viewer
numpy>=1.21.0          # Numerical computing
trame>=3.0.0           # Framework for interactive web applications
trame-vuetify>=2.3.0   # Vuetify UI components for Trame
trame-vtklocal>=0.6.0  # VTK.wasm client-side rendering (NEW)
vtk>=9.2.0             # Visualization Toolkit
wslink>=1.11.0         # WebSocket communication for Trame
```

**Note**: The `trame-vtklocal` package automatically downloads VTK.wasm files (~60MB) on first run. This is a one-time download.

### Optional Packages

For full functionality, you may also need:

```
MDAnalysis>=2.0.0      # For trajectory analysis (optional)
```

## Installation & Setup

### Quick Start (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/chiranjibsur/asvs.git
   cd asvs
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```
   
   This installs all required packages including the new VTK.wasm dependencies.

3. **Run the application**:
   
   **Option A - Flask app with all viewers**:
   ```bash
   python app.py
   ```
   Then navigate to:
   - Main page: http://localhost:5000
   - Ball-and-stick viewer: http://localhost:5000/viewer/ballstick
   - **Ribbon viewer**: http://localhost:5000/viewer/ribbon
   
   **Option B - Direct ribbon viewer**:
   ```bash
   python trame_ribbon_app.py
   ```
   Then open http://localhost:9887

### Manual Installation

If you prefer to install packages individually:

```bash
# System dependency for headless VTK rendering (Linux only)
# Ubuntu/Debian:
sudo apt-get install -y libosmesa6
# RHEL/CentOS/Fedora:
# sudo yum install mesa-libOSMesa
# Arch Linux:
# sudo pacman -S osmesa

# Core dependencies
pip install flask>=2.0.1 numpy>=1.21.0

# Trame + VTK dependencies (required for ribbon viewer)
pip install trame>=3.0.0 trame-vuetify>=2.3.0 trame-vtk>=2.0.0 vtk>=9.2.0 wslink>=1.11.0
```

### Installation on Specific Platforms

#### Windows
```cmd
# Using pip
pip install -e .

# Or using conda
conda create -n asvs python=3.9
conda activate asvs
pip install -e .
```

#### Mac/Linux
```bash
# Using pip
pip install -e .

# Or using conda
conda create -n asvs python=3.9
conda activate asvs
pip install -e .
```

### Docker Installation

1. Make sure Docker is installed on your system
2. Build the Docker image:
   ```bash
   docker build -t molecular-visualizer .
   ```
3. Run the Docker container:
   ```bash
   docker run -p 5000:5000 molecular-visualizer
   ```
4. Open http://localhost:5000 in your browser

### Verifying Installation

After installation, verify everything is working:

```bash
# Test imports
python -c "import trame; import trame_vtk; import vtk; print('All imports successful!')"

# Run the ribbon viewer
python trame_ribbon_app.py
```

On first run, the server starts immediately with no downloads required:
```
[Trame Ribbon] Starting server at http://127.0.0.1:9887

App running at:
 - Local:   http://localhost:9887/
```

## How to Use

### Ribbon Viewer (Trame-based)
1. Start the ribbon viewer: `python trame_ribbon_app.py`
2. Open http://localhost:9887 in your browser
3. Interactive features:
   - Click on residues to view detailed information
   - Use the "Metric" dropdown to switch between hotspot, anomaly, RMSF, and tICA coloring
   - Enable "Distance" or "Angle" tools to measure between residues
   - Enable "Contacts" to visualize residue-residue interactions
   - Use animation controls (play/pause/step) to explore trajectory frames
   - Enable "Clip" to use clipping planes for structure exploration

### Hover & Click Picking (Residue-Level Interaction)

The ribbon viewer supports interactive residue picking directly in the 3D view.

#### Hover Tooltip
- **Move your mouse** over any part of the ribbon to see a lightweight tooltip in the top-left of the view.
- The tooltip displays: **residue name + number**, **chain ID**, and the **hotspot score** for the currently selected frame.
- Example: `ALA42 (Chain A) · Hotspot: 0.347`
- The hotspot score updates automatically when you change frames using the slider or playback controls.

#### Click to Select
- **Left-click** on the ribbon to select a residue and persist the selection.
- The right-side **Residue Info** panel appears and shows:
  - Chain ID, residue name and number, residue index
  - All four ML metrics for the selected residue at the current frame:
    - **Dynamic Hotspot** – per-frame ML hotspot intensity
    - **Dynamic Anomaly** – rare-conformation anomaly score
    - **RMSF (Flexibility)** – frame-independent flexibility measure
    - **tICA Importance** – contribution to slow collective motions
- The selection persists across camera movement (pan / rotate / zoom).
- When you change frames, the displayed metric values automatically update to the new frame.

#### Hotspot Score Details
- The hotspot score is loaded from `viewer/hotspots_residue.json` (per-residue, per-frame data).
- For frames where hotspot data is sparse, the score is computed as a weighted aggregate:
  `hotspot ≈ anomaly × 0.4 + RMSF × 0.3 + tICA × 0.3`
- Values range from **0.0** (low importance) to **1.0** (high importance).
- The ribbon is colored accordingly using the selected colormap.

#### Clear Selection
- Click the **✕** button in the Residue Info card to deselect the current residue.
- Switching to a measurement mode (Distance / Angle) will also use subsequent clicks for measurements instead of selection.

#### Residue Search & Dropdown
- Use the **Search Residue** text field in the right panel to find residues by name (e.g., `ALA`) or number.
- Use the **Select Residue** dropdown to directly navigate to any residue by name/number.

#### Metric-Specific Colormaps
Each metric now has a dedicated colormap for clearer visual differentiation:
| Metric | Colormap | Low → High |
|--------|----------|------------|
| Hotspot | Red-White-Blue | Blue → White → Red |
| Anomaly | Purple → Orange | Dark purple → Orange-red |
| RMSF | Blue → Yellow | Dark blue → Pale yellow |
| tICA | Teal → Magenta | Dark teal → Dark magenta |

Switch colormaps manually using the **Colormap** dropdown in the toolbar.

### Classic Viewer (Flask-based)
1. Once the application is running, open http://localhost:5000 in your browser
2. Click "Load Example Structure" or upload your own PDB file
3. Use mouse controls to interact with the 3D view:
   - Left-click + drag: Rotate the molecule
   - Right-click + drag: Pan the view
   - Scroll wheel: Zoom in/out
4. Try different visualization styles and color mappings using the dropdown options
5. Hover over atoms to see detailed information
6. Click the fullscreen button for a more immersive experience

## Troubleshooting

### Common Issues

#### ImportError: No module named 'trame_vtklocal'
**Solution**: Install the package:
```bash
pip install trame-vtklocal>=0.6.0
```

#### WASM Download Fails
If the VTK.wasm download fails on first run:
1. Check your internet connection
2. The download URL is: https://gitlab.kitware.com/api/v4/projects/13/packages/generic/vtk-wasm32-emscripten/9.5.2/vtk-9.5.2-wasm32-emscripten.tar.gz
3. You can manually download and extract it to: `[python site-packages]/trame_vtklocal/module/serve/wasm/9.5.2/`

#### Click-to-select Not Working
1. Open browser console (F12)
2. Look for `[DEBUG]` messages showing event structure
3. Report the event format if issues persist

#### Animation Not Playing
- Make sure threading is enabled in your Python environment
- Check console for errors
- Verify frame data is loaded correctly

#### Port Already in Use
If port 9887 or 5000 is already in use:
```bash
# For ribbon viewer, specify a different port
python trame_ribbon_app.py --port 8888

# For Flask app
python app.py  # Modify app.py to change port if needed
```

#### Memory Issues with Large Structures
- Close other applications
- Increase available RAM
- Consider using a smaller subset of trajectory frames

### Getting Help

- Check the documentation files in the repository:
  - `VTKLOCAL_MIGRATION.md` - Technical migration details
  - `UI_INTERACTION_FIXES.md` - UI interaction troubleshooting
  - `VUETIFY_UI_ANALYSIS.md` - UI component analysis
- Open an issue on GitHub with:
  - Your Python version
  - Operating system
  - Full error message
  - Steps to reproduce

## Recent Updates

### VTK.wasm + trame-vtklocal Migration (Latest)
The ribbon viewer has been migrated from server-side VTK rendering to client-side WebAssembly-powered rendering using trame-vtklocal. This provides:

- ✅ **Reliable Interactions**: Click-to-select now works consistently across all browsers
- ✅ **Instant Updates**: Metric switching updates colors immediately without lag
- ✅ **Working Measurement Tools**: Distance and angle measurements function reliably
- ✅ **Stable Animation**: Frame playback is smooth and consistent (30-60 FPS)
- ✅ **True Interactivity**: All features work together seamlessly
- ✅ **Performance**: 5-10x faster interactions, zero server round-trips

**Key Changes**:
- Threading-based animation loop for reliability
- Enhanced event handling for trame-vtklocal
- Comprehensive tooltips for all UI controls
- Debug logging for troubleshooting

See [VTKLOCAL_MIGRATION.md](VTKLOCAL_MIGRATION.md) for technical details.

## Future Enhancements

- Support for more visualization styles (Space-filling, Wireframe)
- Molecular surface visualization
- Ligand highlighting
- Export options for images and 3D models

## License

Open source for educational and research purposes.

## Project Structure

```
/ (root)
├── static/                  # Static assets
│   ├── css/                 # CSS stylesheets
│   ├── js/                  # JavaScript files
│   │   ├── 3d_visualizer.js # Three.js based 3D visualization
│   │   └── simple_visualizer.js # 2D canvas visualization
│   ├── lib/                 # Third-party libraries
│   └── examples/            # Example PDB files
├── templates/               # HTML templates
│   └── index.html           # Main application page
├── app.py                   # Flask application
├── setup.py                 # Package setup and dependencies
├── run.bat                  # Windows run script
├── run.sh                   # Mac/Linux run script
└── Dockerfile               # Docker configuration file
```