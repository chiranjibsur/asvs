# Phase 3 Implementation Guide: Molecular Slicing & Measurement Tools

This guide provides step-by-step instructions for implementing Phase 3 of the interactive molecular visualization features.

## Overview

**Phase 3 Goals:**
- Implement molecular slicing with interactive clip planes
- Add distance and angle measurement tools
- Create export capabilities for visualizations and data
- Enhanced filtering and selection tools
- **Timeline:** 2-3 weeks

## Prerequisites

Before starting, ensure:
- Phase 2 is complete and merged (RMSF and contact networks working)
- You have knowledge of Three.js clipping planes and geometry manipulation
- Development environment is set up (see DEVELOPER_GUIDE.md)
- Flask backend is running (`python app.py`)

## Implementation Steps

### Step 1: Set Up New Branch

```bash
# Switch to main integration branch and update
git checkout siya-integration
git pull origin siya-integration

# Create new feature branch
git checkout -b feature/slicing-measurements-phase3
```

### Step 2: Implement Molecular Slicing (Clip Planes)

#### 2.1 Add Clip Plane Controls to Ball-and-Stick Viewer

**File to edit:** `static/js/ballstick_viewer.js`

Add after the contact network code:

```javascript
// ---- Clip Plane Implementation ----
let clipPlanes = [];
let clipPlaneHelpers = [];
let enableClipping = false;

function createClipPlane(normal = new THREE.Vector3(0, 1, 0), constant = 0) {
  const plane = new THREE.Plane(normal, constant);
  clipPlanes.push(plane);
  
  // Create visual helper
  const helper = new THREE.PlaneHelper(plane, 50, 0xffff00);
  helper.visible = enableClipping;
  scene.add(helper);
  clipPlaneHelpers.push(helper);
  
  // Update renderer clipping planes
  renderer.clippingPlanes = clipPlanes;
  renderer.localClippingEnabled = true;
  
  return clipPlanes.length - 1;
}

function toggleClipping() {
  enableClipping = !enableClipping;
  renderer.localClippingEnabled = enableClipping;
  
  clipPlaneHelpers.forEach(helper => {
    helper.visible = enableClipping;
  });
  
  // Show/hide clip plane controls
  document.getElementById('clipPlaneControls').style.display = 
    enableClipping ? 'block' : 'none';
}

function updateClipPlane(index, axis, value) {
  if (index >= clipPlanes.length) return;
  
  const plane = clipPlanes[index];
  
  // Update plane based on axis
  switch(axis) {
    case 'x':
      plane.normal.set(1, 0, 0);
      break;
    case 'y':
      plane.normal.set(0, 1, 0);
      break;
    case 'z':
      plane.normal.set(0, 0, 1);
      break;
  }
  
  plane.constant = value;
  clipPlaneHelpers[index].updateMatrixWorld();
}

function removeClipPlane(index) {
  if (index >= clipPlanes.length) return;
  
  clipPlanes.splice(index, 1);
  
  const helper = clipPlaneHelpers[index];
  scene.remove(helper);
  clipPlaneHelpers.splice(index, 1);
  
  renderer.clippingPlanes = clipPlanes;
}

// Initialize with one clip plane
createClipPlane(new THREE.Vector3(0, 1, 0), 0);
```

#### 2.2 Add Clip Plane UI Controls

**File to edit:** `templates/ballstick_viewer.html`

Add clip plane control panel:

