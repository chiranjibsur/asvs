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

  // ---- atom metadata ----
  const atomInfo = await (await fetch('/api/trajectory/atoms')).json();
  const atoms = atomInfo.atoms;
  const covR  = atomInfo.covalent_radii || {};

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
  }

  // ---- hotspot coloring (strict BWR, no green) ----
  function colorBWR (t) {
    // t in [0,1] → blue(0,0,1) → white(1,1,1) → red(1,0,0)
    t = Math.max(0, Math.min(1, t));
    const c = new THREE.Color();
    if (t <= 0.5) {
      // 0..0.5 : blue -> white
      const k = t / 0.5;            // 0..1
      c.setRGB(k, k, 1.0);
    } else {
      // 0.5..1 : white -> red
      const k = (t - 0.5) / 0.5;    // 0..1
      c.setRGB(1.0, 1.0 - 0.85 * k, 1.0 - k);
    }
    return c;
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

  async function applyHotspotColors (frame) {
    const hs = await fetchHotspots(frame) || {};
    // make dense residue-indexed scores
    const scores = new Float32Array(meta.n_residues);
    for (const k in hs) {
      const idx = parseInt(k, 10);
      if (!Number.isNaN(idx) && idx >= 0 && idx < scores.length) {
        scores[idx] = +hs[k];
      }
    }
    for (let i = 0; i < atomMeshes.length; i++) {
      const rIdx = atomResidueIdx[i];     // 0-based residue index
      const t = scores[rIdx] || 0.0;      // 0..1
      atomMeshes[i].material.color.copy(colorBWR(t));
    }
  }

  // ---- initial placement ----
  updateAtoms(xyz0);
  await applyHotspotColors(0);

  // ---- playback / loading ----
  let playing = false, fi = 0, rafId;

  async function loadFrame (idx) {
    status.textContent = `loading frame ${idx}…`;
    const { xyz } = await (await fetch(`/api/trajectory/frame/${idx}`)).json();
    updateAtoms(xyz);
    await applyHotspotColors(idx);
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
    btnPause.disabled = false;
    const tick = async () => {
      if (!playing) return;
      await loadFrame(fi);
      fi = (fi + 1) % meta.n_frames;
      rafId = requestAnimationFrame(tick);
    };
    tick();
  };

  btnPause.onclick = () => {
    playing = false;
    btnPause.disabled = true;
    if (rafId) cancelAnimationFrame(rafId);
  };

  (function renderLoop () {
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(renderLoop);
  })();
})();
