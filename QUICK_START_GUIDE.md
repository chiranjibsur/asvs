# Quick Start Guide: Interactive Trame Ribbon Viewer

## Installation

```bash
# Install dependencies
pip install vtk trame trame-vuetify trame-vtklocal

# Navigate to project directory
cd /path/to/asvs

# Run the viewer
python trame_ribbon.py
```

## Opening the Viewer

1. Run: `python trame_ribbon.py`
2. Open browser to: `http://localhost:8787`
3. You should see the interactive ribbon viewer

## Understanding the Interface

```
┌──────────────────────────────────────────────────────────────┐
│  Interactive Trame Ribbon Viewer                             │
│  [Distance] [Angle] [Clear]                            [×]   │
├──────────────────────────────────────┬───────────────────────┤
│                                      │ Residue Information   │
│                                      │                       │
│         3D View                      │ Selected Residue:     │
│    (Protein Ribbon)                  │ ALA42 (Chain A)       │
│                                      │                       │
│    🔵 Blue = Low hotspot             │ Hotspot Score:        │
│    ⚪ White = Medium hotspot         │ 0.287                 │
│    🔴 Red = High hotspot             │                       │
│    🟠 Spheres = Critical sites       │ Measurement:          │
│                                      │ Distance: 12.5 Å      │
│                                      │                       │
│                                      │ Legend:               │
│                                      │ • Blue: < 0.15        │
│                                      │ • White: 0.15-0.25    │
│                                      │ • Red: > 0.25         │
│                                      │ • Orange: Critical    │
├──────────────────────────────────────┴───────────────────────┤
│ Status: High hotspot detected! Use measurement tools...      │
└──────────────────────────────────────────────────────────────┘
```

## Basic Interactions

### Mouse Controls (3D View)
- **Left drag**: Rotate view
- **Right drag**: Pan view
- **Scroll wheel**: Zoom in/out
- **Left click**: Select residue

### Visual Elements
- **Blue regions**: Low hotspot areas (score < 0.15)
- **White regions**: Medium hotspot areas (score 0.15-0.25)
- **Red regions**: High hotspot areas (score > 0.25)
- **Orange spheres**: Critical hotspot sites (score > 0.25)
- **Yellow sphere**: Currently selected residue

## Step-by-Step Tutorials

### Tutorial 1: Finding High-Hotspot Residues

**Goal**: Identify the most important residues in the protein

1. **Look for visual cues**:
   - Scan for red regions on the ribbon
   - Locate orange translucent spheres

2. **Select a hotspot**:
   - Click on an orange sphere or red region
   - Yellow highlight appears at the selected residue
   - Info panel updates with residue details

3. **Read the score**:
   - Check "Hotspot Score" in the right panel
   - High score (>0.25) indicates critical residue
   - Status bar provides guidance

**Example Output**:
```
Selected Residue: GLU38 (Chain A)
Hotspot Score: 0.313
Status: High hotspot detected! Use measurement tools to analyze...
```

### Tutorial 2: Measuring Distance Between Residues

**Goal**: Find the spatial separation between two residues

1. **Start measurement mode**:
   - Click the **[Distance]** button in toolbar
   - Status bar shows: "Select two residues to measure distance"

2. **Select first residue**:
   - Click on any part of the ribbon
   - Yellow sphere appears
   - Status bar shows: "Select second residue for distance"

3. **Select second residue**:
   - Click on another part of the ribbon
   - Distance appears in the info panel
   - Result shown in Ångströms (Å)

**Example Output**:
```
Measurement: Distance: 15.7 Å
Status: Distance measured: 15.7 Å
```

**Typical Values**:
- Adjacent residues: 3.8 Å (CA-CA distance)
- Same helix, 4 residues apart: ~6 Å
- Across protein: 20-50 Å

### Tutorial 3: Calculating Backbone Angles

**Goal**: Measure the angle formed by three consecutive residues

1. **Start angle mode**:
   - Click the **[Angle]** button in toolbar
   - Status bar shows: "Select three residues to measure angle"

2. **Select first residue**:
   - Click on the ribbon
   - Status: "Select residue 2 of 3 for angle"

3. **Select second residue (vertex)**:
   - Click the middle residue
   - This is the vertex of the angle
   - Status: "Select residue 3 of 3 for angle"

4. **Select third residue**:
   - Click the final residue
   - Angle appears in degrees
   - Measured at the second (middle) residue

**Example Output**:
```
Measurement: Angle: 125.3°
Status: Angle measured: 125.3°
```

**Typical Values**:
- Helix backbone: ~100-120°
- Sheet backbone: ~120-140°
- Turn/loop: Variable, 60-180°

### Tutorial 4: Comparing Different Regions

**Goal**: Understand hotspot distribution across the protein

1. **Select a high-hotspot residue**:
   - Click on an orange sphere
   - Note the score (e.g., 0.313)

2. **Select a low-hotspot residue**:
   - Click on a blue region
   - Note the lower score (e.g., 0.051)

3. **Measure the distance**:
   - Click **[Distance]**
   - Click both residues
   - See how far apart they are

4. **Analyze**:
   - Are high hotspots clustered?
   - Are they on one side of the protein?
   - What's the spatial distribution?

### Tutorial 5: Analyzing Local Geometry at Hotspots

**Goal**: Study the structural context of critical residues

1. **Find a high-hotspot orange sphere**
   
2. **Measure local angles**:
   - Click **[Angle]**
   - Select residue before hotspot
   - Select the hotspot residue (vertex)
   - Select residue after hotspot

3. **Interpret**:
   - Sharp angle (<90°): Tight turn
   - Medium angle (90-120°): Possible helix
   - Large angle (>140°): Extended structure

