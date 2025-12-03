/**
 * Spline utilities for ribbon visualization
 * Implements rotation-minimizing frames (RMF) for stable ribbon geometry
 * 
 * Reference:
 * - Hanson & Ma (1995) "Parallel Transport Approach to Curve Framing"
 * - Wang et al. (2008) "Computation of Rotation Minimizing Frames"
 */

/* global THREE */

// Constants for backbone processing
const VALID_BACKBONE_THRESHOLD = 0.5;  // Minimum ratio of valid normals for backbone data to be usable

/**
 * Compute ribbon normal from backbone atoms (N, CA, C).
 * The ribbon normal is perpendicular to the peptide plane, giving proper
 * orientation for protein ribbon representations.
 * 
 * @param {Array} n_pos - [x, y, z] position of N atom
 * @param {Array} ca_pos - [x, y, z] position of CA atom  
 * @param {Array} c_pos - [x, y, z] position of C atom
 * @returns {THREE.Vector3} The ribbon normal vector
 */
function computeRibbonNormalFromBackbone(n_pos, ca_pos, c_pos) {
  if (!n_pos || !ca_pos || !c_pos) {
    return null;
  }
  
  const n = new THREE.Vector3(n_pos[0], n_pos[1], n_pos[2]);
  const ca = new THREE.Vector3(ca_pos[0], ca_pos[1], ca_pos[2]);
  const c = new THREE.Vector3(c_pos[0], c_pos[1], c_pos[2]);
  
  // Vectors from CA to N and CA to C
  const ca_n = n.clone().sub(ca);
  const ca_c = c.clone().sub(ca);
  
  // Cross product gives normal to peptide plane
  const normal = new THREE.Vector3().crossVectors(ca_n, ca_c).normalize();
  
  return normal;
}

/**
 * Compute ribbon normals for all residues from backbone data.
 * Falls back to null if backbone data is incomplete.
 * 
 * @param {Array} backboneData - Array of {N, CA, C} for each residue
 * @returns {Array} Array of THREE.Vector3 normals (or null if incomplete)
 */
function computeRibbonNormalsFromBackbone(backboneData) {
  if (!backboneData || backboneData.length === 0) {
    return null;
  }
  
  const normals = [];
  
  for (let i = 0; i < backboneData.length; i++) {
    const res = backboneData[i];
    const normal = computeRibbonNormalFromBackbone(res.N, res.CA, res.C);
    normals.push(normal);
  }
  
  // Check if we have any valid normals
  const validCount = normals.filter(n => n !== null).length;
  if (validCount < backboneData.length * VALID_BACKBONE_THRESHOLD) {
    // Less than threshold valid - backbone data is too incomplete
    return null;
  }
  
  // Interpolate missing normals
  for (let i = 0; i < normals.length; i++) {
    if (normals[i] === null) {
      // Find nearest valid neighbors
      let prevIdx = i - 1;
      while (prevIdx >= 0 && normals[prevIdx] === null) prevIdx--;
      
      let nextIdx = i + 1;
      while (nextIdx < normals.length && normals[nextIdx] === null) nextIdx++;
      
      if (prevIdx >= 0 && nextIdx < normals.length) {
        // Interpolate between neighbors
        normals[i] = normals[prevIdx].clone().lerp(normals[nextIdx], 0.5).normalize();
      } else if (prevIdx >= 0) {
        normals[i] = normals[prevIdx].clone();
      } else if (nextIdx < normals.length) {
        normals[i] = normals[nextIdx].clone();
      } else {
        normals[i] = new THREE.Vector3(0, 1, 0); // Default fallback
      }
    }
  }
  
  return normals;
}

/**
 * Compute rotation-minimizing frames along a curve
 * @param {THREE.Curve} curve - The curve to compute frames for
 * @param {number} segments - Number of segments along the curve
 * @param {THREE.Vector3} initialNormal - Initial normal vector (optional)
 * @param {Array} backboneNormals - Array of THREE.Vector3 normals from backbone (optional)
 * @returns {Array} Array of {position, tangent, normal, binormal} objects
 */
