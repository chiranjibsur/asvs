(() => {
  // ----------------- helpers -----------------
  const $ = (id) => document.getElementById(id);
  const status = (msg) => { const s=$("status"); s.textContent = msg; };

  // Map scalar in [0,1] to blue→white→red
  function heatColor01(v) {
    const t = Math.max(0, Math.min(1, v));
    if (t < 0.5) {
      const k = t / 0.5; // 0..1
      const r = Math.round(255 * k);
      const g = Math.round(255 * k);
      const b = 255;
      return (r << 16) | (g << 8) | b;
    } else {
      const k = (t - 0.5) / 0.5; // 0..1
      const r = 255;
      const g = Math.round(255 * (1 - k));
      const b = Math.round(255 * (1 - k));
      return (r << 16) | (g << 8) | b;
    }
  }

  // ----------------- global state -----------------
  const state = {
    meta: null,
    frame: 0,
    playing: false,
    playHandle: null,

    // three.js
    renderer: null,
    scene: null,
    camera: null,
    controls: null,
    points: null,         // THREE.Points
    geometry: null,       // THREE.BufferGeometry
  };

  // ----------------- init three -----------------
  function initThree() {
    const canvas = $("viewerCanvas");
    const W = canvas.clientWidth;
    const H = canvas.clientHeight;

    state.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    state.renderer.setSize(W, H, false);

    state.scene = new THREE.Scene();
    state.scene.background = new THREE.Color(0x0f1012);

    state.camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 1000);
    state.camera.position.set(0, 0, 120);

    state.controls = new THREE.OrbitControls(state.camera, canvas);
    state.controls.enableDamping = true;

    // light
    const hemi = new THREE.HemisphereLight(0xffffff, 0x202020, 1.0);
    state.scene.add(hemi);

    // placeholder geometry; will be resized on first frame load
    state.geometry = new THREE.BufferGeometry();
    const material = new THREE.PointsMaterial({
      size: 0.7,
      vertexColors: true
    });
    state.points = new THREE.Points(state.geometry, material);
    state.scene.add(state.points);

    window.addEventListener('resize', onResize);
    onResize();
    requestAnimationFrame(loop);
  }

  function onResize() {
    if (!state.renderer) return;
    const canvas = $("viewerCanvas");
    const W = canvas.clientWidth;
    const H = Math.max(320, Math.floor(window.innerHeight - canvas.getBoundingClientRect().top - 60));
    state.renderer.setSize(W, H, false);
    state.camera.aspect = W / H;
    state.camera.updateProjectionMatrix();
  }

  function loop() {
    if (state.controls) state.controls.update();
    if (state.renderer && state.scene && state.camera) {
      state.renderer.render(state.scene, state.camera);
    }
    requestAnimationFrame(loop);
  }

  // ----------------- data fetchers -----------------
  async function fetchJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return await r.json();
  }

  async function getMeta() {
    const m = await fetchJSON('/api/trajectory/meta');
    state.meta = m;
    $("metaPill").textContent =
      `frames: ${m.n_frames} • atoms: ${m.n_atoms ?? '—'} • residues: ${m.n_residues ?? '—'}`;
    $("frameSlider").max = String(m.n_frames - 1);
    $("frameSlider").value = "0";
    $("frameLabel").textContent = "0";
  }

  async function loadFrame(n) {
    if (!state.meta) await getMeta();
    n = Math.max(0, Math.min(state.meta.n_frames - 1, n));
    state.frame = n;

    status(`loading frame ${n} …`);
    const data = await fetchJSON(`/api/trajectory/frame/${n}`);
    // data: { frame, coords: [[x,y,z], ...], hotspots: [score] }

    // prepare typed arrays
    const N = data.coords.length;
    const positions = new Float32Array(N * 3);
    const colors = new Float32Array(N * 3);

    for (let i = 0; i < N; i++) {
      const c = data.coords[i];
      positions[3*i+0] = c[0];
      positions[3*i+1] = c[1];
      positions[3*i+2] = c[2];
    }

    // one scalar for the frame; normalize against anomaly_min/max
    const s = Array.isArray(data.hotspots) && data.hotspots.length
      ? data.hotspots[0] : 0.0;

    const aMin = (state.meta.anomaly_min ?? 0.0);
    const aMax = (state.meta.anomaly_max ?? 1.0);
    const t = (aMax > aMin) ? ((s - aMin) / (aMax - aMin)) : 0.0;

    const rgb = heatColor01(t);
    const R = ((rgb >> 16) & 255) / 255;
    const G = ((rgb >> 8) & 255) / 255;
    const B = (rgb & 255) / 255;

    for (let i = 0; i < N; i++) {
      colors[3*i+0] = R;
      colors[3*i+1] = G;
      colors[3*i+2] = B;
    }

    // update or create geometry
    if (!state.geometry) {
      state.geometry = new THREE.BufferGeometry();
    }
    state.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    state.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    state.geometry.computeBoundingSphere();

    if (!state.points) {
      const material = new THREE.PointsMaterial({ size: 0.7, vertexColors: true });
      state.points = new THREE.Points(state.geometry, material);
      state.scene.add(state.points);
    } else {
      state.points.geometry = state.geometry;
    }

    $("frameSlider").value = String(n);
    $("frameLabel").textContent = String(n);
    status(`frame ${n} loaded — atoms: ${N}, hotspot: ${s.toFixed(3)} (t=${t.toFixed(3)})`);
  }

  function play() {
    if (state.playing) return;
    state.playing = true;
    $("btnPlay").disabled = true;
    $("btnPause").disabled = false;

    const step = async () => {
      if (!state.playing) return;
      const next = (state.frame + 1) % state.meta.n_frames;
      try {
        await loadFrame(next);
      } catch (e) {
        console.error(e);
        status(`error during playback: ${e.message}`);
        pause();
        return;
      }
      state.playHandle = setTimeout(step, 80); // ~12.5 fps; tweak as needed
    };
    step();
  }

  function pause() {
    state.playing = false;
    $("btnPlay").disabled = false;
    $("btnPause").disabled = true;
    if (state.playHandle) {
      clearTimeout(state.playHandle);
      state.playHandle = null;
    }
  }

  // ----------------- wire UI -----------------
  async function boot() {
    initThree();
    try {
      await getMeta();
      status('ready — click “Load frame 0” or press Play');
    } catch (e) {
      console.error(e);
      status(`meta error: ${e.message}`);
    }

    $("btnLoad").addEventListener('click', () => loadFrame(0));
    $("btnPlay").addEventListener('click', play);
    $("btnPause").addEventListener('click', pause);

    $("frameSlider").addEventListener('input', (e) => {
      const v = parseInt(e.target.value || '0', 10);
      $("frameLabel").textContent = String(v);
    });
    $("frameSlider").addEventListener('change', async (e) => {
      const v = parseInt(e.target.value || '0', 10);
      pause();
      await loadFrame(v);
    });
  }

  window.addEventListener('DOMContentLoaded', boot);
})();
