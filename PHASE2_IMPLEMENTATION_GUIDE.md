# Phase 2 Implementation Guide: RMSF Data & Contact Networks

This guide provides step-by-step instructions for implementing Phase 2 of the interactive molecular visualization features.

## Overview

**Phase 2 Goals:**
- Add RMSF (Root Mean Square Fluctuation) data visualization
- Implement contact network visualization between residues
- Create a "Top Interacting Residues" panel
- Enhanced info panel with more dynamic data
- **Timeline:** 2-3 weeks

## Prerequisites

Before starting, ensure:
- Phase 1 is complete and merged (atom/residue selection working in all viewers)
- You have knowledge of JavaScript, Three.js, and molecular dynamics concepts
- Development environment is set up (see DEVELOPER_GUIDE.md)
- Flask backend is running (`python app.py`)

## Implementation Steps

### Step 1: Set Up New Branch

```bash
# Switch to main integration branch and update
git checkout siya-integration
git pull origin siya-integration

# Create new feature branch
git checkout -b feature/rmsf-contacts-phase2
```

### Step 2: Prepare RMSF Data

RMSF (Root Mean Square Fluctuation) measures the flexibility of each residue over the trajectory.

#### 2.1 Calculate RMSF Data (Python)

Create a script `scripts/calculate_rmsf.py`:

```python
#!/usr/bin/env python3
"""
Calculate RMSF (Root Mean Square Fluctuation) for each residue.
Outputs: viewer/rmsf_residue.json
"""
import json
import numpy as np
import MDAnalysis as mda
from MDAnalysis.analysis.rms import RMSF

# Load trajectory
u = mda.Universe("viewer/topology.pdb", "viewer/trajectory.xtc")

# Select C-alpha atoms (one per residue)
ca_atoms = u.select_atoms("name CA")

# Calculate RMSF
rmsf_analysis = RMSF(ca_atoms).run()
rmsf_values = rmsf_analysis.results.rmsf

# Map to residue indices (0-based)
rmsf_dict = {}
for i, atom in enumerate(ca_atoms):
    residue_index = atom.resid - 1  # Convert to 0-based
    rmsf_dict[str(residue_index)] = float(rmsf_values[i])

# Normalize RMSF to [0, 1] for visualization
max_rmsf = max(rmsf_dict.values())
min_rmsf = min(rmsf_dict.values())
rmsf_range = max_rmsf - min_rmsf

for key in rmsf_dict:
    normalized = (rmsf_dict[key] - min_rmsf) / rmsf_range if rmsf_range > 0 else 0.5
    rmsf_dict[key] = round(normalized, 4)

# Save to JSON
output = {
    "min": float(min_rmsf),
    "max": float(max_rmsf),
    "normalized": rmsf_dict
}

with open("viewer/rmsf_residue.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"RMSF calculated for {len(rmsf_dict)} residues")
print(f"Range: {min_rmsf:.3f} - {max_rmsf:.3f} Å")
```

Run the script:
```bash
python scripts/calculate_rmsf.py
```

#### 2.2 Add RMSF API Endpoint

**File to edit:** `app.py`

Add after the hotspots endpoint:

```python
@app.route("/api/rmsf")
def api_rmsf():
    """
    Returns per-residue RMSF (flexibility) data.
    """
    rmsf_path = os.environ.get(
        "ASVS_RMSF",
        os.path.join("viewer", "rmsf_residue.json")
    )
    
    if not os.path.isfile(rmsf_path):
        return jsonify({"error": "RMSF data not found"}), 404
    
    with open(rmsf_path, "r") as f:
        data = json.load(f)
    
    return jsonify(data)
```

### Step 3: Calculate Contact Networks

Contact networks identify residues that are in close proximity during the trajectory.

#### 3.1 Calculate Contacts (Python)

Create a script `scripts/calculate_contacts.py`:

