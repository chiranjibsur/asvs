# Phase 4 Implementation Guide: Advanced Measurements & Export

This guide provides step-by-step instructions for implementing Phase 4 of the interactive molecular visualization features.

## Overview

**Phase 4 Goals:**
- Implement 3-point and 4-point angle measurements
- Add SVG vector export for publication figures
- Create FPS monitoring and performance dashboard
- Enable advanced export formats (video/GIF, 3D models)
- Implement rotated clip planes
- **Timeline:** 3-4 weeks

## Prerequisites

Before starting, ensure:
- Phase 3 is complete and merged (clipping, distance measurements, basic exports)
- Distance measurement system is working and tested
- Three.js renderer and controls are stable
- Development environment is set up (see DEVELOPER_GUIDE.md)
- Flask backend is running (`python app.py`)

## Implementation Steps

### Step 1: Set Up New Branch

```bash
# Switch to main integration branch and update
git checkout siya-integration
git pull origin siya-integration

# Create new feature branch
git checkout -b feature/phase4-angles-advanced-export
```

### Step 2: Implement Angle Measurements

#### 2.1 Add 3-Point Angle Measurement

**File to edit:** `static/js/ballstick_viewer.js`

Extend the measurement system from Phase 3:

```javascript
// ---- Angle Measurement Tool (3-point) ----
let angleMeasurementMode = false;
let anglePoints = [];

function toggleAngleMeasurementMode() {
  angleMeasurementMode = !angleMeasurementMode;
  measurementMode = false; // Disable distance mode
  
  canvas.style.cursor = angleMeasurementMode ? 'crosshair' : 'default';
  
  return angleMeasurementMode;
}

function addAnglePoint(position, atomIndex) {
  anglePoints.push({ position: position.clone(), atomIndex });
  
  // Create sphere marker
  const geometry = new THREE.SphereGeometry(0.5, 16, 16);
  const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 }); // Green for angles
  const marker = new THREE.Mesh(geometry, material);
  marker.position.copy(position);
  scene.add(marker);
  measurementMarkers.push(marker);
  
  // If we have 3 points, create angle measurement
  if (anglePoints.length === 3) {
    createAngleMeasurement();
    anglePoints = []; // Reset for next measurement
  }
}

function createAngleMeasurement() {
  const p1 = anglePoints[0].position;
  const p2 = anglePoints[1].position; // Vertex
  const p3 = anglePoints[2].position;
  
  // Calculate angle using vectors
  const v1 = new THREE.Vector3().subVectors(p1, p2);
  const v2 = new THREE.Vector3().subVectors(p3, p2);
  const angle = v1.angleTo(v2) * (180 / Math.PI); // Convert to degrees
  
  // Create visual arc
  createAngleArc(p1, p2, p3, angle);
  
  // Create connecting lines
  createAngleLines(p1, p2, p3);
  
  // Store measurement info
  const currentFrame = parseInt(slider.value, 10);
  const measurement = {
    id: measurements.length + 1,
    type: 'angle',
    atom1: anglePoints[0].atomIndex,
    atom2: anglePoints[1].atomIndex, // Vertex
    atom3: anglePoints[2].atomIndex,
    angle: angle,
    frame: currentFrame,
    unit: '°'
  };
  measurements.push(measurement);
  
  console.log(`Angle: ${angle.toFixed(2)}° (Atoms ${anglePoints[0].atomIndex}-${anglePoints[1].atomIndex}-${anglePoints[2].atomIndex})`);
  
  // Update UI
  updateMeasurementsList();
}

function createAngleArc(p1, p2, p3, angle) {
  // Create arc geometry
  const radius = 3.0;
  const segments = 32;
  
  const v1 = new THREE.Vector3().subVectors(p1, p2).normalize();
  const v2 = new THREE.Vector3().subVectors(p3, p2).normalize();
  
  const curve = new THREE.QuadraticBezierCurve3(
    p2.clone().add(v1.clone().multiplyScalar(radius)),
    p2.clone().add(v1.clone().add(v2).normalize().multiplyScalar(radius * 1.2)),
    p2.clone().add(v2.clone().multiplyScalar(radius))
  );
  
  const points = curve.getPoints(segments);
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ 
    color: 0x00ff00, 
    linewidth: 2,
    transparent: true,
    opacity: 0.7
  });
  const arc = new THREE.Line(geometry, material);
  scene.add(arc);
  measurementLines.push(arc);
}

function createAngleLines(p1, p2, p3) {
  // Line from p1 to p2 (vertex)
  const points1 = [p1, p2];
  const geometry1 = new THREE.BufferGeometry().setFromPoints(points1);
  const material = new THREE.LineBasicMaterial({ 
    color: 0x00ff00, 
    linewidth: 1,
    transparent: true,
    opacity: 0.5
  });
  const line1 = new THREE.Line(geometry1, material);
  scene.add(line1);
  measurementLines.push(line1);
  
  // Line from p2 to p3
  const points2 = [p2, p3];
  const geometry2 = new THREE.BufferGeometry().setFromPoints(points2);
  const line2 = new THREE.Line(geometry2, material);
  scene.add(line2);
  measurementLines.push(line2);
}
```

