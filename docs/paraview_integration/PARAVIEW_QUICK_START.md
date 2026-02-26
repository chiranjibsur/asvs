# ParaView Visualizer Integration - Quick Start Guide

**Goal:** Add ParaView-style UI to ASVS trame ribbon viewer  
**Time:** 9-12 days  
**Focus:** UI enhancement, NO ML integration

---

## What You're Building

Transform your current ribbon viewer into a ParaView-style interface with:

1. **Pipeline Browser** (left panel) - Shows visualization pipeline
2. **Properties Panel** (right panel) - Tabbed controls for selected items
3. **Filters Menu** (toolbar) - Add/remove visualization filters
4. **View Menu** (toolbar) - Camera presets and controls

---

## Day-by-Day Tasks

### Day 1: Research ParaView UI

**Browse Online (No Installation Required):**
1. Visit: https://github.com/Kitware/visualizer
2. Look at screenshots in README
3. Browse `src/components/` folder
4. Identify UI patterns

**Take Notes On:**
- How Pipeline Browser looks (left panel)
- What's in Properties Panel (right panel)
- What filters are available
- Color scheme and styling

**Deliverable:** Create `PARAVIEW_UI_NOTES.md` with screenshots/observations

---

### Day 2-3: Add Pipeline Browser

**Goal:** Add left sidebar showing pipeline items

**Code to Add:**

```python
# In trame_ribbon_app.py, in the UI section

with layout:
    # Add left drawer for pipeline browser
    with vuetify.VNavigationDrawer(
        app=True,
        clipped=True,
        v_model=("pipelineBrowserVisible", True),
        width=280,
        style="background: #252526;"
    ):
        vuetify.VToolbarTitle("Pipeline Browser", 
            style="color: #cccccc; padding: 16px;")
        
        with vuetify.VList(dense=True, dark=True):
            # Trajectory data source
            with vuetify.VListItem(
                click=(ctrl.select_pipeline_item, ["trajectory"])
            ):
                with vuetify.VListItemIcon():
                    vuetify.VIcon("mdi-database")
                with vuetify.VListItemContent():
                    vuetify.VListItemTitle("Trajectory Data")
            
            # Spline filter
            with vuetify.VListItem(
                click=(ctrl.select_pipeline_item, ["spline"]),
                style="padding-left: 32px;"
            ):
                with vuetify.VListItemIcon():
                    vuetify.VIcon("mdi-chart-bell-curve")
                with vuetify.VListItemContent():
                    vuetify.VListItemTitle("CA Spline")
            
            # Ribbon filter
            with vuetify.VListItem(
                click=(ctrl.select_pipeline_item, ["ribbon"]),
                style="padding-left: 32px;"
            ):
                with vuetify.VListItemIcon():
                    vuetify.VIcon("mdi-ribbon")
                with vuetify.VListItemContent():
                    vuetify.VListItemTitle("Ribbon")
            
            # Clipping (if enabled)
            with vuetify.VListItem(
                v_show="clipping_enabled",
                click=(ctrl.select_pipeline_item, ["clip"]),
                style="padding-left: 32px;"
            ):
                with vuetify.VListItemIcon():
                    vuetify.VIcon("mdi-content-cut")
                with vuetify.VListItemContent():
                    vuetify.VListItemTitle("Clipping Plane")
```

**Add Controller Method:**

```python
def select_pipeline_item(item_id):
    """Handle pipeline item selection."""
    state.selectedPipelineItem = item_id
    # Update properties panel based on selection
```

**Test:**
- Run app, see left panel
- Click items, verify selection works

---

### Day 4-5: Enhance Properties Panel

**Goal:** Add tabs to right panel

**Code to Add:**

```python
# In trame_ribbon_app.py, replace right sidebar with:

with vuetify.VNavigationDrawer(
    app=True,
    clipped=True,
    right=True,
    v_model=("propertiesPanelVisible", True),
    width=320,
    style="background: #252526;"
):
    # Add tabs
    with vuetify.VTabs(v_model=("propertiesTab", 0), dark=True):
        vuetify.VTab("Properties")
        vuetify.VTab("Information")
        vuetify.VTab("Display")
    
    with vuetify.VTabsItems(v_model="propertiesTab"):
        # Tab 1: Properties
        with vuetify.VTabItem():
            # Existing controls go here
            # Frame slider, metric selector, etc.
            pass
        
        # Tab 2: Information
        with vuetify.VTabItem():
            html.Div("Trajectory Information", style="padding: 16px; color: #cccccc;")
            html.Div(f"Frames: {{{{ meta.n_frames }}}}")
            html.Div(f"Residues: {{{{ meta.n_residues }}}}")
            html.Div(f"Atoms: {{{{ meta.n_atoms }}}}")
        
        # Tab 3: Display
        with vuetify.VTabItem():
            html.Div("Display Options", style="padding: 16px; color: #cccccc;")
            # Color map controls
            vuetify.VSelect(
                label="Color Map",
                v_model=("current_colormap", "red_white_blue"),
                items=("availableColormaps", ["red_white_blue", "viridis", "plasma"])
            )
```

