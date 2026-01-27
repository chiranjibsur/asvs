# Interactive Trame Ribbon Viewer with Dynamic Hotspots

## Overview

This enhanced version of the Trame ribbon viewer provides interactive visualization of protein structures with dynamic hotspot detection and analysis capabilities. It addresses the limitations of the previous static 3D visualization by adding:

- **Interactive residue selection** with visual feedback
- **Dynamic hotspot visualization** with color-coding and marker spheres
- **Measurement tools** for distance and angle calculations
- **Context-aware guidance** for hotspot analysis

## Features

### 1. Dynamic Hotspot Visualization

The viewer automatically loads hotspot data from `viewer/hotspots_residue.json` and visualizes it in two ways:

#### Color-Coded Ribbon
- **Blue**: Low hotspot regions (score < 0.15)
- **White**: Medium hotspot regions (score 0.15 - 0.25)
- **Red**: High hotspot regions (score > 0.25)

#### Marker Spheres
- **Orange translucent spheres** appear at high-hotspot residues (score > 0.25)
- Sphere color intensity increases with hotspot score
- Provides visual emphasis for regions of interest

### 2. Interactive Residue Selection

Click on any part of the ribbon to:
- Select the nearest residue
- Display a **yellow highlight sphere** at the selected position
- View detailed information in the side panel:
  - Residue name and number
  - Chain identifier
  - Hotspot score

### 3. Measurement Tools

The toolbar provides three measurement buttons:

#### Distance Measurement
1. Click the **Distance** button
2. Select two residues on the ribbon
3. View the calculated distance in Ångströms

#### Angle Measurement
1. Click the **Angle** button
2. Select three residues sequentially
3. View the calculated angle in degrees (at the middle residue)

#### Clear Measurement
- Click **Clear** to reset measurement mode

### 4. Guided Workflow

The status bar provides context-aware guidance:
- **High hotspot detected**: Suggests using measurement tools
- **Moderate hotspot**: Recommends analysis options
- **Low hotspot region**: Confirms selection
- **Measurement in progress**: Guides next step

## Usage

### Running the Viewer

```bash
python trame_ribbon.py
```

Then open your browser to: http://localhost:8787

### Keyboard and Mouse Controls

- **Left click**: Select residue
- **Left drag**: Rotate view
- **Right drag**: Pan view
- **Scroll**: Zoom in/out

### Workflow Examples

#### Finding High-Hotspot Residues
1. Look for red regions on the ribbon
2. Look for orange sphere markers
3. Click to select and view exact hotspot score

#### Analyzing Hotspot Regions
1. Click **Distance** button
2. Select two residues in a high-hotspot region
3. Review the distance to understand spatial proximity
4. Use **Angle** to analyze local geometry

#### Comparing Different Regions
1. Select a high-hotspot residue (orange sphere)
2. Note the score in the info panel
3. Select a low-hotspot residue (blue region)
4. Compare scores and structural context

## Technical Details

### VTK Pipeline

```
vtkPDBReader
    ↓
vtkProteinRibbonFilter (creates smooth ribbon geometry)
    ↓
Color mapping (based on hotspot data)
    ↓
vtkPolyDataMapper → vtkActor → vtkRenderer
```

### Hotspot Data Format

The viewer expects `viewer/hotspots_residue.json` with this structure:

```json
{
  "0": {  // Frame 0
    "0": 0.051,   // Residue 0 hotspot score
    "1": 0.107,   // Residue 1 hotspot score
    ...
  }
}
```

### Picking Algorithm

1. **Click event** provides screen coordinates (x, y)
2. **vtkCellPicker** performs 3D ray casting
3. **Nearest CA position** found using Euclidean distance
4. **Residue identified** if distance < 5 Å threshold

### Color Mapping Algorithm

For each point on the ribbon:
- Map point index to residue index (ribbon has ~10 points per residue)
- Lookup hotspot value for that residue
- Apply color gradient:
  - `value < 0.15`: Blue tones
  - `0.15 <= value <= 0.25`: White
  - `value > 0.25`: Red tones

## Integration with VTK ProteinRibbons Tutorial

This implementation follows best practices from the VTK ProteinRibbons example:

### From VTK Tutorial
- Uses `vtkPDBReader` for PDB file parsing
- Uses `vtkProteinRibbonFilter` for proper ribbon geometry
- Implements proper camera setup and lighting

### Enhancements Beyond Tutorial
- **Trame integration** for web-based interaction
- **Hotspot-based coloring** for scientific analysis
- **Interactive picking** with visual feedback
- **Measurement tools** for quantitative analysis
- **Guided workflow** for user assistance

## File Structure

```
trame_ribbon.py              # Main interactive viewer
test_interactive_ribbon.py   # Validation tests
viewer/
  hotspots_residue.json     # Hotspot data
  topology.pdb              # Protein structure
static/examples/
  1cbs.pdb                  # Example PDB file
```

## Requirements

- Python >= 3.6
- vtk >= 9.2.0
- trame >= 3.0.0
- trame-vuetify >= 2.3.0
- trame-vtklocal >= 0.6.0

Install with:
```bash
pip install vtk trame trame-vuetify trame-vtklocal
```

## Testing

Run the test suite to validate functionality:

```bash
python test_interactive_ribbon.py
```

Expected output:
```
✓ All 6 tests passed!
```

## Future Enhancements

### Planned Features
1. **Frame-by-frame animation** showing hotspot evolution
2. **Contact visualization** overlay on ribbon
3. **Secondary structure** coloring (helix/sheet/coil)
4. **Multi-residue selection** for region analysis
5. **Export capabilities** (images, measurements)

### Advanced Analysis
1. **Hotspot clustering** algorithm
2. **Correlation with RMSF** and other metrics
3. **Machine learning** hotspot prediction
4. **Time-series analysis** across trajectory frames

## Troubleshooting

### Issue: Clicking doesn't select residues
**Solution**: The picker uses a 5 Å threshold. Click closer to the ribbon backbone.

### Issue: No hotspot colors visible
**Solution**: Ensure `viewer/hotspots_residue.json` exists and contains frame "0" data.

### Issue: Orange spheres not appearing
**Solution**: Check if any residues have hotspot score > 0.25. Lower the threshold in code if needed.

### Issue: Measurements seem incorrect
**Solution**: Measurements are in Ångströms. Typical CA-CA distance is 3.8 Å.

## References

1. **VTK ProteinRibbons Tutorial**: https://examples.vtk.org/site/Cxx/Visualization/ProteinRibbons/
2. **Trame Documentation**: https://kitware.github.io/trame/
3. **Trame Micro-Workflow**: https://www.kitware.com/trame-micro-workflow-use-case/

## License

MIT License - See repository root for details.

## Authors

Developed as part of the ASVS (Automated Structure Visualization System) project.
