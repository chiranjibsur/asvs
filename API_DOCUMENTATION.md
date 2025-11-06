# API Documentation

## Base URL
```
http://localhost:5000
```

## Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trajectory/meta` | GET | Get trajectory metadata |
| `/api/trajectory/frame/<frame>` | GET | Get atom coordinates for a frame |
| `/api/trajectory/residue_map` | GET | Get atom to residue mapping |
| `/api/trajectory/residue_meta` | GET | Get residue information table |
| `/api/trajectory/atoms` | GET | Get atom metadata |
| `/api/trajectory/ca/<frame>` | GET | Get C-alpha coordinates |
| `/api/hotspots/<frame>` | GET | Get hotspot values for a frame |

## Detailed API Reference

### Get Trajectory Metadata

**Endpoint:** `/api/trajectory/meta`  
**Method:** `GET`  
**Description:** Returns basic metadata about the loaded trajectory

**Response:**
```json
{
  "n_frames": 194,
  "n_atoms": 374,
  "n_residues": 374
}
```

**Fields:**
- `n_frames` (integer): Total number of frames in trajectory
- `n_atoms` (integer): Number of atoms in the system
- `n_residues` (integer): Number of residues in the system

**Example:**
```javascript
const meta = await fetch('/api/trajectory/meta').then(r => r.json());
console.log(`Frames: ${meta.n_frames}, Atoms: ${meta.n_atoms}`);
```

---

### Get Frame Coordinates

**Endpoint:** `/api/trajectory/frame/<frame>`  
**Method:** `GET`  
**Description:** Returns 3D coordinates for all atoms in a specific frame

**Parameters:**
- `frame` (integer, path): Frame number (0-indexed)

**Response:**
```json
{
  "frame": 0,
  "xyz": [
    [12.345, -5.678, 23.456],
    [13.456, -4.567, 24.567],
    ...
  ]
}
```

**Fields:**
- `frame` (integer): The requested frame number
- `xyz` (array): Array of [x, y, z] coordinates for each atom

**Notes:**
- Frame numbers are clamped to valid range [0, n_frames-1]
- Coordinates are in Ångströms (Å)
- Array length equals `n_atoms`

**Example:**
```javascript
const data = await fetch('/api/trajectory/frame/0').then(r => r.json());
const firstAtomPos = data.xyz[0];  // [x, y, z]
```

---

### Get Residue Mapping

**Endpoint:** `/api/trajectory/residue_map`  
**Method:** `GET`  
**Description:** Returns mapping from atom indices to residue numbers

**Response:**
```json
{
  "resnos": [1, 1, 1, 2, 2, 2, 3, 3, 3, ...]
}
```

**Fields:**
- `resnos` (array): Residue number for each atom (1-indexed)

**Notes:**
- Array length equals `n_atoms`
- Used to map atom-level data to residues
- Residue numbers may not be sequential

**Example:**
```javascript
const { resnos } = await fetch('/api/trajectory/residue_map').then(r => r.json());
const atomResidueNum = resnos[atomIndex];
```

---

### Get Residue Metadata

**Endpoint:** `/api/trajectory/residue_meta`  
**Method:** `GET`  
**Description:** Returns detailed information about each residue

**Response:**
```json
{
  "residues": [
    {
      "index": 0,
      "resnum": 1,
      "resname": "ALA",
      "chain": "A"
    },
    {
      "index": 1,
      "resnum": 2,
      "resname": "GLY",
      "chain": "A"
    },
    ...
  ]
}
```

**Fields:**
- `residues` (array): Array of residue objects
  - `index` (integer): 0-based residue index
  - `resnum` (integer): PDB residue number
  - `resname` (string): Three-letter residue code
  - `chain` (string): Chain identifier

**Example:**
```javascript
const { residues } = await fetch('/api/trajectory/residue_meta').then(r => r.json());
residues.forEach(res => {
  console.log(`${res.resname}${res.resnum} (Chain ${res.chain})`);
});
```

---

### Get Atom Metadata

**Endpoint:** `/api/trajectory/atoms`  
**Method:** `GET`  
**Description:** Returns atom information and covalent radii for bond detection

**Response:**
```json
{
  "atoms": [
    {
      "index": 0,
      "element": "C",
      "resnum": 1
    },
    {
      "index": 1,
      "element": "N",
      "resnum": 1
    },
    ...
  ],
  "covalent_radii": {
    "H": 0.31,
    "C": 0.76,
    "N": 0.71,
    "O": 0.66,
    "F": 0.57,
    "P": 1.07,
    "S": 1.05,
    "CL": 1.02
  }
}
```

**Fields:**
- `atoms` (array): Array of atom objects
  - `index` (integer): Atom index
  - `element` (string): Element symbol
  - `resnum` (integer): Residue number
- `covalent_radii` (object): Covalent radii in Ångströms by element

**Notes:**
- Used for client-side bond detection
- Bond typically exists if distance < sum of covalent radii × tolerance (e.g., 1.3)

**Example:**
```javascript
const { atoms, covalent_radii } = await fetch('/api/trajectory/atoms').then(r => r.json());

// Detect bond between atoms i and j
const r1 = covalent_radii[atoms[i].element] || 0.76;
const r2 = covalent_radii[atoms[j].element] || 0.76;
const maxDist = (r1 + r2) * 1.3;
const dist = distance(pos[i], pos[j]);
const isBonded = dist < maxDist;
```

---

### Get C-Alpha Coordinates

**Endpoint:** `/api/trajectory/ca/<frame>`  
**Method:** `GET`  
**Description:** Returns C-alpha (backbone) atom positions for ribbon visualization

**Parameters:**
- `frame` (integer, path): Frame number (0-indexed)