```html
<!-- Clip Plane Controls -->
<div id="clipPlaneControls" style="
  position: absolute;
  top: 80px;
  right: 340px;
  width: 280px;
  background: rgba(26, 28, 34, 0.95);
  border: 1px solid #2b2f3a;
  border-radius: 10px;
  padding: 16px;
  display: none;
  z-index: 100;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
">
  <h3 style="margin:0 0 12px 0;color:#e9eaee;font-size:16px;font-weight:600;">
    Clip Plane Controls
  </h3>
  
  <div class="clip-control">
    <label style="color:#b9beca;font-size:13px;margin-bottom:4px;display:block;">
      Plane 1 - Axis
    </label>
    <select id="clip1Axis" class="clip-select">
      <option value="x">X-Axis</option>
      <option value="y" selected>Y-Axis</option>
      <option value="z">Z-Axis</option>
    </select>
  </div>
  
  <div class="clip-control" style="margin-top:12px;">
    <label style="color:#b9beca;font-size:13px;margin-bottom:4px;display:block;">
      Position: <span id="clip1Value">0</span>
    </label>
    <input type="range" id="clip1Slider" min="-50" max="50" value="0" 
           style="width:100%;" />
  </div>
  
  <div style="margin-top:16px;display:flex;gap:8px;">
    <button class="btn" id="btnAddPlane">Add Plane</button>
    <button class="btn" id="btnResetPlanes">Reset</button>
  </div>
  
  <button id="closeClipBtn" class="close-btn">Close</button>
</div>

<style>
  .clip-control {
    margin-bottom: 8px;
  }
  
  .clip-select {
    width: 100%;
    padding: 6px;
    background: #1f232b;
    color: #e9eaee;
    border: 1px solid #2b2f3a;
    border-radius: 6px;
    font-size: 13px;
  }
</style>

<script>
  // Clip plane event listeners
  document.getElementById('clip1Axis').addEventListener('change', (e) => {
    updateClipPlane(0, e.target.value, parseFloat(document.getElementById('clip1Slider').value));
  });
  
  document.getElementById('clip1Slider').addEventListener('input', (e) => {
    const value = parseFloat(e.target.value);
    document.getElementById('clip1Value').textContent = value.toFixed(1);
    const axis = document.getElementById('clip1Axis').value;
    updateClipPlane(0, axis, value);
  });
  
  document.getElementById('btnResetPlanes').addEventListener('click', () => {
    document.getElementById('clip1Slider').value = 0;
    document.getElementById('clip1Value').textContent = '0';
    updateClipPlane(0, document.getElementById('clip1Axis').value, 0);
  });
  
  document.getElementById('closeClipBtn').addEventListener('click', () => {
    toggleClipping();
  });
</script>
```

Add clip plane toggle button:

```html
<button class="btn" id="btnToggleClipping">Enable Clipping</button>

<script>
  document.getElementById('btnToggleClipping').addEventListener('click', () => {
    const btn = document.getElementById('btnToggleClipping');
    btn.textContent = btn.textContent === 'Enable Clipping' ? 'Disable Clipping' : 'Enable Clipping';
    window.toggleClipping();
  });
  
  window.toggleClipping = toggleClipping;
  window.updateClipPlane = updateClipPlane;
</script>
```

### Step 3: Implement Distance Measurement Tool

#### 3.1 Add Distance Measurement Logic

**File to edit:** `static/js/ballstick_viewer.js`

```javascript
// ---- Distance Measurement Tool ----
let measurementMode = false;
let measurementPoints = [];
let measurementLines = [];
let measurementLabels = [];

function toggleMeasurementMode() {
  measurementMode = !measurementMode;
  
  if (!measurementMode) {
    // Clear measurements
    clearMeasurements();
  }
  
  // Update cursor style
  canvas.style.cursor = measurementMode ? 'crosshair' : 'default';
}

function addMeasurementPoint(position, atomIndex) {
  measurementPoints.push({ position, atomIndex });
  
  // Create sphere marker
  const geometry = new THREE.SphereGeometry(0.5, 16, 16);
  const material = new THREE.MeshBasicMaterial({ color: 0xff00ff });
  const marker = new THREE.Mesh(geometry, material);
  marker.position.copy(position);
  scene.add(marker);
  measurementLabels.push(marker);
  
  // If we have 2 points, create measurement line
  if (measurementPoints.length === 2) {
    createDistanceMeasurement();
    measurementPoints = []; // Reset for next measurement
  }
}

function createDistanceMeasurement() {
  const p1 = measurementPoints[0].position;
  const p2 = measurementPoints[1].position;
  
  // Calculate distance
  const distance = p1.distanceTo(p2);
  
  // Create line
  const points = [p1, p2];
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ 
    color: 0xff00ff, 
    linewidth: 2 
  });
  const line = new THREE.Line(geometry, material);
  scene.add(line);
  measurementLines.push(line);
  
  // Create text label (using CSS2DRenderer would be ideal, but for simplicity)
  const midpoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
  
  // Store measurement info
  console.log(`Distance: ${distance.toFixed(2)} Å`);
  
  // Display in UI
  addMeasurementToList(distance, measurementPoints[0].atomIndex, measurementPoints[1].atomIndex);
}

function clearMeasurements() {
  measurementPoints = [];
  
  measurementLines.forEach(line => {
    scene.remove(line);
    line.geometry.dispose();
    line.material.dispose();
  });
  measurementLines = [];
  
  measurementLabels.forEach(marker => {
    scene.remove(marker);
    marker.geometry.dispose();
    marker.material.dispose();
  });
  measurementLabels = [];
  
  // Clear UI list
  document.getElementById('measurementsList').innerHTML = '';
}

function addMeasurementToList(distance, atom1, atom2) {
  const listHtml = `
    <div class="measurement-item">
      <strong>Distance:</strong> ${distance.toFixed(2)} Å<br>
      <span style="opacity:0.7;">Atom ${atom1} ↔ Atom ${atom2}</span>
    </div>
  `;
  
  document.getElementById('measurementsList').innerHTML += listHtml;
}

// Modify click handler to support measurement mode
const originalOnAtomClick = onAtomClick;
function onAtomClick(event) {
  if (measurementMode) {
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(atomMeshes, false);
    
    if (intersects.length > 0) {
      const atomIndex = intersects[0].object.userData.atomIndex;
      const position = intersects[0].point;
      addMeasurementPoint(position, atomIndex);
    }
  } else {
    originalOnAtomClick(event);
  }
}
```

