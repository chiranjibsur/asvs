#!/usr/bin/env python3
"""
Chapter 9 Case Study Inspection Utility.

Loads frame_case_candidates.csv and residue_contrast_cases.csv,
computes structural metrics using the existing trajectory loader,
and exports analysis results and case-study snapshots.

Outputs
-------
analysis_outputs/frame_structural_metrics.csv
analysis_outputs/residue_structural_context.csv
analysis_outputs/case_study_images/frame_<N>_anomaly.png
analysis_outputs/case_study_images/frame_<N>_rmsf.png
"""

import csv
import json
import math
import os
import sys

# ---------------------------------------------------------------------------
# Optional heavy dependencies – degrade gracefully when absent
# ---------------------------------------------------------------------------
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None
    _HAS_NUMPY = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import mpl_toolkits.mplot3d  # noqa: F401 – registers 3-D projection
    _HAS_MPL = True
except ImportError:
    plt = None
    _HAS_MPL = False

# ---------------------------------------------------------------------------
# Repository root and path helpers
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)

_INPUT_DIR = _REPO_ROOT          # CSVs expected at repo root
_OUTPUT_DIR = os.path.join(_REPO_ROOT, "analysis_outputs")
_IMAGES_DIR = os.path.join(_OUTPUT_DIR, "case_study_images")

_VIEWER_DIR = os.path.join(_REPO_ROOT, "viewer")

# CSV paths the caller is expected to provide
_FRAME_CSV = os.path.join(_REPO_ROOT, "frame_case_candidates.csv")
_RESIDUE_CSV = os.path.join(_REPO_ROOT, "residue_contrast_cases.csv")

# Top-N anomaly residues used for cluster / displacement statistics
_TOP_ANOMALY_K = 10

# Neighbourhood radius for local-motion calculation (Å)
_NEIGHBOURHOOD_RADIUS = 5.0


# ===========================================================================
# Utility: pure-Python RMSD
# ===========================================================================

def _rmsd_pure(coords_a: list, coords_b: list) -> float:
    """Compute RMSD between two lists of [x, y, z] tuples using pure Python."""
    if len(coords_a) != len(coords_b) or len(coords_a) == 0:
        return float("nan")
    s = 0.0
    for (ax, ay, az), (bx, by, bz) in zip(coords_a, coords_b):
        dx, dy, dz = ax - bx, ay - by, az - bz
        s += dx * dx + dy * dy + dz * dz
    return math.sqrt(s / len(coords_a))


def _rmsd(coords_a, coords_b) -> float:
    """RMSD – uses NumPy when available, pure Python otherwise."""
    if _HAS_NUMPY:
        a = np.asarray(coords_a, dtype=float)
        b = np.asarray(coords_b, dtype=float)
        if a.shape != b.shape or a.ndim == 0:
            return float("nan")
        diff = a - b
        return float(np.sqrt((diff * diff).sum() / len(a)))
    return _rmsd_pure(coords_a, coords_b)


# ===========================================================================
# Utility: per-residue displacement
# ===========================================================================

def _per_residue_displacement(xyz_ref: list, xyz_tgt: list,
                              res_map: list) -> dict:
    """
    Return {resnum: mean_displacement_Å} for each residue.

    Parameters
    ----------
    xyz_ref, xyz_tgt : list of [x, y, z]
        Atom positions for two frames (same atom order).
    res_map : list of int
        Residue number for each atom (same order as xyz).
    """
    sums: dict = {}
    counts: dict = {}
    for i, (a, b) in enumerate(zip(xyz_ref, xyz_tgt)):
        dx, dy, dz = a[0] - b[0], a[1] - b[1], a[2] - b[2]
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        r = res_map[i] if i < len(res_map) else i
        sums[r] = sums.get(r, 0.0) + d
        counts[r] = counts.get(r, 0) + 1
    return {r: sums[r] / counts[r] for r in sums}


# ===========================================================================
# Utility: positional variance across trajectory
# ===========================================================================