```python
#!/usr/bin/env python3
"""
Calculate residue-residue contacts throughout the trajectory.
Outputs: viewer/contacts.json
"""
import json
import numpy as np
import MDAnalysis as mda
from MDAnalysis.analysis import contacts

# Load trajectory
u = mda.Universe("viewer/topology.pdb", "viewer/trajectory.xtc")

# Select C-alpha atoms
ca_atoms = u.select_atoms("name CA")
n_residues = len(ca_atoms)

# Initialize contact matrix (residue x residue)
contact_freq = np.zeros((n_residues, n_residues))
contact_cutoff = 8.0  # Angstroms

# Calculate contacts for each frame
print("Calculating contacts...")
for ts in u.trajectory:
    positions = ca_atoms.positions
    
    # Calculate pairwise distances
    for i in range(n_residues):
        for j in range(i + 1, n_residues):
            # Skip neighboring residues in sequence
            if abs(i - j) < 3:
                continue
            
            dist = np.linalg.norm(positions[i] - positions[j])
            if dist < contact_cutoff:
                contact_freq[i, j] += 1
                contact_freq[j, i] += 1

# Normalize by number of frames
n_frames = len(u.trajectory)
contact_freq /= n_frames

# Find top contacts (frequency > 0.5)
contacts_list = []
for i in range(n_residues):
    for j in range(i + 1, n_residues):
        if contact_freq[i, j] > 0.5:  # Contact in >50% of frames
            contacts_list.append({
                "residue1": i,
                "residue2": j,
                "frequency": round(float(contact_freq[i, j]), 3)
            })

# Sort by frequency
contacts_list.sort(key=lambda x: x["frequency"], reverse=True)

# Save to JSON
output = {
    "cutoff_angstrom": contact_cutoff,
    "n_frames": n_frames,
    "contacts": contacts_list[:200]  # Top 200 contacts
}

with open("viewer/contacts.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"Found {len(contacts_list)} contacts (showing top 200)")
```

Run the script:
```bash
python scripts/calculate_contacts.py
```

#### 3.2 Add Contacts API Endpoint

**File to edit:** `app.py`

```python
@app.route("/api/contacts")
def api_contacts():
    """
    Returns residue-residue contact network data.
    """
    contacts_path = os.environ.get(
        "ASVS_CONTACTS",
        os.path.join("viewer", "contacts.json")
    )
    
    if not os.path.isfile(contacts_path):
        return jsonify({"error": "Contacts data not found"}), 404
    
    with open(contacts_path, "r") as f:
        data = json.load(f)
    
    return jsonify(data)
```

### Step 4: Enhance Ball-and-Stick Viewer with RMSF

**File to edit:** `static/js/ballstick_viewer.js`

#### 4.1 Add RMSF Toggle

After the existing raycaster setup, add:

```javascript
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
  
  if (showRMSF && rmsfData) {
    applyRMSFColors();
  } else {
    const currentFrame = parseInt(slider.value, 10);
    applyHotspotColors(currentFrame);
  }
}

function applyRMSFColors() {
  if (!rmsfData) return;
  
  const scores = rmsfData.normalized;
  
  for (let i = 0; i < atomMeshes.length; i++) {
    const rIdx = atomResidueIdx[i];
    const t = scores[String(rIdx)] || 0.0;
    atomMeshes[i].material.color.copy(colorBWR(t));
  }
}
```

#### 4.2 Add Toggle Button to HTML

**File to edit:** `templates/ballstick_viewer.html`

Add after the existing buttons:

```html
<button class="btn" id="btnToggleRMSF">Show RMSF</button>

<script>
  // Add to the existing script section
  document.getElementById('btnToggleRMSF').addEventListener('click', () => {
    const btn = document.getElementById('btnToggleRMSF');
    btn.textContent = btn.textContent === 'Show RMSF' ? 'Show Hotspots' : 'Show RMSF';
    toggleRMSFColoring();
  });
</script>
```

### Step 5: Add Contact Network Visualization

#### 5.1 Create Contact Lines in Ball-and-Stick Viewer

**File to edit:** `static/js/ballstick_viewer.js`

Add after bond creation:

```javascript
// ---- Contact network visualization ----
let contactsData = null;
let contactLines = [];
let showContacts = false;

async function fetchContacts() {
  try {
    const r = await fetch('/api/contacts');
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

// Load contacts on startup
contactsData = await fetchContacts();

function toggleContactNetwork() {
  showContacts = !showContacts;
  
  if (showContacts) {
    displayContactNetwork();
  } else {
    hideContactNetwork();
  }
}

function displayContactNetwork() {
  if (!contactsData || contactLines.length > 0) return;
  
  // Get current frame coordinates
  const currentFrame = parseInt(slider.value, 10);
  fetch(`/api/trajectory/frame/${currentFrame}`)
    .then(r => r.json())
    .then(frameData => {
      const xyz = frameData.xyz;
      
      // Create line for each contact
      const lineMaterial = new THREE.LineBasicMaterial({ 
        color: 0x00ff00, 
        transparent: true, 
        opacity: 0.3 
      });
      
      for (const contact of contactsData.contacts.slice(0, 50)) { // Show top 50
        const res1 = contact.residue1;
        const res2 = contact.residue2;
        
        // Find atoms for these residues
        let atom1Idx = atomResidueIdx.indexOf(res1);
        let atom2Idx = atomResidueIdx.indexOf(res2);
        
        if (atom1Idx === -1 || atom2Idx === -1) continue;
        
        const p1 = xyz[atom1Idx];
        const p2 = xyz[atom2Idx];
        
        const points = [
          new THREE.Vector3(p1[0], p1[1], p1[2]),
          new THREE.Vector3(p2[0], p2[1], p2[2])
        ];
        
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, lineMaterial);
        
        scene.add(line);
        contactLines.push(line);
      }
    });
}

function hideContactNetwork() {
  for (const line of contactLines) {
    scene.remove(line);
    line.geometry.dispose();
  }
  contactLines = [];
}
```

