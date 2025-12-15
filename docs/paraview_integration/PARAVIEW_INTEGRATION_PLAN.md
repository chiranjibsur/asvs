# ParaView Visualizer Integration Plan

**Project:** ASVS (Advanced Structure Visualization System)  
**Goal:** Integrate ParaView Visualizer features into the existing trame-based ribbon viewer  
**Status:** Planning Phase  
**Last Updated:** December 15, 2024

---

## Executive Summary

This plan outlines the integration of ParaView Visualizer features into the ASVS project. The goal is to enhance the existing trame-based ribbon viewer with ParaView's professional UI patterns and visualization capabilities, combining the best of both trame/three.js and ParaView.

**Key Objectives:**
1. Add ParaView-style Pipeline Browser for visualization pipeline management
2. Implement Properties Panel with tabbed interface
3. Add Filters menu for applying visualization operations
4. Implement View menu for camera controls
5. Style the UI to match ParaView's professional appearance

**Explicit Exclusions:**
- ML pipeline integration (deferred to future work)
- New ML metric implementation
- ML model training or inference

---

## Current State Analysis

### What We Have

**Technology Stack:**
- **Backend:** Flask + trame framework
- **Frontend:** VTK.wasm (trame-vtklocal) for ribbon visualization
- **UI Framework:** Vue.js + Vuetify (via trame-vuetify)
- **3D Rendering:** VTK pipeline (spline + ribbon filters)

**Current Features in `trame_ribbon_app.py`:**
1. Ribbon visualization using VTK spline and ribbon filters
2. Multiple metrics (hotspot, anomaly, RMSF, tICA)
3. Frame-by-frame animation (194 frames)
4. Click-to-select residues
5. Distance and angle measurements
6. Contact visualization
7. Clipping plane
8. Search functionality
9. Color mapping with lookup tables

**Current UI Layout:**
- Right sidebar: Controls panel with expansion panels
- Center: 3D render view (trame-vtklocal)
- Top: Basic controls and metric selector

### What ParaView Visualizer Offers

**ParaView Visualizer Reference:**
- Repository: https://github.com/Kitware/visualizer
- Technology: ParaView + trame + Vue.js
- Features we want to adopt:

1. **Pipeline Browser (Left Panel)**
   - Shows visualization pipeline as a tree
   - Select pipeline objects to modify properties
   - Visual hierarchy of data sources and filters
   
2. **Properties Panel (Right Panel)**
   - Tabbed interface (Properties, Information, Display)
   - Context-sensitive controls
   - Color map editor
   
3. **Filters Menu (Top Toolbar)**
   - Dropdown with categorized filters
   - Common filters: Clip, Slice, Threshold, Contour
   
4. **View Menu (Top Toolbar)**
   - Camera preset buttons (Front, Top, Side, Isometric)
   - Reset camera
   - Adjust to data

5. **Professional Styling**
   - Dark theme
   - Consistent iconography
   - Logical grouping of controls

---

## Integration Architecture

### UI Layout Plan

```
┌─────────────────────────────────────────────────────────────┐
│  Toolbar: [File] [Edit] [Filters ▼] [View ▼] [Help]        │
├────────────┬────────────────────────────────┬───────────────┤
│  Pipeline  │                                │  Properties   │
│  Browser   │      3D Render View            │  Panel        │
│            │      (trame-vtklocal)          │               │
│  ┌──────┐  │                                │  ┌─────────┐  │
│  │ Data │  │                                │  │Props    │  │
│  ├──────┤  │                                │  ├─────────┤  │
│  │└─Spln│  │                                │  │Info     │  │
│  │└─Rbbn│  │                                │  ├─────────┤  │
│  │└─Clip│  │                                │  │Display  │  │
│  │└─Cntc│  │                                │  └─────────┘  │
│            │                                │               │
│            │                                │  Color Map    │
│            │                                │  Editor       │
└────────────┴────────────────────────────────┴───────────────┘
```

### Component Mapping