**Response:**
```json
{
  "frame": 0,
  "ca": [
    [10.123, -2.456, 15.789],
    [11.234, -1.345, 16.890],
    ...
  ]
}
```

**Fields:**
- `frame` (integer): The requested frame number
- `ca` (array): Array of [x, y, z] coordinates for C-alpha atoms

**Notes:**
- Falls back to backbone atoms if no CA atoms found
- Used for protein ribbon visualization
- Ordered sequentially along protein chain

**Example:**
```javascript
const { ca } = await fetch('/api/trajectory/ca/0').then(r => r.json());
// Create spline through ca positions for ribbon
const curve = new THREE.CatmullRomCurve3(
  ca.map(p => new THREE.Vector3(...p))
);
```

---

### Get Hotspot Values

**Endpoint:** `/api/hotspots/<frame>`  
**Method:** `GET`  
**Description:** Returns per-residue hotspot values for dynamic coloring

**Parameters:**
- `frame` (integer, path): Frame number (0-indexed)

**Response:**
```json
{
  "0": 0.051744,
  "1": 0.107239,
  "2": 0.0,
  "3": 0.189882,
  "4": 0.293869,
  ...
}
```

**Format:**
- Keys: Residue indices (as strings)
- Values: Hotspot values (typically 0.0 to 1.0)

**Error Response:**
```json
{
  "error": "frame 999 not found in viewer/hotspots_residue.json"
}
```

**Notes:**
- Values typically represent some computed property (e.g., flexibility, binding affinity)
- Used for color mapping: low values → blue, mid → white, high → red
- Missing residues default to 0.0

**Example:**
```javascript
const hotspots = await fetch('/api/hotspots/0').then(r => r.json());

// Map hotspot to color
function getHotspotColor(residueIndex) {
  const value = parseFloat(hotspots[residueIndex] || 0);
  // Interpolate between blue (0), white (0.5), red (1)
  if (value < 0.5) {
    return interpolate(BLUE, WHITE, value * 2);
  } else {
    return interpolate(WHITE, RED, (value - 0.5) * 2);
  }
}
```

---

## UI Routes

### Main Viewer
**Route:** `/viewer` or `/`  
**Description:** Points-based hotspot viewer with timeline

### Ball-and-Stick Viewer
**Route:** `/viewer/ballstick`  
**Description:** Ball-and-stick molecular representation

### Ribbon Viewer
**Route:** `/viewer/ribbon`  
**Description:** Protein ribbon (backbone) representation

### Static Files
**Route:** `/static/<path>`  
**Description:** Serves static assets (JS, CSS, images)

**Example:** `/static/lib/three.min.js`

### Viewer Files
**Route:** `/viewer/<filename>`  
**Description:** Serves files from viewer directory

**Example:** `/viewer/hotspots_residue.json`

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Successful request
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

Error responses include a JSON object with an `error` field:

```json
{
  "error": "Description of the error"
}
```

---

## Data Types

### Coordinate Format
All coordinates are arrays of three floating-point numbers:
```javascript
[x, y, z]  // Example: [12.345, -5.678, 23.456]
```

### Units
- **Coordinates**: Ångströms (Å)
- **Covalent Radii**: Ångströms (Å)
- **Hotspot Values**: Normalized 0.0 to 1.0

### Indexing
- **Frames**: 0-indexed (0 to n_frames-1)
- **Atoms**: 0-indexed (0 to n_atoms-1)
- **Residues (index)**: 0-indexed
- **Residues (resnum)**: 1-indexed (PDB numbering)

---

## Performance Considerations

### Caching
- Atom metadata (`/api/trajectory/atoms`) should be fetched once and cached
- Residue map and metadata rarely change, cache them
- Frame coordinates change frequently, cache selectively

### Throttling
- When animating, consider requesting every Nth frame
- Use requestAnimationFrame to sync with display refresh
- Implement frame pre-loading for smooth playback

### Compression
Responses are not gzip-compressed by default. Consider:
```python
from flask import Flask
from flask_compress import Compress

app = Flask(__name__)
Compress(app)
```

---

## Usage Examples

### Complete Frame Visualization
```javascript
async function visualizeFrame(frameNum) {
  // Get coordinates
  const { xyz } = await fetch(`/api/trajectory/frame/${frameNum}`).then(r => r.json());
  
  // Get hotspots
  const hotspots = await fetch(`/api/hotspots/${frameNum}`).then(r => r.json());
  
  // Get residue mapping (cached)
  const { resnos } = await getResnos();  // Cached function
  
  // Visualize
  xyz.forEach((pos, atomIdx) => {
    const residueIdx = resnos[atomIdx];
    const hotspotValue = parseFloat(hotspots[residueIdx] || 0);
    const color = getColor(hotspotValue);
    
    drawAtom(pos, color);
  });
}
```

### Animation Loop
```javascript
async function animateTrajectory(startFrame, endFrame, fps = 30) {
  const frameDelay = 1000 / fps;
  
  for (let frame = startFrame; frame <= endFrame; frame++) {
    await visualizeFrame(frame);
    await sleep(frameDelay);
  }
}
```

### Bond Detection
```javascript
async function detectBonds(positions) {
  const { atoms, covalent_radii } = await getAtoms();  // Cached
  const bonds = [];
  
  for (let i = 0; i < atoms.length; i++) {
    for (let j = i + 1; j < atoms.length; j++) {
      const r1 = covalent_radii[atoms[i].element] || 0.76;
      const r2 = covalent_radii[atoms[j].element] || 0.76;
      const maxDist = (r1 + r2) * 1.3;
      
      const dist = distance(positions[i], positions[j]);
      if (dist < maxDist && dist > 0.4) {
        bonds.push([i, j]);
      }
    }
  }
  
  return bonds;
}
```
