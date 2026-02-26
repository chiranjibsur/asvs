# ParaView Integration Architecture

This document describes the architectural changes for integrating ParaView Visualizer features into ASVS.

---

## Current Architecture (Before Integration)

```
┌──────────────────────────────────────────────────────────┐
│                   ASVS Ribbon Viewer                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────┬──────────────────────┐  │
│  │                            │   Right Sidebar      │  │
│  │                            │                      │  │
│  │     3D Render View         │   ┌──────────────┐   │  │
│  │   (trame-vtklocal)         │   │ Frame Ctrl   │   │  │
│  │                            │   ├──────────────┤   │  │
│  │   VTK Pipeline:            │   │ Metrics      │   │  │
│  │   - Points → Spline        │   ├──────────────┤   │  │
│  │   - Spline → Ribbon        │   │ Measurements │   │  │
│  │   - Color Mapping          │   ├──────────────┤   │  │
│  │                            │   │ Clipping     │   │  │
│  │                            │   ├──────────────┤   │  │
│  │                            │   │ Contacts     │   │  │
│  │                            │   └──────────────┘   │  │
│  └────────────────────────────┴──────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘

Technology Stack:
- Backend: Flask + trame
- Frontend: trame-vtklocal (VTK.wasm)
- UI: trame-vuetify (Vue.js + Vuetify)
- 3D: VTK pipeline (server-side Python)
```

---

## Target Architecture (After Integration)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    ASVS with ParaView Integration                        │
├──────────────────────────────────────────────────────────────────────────┤
│  Top Toolbar                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ ASVS      [Filters ▼] [View ▼] [Help]                             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────┬───────────────────────────────┬──────────────────┐    │
│  │   Pipeline   │                               │   Properties     │    │
│  │   Browser    │      3D Render View           │   Panel          │    │
│  │              │    (trame-vtklocal)           │                  │    │
│  │ ┌──────────┐ │                               │ ┌──────────────┐ │    │
│  │ │●Trajectory│←─────────────────────────────→ │ │ Props  Info  │ │    │
│  │ ├──────────┤ │                               │ │   Display    │ │    │
│  │ │ └─Spline │ │   VTK Pipeline:               │ ├──────────────┤ │    │
│  │ ├──────────┤ │   - Points → Spline           │ │              │ │    │
│  │ │ └─Ribbon │ │   - Spline → Ribbon           │ │ [Controls]   │ │    │
│  │ ├──────────┤ │   - Color Mapping             │ │              │ │    │
│  │ │ └─Clip   │ │                               │ │ Color Map:   │ │    │
│  │ ├──────────┤ │                               │ │ ┌──────────┐ │ │    │
│  │ │ └─Contact│ │                               │ │ │■■■■■■■■■■│ │ │    │
│  │ └──────────┘ │                               │ │ └──────────┘ │ │    │
│  │              │                               │ │              │ │    │
│  └──────────────┴───────────────────────────────┴──────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

New Features:
✓ Pipeline Browser (left panel)
✓ Properties Panel with tabs (right panel)  
✓ Filters menu (toolbar)
✓ View menu (toolbar)
✓ ParaView-style dark theme
```

---

## Component Breakdown

### 1. Pipeline Browser (New Component)

**Location:** Left VNavigationDrawer  
**Purpose:** Show visualization pipeline hierarchy  
**Features:**
- Tree view of pipeline objects
- Click to select and edit properties
- Show/hide individual items
- Visual hierarchy (indentation)

**State Variables:**
```python
state = {
    "pipelineBrowserVisible": True,      # Show/hide left panel
    "selectedPipelineItem": "ribbon",    # Currently selected item
    "pipelineItems": [...]               # List of pipeline objects
}
```

**Pipeline Items Structure:**
```python
pipelineItems = [
    {
        "id": "trajectory",
        "name": "Trajectory Data",
        "type": "source",
        "visible": True,
        "icon": "mdi-database",
        "parent": None
    },
    {
        "id": "spline",
        "name": "CA Spline",
        "type": "filter",
        "visible": True,
        "icon": "mdi-chart-bell-curve",
        "parent": "trajectory"
    },
    # ... more items
]
```

---

### 2. Properties Panel (Enhanced Component)

**Location:** Right VNavigationDrawer  
**Purpose:** Edit properties of selected pipeline item  
**Features:**
- Tabbed interface (Properties, Information, Display)
- Context-sensitive controls
- Color map editor

**Tab Structure:**

#### Properties Tab
Shows editable parameters for selected item:
- Trajectory: frame controls, animation
- Spline: subdivision length
- Ribbon: width, angle
- Clipping: plane normal, position
- Contacts: threshold, visibility

#### Information Tab
Shows read-only statistics:
- Trajectory: # frames, # atoms, # residues
- Ribbon: # points, # cells, bounds
- Selected residue: name, number, chain, metrics

#### Display Tab
Shows rendering options:
- Color mapping: metric selector, colormap
- Appearance: opacity, specular
- Color bar: show/hide, position

**State Variables:**
```python
state = {
    "propertiesPanelVisible": True,  # Show/hide right panel
    "propertiesTab": 0,              # Active tab (0, 1, or 2)
}
```

---

### 3. Filters Menu (New Component)

**Location:** VToolbar (top)  
**Purpose:** Add filters to visualization pipeline  
**Features:**
- Dropdown menu with filter list
- Categorized filters
- Adds items to pipeline browser when applied

**Filter Categories:**
1. **Common Filters**
   - Clip
   - Threshold (by metric)

2. **Molecular Filters**
   - Show Contacts
   - Show RMSF

3. **Selection Filters** (future)
   - Extract Residue Range
   - Extract Chain

**Action Flow:**
```
User clicks "Clip" 
  → ctrl.toggle_clipping() called
  → state.clipping_enabled = True
  → Pipeline item added to pipelineItems
  → UI updates to show clip plane controls