function computeRotationMinimizingFrames(curve, segments, initialNormal = null, backboneNormals = null) {
  // Blend factor for incorporating backbone normals into RMF computation
  // 0 = pure RMF, 1 = use backbone normals directly
  // A value of 0.3 provides smooth transitions while maintaining biological accuracy
  const BACKBONE_NORMAL_BLEND_FACTOR = 0.3;
  
  const frames = [];
  const numResidues = backboneNormals ? backboneNormals.length : 0;
  
  // Initial frame at t=0
  const t0 = 0;
  const p0 = curve.getPointAt(t0);
  const tangent0 = curve.getTangentAt(t0).normalize();
  
  // Determine initial normal
  let normal0;
  
  // Try to use backbone normal if available
  if (backboneNormals && backboneNormals.length > 0 && backboneNormals[0]) {
    normal0 = backboneNormals[0].clone().normalize();
    // Make sure it's perpendicular to tangent
    normal0.sub(tangent0.clone().multiplyScalar(normal0.dot(tangent0))).normalize();
  } else if (initialNormal) {
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
    
    // Get backbone normal for this position if available
    let targetNormal = null;
    if (backboneNormals && numResidues > 0) {
      const residueIdx = Math.min(Math.floor(t * numResidues), numResidues - 1);
      if (backboneNormals[residueIdx]) {
        targetNormal = backboneNormals[residueIdx].clone();
        // Make perpendicular to tangent
        targetNormal.sub(tangent.clone().multiplyScalar(targetNormal.dot(tangent)));
        if (targetNormal.lengthSq() > 1e-8) {
          targetNormal.normalize();
        } else {
          targetNormal = null;
        }
      }
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
    
    // Blend with backbone normal if available (for smoother transitions)
    if (targetNormal) {
      // Use the defined blend factor - backbone normal provides the "target" orientation
      normal.lerp(targetNormal, BACKBONE_NORMAL_BLEND_FACTOR).normalize();
    }
    
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
 * @param {Array} backboneNormals - Optional array of THREE.Vector3 normals from backbone
 * @returns {THREE.BufferGeometry} The ribbon geometry
 */
function createRibbonGeometry(curve, segments, secondaryStructure, colors, backboneNormals = null) {
  const frames = computeRotationMinimizingFrames(curve, segments, null, backboneNormals);
  
  // Geometry arrays
  const positions = [];
  const normals = [];
  const colorArray = [];
  const indices = [];
  
  for (let i = 0; i <= segments; i++) {
    const frame = frames[i];
    const t = i / segments;
    
    // Determine ribbon width and thickness based on secondary structure
    const ssIndex = Math.min(Math.floor(t * secondaryStructure.length), secondaryStructure.length - 1);
    const ss = secondaryStructure[ssIndex] || 'C';
    
    // Get color for this segment
    const colorIndex = Math.min(Math.floor(t * colors.length), colors.length - 1);
    const color = colors[colorIndex] || new THREE.Color(0xcccccc);
    
    if (ss === 'E') {
      // Beta sheet: Flat ribbon (rectangular cross-section)
      const width = 3.0;  // Wide for sheets
      const thickness = 0.2;  // Very thin for flat ribbon
      
      // Create a flat rectangular cross-section
      // Top edge
      const topLeft = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(-width / 2))
        .add(frame.binormal.clone().multiplyScalar(thickness / 2));
      const topRight = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(width / 2))
        .add(frame.binormal.clone().multiplyScalar(thickness / 2));
      
      // Bottom edge
      const bottomLeft = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(-width / 2))
        .add(frame.binormal.clone().multiplyScalar(-thickness / 2));
      const bottomRight = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(width / 2))
        .add(frame.binormal.clone().multiplyScalar(-thickness / 2));
      
      // Add vertices (4 corners of the ribbon)
      positions.push(topLeft.x, topLeft.y, topLeft.z);
      positions.push(topRight.x, topRight.y, topRight.z);
      positions.push(bottomLeft.x, bottomLeft.y, bottomLeft.z);
      positions.push(bottomRight.x, bottomRight.y, bottomRight.z);
      
      // Normals point up/down for flat surface
      const upNormal = frame.binormal.clone();
      const downNormal = frame.binormal.clone().negate();
      
      normals.push(upNormal.x, upNormal.y, upNormal.z);
      normals.push(upNormal.x, upNormal.y, upNormal.z);
      normals.push(downNormal.x, downNormal.y, downNormal.z);
      normals.push(downNormal.x, downNormal.y, downNormal.z);
      
      // Colors
      for (let j = 0; j < 4; j++) {
        colorArray.push(color.r, color.g, color.b);
      }
      
    } else if (ss === 'H') {
      // Alpha helix: Wider flat ribbon with slight rounding
      const width = 2.2;
      const thickness = 0.4;  // Slightly thicker than sheets
      
      // Create a flat rectangular cross-section
      const topLeft = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(-width / 2))
        .add(frame.binormal.clone().multiplyScalar(thickness / 2));
      const topRight = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(width / 2))
        .add(frame.binormal.clone().multiplyScalar(thickness / 2));
      
      const bottomLeft = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(-width / 2))
        .add(frame.binormal.clone().multiplyScalar(-thickness / 2));
      const bottomRight = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(width / 2))
        .add(frame.binormal.clone().multiplyScalar(-thickness / 2));
      
      // Add vertices
      positions.push(topLeft.x, topLeft.y, topLeft.z);
      positions.push(topRight.x, topRight.y, topRight.z);
      positions.push(bottomLeft.x, bottomLeft.y, bottomLeft.z);
      positions.push(bottomRight.x, bottomRight.y, bottomRight.z);
      
      // Normals
      const upNormal = frame.binormal.clone();
      const downNormal = frame.binormal.clone().negate();
      
      normals.push(upNormal.x, upNormal.y, upNormal.z);
      normals.push(upNormal.x, upNormal.y, upNormal.z);
      normals.push(downNormal.x, downNormal.y, downNormal.z);
      normals.push(downNormal.x, downNormal.y, downNormal.z);
      
      // Colors
      for (let j = 0; j < 4; j++) {
        colorArray.push(color.r, color.g, color.b);
      }
      
    } else {
      // Coil/loop: Narrow flat ribbon (like sheets but thinner)
      const width = 1.5;  // Narrower than sheets
      const thickness = 0.15;  // Very thin for flat look
      
      // Create a flat rectangular cross-section
      const topLeft = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(-width / 2))
        .add(frame.binormal.clone().multiplyScalar(thickness / 2));
      const topRight = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(width / 2))
        .add(frame.binormal.clone().multiplyScalar(thickness / 2));
      
      const bottomLeft = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(-width / 2))
        .add(frame.binormal.clone().multiplyScalar(-thickness / 2));
      const bottomRight = frame.position.clone()
        .add(frame.normal.clone().multiplyScalar(width / 2))
        .add(frame.binormal.clone().multiplyScalar(-thickness / 2));
      
      // Add vertices
      positions.push(topLeft.x, topLeft.y, topLeft.z);
      positions.push(topRight.x, topRight.y, topRight.z);
      positions.push(bottomLeft.x, bottomLeft.y, bottomLeft.z);
      positions.push(bottomRight.x, bottomRight.y, bottomRight.z);
      
      // Normals
      const upNormal = frame.binormal.clone();
      const downNormal = frame.binormal.clone().negate();
      
      normals.push(upNormal.x, upNormal.y, upNormal.z);
      normals.push(upNormal.x, upNormal.y, upNormal.z);
      normals.push(downNormal.x, downNormal.y, downNormal.z);
      normals.push(downNormal.x, downNormal.y, downNormal.z);
      
      // Colors
      for (let j = 0; j < 4; j++) {
        colorArray.push(color.r, color.g, color.b);
      }
    }
  }
  
  // Create indices - all types now use 4 vertices (flat ribbons)
  const verticesPerRing = 4;
  for (let i = 0; i < segments; i++) {
    // Create faces for the ribbon strip
    for (let j = 0; j < verticesPerRing - 1; j++) {
      const a = i * verticesPerRing + j;
      const b = a + 1;
      const c = a + verticesPerRing;
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
  smoothArray,
  computeRibbonNormalFromBackbone,
  computeRibbonNormalsFromBackbone
};