def _residue_positional_variance(adapter, res_map: list) -> dict:
    """
    Compute per-residue mean positional variance over all trajectory frames.

    Returns {resnum: variance_Å²}
    """
    n_frames = adapter.get_meta()["n_frames"]

    # Accumulate sum and sum-of-squares per residue
    res_sum: dict = {}    # resnum -> [sx, sy, sz]
    res_sq: dict = {}     # resnum -> [sx2, sy2, sz2]
    res_n: dict = {}      # resnum -> atom count (same every frame)

    for frame_idx in range(n_frames):
        xyz = adapter.get_frame_xyz(frame_idx)
        for i, pos in enumerate(xyz):
            r = res_map[i] if i < len(res_map) else i
            if r not in res_sum:
                res_sum[r] = [0.0, 0.0, 0.0]
                res_sq[r] = [0.0, 0.0, 0.0]
                res_n[r] = 0
            for k in range(3):
                res_sum[r][k] += pos[k]
                res_sq[r][k] += pos[k] * pos[k]
            res_n[r] += 1

    variances: dict = {}
    for r, n in res_n.items():
        if n == 0:
            variances[r] = float("nan")
            continue
        v = 0.0
        for k in range(3):
            mean = res_sum[r][k] / n
            v += res_sq[r][k] / n - mean * mean
        variances[r] = v / 3.0   # mean variance over x, y, z
    return variances


# ===========================================================================
# Utility: load hotspot / anomaly viewer data
# ===========================================================================

def _load_json_safe(path: str):
    """Return parsed JSON or None on failure."""
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return None


def _get_top_anomaly_residues(n_frames: int, k: int = _TOP_ANOMALY_K) -> list:
    """
    Return sorted list of top-k anomaly residue *indices* (0-based).
    Falls back to empty list if viewer data is unavailable.
    """
    anomaly_data = _load_json_safe(
        os.path.join(_VIEWER_DIR, "anomaly_residue.json")
    )
    if anomaly_data is None:
        return []

    scores: dict = {}  # residue_idx -> cumulative score
    for frame_key, frame_scores in anomaly_data.items():
        if not isinstance(frame_scores, dict):
            continue
        for res_key, score in frame_scores.items():
            try:
                scores[int(res_key)] = scores.get(int(res_key), 0.0) + float(score)
            except (ValueError, TypeError):
                pass

    top = sorted(scores, key=lambda r: scores[r], reverse=True)[:k]
    return top


def _get_rmsf_by_residue() -> dict:
    """
    Return {residue_index: normalized_rmsf} from viewer/rmsf_residue.json.
    Falls back to empty dict.
    """
    data = _load_json_safe(os.path.join(_VIEWER_DIR, "rmsf_residue.json"))
    if data is None or "normalized" not in data:
        return {}
    return {int(k): float(v) for k, v in data["normalized"].items()}


# ===========================================================================
# Input CSV loaders
# ===========================================================================

def _load_frame_candidates(path: str) -> list:
    """
    Load frame_case_candidates.csv.

    Expected columns (any order): frame_index, [optional extras]
    Returns list of int frame indices.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"frame_case_candidates.csv not found at: {path}\n"
            "Please create this file with at least a 'frame_index' column."
        )
    frames = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                frames.append(int(row["frame_index"]))
            except (KeyError, ValueError):
                pass
    return frames


def _load_residue_candidates(path: str) -> list:
    """
    Load residue_contrast_cases.csv.

    Expected columns: residue_id, [optional extras]
    Returns list of int residue IDs.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"residue_contrast_cases.csv not found at: {path}\n"
            "Please create this file with at least a 'residue_id' column."
        )
    residues = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                residues.append(int(row["residue_id"]))
            except (KeyError, ValueError):
                pass
    return residues


# ===========================================================================
# PART 1 — Frame-Level Structural Quantification
# ===========================================================================