4. **Measure neighbor distances**:
   - Click **[Clear]** to reset
   - Click **[Distance]**
   - Measure to nearby residues
   - Check if it's in a compact or exposed region

## Workflow Recommendations

### For Structure Analysis
1. **Global scan**: Rotate view, identify red regions and orange spheres
2. **Selection**: Click highest-score orange sphere
3. **Context**: Use **[Distance]** to measure to other hotspots
4. **Geometry**: Use **[Angle]** to understand local structure

### For Comparative Analysis
1. Click multiple high-hotspot residues
2. Record their scores from the info panel
3. Measure distances between them
4. Determine if they form a cluster or are distributed

### For Quantitative Study
1. Systematically click each orange sphere
2. Record residue number and hotspot score
3. Measure distances to create distance matrix
4. Use measurements for further analysis

## Troubleshooting

### Issue: Can't select residues by clicking
**Solution**: 
- Click closer to the ribbon backbone
- Picker uses 5Å threshold
- Try clicking on a thicker part of the ribbon

### Issue: No orange spheres visible
**Solution**:
- Check if hotspot data is loaded (look for colors on ribbon)
- Threshold is 0.25 - only very high hotspots show spheres
- Try rotating view - spheres might be on back side

### Issue: Measurement result seems wrong
**Solution**:
- Distances are in Ångströms (Å), not nanometers
- Typical CA-CA distance is 3.8 Å
- Check you selected the intended residues (yellow sphere shows selection)

### Issue: Colors look wrong
**Solution**:
- Blue is LOW hotspot (good, stable)
- Red is HIGH hotspot (critical, important)
- This is inverted from typical "hot/cold" coloring

### Issue: Can't see the ribbon clearly
**Solution**:
- Use mouse scroll to zoom in
- Right-drag to pan to center the structure
- Try adjusting your browser window size

## Tips and Tricks

### Efficient Exploration
1. Start with a rotated view to see all orange spheres
2. Make a mental note of their positions
3. Systematically click each one
4. Use Clear button frequently to reset measurement mode

### Recording Measurements
1. Keep a notepad handy
2. Note: Residue number, hotspot score, measurements
3. Take screenshots (browser's screenshot feature)
4. Build your own analysis table

### Understanding Hotspot Patterns
- **Clusters**: Multiple orange spheres close together → functional site
- **Distributed**: Spheres spread out → multiple important regions
- **One-sided**: All on one face → binding interface
- **Interior**: Deep in structure → catalytic site

### Best Practices
1. **Start global**: Get overall picture before detailed analysis
2. **Use both tools**: Distance AND angle give complete picture
3. **Clear often**: Don't confuse old measurements with new ones
4. **Follow guidance**: Status bar messages help you know what to do next

## Keyboard Shortcuts

Currently none - all interactions via mouse clicking

## Data Format Notes

### Hotspot Scores
- **Range**: 0.0 to 1.0 (but typically 0.0 to 0.5)
- **Thresholds**: 
  - < 0.15 = Low (blue)
  - 0.15 - 0.25 = Medium (white)
  - > 0.25 = High (red + orange sphere)

### Measurement Units
- **Distance**: Ångströms (Å)
  - 1 Å = 0.1 nanometers
  - Protein CA-CA bond: ~3.8 Å
  
- **Angle**: Degrees (°)
  - 0° = Straight line (no angle)
  - 90° = Right angle
  - 180° = Straight line (opposite direction)

## Getting Help

1. **Status bar**: Always check for guidance messages
2. **Legend**: Right panel shows color scheme
3. **Documentation**: See INTERACTIVE_RIBBON_README.md
4. **Issues**: Report at GitHub repository

## Next Steps

After mastering the basic viewer:
1. Try analyzing different PDB structures
2. Compare hotspot patterns across frames (future feature)
3. Correlate with other metrics (RMSF, TICA, etc.)
4. Export measurements for statistical analysis

## Summary of Features

| Feature | How to Use | What You Get |
|---------|------------|--------------|
| **View rotation** | Left-drag | See structure from all angles |
| **Zoom** | Scroll wheel | Closer/farther view |
| **Select residue** | Left-click | Yellow highlight + info |
| **Measure distance** | [Distance] → click 2 | Distance in Å |
| **Measure angle** | [Angle] → click 3 | Angle in degrees |
| **Reset** | [Clear] | Clear measurement mode |
| **Hotspot ID** | Look for orange | Critical sites |
| **Score check** | Click → read panel | Quantitative value |

## Example Workflow

**Research Question**: "Which residues are most critical for protein function?"

1. **Launch viewer**: `python trame_ribbon.py`
2. **Visual scan**: Rotate to see all 13 orange spheres
3. **Systematic analysis**:
   - Click sphere 1 → Record: Residue 38, Score 0.313
   - Click sphere 2 → Record: Residue 42, Score 0.287
   - ...continue for all 13 spheres
4. **Spatial analysis**:
   - [Distance] → Click sphere 1 → Click sphere 2 → Record: 15.7 Å
   - Repeat for pairs
5. **Conclusion**: 
   - 13 critical residues identified
   - Hotspot scores: 0.25 - 0.31 range
   - Spatial distribution: Clustered in 3 regions
   - Further investigation recommended for residues 38, 42, 55

**Time required**: ~5-10 minutes for initial survey

## That's It!

You now know how to:
✅ Find critical residues visually  
✅ Select and view residue information  
✅ Measure distances quantitatively  
✅ Calculate backbone angles  
✅ Analyze hotspot patterns  

**Happy exploring!** 🧬🔬
