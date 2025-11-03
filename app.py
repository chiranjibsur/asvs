# app.py — stable viewer server with residue hotspots + frame coords
import os
import json
from flask import Flask, jsonify, render_template, send_from_directory, abort

from trajectory_adapter import get_adapter

app = Flask(__name__)

# ---- config for hotspots path (per-residue, per-frame) ----------------------
HOTSPOTS_RES_PATH = os.environ.get(
    "ASVS_HOTSPOTS_RES",
    os.path.join("viewer", "hotspots_residue.json")
)

# Load the adapter once (caches MDAnalysis Universe)
adapter = get_adapter()

# ------------------------------- helpers -------------------------------------
def _to_serializable(obj):
    """
    Convert possible NumPy arrays / scalars to plain Python for jsonify().
    """
    try:
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.floating, np.integer)):
            return obj.item()
    except Exception:
        pass
    return obj

# ------------------------------- UI ROUTES -----------------------------------
@app.route("/")
@app.route("/viewer")
def viewer():
    return render_template("hotspot_viewer.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

@app.route("/viewer/<path:filename>")
def serve_viewer_files(filename):
    """If you keep any extra files under ./viewer."""
    root = os.path.join(os.path.dirname(__file__), "viewer")
    fp = os.path.join(root, filename)
    if not os.path.isfile(fp):
        abort(404)
    return send_from_directory(root, filename)

# ------------------------------- API ROUTES ----------------------------------
@app.route("/api/trajectory/meta")
def api_meta():
    """Basic counts and paths."""
    # Support either adapter.get_meta() or adapter.summary()
    if hasattr(adapter, "get_meta"):
        meta = adapter.get_meta()
    else:
        meta = adapter.summary()
    return jsonify(meta)

@app.route("/api/trajectory/residue_map")
def api_residue_map():
    """
    Returns mapping from atom index (0-based) to residue number (PDB resnum).
    {
      "resnos": [145,145,145,146,146,...]   # len == n_atoms
    }
    """
    resnos = adapter.get_residue_map()
    return jsonify({"resnos": _to_serializable(resnos)})

@app.route("/api/trajectory/residue_meta")
def api_residue_meta():
    """
    Returns residue table for tooltips etc.
    {
      "residues": [
        {"index": 0, "resnum": 1, "resname": "ALA", "chain": "A"},
        ...
      ]
    }
    """
    table = adapter.get_residue_table()
    return jsonify({"residues": _to_serializable(table)})

@app.route("/api/trajectory/frame/<int:frame>")
def api_frame(frame: int):
    """
    Returns atom 3D coordinates for a frame.
    {
      "frame": n,
      "xyz": [[x,y,z], ...]   # len == n_atoms
    }
    """
    xyz = adapter.get_frame_xyz(frame)
    return jsonify({"frame": frame, "xyz": _to_serializable(xyz)})

@app.route("/api/hotspots/<int:frame>")
def api_hotspots_frame(frame: int):
    """
    Returns per-residue hotspot map for a frame.
    {
      "1": 0.12, "2": 0.34, ..., "75": 0.91
    }
    """
    try:
        with open(HOTSPOTS_RES_PATH, "r") as f:
            blob = json.load(f)  # dict[str -> dict[str->float]]
        data = blob.get(str(frame))
        if data is None:
            return jsonify({"error": f"frame {frame} not found in {HOTSPOTS_RES_PATH}"}), 404
        # normalize to floats
        data = {str(k): float(v) for k, v in data.items()}
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": f"missing {HOTSPOTS_RES_PATH}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trajectory/atoms")
def api_atoms():
    """
    One-time atom metadata used to build bonds client-side.
    Returns: { atoms: [{index, element, resnum}], covalent_radii: { 'C': 0.76, ... } }
    """
    return jsonify(adapter.get_atom_table())

@app.route("/api/trajectory/ca/<int:frame>")
def api_ca_frame(frame: int):
    """
    Returns ordered Cα coordinates for a frame:
    { frame: n, ca: [[x,y,z], ...] }
    """
    ca = adapter.get_ca_xyz(frame)
    return jsonify({"frame": frame, "ca": ca})

@app.route("/viewer/ballstick")
def viewer_ballstick():
    return render_template("ballstick_viewer.html")

@app.route("/viewer/ribbon")
def viewer_ribbon():
    return render_template("ribbon_viewer.html")

# ------------------------------- MAIN ----------------------------------------
if __name__ == "__main__":
    # Dev server
    app.run(host="127.0.0.1", port=5000, debug=True)
