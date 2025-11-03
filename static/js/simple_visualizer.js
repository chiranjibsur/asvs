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