| ParaView Component | ASVS Implementation | Status |
|-------------------|---------------------|--------|
| Pipeline Browser | New left sidebar panel | To implement |
| Properties Panel | Enhance right sidebar | To enhance |
| Filters Menu | New toolbar dropdown | To implement |
| View Menu | New toolbar dropdown | To implement |
| Color Map Editor | Existing metric selector | To enhance |
| 3D View | Existing trame-vtklocal | Already working |

---

## Implementation Phases

### Phase 1: Research & Design (Days 1-2)

#### Day 1: ParaView Visualizer Research
**Objective:** Understand ParaView Visualizer architecture

**Tasks:**
1. Browse ParaView Visualizer source code online
   - URL: https://github.com/Kitware/visualizer
   - Focus on: `src/components/`, UI layout files
   
2. Identify UI components
   - Pipeline Browser implementation
   - Properties Panel structure
   - Menu structures
   
3. Document UI patterns
   - Component hierarchy
   - State management approach
   - Vuetify components used
   
4. Take screenshots/notes
   - Panel layouts
   - Color schemes
   - Icon usage
   - Interaction patterns

**Deliverables:**
- `PARAVIEW_UI_ANALYSIS.md` - Detailed analysis of ParaView UI
- Screenshot collection in `docs/paraview_screenshots/`
- Component mapping document

#### Day 2: Integration Design
**Objective:** Plan how to integrate ParaView features into ASVS

**Tasks:**
1. Create architecture diagram
   - Current ASVS architecture
   - ParaView components to integrate
   - Integration points
   
2. Design UI mockups
   - Sketch new layout with all panels
   - Show how existing features fit
   - Plan responsive behavior
   
3. Identify trame-vuetify components needed
   - VList for pipeline browser
   - VTabs for properties panel
   - VMenu for dropdowns
   
4. Plan state management
   - Which state variables needed
   - How components communicate
   - Where to store pipeline state

**Deliverables:**
- Architecture diagram (PNG/SVG)
- UI mockup/wireframe
- Component specification document
- State management plan

---

### Phase 2: Pipeline Browser Implementation (Days 3-4)

#### Day 3: Basic Pipeline Browser
**Objective:** Add left sidebar with pipeline items

**Tasks:**
1. Add left drawer to trame layout
   ```python
   with vuetify.VNavigationDrawer(
       app=True,
       clipped=True,
       v_model=("pipelineBrowserVisible", True),
       width=300
   ):
       # Pipeline browser content
   ```

2. Create pipeline item list
   - Show "Trajectory Data" (root)
   - Show "CA Spline" (filter)
   - Show "Ribbon" (filter)
   - Show "Clipping" (when enabled)
   - Show "Contacts" (when enabled)

3. Implement selection logic
   - Click on item → update selected_pipeline_item state
   - Highlight selected item
   - Update properties panel based on selection

4. Style to match ParaView
   - Dark theme colors
   - Appropriate icons (mdi-database, mdi-filter, etc.)
   - Indentation for hierarchy

**Deliverables:**
- Working pipeline browser panel
- Selection state management
- Basic styling

#### Day 4: Pipeline Interactions
**Objective:** Make pipeline browser interactive and useful

**Tasks:**
1. Add visibility toggles
   - Eye icon for each item
   - Toggle visibility of contacts, clipping
   
2. Add context menu (right-click)
   - Delete filter (if applicable)
   - Rename
   - Duplicate (future)
   
3. Sync with actual pipeline state
   - When clipping enabled → add to pipeline
   - When contacts shown → add to pipeline
   - When disabled → remove from pipeline

4. Add tooltips
   - Hover over item → show description
   - Show filter parameters

**Deliverables:**
- Interactive pipeline browser
- Visibility toggles working
- Pipeline state sync

---

### Phase 3: Properties Panel Enhancement (Days 5-6)

#### Day 5: Tabbed Properties Panel
**Objective:** Add tabbed interface to properties panel

**Tasks:**
1. Restructure right sidebar
   ```python
   with vuetify.VTabs(v_model=("propertiesTab", 0)):
       vuetify.VTab("Properties")
       vuetify.VTab("Information")
       vuetify.VTab("Display")
   ```

