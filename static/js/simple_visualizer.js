(() => {
  // =============== tiny helpers ===============
  const $ = (id) => document.getElementById(id);
  const status = (msg) => { const s = $("status"); if (s) s.textContent = msg; };

  // Legend labels (we keep fixed 0..1 for now)
  function setLegend(min, max) {
    const lmin = $("legendMin");
    const lmax = $("legendMax");
    if (lmin) lmin.textContent = Number(min).toFixed(2);
    if (lmax) lmax.textContent = Number(max).toFixed(2);
  }

  // Blue(0) → White(0.5) → Red(1)
  function heatColor01(v) {
    const t = Math.max(0, Math.min(1, v));
    if (t <= 0.5) {
      const k = t / 0.5;
      const r = Math.round(255 * k);
      const g = Math.round(255 * k);
      const b = 255;
      return (r << 16) | (g << 8) | b;
    } else {
      const k = (t - 0.5) / 0.5;
      const r = 255;
      const g = Math.round(255 * (1 - k));
      const b = Math.round(255 * (1 - k));
      return (r << 16) | (g << 8) | b;
    }
  }

  // =============== global state ===============
  const state = {
    meta: null,
    frame: 0,

    // Playback
    playing: false,
    nextAt: 0,           // ms timestamp for next frame
    fps: 12,             // default ~12 fps
    playRAF: null,

    // three.js
    renderer: null,
    scene: null,
    camera: null,
    controls: null,

    // geometry
    points: null,
    geometry: null,
    posAttr: null,
    colorAttr: null,
    lastGeomSize: 0,

    // data caches
    residueMap: null,          // [atomIndex] -> residueIndex (0-based)
    lastScores: null,          // dict: resid(str) -> score for current frame

    // picking & tooltip
    raycaster: null,
    pointer: new THREE.Vector2(),
    tooltipEl: null,
    picked: null,              // { atom, resid, score }
  };

  // =============== init three.js ===============
  function initThree() {
    const canvas = $("viewerCanvas");
    const W = canvas.clientWidth;
    const H = Math.max(320, Math.floor(window.innerHeight - canvas.getBoundingClientRect().top - 60));

    state.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    state.renderer.setSize(W, H, false);

    state.scene = new THREE.Scene();
    state.scene.background = new THREE.Color(0x0f1012);

    state.camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 1000);
    state.camera.position.set(0, 0, 120);

    state.controls = new THREE.OrbitControls(state.camera, canvas);
    state.controls.enableDamping = true;

    // lights
    state.scene.add(new THREE.HemisphereLight(0xffffff, 0x202020, 1.0));

    // geometry + material for points (sizeAttenuation helps picking feel natural)
    state.geometry = new THREE.BufferGeometry();
    const material = new THREE.PointsMaterial({
      size: 1.0,
      sizeAttenuation: true,
      vertexColors: true
    });
    state.points = new THREE.Points(state.geometry, material);
    state.scene.add(state.points);

    // picking
    state.raycaster = new THREE.Raycaster();
    state.raycaster.params.Points = { threshold: 6 }; // pixels of tolerance
    state.tooltipEl = $("tooltip");

    window.addEventListener('resize', onResize);
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

  // =============== fetch helpers ===============
  async function fetchJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText} @ ${url}`);
    return await r.json();
  }

  async function getMeta() {
    const m = await fetchJSON('/api/trajectory/meta');
    state.meta = m;
    const pill = $("metaPill");
    if (pill) pill.textContent =
      `frames: ${m.n_frames} • atoms: ${m.n_atoms ?? '—'} • residues: ${m.n_residues ?? '—'}`;

    const slider = $("frameSlider");
    if (slider) {
      slider.max = String(m.n_frames - 1);
      slider.value = "0";
    }
    const label = $("frameLabel");
    if (label) label.textContent = "0";
  }

  async function getResidueMap() {
    const map = await fetchJSON('/api/trajectory/residue_map'); // {resnos:[...]}
    if (!map.resnos || !Array.isArray(map.resnos)) throw new Error('invalid residue_map payload');
    state.residueMap = map.resnos.map(Number);
    console.log('[viewer] residue map:', state.residueMap.length, 'atoms');
  }

  // =============== buffers ===============
  function ensureGeometryCapacity(N) {
    if (state.lastGeomSize === N && state.posAttr && state.colorAttr) return;
    state.posAttr  = new THREE.BufferAttribute(new Float32Array(N * 3), 3);
    state.colorAttr= new THREE.BufferAttribute(new Float32Array(N * 3), 3);
    state.geometry.setAttribute('position', state.posAttr);
    state.geometry.setAttribute('color', state.colorAttr);
    state.geometry.computeBoundingSphere();
    state.lastGeomSize = N;
  }

  // =============== frame loader (per-residue coloring) ===============
  async function loadFrame(n) {
    if (!state.meta)        await getMeta();
    if (!state.residueMap)  await getResidueMap();

    const maxF = state.meta.n_frames - 1;
    n = Math.max(0, Math.min(maxF, n));
    state.frame = n;

    // coords
    const data = await fetchJSON(`/api/trajectory/frame/${n}`);  // { frame, coords: [[x,y,z], ...] }
    const N = data.coords.length;
    ensureGeometryCapacity(N);

    // positions
    const pos = state.posAttr.array;
    for (let i = 0; i < N; i++) {
      const c = data.coords[i]; const j = 3 * i;
      pos[j] = c[0]; pos[j+1] = c[1]; pos[j+2] = c[2];
    }
    state.posAttr.needsUpdate = true;

    // scores (dict with "0".."nres-1")
    const scores = await fetchJSON(`/api/hotspots/${n}`);
    state.lastScores = scores;

    // set legend (fixed 0..1 for now)
    setLegend(0.0, 1.0);

    // colorize by residue
    const colors = state.colorAttr.array;
    const resmap = state.residueMap;
    for (let i = 0; i < N; i++) {
      const resid = resmap[i];
      const key = String(resid);
      const s = scores.hasOwnProperty(key) ? Number(scores[key]) : 0.0;
      const rgb = heatColor01(s);
      const R = ((rgb >> 16) & 255) / 255;
      const G = ((rgb >> 8) & 255) / 255;
      const B = (rgb & 255) / 255;
      const j = 3 * i;
      colors[j] = R; colors[j+1] = G; colors[j+2] = B;
    }
    state.colorAttr.needsUpdate = true;

    // UI
    const slider = $("frameSlider"); if (slider) slider.value = String(n);
    const label  = $("frameLabel");  if (label)  label.textContent = String(n);
    status(`frame ${n} loaded`);
  }

  // =============== picking (hover + click) ===============
  function onPointerMove(ev) {
    if (!state.renderer || !state.camera || !state.points) return;
    const rect = state.renderer.domElement.getBoundingClientRect();
    state.pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    state.pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;

    state.raycaster.setFromCamera(state.pointer, state.camera);
    const hits = state.raycaster.intersectObject(state.points, true);
    if (hits.length === 0) {
      hideTooltip();
      state.picked = null;
      return;
    }

    const hit = hits[0];
    const atom = hit.index;                         // atom index within this Points geometry
    const resid = state.residueMap ? state.residueMap[atom] : undefined;
    const score = (state.lastScores && resid != null) ? Number(state.lastScores[String(resid)]) : undefined;

    state.picked = { atom, resid, score };

    const tip = `atom: ${atom}${resid!=null?` • resid: ${resid}`:''}${score!=null?` • score: ${score.toFixed(3)}`:''}`;
    showTooltip(tip, ev.clientX, ev.clientY);
  }

  function onClick(ev) {
    // reuse current hover pick; if you want a “click freezes tooltip” behaviour, keep it visible.
    if (!state.picked) return;
    const { atom, resid, score } = state.picked;
    const tip = `ATOM ${atom}\nRESID ${resid != null ? resid : '—'}\nSCORE ${score != null ? score.toFixed(4) : '—'}`;
    showTooltip(tip.replace(/\n/g, ' • '), ev.clientX, ev.clientY, true);
  }

  function showTooltip(text, clientX, clientY, sticky = false) {
    const el = state.tooltipEl; if (!el) return;
    el.style.display = 'block';
    el.textContent = text;
    // position near cursor, keep inside viewport
    const pad = 12;
    const vw = window.innerWidth, vh = window.innerHeight;
    let x = clientX + 14, y = clientY + 16;
    const rect = el.getBoundingClientRect();
    if (x + rect.width + pad > vw) x = vw - rect.width - pad;
    if (y + rect.height + pad > vh) y = vh - rect.height - pad;
    el.style.left = `${x}px`;
    el.style.top  = `${y}px`;
    if (!sticky) {
      // hide after short delay unless mouse still moves
      clearTimeout(el._hideT);
      el._hideT = setTimeout(() => { el.style.display = 'none'; }, 900);
    } else {
      clearTimeout(el._hideT);
    }
  }

  function hideTooltip() {
    const el = state.tooltipEl; if (!el) return;
    clearTimeout(el._hideT);
    el.style.display = 'none';
  }

  // =============== playback (time-based, reliable Pause) ===============
  function play() {
    if (!state.meta || state.playing) return;
    state.playing = true;
    $("btnPlay") && ($("btnPlay").disabled = true);
    $("btnPause") && ($("btnPause").disabled = false);

    const stepMs = 1000 / state.fps;
    state.nextAt = performance.now();

    const loop = async (t) => {
      if (!state.playing) return;  // hard stop
      if (t >= state.nextAt) {
        const next = (state.frame + 1) % state.meta.n_frames;
        try { await loadFrame(next); } catch (e) { console.error(e); pause(); return; }
        state.nextAt += stepMs;
      }
      state.playRAF = requestAnimationFrame(loop);
    };
    state.playRAF = requestAnimationFrame(loop);
  }

  function pause() {
    state.playing = false;
    $("btnPlay") && ($("btnPlay").disabled = false);
    $("btnPause") && ($("btnPause").disabled = true);
    if (state.playRAF) cancelAnimationFrame(state.playRAF);
    state.playRAF = null;
  }

  // =============== boot & UI wiring ===============
  async function boot() {
    initThree();
    try {
      await getMeta();
      await loadFrame(0);
      status('ready — hover to inspect, click to pin tooltip');
    } catch (e) {
      console.error(e); status(`init error: ${e.message}`);
    }

    // buttons
    $("btnLoad")?.addEventListener('click', () => loadFrame(0));
    $("btnPlay")?.addEventListener('click', play);
    $("btnPause")?.addEventListener('click', pause);

    // frame slider
    const slider = $("frameSlider");
    if (slider) {
      slider.addEventListener('input', (e) => {
        const v = parseInt(e.target.value || '0', 10);
        $("frameLabel").textContent = String(v);
      });
      slider.addEventListener('change', async (e) => {
        const v = parseInt(e.target.value || '0', 10);
        pause();
        await loadFrame(v);
      });
    }

    // pointer events for picking
    const canvas = $("viewerCanvas");
    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('click', onClick);
  }

  window.addEventListener('DOMContentLoaded', boot);
})();