**Test:**
- Verify all 3 tabs appear
- Switch between tabs
- Check content displays correctly

---

### Day 6-7: Add Filters Menu

**Goal:** Add toolbar with Filters dropdown

**Code to Add:**

```python
# Add at top of layout

with layout:
    # Toolbar
    with vuetify.VToolbar(
        app=True,
        clipped_left=True,
        dark=True,
        style="background: #1e1e1e;"
    ):
        vuetify.VToolbarTitle("ASVS - Molecular Visualizer")
        vuetify.VSpacer()
        
        # Filters menu
        with vuetify.VMenu(offset_y=True):
            with vuetify.Template(v_slot_activator="{ on, attrs }"):
                vuetify.VBtn(
                    "Filters",
                    v_bind="attrs",
                    v_on="on",
                    text=True
                )
            with vuetify.VList():
                vuetify.VSubheader("Common Filters")
                vuetify.VListItem(
                    "Clip",
                    click=(ctrl.toggle_clipping, [])
                )
                vuetify.VListItem(
                    "Show Contacts",
                    click=(ctrl.toggle_contacts, [])
                )
                vuetify.VSubheader("Molecular Filters")
                vuetify.VListItem(
                    "Show RMSF",
                    click=(ctrl.set_metric, ["rmsf"])
                )
```

**Test:**
- Click "Filters" button
- Verify menu appears
- Click menu items
- Verify actions work

---

### Day 8: Add View Menu

**Goal:** Add camera presets

**Code to Add:**

```python
# In toolbar, after Filters menu:

with vuetify.VMenu(offset_y=True):
    with vuetify.Template(v_slot_activator="{ on, attrs }"):
        vuetify.VBtn(
            "View",
            v_bind="attrs",
            v_on="on",
            text=True
        )
    with vuetify.VList():
        vuetify.VListItem(
            "+Z (Top View)",
            click=(ctrl.set_camera_view, ["+Z"])
        )
        vuetify.VListItem(
            "+Y (Front View)",
            click=(ctrl.set_camera_view, ["+Y"])
        )
        vuetify.VListItem(
            "+X (Side View)",
            click=(ctrl.set_camera_view, ["+X"])
        )
        vuetify.VDivider()
        vuetify.VListItem(
            "Reset Camera",
            click=(ctrl.reset_camera, [])
        )
```

**Add Controller Methods:**

```python
def set_camera_view(direction):
    """Set camera to standard view."""
    camera = renderer.GetActiveCamera()
    
    # Get bounds for positioning
    bounds = actor.GetBounds()
    center = [
        (bounds[0] + bounds[1]) / 2,
        (bounds[2] + bounds[3]) / 2,
        (bounds[4] + bounds[5]) / 2
    ]
    
    # Calculate distance
    max_dim = max(
        bounds[1] - bounds[0],
        bounds[3] - bounds[2],
        bounds[5] - bounds[4]
    )
    distance = max_dim * 2
    
    # Set position based on direction
    if direction == "+Z":
        camera.SetPosition(center[0], center[1], center[2] + distance)
        camera.SetViewUp(0, 1, 0)
    elif direction == "+Y":
        camera.SetPosition(center[0], center[1] + distance, center[2])
        camera.SetViewUp(0, 0, 1)
    elif direction == "+X":
        camera.SetPosition(center[0] + distance, center[1], center[2])
        camera.SetViewUp(0, 0, 1)
    
    camera.SetFocalPoint(center)
    ctrl.view_update()

def reset_camera():
    """Reset camera to fit all data."""
    renderer.ResetCamera()
    ctrl.view_update()
```

**Test:**
- Click each camera preset
- Verify view changes correctly
- Test Reset Camera

---

### Day 9: Apply ParaView Styling

**Goal:** Match ParaView color scheme

**CSS/Styling:**

