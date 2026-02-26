# Phase 1 Troubleshooting Guide

## Issue: Clicking on molecules doesn't show info panel

### Step 1: Verify Server is Running

```bash
# Start the server
python app.py

# You should see:
# * Running on http://127.0.0.1:5000
# * Debug mode: on
```

### Step 2: Test API Endpoints

Open your browser and test these URLs:

1. **Test metadata endpoint:**
   ```
   http://localhost:5000/api/trajectory/meta
   ```
   Should return: `{"n_atoms": 374, "n_frames": 194, "n_residues": 374}`

2. **Test residue metadata:**
   ```
   http://localhost:5000/api/trajectory/residue_meta
   ```
   Should return JSON with residue information

3. **Test frame data:**
   ```
   http://localhost:5000/api/trajectory/frame/0
   ```
   Should return JSON with xyz coordinates

4. **Test hotspot data:**
   ```
   http://localhost:5000/api/hotspots/0
   ```
   Should return JSON with hotspot scores

**If any of these fail, there's an issue with your data files or server setup.**

### Step 3: Open Browser Developer Console

1. Open the viewer (e.g., http://localhost:5000/viewer/ballstick)
2. Press **F12** to open Developer Tools
3. Go to the **Console** tab
4. Look for any **red error messages**

Common errors and solutions:

#### Error: "Failed to fetch"
- **Cause:** Server is not running or wrong URL
- **Solution:** Make sure Flask server is running on port 5000

#### Error: "404 Not Found"
- **Cause:** Missing API endpoint or incorrect route
- **Solution:** Verify app.py has all routes (see below)

#### Error: "Cannot read property of undefined"
- **Cause:** Data structure mismatch
- **Solution:** Check browser console for specific error, may need to reload page

### Step 4: Verify Data Files Exist

```bash
ls -lh viewer/
```

You should see:
- `topology.pdb` - Molecular structure
- `trajectory.xtc` - Trajectory frames  
- `hotspots_residue.json` - Hotspot data

**If these files are missing, the viewers won't work.**

### Step 5: Check JavaScript is Loading

In browser Developer Tools (F12):
1. Go to **Network** tab
2. Refresh the page
3. Look for these files (should be status 200):
   - `ballstick_viewer.js` (or `ribbon_viewer.js`, `simple_visualizer.js`)
   - `three.min.js`
   - `OrbitControls.js`

**If any show 404, the JavaScript files are missing or paths are wrong.**

### Step 6: Test Clicking Step-by-Step

#### For Ball-and-Stick Viewer:
1. Navigate to http://localhost:5000/viewer/ballstick
2. **Wait 2-3 seconds** for molecule to load
3. You should see colored spheres (atoms) connected by cylinders (bonds)
4. Click **directly on a sphere** (not between them)
5. Info panel should appear on the right
6. Selected atom should turn **bright yellow**

#### For Ribbon Viewer:
1. Navigate to http://localhost:5000/viewer/ribbon
2. **Wait 2-3 seconds** for ribbon to load
3. You should see a colored tube/ribbon
4. Click **anywhere on the ribbon tube**
5. Info panel should appear on the right

#### For Hotspot (Points) Viewer:
1. Navigate to http://localhost:5000/viewer
2. **Wait 2-3 seconds** for points to load
3. You should see many colored dots
4. Click **directly on a dot** (zoom in if needed)
5. Info panel should appear on the right

### Step 7: Check Browser Console for Click Events

In Developer Console, type:

```javascript
// For ball-and-stick
console.log('Testing click detection');

// Check if raycaster exists
console.log(typeof raycaster !== 'undefined' ? 'Raycaster loaded' : 'Raycaster missing');
```

### Step 8: Verify Required Routes in app.py

Your `app.py` must have these routes:

```python
@app.route("/viewer/ballstick")
def viewer_ballstick():
    return render_template("ballstick_viewer.html")

@app.route("/viewer/ribbon")
def viewer_ribbon():
    return render_template("ribbon_viewer.html")

@app.route("/api/trajectory/meta")
@app.route("/api/trajectory/residue_meta")
@app.route("/api/trajectory/frame/<int:frame>")
@app.route("/api/hotspots/<int:frame>")
@app.route("/api/trajectory/atoms")
@app.route("/api/trajectory/ca/<int:frame>")
```

### Common Issues and Solutions

#### Issue: "Nothing happens when I click"

**Solution 1: Wait for molecule to load**
- The status at the bottom should say "frame 0 loaded" or similar
- If it says "initializing...", wait a few more seconds

**Solution 2: Click more precisely**
- In ball-and-stick: Click directly on the center of a sphere
- In ribbon: Click on the thick part of the ribbon, not edges
- In hotspot: Zoom in closer and click directly on a point

**Solution 3: Check if Three.js is working**
- Can you rotate the molecule by dragging with mouse?
- Can you zoom in/out with scroll wheel?
- If not, Three.js may not be loaded properly

#### Issue: "Info panel appears but shows wrong data"

**Solution:** Check that your hotspot data matches the trajectory
- Verify `viewer/hotspots_residue.json` has data for frame 0
- Check that residue numbers match between topology and hotspot data

#### Issue: "Atom turns yellow but no info panel"

**Solution:** Check that `infoPanel` div exists in HTML
```bash
grep -n "infoPanel" templates/ballstick_viewer.html
```
Should show line with `<div id="infoPanel"></div>`

#### Issue: "Server starts but API calls fail"

**Solution:** Check MDAnalysis can load trajectory
```python
python3 -c "import MDAnalysis as mda; u = mda.Universe('viewer/topology.pdb', 'viewer/trajectory.xtc'); print(f'Loaded {len(u.trajectory)} frames')"
```

### Getting Help

If none of these solutions work:

1. **Capture browser console errors:**
   - Open Developer Tools (F12)
   - Copy all red error messages
   - Share them in the issue

2. **Capture server logs:**
   - Look at terminal where `python app.py` is running
   - Copy any error messages
   - Share them in the issue

3. **Check server is responding:**
   ```bash
   curl http://localhost:5000/api/trajectory/meta
   ```
   Share the output

4. **Share your setup:**
   - Operating system (Windows/Mac/Linux)
   - Python version: `python --version`
   - Browser (Chrome/Firefox/Safari)
   - Any proxy or firewall settings