2. **Properties Tab**
   - Show controls for selected pipeline item
   - Trajectory Data: frame selector, animation controls
   - Ribbon: width, angle, subdivision length
   - Clipping: plane normal, position sliders
   - Contacts: distance threshold, count

3. **Information Tab**
   - Show statistics for selected item
   - Trajectory: # frames, # residues, # atoms
   - Ribbon: # points, # cells
   - Clipping: plane equation
   - Selected residue: name, number, chain

4. **Display Tab**
   - Ribbon appearance: opacity, specular
   - Color mapping: metric selector, colormap
   - Representation: Surface, Wireframe (if supported)

**Deliverables:**
- Tabbed properties interface
- Context-sensitive content
- All three tabs functional

#### Day 6: Color Map Editor
**Objective:** Enhance color mapping controls

**Tasks:**
1. Add color map preview bar
   - Show gradient visualization
   - Display min/max values
   
2. Add color map selector
   - List available colormaps
   - Preview on hover
   
3. Add scalar range controls
   - Auto-range vs manual
   - Min/max input fields
   
4. Add color bar options
   - Show/hide color bar
   - Position (left, right, top, bottom)
   - Title and labels

**Deliverables:**
- Enhanced color map controls
- Visual color bar preview
- Color map switching

---

### Phase 4: Filters Menu Implementation (Days 7-8)

#### Day 7: Filters Menu Structure
**Objective:** Add filters dropdown to toolbar

**Tasks:**
1. Add toolbar with menus
   ```python
   with vuetify.VToolbar(app=True, clipped_left=True, dark=True):
       vuetify.VToolbarTitle("ASVS - Molecular Visualizer")
       with vuetify.VMenu():
           with vuetify.Template(v_slot_activator="{ on, attrs }"):
               vuetify.VBtn("Filters", v_bind="attrs", v_on="on")
           with vuetify.VList():
               # Filter items
   ```

2. Add filter categories
   - **Common Filters**
     - Clip
     - Threshold (by metric)
   - **Molecular Filters**
     - Show Contacts
     - Show RMSF
   - **Selection Filters**
     - Extract Residue Range
     - Extract Chain

3. Implement filter actions
   - Click "Clip" → enable clipping, add to pipeline
   - Click "Threshold" → open threshold dialog
   - Click "Show Contacts" → toggle contacts, update pipeline

**Deliverables:**
- Working Filters menu
- Filter application logic
- Pipeline updates on filter add/remove

#### Day 8: Filter Dialogs
**Objective:** Add dialogs for filter configuration

**Tasks:**
1. Threshold filter dialog
   - Metric selector
   - Value range slider
   - Preview option
   - Apply/Cancel buttons
   
2. Extract Residue Range dialog
   - Start residue input
   - End residue input
   - Apply/Cancel
   
3. Wire up filter application
   - Store filter parameters
   - Update visualization
   - Add to pipeline browser

**Deliverables:**
- Filter configuration dialogs
- Filter application working
- Visual feedback

---

### Phase 5: View Menu Implementation (Day 9)

#### Day 9: Camera Controls
**Objective:** Add view menu for camera presets

**Tasks:**
1. Add View menu to toolbar
   ```python
   with vuetify.VMenu():
       with vuetify.Template(v_slot_activator="{ on, attrs }"):
           vuetify.VBtn("View", v_bind="attrs", v_on="on")
       with vuetify.VList():
           # View items
   ```

2. Add camera preset buttons
   - **+X (Right View)**: Camera looks along +X axis
   - **-X (Left View)**: Camera looks along -X axis
   - **+Y (Front View)**: Camera looks along +Y axis
   - **-Y (Back View)**: Camera looks along -Y axis
   - **+Z (Top View)**: Camera looks along +Z axis
   - **-Z (Bottom View)**: Camera looks along -Z axis
   - **Isometric**: Standard isometric view
   - **Reset Camera**: Fit all data in view

