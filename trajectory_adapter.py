import os
import math
from typing import List, Dict, Tuple, Optional

try:
    import MDAnalysis as mda
    import numpy as np
except Exception as e:
    mda = None
    np = None


# ---------- helper: resolve topology/trajectory paths ----------
def _resolve_paths() -> Tuple[str, str]:
    """
    Look for files in (in order):
      1) env vars: ASVS_PDB / ASVS_XTC
      2) <project_root>/viewer/{topology.pdb, trajectory.xtc}
      3) <project_root>/data/md/{topology.pdb, trajectory.xtc}
    Returns (topology_path, trajectory_path) or raises FileNotFoundError.
    """
    env_pdb = os.environ.get("ASVS_PDB")
    env_xtc = os.environ.get("ASVS_XTC")
    if env_pdb and os.path.exists(env_pdb) and env_xtc and os.path.exists(env_xtc):
        return env_pdb, env_xtc

    root = os.path.abspath(os.path.dirname(__file__))
    candidates = [
        (os.path.join(root, "viewer", "topology.pdb"),
         os.path.join(root, "viewer", "trajectory.xtc")),
        (os.path.join(root, "data", "md", "topology.pdb"),
         os.path.join(root, "data", "md", "trajectory.xtc")),
    ]

    for pdb_path, xtc_path in candidates:
        if os.path.exists(pdb_path) and os.path.exists(xtc_path):
            return pdb_path, xtc_path

    lines = ["Could not find required files.", "Looked in:"]
    lines += [f"  - {p}\n    {x}" for p, x in candidates]
    lines.append("Or set ASVS_PDB and ASVS_XTC to absolute paths.")
    raise FileNotFoundError("\n".join(lines))


