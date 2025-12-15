# ParaView Integration - Visual Guide

This document provides ASCII diagrams and visual descriptions of the ParaView integration.

---

## Current UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                    ASVS Ribbon Viewer                           │
│                 (Current Implementation)                        │
└─────────────────────────────────────────────────────────────────┘

┌───────────────────────────────┬───────────────────────────────┐
│                               │   RIGHT SIDEBAR               │
│                               │   (Expansion Panels)          │
│                               │                               │
│    3D RENDER VIEW             │  ┌─────────────────────────┐  │
│   (trame-vtklocal)            │  │ ▼ Frame Controls        │  │
│                               │  │   - Play/Pause          │  │
│   - Ribbon visualization      │  │   - Frame Slider        │  │
│   - Color mapping             │  └─────────────────────────┘  │
│   - Mouse rotation            │                               │
│   - Click to select           │  ┌─────────────────────────┐  │
│                               │  │ ▼ Metrics               │  │
│                               │  │   - Hotspot             │  │
│                               │  │   - Anomaly             │  │
│                               │  │   - RMSF                │  │
│                               │  │   - tICA                │  │
│                               │  └─────────────────────────┘  │
│                               │                               │
│                               │  ┌─────────────────────────┐  │
│                               │  │ ▼ Measurements          │  │
│                               │  │   - Distance            │  │
│                               │  │   - Angle               │  │
│                               │  └─────────────────────────┘  │
│                               │                               │
│                               │  ┌─────────────────────────┐  │
│                               │  │ ▼ Clipping              │  │
│                               │  │   - Enable toggle       │  │
│                               │  │   - Position slider     │  │
│                               │  └─────────────────────────┘  │
│                               │                               │
│                               │  ┌─────────────────────────┐  │
│                               │  │ ▼ Contacts              │  │
│                               │  │   - Show toggle         │  │
│                               │  └─────────────────────────┘  │
└───────────────────────────────┴───────────────────────────────┘

Issues:
- No visual pipeline representation
- Controls scattered in expansion panels
- No quick filter access
- Manual camera positioning only
- Single-column layout limits organization
```

---

## Target UI Layout (After ParaView Integration)

```
┌────────────────────────────────────────────────────────────────────────┐
│  TOOLBAR                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ [ASVS]  [Filters ▼]  [View ▼]  [Help]                      [?]  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘

┌──────────────┬──────────────────────────────────┬──────────────────────┐
│  PIPELINE    │                                  │   PROPERTIES PANEL   │
│  BROWSER     │      3D RENDER VIEW              │                      │
│              │     (trame-vtklocal)             │  ┌────────────────┐  │
│ Search: [__] │                                  │  │Props│Info│Disp│  │
│              │                                  │  └────────────────┘  │
│ ┌──────────┐ │   - Ribbon visualization         │                      │
│ │●Trajectory │  - Color mapping                │  Context-sensitive   │
│ └──────────┘ │   - Mouse rotation               │  controls for:       │
│   ┌────────┐ │   - Click to select              │                      │
│   │└─Spline│ │                                  │  • Trajectory Data   │
│   └────────┘ │                                  │  • Spline Filter     │
│   ┌────────┐ │                                  │  • Ribbon Filter     │
│   │└─Ribbon│←────────────────────────────────→│  • Clipping          │
│   └────────┘ │    Selected item properties     │  • Contacts          │
│   ┌────────┐ │    shown in Properties Panel    │                      │
│   │└─Clip  │ │                                  │  ┌────────────────┐  │
│   └────────┘ │                                  │  │  Color Map     │  │
│   ┌────────┐ │                                  │  │ [■■■■■■■■■■■] │  │
│   │└Contact│ │                                  │  │  0.0    1.0    │  │
│   └────────┘ │                                  │  └────────────────┘  │
│              │                                  │                      │
│              │                                  │  [Apply] [Reset]     │
└──────────────┴──────────────────────────────────┴──────────────────────┘