3. Implement camera positioning
   ```python
   def set_camera_view(direction):
       camera = renderer.GetActiveCamera()
       bounds = actor.GetBounds()
       center = [...]
       
       if direction == '+Z':
           camera.SetPosition(center[0], center[1], center[2] + distance)
           camera.SetViewUp(0, 1, 0)
       # ... other directions
       
       camera.SetFocalPoint(center)
       ctrl.view_update()
   ```

4. Add view options
   - Toggle parallel/perspective projection
   - Show/hide orientation axes
   - Show/hide cube axes

**Deliverables:**
- Working View menu
- All camera presets functional
- View options working

---

### Phase 6: Styling & Polish (Day 10)

#### Day 10: UI Refinement
**Objective:** Match ParaView visual style and polish interactions

**Tasks:**
1. Apply ParaView color scheme
   - Dark background: `#1e1e1e`
   - Panel background: `#252526`
   - Borders: `#3e3e42`
   - Text: `#cccccc`
   - Accent: `#007acc`

2. Add consistent icons
   - Material Design Icons (mdi-*)
   - Pipeline items: database, filter, etc.
   - Buttons: play, pause, stop, etc.

3. Improve layout spacing
   - Consistent padding/margins
   - Proper dividers between sections
   - Collapsible panels

4. Add loading indicators
   - Show spinner during frame load
   - Progress bar for animations

5. Responsive design
   - Test on different screen sizes
   - Make panels collapsible on small screens
   - Ensure minimum usable width

**Deliverables:**
- Polished UI matching ParaView style
- Responsive behavior
- Professional appearance

---

### Phase 7: Testing & Documentation (Days 11-12)

#### Day 11: Comprehensive Testing
**Objective:** Test all features end-to-end

**Tasks:**
1. **Functional Testing**
   - Load ribbon viewer
   - Test each pipeline item selection
   - Test each filter application
   - Test each camera preset
   - Test all property panel tabs
   - Test color map changes

2. **Integration Testing**
   - Verify pipeline browser updates on filter add/remove
   - Verify properties panel shows correct content for selection
   - Verify all metrics still work
   - Verify frame animation still works
   - Verify measurements still work

3. **UI/UX Testing**
   - Test on Chrome, Firefox, Safari
   - Test on different screen sizes
   - Verify tooltips appear
   - Verify all buttons work
   - Check for console errors

4. **Performance Testing**
   - Test with all 194 frames
   - Measure frame rate during animation
   - Check memory usage
   - Verify no memory leaks

**Deliverables:**
- Test results document
- Bug list (if any)
- Performance metrics

#### Day 12: Documentation
**Objective:** Document new features and usage

**Tasks:**
1. Create `PARAVIEW_INTEGRATION.md`
   - Overview of integration
   - List of new features
   - How to use each feature
   - Screenshots of each panel

2. Update `README.md`
   - Add ParaView integration section
   - Update feature list
   - Update screenshots

3. Create architecture diagram
   - Show component relationships
   - Show data flow
   - Export as PNG/SVG

4. Record demo video (optional)
   - Show new UI in action
   - Demonstrate all new features
   - 3-5 minutes length

**Deliverables:**
- PARAVIEW_INTEGRATION.md
- Updated README.md
- Architecture diagram
- Optional demo video

---

## Technical Specifications

### trame-vuetify Components to Use

| Component | Purpose |
|-----------|---------|
| VNavigationDrawer | Pipeline browser (left), Properties panel (right) |
| VList, VListItem | Pipeline items, menu items |
| VTabs, VTabItem | Properties panel tabs |
| VMenu | Filters and View dropdowns |
| VToolbar | Top toolbar |
| VExpansionPanel | Collapsible sections |
| VSlider | Value controls (clipping position, etc.) |
| VTextField | Text inputs (residue range, etc.) |
| VBtn | All buttons |
| VIcon | All icons |
| VDialog | Filter configuration dialogs |

### State Variables to Add