# ---------- adapter ----------
class TrajectoryAdapter:
    def __init__(self) -> None:
        if mda is None:
            raise RuntimeError("MDAnalysis is not available in this environment.")

        topology_path, trajectory_path = _resolve_paths()
        self.universe = mda.Universe(topology_path, trajectory_path)

        # Meta info
        self._meta: Dict[str, int] = {
            "n_frames": len(self.universe.trajectory),
            "n_atoms": len(self.universe.atoms),
            "n_residues": len(self.universe.residues),
        }

        # Atom → residue mapping
        if hasattr(self.universe.atoms, "resnums"):
            self._resnos = [int(a.resnum) for a in self.universe.atoms]
        else:
            self._resnos = []
            for r_idx, r in enumerate(self.universe.residues, start=1):
                self._resnos.extend([r_idx] * len(r.atoms))

        # Residue table
        self._res_table = []
        for idx, r in enumerate(self.universe.residues):
            resnum = int(getattr(r, "resnum", idx + 1))
            resname = str(getattr(r, "resname", "UNK"))
            chain = (
                str(getattr(r, "segid", ""))
                or (str(getattr(r.atoms[0], "chainID", "")) if len(r.atoms) else "")
            )
            self._res_table.append({
                "index": idx,
                "resnum": resnum,
                "resname": resname,
                "chain": chain,
            })

    # ---- methods used by app.py ----
    def get_meta(self) -> Dict[str, int]:
        return self._meta

    def get_residue_map(self) -> List[int]:
        return self._resnos

    def get_residue_table(self) -> List[Dict[str, str]]:
        return self._res_table

    def get_frame_xyz(self, frame: int):
        """Return atom positions [[x, y, z], ...] for given frame."""
        u = self.universe
        frame = max(0, min(frame, len(u.trajectory) - 1))
        u.trajectory[frame]
        return u.atoms.positions.astype(float).tolist()

    # ---- ball-stick view ----
    def get_atom_table(self):
        """Atoms + radii for bonding visualization."""
        u = self.universe
        atoms = []
        for i, a in enumerate(u.atoms):
            elem = (getattr(a, "element", None) or str(a.name).strip()).upper()
            elem = ''.join(ch for ch in elem if ch.isalpha())[:2] or "C"
            if elem.startswith("CA"): elem = "CA" if elem == "CA" else "C"
            if elem[0] in "CONSHPKFZIYWBMDGLEVUTRXQJ":
                elem = elem[0]
            atoms.append({
                "index": int(i),
                "element": elem,
                "resnum": int(getattr(a, "resnum", getattr(a.residue, "resnum", i))),
            })

        covalent_radii = {
            "H": 0.31, "C": 0.76, "N": 0.71, "O": 0.66, "F": 0.57,
            "P": 1.07, "S": 1.05, "CL": 1.02,
        }
        return {"atoms": atoms, "covalent_radii": covalent_radii}

    # ---- ribbon view ----
    def get_ca_xyz(self, frame: int):
        """Cα coordinates or backbone fallback for ribbon."""
        u = self.universe
        u.trajectory[frame]
        try:
            sel = u.select_atoms("name CA")
            if len(sel) == 0:
                raise ValueError
        except Exception:
            sel = u.select_atoms("backbone and not name H*")
        return sel.positions.astype(float).tolist()

    def _reconstruct_backbone_from_ca(self, ca_positions: List[List[float]]) -> List[Dict]:
        """
        Reconstruct N and C backbone positions from CA-only coordinates.
        
        Uses standard protein backbone geometry:
        - N-CA bond: ~1.47 Å
        - CA-C bond: ~1.52 Å
        - N-CA-C angle: ~111°
        
        The reconstruction places N and C atoms along the backbone direction,
        using the local tangent of the CA trace to determine orientation.
        
        Reference: Engh & Huber (1991) - Standard bond lengths in proteins
        """
        if np is None or len(ca_positions) < 2:
            return []
        
        # Standard bond lengths in Ångströms
        N_CA_BOND = 1.47
        CA_C_BOND = 1.52
        
        reconstructed = []
        coords = np.array(ca_positions, dtype=float)
        n = len(coords)
        
        for i in range(n):
            ca = coords[i]
            
            # Compute local backbone direction (tangent)
            if i == 0:
                # First residue: use direction to next CA
                direction = coords[i + 1] - ca
            elif i == n - 1:
                # Last residue: use direction from previous CA
                direction = ca - coords[i - 1]
            else:
                # Interior residues: average of both directions
                direction = (coords[i + 1] - coords[i - 1]) / 2.0
            
            # Normalize direction
            norm = np.linalg.norm(direction)
            if norm < 1e-8:
                direction = np.array([1.0, 0.0, 0.0])
            else:
                direction = direction / norm
            
            # Place N atom "behind" CA along backbone direction
            n_pos = ca - direction * N_CA_BOND
            
            # Place C atom "ahead" of CA along backbone direction
            c_pos = ca + direction * CA_C_BOND
            
            reconstructed.append({
                'N': n_pos.tolist(),
                'CA': ca.tolist(),
                'C': c_pos.tolist()
            })
        
        return reconstructed

    def get_backbone_atoms(self, frame: int):
        """
        Get backbone atoms (N, CA, C) for each residue.
        
        If the topology only contains CA atoms, this method will reconstruct
        approximate N and C positions using standard backbone geometry.
        This enables proper ribbon visualization even for CA-only models.
        
        Returns a dict with 'residues' list where each residue has:
        {
            'index': int,
            'resnum': int,
            'resname': str,
            'N': [x, y, z] or None,
            'CA': [x, y, z] or None,
            'C': [x, y, z] or None
        }
        """
        u = self.universe
        frame = max(0, min(frame, len(u.trajectory) - 1))
        u.trajectory[frame]
        
        result = []
        has_real_backbone = False
        ca_positions = []
        
        for idx, residue in enumerate(u.residues):
            resnum = int(getattr(residue, "resnum", idx + 1))
            resname = str(getattr(residue, "resname", "UNK"))
            
            backbone = {
                'index': idx,
                'resnum': resnum,
                'resname': resname,
                'N': None,
                'CA': None,
                'C': None
            }
            
            # Try to find backbone atoms
            for atom in residue.atoms:
                atom_name = atom.name.strip().upper()
                pos = atom.position.astype(float).tolist()
                
                if atom_name == 'N':
                    backbone['N'] = pos
                    has_real_backbone = True
                elif atom_name == 'CA':
                    backbone['CA'] = pos
                    ca_positions.append(pos)
                elif atom_name == 'C':
                    backbone['C'] = pos
                    has_real_backbone = True
            
            result.append(backbone)
        
        # If we only have CA atoms, reconstruct N and C positions
        if not has_real_backbone and ca_positions:
            reconstructed = self._reconstruct_backbone_from_ca(ca_positions)
            
            for i, res in enumerate(result):
                if i < len(reconstructed):
                    if res['N'] is None:
                        res['N'] = reconstructed[i]['N']
                    if res['C'] is None:
                        res['C'] = reconstructed[i]['C']
        
        return result

    def _compute_dihedral(self, p1, p2, p3, p4):
        """
        Compute dihedral angle between four points.
        Returns angle in degrees, or None if calculation fails.
        Based on standard dihedral angle formula.
        """
        if np is None:
            return None
        
        try:
            # Convert to numpy arrays
            p1 = np.array(p1, dtype=float)
            p2 = np.array(p2, dtype=float)
            p3 = np.array(p3, dtype=float)
            p4 = np.array(p4, dtype=float)
            
            # Calculate vectors
            b1 = p2 - p1
            b2 = p3 - p2
            b3 = p4 - p3
            
            # Normalize b2
            b2_norm = b2 / np.linalg.norm(b2)
            
            # Calculate perpendicular components
            v1 = b1 - np.dot(b1, b2_norm) * b2_norm
            v2 = b3 - np.dot(b3, b2_norm) * b2_norm
            
            # Calculate angle
            x = np.dot(v1, v2)
            y = np.dot(np.cross(b2_norm, v1), v2)
            
            angle = np.degrees(np.arctan2(y, x))
            return float(angle)
        except Exception:
            return None

    def _assign_secondary_structure_from_ca(self, ca_positions, window_size=5):
        """
        Assign secondary structure based on CA trace geometry.
        Uses local curvature and distance patterns to infer helix/sheet/coil.
        
        Parameters:
        - ca_positions: List of [x,y,z] CA coordinates
        - window_size: Number of residues to consider for local geometry
        
        Returns: List of 'H', 'E', or 'C' for each residue
        
        Method:
        - Helices: relatively constant CA-CA distance, smooth moderate curvature
        - Sheets: relatively straight, low curvature
        - Coils: irregular distances and high curvature
        
        Reference: Sklenar et al. (1989), Fodje & Al-Karadaghi (2002)
        """
        if np is None or len(ca_positions) < 3:
            return ['C'] * len(ca_positions)
        
        n = len(ca_positions)
        ss_types = ['C'] * n
        
        # Convert to numpy array
        coords = np.array(ca_positions, dtype=float)
        
        # Calculate CA-CA distances
        distances = []
        for i in range(n - 1):
            dist = np.linalg.norm(coords[i+1] - coords[i])
            distances.append(dist)
        distances.append(distances[-1] if distances else 0)  # pad last
        
        # Calculate local curvature (angle between consecutive CA-CA vectors)
        curvatures = []
        for i in range(1, n - 1):
            v1 = coords[i] - coords[i-1]
            v2 = coords[i+1] - coords[i]
            
            # Normalize
            v1_norm = v1 / (np.linalg.norm(v1) + 1e-8)
            v2_norm = v2 / (np.linalg.norm(v2) + 1e-8)
            
            # Angle
            cos_angle = np.clip(np.dot(v1_norm, v2_norm), -1.0, 1.0)
            angle = np.degrees(np.arccos(cos_angle))
            curvatures.append(angle)
        
        # Pad curvatures
        curvatures = [curvatures[0] if curvatures else 0] + curvatures + [curvatures[-1] if curvatures else 0]
        
        # Assign secondary structure based on patterns
        # Adjusted thresholds for CA-only models
        for i in range(n):
            # Get local window
            start = max(0, i - window_size // 2)
            end = min(n, i + window_size // 2 + 1)
            
            local_dists = distances[start:end]
            local_curvs = curvatures[start:end]
            
            if len(local_dists) < 2:
                continue
            
            avg_dist = np.mean(local_dists)
            std_dist = np.std(local_dists)
            avg_curv = np.mean(local_curvs)
            
            # For this dataset with smaller CA-CA distances (1.5-3.5 Å):
            # Helix detection: moderate distances with regular spacing and moderate curvature
            # Looking for regular patterns with consistent distance and smooth turns
            if 1.8 <= avg_dist <= 2.8 and std_dist < 0.5 and 30 < avg_curv < 90:
                ss_types[i] = 'H'
            
            # Sheet detection: extended regions with low curvature
            # Lower curvature = more extended/straight
            elif avg_curv < 40 and std_dist < 0.6:
                ss_types[i] = 'E'
            
            # Default is coil (already set)
        
        # Post-processing: smooth isolated assignments
        # Short single residues of H or E are likely noise
        for i in range(1, n - 1):
            if ss_types[i] != ss_types[i-1] and ss_types[i] != ss_types[i+1]:
                # Isolated residue - convert to majority neighbor
                ss_types[i] = ss_types[i-1] if ss_types[i-1] == ss_types[i+1] else 'C'
        
        # Extend helices and sheets to meet minimum length requirements
        # Helices should be at least 4 residues, sheets at least 3
        current_type = 'C'
        current_start = 0
        
        for i in range(n + 1):
            if i == n or ss_types[i] != current_type:
                length = i - current_start
                
                # If segment is too short, convert to coil
                if current_type == 'H' and length < 4:
                    for j in range(current_start, i):
                        ss_types[j] = 'C'
                elif current_type == 'E' and length < 3:
                    for j in range(current_start, i):
                        ss_types[j] = 'C'
                
                if i < n:
                    current_type = ss_types[i]
                    current_start = i
        
        return ss_types

    def get_secondary_structure(self, frame: int):
        """
        Compute secondary structure for each residue based on CA trace geometry.
        
        Returns a list of dicts:
        [{
            'index': int,
            'resnum': int,
            'resname': str,
            'ss': 'H' | 'E' | 'C'  (helix, sheet, coil)
        }, ...]
        """
        # Get CA positions
        ca_positions = self.get_ca_xyz(frame)
        
        # Assign secondary structure from CA geometry
        ss_types = self._assign_secondary_structure_from_ca(ca_positions)
        
        # Build result with residue metadata
        result = []
        for i, residue in enumerate(self._res_table):
            if i < len(ss_types):
                result.append({
                    'index': residue['index'],
                    'resnum': residue['resnum'],
                    'resname': residue['resname'],
                    'ss': ss_types[i]
                })
        
        return result


# ---------- singleton ----------
_ADAPTER: TrajectoryAdapter | None = None

def get_adapter() -> TrajectoryAdapter:
    global _ADAPTER
    if _ADAPTER is None:
        _ADAPTER = TrajectoryAdapter()
    return _ADAPTER