def compute_frame_structural_metrics(adapter, frame_candidates: list,
                                     top_anomaly_residues: list) -> list:
    """
    For each candidate frame, compute:
      - rmsd_prev   : RMSD vs frame-1 (NaN for first frame)
      - rmsd_next   : RMSD vs frame+1 (NaN for last frame)
      - max_displacement  : maximum per-residue displacement (vs prev frame)
      - max_residue_id    : residue with that maximum displacement
      - mean_top_anomaly_displacement : mean displacement of top anomaly residues
    """
    n_frames = adapter.get_meta()["n_frames"]
    res_map = adapter.get_residue_map()

    rows = []
    for fi in frame_candidates:
        fi = max(0, min(fi, n_frames - 1))
        xyz_cur = adapter.get_frame_xyz(fi)

        # RMSD vs previous frame
        if fi > 0:
            xyz_prev = adapter.get_frame_xyz(fi - 1)
            rmsd_prev = _rmsd(xyz_cur, xyz_prev)
            disp_prev = _per_residue_displacement(xyz_cur, xyz_prev, res_map)
        else:
            xyz_prev = None
            rmsd_prev = float("nan")
            disp_prev = {}

        # RMSD vs next frame
        if fi < n_frames - 1:
            xyz_next = adapter.get_frame_xyz(fi + 1)
            rmsd_next = _rmsd(xyz_cur, xyz_next)
        else:
            rmsd_next = float("nan")

        # Per-residue displacement relative to previous frame
        if disp_prev:
            max_residue_id = max(disp_prev, key=lambda r: disp_prev[r])
            max_displacement = disp_prev[max_residue_id]

            if top_anomaly_residues:
                # top_anomaly_residues holds 0-based residue indices;
                # disp_prev keys are 1-based residue numbers from res_map.
                # We translate: res_map values are 1-based resnums.
                top_resnums = set()
                res_table = adapter.get_residue_table()
                for r_idx in top_anomaly_residues:
                    if r_idx < len(res_table):
                        top_resnums.add(res_table[r_idx]["resnum"])

                top_displacements = [
                    disp_prev[r] for r in disp_prev if r in top_resnums
                ]
                mean_top = (
                    sum(top_displacements) / len(top_displacements)
                    if top_displacements else float("nan")
                )
            else:
                mean_top = float("nan")
        else:
            max_residue_id = -1
            max_displacement = float("nan")
            mean_top = float("nan")

        rows.append({
            "frame_index": fi,
            "rmsd_prev": rmsd_prev,
            "rmsd_next": rmsd_next,
            "max_displacement": max_displacement,
            "max_residue_id": max_residue_id,
            "mean_top_anomaly_displacement": mean_top,
        })

    return rows


def save_frame_metrics(rows: list, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fieldnames = [
        "frame_index", "rmsd_prev", "rmsd_next",
        "max_displacement", "max_residue_id",
        "mean_top_anomaly_displacement",
    ]
    with open(output_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "frame_index": row["frame_index"],
                "rmsd_prev": f"{row['rmsd_prev']:.4f}" if not math.isnan(row["rmsd_prev"]) else "",
                "rmsd_next": f"{row['rmsd_next']:.4f}" if not math.isnan(row["rmsd_next"]) else "",
                "max_displacement": f"{row['max_displacement']:.4f}" if not math.isnan(row["max_displacement"]) else "",
                "max_residue_id": row["max_residue_id"],
                "mean_top_anomaly_displacement": f"{row['mean_top_anomaly_displacement']:.4f}" if not math.isnan(row["mean_top_anomaly_displacement"]) else "",
            })


# ===========================================================================
# PART 2 — Residue-Level Structural Context
# ===========================================================================

def _find_anomaly_cluster(adapter, top_anomaly_residues: list,
                          frame_idx: int = 0, radius: float = _NEIGHBOURHOOD_RADIUS) -> set:
    """
    Return set of residue *numbers* that lie within `radius` Å of any
    top-anomaly residue Cα (or first atom of residue) in `frame_idx`.
    """
    xyz = adapter.get_frame_xyz(frame_idx)
    res_table = adapter.get_residue_table()
    res_map = adapter.get_residue_map()

    # Build resnum -> first-atom index mapping
    res_first_atom: dict = {}
    for atom_idx, rn in enumerate(res_map):
        if rn not in res_first_atom:
            res_first_atom[rn] = atom_idx

    # Positions of top anomaly residues
    top_resnums = set()
    top_positions = []
    for r_idx in top_anomaly_residues:
        if r_idx < len(res_table):
            rn = res_table[r_idx]["resnum"]
            top_resnums.add(rn)
            atom_i = res_first_atom.get(rn)
            if atom_i is not None and atom_i < len(xyz):
                top_positions.append(xyz[atom_i])

    if not top_positions:
        return top_resnums

    # Find all residues within radius of any top-anomaly position
    cluster = set(top_resnums)
    r2 = radius * radius
    for rn, atom_i in res_first_atom.items():
        if atom_i >= len(xyz):
            continue
        pos = xyz[atom_i]
        for tp in top_positions:
            dx, dy, dz = pos[0] - tp[0], pos[1] - tp[1], pos[2] - tp[2]
            if dx * dx + dy * dy + dz * dz <= r2:
                cluster.add(rn)
                break
    return cluster