```

---

### 4. View Menu (New Component)

**Location:** VToolbar (top)  
**Purpose:** Control camera and view settings  
**Features:**
- Camera preset buttons
- View mode toggles
- Orientation controls

**View Options:**
- +X, -X, +Y, -Y, +Z, -Z (orthogonal views)
- Isometric
- Reset Camera
- Toggle parallel/perspective

**Camera Preset Implementation:**
```python
def set_camera_view(direction):
    camera = renderer.GetActiveCamera()
    bounds = actor.GetBounds()
    center = calculate_center(bounds)
    distance = calculate_distance(bounds)
    
    positions = {
        "+Z": (center[0], center[1], center[2] + distance),
        "+Y": (center[0], center[1] + distance, center[2]),
        "+X": (center[0] + distance, center[1], center[2])
    }
    
    camera.SetPosition(positions[direction])
    camera.SetFocalPoint(center)
    camera.SetViewUp(...)
    ctrl.view_update()
```

---

## Data Flow

### Selecting Pipeline Item

```
User clicks pipeline item
  ↓
Pipeline Browser: VListItem click event
  ↓
Controller: select_pipeline_item(item_id)
  ↓
State: selectedPipelineItem = item_id
  ↓
Properties Panel: Watches selectedPipelineItem
  ↓
Properties Panel: Updates content based on selection
  ↓
UI: Renders appropriate controls
```

### Adding Filter

```
User clicks "Clip" in Filters menu
  ↓
Controller: toggle_clipping()
  ↓
State: clipping_enabled = True
  ↓
Pipeline: Add clip plane to VTK pipeline
  ↓
State: pipelineItems.append({id: "clip", ...})
  ↓
Pipeline Browser: Shows "Clipping Plane" item
  ↓
Properties Panel: Shows clipping controls
  ↓
Render: Updates 3D view
```

### Changing Camera View

```
User clicks "+Z (Top View)" in View menu
  ↓
Controller: set_camera_view("+Z")
  ↓
VTK: camera.SetPosition(...)
  ↓
VTK: camera.SetFocalPoint(...)
  ↓
Controller: ctrl.view_update()
  ↓
Render: Updates 3D view with new camera
```

---

## State Management

### Complete State Schema

```python
state = {
    # Pipeline browser
    "pipelineBrowserVisible": True,
    "selectedPipelineItem": "ribbon",
    "pipelineItems": [...],
    
    # Properties panel
    "propertiesPanelVisible": True,
    "propertiesTab": 0,  # 0=Properties, 1=Info, 2=Display
    
    # Menus
    "filtersMenuOpen": False,
    "viewMenuOpen": False,
    
    # VTK pipeline state
    "clipping_enabled": False,
    "contacts_visible": False,
    
    # Existing state
    "current_frame": 0,
    "current_metric": "hotspot",
    "is_playing": False,
    # ... all existing state variables
}
```

### Reactive Bindings

- `v_model="pipelineBrowserVisible"` - Controls drawer visibility
- `v_show="clipping_enabled"` - Show/hide clip item in pipeline
- `v_model="propertiesTab"` - Active tab in properties panel
- Watchers monitor state changes and update UI

---

## File Structure

```
trame_ribbon_app.py
├── Imports
├── Constants (PARAVIEW_COLORS, etc.)
├── Data loading (adapter, metrics)
├── VTK pipeline setup
│   ├── Points, polydata, lines
│   ├── Spline filter
│   ├── Ribbon filter
│   ├── Mapper and actor
│   └── Renderer and render window
├── State initialization
├── Controller methods
│   ├── Existing methods
│   ├── NEW: select_pipeline_item()
│   ├── NEW: set_camera_view()
│   └── NEW: reset_camera()
└── UI Layout
    ├── Toolbar (NEW)
    │   ├── Filters menu
    │   └── View menu
    ├── Pipeline Browser (NEW)
    ├── Center: 3D View (existing)
    └── Properties Panel (enhanced)
        ├── Properties tab
        ├── Information tab
        └── Display tab
