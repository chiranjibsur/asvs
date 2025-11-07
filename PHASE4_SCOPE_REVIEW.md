# Phase 4 Scope Review - Advanced Analysis & Export

## Quick Overview

**Phase 4 Focus:** Advanced measurement tools, enhanced export, and performance optimization

**Timeline:** 3-4 weeks after Phase 3 merge

**Main Features:**
1. **Angle Measurements** - 3-point and 4-point (dihedral) angle tools
2. **Advanced Clipping** - Rotated planes, animations, save/load presets
3. **Enhanced Export** - SVG vector, video/GIF, 3D models
4. **Performance & UX** - FPS monitoring, level-of-detail rendering

---

## Feature 1: Angle Measurements (Priority: HIGH)

### What it does:
- Measures angles between three atoms (3-point)
- Measures dihedral/torsion angles between four atoms (4-point)
- Visual arc display showing the measured angle
- Export angle data alongside distance measurements

### User Experience:
- Toggle button: "Measure Angle"
- Click mode selector: "3-Point Angle" or "4-Point Dihedral"
- Click 3 or 4 atoms to measure
- Visual arc appears showing angle
- Angle value displayed in degrees
- Added to measurements history panel

### Technical Approach:
- Extend existing measurement system from Phase 3
- Use Vector3.angleTo() for 3-point angles
- Calculate dihedral using cross products and atan2
- Create arc geometry for visual display
- Store angle type in measurements array

### Use Cases:
- Analyzing bond angles in molecular structures
- Measuring protein backbone angles (phi, psi)
- Validating structure quality
- Comparing conformational changes across frames

### Questions to Consider:
- Should angles be calculated in degrees or radians? (Suggested: degrees)
- Show both signed and unsigned dihedrals? (Suggested: signed)
- Visual style for arc display? (Suggested: semi-transparent arc with label)

---

## Feature 2: Advanced Clipping (Priority: MEDIUM)

### What it does:
- Support for rotated/angled clip planes (not just X/Y/Z aligned)
- Animated clipping transitions
- Save/load clip plane configurations
- Multiple clip plane presets
- Clip plane intersection highlighting

### User Experience:
- "Rotate Plane" controls with pitch/yaw/roll sliders
- "Animate Clip" button for smooth transitions
- "Save Preset" / "Load Preset" dropdown
- "Show Intersection" toggle for plane intersections
- Visual feedback for plane orientation

### Technical Approach:
- Use quaternions for plane rotation
- Tween.js or custom interpolation for animations
- LocalStorage or JSON export for presets
- Calculate plane-plane intersections for highlighting
- Update PlaneHelper to show rotation axes

### Use Cases:
- Creating custom viewing angles through structure
- Animating through a molecule layer by layer
- Saving common analysis views
- Highlighting structural features at plane intersections

### Questions to Consider:
- How to make rotation intuitive? (Suggested: visual gizmo or trackball)
- Animation duration? (Suggested: 1-2 seconds, configurable)
- Preset naming convention? (Suggested: user-defined names)

---

## Feature 3: Enhanced Export (Priority: HIGH)

### What it does:
- SVG vector export for publication-quality figures
- Video/GIF animation export for trajectories
- 3D model export (OBJ, STL formats)
- Batch export for multiple frames
- Export settings/quality options

### User Experience:
- Expanded "Export ▼" menu with new options
- "Export SVG" - current view as scalable vector
- "Export Animation" - frame range, format (GIF/MP4), quality
- "Export 3D Model" - format selector, coordinate frame
- "Batch Export" - export multiple frames as images
- Progress indicator for long exports

### Technical Approach:
- **SVG**: Use Three.js SVGRenderer or custom path drawing
- **Video/GIF**: Capture frames, use ffmpeg.js or gif.js
- **3D Models**: Export geometry vertices/faces to OBJ/STL
- **Batch**: Queue-based frame processing
- Blob API and JSZip for multi-file downloads

### Use Cases:
- Creating publication figures (SVG)
- Sharing animations on social media (GIF)
- 3D printing models (STL)
- Generating supplementary materials (batch)

### Questions to Consider:
- Video codec? (Suggested: H.264 for MP4, optimized palette for GIF)
- SVG level of detail? (Suggested: simplified for performance)
- 3D model coordinate system? (Suggested: match PDB conventions)

---

## Feature 4: Performance & UX (Priority: MEDIUM)

### What it does:
- Real-time FPS counter and performance monitoring
- Level-of-detail (LOD) rendering for large structures
- Progressive loading for trajectory files
- WebGL 2.0 optimizations
- Performance warnings and suggestions

### User Experience:
- FPS counter chip (top-right corner, toggleable)
- Performance panel with metrics (draw calls, triangles, memory)
- Auto-adjust quality based on FPS
- Loading progress bar for trajectories
- Warning notifications for performance issues

