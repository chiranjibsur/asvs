/**
 * Spline utilities for ribbon visualization
 * Implements rotation-minimizing frames (RMF) for stable ribbon geometry
 * 
 * Reference:
 * - Hanson & Ma (1995) "Parallel Transport Approach to Curve Framing"
 * - Wang et al. (2008) "Computation of Rotation Minimizing Frames"
 */

/* global THREE */

/**
 * Compute rotation-minimizing frames along a curve
 * @param {THREE.Curve} curve - The curve to compute frames for
 * @param {number} segments - Number of segments along the curve
 * @param {THREE.Vector3} initialNormal - Initial normal vector (optional)
 * @returns {Array} Array of {position, tangent, normal, binormal} objects
 */
function computeRotationMinimizingFrames(curve, segments, initialNormal = null) {
  const frames = [];
  
  // Initial frame at t=0
  const t0 = 0;
  const p0 = curve.getPointAt(t0);
  const tangent0 = curve.getTangentAt(t0).normalize();
  
  // Determine initial normal
  let normal0;
  if (initialNormal) {
    normal0 = initialNormal.clone().normalize();
    // Make sure it's perpendicular to tangent
    normal0.sub(tangent0.clone().multiplyScalar(normal0.dot(tangent0))).normalize();
  } else {
    // Choose an arbitrary perpendicular vector
    if (Math.abs(tangent0.x) < 0.9) {
      normal0 = new THREE.Vector3(1, 0, 0);
    } else {
      normal0 = new THREE.Vector3(0, 1, 0);
    }
    normal0.sub(tangent0.clone().multiplyScalar(normal0.dot(tangent0))).normalize();
  }
  
  const binormal0 = new THREE.Vector3().crossVectors(tangent0, normal0).normalize();
  
  frames.push({
    position: p0.clone(),
    tangent: tangent0.clone(),
    normal: normal0.clone(),
    binormal: binormal0.clone()
  });
  
  // Compute subsequent frames using parallel transport
  for (let i = 1; i <= segments; i++) {
    const t = i / segments;
    const prevFrame = frames[i - 1];
    
    const p = curve.getPointAt(t);
    const tangent = curve.getTangentAt(t).normalize();
    
    // Vector from previous point to current point
    const v1 = p.clone().sub(prevFrame.position);
    const c1 = v1.dot(v1);
    
    if (c1 < 1e-8) {
      // Points too close, reuse previous frame
      frames.push({
        position: p.clone(),
        tangent: tangent.clone(),
        normal: prevFrame.normal.clone(),
        binormal: prevFrame.binormal.clone()
      });
      continue;
    }
    
    // Parallel transport of previous normal
    const rL = prevFrame.normal.clone();
    const tL = prevFrame.tangent.clone();
    
    // Projection of rL onto plane perpendicular to v1
    const v1_norm = v1.clone().divideScalar(Math.sqrt(c1));
    const c2 = 2 / c1;
    const rL_proj = rL.clone().sub(v1_norm.clone().multiplyScalar(c2 * v1.dot(rL)));
    
    // New tangent
    const tL_proj = tL.clone().sub(v1_norm.clone().multiplyScalar(c2 * v1.dot(tL)));
    
    // Reflection of rL_proj to be perpendicular to new tangent
    const v2 = tangent.clone().sub(tL_proj);
    const c3 = v2.dot(v2);
    
    let normal;
    if (c3 < 1e-8) {
      normal = rL_proj.clone();
    } else {
      const c4 = 2 / c3;
      normal = rL_proj.clone().sub(v2.clone().multiplyScalar(c4 * v2.dot(rL_proj)));
    }
    
    normal.normalize();
    const binormal = new THREE.Vector3().crossVectors(tangent, normal).normalize();
    
    frames.push({
      position: p.clone(),
      tangent: tangent.clone(),
      normal: normal.clone(),
      binormal: binormal.clone()
    });
  }
  
  return frames;
}