#### 2.2 Add 4-Point Dihedral Angle Measurement

```javascript
// ---- Dihedral Angle Measurement (4-point) ----
let dihedralMeasurementMode = false;
let dihedralPoints = [];

function toggleDihedralMeasurementMode() {
  dihedralMeasurementMode = !dihedralMeasurementMode;
  measurementMode = false;
  angleMeasurementMode = false;
  
  canvas.style.cursor = dihedralMeasurementMode ? 'crosshair' : 'default';
  
  return dihedralMeasurementMode;
}

function addDihedralPoint(position, atomIndex) {
  dihedralPoints.push({ position: position.clone(), atomIndex });
  
  // Create sphere marker
  const geometry = new THREE.SphereGeometry(0.5, 16, 16);
  const material = new THREE.MeshBasicMaterial({ color: 0xffff00 }); // Yellow for dihedrals
  const marker = new THREE.Mesh(geometry, material);
  marker.position.copy(position);
  scene.add(marker);
  measurementMarkers.push(marker);
  
  // If we have 4 points, create dihedral measurement
  if (dihedralPoints.length === 4) {
    createDihedralMeasurement();
    dihedralPoints = []; // Reset for next measurement
  }
}

function createDihedralMeasurement() {
  const p1 = dihedralPoints[0].position;
  const p2 = dihedralPoints[1].position;
  const p3 = dihedralPoints[2].position;
  const p4 = dihedralPoints[3].position;
  
  // Calculate dihedral angle
  const dihedral = calculateDihedral(p1, p2, p3, p4);
  
  // Create visual representation
  createDihedralLines(p1, p2, p3, p4);
  
  // Store measurement info
  const currentFrame = parseInt(slider.value, 10);
  const measurement = {
    id: measurements.length + 1,
    type: 'dihedral',
    atom1: dihedralPoints[0].atomIndex,
    atom2: dihedralPoints[1].atomIndex,
    atom3: dihedralPoints[2].atomIndex,
    atom4: dihedralPoints[3].atomIndex,
    angle: dihedral,
    frame: currentFrame,
    unit: '°'
  };
  measurements.push(measurement);
  
  console.log(`Dihedral: ${dihedral.toFixed(2)}° (Atoms ${dihedralPoints[0].atomIndex}-${dihedralPoints[1].atomIndex}-${dihedralPoints[2].atomIndex}-${dihedralPoints[3].atomIndex})`);
  
  // Update UI
  updateMeasurementsList();
}

function calculateDihedral(p1, p2, p3, p4) {
  // Calculate dihedral angle using cross products
  const b1 = new THREE.Vector3().subVectors(p2, p1);
  const b2 = new THREE.Vector3().subVectors(p3, p2);
  const b3 = new THREE.Vector3().subVectors(p4, p3);
  
  const n1 = new THREE.Vector3().crossVectors(b1, b2).normalize();
  const n2 = new THREE.Vector3().crossVectors(b2, b3).normalize();
  
  const m1 = new THREE.Vector3().crossVectors(n1, b2.normalize());
  
  const x = n1.dot(n2);
  const y = m1.dot(n2);
  
  const dihedral = -Math.atan2(y, x) * (180 / Math.PI);
  
  return dihedral;
}

function createDihedralLines(p1, p2, p3, p4) {
  const points = [p1, p2, p3, p4];
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ 
    color: 0xffff00, 
    linewidth: 2
  });
  const line = new THREE.Line(geometry, material);
  scene.add(line);
  measurementLines.push(line);
}
```

