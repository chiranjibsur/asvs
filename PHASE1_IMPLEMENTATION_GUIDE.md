# Phase 1 Implementation Guide: Atom Selection & Info Panel

This guide provides step-by-step instructions for implementing Phase 1 of the interactive molecular visualization features.

## Overview

**Phase 1 Goals:**
- Add basic atom selection using Three.js raycasting
- Create an info panel showing atom/residue details on click
- Test with existing topology.pdb data
- **Timeline:** 1-2 weeks

## Prerequisites

Before starting, ensure:
- This documentation PR is merged into `siya-integration`
- You have basic knowledge of JavaScript, Three.js, and Flask
- Development environment is set up (see DEVELOPER_GUIDE.md)

## Implementation Steps

### Step 1: Set Up New Branch

```bash
# Switch to siya-integration and update
git checkout siya-integration
git pull origin siya-integration

# Create new feature branch
git checkout -b feature/atom-selection-phase1
```

### Step 2: Modify Ball-and-Stick Viewer JavaScript

**File to edit:** `static/js/ballstick_viewer.js`

#### 2.1 Add Raycaster for Atom Selection

Add after the scene setup (around line 40):

```javascript
// Raycaster for mouse picking
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let selectedAtom = null;

// Helper to get mouse position in normalized device coordinates
function onMouseMove(event) {
  const rect = canvas.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
}

canvas.addEventListener('mousemove', onMouseMove, false);
```

#### 2.2 Add Click Handler for Atom Selection

Add after the raycaster setup:

```javascript
function onAtomClick(event) {
  // Update raycaster
  raycaster.setFromCamera(mouse, camera);
  
  // Check for intersections with atom spheres
  const intersects = raycaster.intersectObjects(scene.children, true);
  
  if (intersects.length > 0) {
    const clickedObject = intersects[0].object;
    
    // Find the atom index from the object's userData
    if (clickedObject.userData && clickedObject.userData.atomIndex !== undefined) {
      const atomIndex = clickedObject.userData.atomIndex;
      selectAtom(atomIndex);
    }
  } else {
    // Clicked on empty space - deselect
    deselectAtom();
  }
}

canvas.addEventListener('click', onAtomClick, false);
```

#### 2.3 Add Selection Logic

```javascript
function selectAtom(atomIndex) {
  // Store selected atom
  selectedAtom = atomIndex;
  
  // Highlight the selected atom
  highlightAtom(atomIndex);
  
  // Fetch and display atom details
  displayAtomInfo(atomIndex);
}

function deselectAtom() {
  if (selectedAtom !== null) {
    unhighlightAtom(selectedAtom);
    selectedAtom = null;
    hideAtomInfo();
  }
}

function highlightAtom(atomIndex) {
  // Find the atom sphere in the scene
  scene.children.forEach(child => {
    if (child.userData && child.userData.atomIndex === atomIndex) {
      // Save original material
      if (!child.userData.originalMaterial) {
        child.userData.originalMaterial = child.material.clone();
      }
      // Apply highlight material
      child.material = new THREE.MeshPhongMaterial({
        color: 0xffff00,  // Yellow highlight
        emissive: 0x444400,
        shininess: 100
      });
    }
  });
}

function unhighlightAtom(atomIndex) {
  scene.children.forEach(child => {
    if (child.userData && child.userData.atomIndex === atomIndex) {
      if (child.userData.originalMaterial) {
        child.material = child.userData.originalMaterial;
      }
    }
  });
}
```

#### 2.4 Add Atom Data Display Function