Benefits:
✓ Visual pipeline structure
✓ Three-panel professional layout
✓ Toolbar for quick actions
✓ Context-sensitive properties
✓ Better organization
```

---

## Pipeline Browser Detail

```
┌────────────────────────────────────┐
│  PIPELINE BROWSER                  │
├────────────────────────────────────┤
│  Search: [________________]  🔍    │
├────────────────────────────────────┤
│                                    │
│  ● Trajectory Data                 │  ← Source (root)
│    📊 Metadata: 194 frames         │
│                                    │
│    └─ CA Spline                    │  ← Filter (indented)
│       📈 Subdivision: 1.5 Å        │
│                                    │
│       └─ Ribbon                    │  ← Filter (2x indented)
│          🎀 Width: 0.3             │    Selected (highlighted)
│          ✓ Visible                 │
│                                    │
│       └─ Clipping Plane            │  ← Optional filter
│          ✂️ Normal: (1,0,0)        │    (shown when enabled)
│          ✓ Visible                 │
│                                    │
│    └─ Contacts                     │  ← Optional filter
│       🔗 Threshold: 5.0 Å          │    (shown when enabled)
│       ✓ Visible                    │
│                                    │
└────────────────────────────────────┘

Interactions:
• Click item → Select (highlights, updates Properties)
• Eye icon → Toggle visibility
• Right-click → Context menu (future)
```

---

## Properties Panel - Three Tabs

### Properties Tab (Context-Sensitive)

```
┌────────────────────────────────────┐
│ ┌────┬────┬────────┐               │
│ │Props│Info│Display│               │
│ └────┴────┴────────┘               │
├────────────────────────────────────┤
│  Properties of: Ribbon             │
├────────────────────────────────────┤
│                                    │
│  Ribbon Width                      │
│  ├────●────────────┤  0.3          │
│   0.1          0.5                 │
│                                    │
│  Angle                             │
│  ├────●────────────┤  0.0°         │
│   0°           90°                 │
│                                    │
│  Subdivision Length                │
│  ├─────────●───────┤  1.5 Å        │
│   0.5          3.0                 │
│                                    │
│  Color Metric                      │
│  [Hotspot        ▼]                │
│                                    │
│  [Apply Changes]                   │
│                                    │
└────────────────────────────────────┘

When "Clipping Plane" selected:
┌────────────────────────────────────┐
│  Properties of: Clipping Plane     │
├────────────────────────────────────┤
│                                    │
│  Normal Direction                  │
│  ( X )  O Y   O Z                  │
│                                    │
│  Position                          │
│  ├────●────────────┤  50%          │
│   0%          100%                 │
│                                    │
│  Invert Plane                      │
│  [ ]                               │
│                                    │
└────────────────────────────────────┘
```

### Information Tab

```
┌────────────────────────────────────┐
│ ┌────┬────┬────────┐               │
│ │Props│Info│Display│               │
│ └────┴────┴────────┘               │
├────────────────────────────────────┤
│  Information: Trajectory Data      │
├────────────────────────────────────┤
│                                    │
│  Dataset Type:                     │
│  • XTC Trajectory                  │
│                                    │
│  Dimensions:                       │
│  • Frames:     194                 │
│  • Atoms:      374                 │
│  • Residues:   374                 │
│                                    │
│  Current Frame: 0                  │
│                                    │
│  Bounds:                           │
│  • X: [-20.5, 22.3]                │
│  • Y: [-18.2, 19.8]                │
│  • Z: [-15.1, 16.4]                │
│                                    │
│  Memory Usage: 42.3 MB             │
│                                    │
└────────────────────────────────────┘
```

### Display Tab

```
┌────────────────────────────────────┐
│ ┌────┬────┬────────┐               │
│ │Props│Info│Display│               │
│ └────┴────┴────────┘               │
├────────────────────────────────────┤
│  Display Properties                │
├────────────────────────────────────┤
│                                    │
│  Representation                    │
│  [Surface         ▼]               │
│                                    │
│  Opacity                           │
│  ├──────────────●─┤  1.0          │
│   0.0          1.0                 │
│                                    │
│  Color Mapping                     │
│  Metric: [Hotspot      ▼]          │
│                                    │
│  Color Scale                       │
│  [red_white_blue  ▼]               │
│                                    │
│  Preview:                          │
│  [■■■■■■■■■■■■■■■]                │
│   Blue → White → Red               │
│                                    │
│  Scalar Range                      │
│  ( ) Auto                          │
│  (●) Manual                        │
│  Min: [0.0    ]  Max: [1.0    ]    │
│                                    │
│  Specular                          │
│  ├──●────────────┤  0.1            │
│   0.0          1.0                 │
│                                    │
│  Specular Power                    │
│  ├──────●────────┤  10.0           │
│   1.0         100.0                │
│                                    │
└────────────────────────────────────┘
```

---

## Toolbar Menus

### Filters Menu

```
┌──────────────────────────┐
│  [Filters ▼]             │
└──────────────────────────┘
  │
  ├─ Common Filters ────────
  │  ├─ Clip
  │  └─ Threshold...
  │
  └─ Molecular Filters ─────
     ├─ Show Contacts
     └─ Show RMSF