#### 2.3 Update Click Handler

Modify the `onAtomClick` function to support angle measurements:

```javascript
function onAtomClick(event) {
  // Update raycaster
  raycaster.setFromCamera(mouse, camera);
  
  // Check for intersections with atom meshes
  const intersects = raycaster.intersectObjects(atomMeshes, false);
  
  if (intersects.length > 0) {
    const clickedObject = intersects[0].object;
    
    if (clickedObject.userData && clickedObject.userData.atomIndex !== undefined) {
      const atomIndex = clickedObject.userData.atomIndex;
      const position = clickedObject.position.clone();
      
      // Check which mode we're in
      if (measurementMode) {
        addMeasurementPoint(position, atomIndex);
      } else if (angleMeasurementMode) {
        addAnglePoint(position, atomIndex);
      } else if (dihedralMeasurementMode) {
        addDihedralPoint(position, atomIndex);
      } else {
        selectAtom(atomIndex);
      }
    }
  } else {
    // Clicked on empty space
    if (!measurementMode && !angleMeasurementMode && !dihedralMeasurementMode) {
      deselectAtom();
    }
  }
}
```

#### 2.4 Update Measurements List Display

Modify `updateMeasurementsList()` to show different measurement types:

```javascript
function updateMeasurementsList() {
  const listElement = document.getElementById('measurementsList');
  if (!listElement) return;
  
  if (measurements.length === 0) {
    listElement.innerHTML = '<div style="color:#9aa3b2;font-size:12px;text-align:center;">No measurements yet</div>';
    return;
  }
  
  let html = '';
  for (const m of measurements) {
    if (m.type === 'angle') {
      html += `
        <div class="measurement-item">
          <strong>Angle:</strong> ${m.angle.toFixed(2)}${m.unit}<br>
          <span style="opacity:0.7;">Atoms ${m.atom1}-${m.atom2}-${m.atom3}</span>
          ${persistMeasurements ? `<br><span style="opacity:0.5;font-size:11px;">Frame ${m.frame}</span>` : ''}
        </div>
      `;
    } else if (m.type === 'dihedral') {
      html += `
        <div class="measurement-item">
          <strong>Dihedral:</strong> ${m.angle.toFixed(2)}${m.unit}<br>
          <span style="opacity:0.7;">Atoms ${m.atom1}-${m.atom2}-${m.atom3}-${m.atom4}</span>
          ${persistMeasurements ? `<br><span style="opacity:0.5;font-size:11px;">Frame ${m.frame}</span>` : ''}
        </div>
      `;
    } else {
      // Distance measurement
      html += `
        <div class="measurement-item">
          <strong>Distance:</strong> ${m.distance.toFixed(2)} ${m.unit}<br>
          <span style="opacity:0.7;">Atom ${m.atom1} ↔ Atom ${m.atom2}</span>
          ${persistMeasurements ? `<br><span style="opacity:0.5;font-size:11px;">Frame ${m.frame}</span>` : ''}
        </div>
      `;
    }
  }
  
  listElement.innerHTML = html;
}
```

### Step 3: Implement FPS Monitor

#### 3.1 Add FPS Counter

**File to edit:** `static/js/ballstick_viewer.js`

