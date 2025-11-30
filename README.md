# Molecular Visualizer - 3D Interactive Structure Viewer

**Muskan Aneja's Capstone Project**

A web-based platform for interactive visualization of protein structures and molecular dynamics trajectories.

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Running the Application](#-running-the-application)
- [Viewer Modes](#-viewer-modes)
- [Usage Guide](#-usage-guide)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)
- [License](#-license)

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/chiranjibsur/asvs.git
cd asvs

# Install dependencies
pip install -e .

# Run the application
python app.py
```

Then open http://localhost:5000 in your browser.

---

## ✅ Prerequisites

Before you begin, ensure you have the following installed:

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.6 or higher | `python --version` or `python3 --version` |
| pip | Latest | `pip --version` |
| Modern Web Browser | Chrome, Firefox, Safari, or Edge with WebGL support | - |

### Optional (for advanced features):

| Requirement | Purpose |
|-------------|---------|
| [Docker](https://www.docker.com/get-started) | Containerized deployment |
| [MDAnalysis](https://www.mdanalysis.org/) | Molecular dynamics trajectory support |

---

## 📦 Installation

### Option 1: Quick Install (Recommended)

**Windows:**
```batch
run.bat
```

**Mac/Linux:**
```bash
chmod +x run.sh
./run.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Download example PDB file
- Start the application

### Option 2: Manual Install

1. **Clone the repository:**
   ```bash
   git clone https://github.com/chiranjibsur/asvs.git
   cd asvs
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # Activate on Windows:
   venv\Scripts\activate
   
   # Activate on Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   ```

   For trajectory viewer features, also install:
   ```bash
   pip install MDAnalysis
   ```

4. **Verify installation:**
   ```bash
   python -c "import flask, numpy; print('✓ Dependencies installed successfully!')"
   ```

### Option 3: Docker Install

```bash
# Build the image
docker build -t molecular-visualizer .

# Run the container
docker run -p 5000:5000 molecular-visualizer
```

---

## ▶️ Running the Application

Start the server:

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Restarting with stat
 * Debugger is active!
```

Open your browser and navigate to: **http://localhost:5000**

---

## 🔬 Viewer Modes

The application offers three visualization modes:

| Mode | URL | Description |
|------|-----|-------------|
| **Points Viewer** | `/viewer` | Lightweight point cloud visualization |
| **Ball-and-Stick** | `/viewer/ballstick` | Atoms as spheres, bonds as cylinders |
| **Ribbon Viewer** | `/viewer/ribbon` | Protein secondary structure visualization |

### Features by Mode:

- **Points Viewer:** RMSF display, frame animation
- **Ball-and-Stick:** RMSF, contacts network, top contacts, clipping planes, distance measurement, export
- **Ribbon Viewer:** RMSF, clipping planes, secondary structure coloring, export PNG

---

## 🖱️ Usage Guide

### Mouse Controls

| Action | Control |
|--------|---------|
| Rotate | Left-click + drag |
| Pan | Right-click + drag |
| Zoom | Scroll wheel |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause animation |
| `←` / `→` | Previous/Next frame |

### Working with Your Own Data

1. **PDB Files:** Place your `.pdb` file in `static/examples/` or use the upload feature
2. **Trajectory Data:** Place your `.pdb` and `.xtc` files in the `viewer/` directory

---

## ⚙️ Configuration

### Environment Variables

Configure custom data paths using environment variables:

```bash
# Trajectory files
export ASVS_PDB="/path/to/your/topology.pdb"
export ASVS_XTC="/path/to/your/trajectory.xtc"

# Metrics data
export ASVS_HOTSPOTS_RES="/path/to/hotspots_residue.json"
export ASVS_RMSF="/path/to/rmsf_residue.json"
export ASVS_CONTACTS="/path/to/contacts.json"
export ASVS_ANOMALY="/path/to/anomaly_residue.json"
export ASVS_TICA="/path/to/tica_importance.json"
```

### Default Data Locations

| File | Default Path | Description |
|------|--------------|-------------|
| Topology | `viewer/topology.pdb` | Molecular structure |
| Trajectory | `viewer/trajectory.xtc` | MD trajectory frames |
| Hotspots | `viewer/hotspots_residue.json` | Per-residue hotspot values |
| RMSF | `viewer/rmsf_residue.json` | Flexibility data |
| Contacts | `viewer/contacts.json` | Residue contact network |

---

## 🔧 Troubleshooting

### Common Issues

<details>
<summary><strong>❌ "Python is not installed or not in PATH"</strong></summary>

**Solution:** Install Python 3.6+ from https://python.org and ensure it's added to your system PATH.

```bash
# Verify installation
python --version  # Should show Python 3.6 or higher
```
</details>

<details>
<summary><strong>❌ "Port 5000 is already in use"</strong></summary>

**Solution:** Either stop the other application using port 5000, or run on a different port:

```bash
# Find what's using port 5000 (Mac/Linux)
lsof -i :5000

# Or run on a different port by editing app.py
# Change: app.run(host="127.0.0.1", port=5000)
# To:     app.run(host="127.0.0.1", port=5001)
```
</details>

<details>
<summary><strong>❌ "ModuleNotFoundError: No module named 'flask'"</strong></summary>

**Solution:** Install dependencies:

```bash
pip install -e .
# Or manually:
pip install flask numpy
```
</details>

<details>
<summary><strong>❌ "Trajectory files not found"</strong></summary>

**Solution:** Ensure the required files exist in the `viewer/` directory:

```bash
ls viewer/
# Should show: topology.pdb, trajectory.xtc, hotspots_residue.json
```

Or set environment variables to point to your files (see Configuration section).
</details>

<details>
<summary><strong>❌ Blank visualization / WebGL errors</strong></summary>

**Solution:** 
1. Use a modern browser (Chrome, Firefox, Safari, Edge)
2. Enable hardware acceleration in browser settings
3. Update your graphics drivers
4. Check browser console (F12) for JavaScript errors
</details>

### API Health Check

Test that the server is running correctly:

```bash
# Check trajectory metadata
curl http://localhost:5000/api/trajectory/meta

# Check RMSF data
curl http://localhost:5000/api/rmsf
```

---

## 📁 Project Structure

```
asvs/
├── app.py                  # Main Flask application
├── trajectory_adapter.py   # MDAnalysis interface
├── setup.py               # Package configuration
├── run.bat                # Windows launcher
├── run.sh                 # Mac/Linux launcher
├── Dockerfile             # Docker configuration
│
├── static/                # Static web assets
│   ├── js/               # JavaScript modules
│   ├── css/              # Stylesheets
│   ├── lib/              # Third-party libraries (Three.js, Vue.js)
│   └── examples/         # Example PDB files
│
├── templates/             # HTML templates
│   ├── hotspot_viewer.html
│   ├── ballstick_viewer.html
│   └── ribbon_viewer.html
│
├── viewer/                # Trajectory data
│   ├── topology.pdb      # Molecular structure
│   ├── trajectory.xtc    # MD trajectory
│   └── *.json            # Metrics data files
│
├── visualizers/           # VTK visualizers (legacy)
├── colormappers/          # Color mapping strategies
└── utils/                 # Utility functions
```

---

## 📚 Additional Documentation

- [Developer Guide](DEVELOPER_GUIDE.md) - For contributors and developers
- [API Documentation](API_DOCUMENTATION.md) - REST API reference
- [Current Features](CURRENT_FEATURES.md) - Detailed feature documentation
- [ML Pipeline Integration](ML_PIPELINE_INTEGRATION.md) - Machine learning data integration

---

## 📄 License

Open source for educational and research purposes.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📧 Support

For issues or questions:
1. Check the [Troubleshooting](#-troubleshooting) section
2. Search existing [GitHub Issues](https://github.com/chiranjibsur/asvs/issues)
3. Open a new issue if needed