### Technical Approach:
- Monitor renderer.info for stats
- Implement LOD using Three.js LOD objects
- Stream trajectory data instead of loading all
- Use WebGL 2.0 features (UBOs, transform feedback)
- Implement geometry instancing for repeated structures

### Use Cases:
- Debugging performance issues
- Optimizing visualization for large proteins
- Smooth playback of long trajectories
- Better experience on lower-end hardware

### Questions to Consider:
- FPS threshold for warnings? (Suggested: <30 FPS)
- LOD distances? (Suggested: camera-distance based)
- Which features to disable for performance? (Suggested: plane helpers, contacts)

---

## Feature 5: Analysis Tools (Priority: LOW)

### What it does:
- Surface area calculations (solvent accessible surface)
- Volume calculations within clip regions
- Center of mass indicators
- Hydrogen bond visualization
- Salt bridge identification

### User Experience:
- "Analysis" dropdown menu
- "Calculate Surface Area" - shows total/per-residue
- "Calculate Volume" - uses clip planes as boundaries
- "Show Center of Mass" - visual marker
- "Show H-Bonds" - dashed lines with distance labels

### Technical Approach:
- Use marching cubes for surface generation
- Voxel-based volume calculation
- Sum of (mass × position) for COM
- Distance + angle criteria for H-bonds
- Charge-based detection for salt bridges

### Use Cases:
- Quantifying protein size and shape
- Analyzing cavity volumes
- Understanding stability and dynamics
- Identifying key interactions

### Questions to Consider:
- Surface probe radius? (Suggested: 1.4 Å for water)
- Voxel resolution for volume? (Suggested: 0.5 Å)
- H-bond distance cutoff? (Suggested: 3.5 Å, 120° angle)

---

## Implementation Priority

### Must Have (Core Phase 4):
✅ 3-point angle measurements
✅ Dihedral angle measurements (4-point)
✅ SVG vector export
✅ FPS monitoring and display
✅ Angle export in measurements JSON

### Nice to Have (Can be added later):
⏳ Rotated clip planes
⏳ Animated clipping transitions
⏳ Video/GIF animation export
⏳ 3D model export (OBJ/STL)
⏳ Batch export for multiple frames

### Phase 5 Candidates:
🔮 Surface area calculations
🔮 Volume calculations
🔮 Hydrogen bond visualization
🔮 LOD rendering
🔮 WebGL 2.0 optimizations

---

## Estimated Effort

| Feature | Complexity | Time Estimate |
|---------|-----------|---------------|
| 3-Point Angles | Low | 2-3 days |
| Dihedral Angles | Medium | 3-4 days |
| SVG Export | Medium | 3-4 days |
| FPS Monitor | Low | 1-2 days |
| Rotated Planes | High | 4-5 days |
| Video/GIF Export | High | 5-6 days |
| 3D Model Export | Medium | 3-4 days |
| Testing & Polish | Medium | 3-4 days |
| **Total** | | **24-32 days** |

---

## Questions for Review

### Scope Questions:
1. Should Phase 4 include all export formats, or prioritize SVG first?
2. How important is rotated clip plane support vs. more measurement tools?
3. Should we implement video export or defer to Phase 5?
4. Which analysis tools are highest priority (H-bonds, surface area, etc.)?

### UI/UX Questions:
5. Should angle measurements share the measurements panel or have separate UI?
6. How to visualize dihedral angles clearly in 3D?
7. Should FPS monitor be always visible or optional?
8. Export format: separate buttons or unified dialog?

### Technical Questions:
9. Use existing animation frame system or separate video encoder?
10. SVG export: client-side only or offer server-side rendering?
11. Performance budget: target FPS for "good experience"?
12. Should we support undo/redo for measurements and clip planes?

---

## Success Criteria

Phase 4 will be considered complete when:

- [ ] User can measure 3-point angles between atoms
- [ ] User can measure 4-point dihedral angles
- [ ] User can export current view as SVG
- [ ] FPS counter displays real-time performance
- [ ] Angle measurements export correctly in JSON
- [ ] All features work without errors
- [ ] Performance remains acceptable (>30 FPS for typical use)
- [ ] Documentation is complete
- [ ] Code review passed
- [ ] Security scan passed

---

## Recommended Next Steps

1. **Review this document** and provide feedback
2. **Prioritize features** - confirm must-have vs nice-to-have
3. **Answer key questions** above
4. **Approve scope** - once satisfied with feature set
5. **Create Phase 4 branch** - begin implementation
6. **Weekly check-ins** - review progress and adjust scope if needed

---

## Dependencies & Prerequisites

- Phase 3 must be complete and merged
- Measurement system (distance tool) must be working
- Export infrastructure must be in place
- Three.js renderer and controls must be stable

---

**Ready to proceed?** Reply with approval or questions!
