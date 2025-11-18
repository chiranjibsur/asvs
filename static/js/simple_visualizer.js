/* simple_visualizer.js — per-residue dynamic coloring with points geometry + metric switching */
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
  const metricSelect = document.getElementById("metricSelect");
  const metricInfo = document.getElementById("metricInfo");
  const legendTitle = document.getElementById("legendTitle");
  const legendDesc = document.getElementById("legendDesc");
  const heatmapCanvas = document.getElementById("heatmapCanvas");

  // Metric configuration
  const METRIC_CONFIG = {
    hotspot: {
      title: "Dynamic Hotspot",
      description: "Visualize dynamic regions of interest",
      legendDesc: "High values indicate regions of interest",
      fetchData: (frame) => getJSON(`/api/hotspots/${frame}`),
      fetchStaticData: null,
      isFrameDependent: true
    },
    anomaly: {
      title: "Dynamic Anomaly",
      description: "Unusual motion indicative of functional transitions",
      legendDesc: "High values indicate anomalous conformations",
      fetchData: (frame) => getJSON(`/api/metrics/anomaly/${frame}`),
      fetchStaticData: null,
      isFrameDependent: true
    },
    rmsf: {
      title: "RMSF (Flexibility)",
      description: "Root Mean Square Fluctuation - inherent flexibility",
      legendDesc: "High values indicate flexible regions",
      fetchData: null,
      fetchStaticData: () => getJSON('/api/rmsf'),
      isFrameDependent: false
    },
    tica: {
      title: "tICA Importance",
      description: "Contribution to slow collective motions",
      legendDesc: "High values indicate importance in collective dynamics",
      fetchData: null,
      fetchStaticData: () => getJSON('/api/metrics/tica_importance'),
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

  // --- fetching helpers -----------------------------------------------------
  async function fetchFrameXYZ(frame) {
    const j = await getJSON(`/api/trajectory/frame/${frame}`);
    return j.xyz; // [[x,y,z]...]
  }

  // --- build / update points ------------------------------------------------
  async function loadFrame(frame) {
    statusEl.textContent = `loading frame ${frame}…`;

    // Fetch coordinates
    const xyz = await fetchFrameXYZ(frame);
    
    // Fetch metric data
    const scoreData = await fetchMetricData(currentMetric, frame);

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
      
      // Get score for this residue
      let s;
      const residueIdx = residueMeta.findIndex(r => r.resnum === parseInt(resnum));
      if (residueIdx >= 0) {
        s = scoreData[String(residueIdx)] || 0.0;
      } else {
        s = scoreData[resnum] || 0.0;
      }
      
      const { r, g, b } = colorFromScore01(s);

      const p = i * 3;
      posArr[p] = x; posArr[p + 1] = y; posArr[p + 2] = z;
      colArr[p] = r; colArr[p + 1] = g; colArr[p + 2] = b;
    }

    geometry.attributes.position.needsUpdate = true;
    geometry.attributes.color.needsUpdate = true;
    geometry.computeBoundingSphere();

    statusEl.textContent = `frame ${frame} loaded`;
    
    // Update heatmap marker
    await updateTimelineHeatmap();
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
      
      // Get all metric values
      const hotspotData = await fetchMetricData('hotspot', currentFrame);
      const anomalyData = await fetchMetricData('anomaly', currentFrame);
      const rmsfData = await fetchMetricData('rmsf', 0);
      const ticaData = await fetchMetricData('tica', 0);
      
      const residueIdx = residue ? String(residue.index) : String(resnum);
      
      const hotspotValue = hotspotData[resnumStr] || hotspotData[residueIdx] || 0;
      const anomalyValue = anomalyData[resnumStr] || anomalyData[residueIdx] || 0;
      const rmsfValue = rmsfData[residueIdx] || 0;
      const ticaValue = ticaData[residueIdx] || 0;
      
      // Build info HTML
      let residueInfo = '';
      if (residue) {
        residueInfo = `<strong>Residue:</strong> ${residue.resname}${residue.resnum} (Chain ${residue.chain})`;
      } else {
        residueInfo = `<strong>Residue Number:</strong> ${resnum}`;
      }
      
      const infoHTML = `
        <div class="atom-info-panel">
          <h3>Residue Metrics</h3>
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
          <div class="info-section" style="border-top: 1px solid #2b2f3a; padding-top: 10px; margin-top: 10px;">
            <strong>Dynamic Hotspot:</strong> ${hotspotValue.toFixed(3)}<br>
            <span style="font-size: 11px; color: #9aa3b2;">Regions of interest</span>
          </div>
          <div class="info-section">
            <strong>Dynamic Anomaly:</strong> ${anomalyValue.toFixed(3)}<br>
            <span style="font-size: 11px; color: #9aa3b2;">Unusual conformations</span>
          </div>
          <div class="info-section">
            <strong>RMSF (Flexibility):</strong> ${rmsfValue.toFixed(3)}<br>
            <span style="font-size: 11px; color: #9aa3b2;">Inherent flexibility</span>
          </div>
          <div class="info-section">
            <strong>tICA Importance:</strong> ${ticaValue.toFixed(3)}<br>
            <span style="font-size: 11px; color: #9aa3b2;">Collective motion contribution</span>
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

  // Update legend based on current metric
  function updateLegend() {
    const config = METRIC_CONFIG[currentMetric];
    legendTitle.textContent = config.title;
    legendDesc.textContent = config.legendDesc;
    metricInfo.textContent = config.description;
  }

  // Fetch metric data for a specific frame
  async function fetchMetricData(metric, frame) {
    const config = METRIC_CONFIG[metric];
    
    if (!config.isFrameDependent) {
      // Static data (RMSF, tICA) - load once
      if (!metricsCache[metric]) {
        const data = await config.fetchStaticData();
        metricsCache[metric] = data.normalized;
      }
      return metricsCache[metric];
    } else {
      // Frame-dependent data (hotspot, anomaly) - cache per frame
      if (!metricsCache[metric][frame]) {
        const data = await config.fetchData(frame);
        metricsCache[metric][frame] = data;
      }
      return metricsCache[metric][frame];
    }
  }

  // Handle metric selection change
  metricSelect.addEventListener('change', async () => {
    currentMetric = metricSelect.value;
    updateLegend();
    const currentFrame = parseInt(slider.value, 10);
    await loadFrame(currentFrame);
    await updateTimelineHeatmap();
  });

  // Initialize timeline heatmap
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
        const { r, g, b } = colorFromScore01(val);
        ctx.fillStyle = `rgb(${r*255}, ${g*255}, ${b*255})`;
        ctx.fillRect(idx * barWidth, 0, barWidth, height);
      });
      
    } else {
      // For frame-dependent metrics, show max value per frame
      const frameScores = [];
      for (let f = 0; f < meta.n_frames; f++) {
        try {
          const data = await fetchMetricData(currentMetric, f);
          const values = Object.values(data);
          const maxVal = Math.max(...values);
          frameScores.push(maxVal);
        } catch (e) {
          frameScores.push(0);
        }
      }
      
      // Draw heatmap
      const barWidth = width / meta.n_frames;
      frameScores.forEach((score, idx) => {
        const { r, g, b } = colorFromScore01(score);
        ctx.fillStyle = `rgb(${r*255}, ${g*255}, ${b*255})`;
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

  // Handle heatmap clicks
  heatmapCanvas.addEventListener('click', (e) => {
    const rect = heatmapCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const fraction = x / rect.width;
    const targetFrame = Math.floor(fraction * meta.n_frames);
    slider.value = String(targetFrame);
    frameLabel.textContent = String(targetFrame);
    loadFrame(targetFrame);
  });

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

  // Initialize legend and load first frame
  updateLegend();
  await loadFrame(0);
  await updateTimelineHeatmap();
})();
