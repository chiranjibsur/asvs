# Phase 3 Scope Review - Prompt for Discussion

## Quick Overview

**Phase 3 Focus:** Add interactive analysis tools to the molecular viewer

**Timeline:** 2-3 weeks after Phase 2 merge

**Main Features:**
1. **Molecular Slicing (Clip Planes)** - Cut through molecules to see interior
2. **Distance Measurements** - Measure distances between atoms/residues
3. **Export Tools** - Save images and analysis data

---

## Feature 1: Molecular Slicing (Priority: HIGH)

### What it does:
- Adds interactive "clip planes" that slice through the molecular structure
- Like cutting a 3D model with a plane to see what's inside
- Helps visualize binding pockets, cavities, and internal structures

### User Experience:
- Toggle button: "Enable Clipping"
- Control panel appears with:
  - Axis selector (X, Y, or Z)
  - Slider to move plane position
  - Add/Remove plane buttons
  - Visual yellow plane helper in viewer

### Technical Approach:
- Uses Three.js built-in clipping planes
- Real-time updates as user adjusts slider
- Support for multiple planes (up to 6)
- Applies to all atom/bond geometry

### Use Cases:
- Viewing protein binding sites
- Analyzing internal cavities
- Understanding fold structures
- Identifying buried residues

### Questions to Consider:
- How many clip planes do users typically need? (Suggested: Start with 1, allow up to 3)
- Should planes be saveable/loadable?
- Should we support angled planes (not just X/Y/Z)?

---

## Feature 2: Distance Measurement Tool (Priority: MEDIUM)

### What it does:
- Click two atoms to measure the distance between them
- Shows visual line and distance value in Ångströms (Å)
- Keeps history of all measurements
- Useful for analyzing bond lengths, residue distances

### User Experience:
- Toggle button: "Measure Distance"
- Cursor changes to crosshair in measurement mode
- Click atom 1, then click atom 2
- Purple line appears with distance label
- Measurements panel shows all measurements
- "Clear All" button to reset

### Technical Approach:
- Uses Three.js raycasting for atom selection
- Vector3.distanceTo() for accurate distance calculation
- Creates visual markers (spheres) and lines
- Stores measurement data in array

### Use Cases:
- Measuring bond lengths
- Analyzing residue-residue distances
- Validating structure quality
- Comparing with experimental data

### Questions to Consider:
- Should we add angle measurements (3 points)? (Suggested: Phase 3.5 or Phase 4)
- Should measurements persist across frames? (Suggested: Optional toggle)
- Should we show measurements in different units (nm, pm)?

---

## Feature 3: Export Capabilities (Priority: HIGH)

### What it does:
- Export visualizations as PNG images
- Export measurement data as JSON
- Export contact network data as CSV
- Enables users to save their analysis work

### User Experience:
- "Export ▼" dropdown button with 3 options:
  1. PNG Image - Current view as image
  2. Measurements (JSON) - All distance measurements
  3. Contacts (CSV) - Contact network data
- Files downloaded with timestamps

### Technical Approach:
- Canvas.toDataURL() for image export
- Blob API for data file creation
- JSON format for measurements (with metadata)
- CSV format for contacts (easy import to Excel/R/Python)

### Export Formats:

**PNG Image:**
- Current visualization exactly as shown
- Full resolution based on canvas size
- No watermarks

**Measurements JSON:**
```json
{
  "timestamp": "2025-11-07T12:00:00Z",
  "frame": 0,
  "measurements": [
    {
      "id": 1,
      "atom1": 11,
      "atom2": 45,
      "distance": 3.87,
      "unit": "angstrom"
    }
  ]
}
```

**Contacts CSV:**
```csv
Residue1,Residue2,Frequency
0,3,1.0
0,4,1.0
1,5,0.98
```

### Questions to Consider:
- Should we support SVG export (vector graphics)? (Suggested: Phase 4)
- Should we export RMSF data as well?
- Should exports include current frame info?

---

## Implementation Priority

### Must Have (Core Phase 3):
✅ Basic clip plane (1 plane, X/Y/Z axis)
✅ Distance measurement (2-point)
✅ PNG image export
✅ Measurements JSON export
✅ Contacts CSV export

### Nice to Have (Can be added later):
⏳ Multiple clip planes (2-3 simultaneously)
⏳ Angle measurements (3-point)
⏳ Measurement labels in 3D space
⏳ SVG export
⏳ Video/animation export

### Phase 4 Candidates:
🔮 Angled/rotated clip planes
🔮 Dihedral angle measurements
🔮 Surface area calculations
🔮 Volume calculations
🔮 Collaborative features

---

## Estimated Effort

| Feature | Complexity | Time Estimate |
|---------|-----------|---------------|
| Basic Clipping | Medium | 3-4 days |
| Multiple Planes | Low | 1 day |
| Distance Tool | Low | 2-3 days |
| Export (PNG) | Low | 1 day |
| Export (Data) | Low | 1 day |
| Testing & Polish | Medium | 2-3 days |
| **Total** | | **10-13 days** |

---

## Questions for Review

### Scope Questions:
1. Should Phase 3 include angle measurements, or save for Phase 4?
2. How important is multi-plane support (vs. single plane)?
3. Should measurements persist when changing frames?
4. Do we need undo/redo for measurements?

### UI/UX Questions:
5. Should clip plane controls be always visible or toggle-able?
6. Should measurement mode be modal (disable other interactions)?
7. Should we show measurement labels directly in 3D or only in panel?
8. Should export menu be a dropdown or separate buttons?

### Technical Questions:
9. Should we support clip planes in ribbon viewer? (Suggested: Yes, simplified)
10. Should we support clip planes in points viewer? (Suggested: Yes)
11. Should measurements work across all 3 viewers? (Suggested: Ball-stick only initially)
12. What's the WebGL performance impact of multiple clip planes?

---

## Success Criteria

Phase 3 will be considered complete when:

- [ ] User can enable/disable clipping plane
- [ ] User can adjust clip plane axis and position
- [ ] User can measure distance between any 2 atoms
- [ ] User can export current view as PNG
- [ ] User can export measurements as JSON
- [ ] User can export contacts as CSV
- [ ] All features work without errors
- [ ] Performance remains acceptable (>30 FPS)
- [ ] Documentation is complete
- [ ] Code review passed
- [ ] Security scan passed

---

## Recommended Next Steps

1. **Review this document** and provide feedback
2. **Prioritize features** - confirm must-have vs nice-to-have
3. **Answer key questions** above
4. **Approve scope** - once satisfied with feature set
5. **Merge Phase 2 PR** - establish baseline for Phase 3
6. **Create Phase 3 branch** - begin implementation
7. **Weekly check-ins** - review progress and adjust scope if needed

---

## Chat with AI Assistant Prompt

If you want to discuss Phase 3 with an AI assistant, use this prompt:

```
I'm working on a molecular visualization web app. We've completed Phase 2 
(RMSF visualization and contact networks). Now planning Phase 3 which will add:

1. Molecular slicing with clip planes
2. Distance measurement tools  
3. Export capabilities (PNG, JSON, CSV)

Questions:
- Should we support multiple clip planes or start with just one?
- Should measurements work across all 3 viewers (ball-stick, ribbon, points)?
- Should we include angle measurements or save that for Phase 4?
- What's the best UX for the clip plane controls?
- Should measurements persist when changing animation frames?

Tech stack: Three.js for 3D, Flask backend, vanilla JavaScript frontend.
Target users: Researchers analyzing protein dynamics.

Please review the scope and suggest priorities, potential issues, and implementation approaches.
```

---

**Ready to proceed?** Reply with approval or questions!
