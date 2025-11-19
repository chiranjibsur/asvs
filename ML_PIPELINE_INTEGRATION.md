# ML Pipeline Integration Guide

## Overview

This molecular dynamics viewer integrates with the ensemble anomaly detection pipeline to visualize dynamic hotspots, anomaly scores, RMSF (flexibility), and tICA importance metrics.

## External ML Pipeline

The anomaly detection is provided by the separate ML pipeline:
**https://github.com/siya7205/ensemble-anomaly-maps**

This guide explains how to integrate the outputs from that pipeline into the visualization system.

## Data File Formats

### 1. Dynamic Anomaly Scores (`anomaly_residue.json`)

**Location**: `viewer/anomaly_residue.json`

**Format**: Per-residue anomaly scores for each frame
```json
{
  "description": "Dynamic anomaly scores per residue per frame from ensemble-anomaly-maps pipeline",
  "0": {
    "0": 0.0234,
    "1": 0.0512,
    "2": 0.0089,
    ...
  },
  "1": {
    "0": 0.0345,
    "1": 0.0623,
    ...
  },
  ...
}
```

**Key Points**:
- Frame indices are strings (e.g., "0", "1", "2")
- Residue indices are strings (0-based)
- Values should be normalized to [0, 1] range
- Higher values indicate more anomalous conformations

### 2. tICA Importance (`tica_importance.json`)

**Location**: `viewer/tica_importance.json`

**Format**: Per-residue importance scores (static, not frame-dependent)
```json
{
  "description": "tICA importance scores showing residue contribution to slow collective motions",
  "min": 0.0001234,
  "max": 0.8765432,
  "normalized": {
    "0": 0.0234,
    "1": 0.0512,
    "2": 0.0089,
    ...
  }
}
```

**Key Points**:
- Static metric (same for all frames)
- `min` and `max` are the original raw values before normalization
- `normalized` contains values in [0, 1] range
- Residue indices are strings (0-based)

### 3. RMSF Data (`rmsf_residue.json`)

**Location**: `viewer/rmsf_residue.json`

**Format**: Same as tICA importance
```json
{
  "min": 0.4527041036341996,
  "max": 8.684885185845564,
  "normalized": {
    "0": 0.0515,
    "1": 0.0418,
    ...
  }
}
```

**Note**: This file can be generated using the existing script:
```bash
python scripts/calculate_rmsf.py
```

## Integration Steps

### Option 1: Direct File Replacement

1. Run the ensemble-anomaly-maps pipeline on your trajectory
2. Export anomaly scores in the JSON format shown above
3. Replace `viewer/anomaly_residue.json` with your output
4. Similarly, generate and replace `viewer/tica_importance.json`
5. Restart the Flask server

### Option 2: Environment Variable Configuration

Set environment variables to point to your data files:

```bash
export ASVS_ANOMALY=/path/to/your/anomaly_residue.json
export ASVS_TICA=/path/to/your/tica_importance.json
export ASVS_RMSF=/path/to/your/rmsf_residue.json
export ASVS_HOTSPOTS=/path/to/your/hotspots_residue.json
```

Then start the server:
```bash
python app.py
```

### Option 3: Custom Data Converter

If your ML pipeline outputs data in a different format, create a converter script:

```python
#!/usr/bin/env python3
"""
Convert ML pipeline output to viewer format
"""
import json
import numpy as np

def convert_anomaly_scores(input_file, output_file):
    """
    Convert your pipeline's anomaly output to viewer format
    
    Args:
        input_file: Path to ML pipeline output
        output_file: Path to viewer/anomaly_residue.json
    """
    # Load your data
    with open(input_file, 'r') as f:
        ml_data = json.load(f)
    
    # Convert to viewer format
    viewer_data = {}
    for frame_idx, frame_data in ml_data.items():
        viewer_data[str(frame_idx)] = {
            str(res_idx): float(score)
            for res_idx, score in frame_data.items()
        }
    
    # Save
    with open(output_file, 'w') as f:
        json.dump(viewer_data, f, indent=2)

# Usage
convert_anomaly_scores(
    'ml_pipeline_output/anomaly.json',
    'viewer/anomaly_residue.json'
)
```

## API Endpoints

The viewer provides the following endpoints for accessing metrics:

### Get Anomaly Scores for Frame
```http
GET /api/metrics/anomaly/<frame>
```

**Response**:
```json
{
  "0": 0.1396,
  "1": 0.3385,
  "2": 0.3002,
  ...
}
```