Click behavior:
• Clip → Immediately enable clipping
• Threshold → Open dialog
• Show Contacts → Toggle contacts
• Show RMSF → Set metric to RMSF
```

### View Menu

```
┌──────────────────────────┐
│  [View ▼]                │
└──────────────────────────┘
  │
  ├─ Camera Presets ────────
  │  ├─ +Z (Top View)
  │  ├─ +Y (Front View)
  │  ├─ +X (Side View)
  │  ├─ -Z (Bottom View)
  │  ├─ -Y (Back View)
  │  └─ -X (Left View)
  │
  ├─ ──────────────────────
  │
  ├─ Reset Camera
  │
  └─ View Options ──────────
     ├─ [ ] Parallel Projection
     └─ [✓] Show Orientation Axes

Click behavior:
• Camera preset → Instant reposition
• Reset Camera → Fit all data
• Options → Toggle features
```

---

## Color Scheme (ParaView Dark Theme)

```
Background Colors:
┌────────────────────────────────────┐
│ Main Background: #1e1e1e           │  ← Very dark gray
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ Panel Background: #252526          │  ← Slightly lighter
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ Border: #3e3e42                    │  ← Subtle divider
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   │
└────────────────────────────────────┘

Text Colors:
┌────────────────────────────────────┐
│ Primary Text: #cccccc              │  ← Light gray
│ "Pipeline Browser"                 │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ Accent: #007acc                    │  ← Blue
│ ████████                           │
└────────────────────────────────────┘

Color Map Example (red_white_blue):
┌────────────────────────────────────┐
│ 0.0  [████] Blue #08306b           │
│ 0.5  [████] White #ffffff          │
│ 1.0  [████] Red #67000d            │
└────────────────────────────────────┘
```

---

## Interaction Flows

### Flow 1: Selecting a Pipeline Item

```
User Action: Click "Ribbon" in Pipeline Browser
  │
  ├─> Pipeline Browser
  │     • Highlights "Ribbon" item
  │     • Shows checkmark/icon
  │
  ├─> State Update
  │     • selectedPipelineItem = "ribbon"
  │
  └─> Properties Panel
        • Switches to show ribbon properties
        • Properties tab: width, angle, subdivision
        • Information tab: ribbon statistics
        • Display tab: color mapping, appearance
```

### Flow 2: Adding a Filter via Menu

```
User Action: Click Filters → Clip
  │
  ├─> Controller
  │     • toggle_clipping() called
  │
  ├─> State Update
  │     • clipping_enabled = True
  │
  ├─> VTK Pipeline
  │     • Adds clip plane
  │     • Applies clipping
  │
  ├─> Pipeline Browser
  │     • Shows "Clipping Plane" item
  │     • Indented under Ribbon
  │
  ├─> Properties Panel
  │     • Automatically selects "Clipping Plane"
  │     • Shows clip controls
  │
  └─> 3D View
        • Updates to show clipped ribbon
```

### Flow 3: Changing Camera View

```
User Action: Click View → +Z (Top View)
  │
  ├─> Controller
  │     • set_camera_view("+Z") called
  │
  ├─> Camera Calculation
  │     • Get bounds: actor.GetBounds()
  │     • Calculate center point
  │     • Calculate distance
  │
  ├─> VTK Camera
  │     • SetPosition(center[0], center[1], center[2] + distance)
  │     • SetViewUp(0, 1, 0)
  │     • SetFocalPoint(center)
  │
  └─> 3D View
        • Instantly repositions camera
        • Looking down from +Z axis
        • Ribbon viewed from top
