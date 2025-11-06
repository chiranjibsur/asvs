#!/usr/bin/env python3
"""
Calculate residue-residue contacts throughout the trajectory.
Outputs: viewer/contacts.json
"""
import json
import numpy as np
import MDAnalysis as mda

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
    
    # Calculate all pairwise distances at once using scipy
    from scipy.spatial.distance import pdist, squareform
    dist_matrix = squareform(pdist(positions))
    
    # Find contacts within cutoff, excluding neighbors in sequence
    for i in range(n_residues):
        for j in range(i + 3, n_residues):  # Skip i+1, i+2 (neighbors)
            if dist_matrix[i, j] < contact_cutoff:
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