```python
# Add to layout or use style parameter on components

PARAVIEW_COLORS = {
    "background": "#1e1e1e",
    "panel": "#252526",
    "border": "#3e3e42",
    "text": "#cccccc",
    "accent": "#007acc"
}

# Apply to components:
# style=f"background: {PARAVIEW_COLORS['panel']}; color: {PARAVIEW_COLORS['text']};"
```

**Update Icons:**
- Use Material Design Icons (mdi-*)
- Consistent icon usage throughout

**Test:**
- Check visual consistency
- Verify dark theme throughout

---

### Day 10-11: Testing

**Test Checklist:**

- [ ] Pipeline Browser shows all items
- [ ] Clicking pipeline item updates properties
- [ ] All 3 property tabs work
- [ ] Filters menu applies filters correctly
- [ ] View menu changes camera correctly
- [ ] Existing features still work:
  - [ ] Frame animation
  - [ ] Metric switching
  - [ ] Measurements
  - [ ] Contacts
  - [ ] Clipping
- [ ] No console errors
- [ ] Works in Chrome, Firefox, Safari
- [ ] Responsive on different screen sizes

---

### Day 12: Documentation

**Create Documentation:**

1. **PARAVIEW_INTEGRATION.md**
   - What was added
   - How to use new features
   - Screenshots

2. **Update README.md**
   - Add ParaView integration section
   - Update feature list
   - Update screenshots

3. **Architecture Diagram**
   - Show new UI layout
   - Show component relationships

---

## Code Structure

Your `trame_ribbon_app.py` should have this structure:

```python
# Imports
import vtk
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vuetify, html
from trame_vtklocal.widgets import vtklocal

# Constants and data loading
PARAVIEW_COLORS = {...}
adapter = get_adapter()

# VTK pipeline setup
points = vtk.vtkPoints()
# ... existing VTK code ...

# State initialization
server = get_server()
state, ctrl = server.state, server.controller

state.update({
    "pipelineBrowserVisible": True,
    "selectedPipelineItem": "ribbon",
    "propertiesTab": 0,
    "propertiesPanelVisible": True,
})

# Controller methods
@ctrl.add("select_pipeline_item")
def select_pipeline_item(item_id):
    state.selectedPipelineItem = item_id

@ctrl.add("set_camera_view")
def set_camera_view(direction):
    # ... camera code ...

# UI Layout
with SinglePageLayout(server) as layout:
    # Toolbar
    with vuetify.VToolbar(...):
        # Filters, View menus
    
    # Left drawer - Pipeline Browser
    with vuetify.VNavigationDrawer(...):
        # Pipeline items
    
    # Center - 3D View
    with vuetify.VContainer(fluid=True):
        view = vtklocal.LocalView(render_window)
    
    # Right drawer - Properties Panel
    with vuetify.VNavigationDrawer(right=True, ...):
        # Tabbed properties

# Start server
if __name__ == "__main__":
    server.start()
```

---

## Tips & Tricks

1. **Use State for Everything**
   - Don't manipulate DOM directly
   - Let trame's reactive state handle updates

2. **Test Incrementally**
   - Add one panel at a time
   - Test before moving to next

3. **Copy Existing Patterns**
   - Look at existing code in `trame_ribbon_app.py`
   - Use same controller patterns

4. **Use Vuetify Documentation**
   - https://vuetifyjs.com/
   - Check component APIs

5. **Debug with Browser Console**
   - F12 to open dev tools
   - Check for Vue errors
   - Use `console.log()` liberally

---

## Common Issues

### Panel Not Showing
- Check `v_model` is set correctly
- Verify `app=True` on drawers
- Check `clipped=True` if using toolbar

### Buttons Not Working
- Verify controller method is registered with `@ctrl.add()`
- Check method name matches click handler
- Look for errors in terminal

### Styling Not Applied
- Use `style` parameter on components
- Check CSS specificity
- Use browser inspector to debug

### State Not Updating
- Ensure state variable defined in `state.update()`
- Use correct state variable name
- Check for typos

---

## Success Metrics

You're done when:

✅ All panels visible and functional  
✅ Pipeline browser updates on changes  
✅ Properties panel shows correct content  
✅ Filters menu applies filters  
✅ View menu changes camera  
✅ UI looks professional (ParaView-style)  
✅ All existing features still work  
✅ Documentation complete  

---

## Resources

- **trame docs:** https://kitware.github.io/trame/
- **Vuetify components:** https://vuetifyjs.com/en/components/
- **Material icons:** https://materialdesignicons.com/
- **ParaView Visualizer:** https://github.com/Kitware/visualizer

---

**Good luck! Start with Day 1 and work through step by step.** 🚀
