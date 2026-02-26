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
