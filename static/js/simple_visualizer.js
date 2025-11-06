/* simple_visualizer.js — per-residue dynamic coloring with points geometry */
(async function () {
  const canvas = document.getElementById("viewerCanvas");
  const statusEl = document.getElementById("status");
  const metaPill = document.getElementById("metaPill");
  const slider = document.getElementById("frameSlider");
  const frameLabel = document.getElementById("frameLabel");
  const btnLoad = document.getElementById("btnLoad");
  const btnPlay = document.getElementById("btnPlay");
  const btnPause = document.getElementById("btnPause");
  const tooltip = document.getElementById("tooltip");

  const toHex = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, "0");

  function colorFromScore01(s) {
    // clamp 0..1
    const t = Math.max(0, Math.min(1, s));
    // blue (0,0,1) -> white (1,1,1) -> red (1,0,0)
    // piecewise lerp
    let r, g, b;
    if (t <= 0.5) {
      const u = t / 0.5; // 0..1
      r = u; g = u; b = 1; // towards white
    } else {
      const u = (t - 0.5) / 0.5; // 0..1
      r = 1; g = 1 - u; b = 1 - u; // white to red
    }
    return { r, g, b }; // 0..1 components
  }

  async function getJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.json();
  }

  // --- fetch meta + residue map + optional residue table  -------------------
  const meta = await getJSON("/api/trajectory/meta");
  const resMapObj = await getJSON("/api/trajectory/residue_map");
  const residueMap = resMapObj.resnos; // array len = n_atoms

  let residueMeta = [];
  try {
    const rm = await getJSON("/api/trajectory/residue_meta");
    residueMeta = rm.residues || [];
  } catch (e) {
    // optional; ignore if 404
  }

  metaPill.textContent = `frames: ${meta.n_frames} • atoms: ${meta.n_atoms} • residues: ${meta.n_residues}`;
  slider.max = String(meta.n_frames - 1);
  slider.value = "0";
  frameLabel.textContent = "0";

  // --- Three.js scene -------------------------------------------------------
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0c0f);

  const camera = new THREE.PerspectiveCamera(35, canvas.clientWidth / canvas.clientHeight, 0.1, 10000);
  camera.position.set(0, 0, 180);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  const light = new THREE.AmbientLight(0xffffff, 1.0);
  scene.add(light);

  let points = null;      // THREE.Points
  let geometry = null;    // THREE.BufferGeometry
  let colorAttr = null;   // Float32Array attribute (per-vertex RGB)
  let currentHotspots = {}; // Store current hotspot data for selection

  // ---- Raycaster for atom/residue selection ----
  const raycaster = new THREE.Raycaster();
  raycaster.params.Points.threshold = 0.8; // Increase point picking threshold
  const mouse = new THREE.Vector2();
  let selectedAtom = null;

  // Helper to get mouse position in normalized device coordinates
  function onMouseMove(event) {
    const rect = canvas.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  }

  canvas.addEventListener('mousemove', onMouseMove, false);

  // --- fetching helpers -----------------------------------------------------
  async function fetchFrameXYZ(frame) {
    const j = await getJSON(`/api/trajectory/frame/${frame}`);
    return j.xyz; // [[x,y,z]...]
  }
  async function fetchHotspots(frame) {
    return getJSON(`/api/hotspots/${frame}`); // { "1":score, ... }
  }

  // --- build / update points ------------------------------------------------
  async function loadFrame(frame) {
    statusEl.textContent = `loading frame ${frame}…`;

    const [xyz, hotspots] = await Promise.all([
      fetchFrameXYZ(frame),
      fetchHotspots(frame)
    ]);

    // Build a mapping residueNumber(string) -> score
    // hotspots keys are strings "1".."N"
    const hmap = hotspots; // already string keyed
    currentHotspots = hotspots; // Store for selection
    const nAtoms = xyz.length;

    if (!geometry) {
      geometry = new THREE.BufferGeometry();
      const pos = new Float32Array(nAtoms * 3);
      geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      const colors = new Float32Array(nAtoms * 3);
      colorAttr = new THREE.BufferAttribute(colors, 3);
      geometry.setAttribute("color", colorAttr);

      const material = new THREE.PointsMaterial({ size: 1.6, vertexColors: true });
      points = new THREE.Points(geometry, material);
      scene.add(points);
    }

    // fill positions & colors
    const posArr = geometry.attributes.position.array;
    const colArr = colorAttr.array;

    for (let i = 0; i < nAtoms; i++) {
      const [x, y, z] = xyz[i];
      const resnum = String(residueMap[i]); // PDB residue number as string
      const s = hmap[resnum] !== undefined ? hmap[resnum] : 0.0;
      const { r, g, b } = colorFromScore01(s);

      const p = i * 3;
      posArr[p] = x; posArr[p + 1] = y; posArr[p + 2] = z;
      colArr[p] = r; colArr[p + 1] = g; colArr[p + 2] = b;
    }

    geometry.attributes.position.needsUpdate = true;
    geometry.attributes.color.needsUpdate = true;
    geometry.computeBoundingSphere();

    statusEl.textContent = `frame ${frame} loaded`;
  }

  // ---- Atom/Residue selection functions ----
  function onPointClick(event) {
    // Update raycaster
    raycaster.setFromCamera(mouse, camera);
    
    // Check for intersections with points
    if (!points) return;
    
    const intersects = raycaster.intersectObject(points, false);
    
    if (intersects.length > 0) {
      const atomIndex = intersects[0].index;
      selectAtom(atomIndex);
    } else {
      // Clicked on empty space - deselect
      deselectAtom();
    }
  }

  canvas.addEventListener('click', onPointClick, false);

  function selectAtom(atomIndex) {
    selectedAtom = atomIndex;
    displayAtomInfo(atomIndex);
  }

  function deselectAtom() {
    selectedAtom = null;
    hideAtomInfo();
  }

  async function displayAtomInfo(atomIndex) {
    try {
      // Get atom residue number
      const resnum = residueMap[atomIndex];
      const resnumStr = String(resnum);
      
      // Find residue in metadata
      let residue = null;
      if (residueMeta.length > 0) {
        residue = residueMeta.find(r => r.resnum === resnum);
      }
      
      // Get current frame
      const currentFrame = parseInt(slider.value, 10);
      
      // Get coordinates
      const posArr = geometry.attributes.position.array;
      const p = atomIndex * 3;
      const coords = [posArr[p], posArr[p + 1], posArr[p + 2]];
      
      // Get hotspot score
      const hotspotValue = currentHotspots[resnumStr] || 0;
      
      // Build info HTML
      let residueInfo = '';
      if (residue) {
        residueInfo = `<strong>Residue:</strong> ${residue.resname}${residue.resnum} (Chain ${residue.chain})`;
      } else {
        residueInfo = `<strong>Residue Number:</strong> ${resnum}`;
      }
      
      const infoHTML = `
        <div class="atom-info-panel">
          <h3>Atom Information</h3>
          <div class="info-section">
            <strong>Atom Index:</strong> ${atomIndex}
          </div>
          <div class="info-section">
            ${residueInfo}
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
          <button id="closeInfoBtn" class="close-btn">Close</button>
        </div>
      `;
      
      // Display the panel
      const panel = document.getElementById('infoPanel');
      panel.innerHTML = infoHTML;
      panel.style.display = 'block';
      
      // Attach close button event listener
      const closeBtn = document.getElementById('closeInfoBtn');
      closeBtn.removeEventListener('click', deselectAtom);
      closeBtn.addEventListener('click', deselectAtom);
    } catch (error) {
      console.error('Error displaying atom info:', error);
      hideAtomInfo();
    }
  }

  function hideAtomInfo() {
    const panel = document.getElementById('infoPanel');
    if (panel) panel.style.display = 'none';
  }

  // --- render loop ----------------------------------------------------------
  function onResize() {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", onResize);

  function tick() {
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(tick);
  }
  tick();

  // --- UI wiring ------------------------------------------------------------
  let playing = false;
  let playHandle = null;

  btnLoad.addEventListener("click", async () => {
    const f = parseInt(slider.value, 10);
    frameLabel.textContent = String(f);
    await loadFrame(f);
  });

  slider.addEventListener("input", async (e) => {
    const f = parseInt(e.target.value, 10);
    frameLabel.textContent = String(f);
    if (!playing) await loadFrame(f);
  });

  btnPlay.addEventListener("click", async () => {
    if (playing) return;
    playing = true;
    btnPlay.disabled = true;
    btnPause.disabled = false;

    let f = parseInt(slider.value, 10);
    const maxF = parseInt(slider.max, 10);

    const step = async () => {
      if (!playing) return;
      await loadFrame(f);
      slider.value = String(f);
      frameLabel.textContent = String(f);
      f = (f + 1) % (maxF + 1);
      playHandle = setTimeout(step, 110); // ~9 fps; smooth enough
    };
    step();
  });

  btnPause.addEventListener("click", () => {
    playing = false;
    btnPlay.disabled = false;
    btnPause.disabled = true;
    if (playHandle) { clearTimeout(playHandle); playHandle = null; }
  });

  // Auto-load frame 0 on init
  await loadFrame(0);
})();