#### 5.2 Add Contact Toggle Button

**File to edit:** `templates/ballstick_viewer.html`

```html
<button class="btn" id="btnToggleContacts">Show Contacts</button>

<script>
  document.getElementById('btnToggleContacts').addEventListener('click', () => {
    const btn = document.getElementById('btnToggleContacts');
    btn.textContent = btn.textContent === 'Show Contacts' ? 'Hide Contacts' : 'Show Contacts';
    toggleContactNetwork();
  });
</script>
```

### Step 6: Add "Top Interacting Residues" Panel

#### 6.1 Create Panel HTML

**File to edit:** `templates/ballstick_viewer.html`

Add before the closing `</body>` tag:

```html
<!-- Top Contacts Panel -->
<div id="contactsPanel" style="
  position: absolute;
  top: 80px;
  left: 20px;
  width: 280px;
  max-height: 400px;
  background: rgba(26, 28, 34, 0.95);
  border: 1px solid #2b2f3a;
  border-radius: 10px;
  padding: 16px;
  display: none;
  z-index: 100;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
">
  <h3 style="margin:0 0 12px 0;color:#e9eaee;font-size:16px;font-weight:600;">
    Top Interacting Residues
  </h3>
  <div id="contactsList" style="font-size:12px;color:#b9beca;"></div>
  <button id="closeContactsBtn" class="close-btn">Close</button>
</div>

<style>
  .contact-item {
    padding: 8px;
    margin-bottom: 6px;
    background: #1f232b;
    border-radius: 6px;
    cursor: pointer;
  }
  
  .contact-item:hover {
    background: #2d3a4f;
  }
</style>
```

#### 6.2 Add Panel Logic

**File to edit:** `static/js/ballstick_viewer.js`

```javascript
async function showTopContacts() {
  if (!contactsData) {
    alert("Contact data not available");
    return;
  }
  
  // Fetch residue metadata
  const residueMeta = await fetch('/api/trajectory/residue_meta').then(r => r.json());
  
  // Build list
  let html = '';
  for (const contact of contactsData.contacts.slice(0, 20)) { // Top 20
    const res1 = residueMeta.residues[contact.residue1];
    const res2 = residueMeta.residues[contact.residue2];
    
    if (!res1 || !res2) continue;
    
    html += `
      <div class="contact-item" onclick="selectContact(${contact.residue1}, ${contact.residue2})">
        <strong>${res1.resname}${res1.resnum}</strong> ↔ <strong>${res2.resname}${res2.resnum}</strong>
        <br>
        <span style="opacity:0.7;">Contact frequency: ${(contact.frequency * 100).toFixed(1)}%</span>
      </div>
    `;
  }
  
  document.getElementById('contactsList').innerHTML = html;
  document.getElementById('contactsPanel').style.display = 'block';
}

function selectContact(res1, res2) {
  // Find and highlight both residues
  for (let i = 0; i < atomMeshes.length; i++) {
    const rIdx = atomResidueIdx[i];
    if (rIdx === res1 || rIdx === res2) {
      highlightAtom(i);
    }
  }
}

document.getElementById('closeContactsBtn').addEventListener('click', () => {
  document.getElementById('contactsPanel').style.display = 'none';
});
```

#### 6.3 Add Button to Show Panel

**File to edit:** `templates/ballstick_viewer.html`

```html
<button class="btn" id="btnShowContacts">Top Contacts</button>

<script>
  document.getElementById('btnShowContacts').addEventListener('click', showTopContacts);
</script>
```

### Step 7: Enhance Info Panel with RMSF and Contacts