def _local_neighborhood_motion(adapter, resnum: int, res_map: list,
                                frame_a: int, frame_b: int,
                                radius: float = _NEIGHBOURHOOD_RADIUS) -> float:
    """
    Mean displacement of atoms within `radius` Å of `resnum`'s centroid
    between frame_a and frame_b.
    """
    xyz_a = adapter.get_frame_xyz(frame_a)
    xyz_b = adapter.get_frame_xyz(frame_b)

    # Centroid of resnum in frame_a
    res_indices = [i for i, r in enumerate(res_map) if r == resnum]
    if not res_indices:
        return float("nan")

    cx = sum(xyz_a[i][0] for i in res_indices) / len(res_indices)
    cy = sum(xyz_a[i][1] for i in res_indices) / len(res_indices)
    cz = sum(xyz_a[i][2] for i in res_indices) / len(res_indices)

    r2 = radius * radius
    displacements = []
    for i, (a, b) in enumerate(zip(xyz_a, xyz_b)):
        dx, dy, dz = a[0] - cx, a[1] - cy, a[2] - cz
        if dx * dx + dy * dy + dz * dz <= r2:
            ddx, ddy, ddz = a[0] - b[0], a[1] - b[1], a[2] - b[2]
            displacements.append(math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz))

    if not displacements:
        return float("nan")
    return sum(displacements) / len(displacements)


def compute_residue_structural_context(adapter, residue_candidates: list,
                                       top_anomaly_residues: list) -> list:
    """
    For each candidate residue compute:
      - mean_variance              : average positional variance across trajectory
      - local_neighborhood_motion : mean displacement within 5 Å (frame 0 → 1)
      - in_anomaly_cluster        : boolean cluster membership
    """
    res_map = adapter.get_residue_map()
    n_frames = adapter.get_meta()["n_frames"]

    # Positional variance for all residues
    all_variances = _residue_positional_variance(adapter, res_map)

    # Anomaly cluster
    cluster = _find_anomaly_cluster(adapter, top_anomaly_residues, frame_idx=0)

    # Reference frames for neighbourhood motion (first two frames)
    frame_a = 0
    frame_b = min(1, n_frames - 1)

    rows = []
    for resnum in residue_candidates:
        mean_var = all_variances.get(resnum, float("nan"))
        local_motion = _local_neighborhood_motion(
            adapter, resnum, res_map, frame_a, frame_b
        )
        in_cluster = resnum in cluster

        rows.append({
            "residue_id": resnum,
            "mean_variance": mean_var,
            "local_neighborhood_motion": local_motion,
            "in_anomaly_cluster": in_cluster,
        })

    return rows


