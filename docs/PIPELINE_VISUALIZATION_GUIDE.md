# ML Pipeline to ASVS Visualization Guide

This guide explains how to run the **ensemble-anomaly-maps** ML pipeline and visualize the results using the **ASVS** (Animated Structure Visualization System) visualizer.

---

## Overview

The workflow consists of two main steps:
1. **Run the ML Pipeline** (`ensemble-anomaly-maps`) - Processes MD trajectories to compute hotspots, anomalies, RMSF, and tICA importance
2. **Visualize with ASVS** (`asvs`) - Displays the results in interactive 3D viewers (Ribbon, Ball-and-Stick)

---

## Prerequisites

### For the ML Pipeline (ensemble-anomaly-maps)
```bash
# Clone the ML pipeline
git clone https://github.com/siya7205/ensemble-anomaly-maps.git
cd ensemble-anomaly-maps

# Install dependencies
pip install -r requirements_metrics.txt
```

### For the Visualizer (ASVS)
```bash
# Clone the visualizer
git clone https://github.com/chiranjibsur/asvs.git
cd asvs

# Install dependencies
pip install -e .
# Or: pip install flask MDAnalysis numpy
```

---

## Step 1: Prepare Your Trajectory Data

Place your MD simulation files in the ML pipeline's data directory:

```bash
cd ensemble-anomaly-maps

# Create directory structure
mkdir -p data/raw_trajectory

# Copy your files:
# - topology.pdb or align_topol.pdb (structure with all atoms)
# - trajectory.xtc (or multiple trajectory_*.xtc files)
```

**Important:** Use a full-atom PDB file (with N, CA, C, O atoms) for proper ribbon visualization. CA-only topologies will work but with reconstructed backbone atoms.

---

## Step 2: Run the ML Pipeline

### Option A: Quick Pipeline (Recommended for Testing)
```bash
cd ensemble-anomaly-maps

# Generate features from trajectory
python tools/generate_features.py \
    --topology data/raw_trajectory/align_topol.pdb \
    --trajectory data/raw_trajectory/trajectory_0.xtc \
    --output data/features.npy

# Run tICA projection
python tools/run_tica.py \
    --features data/features.npy \
    --output data/tica/

# Generate hotspot scores
python tools/generate_hotspots.py \
    --features data/features.npy \
    --tica_dir data/tica/ \
    --output viewer/
```

### Option B: Full Pipeline with All Metrics (Recommended for Production)
```bash
cd ensemble-anomaly-maps

# Compute all three metric channels in one step
python tools/compute_all_metrics.py \
    --topology data/raw_trajectory/align_topol.pdb \
    --trajectory data/raw_trajectory/trajectory_0.xtc \
    --msm_dir outputs/msm \
    --output_dir outputs/metrics \
    --normalization percentile \
    --low-percentile 0.05 \
    --high-percentile 0.95
```

This generates:
- `outputs/metrics/hotspots_unified.json` - All metrics for viewer
- `outputs/metrics/residue_scores_dynamic.json` - Dynamic anomaly scores
- `outputs/metrics/residue_scores_rmsf.json` - RMSF/flexibility scores  
- `outputs/metrics/residue_scores_tica_importance.json` - tICA importance scores
- `outputs/metrics/hotspots_residue.json` - Legacy format for ASVS

---

## Step 3: Copy Output Files to ASVS Viewer

```bash
# From ensemble-anomaly-maps directory
# Copy to ASVS viewer directory

# Copy topology (use full-atom PDB for best results!)
cp data/raw_trajectory/align_topol.pdb ../asvs/viewer/topology.pdb

# Copy trajectory
cp data/raw_trajectory/trajectory_0.xtc ../asvs/viewer/trajectory.xtc

# Copy hotspot data
cp outputs/metrics/hotspots_residue.json ../asvs/viewer/hotspots_residue.json

# Copy RMSF data (optional but recommended)
cp outputs/metrics/residue_scores_rmsf.json ../asvs/viewer/rmsf_residue.json

# Copy tICA importance (optional)
cp outputs/metrics/residue_scores_tica_importance.json ../asvs/viewer/tica_importance.json
```

---

## Step 4: Run the ASVS Visualizer

```bash
cd asvs

# Run the Flask server
python app.py
```

Then open your browser to:
- **http://localhost:5000/** - Main hotspot viewer
- **http://localhost:5000/ribbon** - Ribbon visualization with secondary structure
- **http://localhost:5000/ballstick** - Ball-and-stick atomic view

---

## Visualizing Different Trajectories

### Method 1: Using Environment Variables

You can point ASVS to different data files using environment variables:

```bash
# Set paths to your specific trajectory
export ASVS_PDB="/path/to/your/topology.pdb"
export ASVS_XTC="/path/to/your/trajectory.xtc"
export ASVS_HOTSPOTS_RES="/path/to/your/hotspots_residue.json"
export ASVS_RMSF="/path/to/your/rmsf_residue.json"

# Run the visualizer
python app.py
```

