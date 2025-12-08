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

## How to Run the Application

### Method 1: Using Python directly

#### Windows:
1. Make sure Python 3.6+ is installed
2. Double-click on `run.bat` or open a command prompt and run:
   ```
   run.bat
   ```
3. Open http://localhost:5000 in your browser

#### Mac/Linux:
1. Make sure Python 3.6+ is installed
2. Open a terminal and run:
   ```
   chmod +x run.sh
   ./run.sh
   ```
3. Open http://localhost:5000 in your browser

### Method 2: Using Docker

1. Make sure Docker is installed on your system
2. Build the Docker image:
   ```
   docker build -t molecular-visualizer .
   ```
3. Run the Docker container:
   ```
   docker run -p 5000:5000 molecular-visualizer
   ```
4. Open http://localhost:5000 in your browser

### Method 3: Using Python manually

1. Install the required dependencies:
   ```
   pip install -e .
   ```
2. Run the application:
   ```
   python app.py
   ```
3. Open http://localhost:5000 in your browser

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

## Recent Updates

### VTK.wasm + trame-vtklocal Migration (Latest)
The ribbon viewer has been migrated from server-side VTK rendering to client-side WebAssembly-powered rendering using trame-vtklocal. This provides:

- ✅ **Reliable Interactions**: Click-to-select now works consistently across all browsers
- ✅ **Instant Updates**: Metric switching updates colors immediately without lag
- ✅ **Working Measurement Tools**: Distance and angle measurements function reliably
- ✅ **Stable Animation**: Frame playback is smooth and consistent
- ✅ **True Interactivity**: All features work together seamlessly

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