**File to edit:** `static/js/ballstick_viewer.js`

Modify the `displayAtomInfo` function:

```javascript
async function displayAtomInfo(atomIndex) {
  try {
    const atom = atoms[atomIndex];
    const residueNum = atom.resnum;
    const residueIndex = atomResidueIdx[atomIndex];
    
    const residueMeta = await fetch('/api/trajectory/residue_meta').then(r => r.json());
    const residue = residueMeta.residues.find(r => r.resnum === residueNum);
    
    if (!residue) return;
    
    const currentFrame = parseInt(slider.value, 10);
    const frameData = await fetch(`/api/trajectory/frame/${currentFrame}`).then(r => r.json());
    const coords = frameData.xyz[atomIndex];
    
    const hotspotData = await fetch(`/api/hotspots/${currentFrame}`).then(r => r.json());
    const hotspotValue = hotspotData[residue.index] || 0;
    
    // Get RMSF value
    let rmsfHTML = '';
    if (rmsfData && rmsfData.normalized) {
      const rmsfValue = rmsfData.normalized[String(residueIndex)] || 0;
      const actualRMSF = rmsfData.min + (rmsfValue * (rmsfData.max - rmsfData.min));
      rmsfHTML = `
        <div class="info-section">
          <strong>RMSF (Flexibility):</strong> ${actualRMSF.toFixed(2)} Å
        </div>
      `;
    }
    
    // Get contacts for this residue
    let contactsHTML = '';
    if (contactsData) {
      const relatedContacts = contactsData.contacts.filter(c => 
        c.residue1 === residueIndex || c.residue2 === residueIndex
      ).slice(0, 3); // Top 3
      
      if (relatedContacts.length > 0) {
        const contactText = relatedContacts.map(c => {
          const otherRes = c.residue1 === residueIndex ? c.residue2 : c.residue1;
          const other = residueMeta.residues[otherRes];
          return `${other.resname}${other.resnum} (${(c.frequency*100).toFixed(0)}%)`;
        }).join(', ');
        
        contactsHTML = `
          <div class="info-section">
            <strong>Top Contacts:</strong> ${contactText}
          </div>
        `;
      }
    }
    
    const infoHTML = `
      <div class="atom-info-panel">
        <h3>Atom Information</h3>
        <div class="info-section">
          <strong>Atom:</strong> ${atom.element} (Index: ${atomIndex})
        </div>
        <div class="info-section">
          <strong>Residue:</strong> ${residue.resname}${residue.resnum} (Chain ${residue.chain})
        </div>
        <div class="info-section">
          <strong>Coordinates:</strong><br>
          X: ${coords[0].toFixed(2)} Å<br>
          Y: ${coords[1].toFixed(2)} Å<br>
          Z: ${coords[2].toFixed(2)} Å
        </div>
        <div class="info-section">
          <strong>Hotspot Score:</strong> ${hotspotValue.toFixed(3)}
        </div>
        ${rmsfHTML}
        ${contactsHTML}
        <button id="closeInfoBtn" class="close-btn">Close</button>
      </div>
    `;
    
    const panel = document.getElementById('infoPanel');
    panel.innerHTML = infoHTML;
    panel.style.display = 'block';
    
    const closeBtn = document.getElementById('closeInfoBtn');
    closeBtn.removeEventListener('click', deselectAtom);
    closeBtn.addEventListener('click', deselectAtom);
  } catch (error) {
    console.error('Error displaying atom info:', error);
    hideAtomInfo();
  }
}
```

### Step 8: Apply Phase 2 to Ribbon and Hotspot Viewers

Repeat similar changes for:
- `static/js/ribbon_viewer.js` - Add RMSF coloring toggle
- `static/js/simple_visualizer.js` - Add RMSF coloring toggle

The contact network visualization is primarily for the Ball-and-Stick viewer since it shows atom-level detail.

### Step 9: Testing

#### 9.1 Manual Testing Checklist

- [ ] Start the Flask server: `python app.py`
- [ ] Navigate to http://localhost:5000/viewer/ballstick
- [ ] Test RMSF toggle - atoms should change colors based on flexibility
- [ ] Test contact network toggle - green lines should appear between interacting residues
- [ ] Click "Top Contacts" - panel should show list of interacting residues
- [ ] Click on a contact pair - both residues should highlight
- [ ] Select an atom - info panel should show RMSF and top contacts
- [ ] Test with different frames
- [ ] Repeat for Ribbon and Hotspot viewers