```javascript
// ---- FPS Monitor ----
let showFPS = true;
let fpsHistory = [];
let lastTime = performance.now();

function updateFPS() {
  const now = performance.now();
  const delta = now - lastTime;
  lastTime = now;
  
  const fps = 1000 / delta;
  fpsHistory.push(fps);
  if (fpsHistory.length > 60) fpsHistory.shift(); // Keep last 60 frames
  
  const avgFPS = fpsHistory.reduce((a, b) => a + b, 0) / fpsHistory.length;
  
  // Update FPS display
  if (showFPS) {
    const fpsElement = document.getElementById('fpsCounter');
    if (fpsElement) {
      fpsElement.textContent = `${Math.round(avgFPS)} FPS`;
      
      // Color code based on performance
      if (avgFPS < PERFORMANCE_FPS_WARNING) {
        fpsElement.style.color = '#ff6b6b'; // Red
      } else if (avgFPS < 50) {
        fpsElement.style.color = '#ffd93d'; // Yellow
      } else {
        fpsElement.style.color = '#6bcf7f'; // Green
      }
    }
  }
}

function toggleFPS() {
  showFPS = !showFPS;
  const fpsElement = document.getElementById('fpsCounter');
  if (fpsElement) {
    fpsElement.style.display = showFPS ? 'block' : 'none';
  }
  return showFPS;
}
```

#### 3.2 Update Render Loop

```javascript
(function renderLoop () {
  controls.update();
  renderer.render(scene, camera);
  updateFPS(); // Add FPS monitoring
  requestAnimationFrame(renderLoop);
})();
```

### Step 4: Implement SVG Export

#### 4.1 Add SVG Export Function

**File to edit:** `static/js/ballstick_viewer.js`

```javascript
// ---- SVG Export ----
function exportSVG() {
  // Create SVGRenderer
  const svgRenderer = new THREE.SVGRenderer();
  svgRenderer.setSize(canvas.clientWidth, canvas.clientHeight);
  
  // Render scene to SVG
  svgRenderer.render(scene, camera);
  
  // Get SVG content
  const svgElement = svgRenderer.domElement;
  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(svgElement);
  
  // Create download link
  const blob = new Blob([svgString], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const currentFrame = parseInt(slider.value, 10);
  link.download = `molecular-view-frame${currentFrame}-${timestamp}.svg`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}
```

**Note:** You'll need to include Three.js SVGRenderer. Add to HTML:

```html
<script src="https://cdn.jsdelivr.net/npm/three@0.150.0/examples/js/renderers/SVGRenderer.js"></script>
```

### Step 5: Add UI Controls

#### 5.1 Update Ball-and-Stick Viewer HTML

**File to edit:** `templates/ballstick_viewer.html`

Add measurement mode selector:

```html
<div style="display:flex;gap:10px;margin-bottom:12px">
  <!-- Existing buttons -->
  <button class="btn" id="btnToggleRMSF">Show RMSF</button>
  <button class="btn" id="btnToggleContacts">Show Contacts</button>
  <button class="btn" id="btnShowContacts">Top Contacts</button>
  <button class="btn" id="btnToggleClipping">Enable Clipping</button>
  
  <!-- New: Measurement mode selector -->
  <select id="measurementModeSelector" class="btn" style="padding:8px 12px;">
    <option value="none">Select Tool</option>
    <option value="distance">Distance (2-point)</option>
    <option value="angle">Angle (3-point)</option>
    <option value="dihedral">Dihedral (4-point)</option>
  </select>
  
  <button class="btn" id="btnExport">Export ▼</button>
  
  <!-- FPS Counter -->
  <div id="fpsCounter" style="
    position:fixed;
    top:20px;
    right:20px;
    padding:8px 12px;
    background:rgba(26, 28, 34, 0.95);
    border:1px solid #2b2f3a;
    border-radius:8px;
    font-size:14px;
    font-weight:600;
    z-index:1000;
  ">60 FPS</div>
</div>
```

Add SVG export option:

```html
<!-- Export Menu -->
<div id="exportMenu" style="...">
  <button class="menu-btn" id="btnExportPNG">PNG Image</button>
  <button class="menu-btn" id="btnExportSVG">SVG Vector</button>
  <button class="menu-btn" id="btnExportMeasurements">Measurements (JSON)</button>
  <button class="menu-btn" id="btnExportContacts">Contacts (CSV)</button>
</div>
```

#### 5.2 Add Event Listeners

