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

#### 6.1 Manual Testing Checklist

- [ ] Start the Flask server: `python app.py`
- [ ] Navigate to http://localhost:5000/viewer/ballstick
- [ ] Load a frame and verify atoms are visible
- [ ] Click on an atom - info panel should appear
- [ ] Verify the selected atom is highlighted in yellow
- [ ] Check that atom details are correct (element, residue, coordinates)
- [ ] Click on empty space - selection should clear
- [ ] Click on different atoms - panel should update
- [ ] Test with different frames using the slider

#### 6.2 Browser Console Testing

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