#### 9.2 Data Validation

```bash
# Verify RMSF data exists
cat viewer/rmsf_residue.json | head

# Verify contacts data exists
cat viewer/contacts.json | head

# Test API endpoints
curl http://localhost:5000/api/rmsf
curl http://localhost:5000/api/contacts
```

### Step 10: Commit and Push

```bash
# Add changes
git add scripts/calculate_rmsf.py
git add scripts/calculate_contacts.py
git add viewer/rmsf_residue.json
git add viewer/contacts.json
git add app.py
git add static/js/ballstick_viewer.js
git add static/js/ribbon_viewer.js
git add static/js/simple_visualizer.js
git add templates/ballstick_viewer.html
git add templates/ribbon_viewer.html
git add templates/hotspot_viewer.html

# Commit
git commit -m "Add Phase 2: RMSF visualization and contact networks

- Calculate and display RMSF (flexibility) data
- Implement contact network visualization
- Add top interacting residues panel
- Enhance info panel with RMSF and contact data
- Add toggle buttons for RMSF and contacts"

# Push to remote
git push origin feature/rmsf-contacts-phase2
```

### Step 11: Create Pull Request

1. Go to GitHub repository
2. Click "Compare & pull request" for your new branch
3. Set base branch to `siya-integration`
4. Title: "Phase 2: Add RMSF visualization and contact networks"
5. Description: Use the template below

```markdown
## Phase 2: RMSF Visualization & Contact Networks

Implements advanced molecular dynamics analysis features for all viewers.

### Features Added

#### RMSF (Flexibility) Visualization
- Calculate per-residue RMSF from trajectory
- Toggle between hotspot and RMSF coloring
- Display RMSF values in info panel
- API endpoint: `/api/rmsf`

#### Contact Network Analysis
- Calculate residue-residue contacts across trajectory
- Visualize contact network as green lines
- Top Interacting Residues panel
- Click contacts to highlight both residues
- Show top 3 contacts in atom info panel
- API endpoint: `/api/contacts`

#### Enhanced Info Panel
- Now shows RMSF (flexibility) value
- Shows top 3 contacting residues
- Available in all three viewers

### Testing Done
- [x] RMSF calculation works correctly
- [x] RMSF coloring toggle works
- [x] Contact network displays correctly
- [x] Top contacts panel functional
- [x] Info panel shows all new data
- [x] Works in all three viewers
- [x] No console errors

### Screenshots
[Add screenshots of the features in action]

### API Documentation
See API_DOCUMENTATION.md for new endpoint details.

### Next Steps
- Phase 3: Molecular slicing and filtering
- Enhanced measurement tools
```

## Troubleshooting

### Issue: RMSF calculation fails
**Solution:** Ensure MDAnalysis is installed: `pip install MDAnalysis`. Check that C-alpha atoms are properly identified in topology.

### Issue: Contacts not displaying
**Solution:** Verify `contacts.json` exists. Check browser console for errors. Ensure coordinate data is loaded for current frame.

### Issue: Performance issues with contacts
**Solution:** Reduce number of displayed contacts in `displayContactNetwork()`. Default is 50, try reducing to 20-30.

### Issue: RMSF values seem incorrect
**Solution:** RMSF is normalized to [0,1] for coloring. Check `rmsf_residue.json` for actual min/max values.

## Performance Considerations

- Contact calculation can be slow for large trajectories - consider parallel processing
- Limit displayed contacts to top 50 to maintain performance
- RMSF data is static and cached after first load
- Consider implementing level-of-detail (LOD) for large structures

## Code Style

- Follow existing code style in the repository
- Use async/await for API calls
- Add comments for complex logic
- Keep functions small and focused

## Resources

- [MDAnalysis RMSF Analysis](https://docs.mdanalysis.org/stable/documentation_pages/analysis/rms.html)
- [MDAnalysis Contacts](https://docs.mdanalysis.org/stable/documentation_pages/analysis/contacts.html)
- [Three.js Line Geometry](https://threejs.org/docs/#api/en/objects/Line)
- See ARCHITECTURE.md for system overview
- See API_DOCUMENTATION.md for API endpoint details

## Phase 3 Preview

Once Phase 2 is complete and merged, Phase 3 will add:
- Molecular slicing (clip planes)
- Distance and angle measurement tools
- Export capabilities (images, data)
- Timeline: 2-3 weeks after Phase 2

---

**Questions?** Refer to DEVELOPER_GUIDE.md or create an issue in the repository.
