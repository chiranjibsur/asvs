import os
import io
from flask import Flask, send_from_directory, request, jsonify, render_template, send_file, abort

from asvs.trajectory_adapter import register_routes

# Initialize Flask app
app = Flask(__name__)


register_routes(app)
# ---- add near top of app.py (after Flask imports) ----
import os
import json
from flask import jsonify
try:
    import MDAnalysis as mda
except Exception as e:
    mda = None

# Configure paths to your viewer files
PDB_PATH = os.environ.get("ASVS_PDB", "viewer/topology.pdb")
XTC_PATH = os.environ.get("ASVS_XTC", "viewer/trajectory.xtc")

# Simple singleton cache
_UNIVERSE = None
_RESNOS = None  # list[int] length = n_atoms

def get_universe():
    """Load and cache the MDAnalysis Universe (one-time)."""
    global _UNIVERSE
    if _UNIVERSE is None:
        if mda is None:
            raise RuntimeError("MDAnalysis not available in this environment")
        if not (os.path.exists(PDB_PATH) and os.path.exists(XTC_PATH)):
            raise FileNotFoundError(f"Missing topology/trajectory at {PDB_PATH} / {XTC_PATH}")
        _UNIVERSE = mda.Universe(PDB_PATH, XTC_PATH)
        # Optionally prime to frame 0
        _ = _UNIVERSE.trajectory[0]
    return _UNIVERSE

def get_residue_map():
    """Return atomIndex -> PDB residue number (resnum) array; cache it."""
    global _RESNOS
    if _RESNOS is None:
        u = get_universe()
        # PDB-style residue numbers (can include insertion codes in PDB, but resnum is int)
        _RESNOS = [int(atom.resnum) for atom in u.atoms]
    return _RESNOS

def parse_pdb_info(pdb_content):
    """Parse basic information from PDB file"""
    lines = pdb_content.splitlines()
    
    # Count atoms, residues, and chains
    atoms = 0
    residues = set()
    chains = set()
    
    for line in lines:
        if line.startswith("ATOM") or line.startswith("HETATM"):
            atoms += 1
            try:
                residue_id = line[22:27].strip()
                chain_id = line[21]
                residues.add(residue_id + chain_id)
                chains.add(chain_id)
            except:
                pass
    
    return {
        "atoms": atoms,
        "residues": len(residues),
        "chains": len(chains)
    }

@app.route('/')
def index():
    # Serve the index.html file directly as static content
    return send_file('templates/index.html')

@app.route('/load_example')
def load_example():
    """Load example PDB file"""
    example_path = os.path.join(os.path.dirname(__file__), "static/examples/1cbs.pdb")
    
    if os.path.exists(example_path):
        with open(example_path, 'r') as f:
            pdb_content = f.read()
        
        # Parse PDB info
        info = parse_pdb_info(pdb_content)
        info["filename"] = "1cbs.pdb"
        
        print(f"Loaded PDB with {info['atoms']} atoms, {info['residues']} residues, {info['chains']} chains")
        
        return jsonify({
            "info": info,
            "content": pdb_content
        })
    else:
        return jsonify({"error": f"Example file not found: {example_path}"}), 404

@app.route('/upload_pdb', methods=['POST'])
def upload_pdb():
    """Handle PDB file upload"""
    # Check if request has a file
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    
    # If user doesn't select a file
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Check if file is a PDB
    if not file.filename.lower().endswith('.pdb'):
        return jsonify({"error": "Not a PDB file (must end with .pdb)"}), 400
    
    # Read the file content
    pdb_content = file.read().decode('utf-8')
    
    # Validate the file has atom entries
    if not 'ATOM' in pdb_content and not 'HETATM' in pdb_content:
        return jsonify({"error": "Invalid PDB file format (no ATOM or HETATM entries)"}), 400
    
    # Parse PDB info
    info = parse_pdb_info(pdb_content)
    info["filename"] = file.filename
    
    print(f"Uploaded PDB with {info['atoms']} atoms, {info['residues']} residues, {info['chains']} chains")
    
    return jsonify({
        "info": info,
        "content": pdb_content
    })

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route("/viewer")
def viewer_page():
    return render_template("index.html")

@app.route("/viewer/<path:filename>")
def serve_viewer_files(filename):
    root = os.path.join(os.path.dirname(__file__), "viewer")
    file_path = os.path.join(root, filename)
    if not os.path.isfile(file_path):
        abort(404)
    return send_from_directory(root, filename)

import json
from flask import jsonify

@app.route("/api/hotspots/<int:frame>")
def get_hotspot_frame(frame):
    """
    Returns per-residue hotspot scores for a given frame.
    Reads from viewer/hotspots_residue.json
    """
    try:
        with open("viewer/hotspots_residue.json") as f:
            hotspots = json.load(f)
        # JSON keys are stored as strings
        frame_data = hotspots.get(str(frame))
        if frame_data is None:
            return jsonify({"error": f"Frame {frame} not found"}), 404
        return jsonify(frame_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trajectory/residue_map")
def residue_map():
    """
    Returns a mapping from atom index (0-based) to PDB residue number (resnum).
    {
      "resnos": [145,145,145,146,146,...]  # len == n_atoms
    }
    """
    try:
        resnos = get_residue_map()
        return jsonify({"resnos": resnos})
    except Exception as e:
        # helpful error for debugging
        return jsonify({"error": str(e), "pdb": PDB_PATH, "xtc": XTC_PATH}), 500

@app.route("/api/trajectory/residue_table")
def residue_table():
    """
    One-time residue table:
      index: 0-based residue index (matches /api/trajectory/residue_map values)
      resnum: PDB residue number
      resname: residue name
      chain: chain/segment id (segid if present, else guess from atom.chainID if available)
    """
    tbl = []
    # Prefer segid when present; fall back to chainIDs if available
    for r in u.residues:
        chain = getattr(r, 'segid', '') or (getattr(r.atoms[0], 'chainID', '') if len(r.atoms) else '')
        tbl.append({
            "index": int(r.ix),
            "resnum": int(getattr(r, 'resnum', r.id) if hasattr(r, 'resnum') else r.id),
            "resname": str(r.resname),
            "chain": str(chain)
        })
    return jsonify({"residues": tbl})

@app.route('/viewer/ballstick')
def ballstick_viewer():
    """Serves the ball-and-stick visualization page."""
    return render_template('ballstick_viewer.html')

@app.route('/viewer/ballstick_frames/<path:filename>')
def serve_ballstick_frames(filename):
    """Serves frames.json or other outputs for ballstick view."""
    folder = os.path.join('viewer', 'ballstick_frames')
    return send_from_directory(folder, filename)

if __name__ == '__main__':
    os.makedirs('static/examples', exist_ok=True)
    example_path = 'static/examples/1cbs.pdb'
    if not os.path.exists(example_path):
        import urllib.request
        url = 'https://files.rcsb.org/download/1CBS.pdb'
        try:
            urllib.request.urlretrieve(url, example_path)
            print(f"Downloaded example PDB file to {example_path}")
        except Exception as e:
            print(f"Error downloading example file: {e}")

    # Note: this hardcodes port 5000; env vars won't override.
    app.run(host='0.0.0.0', port=5000)