```javascript
async function displayAtomInfo(atomIndex) {
  // Get atom metadata
  const atom = atoms[atomIndex];
  const residueNum = atom.resnum;
  
  // Fetch residue metadata
  const residueMeta = await fetch('/api/trajectory/residue_meta').then(r => r.json());
  const residue = residueMeta.residues.find(r => r.resnum === residueNum);
  
  // Get current frame coordinates
  const frameData = await fetch(`/api/trajectory/frame/${currentFrame}`).then(r => r.json());
  const coords = frameData.xyz[atomIndex];
  
  // Fetch hotspot data for this residue
  const hotspotData = await fetch(`/api/hotspots/${currentFrame}`).then(r => r.json());
  const hotspotValue = hotspotData[residue.index] || 0;
  
  // Build info HTML
  const infoHTML = `
    <div class="atom-info-panel">
      <h3>Atom Information</h3>
      <div class="info-section">
        <strong>Atom:</strong> ${atom.element} (Index: ${atomIndex})
      </div>
      <div class="info-section">
        <strong>Residue:</strong> ${residue.resname}${residue.resnum} (Chain ${residue.chain})
      </div>
      <div class="info-section">
        <strong>Coordinates:</strong><br>
        X: ${coords[0].toFixed(2)} Å<br>
        Y: ${coords[1].toFixed(2)} Å<br>
        Z: ${coords[2].toFixed(2)} Å
      </div>
      <div class="info-section">
        <strong>Hotspot Score:</strong> ${hotspotValue.toFixed(3)}
      </div>
      <button onclick="deselectAtom()" class="close-btn">Close</button>
    </div>
  `;
  
  // Display the panel
  document.getElementById('infoPanel').innerHTML = infoHTML;
  document.getElementById('infoPanel').style.display = 'block';
}

function hideAtomInfo() {
  document.getElementById('infoPanel').style.display = 'none';
}
```

### Step 3: Modify Ball-and-Stick HTML Template

**File to edit:** `templates/ballstick_viewer.html`

#### 3.1 Add Info Panel Container

Add before the closing `</body>` tag:

```html
<!-- Atom Info Panel -->
<div id="infoPanel" style="
  position: absolute;
  top: 80px;
  right: 20px;
  width: 300px;
  background: rgba(26, 28, 34, 0.95);
  border: 1px solid #2b2f3a;
  border-radius: 10px;
  padding: 16px;
  display: none;
  z-index: 100;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
">
</div>

<style>
.atom-info-panel h3 {
  margin: 0 0 12px 0;
  color: #e9eaee;
  font-size: 16px;
  font-weight: 600;
}

.info-section {
  margin-bottom: 10px;
  color: #b9beca;
  font-size: 13px;
  line-height: 1.5;
}

.info-section strong {
  color: #e9eaee;
}

.close-btn {
  width: 100%;
  padding: 8px;
  margin-top: 8px;
  background: #263043;
  color: #fff;
  border: 1px solid #2b2f3a;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.close-btn:hover {
  background: #2d3a4f;
}
</style>
```

### Step 4: Update Atom Rendering to Include userData

In the atom rendering section of `ballstick_viewer.js`, modify the sphere creation to include atom index:

```javascript
// When creating atom spheres
const atomSphere = new THREE.Mesh(sphereGeometry, atomMaterial);
atomSphere.position.set(x, y, z);

// Add atom index to userData for raycasting
atomSphere.userData.atomIndex = i;
atomSphere.userData.element = atoms[i].element;
atomSphere.userData.resnum = atoms[i].resnum;

scene.add(atomSphere);
```

### Step 5: Add Backend API Enhancement (Optional)

**File to edit:** `app.py`

Add a new endpoint for detailed atom information:

```python
@app.route("/api/atom/<int:atom_id>")
def api_atom_details(atom_id: int):
    """
    Returns detailed information about a specific atom.
    """
    atom_data = adapter.get_atom_table()
    atoms = atom_data['atoms']
    
    if atom_id < 0 or atom_id >= len(atoms):
        return jsonify({"error": "Invalid atom ID"}), 404
    
    atom = atoms[atom_id]
    
    # Get residue information
    residue_table = adapter.get_residue_table()
    residue = next((r for r in residue_table if r['resnum'] == atom['resnum']), None)
    
    return jsonify({
        "atom": atom,
        "residue": residue
    })
```

### Step 6: Testing

#### 6.1 How to Check if Phase 1 Works

**Starting the Application:**

1. **Install Dependencies (if not already done):**
   ```bash
   pip install -e .
   ```

2. **Start the Flask Server:**
   ```bash
   python app.py
   ```
   
   The server should start on http://127.0.0.1:5000
   
   You should see output like:
   ```
   * Running on http://127.0.0.1:5000
   * Restarting with stat
   ```

3. **Open Your Web Browser:**
   - Navigate to http://localhost:5000/viewer/ballstick
   - Or http://localhost:5000/viewer/ribbon for the ribbon viewer
   - Or http://localhost:5000/viewer for the hotspot (points) viewer

