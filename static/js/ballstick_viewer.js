/* global THREE */
(async function () {
  const canvas   = document.getElementById('canvas');
  const status   = document.getElementById('status');
  const slider   = document.getElementById('slider');
  const frameLbl = document.getElementById('frameLbl');
  const btnLoad  = document.getElementById('btnLoad');
  const btnPlay  = document.getElementById('btnPlay');
  const btnPause = document.getElementById('btnPause');
  const metaPill = document.getElementById('metaPill');
  const metricSelect = document.getElementById('metricSelect');
  const metricInfo = document.getElementById('metricInfo');
  const legendTitle = document.getElementById('legendTitle');
  const legendDesc = document.getElementById('legendDesc');
  const heatmapCanvas = document.getElementById('heatmapCanvas');

  // ---- Metric Configuration ----
  const METRIC_CONFIG = {
    hotspot: {
      title: "Dynamic Hotspot",
      description: "Visualize dynamic regions of interest",
      legendDesc: "High values indicate regions of interest",
      fetchData: (frame) => fetch(`/api/hotspots/${frame}`).then(r => r.ok ? r.json() : {}),
      fetchStaticData: null,
      isFrameDependent: true
    },
    anomaly: {
      title: "Dynamic Anomaly",
      description: "Unusual motion indicative of functional transitions",
      legendDesc: "High values indicate anomalous conformations",
      fetchData: (frame) => fetch(`/api/metrics/anomaly/${frame}`).then(r => r.ok ? r.json() : {}),
      fetchStaticData: null,
      isFrameDependent: true
    },
    rmsf: {
      title: "RMSF (Flexibility)",
      description: "Root Mean Square Fluctuation - inherent flexibility",
      legendDesc: "High values indicate flexible regions",
      fetchData: null,
      fetchStaticData: () => fetch('/api/rmsf').then(r => r.ok ? r.json() : {normalized: {}}),
      isFrameDependent: false
    },
    tica: {
      title: "tICA Importance",
      description: "Contribution to slow collective motions",
      legendDesc: "High values indicate importance in collective dynamics",
      fetchData: null,
      fetchStaticData: () => fetch('/api/metrics/tica_importance').then(r => r.ok ? r.json() : {normalized: {}}),
      isFrameDependent: false
    }
  };

  let currentMetric = 'hotspot';
  let metricsCache = {
    hotspot: {},
    anomaly: {},
    rmsf: null,
    tica: null
  };

  // ---- meta ----
  const meta = await (await fetch('/api/trajectory/meta')).json();
  slider.max = meta.n_frames - 1;
  frameLbl.textContent = '0';
  metaPill.textContent = `frames: ${meta.n_frames} • atoms: ${meta.n_atoms} • residues: ${meta.n_residues}`;

  // ---- scene ----
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0c0f);

  const camera = new THREE.PerspectiveCamera(45, canvas.clientWidth / canvas.clientHeight, 0.1, 2000);
  camera.position.set(0, 0, 120);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
  dirLight.position.set(1, 1, 1);
  scene.add(dirLight);
  scene.add(new THREE.AmbientLight(0xffffff, 0.3));

  function resize () {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  // ---- Configuration Constants ----
  const MAX_UI_PLANES = 3;
  const PERFORMANCE_FPS_WARNING = 30;

  // ---- Phase 4: FPS Monitoring ----
  let showFPS = false;
  let fpsFrameCount = 0;
  let fpsLastTime = performance.now();
  let currentFPS = 0;
  let fpsUpdateInterval = 500; // Update FPS display every 500ms

  function toggleFPSDisplay() {
    showFPS = !showFPS;
    const fpsDisplay = document.getElementById('fpsDisplay');
    if (fpsDisplay) {
      fpsDisplay.style.display = showFPS ? 'block' : 'none';
    }
    return showFPS;
  }

  function updateFPS() {
    fpsFrameCount++;
    const currentTime = performance.now();
    const elapsed = currentTime - fpsLastTime;
    
    if (elapsed >= fpsUpdateInterval) {
      currentFPS = Math.round((fpsFrameCount * 1000) / elapsed);
      fpsFrameCount = 0;
      fpsLastTime = currentTime;
      
      const fpsDisplay = document.getElementById('fpsDisplay');
      if (fpsDisplay && showFPS) {
        const color = currentFPS < PERFORMANCE_FPS_WARNING ? '#ff6b6b' : '#51cf66';
        fpsDisplay.innerHTML = `FPS: <span style="color: ${color};">${currentFPS}</span>`;
      }
    }
  }

  // ---- Clip Plane Implementation ----
  let clipPlanes = [];
  let clipPlaneHelpers = [];
  let enableClipping = false;
  let showPlaneHelpers = true;

  function createClipPlane(normal = new THREE.Vector3(0, 1, 0), constant = 0) {
    const plane = new THREE.Plane(normal, constant);
    clipPlanes.push(plane);
    
    // Create visual helper
    const helper = new THREE.PlaneHelper(plane, 50, 0xffff00);
    helper.visible = enableClipping && showPlaneHelpers;
    scene.add(helper);
    clipPlaneHelpers.push(helper);
    
    // Update renderer clipping planes only if clipping is enabled
    renderer.clippingPlanes = enableClipping ? clipPlanes : [];
    renderer.localClippingEnabled = enableClipping;
    
    return clipPlanes.length - 1;
  }

  function toggleClipping() {
    enableClipping = !enableClipping;
    renderer.localClippingEnabled = enableClipping;
    renderer.clippingPlanes = enableClipping ? clipPlanes : [];
    
    clipPlaneHelpers.forEach(helper => {
      helper.visible = enableClipping && showPlaneHelpers;
    });
    
    return enableClipping;
  }

  function togglePlaneHelpers() {
    showPlaneHelpers = !showPlaneHelpers;
    clipPlaneHelpers.forEach(helper => {
      helper.visible = enableClipping && showPlaneHelpers;
    });
    return showPlaneHelpers;
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
    if (clipPlaneHelpers[index]) {
      clipPlaneHelpers[index].updateMatrixWorld();
    }
  }

  function removeClipPlane(index) {
    if (index >= clipPlanes.length) return;
    
    clipPlanes.splice(index, 1);
    
    const helper = clipPlaneHelpers[index];
    scene.remove(helper);
    clipPlaneHelpers.splice(index, 1);
    
    renderer.clippingPlanes = enableClipping ? clipPlanes : [];
  }

  function addClipPlane() {
    if (clipPlanes.length >= MAX_UI_PLANES) {
      console.warn(`Maximum of ${MAX_UI_PLANES} clip planes reached`);
      // Show warning in status area instead of alert
      if (status) {
        const oldText = status.textContent;
        status.textContent = `⚠ Maximum of ${MAX_UI_PLANES} clip planes reached`;
        status.style.color = '#ffaa00';
        setTimeout(() => {
          status.textContent = oldText;
          status.style.color = '#9aa3b2';
        }, 3000);
      }
      return -1;
    }
    return createClipPlane(new THREE.Vector3(0, 1, 0), 0);
  }

  function resetClipPlanes() {
    // Remove all planes except the first one
    while (clipPlanes.length > 1) {
      removeClipPlane(clipPlanes.length - 1);
    }
    // Reset first plane
    if (clipPlanes.length > 0) {
      updateClipPlane(0, 'y', 0);
    }
  }

  // Initialize with one clip plane
  createClipPlane(new THREE.Vector3(0, 1, 0), 0);

  // ---- Raycaster for atom selection ----
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  let selectedAtom = null;
  
  // Reusable highlight material to prevent memory leaks
  const highlightMaterial = new THREE.MeshStandardMaterial({
    color: 0xffff00,  // Yellow highlight
    emissive: 0x444400,
    metalness: 0.0,
    roughness: 0.5
  });

  // Helper to get mouse position in normalized device coordinates
  function onMouseMove(event) {
    const rect = canvas.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  }

  canvas.addEventListener('mousemove', onMouseMove, false);

  // ---- RMSF data and toggle ----
  let rmsfData = null;
  let showRMSF = false;

  async function fetchRMSF() {
    try {
      const r = await fetch('/api/rmsf');
      if (!r.ok) return null;
      return await r.json();
    } catch {
      return null;
    }
  }

  // Load RMSF on startup
  rmsfData = await fetchRMSF();

  function toggleRMSFColoring() {
    showRMSF = !showRMSF;
    
    if (showRMSF && rmsfData) {
      applyRMSFColors();
    } else {
      const currentFrame = parseInt(slider.value, 10);
      applyHotspotColors(currentFrame);
    }
  }

  function applyRMSFColors() {
    if (!rmsfData) return;
    
    const scores = rmsfData.normalized;
    
    for (let i = 0; i < atomMeshes.length; i++) {
      const rIdx = atomResidueIdx[i];
      const t = scores[String(rIdx)] || 0.0;
      atomMeshes[i].material.color.copy(colorBWR(t));
    }
  }

  // ---- atom metadata ----
  const atomInfo = await (await fetch('/api/trajectory/atoms')).json();
  const atoms = atomInfo.atoms;
  const covR  = atomInfo.covalent_radii || {};
  const hasFullBackbone = atomInfo.has_full_backbone || false;
  
  // Log backbone status for debugging
  console.log('Has full backbone data:', hasFullBackbone);
  if (!hasFullBackbone) {
    console.log('Note: Topology contains only CA atoms. Full backbone visualization is using reconstructed data.');
  }

  // ---- build atom -> residueIndex mapping (robust) ----
  async function getAtomResidueIndexArray () {
    // Preferred: dedicated endpoint
    try {
      const resp = await fetch('/api/trajectory/atom_residue_index');
      if (resp.ok) return await resp.json(); // [resIdx,...] length = n_atoms
    } catch (_) {}

    // Fallback path: need residue index per resnum + per-atom resnum list
    // 1) residue table: [{index, resnum, ...}]
    const resTbl = await (await fetch('/api/trajectory/residue_meta')).json();
    const resnumToIndex = new Map();
    for (const r of resTbl.residues) resnumToIndex.set(String(r.resnum), r.index);

    // 2) per-atom PDB resnum list
    const resmap = await (await fetch('/api/trajectory/residue_map')).json();
    const atomResnum = resmap.resnos; // array of PDB resnums (len = n_atoms)

    // 3) convert to residue indices (0-based) via the table
    return atomResnum.map(rn => {
      const idx = resnumToIndex.get(String(rn));
      return (idx == null) ? 0 : idx;
    });
  }

  const atomResidueIdx = await getAtomResidueIndexArray(); // length = n_atoms

  // ---- geometry holders ----
  const atomMeshes = [];
  const atomGeom = new THREE.SphereGeometry(0.9, 20, 20);

  // metals/roughness neutral; color set per-frame
  function makeAtomMaterial () {
    return new THREE.MeshStandardMaterial({ metalness: 0.0, roughness: 0.8 });
  }

  for (let i = 0; i < atoms.length; i++) {
    const m = new THREE.Mesh(atomGeom, makeAtomMaterial());
    // Add atom index to userData for raycasting
    m.userData.atomIndex = i;
    m.userData.element = atoms[i].element;
    m.userData.resnum = atoms[i].resnum;
    m.userData.name = atoms[i].name || '';
    m.userData.backboneType = atoms[i].backbone_type || 'sidechain';
    scene.add(m);
    atomMeshes.push(m);
  }

  // ---- bonds (simple cutoff) ----
  const bonds = [];
  const bondMaterial = new THREE.MeshStandardMaterial({ metalness: 0.0, roughness: 0.6 });
  const cylGeom = new THREE.CylinderGeometry(0.28, 0.28, 1, 10);

  function cutoff (e1, e2) {
    const r1 = covR[e1] ?? 0.76;
    const r2 = covR[e2] ?? 0.76;
    return (r1 + r2) * 1.25 + 0.25; // generous
  }

  function makeBond (i, j) {
    const mesh = new THREE.Mesh(cylGeom, bondMaterial);
    mesh.userData = { i, j };
    scene.add(mesh);
    bonds.push(mesh);
  }

  function placeBond (mesh, p, q) {
    const v1 = new THREE.Vector3(p[0], p[1], p[2]);
    const v2 = new THREE.Vector3(q[0], q[1], q[2]);
    const mid = v1.clone().add(v2).multiplyScalar(0.5);
    const dir = v2.clone().sub(v1);
    const len = dir.length();

    mesh.position.copy(mid);
    mesh.scale.set(1, 1, len);
    // orient cylinder along v1->v2
    const up = new THREE.Vector3(0, 1, 0);
    mesh.quaternion.setFromUnitVectors(up, dir.clone().normalize());
  }

  // initial xyz for bond construction
  const xyz0 = (await (await fetch('/api/trajectory/frame/0')).json()).xyz;

  // brute-force bonds (N ~ 374 → fine)
  for (let i = 0; i < atoms.length; i++) {
    for (let j = i + 1; j < atoms.length; j++) {
      const p = xyz0[i], q = xyz0[j];
      const dx = p[0] - q[0], dy = p[1] - q[1], dz = p[2] - q[2];
      const dist = Math.sqrt(dx*dx + dy*dy + dz*dz);
      const c = cutoff(atoms[i].element, atoms[j].element);
      if (dist > 0.4 && dist < c) makeBond(i, j);
    }
  }

  function updateAtoms (xyz) {
    for (let i = 0; i < atomMeshes.length; i++) {
      const m = atomMeshes[i], p = xyz[i];
      m.position.set(p[0], p[1], p[2]);
    }
    for (const b of bonds) {
      placeBond(b, xyz[b.userData.i], xyz[b.userData.j]);
    }
    // Update contact lines if visible
    if (showContacts && contactLines.length > 0) {
      updateContactLines(xyz);
    }
  }

  // ---- Contact network visualization ----
  let contactsData = null;
  let contactLines = [];
  let showContacts = false;
  const MAX_CONTACT_LINES = 50; // Maximum number of contact lines to display

  async function fetchContacts() {
    try {
      const r = await fetch('/api/contacts');
      if (!r.ok) return null;
      return await r.json();
    } catch {
      return null;
    }
  }

  // Load contacts on startup
  contactsData = await fetchContacts();

  function toggleContactNetwork() {
    showContacts = !showContacts;
    
    if (showContacts) {
      displayContactNetwork();
    } else {
      hideContactNetwork();
    }
  }

  function displayContactNetwork() {
    if (!contactsData || contactLines.length > 0) return;
    
    // Get current frame coordinates
    const currentFrame = parseInt(slider.value, 10);
    fetch(`/api/trajectory/frame/${currentFrame}`)
      .then(r => r.json())
      .then(frameData => {
        const xyz = frameData.xyz;
        
        // Create line for each contact
        const lineMaterial = new THREE.LineBasicMaterial({ 
          color: 0x00ff00, 
          transparent: true, 
          opacity: 0.3 
        });
        
        for (const contact of contactsData.contacts.slice(0, MAX_CONTACT_LINES)) {
          const res1 = contact.residue1;
          const res2 = contact.residue2;
          
          // Find atoms for these residues
          let atom1Idx = atomResidueIdx.indexOf(res1);
          let atom2Idx = atomResidueIdx.indexOf(res2);
          
          if (atom1Idx === -1 || atom2Idx === -1) continue;
          
          const p1 = xyz[atom1Idx];
          const p2 = xyz[atom2Idx];
          
          const points = [
            new THREE.Vector3(p1[0], p1[1], p1[2]),
            new THREE.Vector3(p2[0], p2[1], p2[2])
          ];
          
          const geometry = new THREE.BufferGeometry().setFromPoints(points);
          const line = new THREE.Line(geometry, lineMaterial);
          line.userData = { res1, res2 };
          
          scene.add(line);
          contactLines.push(line);
        }
      });
  }

  function hideContactNetwork() {
    for (const line of contactLines) {
      scene.remove(line);
      line.geometry.dispose();
    }
    contactLines = [];
  }

  function updateContactLines(xyz) {
    for (const line of contactLines) {
      const res1 = line.userData.res1;
      const res2 = line.userData.res2;
      
      let atom1Idx = atomResidueIdx.indexOf(res1);
      let atom2Idx = atomResidueIdx.indexOf(res2);
      
      if (atom1Idx === -1 || atom2Idx === -1) continue;
      
      const p1 = xyz[atom1Idx];
      const p2 = xyz[atom2Idx];
      
      const points = [
        new THREE.Vector3(p1[0], p1[1], p1[2]),
        new THREE.Vector3(p2[0], p2[1], p2[2])
      ];
      
      line.geometry.setFromPoints(points);
    }
  }

  // ---- Distance Measurement Tool ----
  let measurementMode = false;
  let measurementPoints = [];
  let measurementLines = [];
  let measurementMarkers = [];
  let measurements = []; // Store measurement data
  let persistMeasurements = false;

  // ---- Phase 4: Angle Measurement Tool ----
  let angleMeasurementMode = false;
  let angleMode3Point = true; // true = 3-point angle, false = 4-point dihedral
  let anglePoints = [];
  let angleArcs = []; // Visual arc representations

  function toggleMeasurementMode() {
    measurementMode = !measurementMode;
    
    // Update cursor style
    canvas.style.cursor = measurementMode ? 'crosshair' : 'default';
    
    return measurementMode;
  }

  function togglePersistMeasurements() {
    persistMeasurements = !persistMeasurements;
    return persistMeasurements;
  }

  function addMeasurementPoint(position, atomIndex) {
    measurementPoints.push({ position: position.clone(), atomIndex });
    
    // Create sphere marker
    const geometry = new THREE.SphereGeometry(0.5, 16, 16);
    const material = new THREE.MeshBasicMaterial({ color: 0xff00ff });
    const marker = new THREE.Mesh(geometry, material);
    marker.position.copy(position);
    scene.add(marker);
    measurementMarkers.push(marker);
    
    // If we have 2 points, create measurement line
    if (measurementPoints.length === 2) {
      createDistanceMeasurement();
      measurementPoints = []; // Reset for next measurement
    }
  }

  function createDistanceMeasurement() {
    const p1 = measurementPoints[0].position;
    const p2 = measurementPoints[1].position;
    const atom1 = measurementPoints[0].atomIndex;
    const atom2 = measurementPoints[1].atomIndex;
    
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
    
    // Store measurement info
    const currentFrame = parseInt(slider.value, 10);
    const measurement = {
      id: measurements.length + 1,
      atom1,
      atom2,
      distance,
      frame: currentFrame,
      unit: 'Å'
    };
    measurements.push(measurement);
    
    console.log(`Distance: ${distance.toFixed(2)} Å (Atom ${atom1} ↔ Atom ${atom2})`);
    
    // Update UI
    updateMeasurementsList();
  }

  function clearMeasurements() {
    measurementPoints = [];
    anglePoints = [];
    
    measurementLines.forEach(line => {
      scene.remove(line);
      line.geometry.dispose();
      line.material.dispose();
    });
    measurementLines = [];
    
    measurementMarkers.forEach(marker => {
      scene.remove(marker);
      marker.geometry.dispose();
      marker.material.dispose();
    });
    measurementMarkers = [];
    
    // Clear angle arcs
    angleArcs.forEach(arc => {
      scene.remove(arc);
      arc.geometry.dispose();
      arc.material.dispose();
    });
    angleArcs = [];
    
    measurements = [];
    
    // Clear UI list
    updateMeasurementsList();
  }

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
            <span style="opacity:0.7;">Atom ${m.atom1} - ${m.atom2} - ${m.atom3}</span>
            ${persistMeasurements ? `<br><span style="opacity:0.5;font-size:11px;">Frame ${m.frame}</span>` : ''}
          </div>
        `;
      } else if (m.type === 'dihedral') {
        html += `
          <div class="measurement-item">
            <strong>Dihedral:</strong> ${m.angle.toFixed(2)}${m.unit}<br>
            <span style="opacity:0.7;">Atom ${m.atom1} - ${m.atom2} - ${m.atom3} - ${m.atom4}</span>
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

  // ---- Phase 4: Angle Measurement Functions ----
  function toggleAngleMeasurementMode() {
    angleMeasurementMode = !angleMeasurementMode;
    
    // Disable distance measurement mode when angle mode is enabled
    if (angleMeasurementMode) {
      measurementMode = false;
    }
    
    // Update cursor style
    canvas.style.cursor = angleMeasurementMode ? 'crosshair' : 'default';
    
    return angleMeasurementMode;
  }

  function toggleAngleMode() {
    angleMode3Point = !angleMode3Point;
    anglePoints = []; // Reset points when changing mode
    return angleMode3Point;
  }

  function addAnglePoint(position, atomIndex) {
    anglePoints.push({ position: position.clone(), atomIndex });
    
    // Create sphere marker (green for angles)
    const geometry = new THREE.SphereGeometry(0.5, 16, 16);
    const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
    const marker = new THREE.Mesh(geometry, material);
    marker.position.copy(position);
    scene.add(marker);
    measurementMarkers.push(marker);
    
    // Check if we have enough points
    const requiredPoints = angleMode3Point ? 3 : 4;
    if (anglePoints.length === requiredPoints) {
      if (angleMode3Point) {
        create3PointAngleMeasurement();
      } else {
        create4PointDihedralMeasurement();
      }
      anglePoints = []; // Reset for next measurement
    }
  }

  function create3PointAngleMeasurement() {
    const p1 = anglePoints[0].position;
    const p2 = anglePoints[1].position; // Vertex
    const p3 = anglePoints[2].position;
    
    const atom1 = anglePoints[0].atomIndex;
    const atom2 = anglePoints[1].atomIndex; // Vertex
    const atom3 = anglePoints[2].atomIndex;
    
    // Calculate angle using vectors
    const v1 = new THREE.Vector3().subVectors(p1, p2);
    const v2 = new THREE.Vector3().subVectors(p3, p2);
    const angle = v1.angleTo(v2) * (180 / Math.PI); // Convert to degrees
    
    // Create visual arc
    createAngleArc(p1, p2, p3, angle);
    
    // Create connecting lines from vertex to endpoints
    const points1 = [p2, p1];
    const points2 = [p2, p3];
    const geometry1 = new THREE.BufferGeometry().setFromPoints(points1);
    const geometry2 = new THREE.BufferGeometry().setFromPoints(points2);
    const material = new THREE.LineBasicMaterial({ color: 0x00ff00, linewidth: 2 });
    
    const line1 = new THREE.Line(geometry1, material);
    const line2 = new THREE.Line(geometry2, material);
    scene.add(line1);
    scene.add(line2);
    measurementLines.push(line1, line2);
    
    // Store measurement info
    const currentFrame = parseInt(slider.value, 10);
    const measurement = {
      id: measurements.length + 1,
      type: 'angle',
      atom1,
      atom2, // Vertex
      atom3,
      angle,
      frame: currentFrame,
      unit: '°'
    };
    measurements.push(measurement);
    
    console.log(`Angle: ${angle.toFixed(2)}° (Atom ${atom1} - Atom ${atom2} - Atom ${atom3})`);
    
    // Update UI
    updateMeasurementsList();
  }

  function create4PointDihedralMeasurement() {
    const p1 = anglePoints[0].position;
    const p2 = anglePoints[1].position;
    const p3 = anglePoints[2].position;
    const p4 = anglePoints[3].position;
    
    const atom1 = anglePoints[0].atomIndex;
    const atom2 = anglePoints[1].atomIndex;
    const atom3 = anglePoints[2].atomIndex;
    const atom4 = anglePoints[3].atomIndex;
    
    // Calculate dihedral angle
    const b1 = new THREE.Vector3().subVectors(p2, p1);
    const b2 = new THREE.Vector3().subVectors(p3, p2);
    const b3 = new THREE.Vector3().subVectors(p4, p3);
    
    const n1 = new THREE.Vector3().crossVectors(b1, b2).normalize();
    const n2 = new THREE.Vector3().crossVectors(b2, b3).normalize();
    
    const m1 = new THREE.Vector3().crossVectors(n1, b2.normalize());
    
    const x = n1.dot(n2);
    const y = m1.dot(n2);
    
    const dihedral = Math.atan2(y, x) * (180 / Math.PI); // Signed angle in degrees
    
    // Create connecting lines
    const points = [p1, p2, p3, p4];
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({ color: 0x00ff00, linewidth: 2 });
    const line = new THREE.Line(geometry, material);
    scene.add(line);
    measurementLines.push(line);
    
    // Store measurement info
    const currentFrame = parseInt(slider.value, 10);
    const measurement = {
      id: measurements.length + 1,
      type: 'dihedral',
      atom1,
      atom2,
      atom3,
      atom4,
      angle: dihedral,
      frame: currentFrame,
      unit: '°'
    };
    measurements.push(measurement);
    
    console.log(`Dihedral: ${dihedral.toFixed(2)}° (Atom ${atom1} - ${atom2} - ${atom3} - ${atom4})`);
    
    // Update UI
    updateMeasurementsList();
  }

  function createAngleArc(p1, vertex, p3, angleDegrees) {
    // Create an arc to visualize the angle
    const v1 = new THREE.Vector3().subVectors(p1, vertex).normalize();
    const v2 = new THREE.Vector3().subVectors(p3, vertex).normalize();
    
    // Create arc curve
    const arcRadius = 3.0;
    const segments = 32;
    const points = [];
    
    for (let i = 0; i <= segments; i++) {
      const t = i / segments;
      const angle = t * angleDegrees * (Math.PI / 180);
      
      // Rotate v1 towards v2
      const rotationAxis = new THREE.Vector3().crossVectors(v1, v2).normalize();
      const point = v1.clone().applyAxisAngle(rotationAxis, angle).multiplyScalar(arcRadius).add(vertex);
      points.push(point);
    }
    
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({ color: 0x00ff00, linewidth: 2 });
    const arc = new THREE.Line(geometry, material);
    scene.add(arc);
    angleArcs.push(arc);
  }

  function clearAngleMeasurements() {
    anglePoints = [];
    
    angleArcs.forEach(arc => {
      scene.remove(arc);
      arc.geometry.dispose();
      arc.material.dispose();
    });
    angleArcs = [];
  }

  // ---- Export Functionality ----
  function exportScreenshot(format = 'png') {
    // Render the scene
    renderer.render(scene, camera);
    
    // Get canvas data
    const dataURL = canvas.toDataURL(`image/${format}`);
    
    // Create download link
    const link = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const currentFrame = parseInt(slider.value, 10);
    link.download = `molecular-view-frame${currentFrame}-${timestamp}.${format}`;
    link.href = dataURL;
    link.click();
  }

  // Phase 4: SVG Export
  function exportSVG() {
    try {
      // Create SVG string manually by converting scene geometry
      const svgWidth = canvas.clientWidth;
      const svgHeight = canvas.clientHeight;
      
      let svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg width="${svgWidth}" height="${svgHeight}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgWidth} ${svgHeight}">
  <rect width="100%" height="100%" fill="#0b0c0f"/>
  <g id="molecules">
`;
      
      // Project 3D points to 2D screen space
      const projectedAtoms = [];
      for (let i = 0; i < atomMeshes.length; i++) {
        const mesh = atomMeshes[i];
        const pos = mesh.position.clone();
        pos.project(camera);
        
        // Convert to screen coordinates
        const x = (pos.x + 1) * svgWidth / 2;
        const y = (-pos.y + 1) * svgHeight / 2;
        const z = pos.z;
        
        // Get color
        const color = '#' + mesh.material.color.getHexString();
        
        // Get radius (approximate from scale)
        const radius = mesh.scale.x * 2; // Approximate pixel radius
        
        projectedAtoms.push({ x, y, z, color, radius, visible: z < 1 });
      }
      
      // Sort by depth (back to front)
      projectedAtoms.sort((a, b) => b.z - a.z);
      
      // Draw atoms
      for (const atom of projectedAtoms) {
        if (atom.visible) {
          svgContent += `    <circle cx="${atom.x.toFixed(2)}" cy="${atom.y.toFixed(2)}" r="${atom.radius.toFixed(2)}" fill="${atom.color}" opacity="0.9"/>\n`;
        }
      }
      
      svgContent += `  </g>
</svg>`;
      
      // Create download
      const blob = new Blob([svgContent], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const currentFrame = parseInt(slider.value, 10);
      link.download = `molecular-view-frame${currentFrame}-${timestamp}.svg`;
      link.href = url;
      link.click();
      URL.revokeObjectURL(url);
      
      console.log('SVG exported successfully');
    } catch (error) {
      console.error('Error exporting SVG:', error);
      if (status) {
        status.textContent = '❌ SVG export failed';
        setTimeout(() => { status.textContent = ''; }, 3000);
      }
    }
  }

  function exportMeasurements() {
    if (measurements.length === 0) {
      console.log("No measurements to export");
      if (status) {
        const oldText = status.textContent;
        status.textContent = "ℹ No measurements to export";
        status.style.color = '#6bb6ff';
        setTimeout(() => {
          status.textContent = oldText;
          status.style.color = '#9aa3b2';
        }, 3000);
      }
      return;
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
      measurements: measurements
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

  function exportContactsData() {
    if (!contactsData) {
      console.log("No contacts data available");
      if (status) {
        const oldText = status.textContent;
        status.textContent = "ℹ No contacts data available";
        status.style.color = '#6bb6ff';
        setTimeout(() => {
          status.textContent = oldText;
          status.style.color = '#9aa3b2';
        }, 3000);
      }
      return;
    }
    
    const currentFrame = parseInt(slider.value, 10);
    const csv = convertContactsToCSV(contactsData.contacts, currentFrame);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    link.download = `contacts-frame${currentFrame}-${timestamp}.csv`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }

  function convertContactsToCSV(contacts, frame) {
    const headers = 'Residue1,Residue2,Frequency,Frame\n';
    const rows = contacts.slice(0, 50).map(c => 
      `${c.residue1},${c.residue2},${c.frequency},${frame}`
    ).join('\n');
    return headers + rows;
  }

  // ---- Colormap System ----
  let currentColormap = 'red_white_blue'; // Single colormap: Red-White-Blue
  
  const COLORMAPS = {
    red_white_blue: {
      name: 'Red-White-Blue',
      desc: 'Blue (low) → White (mid) → Red (high)',
      cssGradient: 'linear-gradient(to right, #08306b, #2171b5, #4292c6, #6baed6, #ffffff, #fb6a4a, #ef3b2c, #cb181d, #67000d)'
    }
  };

  // Red-White-Blue colormap with smooth gradient shades
  // Blue = low values, White = mid values, Red = high values
  function colorRedWhiteBlue(t) {
    t = Math.max(0, Math.min(1, t));
    const c = new THREE.Color();
    
    // Stops: dark blue -> medium blue -> light blue -> white -> light red -> medium red -> dark red
    const stops = [
      { t: 0.0, r: 0x08/255, g: 0x30/255, b: 0x6b/255 },    // Dark blue
      { t: 0.125, r: 0x21/255, g: 0x71/255, b: 0xb5/255 },  // Medium-dark blue
      { t: 0.25, r: 0x42/255, g: 0x92/255, b: 0xc6/255 },   // Medium blue
      { t: 0.375, r: 0x6b/255, g: 0xae/255, b: 0xd6/255 },  // Light-medium blue
      { t: 0.5, r: 1.0, g: 1.0, b: 1.0 },                    // White
      { t: 0.625, r: 0xfb/255, g: 0x6a/255, b: 0x4a/255 },  // Light-medium red
      { t: 0.75, r: 0xef/255, g: 0x3b/255, b: 0x2c/255 },   // Medium red
      { t: 0.875, r: 0xcb/255, g: 0x18/255, b: 0x1d/255 },  // Medium-dark red
      { t: 1.0, r: 0x67/255, g: 0x00/255, b: 0x0d/255 }     // Dark red
    ];
    
    let i = 0;
    while (i < stops.length - 1 && stops[i + 1].t < t) i++;
    
    const s1 = stops[i], s2 = stops[Math.min(i + 1, stops.length - 1)];
    const u = (t - s1.t) / (s2.t - s1.t || 1);
    
    c.setRGB(
      s1.r + u * (s2.r - s1.r),
      s1.g + u * (s2.g - s1.g),
      s1.b + u * (s2.b - s1.b)
    );
    return c;
  }

  // Get color - always uses Red-White-Blue
  function getColor(t) {
    return colorRedWhiteBlue(t);
  }

  // Set colormap and update legend
  function setColormap(name) {
    if (COLORMAPS[name]) {
      currentColormap = name;
      updateLegendColorbar();
      return true;
    }
    return false;
  }

  // Update legend colorbar based on current colormap
  function updateLegendColorbar() {
    const legendBar = document.getElementById('legendBar');
    if (legendBar && COLORMAPS[currentColormap]) {
      legendBar.style.background = COLORMAPS[currentColormap].cssGradient;
    }
  }

  // Expose colormap functions
  window.setColormap = setColormap;
  window.getColormap = () => currentColormap;
  window.getColormaps = () => Object.keys(COLORMAPS);

  // ---- Metric Data Fetching ----
  async function fetchMetricData(metric, frame) {
    const config = METRIC_CONFIG[metric];
    
    if (!config.isFrameDependent) {
      // Static data (RMSF, tICA) - load once
      if (!metricsCache[metric]) {
        const data = await config.fetchStaticData();
        metricsCache[metric] = data.normalized || data;
      }
      return metricsCache[metric];
    } else {
      // Frame-dependent data (hotspot, anomaly) - cache per frame
      if (!metricsCache[metric][frame]) {
        const data = await config.fetchData(frame);
        metricsCache[metric][frame] = data;
      }
      
      // For hotspot, if data is incomplete, compute from other metrics
      if (metric === 'hotspot') {
        const hotspotData = metricsCache[metric][frame];
        const hotspotKeys = Object.keys(hotspotData || {});
        
        // Check if hotspot data is incomplete (fewer entries than expected)
        // If so, compute hotspot as aggregate of anomaly, RMSF, and tICA
        if (hotspotKeys.length < meta.n_residues * 0.5) {
          // Load other metrics
          const anomalyData = await fetchMetricData('anomaly', frame);
          const rmsfData = await fetchMetricData('rmsf', 0);
          const ticaData = await fetchMetricData('tica', 0);
          
          // Compute aggregated hotspot score for each residue
          // Formula: hotspot = (anomaly * 0.4 + rmsf * 0.3 + tica * 0.3)
          const computedHotspot = {};
          const allKeys = new Set([
            ...Object.keys(anomalyData || {}),
            ...Object.keys(rmsfData || {}),
            ...Object.keys(ticaData || {})
          ]);
          
          for (const key of allKeys) {
            const anomaly = parseFloat(anomalyData[key]) || 0;
            const rmsf = parseFloat(rmsfData[key]) || 0;
            const tica = parseFloat(ticaData[key]) || 0;
            computedHotspot[key] = anomaly * 0.4 + rmsf * 0.3 + tica * 0.3;
          }
          
          metricsCache[metric][frame] = computedHotspot;
          return computedHotspot;
        }
      }
      
      return metricsCache[metric][frame];
    }
  }

  function updateLegend() {
    const config = METRIC_CONFIG[currentMetric];
    legendTitle.textContent = config.title;
    legendDesc.textContent = config.legendDesc;
    metricInfo.textContent = config.description;
    updateLegendColorbar();
  }

  async function updateTimelineHeatmap() {
    const ctx = heatmapCanvas.getContext('2d');
    const width = heatmapCanvas.width = heatmapCanvas.clientWidth;
    const height = heatmapCanvas.height = heatmapCanvas.clientHeight;
    
    const config = METRIC_CONFIG[currentMetric];
    
    if (!config.isFrameDependent) {
      // For static metrics, show distribution across residues
      const data = await fetchMetricData(currentMetric, 0);
      const values = Object.values(data);
      
      // Draw simple bar chart
      const barWidth = width / values.length;
      values.forEach((val, idx) => {
        const col = getColor(val);
        ctx.fillStyle = `rgb(${col.r*255}, ${col.g*255}, ${col.b*255})`;
        ctx.fillRect(idx * barWidth, 0, barWidth, height);
      });
      
    } else {
      // For frame-dependent metrics, show max value per frame
      const frameScores = [];
      for (let f = 0; f < meta.n_frames; f++) {
        try {
          const data = await fetchMetricData(currentMetric, f);
          const values = Object.values(data);
          const maxVal = values.length > 0 ? Math.max(...values) : 0;
          frameScores.push(maxVal);
        } catch (e) {
          frameScores.push(0);
        }
      }
      
      // Draw heatmap
      const barWidth = width / meta.n_frames;
      frameScores.forEach((score, idx) => {
        const col = getColor(score);
        ctx.fillStyle = `rgb(${col.r*255}, ${col.g*255}, ${col.b*255})`;
        ctx.fillRect(idx * barWidth, 0, barWidth, height);
      });
    }
    
    // Draw current frame indicator
    const currentFrame = parseInt(slider.value, 10);
    const markerX = (currentFrame / meta.n_frames) * width;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(markerX, 0);
    ctx.lineTo(markerX, height);
    ctx.stroke();
  }

  async function fetchHotspots (frame) {
    try {
      const r = await fetch(`/api/hotspots/${frame}`);
      if (!r.ok) return null;
      return await r.json(); // object with keys "0","1",...
    } catch {
      return null;
    }
  }

  async function applyMetricColors(frame) {
    const metricData = await fetchMetricData(currentMetric, frame);
    // make dense residue-indexed scores
    const scores = new Float32Array(meta.n_residues);
    for (const k in metricData) {
      const idx = parseInt(k, 10);
      if (!Number.isNaN(idx) && idx >= 0 && idx < scores.length) {
        scores[idx] = +metricData[k];
      }
    }
    for (let i = 0; i < atomMeshes.length; i++) {
      const rIdx = atomResidueIdx[i];     // 0-based residue index
      const t = scores[rIdx] ?? 0.0;      // 0..1 (use ?? to handle actual 0 values)
      atomMeshes[i].material.color.copy(getColor(t));
    }
    // Update timeline
    await updateTimelineHeatmap();
  }

  async function applyHotspotColors (frame) {
    // Legacy function - now redirects to applyMetricColors
    await applyMetricColors(frame);
  }

  // ---- initial placement ----
  updateAtoms(xyz0);
  await applyMetricColors(0);
  updateLegend();
  await updateTimelineHeatmap();

  // ---- Atom selection functions ----
  function onAtomClick(event) {
    // Update raycaster
    raycaster.setFromCamera(mouse, camera);
    
    // Check for intersections with atom meshes
    const intersects = raycaster.intersectObjects(atomMeshes, false);
    
    if (intersects.length > 0) {
      const clickedObject = intersects[0].object;
      
      // Pause playback when clicking on a molecule
      if (playing) {
        pausePlayback();
        status.textContent = 'Paused (clicked molecule)';
      }
      
      // Find the atom index from the object's userData
      if (clickedObject.userData && clickedObject.userData.atomIndex !== undefined) {
        const atomIndex = clickedObject.userData.atomIndex;
        
        // If in measurement mode, add measurement point instead of selecting
        if (measurementMode) {
          const position = clickedObject.position.clone();
          addMeasurementPoint(position, atomIndex);
        } else if (angleMeasurementMode) {
          const position = clickedObject.position.clone();
          addAnglePoint(position, atomIndex);
        } else {
          selectAtom(atomIndex);
        }
      }
    } else {
      // Clicked on empty space - deselect (only if not in measurement mode)
      if (!measurementMode && !angleMeasurementMode) {
        deselectAtom();
      }
    }
  }

  canvas.addEventListener('click', onAtomClick, false);

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
    // Find the atom mesh
    const mesh = atomMeshes[atomIndex];
    if (mesh) {
      // Save original material
      if (!mesh.userData.originalMaterial) {
        mesh.userData.originalMaterial = mesh.material;
      }
      // Apply reusable highlight material
      mesh.material = highlightMaterial;
    }
  }

  function unhighlightAtom(atomIndex) {
    const mesh = atomMeshes[atomIndex];
    if (mesh && mesh.userData.originalMaterial) {
      mesh.material = mesh.userData.originalMaterial;
      delete mesh.userData.originalMaterial;
    }
  }

  // Helper functions to generate detailed explanations for metric values
  // Based on structural biology principles and MD analysis best practices
  function getHotspotExplanation(value) {
    if (value < 0.2) {
      return `<strong>Low Activity Region</strong><br>This residue shows minimal dynamic activity in this frame. Typically indicates stable structural regions.<br><em style="font-size: 10px; opacity: 0.7;">Interpretation: Low hotspot scores suggest residues maintaining structural stability.</em>`;
    } else if (value < 0.5) {
      return `<strong>Moderate Activity</strong><br>This residue exhibits moderate dynamic behavior. May be involved in conformational flexibility or peripheral functional regions.<br><em style="font-size: 10px; opacity: 0.7;">Interpretation: Intermediate scores often found at domain interfaces or flexible loops.</em>`;
    } else if (value < 0.8) {
      return `<strong>High Activity Region</strong><br>This residue is highly dynamic and potentially functionally important. Common in binding sites, catalytic regions, or allosteric pathways.<br><em style="font-size: 10px; opacity: 0.7;">Interpretation: High scores correlate with functional hotspots (Ref: ensemble-anomaly-maps pipeline).</em>`;
    } else {
      return `<strong>Critical Hotspot</strong><br>This residue shows exceptional activity - likely central to protein function. May indicate active sites, critical binding interfaces, or key hinge regions.<br><em style="font-size: 10px; opacity: 0.7;">Interpretation: Extreme scores (>0.8) warrant detailed investigation for functional significance.</em>`;
    }
  }

  function getAnomalyExplanation(value) {
    if (value < 0.2) {
      return `<strong>Normal Conformation</strong><br>This residue adopts a typical conformation consistent with equilibrium dynamics. No unusual structural deviations detected by the ML pipeline.<br><em style="font-size: 10px; opacity: 0.7;">Method: Anomaly detection identifies deviations from typical conformational ensemble.</em>`;
    } else if (value < 0.5) {
      return `<strong>Minor Deviation</strong><br>Slight deviation from typical behavior. Could represent thermal fluctuations or minor conformational sampling within normal dynamics.<br><em style="font-size: 10px; opacity: 0.7;">Note: Moderate anomalies may reflect transient conformational states.</em>`;
    } else if (value < 0.8) {
      return `<strong>Unusual Conformation</strong><br>Significant anomalous behavior detected! May be exploring rare conformational states important for function, such as transition states or induced-fit conformations.<br><em style="font-size: 10px; opacity: 0.7;">Significance: High anomaly scores can indicate functionally relevant rare events.</em>`;
    } else {
      return `<strong>Highly Anomalous!</strong><br>Extremely unusual conformation detected by ML analysis. Possible interpretations: (1) functional transition state, (2) rare but biologically relevant conformation, (3) critical dynamic event.<br><em style="font-size: 10px; opacity: 0.7;">⚠️ Extreme anomalies should be validated with additional analysis.</em>`;
    }
  }

  function getRMSFExplanation(value) {
    if (value < 0.2) {
      return `<strong>Rigid/Stable Region</strong><br>Highly constrained with minimal fluctuation. Characteristic of structural core residues, secondary structure elements (α-helix/β-sheet), or residues critical for architecture.<br><em style="font-size: 10px; opacity: 0.7;">RMSF: Root Mean Square Fluctuation measures time-averaged positional variance.</em>`;
    } else if (value < 0.5) {
      return `<strong>Moderate Flexibility</strong><br>Shows moderate fluctuations with some conformational freedom. Typical of residues in stable loops or at secondary structure boundaries.<br><em style="font-size: 10px; opacity: 0.7;">Interpretation: Intermediate RMSF common in semi-flexible regions.</em>`;
    } else if (value < 0.8) {
      return `<strong>Flexible Region</strong><br>High flexibility with significant fluctuations. Common in surface loops, linker regions, or areas involved in conformational changes. May be functionally important for binding/catalysis.<br><em style="font-size: 10px; opacity: 0.7;">Note: High RMSF correlates with entropic contributions to binding (thermodynamics).</em>`;
    } else {
      return `<strong>Extremely Flexible</strong><br>Very high flexibility - likely in highly mobile regions (terminal ends, long loops, or intrinsically disordered regions). May be critical for adaptive functions.<br><em style="font-size: 10px; opacity: 0.7;">⚠️ Extreme RMSF (>0.8) may indicate poor sampling or genuine disorder.</em>`;
    }
  }

  function getTICAExplanation(value) {
    if (value < 0.2) {
      return `<strong>Low Collective Motion Role</strong><br>Minimal contribution to slowest collective motions. Likely moves independently or participates in fast, localized fluctuations rather than large-scale changes.<br><em style="font-size: 10px; opacity: 0.7;">tICA: Time-lagged Independent Component Analysis identifies slow collective modes.</em>`;
    } else if (value < 0.5) {
      return `<strong>Moderate Contribution</strong><br>Moderate involvement in collective dynamics. Participates in some large-scale motions but not a primary driver of slow conformational transitions.<br><em style="font-size: 10px; opacity: 0.7;">Method: tICA importance reflects contribution to slowest eigenvectors.</em>`;
    } else if (value < 0.8) {
      return `<strong>Important for Collective Motion</strong><br>Significant contribution to slow, collective protein motions! Likely involved in functionally relevant changes such as domain movements or allosteric transitions.<br><em style="font-size: 10px; opacity: 0.7;">Significance: High tICA scores indicate residues driving functional dynamics.</em>`;
    } else {
      return `<strong>Critical Driver of Dynamics</strong><br>Key player in slowest collective motions! Essential for large-scale conformational changes - likely critical for biological function, allosteric regulation, or structural transitions.<br><em style="font-size: 10px; opacity: 0.7;">⚠️ Highest tICA scores identify allosteric networks and functional hinges.</em>`;
    }
  }

  async function displayAtomInfo(atomIndex) {
    try {
      // Get atom metadata
      const atom = atoms[atomIndex];
      const residueNum = atom.resnum;
      const residueIndex = atomResidueIdx[atomIndex];
      
      // Fetch residue metadata
      const residueMeta = await fetch('/api/trajectory/residue_meta').then(r => {
        if (!r.ok) throw new Error('Failed to fetch residue metadata');
        return r.json();
      });
      const residue = residueMeta.residues.find(r => r.resnum === residueNum);
      
      if (!residue) {
        console.warn(`Residue ${residueNum} not found in metadata`);
        return;
      }
      
      // Get current frame coordinates
      const currentFrame = parseInt(slider.value, 10);
      const frameData = await fetch(`/api/trajectory/frame/${currentFrame}`).then(r => {
        if (!r.ok) throw new Error('Failed to fetch frame data');
        return r.json();
      });
      const coords = frameData.xyz[atomIndex];
      
      // Fetch all metric data for this residue
      const hotspotData = await fetchMetricData('hotspot', currentFrame);
      const anomalyData = await fetchMetricData('anomaly', currentFrame);
      const rmsfData_local = await fetchMetricData('rmsf', 0);
      const ticaData = await fetchMetricData('tica', 0);
      
      const residueIdx = String(residue.index);
      const resnumStr = String(residue.resnum);
      
      // Look up by residue INDEX first (0-based), fall back to PDB resnum
      // Use ?? instead of || to handle actual 0 values correctly
      const hotspotValue = hotspotData[residueIdx] ?? hotspotData[resnumStr] ?? 0;
      const anomalyValue = anomalyData[residueIdx] ?? anomalyData[resnumStr] ?? 0;
      const rmsfValue = rmsfData_local[residueIdx] ?? 0;
      const ticaValue = ticaData[residueIdx] ?? 0;
      
      // Generate detailed explanations for each metric
      const hotspotExplanation = getHotspotExplanation(hotspotValue);
      const anomalyExplanation = getAnomalyExplanation(anomalyValue);
      const rmsfExplanation = getRMSFExplanation(rmsfValue);
      const ticaExplanation = getTICAExplanation(ticaValue);
      
      // Get contacts for this residue
      let contactsHTML = '';
      if (contactsData) {
        const relatedContacts = contactsData.contacts.filter(c => 
          c.residue1 === residueIndex || c.residue2 === residueIndex
        ).slice(0, 3); // Top 3
        
        if (relatedContacts.length > 0) {
          const contactText = relatedContacts.map(c => {
            const otherRes = c.residue1 === residueIndex ? c.residue2 : c.residue1;
            const other = residueMeta.residues[otherRes];
            return `${other.resname}${other.resnum} (${(c.frequency*100).toFixed(0)}%)`;
          }).join(', ');
          
          contactsHTML = `
            <div class="info-section">
              <strong>Top Contacts:</strong> ${contactText}
            </div>
          `;
        }
      }
      
      // Build info HTML with scientific explanations
      const infoHTML = `
        <div class="atom-info-panel">
          <h3>Residue Metrics Analysis</h3>
          <div class="info-section">
            <strong>Atom Index:</strong> ${atomIndex}
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
          <div class="info-section" style="border-top: 1px solid #2b2f3a; padding-top: 10px; margin-top: 10px;">
            <strong>🔴 Dynamic Hotspot: ${hotspotValue.toFixed(3)}</strong><br>
            <span style="font-size: 11px; color: #9aa3b2; line-height: 1.4;">${hotspotExplanation}</span>
          </div>
          <div class="info-section">
            <strong>🟠 Dynamic Anomaly: ${anomalyValue.toFixed(3)}</strong><br>
            <span style="font-size: 11px; color: #9aa3b2; line-height: 1.4;">${anomalyExplanation}</span>
          </div>
          <div class="info-section">
            <strong>🟡 RMSF (Flexibility): ${rmsfValue.toFixed(3)}</strong><br>
            <span style="font-size: 11px; color: #9aa3b2; line-height: 1.4;">${rmsfExplanation}</span>
          </div>
          <div class="info-section">
            <strong>🟢 tICA Importance: ${ticaValue.toFixed(3)}</strong><br>
            <span style="font-size: 11px; color: #9aa3b2; line-height: 1.4;">${ticaExplanation}</span>
          </div>
          ${contactsHTML}
          <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #2b2f3a; font-size: 10px; color: #7a8394; line-height: 1.4;">
            <strong>ℹ️ Scientific Note:</strong> These interpretations are based on established structural biology principles and typical value ranges. Individual proteins may vary. For definitive functional conclusions, correlate with experimental data and structural context.
          </div>
          <button id="closeInfoBtn" class="close-btn">Close</button>
        </div>
      `;
      
      // Display the panel
      const panel = document.getElementById('infoPanel');
      panel.innerHTML = infoHTML;
      panel.style.display = 'block';
      
      // Attach close button event listener (remove any previous listener to prevent memory leaks)
      const closeBtn = document.getElementById('closeInfoBtn');
      closeBtn.removeEventListener('click', deselectAtom);
      closeBtn.addEventListener('click', deselectAtom);
    } catch (error) {
      console.error('Error displaying atom info:', error);
      hideAtomInfo();
    }
  }

  function hideAtomInfo() {
    document.getElementById('infoPanel').style.display = 'none';
  }

  // ---- Top Contacts Panel ----
  async function showTopContacts() {
    if (!contactsData) {
      alert("Contact data not available");
      return;
    }
    
    // Fetch residue metadata
    const residueMeta = await fetch('/api/trajectory/residue_meta').then(r => r.json());
    
    // Build list
    let html = '';
    for (const contact of contactsData.contacts.slice(0, 20)) { // Top 20
      const res1 = residueMeta.residues[contact.residue1];
      const res2 = residueMeta.residues[contact.residue2];
      
      if (!res1 || !res2) continue;
      
      html += `
        <div class="contact-item" onclick="selectContact(${contact.residue1}, ${contact.residue2})">
          <strong>${res1.resname}${res1.resnum}</strong> ↔ <strong>${res2.resname}${res2.resnum}</strong>
          <br>
          <span style="opacity:0.7;">Contact frequency: ${(contact.frequency * 100).toFixed(1)}%</span>
        </div>
      `;
    }
    
    document.getElementById('contactsList').innerHTML = html;
    document.getElementById('contactsPanel').style.display = 'block';
  }

  window.selectContact = function(res1, res2) {
    // Find and highlight both residues
    for (let i = 0; i < atomMeshes.length; i++) {
      const rIdx = atomResidueIdx[i];
      if (rIdx === res1 || rIdx === res2) {
        highlightAtom(i);
      }
    }
  };

  // ---- playback / loading ----
  let playing = false, fi = 0, rafId;
  let playbackSpeed = 0.5; // Default to 0.5x speed (slower)
  let lastFrameTime = 0;
  const BASE_FRAME_DELAY = 200; // Base delay in ms at 1x speed

  // Pause playback function (exposed for click-to-pause)
  function pausePlayback() {
    if (playing) {
      playing = false;
      btnPause.disabled = true;
      btnPlay.disabled = false;
      if (rafId) cancelAnimationFrame(rafId);
    }
  }

  // Set playback speed (0.25 to 2.0)
  function setPlaybackSpeed(speed) {
    playbackSpeed = Math.max(0.25, Math.min(2.0, speed));
    return playbackSpeed;
  }

  async function loadFrame (idx) {
    status.textContent = `loading frame ${idx}…`;
    const { xyz } = await (await fetch(`/api/trajectory/frame/${idx}`)).json();
    updateAtoms(xyz);
    if (showRMSF && rmsfData) {
      applyRMSFColors();
    } else {
      await applyMetricColors(idx);
    }
    status.textContent = `frame ${idx} loaded`;
  }

  btnLoad.onclick = () => loadFrame(parseInt(slider.value, 10));

  slider.oninput = e => {
    const v = +e.target.value;
    frameLbl.textContent = String(v);
    if (!playing) loadFrame(v);
  };

  btnPlay.onclick = () => {
    if (playing) return;
    playing = true;
    btnPlay.disabled = true;
    btnPause.disabled = false;
    lastFrameTime = performance.now();
    
    const tick = async (currentTime) => {
      if (!playing) return;
      
      const elapsed = currentTime - lastFrameTime;
      const frameDelay = BASE_FRAME_DELAY / playbackSpeed;
      
      if (elapsed >= frameDelay) {
        await loadFrame(fi);
        slider.value = String(fi);
        frameLbl.textContent = String(fi);
        fi = (fi + 1) % meta.n_frames;
        lastFrameTime = currentTime;
      }
      
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
  };

  btnPause.onclick = pausePlayback;

  // Reload current frame with current colormap/metric settings
  async function reloadCurrentFrame() {
    const currentFrame = parseInt(slider.value, 10);
    await applyMetricColors(currentFrame);
  }

  // Expose playback controls
  window.pausePlayback = pausePlayback;
  window.setPlaybackSpeed = setPlaybackSpeed;
  window.getPlaybackSpeed = () => playbackSpeed;
  window.reloadCurrentFrame = reloadCurrentFrame;

  // ---- Metric selector and timeline handlers ----
  metricSelect.addEventListener('change', async () => {
    currentMetric = metricSelect.value;
    updateLegend();
    const currentFrame = parseInt(slider.value, 10);
    await applyMetricColors(currentFrame);
  });

  heatmapCanvas.addEventListener('click', (e) => {
    const rect = heatmapCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const fraction = x / rect.width;
    const targetFrame = Math.floor(fraction * meta.n_frames);
    slider.value = String(targetFrame);
    frameLbl.textContent = String(targetFrame);
    loadFrame(targetFrame);
  });

  // Expose functions to global scope for button handlers
  window.toggleRMSFColoring = toggleRMSFColoring;
  window.toggleContactNetwork = toggleContactNetwork;
  window.showTopContacts = showTopContacts;
  
  // Phase 3 functions
  window.toggleClipping = toggleClipping;
  window.togglePlaneHelpers = togglePlaneHelpers;
  window.updateClipPlane = updateClipPlane;
  window.addClipPlane = addClipPlane;
  window.removeClipPlane = removeClipPlane;
  window.resetClipPlanes = resetClipPlanes;
  window.toggleMeasurementMode = toggleMeasurementMode;
  window.togglePersistMeasurements = togglePersistMeasurements;
  window.clearMeasurements = clearMeasurements;
  window.toggleAngleMeasurementMode = toggleAngleMeasurementMode;
  window.toggleAngleMode = toggleAngleMode;
  window.getAngleMode = () => angleMode3Point; // Export angle mode getter
  window.toggleFPSDisplay = toggleFPSDisplay;
  window.exportScreenshot = exportScreenshot;
  window.exportSVG = exportSVG;
  window.exportMeasurements = exportMeasurements;
  window.exportContactsData = exportContactsData;

  (function renderLoop () {
    controls.update();
    renderer.render(scene, camera);
    updateFPS(); // Phase 4: Update FPS counter
    requestAnimationFrame(renderLoop);
  })();
})();