#### 3.2 Add Measurement UI Panel

**File to edit:** `templates/ballstick_viewer.html`

```html
<!-- Measurements Panel -->
<div id="measurementsPanel" style="
  position: absolute;
  bottom: 20px;
  left: 20px;
  width: 280px;
  max-height: 300px;
  background: rgba(26, 28, 34, 0.95);
  border: 1px solid #2b2f3a;
  border-radius: 10px;
  padding: 16px;
  display: none;
  z-index: 100;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
">
  <h3 style="margin:0 0 12px 0;color:#e9eaee;font-size:16px;font-weight:600;">
    Measurements
  </h3>
  <div id="measurementsList"></div>
  <button class="btn" id="btnClearMeasurements" style="margin-top:12px;width:100%;">
    Clear All
  </button>
</div>

<style>
  .measurement-item {
    padding: 8px;
    margin-bottom: 6px;
    background: #1f232b;
    border-radius: 6px;
    font-size: 12px;
    color: #b9beca;
  }
</style>
```

Add measurement toggle button:

```html
<button class="btn" id="btnToggleMeasure">Measure Distance</button>

<script>
  document.getElementById('btnToggleMeasure').addEventListener('click', () => {
    const btn = document.getElementById('btnToggleMeasure');
    const isActive = btn.textContent === 'Measure Distance';
    btn.textContent = isActive ? 'Stop Measuring' : 'Measure Distance';
    
    if (isActive) {
      document.getElementById('measurementsPanel').style.display = 'block';
    }
    
    window.toggleMeasurementMode();
  });
  
  document.getElementById('btnClearMeasurements').addEventListener('click', () => {
    window.clearMeasurements();
  });
  
  window.toggleMeasurementMode = toggleMeasurementMode;
  window.clearMeasurements = clearMeasurements;
</script>
```

### Step 4: Implement Export Capabilities

#### 4.1 Add Screenshot Export

**File to edit:** `static/js/ballstick_viewer.js`

```javascript
// ---- Export Functionality ----
function exportScreenshot(format = 'png') {
  // Render the scene
  renderer.render(scene, camera);
  
  // Get canvas data
  const dataURL = canvas.toDataURL(`image/${format}`);
  
  // Create download link
  const link = document.createElement('a');
  link.download = `molecular-view-${Date.now()}.${format}`;
  link.href = dataURL;
  link.click();
}

function exportMeasurements() {
  const measurements = [];
  const items = document.querySelectorAll('.measurement-item');
  
  items.forEach((item, index) => {
    const text = item.textContent;
    measurements.push({
      id: index + 1,
      text: text.trim()
    });
  });
  
  const data = {
    timestamp: new Date().toISOString(),
    measurements: measurements,
    frame: parseInt(slider.value, 10)
  };
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { 
    type: 'application/json' 
  });
  
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.download = `measurements-${Date.now()}.json`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}

function exportContactsData() {
  if (!contactsData) {
    alert("No contacts data available");
    return;
  }
  
  const data = {
    timestamp: new Date().toISOString(),
    frame: parseInt(slider.value, 10),
    contacts: contactsData.contacts.slice(0, 50)
  };
  
  const csv = convertContactsToCSV(data.contacts);
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.download = `contacts-${Date.now()}.csv`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}

function convertContactsToCSV(contacts) {
  const headers = 'Residue1,Residue2,Frequency\n';
  const rows = contacts.map(c => 
    `${c.residue1},${c.residue2},${c.frequency}`
  ).join('\n');
  return headers + rows;
}
```

