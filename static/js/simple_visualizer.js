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

  // ---- Colormap System ----
  let currentColormap = 'red_white_blue'; // Single colormap: Red-White-Blue
  
  const COLORMAPS = {
    red_white_blue: {
      name: 'Red-White-Blue',
      cssGradient: 'linear-gradient(to right, #08306b, #2171b5, #4292c6, #6baed6, #ffffff, #fb6a4a, #ef3b2c, #cb181d, #67000d)'
    }
  };

  // Red-White-Blue colormap with smooth gradient shades
  // Blue = low values, White = mid values, Red = high values
  function colorRedWhiteBlue(t) {
    t = Math.max(0, Math.min(1, t));
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
    return { r: s1.r + u * (s2.r - s1.r), g: s1.g + u * (s2.g - s1.g), b: s1.b + u * (s2.b - s1.b) };
  }

  // Get color - always uses Red-White-Blue
  function colorFromScore01(s) {
    const t = Math.max(0, Math.min(1, s));
    return colorRedWhiteBlue(t);
  }

  // Set colormap (kept for compatibility but only one colormap now)
  function setColormap(name) {
    currentColormap = 'red_white_blue';
    updateLegendColorbar();
    return true;
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
      
      // Get score for this residue - look up by residue INDEX (0-based)
      let s;
      const residueIdx = residueMeta.findIndex(r => r.resnum === parseInt(resnum));
      if (residueIdx >= 0) {
        // Use ?? to handle actual 0 values correctly
        s = scoreData[String(residueIdx)] ?? 0.0;
      } else {
        s = scoreData[resnum] ?? 0.0;
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
      // Pause playback when clicking on molecule
      if (playing) {
        pausePlayback();
        statusEl.textContent = 'Paused (clicked molecule)';
      }
      
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
      
      // Look up by residue INDEX first (0-based), fall back to PDB resnum
      // Use ?? instead of || to handle actual 0 values correctly
      const hotspotValue = hotspotData[residueIdx] ?? hotspotData[resnumStr] ?? 0;
      const anomalyValue = anomalyData[residueIdx] ?? anomalyData[resnumStr] ?? 0;
      const rmsfValue = rmsfData[residueIdx] ?? 0;
      const ticaValue = ticaData[residueIdx] ?? 0;
      
      // Generate detailed explanations for each metric
      const hotspotExplanation = getHotspotExplanation(hotspotValue);
      const anomalyExplanation = getAnomalyExplanation(anomalyValue);
      const rmsfExplanation = getRMSFExplanation(rmsfValue);
      const ticaExplanation = getTICAExplanation(ticaValue);
      
      // Build info HTML
      let residueInfo = '';
      if (residue) {
        residueInfo = `<strong>Residue:</strong> ${residue.resname}${residue.resnum} (Chain ${residue.chain})`;
      } else {
        residueInfo = `<strong>Residue Number:</strong> ${resnum}`;
      }
      
      const infoHTML = `
        <div class="atom-info-panel">
          <h3>Residue Metrics Analysis</h3>
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
    updateLegendColorbar();
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

  // Playback speed control
  let playbackSpeed = 0.5; // Default to 0.5x speed (slower)
  const BASE_FRAME_DELAY = 200; // Base delay in ms at 1x speed

  // Pause playback function (exposed for click-to-pause)
  function pausePlayback() {
    if (playing) {
      playing = false;
      btnPlay.disabled = false;
      btnPause.disabled = true;
      if (playHandle) { clearTimeout(playHandle); playHandle = null; }
    }
  }

  // Set playback speed (0.25 to 2.0)
  function setPlaybackSpeed(speed) {
    playbackSpeed = Math.max(0.25, Math.min(2.0, speed));
    return playbackSpeed;
  }

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
      const frameDelay = BASE_FRAME_DELAY / playbackSpeed;
      playHandle = setTimeout(step, frameDelay);
    };
    step();
  });

  btnPause.addEventListener("click", pausePlayback);

  // Reload current frame with current colormap/metric settings
  async function reloadCurrentFrame() {
    const currentFrame = parseInt(slider.value, 10);
    await loadFrame(currentFrame);
  }

  // Expose playback controls
  window.pausePlayback = pausePlayback;
  window.setPlaybackSpeed = setPlaybackSpeed;
  window.getPlaybackSpeed = () => playbackSpeed;
  window.reloadCurrentFrame = reloadCurrentFrame;

  // Initialize legend and load first frame
  updateLegend();
  await loadFrame(0);
  await updateTimelineHeatmap();
})();
