import os
from typing import List, Dict, Tuple

try:
    import MDAnalysis as mda
except Exception as e:
    mda = None


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


# ---------- singleton ----------
_ADAPTER: TrajectoryAdapter | None = None

def get_adapter() -> TrajectoryAdapter:
    global _ADAPTER
    if _ADAPTER is None:
        _ADAPTER = TrajectoryAdapter()
    return _ADAPTER
