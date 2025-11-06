# Developer Guide

## Getting Started

### Prerequisites
- Python 3.6 or higher
- pip package manager
- Modern web browser with WebGL support
- (Optional) Docker for containerized deployment

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/chiranjibsur/asvs.git
   cd asvs
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
   # Or manually:
   pip install flask>=2.0.1 numpy>=1.21.0 MDAnalysis
   ```

3. **Verify installation**
   ```bash
   python -c "import flask, numpy, MDAnalysis; print('All dependencies installed!')"
   ```

### Running the Application

#### Quick Start (Windows)
```bash
run.bat
```

#### Quick Start (Mac/Linux)
```bash
chmod +x run.sh
./run.sh
```

#### Manual Start
```bash
python app.py
```

Then open http://localhost:5000 in your browser.

## Project Structure

```
asvs/
├── app.py                      # Main Flask server (trajectory viewer)
├── App.py                      # Legacy Flask server (PDB viewer)
├── trajectory_adapter.py       # MDAnalysis interface
├── setup.py                    # Package configuration
├── requirements.txt            # Python dependencies
│
├── templates/                  # HTML templates
│   ├── hotspot_viewer.html     # Main trajectory viewer
│   ├── ballstick_viewer.html   # Ball-and-stick viewer
│   ├── ribbon_viewer.html      # Ribbon viewer
│   └── index.html              # Legacy PDB viewer
│
├── static/                     # Static assets
│   ├── js/                     # JavaScript modules
│   │   ├── ballstick_viewer.js
│   │   ├── ribbon_viewer.js
│   │   ├── 3d_visualizer.js    # Legacy viewer
│   │   └── pdb_visualizer.js
│   ├── lib/                    # Third-party libraries
│   │   ├── three.min.js
│   │   ├── OrbitControls.js
│   │   ├── vue.min.js
│   │   └── vuetify.min.js
│   ├── css/                    # Stylesheets
│   └── examples/               # Example PDB files
│       └── 1cbs.pdb
│
├── viewer/                     # Trajectory data
│   ├── topology.pdb            # Molecular topology
│   ├── trajectory.xtc          # MD trajectory
│   └── hotspots_residue.json   # Hotspot data
│
├── visualizers/                # VTK visualizers (legacy)
│   ├── base.py
│   ├── ball_and_stick.py
│   └── protein_ribbon.py
│
├── colormappers/              # Color mapping strategies
│   ├── base.py
│   ├── atom.py                # CPK coloring
│   ├── bfactor.py             # B-factor coloring
│   └── residue.py             # Residue-based coloring
│
├── utils/                     # Utility functions
│   ├── molecule_data.py
│   └── visualization.py
│
└── ui/                        # UI components (legacy)
    ├── drawer.py
    └── viewer.py
```

## Development Workflow

### Adding New Visualization Modes

1. **Create JavaScript visualizer** in `static/js/`
   ```javascript
   // Example: my_visualizer.js
   (async function() {
     const meta = await fetch('/api/trajectory/meta').then(r => r.json());
     // Your visualization logic
   })();
   ```

2. **Create HTML template** in `templates/`
   ```html
   <!doctype html>
   <html>
     <head>
       <title>My Visualizer</title>
       <script src="/static/lib/three.min.js"></script>
     </head>
     <body>
       <canvas id="canvas"></canvas>
       <script src="/static/js/my_visualizer.js"></script>
     </body>
   </html>
   ```

3. **Add Flask route** in `app.py`
   ```python
   @app.route("/viewer/my-mode")
   def viewer_my_mode():
       return render_template("my_visualizer.html")
   ```

### Adding New API Endpoints

```python
@app.route("/api/my-endpoint/<int:param>")
def api_my_endpoint(param: int):
    # Your logic here
    data = adapter.get_some_data(param)
    return jsonify({"result": _to_serializable(data)})
```

### Adding New Color Mappers

1. **Create mapper class** in `colormappers/`
   ```python
   from .base import BaseColorMapper
   
   class MyColorMapper(BaseColorMapper):
       def apply_to_ball_and_stick(self, reader, renderer):
           # Implementation
           pass
       
       def apply_to_protein_ribbon(self, ribbon, renderer):
           # Implementation
           pass
   ```

2. **Register in** `colormappers/__init__.py`

## Testing

### Manual Testing
1. Start the server: `python app.py`
2. Navigate to http://localhost:5000
3. Test each viewer mode:
   - Points viewer: /viewer
   - Ball-and-stick: /viewer/ballstick
   - Ribbon: /viewer/ribbon
4. Verify frame animation works
5. Check hotspot coloring updates
6. Test tooltips and interactions

### API Testing
```python
from app import app

with app.test_client() as client:
    # Test meta endpoint
    response = client.get('/api/trajectory/meta')
    assert response.status_code == 200
    
    # Test frame endpoint
    response = client.get('/api/trajectory/frame/0')
    assert response.status_code == 200
    data = response.get_json()
    assert 'xyz' in data
```

## Common Development Tasks

### Adding New Example Files
1. Place PDB file in `static/examples/`
2. Update frontend to reference new file

### Customizing Hotspot Data
1. Edit `viewer/hotspots_residue.json`
2. Format: `{"frame_number": {"residue_number": hotspot_value}}`
3. Values should be 0.0 to 1.0 for best results

### Modifying Trajectory Data
1. Replace `viewer/topology.pdb` and `viewer/trajectory.xtc`
2. Ensure atom count matches between files
3. Restart server to reload data

### Changing Color Schemes
Edit the gradient in HTML templates:
```javascript
// In hotspot_viewer.html
const gradient = [
  [0, 0x0b5cff],    // Blue at 0
  [0.5, 0xffffff],  // White at 0.5
  [1, 0xff2b2b]     // Red at 1
];
```

## Debugging Tips

### Enable Flask Debug Mode
Already enabled in `app.py`:
```python
app.run(host="127.0.0.1", port=5000, debug=True)
```

### Check Console Logs
- **Browser Console**: F12 → Console tab
- **Server Console**: Terminal running `python app.py`

### Common Issues

1. **"Topology and trajectory don't match"**
   - Ensure `topology.pdb` has same atom count as `trajectory.xtc`
   - Check MDAnalysis can read both files

2. **"File not found" for trajectory**
   - Verify files exist in `viewer/` directory
   - Or set environment variables: `ASVS_PDB`, `ASVS_XTC`

3. **Blank visualization**
   - Check browser console for JavaScript errors
   - Verify API endpoints return data
   - Check Three.js loaded correctly

4. **Hotspots not showing**
   - Verify `viewer/hotspots_residue.json` exists
   - Check frame number exists in JSON
   - Ensure values are numeric

## Performance Optimization

### Client-Side
- Use `requestAnimationFrame` for smooth animations
- Implement frame caching for visited frames
- Use Three.js BufferGeometry for large molecules
- Debounce interactive controls

### Server-Side
- Keep adapter as singleton (already implemented)
- Use NumPy for vectorized operations
- Consider frame-level caching with TTL
- Enable gzip compression for JSON responses

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages
6. Submit a pull request

## Additional Resources

- [Three.js Documentation](https://threejs.org/docs/)
- [MDAnalysis User Guide](https://docs.mdanalysis.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [PDB File Format](https://www.wwpdb.org/documentation/file-format)
- [XTC Format (Gromacs)](https://manual.gromacs.org/current/reference-manual/file-formats.html#xtc)