### Get tICA Importance
```http
GET /api/metrics/tica_importance
```

**Response**:
```json
{
  "description": "tICA importance scores...",
  "min": 0.0001234,
  "max": 0.8765432,
  "normalized": {
    "0": 0.0234,
    ...
  }
}
```

### Get RMSF Data
```http
GET /api/rmsf
```

**Response**: Same format as tICA importance

## Viewer Usage

### Selecting Metrics

1. Open the viewer: http://localhost:5000/viewer
2. Use the **Metric** dropdown to select:
   - Dynamic Hotspot (default)
   - Dynamic Anomaly
   - RMSF (Flexibility)
   - tICA Importance

3. The visualization and legend update automatically

### Timeline Heatmap

- Shows metric trends across all frames
- Click on the heatmap to jump to a specific frame
- White vertical line indicates current frame

### Per-Residue Analysis

1. Click on any atom in the 3D visualization
2. The info panel shows all metrics for that residue:
   - Dynamic Hotspot score
   - Dynamic Anomaly score
   - RMSF value
   - tICA Importance value

### Playback Controls

- **Play**: Animate through frames
- **Pause**: Stop animation
- **Slider**: Manually scrub through frames
- Metrics update automatically during playback

## Troubleshooting

### Issue: "Anomaly data not found"

**Solution**: Ensure `viewer/anomaly_residue.json` exists or set `ASVS_ANOMALY` environment variable

### Issue: Metrics show all zeros

**Solution**: Check that:
1. JSON files have correct format
2. Residue indices match (0-based, as strings)
3. Values are normalized to [0, 1]

### Issue: Heatmap not updating

**Solution**: 
1. Check browser console for errors
2. Verify frame data exists for all frames in JSON
3. Clear browser cache and reload

### Issue: Wrong colors displayed

**Solution**: Verify values are in [0, 1] range. The color mapping is:
- 0.0 → Blue (low)
- 0.5 → White (medium)
- 1.0 → Red (high)

## Performance Considerations

### Large Trajectories

For trajectories with many frames (>1000):
1. Consider pre-computing and caching data
2. Use sparse frame sampling
3. Load data on-demand rather than all at once

### File Size

- Anomaly data: ~2KB per frame for 374 residues
- For 1000 frames: ~2MB total
- Use compression if needed (gzip JSON)

## Scientific Interpretation

### Dynamic Anomaly
- **Low values (0.0-0.3)**: Normal, expected conformations
- **Medium values (0.3-0.7)**: Unusual but not rare
- **High values (0.7-1.0)**: Rare, potentially important conformational changes

### RMSF (Flexibility)
- **Low values**: Rigid, stable regions (often α-helices, β-sheets)
- **High values**: Flexible regions (often loops, termini)

### tICA Importance
- **High values**: Residues critical for slow collective motions
- **Low values**: Residues that don't contribute significantly to dynamics

## Example Workflow

1. **Run MD Simulation**
   ```bash
   gmx mdrun -s system.tpr -deffnm md
   ```

2. **Run Ensemble Anomaly Pipeline**
   ```bash
   cd /path/to/ensemble-anomaly-maps
   python run_pipeline.py --trajectory md.xtc --topology system.pdb
   ```

3. **Convert and Copy Data**
   ```bash
   python convert_to_viewer_format.py
   cp output/anomaly_residue.json /path/to/asvs/viewer/
   cp output/tica_importance.json /path/to/asvs/viewer/
   ```

4. **Start Viewer**
   ```bash
   cd /path/to/asvs
   python app.py
   ```

5. **Visualize**
   - Open http://localhost:5000/viewer
   - Select "Dynamic Anomaly" metric
   - Explore anomalous frames and residues

## Sample Data

The repository includes synthetic sample data for demonstration:
- `viewer/anomaly_residue.json`: 194 frames, 374 residues
- `viewer/tica_importance.json`: 374 residues
- `viewer/rmsf_residue.json`: 374 residues

Replace these with your real ML pipeline outputs for production use.

## References

- Ensemble Anomaly Maps Pipeline: https://github.com/siya7205/ensemble-anomaly-maps
- MDAnalysis Documentation: https://www.mdanalysis.org/
- tICA Method: Time-lagged Independent Component Analysis
- RMSF Calculation: Root Mean Square Fluctuation

## Support

For issues related to:
- **ML Pipeline**: See https://github.com/siya7205/ensemble-anomaly-maps
- **Viewer Integration**: Open an issue in this repository
- **Data Format**: Refer to this documentation or example files
