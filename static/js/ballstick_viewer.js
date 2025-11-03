/* global THREE */
(async function () {
  const canvas = document.getElementById('canvas');
  const status = document.getElementById('status');
  const slider = document.getElementById('slider');
  const frameLbl = document.getElementById('frameLbl');
  const btnLoad = document.getElementById('btnLoad');
  const btnPlay = document.getElementById('btnPlay');
  const btnPause = document.getElementById('btnPause');
  const metaPill = document.getElementById('metaPill');

  const r = await fetch('/api/trajectory/meta'); const meta = await r.json();
  slider.max = meta.n_frames - 1; frameLbl.textContent = '0';
  metaPill.textContent = `frames: ${meta.n_frames} • atoms: ${meta.n_atoms} • residues: ${meta.n_residues}`;

  // scene
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x0b0c0f);
  const camera = new THREE.PerspectiveCamera(45, canvas.clientWidth / canvas.clientHeight, 0.1, 2000);
  camera.position.set(0, 0, 120);
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  const light = new THREE.DirectionalLight(0xffffff, 1.2); light.position.set(1,1,1); scene.add(light);
  scene.add(new THREE.AmbientLight(0xffffff, 0.3));

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize); resize();

  // one-time atom metadata (element/resnum) and make bonds
  const atomInfo = await (await fetch('/api/trajectory/atoms')).json();
  const atoms = atomInfo.atoms;
  const rad = atomInfo.covalent_radii;

  const atomMeshes = [];
  const atomGeom = new THREE.SphereGeometry(0.9, 16, 16);
  const matByElement = {};
  function matFor(element){ if(!matByElement[element]) matByElement[element] = new THREE.MeshStandardMaterial(); return matByElement[element]; }

  atoms.forEach(() => {
    const m = new THREE.Mesh(atomGeom, new THREE.MeshStandardMaterial());
    scene.add(m); atomMeshes.push(m);
  });

  // Build bonds (simple cutoff)
  const bonds = [];
  const bondMaterial = new THREE.MeshStandardMaterial({opacity:1, transparent:false});
  const cylGeom = new THREE.CylinderGeometry(0.3, 0.3, 1, 8);
  function makeBond(i, j, d) {
    const mesh = new THREE.Mesh(cylGeom, bondMaterial);
    mesh.userData = { i, j, d };
    scene.add(mesh); bonds.push(mesh);
  }

  // get an initial frame of xyz to decide bonds
  const f0 = await (await fetch('/api/trajectory/frame/0')).json();
  const xyz0 = f0.xyz;
  const cutoff = (e1, e2) => {
    const r1 = rad[e1] ?? 0.76, r2 = rad[e2] ?? 0.76;
    return (r1 + r2) * 1.25 + 0.25; // generous cutoff
  };

  // kd-lite: brute force (374 atoms is fine)
  for (let i = 0; i < atoms.length; i++) {
    for (let j = i + 1; j < atoms.length; j++) {
      const p = xyz0[i], q = xyz0[j];
      const dx = p[0]-q[0], dy = p[1]-q[1], dz = p[2]-q[2];
      const dist = Math.sqrt(dx*dx+dy*dy+dz*dz);
      const c = cutoff(atoms[i].element, atoms[j].element);
      if (dist > 0.4 && dist < c) makeBond(i, j, dist);
    }
  }

  function placeBond(mesh, p, q) {
    const v1 = new THREE.Vector3(p[0],p[1],p[2]);
    const v2 = new THREE.Vector3(q[0],q[1],q[2]);
    const mid = v1.clone().add(v2).multiplyScalar(0.5);
    const dir = v2.clone().sub(v1); const len = dir.length();
    mesh.position.copy(mid);
    mesh.scale.set(1,1,len);
    mesh.lookAt(v2);
  }

  function updateAtoms(xyz) {
    for (let i = 0; i < atomMeshes.length; i++) {
      const m = atomMeshes[i], p = xyz[i];
      m.position.set(p[0], p[1], p[2]);
      // lazy element tint per frame (optional): keep one muted color
      m.material.color.setHex(0x7fa6ff);
    }
    for (const b of bonds) {
      placeBond(b, xyz[b.userData.i], xyz[b.userData.j]);
    }
  }

  updateAtoms(xyz0);

  let playing = false, fi = 0, raf;
  async function loadFrame(idx){
    status.textContent = `loading frame ${idx}…`;
    const resp = await fetch(`/api/trajectory/frame/${idx}`); const { xyz } = await resp.json();
    updateAtoms(xyz);
    status.textContent = `frame ${idx} loaded`;
  }

  btnLoad.onclick = () => loadFrame(parseInt(slider.value,10));
  slider.oninput = e => { frameLbl.textContent = e.target.value; if(!playing) loadFrame(+e.target.value); };

  btnPlay.onclick = () => {
    if (playing) return; playing = true; btnPause.disabled = false;
    const tick = async () => {
      if (!playing) return;
      await loadFrame(fi); fi = (fi + 1) % meta.n_frames;
      raf = requestAnimationFrame(tick);
    }; tick();
  };
  btnPause.onclick = () => { playing = false; btnPause.disabled = true; cancelAnimationFrame(raf); };

  (function render(){ controls.update(); renderer.render(scene, camera); requestAnimationFrame(render); })();
})();