### Method 2: Replacing Files in the Viewer Directory

Simply replace the files in the `viewer/` directory:

```bash
cd asvs/viewer/

# Replace with your new trajectory data
cp /path/to/new_topology.pdb topology.pdb
cp /path/to/new_trajectory.xtc trajectory.xtc
cp /path/to/new_hotspots.json hotspots_residue.json
```

### Method 3: Multiple Trajectory Comparison

To compare different trajectories, you can run multiple ASVS instances on different ports:

```bash
# Terminal 1: First trajectory
export ASVS_PDB="data/traj1/topology.pdb"
export ASVS_XTC="data/traj1/trajectory.xtc"
python app.py --port 5000

# Terminal 2: Second trajectory
export ASVS_PDB="data/traj2/topology.pdb"
export ASVS_XTC="data/traj2/trajectory.xtc"
python app.py --port 5001
```

---

## Understanding the Output Files

### From ML Pipeline:

| File | Description |
|------|-------------|
| `hotspots_residue.json` | Per-frame, per-residue hotspot scores (0-1) |
| `rmsf_residue.json` | Root Mean Square Fluctuation per residue |
| `tica_importance.json` | Contribution to slow collective motions |
| `anomaly_frame.json` | Per-frame anomaly detection scores |

### JSON Format Example:

```json
{
  "0": {"1": 0.12, "2": 0.34, "3": 0.56},
  "1": {"1": 0.15, "2": 0.38, "3": 0.52},
  ...
}
```
- Outer keys = frame numbers
- Inner keys = residue numbers  
- Values = normalized scores (0-1)

---

## Troubleshooting

### Issue: "Topology only has CA atoms"

**Solution:** Use the full-atom PDB from the ML pipeline's `data/raw_trajectory/align_topol.pdb` instead of a CA-only topology. The ASVS visualizer will automatically reconstruct backbone atoms if needed, but full-atom topologies provide better visualization.

### Issue: "Frame X not found"

**Solution:** Ensure the trajectory and hotspot JSON have matching frame counts:
```python
import json
import MDAnalysis as mda

# Check trajectory frames
u = mda.Universe("topology.pdb", "trajectory.xtc")
print(f"Trajectory frames: {len(u.trajectory)}")

# Check JSON frames
with open("hotspots_residue.json") as f:
    data = json.load(f)
print(f"JSON frames: {len(data)}")
```

### Issue: Colors all look the same (all blue or all red)

**Solution:** This is usually a normalization issue. Re-run the ML pipeline with percentile normalization:
```bash
python tools/compute_all_metrics.py \
    --normalization percentile \
    --low-percentile 0.05 \
    --high-percentile 0.95
```

---

## File Structure Reference

### ML Pipeline (ensemble-anomaly-maps)
```
ensemble-anomaly-maps/
├── data/
│   ├── raw_trajectory/
│   │   ├── align_topol.pdb      # Full-atom topology (use this!)
│   │   └── trajectory_*.xtc     # MD trajectories
│   └── features.npy             # Extracted features
├── outputs/
│   ├── metrics/
│   │   ├── hotspots_residue.json
│   │   ├── rmsf_residue.json
│   │   └── tica_importance.json
│   └── msm/                     # Markov State Model outputs
└── tools/
    ├── generate_features.py
    ├── run_tica.py
    ├── generate_hotspots.py
    └── compute_all_metrics.py
```

### ASVS Visualizer
```
asvs/
├── viewer/
│   ├── topology.pdb             # Copy from ML pipeline
│   ├── trajectory.xtc           # Copy from ML pipeline
│   ├── hotspots_residue.json    # Copy from ML pipeline
│   └── rmsf_residue.json        # Optional
├── app.py                       # Flask server
├── trajectory_adapter.py        # Data loading/processing
├── static/js/
│   ├── ribbon_viewer.js         # Ribbon visualization
│   ├── ballstick_viewer.js      # Ball-and-stick visualization
│   └── utils/spline.js          # Ribbon geometry utilities
└── templates/
    ├── ribbon_viewer.html
    └── ballstick_viewer.html
```

---

## Quick Reference Commands

```bash
# === ML Pipeline ===
# Full pipeline
cd ensemble-anomaly-maps
python tools/compute_all_metrics.py \
    --topology data/raw_trajectory/align_topol.pdb \
    --trajectory data/raw_trajectory/trajectory_0.xtc \
    --output_dir outputs/metrics

# === Copy to Visualizer ===
cp data/raw_trajectory/align_topol.pdb ../asvs/viewer/topology.pdb
cp data/raw_trajectory/trajectory_0.xtc ../asvs/viewer/trajectory.xtc
cp outputs/metrics/hotspots_residue.json ../asvs/viewer/

# === Run Visualizer ===
cd ../asvs
python app.py

# Open browser: http://localhost:5000
```

---

## Support

- **ML Pipeline Issues:** https://github.com/siya7205/ensemble-anomaly-maps/issues
- **Visualizer Issues:** https://github.com/chiranjibsur/asvs/issues
