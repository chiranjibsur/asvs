# Scientific Documentation for siya-integration Branch

**Branch:** `siya-integration`  
**Purpose:** Dynamic Hotspot Detection in Molecular Dynamics Trajectories  
**Last Updated:** November 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Scientific Foundation](#scientific-foundation)
3. [Molecular Dynamics (MD) Simulation Data](#molecular-dynamics-md-simulation-data)
4. [Feature Extraction and Analysis](#feature-extraction-and-analysis)
5. [Machine Learning for Hotspot Detection](#machine-learning-for-hotspot-detection)
6. [Hotspot Detection Algorithm](#hotspot-detection-algorithm)
7. [Visualization and Interactivity](#visualization-and-interactivity)
8. [Data Structures and File Formats](#data-structures-and-file-formats)
9. [API Architecture and Endpoints](#api-architecture-and-endpoints)
10. [Implementation Details](#implementation-details)
11. [Future Directions](#future-directions)
12. [Scientific Applications](#scientific-applications)
13. [References and Further Reading](#references-and-further-reading)

---

## Overview

The `siya-integration` branch represents a comprehensive platform for detecting, analyzing, and visualizing **dynamic hotspots** in molecular dynamics (MD) trajectories. It bridges the gap between computational simulations and machine learning-based analysis by providing:

- **Real-time 3D visualization** of protein structures and dynamics
- **Dynamic hotspot detection** using anomaly scoring and machine learning
- **Interactive exploration** of protein flexibility, contacts, and conformational changes
- **Integration of multiple analytical techniques** (RMSF, tICA, VAMPnet, contact analysis)

### Key Significance

This system is crucial for:

1. **Protein Design**: Identifying regions amenable to engineering or mutation
2. **Drug Discovery**: Locating potential binding sites and allosteric regions
3. **Disease Mechanism Studies**: Understanding how mutations affect protein dynamics
4. **Structural Biology**: Analyzing conformational changes and protein function

---

## Scientific Foundation

### What are Molecular Dynamics (MD) Simulations?

**Molecular Dynamics** simulations compute the time-dependent behavior of molecular systems by solving Newton's equations of motion for all atoms:

```
F = ma  →  Force = mass × acceleration
```

For biomolecules, forces come from:
- **Bonded interactions**: Bond stretching, angle bending, torsional rotation
- **Non-bonded interactions**: Van der Waals forces, electrostatic interactions
- **Solvent effects**: Implicit or explicit water molecules

**Output**: A trajectory of atomic positions over time (typically nanoseconds to microseconds)

### Why Study Protein Dynamics?

Proteins are not static structures—they fluctuate, breathe, and undergo conformational changes essential for their biological function. Understanding these dynamics reveals:

- **Functional mechanisms**: How proteins bind ligands, catalyze reactions, or transduce signals
- **Allosteric regulation**: How distant sites communicate through conformational changes
- **Stability and flexibility**: Which regions are rigid (stable) vs. flexible (dynamic)
- **Binding sites**: Transient pockets that may serve as drug targets

---

## Molecular Dynamics (MD) Simulation Data

### Core Data Files

#### 1. Topology File (`topology.pdb`)

**Purpose**: Defines the molecular structure and connectivity

**Contents**:
- Atom coordinates (initial structure)
- Atom types (C, N, O, S, etc.)
- Residue information (amino acid sequence)
- Chain identifiers
- Connectivity (bonds between atoms)

**Format**: Protein Data Bank (PDB) format

**In this implementation**:
- 374 atoms (representing C-alpha atoms only for simplicity)
- Single protein chain
- Auto-generated to match trajectory dimensions

**Scientific Relevance**: The topology provides the "blueprint" of the molecule, allowing us to:
- Map atom indices to residues
- Identify backbone vs. sidechain atoms
- Understand secondary structure elements

#### 2. Trajectory File (`trajectory.xtc`)

**Purpose**: Contains atomic positions over time

**Contents**:
- 3D coordinates for all atoms at each time step
- 194 frames in current dataset
- Compressed format (Gromacs XTC)

**Temporal Resolution**: Each frame represents a snapshot in time (typically every 10-100 picoseconds)

**Format**: XTC (Gromacs compressed trajectory format)

**Scientific Relevance**: The trajectory captures:
- Conformational fluctuations
- Domain movements
- Binding/unbinding events
- Structural transitions

### Coordinate System and Units

- **Spatial Units**: Ångströms (Å), where 1 Å = 10⁻¹⁰ meters
- **Coordinate System**: Cartesian (x, y, z) coordinates
- **Reference Frame**: As defined in the initial PDB structure
- **Typical Protein Size**: 20-50 Å diameter for small proteins

---

## Feature Extraction and Analysis

To understand protein dynamics, we extract **features** from the raw trajectory data. These features capture different aspects of molecular behavior.

### 1. Root Mean Square Deviation (RMSD)

**Definition**: Measures the average distance between corresponding atoms in two structures

**Formula**:
```
RMSD = sqrt( (1/N) * Σ(rᵢ - r̂ᵢ)² )
```
where:
- N = number of atoms
- rᵢ = position of atom i in current frame
- r̂ᵢ = position of atom i in reference frame

**Units**: Ångströms (Å)

**Interpretation**:
- Low RMSD (< 2 Å): Similar conformations
- High RMSD (> 5 Å): Significant structural change
- Time-dependent RMSD tracks stability vs. transitions

**Scientific Use**:
- Assessing simulation convergence
- Identifying stable vs. transitional states
- Comparing conformations

**Implementation**: Calculated using MDAnalysis RMSD module

### 2. Root Mean Square Fluctuation (RMSF)

**Definition**: Measures the flexibility of individual residues over the entire trajectory

**Formula**:
```
RMSF(residue i) = sqrt( ⟨(rᵢ(t) - ⟨rᵢ⟩)²⟩ₜ )
```
where:
- rᵢ(t) = position of residue i at time t
- ⟨rᵢ⟩ = average position over all frames
- ⟨...⟩ₜ = time average

**Units**: Ångströms (Å)

**Interpretation**:
- Low RMSF (< 1 Å): Rigid, stable regions (often functional sites or structural cores)
- High RMSF (> 3 Å): Flexible regions (often loops, termini, or disordered regions)

**Scientific Use**:
- Identifying flexible loops and hinges
- Locating potential binding sites
- Comparing with experimental B-factors
- Understanding conformational entropy

**Implementation**:
```python
# scripts/calculate_rmsf.py
from MDAnalysis.analysis.rms import RMSF
ca_atoms = universe.select_atoms("name CA")
rmsf_analysis = RMSF(ca_atoms).run()
```

**Data File**: `viewer/rmsf_residue.json`

### 3. Radius of Gyration (Rg)

**Definition**: Measures the compactness of the protein structure

**Formula**:
```
Rg = sqrt( Σmᵢ(rᵢ - rcm)² / Σmᵢ )
```
where:
- mᵢ = mass of atom i
- rᵢ = position of atom i
- rcm = center of mass

**Units**: Ångströms (Å)

**Interpretation**:
- Increasing Rg: Protein unfolding or expansion
- Decreasing Rg: Protein compaction or folding
- Constant Rg: Stable, folded state

**Scientific Use**:
- Monitoring protein folding/unfolding
- Detecting domain movements
- Assessing global structural stability

### 4. C-alpha Contact Analysis

**Definition**: Identifies residue-residue contacts based on C-alpha distances

**Cutoff Distance**: Typically 8-10 Å

**Formula**:
```
Contact(i,j) = 1 if distance(CAᵢ, CAⱼ) < cutoff, else 0
Contact Frequency = Σframes Contact(i,j) / Total Frames
```

**Interpretation**:
- High frequency (> 0.7): Persistent structural contact
- Medium frequency (0.3-0.7): Transient interaction
- Low frequency (< 0.3): Rare or no contact

**Scientific Use**:
- Identifying structural domains
- Detecting allosteric pathways
- Understanding protein communication networks
- Finding correlated motions

**Implementation**:
```python
# scripts/calculate_contacts.py
cutoff = 8.0  # Ångströms
for frame in trajectory:
    distances = calculate_pairwise_distances(ca_atoms)
    contacts = distances < cutoff
    contact_frequency += contacts
contact_frequency /= n_frames
```

**Data File**: `viewer/contacts.json`

### 5. Dihedral Angles (Φ and Ψ)

**Definition**: Backbone torsion angles defining protein conformation

**Phi (Φ)**: C-N-Cα-C torsion angle  
**Psi (Ψ)**: N-Cα-C-N torsion angle

**Range**: -180° to +180°

**Ramachandran Plot**: 2D plot of Φ vs. Ψ showing allowed regions

**Interpretation**:
- α-helix: Φ ≈ -60°, Ψ ≈ -45°
- β-sheet: Φ ≈ -120°, Ψ ≈ +120°
- Other values: Loops, turns, or disallowed regions

**Scientific Use**:
- Identifying secondary structure transitions
- Validating structure quality
- Detecting conformational changes

---

## Machine Learning for Hotspot Detection

The system employs advanced machine learning techniques to identify **dynamic hotspots**—regions of the protein that exhibit significant, functionally relevant dynamics.

### 1. Time-lagged Independent Component Analysis (tICA)

#### What is tICA?

**tICA** is a dimensionality reduction technique that identifies **slow collective motions** in molecular dynamics trajectories. Unlike PCA (Principal Component Analysis), which finds directions of maximum variance, tICA finds directions of maximum autocorrelation (slow motions).

#### Why tICA?

**Slow motions are functionally important**:
- They correspond to large-scale conformational changes
- They often relate to biological function (e.g., binding, catalysis)
- They capture the essential dynamics on long timescales

#### Mathematical Foundation

Given feature vectors x(t) from the trajectory:

1. **Compute time-lagged covariance matrices**:
   ```
   C₀ = ⟨x(t) ⊗ x(t)⟩
   Cτ = ⟨x(t) ⊗ x(t+τ)⟩
   ```
   where τ is the lag time (e.g., 10-50 frames)

2. **Solve generalized eigenvalue problem**:
   ```
   Cτ vᵢ = λᵢ C₀ vᵢ
   ```

3. **tICA components**: Eigenvectors vᵢ ordered by eigenvalues λᵢ

4. **Interpretation**:
   - λᵢ ≈ 1: Very slow motion (long autocorrelation)
   - λᵢ ≈ 0: Fast fluctuation (short autocorrelation)

#### Features Used for tICA

Typical input features include:
- All inter-residue C-alpha distances
- Backbone dihedral angles (Φ, Ψ)
- Selected sidechain dihedrals
- Contact indicators

**Dimensionality**: For a protein with N residues:
- C-alpha distances: ~N(N-1)/2 features
- Dihedrals: 2N features
- **Total**: Often thousands of features

**tICA output**: Typically 2-10 components capturing >90% of slow dynamics

#### Scientific Interpretation

**Top tICA components reveal**:
- Domain movements (e.g., hinge motions)
- Allosteric pathways
- Conformational transitions between states
- Collective breathing motions

**Per-residue tICA weights**: Show which residues contribute most to each slow motion

### 2. VAMPnet (Variational Approach for Markov Processes)

#### What is VAMPnet?

**VAMPnet** is a deep learning approach for discovering **metastable states** in molecular trajectories. It extends the VAMP framework by using neural networks to learn optimal feature representations.

#### Metastable States

**Definition**: Long-lived conformational states separated by high energy barriers

**Examples**:
- Open vs. closed conformations of enzymes
- Bound vs. unbound states
- Different folding intermediates

**Significance**: Understanding metastable states reveals:
- The functional energy landscape
- Transition pathways between states
- Timescales of conformational changes

#### How VAMPnet Works

1. **Neural Network Architecture**:
   - Input: Raw or pre-processed features (coordinates, distances, etc.)
   - Hidden layers: Learn optimal feature transformation
   - Output: Soft state assignments (probabilities for each metastable state)

2. **VAMP Loss Function**:
   - Maximizes the sum of eigenvalues of the Koopman operator
   - Equivalent to finding states with slowest transitions
   - Trained using time-lagged pairs of trajectory frames

3. **Training Process**:
   ```
   For each pair (x(t), x(t+τ)):
       z(t) = Network(x(t))      # State probabilities at time t
       z(t+τ) = Network(x(t+τ))  # State probabilities at time t+τ
       Loss = -VAMP_score(z(t), z(t+τ))
       Update network weights
   ```

4. **Output**:
   - K metastable states (typically 2-10 states)
   - Soft assignments: probability of being in each state
   - Transition probability matrix

#### Integration with Hotspot Detection

**VAMPnet soft assignments** are used to:
- Identify frames in transition between states (high uncertainty)
- Compute state-specific hotspot scores
- Detect allosteric pathways connecting states

**Entropy of state assignments**:
```
Entropy = -Σᵢ pᵢ log(pᵢ)
```
- High entropy: Uncertain state, likely a transition
- Low entropy: Clearly in one metastable state

#### Scientific Applications

- **Protein folding**: Identify folding intermediates
- **Allostery**: Map communication pathways
- **Ligand binding**: Characterize bound/unbound states
- **Conformational selection**: Understand binding mechanisms

### 3. Anomaly Detection and Hotspot Scoring

#### Composite Anomaly Score

The system combines multiple metrics to compute a **hotspot score** for each residue in each frame:

```
Hotspot Score = w₁ × Rarity + w₂ × Transition Surprise + w₃ × Local Density
```

where w₁, w₂, w₃ are weights (often equal or tuned empirically).

#### Component 1: Rarity Score

**Definition**: How unusual is the current conformation?

**Method**: k-Nearest Neighbors (k-NN) in tICA space

**Calculation**:
```python
# For each frame:
tica_coords = tica_model.transform(features)
distances, indices = knn.kneighbors(tica_coords)
rarity = np.mean(distances, axis=1)  # Average distance to k neighbors
```

**Interpretation**:
- High rarity: This conformation is far from typical states
- Low rarity: Common, frequently visited conformation

**Normalization**: Usually scaled to [0, 1] using min-max scaling

#### Component 2: Transition Surprise

**Definition**: How unexpected is the transition from the previous frame?

**Method**: Analyze tICA trajectory velocity and direction

**Calculation**:
```python
# Velocity in tICA space
velocity = tica_coords[t] - tica_coords[t-1]
speed = np.linalg.norm(velocity)

# Compare to historical transitions
typical_speed = np.percentile(all_speeds, 50)
surprise = speed / typical_speed
```

**Interpretation**:
- High surprise: Rapid, unusual conformational change
- Low surprise: Typical fluctuation

**Alternative approach**: Use VAMPnet state transition probabilities

#### Component 3: Local Density (k-NN Distance)

**Definition**: How isolated is this conformation in conformational space?

**Method**: Distance to k-th nearest neighbor

**Calculation**:
```python
knn = NearestNeighbors(n_neighbors=k+1)
knn.fit(tica_coords)
distances, _ = knn.kneighbors(tica_coords)
local_density = distances[:, -1]  # Distance to k-th neighbor
```

**Interpretation**:
- High k-NN distance: Isolated, rare conformation
- Low k-NN distance: Dense region, frequently visited

#### Per-Residue Hotspot Mapping

The frame-level anomaly score is mapped to individual residues:

**Method 1: tICA Component Contributions**
```python
# Weight residues by their contribution to active tICA components
for residue in protein:
    score = sum(abs(tica_weights[residue, ic]) * anomaly_score[ic] 
                for ic in top_components)
```

**Method 2: RMSF-based**
```python
# High RMSF residues in anomalous frames get higher scores
score = rmsf[residue] * frame_anomaly_score
```

**Method 3: Contact Changes**
```python
# Residues with changing contacts in anomalous frames
contact_change = abs(contacts[t] - contacts[t-1])
score = contact_change[residue] * frame_anomaly_score
```

#### Normalization and Visualization

**Final processing**:
1. Compute per-residue scores for each frame
2. Normalize to [0, 1] range
3. Apply smoothing (optional): temporal or spatial
4. Map to color scale: Blue (0) → White (0.5) → Red (1)

**Output**: `viewer/hotspots_residue.json`
```json
{
  "frame_0": {
    "0": 0.051744,
    "1": 0.107239,
    ...
  },
  "frame_1": { ... }
}
```

---

## Hotspot Detection Algorithm

### Complete Pipeline

```
1. Load MD Trajectory
   ├─ topology.pdb (structure)
   └─ trajectory.xtc (dynamics)
   
2. Feature Extraction
   ├─ RMSD calculation
   ├─ RMSF per residue
   ├─ Radius of gyration
   ├─ CA-CA contacts
   └─ Dihedral angles (Φ, Ψ)
   
3. Dimensionality Reduction
   ├─ Feature matrix (n_frames × n_features)
   ├─ tICA with lag time τ
   └─ Select top k components (k ≈ 5-10)
   
4. Metastable State Analysis (Optional)
   ├─ VAMPnet training
   ├─ Soft state assignments
   └─ Transition matrix
   
5. Anomaly Detection
   ├─ k-NN rarity in tICA space
   ├─ Transition surprise score
   └─ Local density estimation
   
6. Per-Residue Hotspot Scoring
   ├─ Map frame anomalies to residues
   ├─ Weight by tICA contributions
   ├─ Normalize to [0, 1]
   └─ Generate hotspots_residue.json
   
7. Visualization
   ├─ Load trajectory in viewer
   ├─ Apply hotspot colors per frame
   └─ Interactive exploration
```

### Pseudocode

```python
# Simplified hotspot detection pipeline

# 1. Load trajectory
universe = MDAnalysis.Universe('topology.pdb', 'trajectory.xtc')

# 2. Extract features
features = extract_features(universe)
# Shape: (n_frames, n_features)

# 3. Dimensionality reduction with tICA
tica = tICA(lag_time=10, n_components=5)
tica_coords = tica.fit_transform(features)
# Shape: (n_frames, 5)

# 4. VAMPnet (optional)
vampnet = VAMPnet(n_states=4)
vampnet.train(features, lag_time=10)
state_probs = vampnet.predict(features)
# Shape: (n_frames, 4)

# 5. Anomaly detection
knn = NearestNeighbors(n_neighbors=20)
knn.fit(tica_coords)
distances, _ = knn.kneighbors(tica_coords)

rarity = np.mean(distances, axis=1)
velocities = np.linalg.norm(np.diff(tica_coords, axis=0), axis=1)
surprise = velocities / np.median(velocities)
local_density = distances[:, -1]

# Combine scores
anomaly_score = (
    normalize(rarity) + 
    normalize(surprise) + 
    normalize(local_density)
) / 3

# 6. Map to residues
hotspots = {}
for frame in range(n_frames):
    residue_scores = {}
    for residue in range(n_residues):
        # Weight by tICA contribution
        contribution = np.sum(np.abs(tica.components_[:, residue_features]))
        score = anomaly_score[frame] * contribution
        residue_scores[str(residue)] = normalize(score)
    hotspots[f"frame_{frame}"] = residue_scores

# 7. Save
save_json(hotspots, 'hotspots_residue.json')
```

### Parameter Selection

**Critical parameters**:

1. **tICA lag time (τ)**: 
   - Too small: Captures fast, unimportant motions
   - Too large: Loses temporal resolution
   - **Recommended**: 10-50 frames (1-5 ns for typical simulations)
   - **Selection method**: Implied timescales plot

2. **Number of tICA components**:
   - Too few: Miss important motions
   - Too many: Include noise
   - **Recommended**: 5-10 components
   - **Selection method**: Cumulative explained correlation

3. **k-NN parameter (k)**:
   - Too small: Sensitive to noise
   - Too large: Oversmoothing
   - **Recommended**: k = 10-50
   - **Selection method**: Elbow plot of distance vs. k

4. **VAMPnet states**:
   - **Recommended**: 2-6 states for most proteins
   - **Selection method**: VAMP-2 score vs. number of states

---

## Visualization and Interactivity

### Three.js 3D Molecular Viewer

#### Rendering Modes

**1. Points Viewer** (`/viewer`)
- **Technology**: WebGL point cloud
- **Performance**: Excellent for large systems
- **Use case**: Rapid exploration, animation
- **Features**: Frame scrubbing, play/pause, tooltips

**2. Ball-and-Stick Viewer** (`/viewer/ballstick`)
- **Technology**: Sphere + cylinder geometries
- **Accuracy**: Atomic-level detail
- **Use case**: Detailed structural analysis
- **Features**: Bond visualization, clipping planes, distance measurement

**3. Ribbon Viewer** (`/viewer/ribbon`)
- **Technology**: CatmullRomCurve3 tube geometry
- **Focus**: Protein backbone
- **Use case**: Secondary structure emphasis
- **Features**: Smooth interpolation, export to PNG

### Color Mapping System

#### Hotspot Color Scale

```
Value   Color    RGB           Meaning
0.0     Blue     (11,92,255)   Low activity, stable
0.5     White    (255,255,255) Medium activity
1.0     Red      (255,43,43)   High activity, hotspot
```

**Interpolation**:
```javascript
function getHotspotColor(value) {
  const blue = [11, 92, 255];
  const white = [255, 255, 255];
  const red = [255, 43, 43];
  
  if (value < 0.5) {
    return interpolate(blue, white, value * 2);
  } else {
    return interpolate(white, red, (value - 0.5) * 2);
  }
}
```

### Interactive Features

#### Residue Information Panel

**Activated by**: Hover or click on atom/residue

**Displayed Information**:
- Residue name (e.g., "ALA", "GLY", "TRP")
- Residue number (PDB numbering)
- Chain identifier
- Current hotspot value (frame-specific)
- RMSF (flexibility over trajectory)
- tICA component contributions
- Contact partners
- Atom coordinates (x, y, z)

#### Timeline Controls

**Frame Slider**:
- Range: 0 to n_frames - 1
- Real-time update: Scrubbing changes visualization instantly
- Hotspot values update per frame

**Play/Pause Animation**:
- Configurable FPS (default: 10-30 fps)
- Loop: Continuous playback
- Smooth interpolation option (future)

#### Camera Controls (OrbitControls)

- **Rotate**: Left-click + drag
- **Pan**: Right-click + drag
- **Zoom**: Mouse wheel or pinch
- **Reset**: Double-click (future)

### Data Fetching Strategy

**Efficient Loading**:
```javascript
// Cache static data
const residueMap = await fetch('/api/trajectory/residue_map').then(r => r.json());
const residueMeta = await fetch('/api/trajectory/residue_meta').then(r => r.json());
const atoms = await fetch('/api/trajectory/atoms').then(r => r.json());

// Dynamic per-frame data
async function loadFrame(frameNum) {
  const [coords, hotspots] = await Promise.all([
    fetch(`/api/trajectory/frame/${frameNum}`).then(r => r.json()),
    fetch(`/api/hotspots/${frameNum}`).then(r => r.json())
  ]);
  updateVisualization(coords, hotspots);
}
```

---

## Data Structures and File Formats

### File Inventory

| File | Format | Purpose | Size | Update Frequency |
|------|--------|---------|------|------------------|
| `topology.pdb` | PDB | Molecular structure | ~50 KB | Static |
| `trajectory.xtc` | XTC | Atomic coordinates over time | ~5 MB | Static |
| `hotspots_residue.json` | JSON | Per-residue hotspot scores | ~500 KB | Computed once |
| `rmsf_residue.json` | JSON | Per-residue flexibility | ~10 KB | Computed once |
| `contacts.json` | JSON | Residue contact network | ~50 KB | Computed once |
| `.trajectory.xtc_offsets.npz` | NPZ | MDAnalysis frame index cache | ~5 KB | Auto-generated |

### Data Format Specifications

#### 1. `hotspots_residue.json`

**Structure**:
```json
{
  "frame_0": {
    "0": 0.051744,
    "1": 0.107239,
    "2": 0.0,
    ...
  },
  "frame_1": { ... },
  ...
}
```

**Fields**:
- **Outer keys**: `"frame_N"` where N is 0-indexed frame number
- **Inner keys**: Residue indices (0-indexed) as strings
- **Values**: Hotspot scores (float, 0.0 to 1.0)

**Missing residues**: Default to 0.0 (no hotspot)

**Usage**:
```javascript
const hotspots = await fetch('/api/hotspots/42').then(r => r.json());
const residue10Score = parseFloat(hotspots["10"] || 0.0);
```

#### 2. `rmsf_residue.json`

**Structure**:
```json
{
  "min": 0.234,
  "max": 4.567,
  "normalized": {
    "0": 0.1234,
    "1": 0.5678,
    ...
  }
}
```

**Fields**:
- `min`, `max`: Original RMSF range in Ångströms
- `normalized`: Per-residue RMSF normalized to [0, 1]

**Scientific Interpretation**:
- High RMSF: Flexible loop, potential binding site
- Low RMSF: Rigid core, structural element

#### 3. `contacts.json`

**Structure**:
```json
{
  "cutoff_angstrom": 8.0,
  "n_frames": 194,
  "contacts": [
    {
      "residue1": 5,
      "residue2": 123,
      "frequency": 0.987
    },
    ...
  ]
}
```

**Fields**:
- `cutoff_angstrom`: Distance threshold for contact
- `n_frames`: Total frames analyzed
- `contacts`: Array of persistent contacts (frequency > 0.5)
  - `residue1`, `residue2`: Residue indices (0-indexed)
  - `frequency`: Fraction of frames with contact (0.0 to 1.0)

**Scientific Interpretation**:
- frequency > 0.9: Structural contact (secondary structure)
- frequency 0.5-0.9: Semi-persistent interaction
- High contact density: Domain cores or binding interfaces

#### 4. Trajectory Metadata (API Response)

**`/api/trajectory/meta`**:
```json
{
  "n_frames": 194,
  "n_atoms": 374,
  "n_residues": 374
}
```

**`/api/trajectory/residue_meta`**:
```json
{
  "residues": [
    {
      "index": 0,
      "resnum": 1,
      "resname": "ALA",
      "chain": "A"
    },
    ...
  ]
}
```

---

## API Architecture and Endpoints

### RESTful API Design

**Base URL**: `http://localhost:5000`

**Design Principles**:
- Stateless: Each request is independent
- Cacheable: Static metadata can be cached client-side
- Predictable: Consistent URL patterns
- JSON-only: All responses are JSON formatted

### Endpoint Reference

#### 1. Trajectory Metadata

**`GET /api/trajectory/meta`**

**Purpose**: Get basic trajectory information

**Response**:
```json
{
  "n_frames": 194,
  "n_atoms": 374,
  "n_residues": 374
}
```

**Use case**: Initialize viewer, validate frame ranges

---

#### 2. Frame Coordinates

**`GET /api/trajectory/frame/<int:frame>`**

**Purpose**: Get 3D coordinates for all atoms in a specific frame

**Parameters**:
- `frame` (path, int): Frame number (0 to n_frames-1), clamped to valid range

**Response**:
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

**Units**: Ångströms (Å)

**Array length**: n_atoms

**Scientific use**: Render atoms, calculate distances

---

#### 3. Residue Mapping

**`GET /api/trajectory/residue_map`**

**Purpose**: Map atom indices to residue numbers

**Response**:
```json
{
  "resnos": [1, 1, 1, 2, 2, 2, 3, 3, 3, ...]
}
```

**Indexing**:
- Array index: Atom index (0-indexed)
- Array value: Residue number (1-indexed, PDB convention)

**Scientific use**: Aggregate atom properties to residue level

---

#### 4. Residue Metadata

**`GET /api/trajectory/residue_meta`**

**Purpose**: Get detailed residue information

**Response**:
```json
{
  "residues": [
    {
      "index": 0,
      "resnum": 1,
      "resname": "ALA",
      "chain": "A"
    },
    ...
  ]
}
```

**Fields**:
- `index`: 0-based residue index (for arrays)
- `resnum`: PDB residue number (1-based, may have gaps)
- `resname`: Three-letter amino acid code
- `chain`: Chain identifier (usually "A", "B", etc.)

**Scientific use**: Display residue names, identify chains

---

#### 5. Atom Metadata

**`GET /api/trajectory/atoms`**

**Purpose**: Get atom types and covalent radii for bond detection

**Response**:
```json
{
  "atoms": [
    {
      "index": 0,
      "element": "C",
      "resnum": 1
    },
    ...
  ],
  "covalent_radii": {
    "H": 0.31,
    "C": 0.76,
    "N": 0.71,
    "O": 0.66,
    ...
  }
}
```

**Scientific use**: 
- Bond detection: distance < (r1 + r2) × 1.3
- Element-based coloring (CPK)

---

#### 6. C-alpha Coordinates

**`GET /api/trajectory/ca/<int:frame>`**

**Purpose**: Get backbone (C-alpha) coordinates for ribbon visualization

**Response**:
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

**Array length**: n_residues (one CA per residue)

**Scientific use**: 
- Ribbon/cartoon visualization
- Backbone tracing
- Secondary structure representation

---

#### 7. Hotspot Values

**`GET /api/hotspots/<int:frame>`**

**Purpose**: Get per-residue hotspot scores for a specific frame

**Response**:
```json
{
  "0": 0.051744,
  "1": 0.107239,
  "2": 0.0,
  ...
}
```

**Keys**: Residue indices (0-based) as strings  
**Values**: Hotspot scores (0.0 to 1.0)

**Scientific interpretation**:
- 0.0-0.3: Low activity (blue)
- 0.3-0.7: Moderate activity (white)
- 0.7-1.0: High activity, hotspot (red)

**Error handling**:
```json
{
  "error": "frame 999 not found in viewer/hotspots_residue.json"
}
```

---

### API Usage Patterns

#### Initial Load (One-time)

```javascript
// Fetch static metadata
const [meta, residueMap, residueMeta, atoms] = await Promise.all([
  fetch('/api/trajectory/meta').then(r => r.json()),
  fetch('/api/trajectory/residue_map').then(r => r.json()),
  fetch('/api/trajectory/residue_meta').then(r => r.json()),
  fetch('/api/trajectory/atoms').then(r => r.json())
]);

// Cache for reuse
window.cachedData = { meta, residueMap, residueMeta, atoms };
```

#### Frame Update (Per-frame)

```javascript
async function updateFrame(frameNum) {
  const [coords, hotspots] = await Promise.all([
    fetch(`/api/trajectory/frame/${frameNum}`).then(r => r.json()),
    fetch(`/api/hotspots/${frameNum}`).then(r => r.json())
  ]);
  
  // Update visualization
  renderFrame(coords.xyz, hotspots);
}
```

#### Animation Loop

```javascript
async function animate(startFrame, endFrame, fps) {
  for (let frame = startFrame; frame <= endFrame; frame++) {
    await updateFrame(frame);
    await sleep(1000 / fps);
  }
}
```

---

## Implementation Details

### Backend Stack

**Flask Application** (`app.py`):
```python
from flask import Flask, jsonify
from trajectory_adapter import TrajectoryAdapter

app = Flask(__name__)
adapter = TrajectoryAdapter()  # Singleton pattern

@app.route('/api/trajectory/frame/<int:frame>')
def get_frame(frame):
    xyz = adapter.get_frame_coordinates(frame)
    return jsonify({"frame": frame, "xyz": xyz.tolist()})
```

**TrajectoryAdapter** (`trajectory_adapter.py`):
- Wraps MDAnalysis Universe
- Singleton pattern: Loads trajectory once
- Provides clean API for coordinate extraction
- Handles element detection and normalization

**Key Technologies**:
- **Flask** 2.0+: Web framework
- **MDAnalysis** 2.0+: Trajectory parsing
- **NumPy** 1.21+: Numerical operations
- **SciPy**: Distance calculations (contacts)

### Frontend Stack

**Core Technologies**:
- **Three.js** r128+: WebGL rendering
- **Vanilla JavaScript**: No framework overhead
- **HTML5**: Modern web standards

**Rendering Pipeline**:
```javascript
// 1. Initialize scene
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, width/height, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });

// 2. Create geometry
const geometry = new THREE.BufferGeometry();
const positions = new Float32Array(n_atoms * 3);
const colors = new Float32Array(n_atoms * 3);

// 3. Update per frame
function updateFrame(coords, hotspots) {
  coords.forEach((pos, i) => {
    positions[i*3] = pos[0];
    positions[i*3+1] = pos[1];
    positions[i*3+2] = pos[2];
    
    const color = getHotspotColor(hotspots[residueMap[i]]);
    colors[i*3] = color.r;
    colors[i*3+1] = color.g;
    colors[i*3+2] = color.b;
  });
  
  geometry.attributes.position.needsUpdate = true;
  geometry.attributes.color.needsUpdate = true;
}

// 4. Render loop
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
```

### Performance Optimizations

**1. Lazy Loading**:
- Trajectory loaded once on server startup
- MDAnalysis creates frame index for fast seeking

**2. Client-Side Caching**:
- Atom metadata fetched once
- Residue map cached in memory
- Hotspot data cached per frame

**3. Buffer Reuse**:
- Three.js geometries updated in-place
- No object creation/destruction per frame

**4. Parallel Requests**:
- Coordinates and hotspots fetched simultaneously
- Multiple frames pre-loaded (future)

**5. JSON Compression** (future):
- Enable gzip compression on server
- Binary formats for coordinates (MessagePack)

### Calculation Scripts

**RMSF Calculation** (`scripts/calculate_rmsf.py`):
```python
import MDAnalysis as mda
from MDAnalysis.analysis.rms import RMSF

u = mda.Universe("viewer/topology.pdb", "viewer/trajectory.xtc")
ca = u.select_atoms("name CA")
rmsf = RMSF(ca).run()

# Normalize and save
rmsf_dict = normalize_rmsf(rmsf.results.rmsf)
save_json(rmsf_dict, "viewer/rmsf_residue.json")
```

**Contact Calculation** (`scripts/calculate_contacts.py`):
```python
from scipy.spatial.distance import pdist, squareform

contact_freq = np.zeros((n_residues, n_residues))

for ts in u.trajectory:
    positions = ca.positions
    dist_matrix = squareform(pdist(positions))
    
    # Find contacts < 8.0 Å, excluding neighbors
    contacts = (dist_matrix < 8.0) & (dist_matrix > 0)
    contact_freq += contacts

contact_freq /= len(u.trajectory)

# Filter and save top contacts
top_contacts = filter_top_contacts(contact_freq, threshold=0.5)
save_json(top_contacts, "viewer/contacts.json")
```

---

## Future Directions

### Phase 1: Enhanced Residue Interaction

**Goal**: Deeper interactive analysis of individual residues

**Features**:
1. **Click-to-Inspect**:
   - Detailed residue panel with:
     - RMSF value and interpretation
     - Hotspot trajectory (plot over time)
     - tICA component contributions
     - Top contact partners
     - Secondary structure assignment
   
2. **Residue Selection**:
   - Multi-select residues
   - Highlight selected in all frames
   - Export selection coordinates

3. **Comparison Mode**:
   - Compare two residues side-by-side
   - Correlation plots
   - Distance evolution

**Implementation Priority**: High  
**Estimated Effort**: 2-3 weeks

### Phase 2: Real-Time ML Inference

**Goal**: Live hotspot computation during trajectory exploration

**Features**:
1. **On-Demand tICA Projection**:
   - Compute tICA coordinates for uploaded trajectories
   - Interactive lag time selection
   
2. **Dynamic Hotspot Recomputation**:
   - Adjust anomaly detection parameters
   - See results update in real-time
   
3. **Custom Feature Selection**:
   - Choose which features to include in analysis
   - Compare different feature sets

**Technologies**:
- **TensorFlow.js**: Client-side ML inference
- **WebWorkers**: Background computation
- **Streaming**: Progressive result updates

**Implementation Priority**: Medium  
**Estimated Effort**: 4-6 weeks

### Phase 3: Advanced Visualization Layers

**Goal**: Multi-modal visualization of protein dynamics

**Features**:
1. **RMSF Bands**:
   - Tube thickness proportional to RMSF
   - Color-coded flexibility zones
   
2. **Contact Network Overlay**:
   - Draw lines between contacting residues
   - Line thickness = contact frequency
   - Highlight allosteric pathways
   
3. **tICA Projection View**:
   - 2D scatter plot of tICA components
   - Click points to jump to frames
   - Trajectory path overlay
   - State boundaries (Voronoi cells)

4. **Free Energy Surface**:
   - Heatmap of tICA space
   - Energy barriers and basins
   - Minimum free energy pathways

**Implementation Priority**: High  
**Estimated Effort**: 3-4 weeks

### Phase 4: Metastable State Visualization

**Goal**: Integrate VAMPnet state assignments into visualization

**Features**:
1. **State-Based Coloring**:
   - Color residues by dominant metastable state
   - Show state probabilities as transparency
   
2. **State Entropy Display**:
   - Highlight residues with high state uncertainty
   - Indicates transition regions
   
3. **Transition Pathway Animation**:
   - Identify frames transitioning between states
   - Slow-motion playback of transitions
   - Highlight critical residues for transition

4. **Energy Landscape**:
   - 3D plot: tICA1 × tICA2 × Free Energy
   - Interactive rotation
   - Click to view representative structures

**Implementation Priority**: Low (requires VAMPnet integration)  
**Estimated Effort**: 4-5 weeks

### Phase 5: Comparative Analysis

**Goal**: Compare multiple trajectories or simulations

**Features**:
1. **Side-by-Side Viewer**:
   - Load two trajectories simultaneously
   - Synchronized playback
   
2. **Difference Hotspots**:
   - Compute Δhotspot = hotspot_A - hotspot_B
   - Identify mutation effects
   
3. **RMSD Matrix**:
   - All-vs-all frame comparison
   - Cluster similar conformations

**Implementation Priority**: Medium  
**Estimated Effort**: 3-4 weeks

### Phase 6: Export and Reporting

**Goal**: Generate publication-quality outputs

**Features**:
1. **High-Resolution Images**:
   - 4K+ resolution screenshots
   - Ray-traced rendering option
   
2. **Animation Export**:
   - MP4 video export
   - GIF creation
   
3. **Data Export**:
   - CSV: Hotspot values, RMSF, contacts
   - PDB: Selected frames or residues
   - JSON: Complete analysis results
   
4. **Auto-Generated Report**:
   - Summary statistics
   - Key findings (top hotspots, critical transitions)
   - Figures and tables
   - LaTeX-compatible formatting

**Implementation Priority**: Medium  
**Estimated Effort**: 2-3 weeks

---

## Scientific Applications

### 1. Protein Design and Engineering

**Use Case**: Identify mutation sites that won't disrupt function

**Workflow**:
1. Run MD simulation of wild-type protein
2. Identify low-RMSF, low-hotspot regions (stable core)
3. Identify high-RMSF regions away from active site (designable loops)
4. Propose mutations in designable regions
5. Validate with follow-up simulations

**Example**: Engineering thermostable enzymes by rigidifying loops

### 2. Drug Discovery

**Use Case**: Find cryptic pockets and allosteric sites

**Workflow**:
1. Simulate apo protein (no ligand)
2. Identify hotspots with high anomaly scores
3. Correlate hotspots with transient pockets (volume > 200 Å³)
4. Design molecules to bind cryptic pockets
5. Validate with docking and MD

**Example**: Discovering allosteric inhibitor sites in kinases

### 3. Understanding Disease Mutations

**Use Case**: Predict effect of pathogenic mutations

**Workflow**:
1. Simulate wild-type and mutant proteins
2. Compare hotspot patterns
3. Identify altered dynamics near mutation site
4. Correlate with disease phenotype
5. Propose rescue mutations

**Example**: Analyzing cancer-associated p53 mutations

### 4. Ligand Binding Mechanism

**Use Case**: Characterize binding pathways and induced fit

**Workflow**:
1. Simulate ligand binding trajectories
2. Identify hotspots in binding pocket
3. Use VAMPnet to find bound/unbound states
4. Map transition pathway
5. Identify key residues for binding

**Example**: Understanding enzyme-substrate recognition

### 5. Protein-Protein Interactions

**Use Case**: Map binding interfaces and specificity determinants

**Workflow**:
1. Simulate protein complex formation
2. Identify contact hotspots at interface
3. Correlate with binding affinity changes
4. Design mutations to alter specificity
5. Predict binding partners

**Example**: Engineering antibody-antigen specificity

---

## References and Further Reading

### Molecular Dynamics Simulations

1. **Karplus, M., & McCammon, J. A. (2002)**. "Molecular dynamics simulations of biomolecules". *Nature Structural Biology*, 9(9), 646-652.
   - Classic review of MD simulation fundamentals

2. **Hospital, A., et al. (2015)**. "Molecular dynamics simulations: advances and applications". *Advances and Applications in Bioinformatics and Chemistry*, 8, 37-47.
   - Modern overview of MD applications

3. **Hollingsworth, S. A., & Dror, R. O. (2018)**. "Molecular dynamics simulation for all". *Neuron*, 99(6), 1129-1143.
   - Accessible introduction to MD for biologists

### Feature Extraction and Analysis

4. **Bakan, A., Meireles, L. M., & Bahar, I. (2011)**. "ProDy: protein dynamics inferred from theory and experiments". *Bioinformatics*, 27(11), 1575-1577.
   - Tool for analyzing protein dynamics

5. **Ichiye, T., & Karplus, M. (1991)**. "Collective motions in proteins: a covariance analysis of atomic fluctuations in molecular dynamics and normal mode simulations". *Proteins*, 11(3), 205-217.
   - Foundational work on collective motions

### Dimensionality Reduction

6. **Pérez-Hernández, G., et al. (2013)**. "Identification of slow molecular order parameters for Markov model construction". *Journal of Chemical Physics*, 139(1), 015102.
   - Original tICA paper for MD analysis

7. **Schwantes, C. R., & Pande, V. S. (2013)**. "Improvements in Markov State Model Construction Reveal Many Non-Native Interactions in the Folding of NTL9". *Journal of Chemical Theory and Computation*, 9(4), 2000-2009.
   - tICA application to protein folding

8. **Noé, F., & Clementi, C. (2015)**. "Kinetic distance and kinetic maps from molecular dynamics simulation". *Journal of Chemical Theory and Computation*, 11(10), 5002-5011.
   - Theoretical foundations of tICA

### Markov State Models and VAMPnet

9. **Wu, H., & Noé, F. (2020)**. "Variational approach for learning Markov processes from time series data". *Journal of Nonlinear Science*, 30, 23-66.
   - VAMP framework fundamentals

10. **Mardt, A., et al. (2018)**. "VAMPnets for deep learning of molecular kinetics". *Nature Communications*, 9(1), 5.
    - Original VAMPnet paper

11. **Husic, B. E., & Pande, V. S. (2018)**. "Markov State Models: From an Art to a Science". *Journal of the American Chemical Society*, 140(7), 2386-2396.
    - Comprehensive MSM review

### Anomaly Detection

12. **Breunig, M. M., et al. (2000)**. "LOF: identifying density-based local outliers". *ACM SIGMOD Record*, 29(2), 93-104.
    - Local Outlier Factor algorithm

13. **Ramaswamy, S., et al. (2000)**. "Efficient algorithms for mining outliers from large data sets". *ACM SIGMOD Record*, 29(2), 427-438.
    - k-NN based anomaly detection

### Visualization

14. **Humphrey, W., et al. (1996)**. "VMD: visual molecular dynamics". *Journal of Molecular Graphics*, 14(1), 33-38.
    - Classic molecular visualization tool

15. **Schrodinger, LLC (2015)**. "The PyMOL Molecular Graphics System, Version 1.8."
    - Popular visualization software

### MDAnalysis

16. **Michaud-Agrawal, N., et al. (2011)**. "MDAnalysis: a toolkit for the analysis of molecular dynamics simulations". *Journal of Computational Chemistry*, 32(10), 2319-2327.
    - MDAnalysis library documentation

17. **Gowers, R. J., et al. (2016)**. "MDAnalysis: a Python package for the rapid analysis of molecular dynamics simulations". *Proceedings of the 15th Python in Science Conference*, 98-105.
    - Updated MDAnalysis features

### Web-Based Visualization

18. **Rose, A. S., et al. (2018)**. "NGL viewer: web-based molecular graphics for large complexes". *Bioinformatics*, 34(21), 3755-3758.
    - Modern web-based molecular viewer

19. **Sehnal, D., et al. (2021)**. "Mol* Viewer: modern web app for 3D visualization and analysis of large biomolecular structures". *Nucleic Acids Research*, 49(W1), W431-W437.
    - State-of-the-art web visualization

### Protein Dynamics and Function

20. **Henzler-Wildman, K., & Kern, D. (2007)**. "Dynamic personalities of proteins". *Nature*, 450(7172), 964-972.
    - Importance of dynamics for function

21. **Boehr, D. D., et al. (2009)**. "The role of dynamic conformational ensembles in biomolecular recognition". *Nature Chemical Biology*, 5(11), 789-796.
    - Conformational selection vs. induced fit

---

## Conclusion

The `siya-integration` branch represents a sophisticated integration of molecular dynamics simulation, machine learning, and interactive visualization. By combining:

- **MD trajectory analysis** (RMSF, contacts, conformational changes)
- **Advanced ML techniques** (tICA, VAMPnet, anomaly detection)
- **Real-time 3D visualization** (Three.js, WebGL)
- **Interactive exploration** (timeline controls, tooltips, multi-view modes)

The system enables researchers to:

1. **Identify** dynamic hotspots—regions undergoing significant functional motions
2. **Visualize** protein flexibility and conformational changes interactively
3. **Understand** slow collective motions and metastable states
4. **Discover** allosteric pathways and cryptic binding sites
5. **Analyze** protein behavior for design, drug discovery, and disease studies

This documentation provides the scientific foundation and technical details necessary to understand, use, and extend the system for cutting-edge biomolecular research.

---

## Appendix: Glossary

**Ångström (Å)**: Unit of length, 10⁻¹⁰ meters, typical for atomic distances

**Anomaly Score**: Composite metric indicating how unusual a conformation is

**C-alpha (CA)**: The central carbon atom in amino acids, used to trace protein backbone

**Collective Motion**: Coordinated movement of multiple residues or domains

**Conformational Space**: The set of all possible 3D structures a protein can adopt

**Covalent Radius**: Atomic radius used for bond detection

**Free Energy Landscape**: Energy as a function of conformational coordinates

**Hotspot**: Region of protein exhibiting significant dynamic behavior

**k-NN**: k-Nearest Neighbors algorithm for density estimation

**Lag Time (τ)**: Time delay used in time-lagged correlation analysis

**Markov State Model (MSM)**: Statistical model of conformational transitions

**MD Trajectory**: Time series of atomic coordinates from simulation

**Metastable State**: Long-lived conformational state separated by energy barriers

**PDB**: Protein Data Bank, repository and file format for biomolecular structures

**Residue**: Amino acid in a protein sequence

**RMSD**: Root Mean Square Deviation, measure of structural similarity

**RMSF**: Root Mean Square Fluctuation, measure of flexibility

**tICA**: Time-lagged Independent Component Analysis, dimensionality reduction method

**Topology**: Molecular structure definition (atoms, bonds, residues)

**VAMPnet**: Variational Approach for Markov Processes using neural networks

**XTC**: Compressed trajectory format from Gromacs MD software

---

*Document prepared for the siya-integration branch of the Molecular Visualizer project. For questions or contributions, please refer to the GitHub repository.*