```

---

## Technology Stack (No Changes)

**Backend:**
- Flask 2.0.1+
- trame 3.0.0+
- VTK 9.2.0+

**Frontend:**
- trame-vtklocal 0.6.0+ (VTK.wasm)
- trame-vuetify 2.3.0+ (UI components)
- Vue.js 2.x (via trame)
- Vuetify 2.x (via trame-vuetify)

**3D Rendering:**
- VTK pipeline (Python)
- VTK.wasm (WebAssembly in browser)

**No new dependencies required!** All components already available in trame ecosystem.

---

## Integration Points

### Existing Code to Keep

✓ All VTK pipeline setup  
✓ All metric calculations  
✓ All measurement tools  
✓ Animation loop  
✓ Picking logic  
✓ Contact visualization  

### Existing Code to Enhance

△ UI layout - Add toolbar, restructure panels  
△ State variables - Add new state for panels  
△ Controller - Add new methods for UI actions  

### New Code to Add

+ Pipeline browser component  
+ Tabbed properties panel  
+ Filters menu  
+ View menu  
+ Camera preset methods  
+ ParaView styling  

---

## Performance Considerations

**No Performance Impact Expected:**
- New UI components are lightweight Vuetify elements
- No changes to VTK pipeline (already optimized)
- No additional data loading
- State updates are reactive and efficient

**If Performance Issues Arise:**
- Lazy load panels (defer rendering until opened)
- Virtualize pipeline browser for many items
- Debounce camera updates
- Cache computed properties

---

## Browser Compatibility

**Target Browsers:**
- Chrome 90+ ✓
- Firefox 89+ ✓
- Safari 14+ ✓
- Edge 90+ ✓

**Requirements:**
- WebAssembly support (for VTK.wasm)
- Modern JavaScript (ES6+)
- CSS Grid and Flexbox

All supported browsers already meet these requirements for existing trame app.

---

## Testing Strategy

### Unit Testing
- Test controller methods in isolation
- Test state updates
- Test pipeline item add/remove

### Integration Testing
- Test pipeline browser → properties panel interaction
- Test filters menu → pipeline update
- Test view menu → camera changes
- Test all existing features still work

### UI Testing
- Manual testing on target browsers
- Test responsive behavior
- Test accessibility (keyboard navigation)
- Visual regression testing (screenshots)

### Performance Testing
- Measure frame rate during animation
- Monitor memory usage
- Profile state updates
- Test with maximum pipeline items

---

## Rollback Plan

If integration causes issues:

1. **Keep Original Code:** Save current `trame_ribbon_app.py` as `trame_ribbon_app_original.py`
2. **Feature Flags:** Add state variable to enable/disable ParaView UI
3. **Git Branch:** Work on separate branch, merge only when stable
4. **Incremental Rollback:** Can disable individual panels if needed

---

## Success Metrics

**Functional:**
- ✓ All new UI components render correctly
- ✓ All interactions work as expected
- ✓ All existing features still functional
- ✓ No console errors
- ✓ No visual glitches

**Performance:**
- ✓ Frame rate ≥30 FPS during animation
- ✓ UI responsive (<100ms for interactions)
- ✓ No memory leaks

**Quality:**
- ✓ Code follows existing patterns
- ✓ Documentation complete
- ✓ Professional appearance

---

## Future Enhancements (Post-Integration)

**Phase 2 Features:**
- More filter types (Threshold, Slice, Contour)
- Filter parameters dialog
- Pipeline item drag-and-drop reordering
- Export pipeline configuration
- Save/load camera bookmarks

**Phase 3 Features:**
- Multiple 3D views (split screen)
- Animation timeline editor
- Advanced color map editing
- Lighting controls
- Background options

---

**This architecture provides a clear path to ParaView-style UI while maintaining all existing functionality and performance.**