#### 4.2 Add Export UI

**File to edit:** `templates/ballstick_viewer.html`

```html
<button class="btn" id="btnExport">Export ▼</button>

<!-- Export dropdown menu -->
<div id="exportMenu" style="
  position: absolute;
  top: 180px;
  left: 20px;
  width: 200px;
  background: rgba(26, 28, 34, 0.95);
  border: 1px solid #2b2f3a;
  border-radius: 8px;
  padding: 8px;
  display: none;
  z-index: 101;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
">
  <button class="btn" id="btnExportPNG" style="width:100%;margin-bottom:4px;">
    PNG Image
  </button>
  <button class="btn" id="btnExportMeasurements" style="width:100%;margin-bottom:4px;">
    Measurements (JSON)
  </button>
  <button class="btn" id="btnExportContacts" style="width:100%;">
    Contacts (CSV)
  </button>
</div>

<script>
  document.getElementById('btnExport').addEventListener('click', () => {
    const menu = document.getElementById('exportMenu');
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
  });
  
  document.getElementById('btnExportPNG').addEventListener('click', () => {
    window.exportScreenshot('png');
    document.getElementById('exportMenu').style.display = 'none';
  });
  
  document.getElementById('btnExportMeasurements').addEventListener('click', () => {
    window.exportMeasurements();
    document.getElementById('exportMenu').style.display = 'none';
  });
  
  document.getElementById('btnExportContacts').addEventListener('click', () => {
    window.exportContactsData();
    document.getElementById('exportMenu').style.display = 'none';
  });
  
  window.exportScreenshot = exportScreenshot;
  window.exportMeasurements = exportMeasurements;
  window.exportContactsData = exportContactsData;
</script>
```

### Step 5: Apply to Ribbon Viewer

Add simplified clipping and export to ribbon viewer:

**File to edit:** `static/js/ribbon_viewer.js`

```javascript
// ---- Clip Plane for Ribbon ----
let clipPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
let enableClipping = false;

function toggleClipping() {
  enableClipping = !enableClipping;
  renderer.localClippingEnabled = enableClipping;
  
  if (tube) {
    tube.material.clippingPlanes = enableClipping ? [clipPlane] : [];
  }
}

function updateClipPlane(axis, value) {
  switch(axis) {
    case 'x':
      clipPlane.normal.set(1, 0, 0);
      break;
    case 'y':
      clipPlane.normal.set(0, 1, 0);
      break;
    case 'z':
      clipPlane.normal.set(0, 0, 1);
      break;
  }
  clipPlane.constant = value;
}

// Export functionality
function exportScreenshot(format = 'png') {
  renderer.render(scene, camera);
  const dataURL = canvas.toDataURL(`image/${format}`);
  const link = document.createElement('a');
  link.download = `ribbon-view-${Date.now()}.${format}`;
  link.href = dataURL;
  link.click();
}
```

### Step 6: Testing

#### 6.1 Manual Testing Checklist

- [ ] Clip planes work in ball-and-stick viewer
- [ ] Multiple clip planes can be added
- [ ] Clip plane controls update the visualization in real-time
- [ ] Distance measurement mode activates correctly
- [ ] Measurements display correct distances
- [ ] Measurements list updates properly
- [ ] PNG export works
- [ ] Measurement data export (JSON) works
- [ ] Contact data export (CSV) works
- [ ] All features work across frames
- [ ] No performance degradation with clipping enabled

#### 6.2 Visual Validation

```bash
# Start Flask server
python app.py

# Test in browser
# 1. Navigate to http://localhost:5000/viewer/ballstick
# 2. Enable clipping and adjust plane
# 3. Click "Measure Distance" and select two atoms
# 4. Use Export menu to test all export functions
```

### Step 7: Commit and Push