#### 6.2 Testing Ball-and-Stick Viewer

Navigate to http://localhost:5000/viewer/ballstick

- [ ] **Page loads successfully** - You should see a 3D molecular structure
- [ ] **Load a frame** - Click "Load frame" button, atoms should appear
- [ ] **Click on an atom** - Click directly on any sphere (atom)
  - Info panel should appear on the right side of the screen
  - Selected atom should turn yellow
  - Panel should show:
    - Atom element and index
    - Residue name, number, and chain
    - X, Y, Z coordinates
    - Hotspot score
- [ ] **Close the info panel** - Click the "Close" button
  - Panel should disappear
  - Yellow highlight should be removed
- [ ] **Click on empty space** - Click on the black background
  - Any selection should be cleared
  - Info panel should close
- [ ] **Select different atoms** - Click on multiple atoms
  - Panel should update with new atom's information
  - Only one atom should be highlighted at a time
- [ ] **Test with animation** - Click "Play" button
  - Animation should work smoothly
  - You can click atoms during animation
- [ ] **Check browser console** - Press F12 to open developer tools
  - Should be no JavaScript errors

#### 6.3 Testing Ribbon Viewer

Navigate to http://localhost:5000/viewer/ribbon

- [ ] **Page loads successfully** - You should see a ribbon/tube structure
- [ ] **Click on the ribbon** - Click anywhere on the colored tube
  - Info panel should appear
  - Panel should show residue information for the closest C-alpha atom
  - Should display:
    - Residue name, number, and chain
    - Residue index
    - C-alpha coordinates
    - Hotspot score
- [ ] **Close the info panel** - Click the "Close" button
  - Panel should disappear
- [ ] **Click on empty space** - Selection should clear
- [ ] **Click different parts of the ribbon** - Info should update
- [ ] **Test with frame slider** - Move the slider
  - Ribbon should update to new frame
  - Click interactions should still work
- [ ] **Check browser console** - Should be no errors

#### 6.4 Testing Hotspot (Points) Viewer

Navigate to http://localhost:5000/viewer

- [ ] **Page loads successfully** - You should see colored points
- [ ] **Load frame 0** - Click "Load frame 0" button
- [ ] **Click on a point** - Click directly on any colored point
  - Info panel should appear
  - Panel should show:
    - Atom index
    - Residue information (if available)
    - X, Y, Z coordinates
    - Hotspot score
- [ ] **Close the info panel** - Click the "Close" button
- [ ] **Click on empty space** - Selection should clear
- [ ] **Click different points** - Info should update
- [ ] **Test animation** - Click "Play" button
  - Animation should work
  - Click interactions should work during playback
- [ ] **Check browser console** - Should be no errors

#### 6.5 Common Issues and Solutions

**Issue: Clicking atoms does nothing**
- **Solution:** Ensure the JavaScript files are loaded correctly. Check browser console (F12) for errors.
- Verify that `ballstick_viewer.js`, `ribbon_viewer.js`, or `simple_visualizer.js` are loaded without errors.

**Issue: Info panel doesn't appear**
- **Solution:** Check that the `infoPanel` div exists in the HTML template.
- Verify API endpoints are responding: try opening http://localhost:5000/api/trajectory/meta in your browser.

**Issue: Wrong atom/residue selected**
- **Solution:** This can happen with overlapping atoms. Try zooming in and clicking more precisely.
- In the hotspot viewer, points may be small - try adjusting the raycaster threshold.

**Issue: Server won't start**
- **Solution:** Check that all dependencies are installed: `pip install -e .`
- Verify that `viewer/topology.pdb` and `viewer/trajectory.xtc` files exist.
- Check that port 5000 is not already in use.

**Issue: "Failed to fetch" errors in console**
- **Solution:** Ensure the Flask server is running.
- Check that the API endpoints exist in `app.py`.
- Verify data files exist in the `viewer/` directory.

#### 6.6 Manual Testing Checklist

Complete testing across all three viewers:

#### 6.6 Manual Testing Checklist

Complete testing across all three viewers:

**Ball-and-Stick Viewer:**
- [ ] Start the Flask server: `python app.py`
- [ ] Navigate to http://localhost:5000/viewer/ballstick
- [ ] Load a frame and verify atoms are visible
- [ ] Click on an atom - info panel should appear
- [ ] Verify the selected atom is highlighted in yellow
- [ ] Check that atom details are correct (element, residue, coordinates)
- [ ] Click on empty space - selection should clear
- [ ] Click on different atoms - panel should update
- [ ] Test with different frames using the slider

**Ribbon Viewer:**
- [ ] Navigate to http://localhost:5000/viewer/ribbon
- [ ] Verify ribbon structure is visible
- [ ] Click on the ribbon - info panel should appear with residue info
- [ ] Click on empty space - selection should clear
- [ ] Test with frame slider
- [ ] Verify coordinates and hotspot scores are displayed correctly

**Hotspot (Points) Viewer:**
- [ ] Navigate to http://localhost:5000/viewer
- [ ] Click "Load frame 0" to load points
- [ ] Click on a point - info panel should appear
- [ ] Verify atom/residue information is displayed
- [ ] Click on empty space - selection should clear
- [ ] Test with animation (Play button)

#### 6.7 Browser Console Testing

Open browser console (F12) and test:

```javascript
// Should log the selected atom index when clicking
console.log('Selected atom:', selectedAtom);
```

### Step 7: Commit and Push

```bash
# Add changes
git add static/js/ballstick_viewer.js
git add templates/ballstick_viewer.html
git add app.py  # if you added the API endpoint

# Commit
git commit -m "Add Phase 1: Atom selection with info panel

- Implement Three.js raycasting for atom selection
- Add click handler to select/deselect atoms
- Create info panel showing atom/residue details
- Highlight selected atoms in yellow
- Display coordinates, residue info, and hotspot scores"

# Push to remote
git push origin feature/atom-selection-phase1
```

### Step 8: Create Pull Request

1. Go to GitHub repository
2. Click "Compare & pull request" for your new branch
3. Set base branch to `siya-integration`
4. Title: "Phase 1: Add atom selection and info panel"
5. Description: Use the template below

```markdown
## Phase 1: Atom Selection & Info Panel

Implements basic interactive atom selection for the ball-and-stick molecular viewer.

### Features Added
- Click on any atom to select it and view details
- Selected atoms are highlighted in yellow
- Info panel displays:
  - Atom element and index
  - Residue name, number, and chain
  - 3D coordinates (X, Y, Z)
  - Hotspot score for the residue
- Click empty space to deselect

### Testing Done
- [x] Atom selection works correctly
- [x] Info panel displays accurate data
- [x] Highlighting works as expected
- [x] No console errors

### Screenshots
[Add screenshots of the feature in action]

### Next Steps
- Phase 2: Add RMSF data and contact networks
- Phase 3: Implement molecular slicing
```

## Troubleshooting

### Issue: Raycaster not detecting atoms
**Solution:** Ensure atoms are added to the scene and have proper userData. Check that camera and canvas are properly initialized.

### Issue: Info panel not appearing
**Solution:** Check browser console for errors. Verify the API endpoints are returning data. Ensure the panel div exists in the HTML.

### Issue: Wrong atom selected
**Solution:** Verify atom indices match between the rendering code and the atoms array. Check that userData.atomIndex is set correctly.

### Issue: Hotspot data missing
**Solution:** Ensure `viewer/hotspots_residue.json` exists and contains data for the current frame.

## Performance Considerations

- Raycasting on every click is efficient for typical molecular structures (< 10,000 atoms)
- For very large structures, consider implementing spatial indexing
- Info panel updates are throttled to avoid excessive API calls

## Code Style

- Follow existing code style in the repository
- Use async/await for API calls
- Add comments for complex logic
- Keep functions small and focused

## Resources

- [Three.js Raycasting Documentation](https://threejs.org/docs/#api/en/core/Raycaster)
- [MDN Mouse Events](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent)
- See ARCHITECTURE.md for system overview
- See API_DOCUMENTATION.md for API endpoint details

## Phase 2 Preview

Once Phase 1 is complete and merged, Phase 2 will add:
- RMSF (flexibility) data display
- Contact network visualization
- Top interacting residues list
- Timeline: 1-2 weeks after Phase 1

---

**Questions?** Refer to DEVELOPER_GUIDE.md or create an issue in the repository.
