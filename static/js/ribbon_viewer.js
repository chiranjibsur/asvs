/* global THREE */
(async function () {
  const canvas   = document.getElementById('canvas');
  const slider   = document.getElementById('slider');
  const frameLbl = document.getElementById('frameLbl');
  const status   = document.getElementById('status');
  const btnPlay  = document.getElementById('btnPlay');
  const btnPause = document.getElementById('btnPause');

  // --- meta / counts ---
  const meta = await (await fetch('/api/trajectory/meta')).json();
  slider.max = meta.n_frames - 1;
  frameLbl.textContent = '0';

  // --- residue order (for mapping CA order -> residue number) ---
  // Expect: { residues: [{index, resnum, resname, chain}, ...] }
  const residueMeta = await (await fetch('/api/trajectory/residue_meta')).json();
  const resnumsInOrder = residueMeta.residues.map(r => String(r.resnum)); // string keys for hotspot JSON

  // --- scene setup ---
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  const scene    = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0c0f);

  const camera = new THREE.PerspectiveCamera(
    45, canvas.clientWidth / canvas.clientHeight, 0.1, 4000
  );
  camera.position.set(0, 0, 180);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  scene.add(new THREE.DirectionalLight(0xffffff, 1.2)).position.set(1, 1, 1);
  scene.add(new THREE.AmbientLight(0xffffff, 0.3));

  function resize () {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  // ---- Raycaster for residue selection ----
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  let selectedResidue = null;

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
    const currentFrame = parseInt(slider.value, 10);
    loadRibbon(currentFrame);
  }

  // --- color helpers (blue → white → red) ---
  function colorFromScore (s) {
    const t = Math.max(0, Math.min(1, +s || 0));
    const c = new THREE.Color();
    if (t <= 0.5) {
      const k = t / 0.5;                // 0..1
      c.setRGB(k, k, 1);                // (0,0,1) → (1,1,1)
    } else {
      const k = (t - 0.5) / 0.5;        // 0..1
      c.setRGB(1, 1 - 0.2 * k, 1 - k);  // (1,1,1) → (1,0.8,0) → (1,0,0)
    }
    return c;
  }

  async function fetchHotspots (frame) {
    try {
      const r = await fetch(`/api/hotspots/${frame}`);
      if (!r.ok) return {};
      return await r.json();  // keys are strings (resnum or index)
    } catch {
      return {};
    }
  }

  let tube;
  let caPositions = []; // Store CA positions for interaction
  let currentHotspots = {}; // Store current hotspot data
  
  async function loadRibbon (frame) {
    status.textContent = `loading ribbon frame ${frame}…`;

    // 1) ordered Cα coordinates
    const ca = (await (await fetch(`/api/trajectory/ca/${frame}`)).json()).ca; // [[x,y,z], ...]
    caPositions = ca; // Store for click detection
    
    // 2) per-residue hotspot scores or RMSF
    let scoreData = {};
    if (showRMSF && rmsfData) {
      scoreData = rmsfData.normalized;
    } else {
      const hs = await fetchHotspots(frame);                                     // { "42": 0.71, ... }
      currentHotspots = hs; // Store for display
      scoreData = hs;
    }

    // build curve through Cα
    const pts   = ca.map(p => new THREE.Vector3(p[0], p[1], p[2]));
    const curve = new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.1);

    // geometry: tube with vertex colors
    if (tube) { scene.remove(tube); tube.geometry.dispose(); tube.material.dispose(); }
    const tubularSegments = Math.max(120, pts.length * 4);
    const radius = 1.2, radialSegments = 12;
    const geom = new THREE.TubeGeometry(curve, tubularSegments, radius, radialSegments, false);

    // map each ring of the tube (along the path) to the nearest residue index
    const rings = tubularSegments + 1; // tube has this many rings along path
    const colors = new Float32Array(geom.attributes.position.count * 3);

    function scoreForRing (ringIdx) {
      // nearest residue index in [0, resnumsInOrder.length-1]
      const ridx = Math.round(ringIdx / (rings - 1) * (resnumsInOrder.length - 1));
      
      if (showRMSF && rmsfData) {
        // For RMSF, use 0-based index
        return scoreData[String(ridx)] ?? 0.0;
      } else {
        // For hotspots, use resnum
        const resnumKey = resnumsInOrder[ridx];        // prefer PDB resnum
        const s = scoreData[resnumKey] ?? scoreData[String(ridx+1)]  // fallback: 1-based index
                                 ?? scoreData[String(ridx)]   // fallback: 0-based index
                                 ?? 0.0;
        return s;
      }
    }

    // paint each vertex by its ring’s score
    for (let ring = 0; ring < rings; ring++) {
      const s = scoreForRing(ring);
      const col = colorFromScore(s);
      for (let j = 0; j < radialSegments + 1; j++) {
        const idx = (ring * (radialSegments + 1) + j) * 3;
        colors[idx + 0] = col.r;
        colors[idx + 1] = col.g;
        colors[idx + 2] = col.b;
      }
    }
    geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, metalness: 0.1, roughness: 0.5 });
    tube = new THREE.Mesh(geom, mat);
    scene.add(tube);

    status.textContent = `frame ${frame} loaded`;
  }

  // ---- Residue selection functions ----
  function onRibbonClick(event) {
    // Update raycaster
    raycaster.setFromCamera(mouse, camera);
    
    // Check for intersections with the tube
    if (!tube) return;
    
    const intersects = raycaster.intersectObject(tube, false);
    
    if (intersects.length > 0) {
      const point = intersects[0].point;
      
      // Find the closest C-alpha to the clicked point
      let closestIndex = 0;
      let minDist = Infinity;
      
      for (let i = 0; i < caPositions.length; i++) {
        const ca = caPositions[i];
        const dx = point.x - ca[0];
        const dy = point.y - ca[1];
        const dz = point.z - ca[2];
        const dist = Math.sqrt(dx*dx + dy*dy + dz*dz);
        
        if (dist < minDist) {
          minDist = dist;
          closestIndex = i;
        }
      }
      
      selectResidue(closestIndex);
    } else {
      // Clicked on empty space - deselect
      deselectResidue();
    }
  }

  canvas.addEventListener('click', onRibbonClick, false);

  function selectResidue(residueIndex) {
    selectedResidue = residueIndex;
    displayResidueInfo(residueIndex);
  }

  function deselectResidue() {
    selectedResidue = null;
    hideResidueInfo();
  }

  async function displayResidueInfo(residueIndex) {
    try {
      // Get residue metadata
      const residue = residueMeta.residues[residueIndex];
      
      if (!residue) {
        console.warn(`Residue ${residueIndex} not found in metadata`);
        return;
      }
      
      // Get current frame coordinates
      const currentFrame = parseInt(slider.value, 10);
      const coords = caPositions[residueIndex];
      
      // Get hotspot data for this residue
      const resnumKey = String(residue.resnum);
      const hotspotValue = currentHotspots[resnumKey] 
                        ?? currentHotspots[String(residueIndex+1)] 
                        ?? currentHotspots[String(residueIndex)] 
                        ?? 0;
      
      // Get RMSF value
      let rmsfHTML = '';
      if (rmsfData && rmsfData.normalized) {
        const rmsfValue = rmsfData.normalized[String(residueIndex)] || 0;
        const actualRMSF = rmsfData.min + (rmsfValue * (rmsfData.max - rmsfData.min));
        rmsfHTML = `
          <div class="info-section">
            <strong>RMSF (Flexibility):</strong> ${actualRMSF.toFixed(2)} Å
          </div>
        `;
      }
      
      // Build info HTML
      const infoHTML = `
        <div class="residue-info-panel">
          <h3>Residue Information</h3>
          <div class="info-section">
            <strong>Residue:</strong> ${residue.resname}${residue.resnum} (Chain ${residue.chain})
          </div>
          <div class="info-section">
            <strong>Index:</strong> ${residueIndex}
          </div>
          <div class="info-section">
            <strong>C-alpha Coordinates:</strong><br>
            X: ${coords[0].toFixed(2)} Å<br>
            Y: ${coords[1].toFixed(2)} Å<br>
            Z: ${coords[2].toFixed(2)} Å
          </div>
          <div class="info-section">
            <strong>Hotspot Score:</strong> ${hotspotValue.toFixed(3)}
          </div>
          ${rmsfHTML}
          <button id="closeInfoBtn" class="close-btn">Close</button>
        </div>
      `;
      
      // Display the panel
      const panel = document.getElementById('infoPanel');
      panel.innerHTML = infoHTML;
      panel.style.display = 'block';
      
      // Attach close button event listener
      const closeBtn = document.getElementById('closeInfoBtn');
      closeBtn.removeEventListener('click', deselectResidue);
      closeBtn.addEventListener('click', deselectResidue);
    } catch (error) {
      console.error('Error displaying residue info:', error);
      hideResidueInfo();
    }
  }

  function hideResidueInfo() {
    const panel = document.getElementById('infoPanel');
    if (panel) panel.style.display = 'none';
  }

  // UI wiring
  slider.oninput = e => { frameLbl.textContent = e.target.value; loadRibbon(+e.target.value); };

  let playing = false, fi = 0, raf;
  btnPlay.onclick = () => {
    if (playing) return;
    playing = true; btnPause.disabled = false;
    const loop = async () => {
      if (!playing) return;
      await loadRibbon(fi);
      fi = (fi + 1) % meta.n_frames;
      raf = requestAnimationFrame(loop);
    };
    loop();
  };
  btnPause.onclick = () => { playing = false; btnPause.disabled = true; cancelAnimationFrame(raf); };

  // Expose toggleRMSFColoring to global scope for button handler
  window.toggleRMSFColoring = toggleRMSFColoring;

  // initial render
  await loadRibbon(0);
  (function render () { controls.update(); renderer.render(scene, camera); requestAnimationFrame(render); })();
})();
