/* global THREE */
(async function () {
  const canvas   = document.getElementById('canvas');
  const slider   = document.getElementById('slider');
  const frameLbl = document.getElementById('frameLbl');
  const status   = document.getElementById('status');
  const btnPlay  = document.getElementById('btnPlay');
  const btnPause = document.getElementById('btnPause');
  const metricSelect = document.getElementById('metricSelect');
  const metricInfo = document.getElementById('metricInfo');
  const legendTitle = document.getElementById('legendTitle');
  const legendDesc = document.getElementById('legendDesc');
  const heatmapCanvas = document.getElementById('heatmapCanvas');

  // ---- Metric Configuration ----
  const METRIC_CONFIG = {
    hotspot: {
      title: "Dynamic Hotspot",
      description: "Visualize dynamic regions of interest",
      legendDesc: "High values indicate regions of interest",
      fetchData: (frame) => fetch(`/api/hotspots/${frame}`).then(r => r.ok ? r.json() : {}),
      fetchStaticData: null,
      isFrameDependent: true
    },
    anomaly: {
      title: "Dynamic Anomaly",
      description: "Unusual motion indicative of functional transitions",
      legendDesc: "High values indicate anomalous conformations",
      fetchData: (frame) => fetch(`/api/metrics/anomaly/${frame}`).then(r => r.ok ? r.json() : {}),
      fetchStaticData: null,
      isFrameDependent: true
    },
    rmsf: {
      title: "RMSF (Flexibility)",
      description: "Root Mean Square Fluctuation - inherent flexibility",
      legendDesc: "High values indicate flexible regions",
      fetchData: null,
      fetchStaticData: () => fetch('/api/rmsf').then(r => r.ok ? r.json() : {normalized: {}}),
      isFrameDependent: false
    },
    tica: {
      title: "tICA Importance",
      description: "Contribution to slow collective motions",
      legendDesc: "High values indicate importance in collective dynamics",
      fetchData: null,
      fetchStaticData: () => fetch('/api/metrics/tica_importance').then(r => r.ok ? r.json() : {normalized: {}}),
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

  // ---- Colormap System ----
  let currentColormap = 'viridis'; // Default to viridis (more visually appealing)
  
  const COLORMAPS = {
    viridis: {
      name: 'Viridis',
      desc: 'Perceptually uniform, colorblind friendly',
      cssGradient: 'linear-gradient(to right, #440154, #482878, #3e4a89, #31688e, #26828e, #1f9e89, #35b779, #6ece58, #b5de2b, #fde725)'
    },
    plasma: {
      name: 'Plasma',
      desc: 'Warm tones, perceptually uniform',
      cssGradient: 'linear-gradient(to right, #0d0887, #5c01a6, #9c179e, #cc4778, #ed7953, #fdb42f, #f0f921)'
    },
    coolwarm: {
      name: 'Cool-Warm',
      desc: 'Diverging blue to red',
      cssGradient: 'linear-gradient(to right, #3b4cc0, #6b8de3, #aac7fd, #dddddd, #f7b89c, #e26952, #b40426)'
    },
    rainbow: {
      name: 'Rainbow',
      desc: 'Classic rainbow spectrum',
      cssGradient: 'linear-gradient(to right, #0000ff, #00ffff, #00ff00, #ffff00, #ff8800, #ff0000)'
    },
    bwr: {
      name: 'Blue-White-Red',
      desc: 'Diverging colormap (original)',
      cssGradient: 'linear-gradient(to right, #0000ff, #4fa9ff, #ffffff, #ffb6c1, #ff6666, #8b0000)'
    }
  };

  // Viridis colormap
  function colorViridis(t) {
    t = Math.max(0, Math.min(1, t));
    const c = new THREE.Color();
    const stops = [
      { t: 0.0, r: 0x44/255, g: 0x01/255, b: 0x54/255 },
      { t: 0.25, r: 0x3e/255, g: 0x4a/255, b: 0x89/255 },
      { t: 0.5, r: 0x26/255, g: 0x82/255, b: 0x8e/255 },
      { t: 0.75, r: 0x6e/255, g: 0xce/255, b: 0x58/255 },
      { t: 1.0, r: 0xfd/255, g: 0xe7/255, b: 0x25/255 }
    ];
    let i = 0;
    while (i < stops.length - 1 && stops[i + 1].t < t) i++;
    const s1 = stops[i], s2 = stops[Math.min(i + 1, stops.length - 1)];
    const u = (t - s1.t) / (s2.t - s1.t || 1);
    c.setRGB(s1.r + u * (s2.r - s1.r), s1.g + u * (s2.g - s1.g), s1.b + u * (s2.b - s1.b));
    return c;
  }

  // Plasma colormap
  function colorPlasma(t) {
    t = Math.max(0, Math.min(1, t));
    const c = new THREE.Color();
    const stops = [
      { t: 0.0, r: 0x0d/255, g: 0x08/255, b: 0x87/255 },
      { t: 0.25, r: 0x7c/255, g: 0x02/255, b: 0xa8/255 },
      { t: 0.5, r: 0xcc/255, g: 0x47/255, b: 0x78/255 },
      { t: 0.75, r: 0xf8/255, g: 0x97/255, b: 0x40/255 },
      { t: 1.0, r: 0xf0/255, g: 0xf9/255, b: 0x21/255 }
    ];
    let i = 0;
    while (i < stops.length - 1 && stops[i + 1].t < t) i++;
    const s1 = stops[i], s2 = stops[Math.min(i + 1, stops.length - 1)];
    const u = (t - s1.t) / (s2.t - s1.t || 1);
    c.setRGB(s1.r + u * (s2.r - s1.r), s1.g + u * (s2.g - s1.g), s1.b + u * (s2.b - s1.b));
    return c;
  }

  // Cool-Warm diverging colormap
  function colorCoolWarm(t) {
    t = Math.max(0, Math.min(1, t));
    const c = new THREE.Color();
    const stops = [
      { t: 0.0, r: 0x3b/255, g: 0x4c/255, b: 0xc0/255 },
      { t: 0.25, r: 0x6b/255, g: 0x8d/255, b: 0xe3/255 },
      { t: 0.5, r: 0xdd/255, g: 0xdd/255, b: 0xdd/255 },
      { t: 0.75, r: 0xf7/255, g: 0x89/255, b: 0x5c/255 },
      { t: 1.0, r: 0xb4/255, g: 0x04/255, b: 0x26/255 }
    ];
    let i = 0;
    while (i < stops.length - 1 && stops[i + 1].t < t) i++;
    const s1 = stops[i], s2 = stops[Math.min(i + 1, stops.length - 1)];
    const u = (t - s1.t) / (s2.t - s1.t || 1);
    c.setRGB(s1.r + u * (s2.r - s1.r), s1.g + u * (s2.g - s1.g), s1.b + u * (s2.b - s1.b));
    return c;
  }

  // Rainbow colormap
  function colorRainbow(t) {
    t = Math.max(0, Math.min(1, t));
    const c = new THREE.Color();
    c.setHSL((1 - t) * 0.7, 1.0, 0.5);
    return c;
  }

  // Blue-White-Red (original)
  function colorBWR(t) {
    t = Math.max(0, Math.min(1, +t || 0));
    const c = new THREE.Color();
    let r, g, b;
    if (t <= 0.2) {
      const u = t / 0.2;
      r = 0 + u * 0x4f / 255; g = 0 + u * 0xa9 / 255; b = 1;
    } else if (t <= 0.4) {
      const u = (t - 0.2) / 0.2;
      r = 0x4f / 255 + u * (1 - 0x4f / 255); g = 0xa9 / 255 + u * (1 - 0xa9 / 255); b = 1;
    } else if (t <= 0.6) {
      const u = (t - 0.4) / 0.2;
      r = 1; g = 1 - u * (1 - 0xb6 / 255); b = 1 - u * (1 - 0xc1 / 255);
    } else if (t <= 0.8) {
      const u = (t - 0.6) / 0.2;
      r = 1; g = 0xb6 / 255 - u * (0xb6 / 255 - 0x66 / 255); b = 0xc1 / 255 - u * (0xc1 / 255 - 0x66 / 255);
    } else {
      const u = (t - 0.8) / 0.2;
      r = 1 - u * (1 - 0x8b / 255); g = 0x66 / 255 - u * (0x66 / 255); b = 0x66 / 255 - u * (0x66 / 255);
    }
    c.setRGB(r, g, b);
    return c;
  }

  // Get color based on current colormap
  function colorFromScore(s) {
    const t = Math.max(0, Math.min(1, +s || 0));
    switch (currentColormap) {
      case 'viridis': return colorViridis(t);
      case 'plasma': return colorPlasma(t);
      case 'coolwarm': return colorCoolWarm(t);
      case 'rainbow': return colorRainbow(t);
      case 'bwr': return colorBWR(t);
      default: return colorViridis(t);
    }
  }

  // Set colormap and update legend
  function setColormap(name) {
    if (COLORMAPS[name]) {
      currentColormap = name;
      updateLegendColorbar();
      return true;
    }
    return false;
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

  // ---- Metric Data Fetching ----
  async function fetchMetricData(metric, frame) {
    const config = METRIC_CONFIG[metric];
    
    if (!config.isFrameDependent) {
      // Static data (RMSF, tICA) - load once
      if (!metricsCache[metric]) {
        const data = await config.fetchStaticData();
        metricsCache[metric] = data.normalized || data;
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

  function updateLegend() {
    const config = METRIC_CONFIG[currentMetric];
    legendTitle.textContent = config.title;
    legendDesc.textContent = config.legendDesc;
    metricInfo.textContent = config.description;
    updateLegendColorbar();
  }

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
        const col = colorFromScore(val);
        ctx.fillStyle = `rgb(${col.r*255}, ${col.g*255}, ${col.b*255})`;
        ctx.fillRect(idx * barWidth, 0, barWidth, height);
      });
      
    } else {
      // For frame-dependent metrics, show max value per frame
      const frameScores = [];
      for (let f = 0; f < meta.n_frames; f++) {
        try {
          const data = await fetchMetricData(currentMetric, f);
          const values = Object.values(data);
          const maxVal = values.length > 0 ? Math.max(...values) : 0;
          frameScores.push(maxVal);
        } catch (e) {
          frameScores.push(0);
        }
      }
      
      // Draw heatmap
      const barWidth = width / meta.n_frames;
      frameScores.forEach((score, idx) => {
        const col = colorFromScore(score);
        ctx.fillStyle = `rgb(${col.r*255}, ${col.g*255}, ${col.b*255})`;
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
  let useEnhancedRibbon = true; // Toggle for enhanced ribbon
  
  async function loadRibbon (frame) {
    status.textContent = `loading ribbon frame ${frame}...`;

    // 1) ordered Ca coordinates
    const ca = (await (await fetch(`/api/trajectory/ca/${frame}`)).json()).ca; // [[x,y,z], ...]
    caPositions = ca; // Store for click detection
    
    // 2) fetch secondary structure
    let ssData = null;
    try {
      const ssResponse = await fetch(`/api/trajectory/secondary_structure/${frame}`);
      if (ssResponse.ok) {
        ssData = await ssResponse.json();
      }
    } catch (e) {
      console.warn('Could not fetch secondary structure data:', e);
    }
    
    // 3) per-residue metric scores
    let scoreData = {};
    if (showRMSF && rmsfData) {
      scoreData = rmsfData.normalized;
    } else {
      scoreData = await fetchMetricData(currentMetric, frame);
      currentHotspots = scoreData; // Store for display
    }
    
    // Update timeline
    await updateTimelineHeatmap();

    // build curve through Ca
    const pts   = ca.map(p => new THREE.Vector3(p[0], p[1], p[2]));
    const curve = new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.1);

    // Clean up previous tube
    if (tube) { scene.remove(tube); tube.geometry.dispose(); tube.material.dispose(); }

    // Decide whether to use enhanced ribbon or fallback to simple tube
    const canUseEnhanced = useEnhancedRibbon && window.SplineUtils && ssData && ssData.residues;
    
    let geom;
    if (canUseEnhanced) {
      // Use enhanced ribbon with secondary structure
      const tubularSegments = Math.max(120, pts.length * 4);
      
      // Extract secondary structure array
      const ssArray = ssData.residues.map(r => r.ss || 'C');
      
      // Build color array for each residue
      const colorArray = [];
      for (let i = 0; i < resnumsInOrder.length; i++) {
        const resnumKey = resnumsInOrder[i];
        let score = 0.0;
        
        if (showRMSF && rmsfData) {
          score = scoreData[String(i)] ?? 0.0;
        } else {
          score = scoreData[resnumKey] ?? scoreData[String(i+1)] ?? scoreData[String(i)] ?? 0.0;
        }
        
        colorArray.push(colorFromScore(score));
      }
      
      // Create enhanced ribbon geometry
      geom = window.SplineUtils.createRibbonGeometry(curve, tubularSegments, ssArray, colorArray);
    } else {
      // Fallback to simple tube geometry
      const tubularSegments = Math.max(120, pts.length * 4);
      const radius = 1.2, radialSegments = 12;
      geom = new THREE.TubeGeometry(curve, tubularSegments, radius, radialSegments, false);

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

      // paint each vertex by its ring's score
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
    }

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
      
      // Pause playback when clicking on the molecule
      if (playing) {
        pausePlayback();
        status.textContent = 'Paused (clicked molecule)';
      }
      
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
      
      // Get all metric data for this residue
      const hotspotData = await fetchMetricData('hotspot', currentFrame);
      const anomalyData = await fetchMetricData('anomaly', currentFrame);
      const rmsfData_local = await fetchMetricData('rmsf', 0);
      const ticaData = await fetchMetricData('tica', 0);
      
      const resnumKey = String(residue.resnum);
      const residueIdx = String(residueIndex);
      
      const hotspotValue = hotspotData[resnumKey] 
                        ?? hotspotData[String(residueIndex+1)] 
                        ?? hotspotData[residueIdx] 
                        ?? 0;
      const anomalyValue = anomalyData[resnumKey] 
                        ?? anomalyData[String(residueIndex+1)] 
                        ?? anomalyData[residueIdx] 
                        ?? 0;
      const rmsfValue = rmsfData_local[residueIdx] || 0;
      const ticaValue = ticaData[residueIdx] || 0;
      
      // Generate detailed explanations for each metric
      const hotspotExplanation = getHotspotExplanation(hotspotValue);
      const anomalyExplanation = getAnomalyExplanation(anomalyValue);
      const rmsfExplanation = getRMSFExplanation(rmsfValue);
      const ticaExplanation = getTICAExplanation(ticaValue);
      
      // Build info HTML with scientific explanations
      const infoHTML = `
        <div class="residue-info-panel">
          <h3>Residue Metrics Analysis</h3>
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
  let playbackSpeed = 0.5; // Default to 0.5x speed (slower)
  let lastFrameTime = 0;
  const BASE_FRAME_DELAY = 200; // Base delay in ms at 1x speed

  // Pause playback function (exposed for click-to-pause)
  function pausePlayback() {
    if (playing) {
      playing = false;
      btnPause.disabled = true;
      btnPlay.disabled = false;
      if (raf) cancelAnimationFrame(raf);
    }
  }

  // Set playback speed (0.25 to 2.0)
  function setPlaybackSpeed(speed) {
    playbackSpeed = Math.max(0.25, Math.min(2.0, speed));
    return playbackSpeed;
  }

  btnPlay.onclick = () => {
    if (playing) return;
    playing = true;
    btnPlay.disabled = true;
    btnPause.disabled = false;
    lastFrameTime = performance.now();
    
    const loop = async (currentTime) => {
      if (!playing) return;
      
      const elapsed = currentTime - lastFrameTime;
      const frameDelay = BASE_FRAME_DELAY / playbackSpeed;
      
      if (elapsed >= frameDelay) {
        await loadRibbon(fi);
        slider.value = String(fi);
        frameLbl.textContent = String(fi);
        fi = (fi + 1) % meta.n_frames;
        lastFrameTime = currentTime;
      }
      
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
  };
  btnPause.onclick = pausePlayback;

  // Expose playback controls
  window.pausePlayback = pausePlayback;
  window.setPlaybackSpeed = setPlaybackSpeed;
  window.getPlaybackSpeed = () => playbackSpeed;

  // ---- Metric selector and timeline handlers ----
  metricSelect.addEventListener('change', async () => {
    currentMetric = metricSelect.value;
    updateLegend();
    const currentFrame = parseInt(slider.value, 10);
    await loadRibbon(currentFrame);
  });

  heatmapCanvas.addEventListener('click', (e) => {
    const rect = heatmapCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const fraction = x / rect.width;
    const targetFrame = Math.floor(fraction * meta.n_frames);
    slider.value = String(targetFrame);
    frameLbl.textContent = String(targetFrame);
    loadRibbon(targetFrame);
  });

  // Initialize legend and timeline
  updateLegend();
  await updateTimelineHeatmap();

  // Expose toggleRMSFColoring to global scope for button handler
  window.toggleRMSFColoring = toggleRMSFColoring;

  // ---- Phase 3: Simplified Clip Plane for Ribbon ----
  let clipPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  let clipEnabled = false;

  function toggleClipping() {
    clipEnabled = !clipEnabled;
    renderer.localClippingEnabled = clipEnabled;
    
    // Apply clipping to tube material if it exists
    if (tube && tube.material) {
      tube.material.clippingPlanes = clipEnabled ? [clipPlane] : [];
      tube.material.needsUpdate = true;
    }
    
    return clipEnabled;
  }

  function updateClipPlane(axis, value) {
    switch(axis) {
      case 'x':
        clipPlane.normal.set(1, 0, 0);
        break;
      case 'y':
        clipPlane.normal.set(0, 1, 0);
        break;
      case 'z':
        clipPlane.normal.set(0, 0, 1);
        break;
    }
    clipPlane.constant = value;
  }

  // ---- Phase 3: Export functionality ----
  function exportScreenshot(format = 'png') {
    renderer.render(scene, camera);
    const dataURL = canvas.toDataURL(`image/${format}`);
    const link = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const currentFrame = parseInt(slider.value, 10);
    link.download = `ribbon-view-frame${currentFrame}-${timestamp}.${format}`;
    link.href = dataURL;
    link.click();
  }

  window.toggleClipping = toggleClipping;
  window.updateClipPlane = updateClipPlane;
  window.exportScreenshot = exportScreenshot;

  // initial render
  await loadRibbon(0);
  (function render () { controls.update(); renderer.render(scene, camera); requestAnimationFrame(render); })();
})();