def save_residue_context(rows: list, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fieldnames = [
        "residue_id", "mean_variance",
        "local_neighborhood_motion", "in_anomaly_cluster",
    ]
    with open(output_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            mv = row["mean_variance"]
            lm = row["local_neighborhood_motion"]
            writer.writerow({
                "residue_id": row["residue_id"],
                "mean_variance": f"{mv:.4f}" if not math.isnan(mv) else "",
                "local_neighborhood_motion": f"{lm:.4f}" if not math.isnan(lm) else "",
                "in_anomaly_cluster": str(row["in_anomaly_cluster"]),
            })


# ===========================================================================
# PART 3 — Case Study Snapshot Preparation
# ===========================================================================

def _get_top3_anomaly_frames() -> list:
    """
    Return the top-3 frame indices sorted by highest anomaly score.
    Falls back to [0, 1, 2] if hotspots.json is unavailable.
    """
    hotspots = _load_json_safe(os.path.join(_VIEWER_DIR, "hotspots.json"))
    if not hotspots or not isinstance(hotspots, list):
        return [0, 1, 2]
    sorted_hs = sorted(hotspots, key=lambda h: h.get("score", 0.0), reverse=True)
    return [int(h["frame"]) for h in sorted_hs[:3]]


def _export_snapshot_anomaly(adapter, frame_idx: int,
                              top_anomaly_residues: list,
                              out_path: str) -> None:
    """
    Save a 3-D scatter PNG highlighting Cα atoms coloured by anomaly score.
    """
    if not _HAS_MPL:
        _write_placeholder(out_path, f"frame {frame_idx} anomaly snapshot "
                                     "(matplotlib unavailable)")
        return

    ca_positions = adapter.get_ca_xyz(frame_idx)
    if not ca_positions:
        _write_placeholder(out_path, f"frame {frame_idx}: no Cα data")
        return

    anomaly_data = _load_json_safe(
        os.path.join(_VIEWER_DIR, "anomaly_residue.json")
    )
    frame_scores: dict = {}
    if anomaly_data and str(frame_idx) in anomaly_data:
        raw = anomaly_data[str(frame_idx)]
        if isinstance(raw, dict):
            frame_scores = {int(k): float(v) for k, v in raw.items()}

    n = len(ca_positions)
    scores = [frame_scores.get(i, 0.0) for i in range(n)]
    highlight = [i in top_anomaly_residues for i in range(n)]

    xs = [p[0] for p in ca_positions]
    ys = [p[1] for p in ca_positions]
    zs = [p[2] for p in ca_positions]

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")

    sc = ax.scatter(xs, ys, zs, c=scores, cmap="hot_r", s=40,
                    vmin=0.0, vmax=1.0, alpha=0.8, label="Residues")

    # Overlay top anomaly residues
    top_x = [xs[i] for i in range(n) if highlight[i]]
    top_y = [ys[i] for i in range(n) if highlight[i]]
    top_z = [zs[i] for i in range(n) if highlight[i]]
    if top_x:
        ax.scatter(top_x, top_y, top_z, c="yellow", s=100,
                   edgecolors="red", linewidths=1.5,
                   label="Top anomaly", zorder=5)

    fig.colorbar(sc, ax=ax, shrink=0.6, label="Anomaly score")
    ax.set_title(f"Frame {frame_idx} – Anomaly Highlight")
    ax.set_xlabel("X (Å)")
    ax.set_ylabel("Y (Å)")
    ax.set_zlabel("Z (Å)")
    ax.legend(loc="upper left", fontsize=8)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _export_snapshot_rmsf(adapter, frame_idx: int,
                           rmsf_by_residue: dict,
                           out_path: str) -> None:
    """
    Save a 3-D scatter PNG with Cα atoms coloured by RMSF.
    """
    if not _HAS_MPL:
        _write_placeholder(out_path, f"frame {frame_idx} RMSF snapshot "
                                     "(matplotlib unavailable)")
        return

    ca_positions = adapter.get_ca_xyz(frame_idx)
    if not ca_positions:
        _write_placeholder(out_path, f"frame {frame_idx}: no Cα data")
        return

    n = len(ca_positions)
    rmsf_vals = [rmsf_by_residue.get(i, 0.0) for i in range(n)]

    xs = [p[0] for p in ca_positions]
    ys = [p[1] for p in ca_positions]
    zs = [p[2] for p in ca_positions]

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")

    sc = ax.scatter(xs, ys, zs, c=rmsf_vals, cmap="coolwarm", s=40,
                    vmin=0.0, vmax=1.0, alpha=0.8)

    fig.colorbar(sc, ax=ax, shrink=0.6, label="RMSF (normalized)")
    ax.set_title(f"Frame {frame_idx} – RMSF Highlight")
    ax.set_xlabel("X (Å)")
    ax.set_ylabel("Y (Å)")
    ax.set_zlabel("Z (Å)")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _write_placeholder(path: str, message: str) -> None:
    """Write a plain-text placeholder when image export is unavailable."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    txt_path = os.path.splitext(path)[0] + ".txt"
    with open(txt_path, "w") as fh:
        fh.write(message + "\n")
    print(f"  [placeholder] {txt_path}")


def export_case_study_snapshots(adapter, top_anomaly_residues: list,
                                 rmsf_by_residue: dict) -> list:
    """
    Export anomaly + RMSF PNG snapshots for the top-3 anomaly frames.
    Returns list of exported file paths.
    """
    top3 = _get_top3_anomaly_frames()
    exported = []

    for frame_idx in top3:
        anomaly_path = os.path.join(
            _IMAGES_DIR, f"frame_{frame_idx}_anomaly.png"
        )
        rmsf_path = os.path.join(
            _IMAGES_DIR, f"frame_{frame_idx}_rmsf.png"
        )

        print(f"  Exporting frame {frame_idx} snapshots …")
        _export_snapshot_anomaly(adapter, frame_idx, top_anomaly_residues,
                                 anomaly_path)
        _export_snapshot_rmsf(adapter, frame_idx, rmsf_by_residue, rmsf_path)

        exported.extend([anomaly_path, rmsf_path])

    return exported


# ===========================================================================
# Summary printing
# ===========================================================================

def print_summary(frame_rows: list, residue_rows: list,
                  top_anomaly_residues: list) -> None:
    """Print structural metrics summary, top displacement residues,
    and cluster membership counts."""
    sep = "=" * 65

    print(f"\n{sep}")
    print("  STRUCTURAL METRICS SUMMARY — Chapter 9 Case Inspection")
    print(sep)

    # Frame metrics
    print("\n[Frame-Level Metrics]")
    print(f"  {'Frame':>6}  {'RMSD_prev':>10}  {'RMSD_next':>10}  "
          f"{'MaxDisp':>10}  {'MaxResID':>10}")
    for r in frame_rows:
        rp = f"{r['rmsd_prev']:.3f}" if not math.isnan(r["rmsd_prev"]) else "   N/A"
        rn = f"{r['rmsd_next']:.3f}" if not math.isnan(r["rmsd_next"]) else "   N/A"
        md = f"{r['max_displacement']:.3f}" if not math.isnan(r["max_displacement"]) else "   N/A"
        print(f"  {r['frame_index']:>6}  {rp:>10}  {rn:>10}  "
              f"{md:>10}  {r['max_residue_id']:>10}")

    # Top displacement residues across all candidate frames
    print("\n[Top Displacement Residues across candidate frames]")
    disp_map: dict = {}
    for r in frame_rows:
        rid = r["max_residue_id"]
        md = r["max_displacement"]
        if rid >= 0 and not math.isnan(md):
            if rid not in disp_map or disp_map[rid] < md:
                disp_map[rid] = md
    top_disp = sorted(disp_map, key=lambda x: disp_map[x], reverse=True)[:10]
    for rid in top_disp:
        print(f"  Residue {rid:>5}: max_displacement = {disp_map[rid]:.4f} Å")

    # Residue cluster membership
    in_cluster = sum(1 for r in residue_rows if r["in_anomaly_cluster"])
    out_cluster = len(residue_rows) - in_cluster
    print("\n[Cluster Membership Counts]")
    print(f"  Candidate residues total : {len(residue_rows)}")
    print(f"  In anomaly cluster       : {in_cluster}")
    print(f"  Outside anomaly cluster  : {out_cluster}")

    print(f"\n{sep}\n")


# ===========================================================================
# Main entry point
# ===========================================================================

def main() -> None:
    print("Chapter 9 Case Study Inspection – starting …\n")

    # ------------------------------------------------------------------
    # Load trajectory adapter
    # ------------------------------------------------------------------
    sys.path.insert(0, _REPO_ROOT)
    try:
        from trajectory_adapter import get_adapter
        adapter = get_adapter()
        meta = adapter.get_meta()
        print(f"Trajectory loaded: {meta['n_frames']} frames, "
              f"{meta['n_residues']} residues, {meta['n_atoms']} atoms")
    except Exception as exc:
        print(f"ERROR: Could not load trajectory adapter: {exc}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Load input CSVs
    # ------------------------------------------------------------------
    try:
        frame_candidates = _load_frame_candidates(_FRAME_CSV)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        residue_candidates = _load_residue_candidates(_RESIDUE_CSV)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Frame candidates: {len(frame_candidates)}")
    print(f"Residue candidates: {len(residue_candidates)}")

    # ------------------------------------------------------------------
    # Shared derived data
    # ------------------------------------------------------------------
    n_frames = meta["n_frames"]
    top_anomaly_residues = _get_top_anomaly_residues(n_frames)
    rmsf_by_residue = _get_rmsf_by_residue()

    # ------------------------------------------------------------------
    # PART 1 — Frame-Level Structural Quantification
    # ------------------------------------------------------------------
    print("\n[PART 1] Computing frame-level structural metrics …")
    frame_rows = compute_frame_structural_metrics(
        adapter, frame_candidates, top_anomaly_residues
    )
    out_frame_csv = os.path.join(_OUTPUT_DIR, "frame_structural_metrics.csv")
    save_frame_metrics(frame_rows, out_frame_csv)
    print(f"  Saved → {out_frame_csv}")

    # ------------------------------------------------------------------
    # PART 2 — Residue-Level Structural Context
    # ------------------------------------------------------------------
    print("\n[PART 2] Computing residue-level structural context …")
    residue_rows = compute_residue_structural_context(
        adapter, residue_candidates, top_anomaly_residues
    )
    out_residue_csv = os.path.join(_OUTPUT_DIR, "residue_structural_context.csv")
    save_residue_context(residue_rows, out_residue_csv)
    print(f"  Saved → {out_residue_csv}")

    # ------------------------------------------------------------------
    # PART 3 — Case Study Snapshot Preparation
    # ------------------------------------------------------------------
    print("\n[PART 3] Exporting case study snapshots …")
    exported = export_case_study_snapshots(
        adapter, top_anomaly_residues, rmsf_by_residue
    )
    for p in exported:
        print(f"  Saved → {p}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print_summary(frame_rows, residue_rows, top_anomaly_residues)


if __name__ == "__main__":
    main()
