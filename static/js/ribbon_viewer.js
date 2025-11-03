/* global THREE */
(async function () {
  const canvas = document.getElementById('canvas');
  const slider = document.getElementById('slider');
  const frameLbl = document.getElementById('frameLbl');
  const status = document.getElementById('status');
  const btnPlay = document.getElementById('btnPlay');
  const btnPause = document.getElementById('btnPause');

  const meta = await (await fetch('/api/trajectory/meta')).json();
  slider.max = meta.n_frames - 1;

  // scene
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x0b0c0f);
  const camera = new THREE.PerspectiveCamera(45, canvas.clientWidth / canvas.clientHeight, 0.1, 4000);
  camera.position.set(0, 0, 180);
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  scene.add(new THREE.DirectionalLight(0xffffff, 1.2)).position.set(1,1,1);
  scene.add(new THREE.AmbientLight(0xffffff, 0.3));

  function resize(){ const w=canvas.clientWidth,h=canvas.clientHeight; renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix(); }
  window.addEventListener('resize', resize); resize();

  let tube, tubeMat;
  function colorLerp(t){ // blue -> white -> red
    if (t <= 0.5){ const k=t/0.5; return new THREE.Color().setRGB( k, k, 1 ); }
    const k=(t-0.5)/0.5; return new THREE.Color().setRGB( 1, 1-k*0.2, 1-k );
  }

  async function loadRibbon(frame){
    status.textContent = `loading ribbon frame ${frame}…`;
    const ca = (await (await fetch(`/api/trajectory/ca/${frame}`)).json()).ca;
    const hs = await (await fetch(`/api/hotspots/${frame}`)).json(); // { "1":score,... }

    // build curve points
    const pts = ca.map(p => new THREE.Vector3(p[0], p[1], p[2]));
    const curve = new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.1);

    // remove previous
    if (tube) { scene.remove(tube); tube.geometry.dispose(); }

    // geometry with per-vertex colors
    const tubularSegments = Math.max(100, pts.length * 3);
    const radius = 1.2;
    const radialSegments = 12;
    const geometry = new THREE.TubeGeometry(curve, tubularSegments, radius, radialSegments, false);
    const N = geometry.parameters.path.points.length;
    const colors = new Float32Array(geometry.attributes.position.count * 3);

    // map path point -> residue index (approx evenly)
    const resCount = Object.keys(hs).length || pts.length;
    function scoreAtPathIndex(i){
      const ridx = Math.max(0, Math.min(resCount-1, Math.round(i / (N-1) * (resCount-1))));
      const key = String(ridx+1);
      return Math.max(0, Math.min(1, (hs[key] ?? 0)));
    }

    for (let i = 0; i < geometry.attributes.position.count; i++) {
      const t = scoreAtPathIndex(Math.floor(i / radialSegments));
      const c = colorLerp(t);
      colors[i*3+0] = c.r; colors[i*3+1] = c.g; colors[i*3+2] = c.b;
    }
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    tubeMat = new THREE.MeshStandardMaterial({ vertexColors: true });
    tube = new THREE.Mesh(geometry, tubeMat);
    scene.add(tube);
    status.textContent = `frame ${frame} loaded`;
  }

  slider.oninput = e => { frameLbl.textContent = e.target.value; loadRibbon(+e.target.value); };

  let playing=false, fi=0, raf;
  btnPlay.onclick = () => { if(playing) return; playing=true; btnPause.disabled=false;
    const loop=async()=>{ if(!playing) return; await loadRibbon(fi); fi=(fi+1)%meta.n_frames; raf=requestAnimationFrame(loop); }; loop();
  };
  btnPause.onclick = () => { playing=false; btnPause.disabled=true; cancelAnimationFrame(raf); };

  // initial
  loadRibbon(0);
  (function render(){ controls.update(); renderer.render(scene, camera); requestAnimationFrame(render);} )();
})();