```python
state = {
    # Pipeline browser
    "pipelineBrowserVisible": True,
    "selectedPipelineItem": "ribbon",
    "pipelineItems": [...],
    
    # Properties panel
    "propertiesTab": 0,  # 0=Properties, 1=Information, 2=Display
    
    # Filters
    "filtersMenuOpen": False,
    
    # View
    "viewMenuOpen": False,
    "currentView": "isometric",
}
```

### VTK Pipeline State to Track

```python
pipeline_items = [
    {
        "id": "trajectory",
        "name": "Trajectory Data",
        "type": "source",
        "visible": True,
        "icon": "mdi-database"
    },
    {
        "id": "spline",
        "name": "CA Spline",
        "type": "filter",
        "visible": True,
        "icon": "mdi-chart-bell-curve"
    },
    {
        "id": "ribbon",
        "name": "Ribbon",
        "type": "filter",
        "visible": True,
        "icon": "mdi-ribbon"
    },
    # ... more items added dynamically
]
```

---

## Success Criteria

The integration is successful when:

1. ✅ Pipeline Browser shows all active pipeline items
2. ✅ Selecting pipeline item updates Properties Panel
3. ✅ Properties Panel has three functional tabs
4. ✅ Filters menu allows adding filters to pipeline
5. ✅ View menu provides camera presets
6. ✅ UI matches ParaView visual style
7. ✅ All existing features still work (metrics, measurements, etc.)
8. ✅ Documentation is complete and clear
9. ✅ No regressions in performance or stability

---

## Timeline Summary

| Days | Phase | Key Deliverable |
|------|-------|-----------------|
| 1-2 | Research & Design | UI analysis, architecture diagram, mockups |
| 3-4 | Pipeline Browser | Working pipeline browser with selection |
| 5-6 | Properties Panel | Tabbed properties with color map editor |
| 7-8 | Filters Menu | Filters menu with dialogs |
| 9 | View Menu | Camera presets and view controls |
| 10 | Styling & Polish | ParaView-style UI, responsive design |
| 11-12 | Testing & Docs | Complete testing, documentation |

**Total: 12 days (~2 weeks)**

---

## Quick Start (Minimum Viable Integration)

If time is limited, implement these essential features first:

### Week 1: Core Features
1. **Day 1-2**: Pipeline Browser with basic item list
2. **Day 3-4**: Properties Panel with Properties tab only
3. **Day 4-5**: Filters menu with Clip and Contacts

### Week 2: Polish
1. **Day 6**: View menu with camera presets
2. **Day 7**: Basic ParaView styling
3. **Day 8**: Testing and bug fixes
4. **Day 9**: Documentation

This gives a working ParaView-style integration in 9 days.

---

## Risk Mitigation

### Potential Risks

1. **Complexity of VTK Pipeline Tracking**
   - Mitigation: Start simple, track only major pipeline objects
   
2. **State Management Complexity**
   - Mitigation: Use trame's reactive state, avoid manual DOM manipulation
   
3. **Performance Issues with More UI**
   - Mitigation: Profile early, optimize as needed, lazy load panels
   
4. **Browser Compatibility**
   - Mitigation: Test on major browsers early, use standard Vuetify components

---

## Resources

### ParaView Resources
- ParaView Visualizer GitHub: https://github.com/Kitware/visualizer
- ParaView Documentation: https://docs.paraview.org/
- trame Documentation: https://kitware.github.io/trame/

### trame Resources
- trame-vuetify Components: https://kitware.github.io/trame/docs/widgets.html#vuetify
- trame Examples: https://kitware.github.io/trame/examples/
- Material Design Icons: https://materialdesignicons.com/

### Current ASVS Codebase
- Main app: `trame_ribbon_app.py`
- Architecture: `ARCHITECTURE.md`
- Current features: `CURRENT_FEATURES.md`

---

## Next Steps

1. Review this plan with stakeholders
2. Create GitHub issues for each phase
3. Set up milestone: "ParaView Integration"
4. Begin Phase 1: Research & Design

**Ready to start? Let's begin with Day 1: ParaView Visualizer Research!** 🚀