```

---

## Responsive Behavior

### Desktop (1920x1080)

```
┌──────────────────────────────────────────────────────────────────┐
│  Toolbar (full width)                                            │
├──────────┬─────────────────────────────────────┬─────────────────┤
│ Pipeline │          3D View (large)            │   Properties    │
│  (280px) │           (expanding)               │     (320px)     │
│          │                                     │                 │
│  [full]  │                                     │     [full]      │
└──────────┴─────────────────────────────────────┴─────────────────┘
```

### Laptop (1366x768)

```
┌────────────────────────────────────────────────────────────┐
│  Toolbar (full width)                                      │
├──────┬──────────────────────────────────┬──────────────────┤
│ Pipe │      3D View (medium)            │   Properties     │
│(240) │       (expanding)                │     (280px)      │
│      │                                  │                  │
│[full]│                                  │     [tabs]       │
└──────┴──────────────────────────────────┴──────────────────┘
```

### Tablet (768px wide)

```
┌──────────────────────────────────────────┐
│  Toolbar (full width)                    │
├──────────────────────────────────────────┤
│  [☰] Pipeline (drawer, hidden)           │
│                                          │
│          3D View (full width)            │
│                                          │
│                                          │
│  [⚙] Properties (drawer, bottom)        │
└──────────────────────────────────────────┘

Panels collapse to drawers:
• Click ☰ → Pipeline slides in from left
• Click ⚙ → Properties slides in from right
```

---

## Icon Reference

```
Pipeline Browser Icons:
🗄️ mdi-database      → Trajectory Data (source)
📊 mdi-chart-bell-curve → CA Spline (filter)
🎀 mdi-ribbon        → Ribbon (filter)
✂️ mdi-content-cut   → Clipping Plane (filter)
🔗 mdi-link-variant  → Contacts (filter)

Toolbar Icons:
🔽 mdi-menu-down     → Dropdown menus
👁️ mdi-eye          → Visibility toggle
👁️‍🗨️ mdi-eye-off     → Hidden item
❓ mdi-help-circle   → Help

Controls:
▶️ mdi-play         → Play animation
⏸️ mdi-pause        → Pause animation
🔄 mdi-refresh      → Reset camera
📷 mdi-camera       → Camera controls
🎨 mdi-palette      → Color mapping
📏 mdi-ruler        → Measurements
```

---

## State Diagram

```
Application State:
┌────────────────────────────────────────┐
│  Global State                          │
├────────────────────────────────────────┤
│  • current_frame: 0..193               │
│  • current_metric: "hotspot"           │
│  • is_playing: false                   │
│  • clipping_enabled: false             │
│  • contacts_visible: false             │
├────────────────────────────────────────┤
│  Pipeline Browser State                │
├────────────────────────────────────────┤
│  • pipelineBrowserVisible: true        │
│  • selectedPipelineItem: "ribbon"      │
│  • pipelineItems: [...]                │
├────────────────────────────────────────┤
│  Properties Panel State                │
├────────────────────────────────────────┤
│  • propertiesPanelVisible: true        │
│  • propertiesTab: 0  (Props=0,Info=1)  │
├────────────────────────────────────────┤
│  VTK Pipeline State                    │
├────────────────────────────────────────┤
│  • ribbon_width: 0.3                   │
│  • ribbon_angle: 0.0                   │
│  • clip_position: 0.5                  │
│  • clip_normal: (1, 0, 0)              │
└────────────────────────────────────────┘

State changes trigger:
• UI updates (reactive)
• VTK pipeline updates
• Render window refresh
```

---

## Implementation Checklist (Visual)

```
Phase 1: Research ✓
  [■■■■■■■■■■] 100% COMPLETE

Phase 2: Pipeline Browser
  [          ] 0%
  
Phase 3: Properties Panel
  [          ] 0%
  
Phase 4: Filters Menu
  [          ] 0%
  
Phase 5: View Menu
  [          ] 0%
  
Phase 6: Styling
  [          ] 0%
  
Phase 7: Testing
  [          ] 0%
  
Phase 8: Documentation
  [          ] 0%

Overall Progress:
  [■■        ] 12.5% (1/8 phases)
```

---

**This visual guide provides a clear picture of what the ParaView integration will look like and how it will work.**