```javascript
// Measurement mode selector
document.getElementById('measurementModeSelector').addEventListener('change', (e) => {
  const mode = e.target.value;
  
  // Disable all measurement modes first
  if (measurementMode) window.toggleMeasurementMode();
  if (angleMeasurementMode) window.toggleAngleMeasurementMode();
  if (dihedralMeasurementMode) window.toggleDihedralMeasurementMode();
  
  // Enable selected mode
  if (mode === 'distance') {
    window.toggleMeasurementMode();
    document.getElementById('measurementsPanel').style.display = 'block';
  } else if (mode === 'angle') {
    window.toggleAngleMeasurementMode();
    document.getElementById('measurementsPanel').style.display = 'block';
  } else if (mode === 'dihedral') {
    window.toggleDihedralMeasurementMode();
    document.getElementById('measurementsPanel').style.display = 'block';
  } else {
    document.getElementById('measurementsPanel').style.display = 'none';
  }
});

// SVG export
document.getElementById('btnExportSVG').addEventListener('click', () => {
  window.exportSVG();
  document.getElementById('exportMenu').style.display = 'none';
});

// FPS toggle (double-click on counter)
document.getElementById('fpsCounter').addEventListener('dblclick', () => {
  window.toggleFPS();
});
```

### Step 6: Expose New Functions

Add to the end of `ballstick_viewer.js`:

```javascript
// Expose Phase 4 functions
window.toggleAngleMeasurementMode = toggleAngleMeasurementMode;
window.toggleDihedralMeasurementMode = toggleDihedralMeasurementMode;
window.exportSVG = exportSVG;
window.toggleFPS = toggleFPS;
```

### Step 7: Testing

#### 7.1 Manual Testing Checklist

- [ ] 3-point angle measurement works correctly
- [ ] Angle visual arc displays properly
- [ ] 4-point dihedral measurement calculates correct values
- [ ] Dihedral visual lines connect all 4 points
- [ ] Measurements panel shows all measurement types
- [ ] FPS counter displays and updates in real-time
- [ ] FPS counter color codes based on performance
- [ ] SVG export creates valid downloadable file
- [ ] SVG export includes all visible geometry
- [ ] Measurement mode selector switches modes correctly
- [ ] All measurements export correctly in JSON
- [ ] No performance degradation with new features

#### 7.2 Visual Validation

```bash
# Start Flask server
python app.py

# Test in browser
# 1. Navigate to http://localhost:5000/viewer/ballstick
# 2. Select "Angle (3-point)" from measurement tool
# 3. Click 3 atoms and verify angle display
# 4. Select "Dihedral (4-point)" and test
# 5. Export as SVG and verify output
# 6. Check FPS counter in top-right
```

### Step 8: Advanced Features (Optional)

#### 8.1 Rotated Clip Planes

```javascript
// ---- Rotated Clip Planes ----
function rotateClipPlane(index, pitch, yaw, roll) {
  if (index >= clipPlanes.length) return;
  
  const plane = clipPlanes[index];
  
  // Create rotation quaternion
  const euler = new THREE.Euler(
    pitch * Math.PI / 180,
    yaw * Math.PI / 180,
    roll * Math.PI / 180,
    'XYZ'
  );
  const quaternion = new THREE.Quaternion().setFromEuler(euler);
  
  // Apply rotation to plane normal
  const normal = new THREE.Vector3(0, 1, 0).applyQuaternion(quaternion);
  plane.normal.copy(normal);
  
  // Update helper
  if (clipPlaneHelpers[index]) {
    clipPlaneHelpers[index].updateMatrixWorld();
  }
}
```

#### 8.2 Video/GIF Export

```javascript
// ---- Video Export (using CCapture.js) ----
let capturer = null;
let isCapturing = false;

function startVideoCapture(format = 'gif') {
  capturer = new CCapture({
    format: format, // 'gif' or 'webm'
    framerate: 30,
    quality: 100,
    name: 'molecular-animation'
  });
  
  capturer.start();
  isCapturing = true;
}

function captureFrame() {
  if (isCapturing && capturer) {
    capturer.capture(canvas);
  }
}

function stopVideoCapture() {
  if (capturer) {
    capturer.stop();
    capturer.save();
    capturer = null;
    isCapturing = false;
  }
}

// Add to render loop
(function renderLoop () {
  controls.update();
  renderer.render(scene, camera);
  updateFPS();
  captureFrame(); // Capture if recording
  requestAnimationFrame(renderLoop);
})();
```