/**
 * Create a ribbon mesh with varying width and thickness based on secondary structure
 * @param {THREE.Curve} curve - The curve to create ribbon along
 * @param {number} segments - Number of segments
 * @param {Array} secondaryStructure - Array of 'H', 'E', or 'C' for each segment
 * @param {Array} colors - Array of THREE.Color objects for each segment
 * @returns {THREE.BufferGeometry} The ribbon geometry
 */
function createRibbonGeometry(curve, segments, secondaryStructure, colors) {
  const frames = computeRotationMinimizingFrames(curve, segments);
  
  // Geometry arrays
  const positions = [];
  const normals = [];
  const colorArray = [];
  const indices = [];
  
  // Number of points across the ribbon
  const crossSectionPoints = 12;
  
  for (let i = 0; i <= segments; i++) {
    const frame = frames[i];
    const t = i / segments;
    
    // Determine ribbon width and thickness based on secondary structure
    const ssIndex = Math.min(Math.floor(t * secondaryStructure.length), secondaryStructure.length - 1);
    const ss = secondaryStructure[ssIndex] || 'C';
    
    let width, thickness;
    if (ss === 'H') {
      // Helix: moderate width, circular cross-section
      width = 1.5;
      thickness = 1.5;
    } else if (ss === 'E') {
      // Sheet: wide and flat
      width = 2.5;
      thickness = 0.3;
    } else {
      // Coil: thin tube
      width = 0.8;
      thickness = 0.8;
    }
    
    // Get color for this segment
    const colorIndex = Math.min(Math.floor(t * colors.length), colors.length - 1);
    const color = colors[colorIndex] || new THREE.Color(0xcccccc);
    
    // Create cross-section
    for (let j = 0; j <= crossSectionPoints; j++) {
      const angle = (j / crossSectionPoints) * Math.PI * 2;
      
      // Elliptical cross-section
      const x = Math.cos(angle) * width;
      const y = Math.sin(angle) * thickness;
      
      // Position in 3D
      const offset = frame.normal.clone().multiplyScalar(x)
        .add(frame.binormal.clone().multiplyScalar(y));
      const pos = frame.position.clone().add(offset);
      
      positions.push(pos.x, pos.y, pos.z);
      
      // Normal for lighting
      const normal = frame.normal.clone().multiplyScalar(Math.cos(angle))
        .add(frame.binormal.clone().multiplyScalar(Math.sin(angle))).normalize();
      normals.push(normal.x, normal.y, normal.z);
      
      // Color
      colorArray.push(color.r, color.g, color.b);
    }
  }
  
  // Create indices for triangles
  for (let i = 0; i < segments; i++) {
    for (let j = 0; j < crossSectionPoints; j++) {
      const a = i * (crossSectionPoints + 1) + j;
      const b = a + 1;
      const c = a + (crossSectionPoints + 1);
      const d = c + 1;
      
      // Two triangles per quad
      indices.push(a, b, c);
      indices.push(b, d, c);
    }
  }
  
  // Create geometry
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colorArray, 3));
  geometry.setIndex(indices);
  
  // Compute smooth normals
  geometry.computeVertexNormals();
  
  return geometry;
}

/**
 * Smooth an array of values using a moving average filter
 * @param {Array} values - Array of values to smooth
 * @param {number} windowSize - Size of the smoothing window
 * @returns {Array} Smoothed values
 */
function smoothArray(values, windowSize = 3) {
  if (values.length < windowSize) {
    return values.slice();
  }
  
  const smoothed = [];
  const halfWindow = Math.floor(windowSize / 2);
  
  for (let i = 0; i < values.length; i++) {
    let sum = 0;
    let count = 0;
    
    for (let j = Math.max(0, i - halfWindow); j <= Math.min(values.length - 1, i + halfWindow); j++) {
      sum += values[j];
      count++;
    }
    
    smoothed.push(sum / count);
  }
  
  return smoothed;
}

// Export functions for use in ribbon_viewer.js
window.SplineUtils = {
  computeRotationMinimizingFrames,
  createRibbonGeometry,
  smoothArray
};