```bash
# Add changes
git add static/js/ballstick_viewer.js
git add static/js/ribbon_viewer.js
git add templates/ballstick_viewer.html
git add templates/ribbon_viewer.html

# Commit
git commit -m "Add Phase 3: Molecular slicing, measurements, and export

- Implement clip plane controls with adjustable position/axis
- Add distance measurement tool with visual markers
- Create export functionality for images and data
- Support multiple clip planes
- Add measurement history panel
- Export options: PNG, JSON measurements, CSV contacts"

# Push to remote
git push origin feature/slicing-measurements-phase3
```

### Step 8: Create Pull Request

1. Go to GitHub repository
2. Click "Compare & pull request" for your new branch
3. Set base branch to `siya-integration`
4. Title: "Phase 3: Add molecular slicing, measurements, and export"
5. Description: Use the template below

```markdown
## Phase 3: Molecular Slicing, Measurements & Export

Implements advanced analysis and visualization control features.

### Features Added

#### Molecular Slicing (Clip Planes)
- Interactive clip plane controls
- Adjustable axis (X, Y, Z) and position
- Multiple clip plane support
- Real-time visualization updates
- Visual plane helpers

#### Distance Measurement Tool
- Click two atoms to measure distance
- Visual markers (purple spheres)
- Measurement history panel
- Accurate Ångström calculations
- Clear all measurements option

#### Export Capabilities
- **PNG Export**: High-quality screenshots
- **Measurements Export**: JSON format with metadata
- **Contacts Export**: CSV format for analysis
- Timestamped filenames

### Implementation Details

**Clipping:**
- Uses Three.js Plane and renderer.clippingPlanes
- Supports up to 6 planes (WebGL limit)
- Real-time updates via slider controls

**Measurements:**
- Distance calculated using Three.js Vector3.distanceTo()
- Measurement mode with crosshair cursor
- Persistent markers and lines
- Export to JSON for external analysis

**Export:**
- Canvas.toDataURL() for image export
- Blob API for data downloads
- CSV conversion for contact networks

### Testing Done
- [x] Clip planes work correctly
- [x] Measurements accurate
- [x] All export formats work
- [x] No console errors
- [x] Performance acceptable with multiple planes

### Screenshots
[Add screenshots of clip plane, measurements, and export menu]
```

## Troubleshooting

### Issue: Clipping plane not visible
**Solution:** Ensure `renderer.localClippingEnabled = true` and PlaneHelper is added to scene.

### Issue: Measurements not showing
**Solution:** Check that measurement mode is active (crosshair cursor). Verify raycaster is detecting intersections.

### Issue: Export fails
**Solution:** Check browser console for errors. Ensure canvas is properly rendered before export. Some browsers block automatic downloads.

### Issue: Performance issues with multiple clip planes
**Solution:** Limit to 3-4 planes. Consider simplifying geometry or reducing render quality.

## Advanced Features (Optional)

### Angle Measurement
Extend measurement tool to support 3-point angle measurement:

```javascript
function calculateAngle(p1, p2, p3) {
  const v1 = new THREE.Vector3().subVectors(p1, p2);
  const v2 = new THREE.Vector3().subVectors(p3, p2);
  return v1.angleTo(v2) * (180 / Math.PI); // Convert to degrees
}
```

### Animated Clipping
Create smooth clip plane animations:

```javascript
function animateClipPlane(targetValue, duration = 1000) {
  const startValue = clipPlane.constant;
  const startTime = Date.now();
  
  function animate() {
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    clipPlane.constant = startValue + (targetValue - startValue) * progress;
    
    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  }
  
  animate();
}
```

## Performance Considerations

- Clipping can be GPU-intensive; monitor frame rate
- Limit number of measurement markers
- Clear old measurements periodically
- Consider level-of-detail for large structures

## Code Style

- Follow existing Three.js patterns
- Use async/await for export operations
- Keep measurement data structures simple
- Add comments for complex calculations

## Resources

- [Three.js Clipping Documentation](https://threejs.org/docs/#api/en/materials/Material.clippingPlanes)
- [Three.js PlaneHelper](https://threejs.org/docs/#api/en/helpers/PlaneHelper)
- [Canvas toDataURL](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toDataURL)
- [Blob API](https://developer.mozilla.org/en-US/docs/Web/API/Blob)

## Future Enhancements (Phase 4+)

After Phase 3 is complete:
- Dihedral angle measurements
- Surface area calculations
- Volume calculations within clip regions
- Animation export (video/GIF)
- VR/AR support
- Collaborative viewing

---

**Questions?** Refer to DEVELOPER_GUIDE.md or create an issue in the repository.