### Step 9: Documentation

Update measurements export format to include angles:

```javascript
function exportMeasurements() {
  if (measurements.length === 0) {
    // ... (existing code)
  }
  
  const currentFrame = parseInt(slider.value, 10);
  const data = {
    timestamp: new Date().toISOString(),
    frame: currentFrame,
    camera: {
      position: {
        x: camera.position.x,
        y: camera.position.y,
        z: camera.position.z
      },
      rotation: {
        x: camera.rotation.x,
        y: camera.rotation.y,
        z: camera.rotation.z
      }
    },
    measurements: measurements.map(m => {
      if (m.type === 'angle') {
        return {
          id: m.id,
          type: 'angle',
          atoms: [m.atom1, m.atom2, m.atom3],
          value: m.angle,
          unit: m.unit,
          frame: m.frame
        };
      } else if (m.type === 'dihedral') {
        return {
          id: m.id,
          type: 'dihedral',
          atoms: [m.atom1, m.atom2, m.atom3, m.atom4],
          value: m.angle,
          unit: m.unit,
          frame: m.frame
        };
      } else {
        return {
          id: m.id,
          type: 'distance',
          atoms: [m.atom1, m.atom2],
          value: m.distance,
          unit: m.unit,
          frame: m.frame
        };
      }
    })
  };
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { 
    type: 'application/json' 
  });
  
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  link.download = `measurements-${timestamp}.json`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
}
```

### Step 10: Commit and Push

```bash
# Add changes
git add static/js/ballstick_viewer.js
git add templates/ballstick_viewer.html
git add PHASE4_IMPLEMENTATION_GUIDE.md
git add PHASE4_SCOPE_REVIEW.md

# Commit
git commit -m "Add Phase 4: Angle measurements, SVG export, FPS monitor

- Implement 3-point angle measurement with visual arc
- Implement 4-point dihedral angle measurement
- Add SVG vector export for publication figures
- Add FPS counter with color-coded performance
- Add measurement mode selector UI
- Update measurements export to include angles
- Add optional video capture support
- Update documentation with Phase 4 guide"

# Push to remote
git push origin feature/phase4-angles-advanced-export
```

## Troubleshooting

### Issue: SVG export is blank
**Solution:** Ensure SVGRenderer is properly loaded. Check console for errors. Some Three.js materials may not render in SVG.

### Issue: Angle measurements show incorrect values
**Solution:** Verify vector calculations. Ensure vectors are properly normalized. Check for edge cases (collinear points).

### Issue: FPS counter shows incorrect values
**Solution:** Ensure render loop is calling updateFPS() once per frame. Check for multiple render loops.

### Issue: Dihedral angles jump between positive/negative
**Solution:** This is expected behavior for dihedrals. Consider displaying absolute value or providing sign interpretation.

## Performance Considerations

- Angle arcs add geometry to scene; limit number of active measurements
- SVG export can be slow for complex scenes; consider simplification
- FPS monitoring has minimal overhead but still requires one calculation per frame
- Video capture significantly impacts performance; consider recording at lower FPS

## Code Style

- Follow existing Three.js patterns
- Use async/await for export operations  
- Keep angle calculation functions pure
- Add comments for complex math
- Use descriptive variable names

## Resources

- [Three.js Math](https://threejs.org/docs/#api/en/math/Vector3)
- [SVGRenderer](https://threejs.org/docs/#examples/en/renderers/SVGRenderer)
- [CCapture.js](https://github.com/spite/ccapture.js/)
- [Dihedral Angle Calculation](https://en.wikipedia.org/wiki/Dihedral_angle)

## Phase 4 Completion Status

**✅ Core Features:**
- 3-point angle measurements
- 4-point dihedral measurements
- SVG vector export
- FPS monitoring
- Measurement mode selector

**⏳ Optional Features:**
- Rotated clip planes
- Video/GIF export
- 3D model export
- Batch export

**Phase 5 Candidates:**
- Surface area calculations
- Volume calculations
- Hydrogen bond visualization
- LOD rendering

---

**Questions?** Refer to DEVELOPER_GUIDE.md or create an issue in the repository.
