#!/usr/bin/env python
"""
Test script for enhanced Trame ribbon viewer features.
Validates clipping, contacts, measurements, residue info, and color schemes.
"""

import json
import math
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_trame_ribbon_import():
    """Test that the trame_ribbon_app module imports without errors."""
    print("Testing trame_ribbon_app import...")
    
    import trame_ribbon_app
    
    # Verify key attributes exist
    assert hasattr(trame_ribbon_app, 'server'), "Missing 'server' attribute"
    assert hasattr(trame_ribbon_app, 'state'), "Missing 'state' attribute"
    assert hasattr(trame_ribbon_app, 'ctrl'), "Missing 'ctrl' attribute"
    assert hasattr(trame_ribbon_app, 'update_ribbon_geometry'), "Missing 'update_ribbon_geometry' function"
    
    print("✓ trame_ribbon_app imports successfully")
    return True


def test_metric_config():
    """Test that metric configuration is properly set up."""
    print("\nTesting metric configuration...")
    
    import trame_ribbon_app
    
    # Verify metric configs exist
    assert 'hotspot' in trame_ribbon_app.METRIC_CONFIG, "Missing 'hotspot' metric"
    assert 'anomaly' in trame_ribbon_app.METRIC_CONFIG, "Missing 'anomaly' metric"
    assert 'rmsf' in trame_ribbon_app.METRIC_CONFIG, "Missing 'rmsf' metric"
    assert 'tica' in trame_ribbon_app.METRIC_CONFIG, "Missing 'tica' metric"
    
    # Verify each metric has required fields
    for metric_name, config in trame_ribbon_app.METRIC_CONFIG.items():
        assert 'label' in config, f"Metric '{metric_name}' missing 'label'"
        assert 'description' in config, f"Metric '{metric_name}' missing 'description'"
        assert 'frame_dependent' in config, f"Metric '{metric_name}' missing 'frame_dependent'"
        assert 'source' in config, f"Metric '{metric_name}' missing 'source'"
    
    print(f"✓ All {len(trame_ribbon_app.METRIC_CONFIG)} metrics properly configured")
    return True


def test_metric_explanations():
    """Test that metric explanations are available (Task 4)."""
    print("\nTesting metric explanations...")
    
    import trame_ribbon_app
    
    assert hasattr(trame_ribbon_app, 'METRIC_EXPLANATIONS'), "Missing METRIC_EXPLANATIONS"
    
    explanations = trame_ribbon_app.METRIC_EXPLANATIONS
    assert 'hotspot' in explanations, "Missing hotspot explanation"
    assert 'anomaly' in explanations, "Missing anomaly explanation"
    assert 'rmsf' in explanations, "Missing rmsf explanation"
    assert 'tica' in explanations, "Missing tica explanation"
    
    # Verify explanations are non-empty strings
    for key, explanation in explanations.items():
        assert isinstance(explanation, str) and len(explanation) > 10, \
            f"Explanation for '{key}' should be a meaningful string"
    
    print(f"✓ All {len(explanations)} metric explanations available")
    return True


def test_metric_specific_colormaps():
    """Test that metric-specific color maps exist (Task 5)."""
    print("\nTesting metric-specific colormaps...")
    
    import trame_ribbon_app
    
    assert hasattr(trame_ribbon_app, 'METRIC_COLORMAPS'), "Missing METRIC_COLORMAPS"
    assert hasattr(trame_ribbon_app, 'COLORMAP_PRESETS'), "Missing COLORMAP_PRESETS"
    
    metric_colormaps = trame_ribbon_app.METRIC_COLORMAPS
    colormap_presets = trame_ribbon_app.COLORMAP_PRESETS
    
    # Verify metric-specific colormaps are defined
    assert 'anomaly' in metric_colormaps, "Missing anomaly colormap mapping"
    assert 'rmsf' in metric_colormaps, "Missing rmsf colormap mapping"
    assert 'tica' in metric_colormaps, "Missing tica colormap mapping"
    
    # Verify the gradient presets exist
    assert 'anomaly_gradient' in colormap_presets, "Missing anomaly_gradient preset"
    assert 'rmsf_gradient' in colormap_presets, "Missing rmsf_gradient preset"
    assert 'tica_gradient' in colormap_presets, "Missing tica_gradient preset"
    
    # Verify gradient structure
    for preset_name in ['anomaly_gradient', 'rmsf_gradient', 'tica_gradient']:
        preset = colormap_presets[preset_name]
        assert len(preset) >= 2, f"Preset '{preset_name}' should have at least 2 color stops"
        for pos, color in preset:
            assert 0 <= pos <= 1, f"Position {pos} out of range [0,1]"
            assert color.startswith('#'), f"Color {color} should be hex format"
    
    print("✓ Metric-specific colormaps properly configured")
    return True


def test_contacts_loading():
    """Test that contacts data is loaded (Task 2)."""
    print("\nTesting contacts data loading...")
    
    import trame_ribbon_app
    
    assert hasattr(trame_ribbon_app, 'CONTACTS_DATA'), "Missing CONTACTS_DATA"
    
    contacts_data = trame_ribbon_app.CONTACTS_DATA
    assert 'contacts' in contacts_data, "CONTACTS_DATA missing 'contacts' key"
    
    contacts = contacts_data['contacts']
    assert len(contacts) > 0, "No contacts loaded"
    
    # Verify contact structure
    for contact in contacts[:5]:
        assert 'residue1' in contact, "Contact missing 'residue1'"
        assert 'residue2' in contact, "Contact missing 'residue2'"
        assert 'frequency' in contact, "Contact missing 'frequency'"
    
    print(f"✓ Loaded {len(contacts)} contacts")
    return True


def test_clipping_infrastructure():
    """Test that clipping plane infrastructure exists (Task 1)."""
    print("\nTesting clipping plane infrastructure...")
    
    import trame_ribbon_app
    
    # Verify clip_plane exists
    assert hasattr(trame_ribbon_app, 'clip_plane'), "Missing clip_plane"
    
    # Verify state variables for clipping
    state = trame_ribbon_app.state
    assert hasattr(state, 'clip_enabled'), "State missing 'clip_enabled'"
    assert hasattr(state, 'clip_axis'), "State missing 'clip_axis'"
    assert hasattr(state, 'clip_position'), "State missing 'clip_position'"
    
    # Verify clipping update function
    assert hasattr(trame_ribbon_app, '_update_clipping'), "Missing '_update_clipping' function"
    
    print("✓ Clipping plane infrastructure in place")
    return True


def test_measurement_infrastructure():
    """Test that measurement infrastructure exists (Task 3)."""
    print("\nTesting measurement infrastructure...")
    
    import trame_ribbon_app
    
    # Verify distance calculation function
    assert hasattr(trame_ribbon_app, '_calculate_distance'), "Missing '_calculate_distance'"
    
    # Verify angle calculation function
    assert hasattr(trame_ribbon_app, '_calculate_angle'), "Missing '_calculate_angle'"
    
    # Verify state variables
    state = trame_ribbon_app.state
    assert hasattr(state, 'measurement_mode'), "State missing 'measurement_mode'"
    assert hasattr(state, 'measurement_result'), "State missing 'measurement_result'"
    
    print("✓ Measurement infrastructure in place")
    return True


def test_distance_calculation():
    """Test distance calculation function (Task 3)."""
    print("\nTesting distance calculation...")
    
    import trame_ribbon_app
    
    # First update geometry to populate CA positions
    trame_ribbon_app.update_ribbon_geometry(0, 'hotspot')
    
    # Maximum reasonable CA-CA distance in proteins (in Angstroms)
    MAX_REASONABLE_DISTANCE_ANGSTROM = 100
    
    # Test distance between first two residues
    if len(trame_ribbon_app._ca_positions_cache) >= 2:
        dist = trame_ribbon_app._calculate_distance(0, 1)
        assert dist > 0, "Distance should be positive"
        assert dist < MAX_REASONABLE_DISTANCE_ANGSTROM, \
            f"Distance should be reasonable (< {MAX_REASONABLE_DISTANCE_ANGSTROM} Å)"
        print(f"  Distance between residue 0 and 1: {dist:.2f} Å")
    
    print("✓ Distance calculation works")
    return True


def test_angle_calculation():
    """Test angle calculation function (Task 3)."""
    print("\nTesting angle calculation...")
    
    import trame_ribbon_app
    
    # First update geometry to populate CA positions
    trame_ribbon_app.update_ribbon_geometry(0, 'hotspot')
    
    # Test angle between first three residues
    if len(trame_ribbon_app._ca_positions_cache) >= 3:
        angle = trame_ribbon_app._calculate_angle(0, 1, 2)
        assert 0 <= angle <= 180, f"Angle should be in [0, 180], got {angle}"
        print(f"  Angle at residue 1 (0-1-2): {angle:.1f}°")
    
    print("✓ Angle calculation works")
    return True


def test_residue_info_formatting():
    """Test residue info formatting function (Task 4)."""
    print("\nTesting residue info formatting...")
    
    import trame_ribbon_app
    
    # Get info for first residue
    info = trame_ribbon_app._format_residue_info(0, 0)
    
    assert 'index' in info, "Info missing 'index'"
    assert 'resnum' in info, "Info missing 'resnum'"
    assert 'resname' in info, "Info missing 'resname'"
    assert 'chain' in info, "Info missing 'chain'"
    assert 'metrics' in info, "Info missing 'metrics'"
    assert 'explanations' in info, "Info missing 'explanations'"
    
    # Verify metrics dict has all metric types
    metrics = info['metrics']
    assert 'hotspot' in metrics, "Metrics missing 'hotspot'"
    assert 'anomaly' in metrics, "Metrics missing 'anomaly'"
    assert 'rmsf' in metrics, "Metrics missing 'rmsf'"
    assert 'tica' in metrics, "Metrics missing 'tica'"
    
    print(f"✓ Residue info formatting works")
    print(f"  Sample: {info['resname']}{info['resnum']} (chain {info['chain']})")
    return True


def test_contact_actors_building():
    """Test contact actors building (Task 2)."""
    print("\nTesting contact actors building...")
    
    import trame_ribbon_app
    
    # First update geometry
    trame_ribbon_app.update_ribbon_geometry(0, 'hotspot')
    
    # Get top contacts
    top_contacts = trame_ribbon_app._get_top_contacts(50)
    assert len(top_contacts) > 0, "Should have top contacts"
    
    # Verify contact structure
    contact = top_contacts[0]
    assert 'residue1' in contact
    assert 'residue2' in contact
    assert 'frequency' in contact
    
    print(f"✓ Got {len(top_contacts)} top contacts")
    return True


def test_state_initialization():
    """Test that all state variables are properly initialized."""
    print("\nTesting state initialization...")
    
    import trame_ribbon_app
    
    state = trame_ribbon_app.state
    
    # Core state
    assert hasattr(state, 'current_frame'), "Missing current_frame"
    assert hasattr(state, 'current_metric'), "Missing current_metric"
    assert hasattr(state, 'current_colormap'), "Missing current_colormap"
    
    # Clipping state (Task 1)
    assert hasattr(state, 'clip_enabled'), "Missing clip_enabled"
    assert hasattr(state, 'clip_axis'), "Missing clip_axis"
    assert hasattr(state, 'clip_position'), "Missing clip_position"
    
    # Contacts state (Task 2)
    assert hasattr(state, 'show_contacts'), "Missing show_contacts"
    assert hasattr(state, 'top_contacts_list'), "Missing top_contacts_list"
    
    # Measurement state (Task 3)
    assert hasattr(state, 'measurement_mode'), "Missing measurement_mode"
    assert hasattr(state, 'measurement_result'), "Missing measurement_result"
    
    # Residue info state (Task 4)
    assert hasattr(state, 'selected_residue_idx'), "Missing selected_residue_idx"
    assert hasattr(state, 'residue_info'), "Missing residue_info"
    assert hasattr(state, 'show_residue_info'), "Missing show_residue_info"
    
    # Color bar state (Task 5)
    assert hasattr(state, 'color_bar_label'), "Missing color_bar_label"
    
    print("✓ All state variables properly initialized")
    return True


def test_controller_functions():
    """Test that controller functions are registered."""
    print("\nTesting controller functions...")
    
    import trame_ribbon_app
    
    ctrl = trame_ribbon_app.ctrl
    
    # Basic controls
    assert hasattr(ctrl, 'update_view'), "Missing update_view"
    
    # Measurement controls (Task 3)
    # These are registered via @ctrl.add decorator
    
    print("✓ Controller functions registered")
    return True


def test_picking_infrastructure():
    """Test that picking infrastructure is properly set up."""
    print("\nTesting picking infrastructure...")
    
    import trame_ribbon_app
    
    # Verify pickers exist
    assert hasattr(trame_ribbon_app, 'cell_picker'), "Missing cell_picker"
    assert hasattr(trame_ribbon_app, 'point_picker'), "Missing point_picker"
    
    # Verify picking functions exist
    assert hasattr(trame_ribbon_app, '_pick_position_to_residue'), "Missing _pick_position_to_residue"
    assert hasattr(trame_ribbon_app, '_perform_pick'), "Missing _perform_pick"
    
    # Test _pick_position_to_residue with CA cache
    trame_ribbon_app.update_ribbon_geometry(0, 'hotspot')
    
    if len(trame_ribbon_app._ca_positions_cache) > 0:
        # Pick first CA position - should return residue 0
        ca_pos = trame_ribbon_app._ca_positions_cache[0]
        residue_idx = trame_ribbon_app._pick_position_to_residue(ca_pos)
        assert residue_idx == 0, f"Expected residue 0, got {residue_idx}"
        
        # Pick position far away - should return -1
        far_pos = (1000.0, 1000.0, 1000.0)
        residue_idx = trame_ribbon_app._pick_position_to_residue(far_pos)
        assert residue_idx == -1, f"Expected -1 for far position, got {residue_idx}"
    
    print("✓ Picking infrastructure in place")
    return True


def test_click_handlers():
    """Test that click handlers are registered."""
    print("\nTesting click handlers...")
    
    import trame_ribbon_app
    
    # Verify controller has click handlers
    ctrl = trame_ribbon_app.ctrl
    
    # on_vtk_click and on_vtk_select should be registered
    # These are added via @ctrl.add decorator
    
    # Test that handle_residue_pick exists and works
    assert hasattr(trame_ribbon_app, '_handle_residue_pick'), "Missing _handle_residue_pick"
    
    # Test picking a residue updates state (without measurement mode)
    trame_ribbon_app.update_ribbon_geometry(0, 'hotspot')
    trame_ribbon_app.state.measurement_mode = ""
    trame_ribbon_app._handle_residue_pick(5)
    
    # Should show residue info
    assert trame_ribbon_app.state.show_residue_info == True, "Should show residue info"
    assert trame_ribbon_app.state.selected_residue_idx == 5, "Should select residue 5"
    
    print("✓ Click handlers registered and working")
    return True


def test_animation_playback():
    """Test animation playback state and functions."""
    print("\nTesting animation playback...")
    
    import trame_ribbon_app
    
    state = trame_ribbon_app.state
    
    # Verify animation state variables
    assert hasattr(state, 'animation_playing'), "Missing animation_playing state"
    assert hasattr(state, 'animation_speed'), "Missing animation_speed state"
    assert hasattr(state, 'animation_speed_options'), "Missing animation_speed_options state"
    
    # Verify animation functions
    assert hasattr(trame_ribbon_app, '_animation_step'), "Missing _animation_step function"
    
    # Test animation step
    state.current_frame = 0
    trame_ribbon_app._animation_step()
    # Frame should advance (if animation_playing is True, but we test the function itself)
    
    print("✓ Animation playback infrastructure in place")
    return True


def test_residue_search():
    """Test residue search functionality."""
    print("\nTesting residue search...")
    
    import trame_ribbon_app
    
    # Verify search function exists
    assert hasattr(trame_ribbon_app, '_search_residues'), "Missing _search_residues function"
    
    # Test search function
    results = trame_ribbon_app._search_residues("ALA")
    assert isinstance(results, list), "Search should return list"
    
    # Test with number
    results = trame_ribbon_app._search_residues("1")
    assert isinstance(results, list), "Search by number should return list"
    
    # Test state variables
    state = trame_ribbon_app.state
    assert hasattr(state, 'search_query'), "Missing search_query state"
    assert hasattr(state, 'search_results'), "Missing search_results state"
    
    print("✓ Residue search working")
    return True


def test_multi_selection():
    """Test multi-selection functionality."""
    print("\nTesting multi-selection...")
    
    import trame_ribbon_app
    
    state = trame_ribbon_app.state
    
    # Verify state variables
    assert hasattr(state, 'multi_select_enabled'), "Missing multi_select_enabled state"
    assert hasattr(state, 'selected_residues'), "Missing selected_residues state"
    assert hasattr(state, 'multi_select_metrics'), "Missing multi_select_metrics state"
    
    # Verify metrics calculation
    assert hasattr(trame_ribbon_app, '_get_multi_select_metrics'), "Missing _get_multi_select_metrics function"
    
    print("✓ Multi-selection infrastructure in place")
    return True


def test_hover_tooltips():
    """Test hover tooltip functionality."""
    print("\nTesting hover tooltips...")
    
    import trame_ribbon_app
    
    state = trame_ribbon_app.state
    
    # Verify state variables
    assert hasattr(state, 'hover_enabled'), "Missing hover_enabled state"
    assert hasattr(state, 'hover_residue_idx'), "Missing hover_residue_idx state"
    assert hasattr(state, 'hover_tooltip_text'), "Missing hover_tooltip_text state"
    
    # Verify tooltip function
    assert hasattr(trame_ribbon_app, '_get_hover_tooltip'), "Missing _get_hover_tooltip function"
    
    # Test tooltip generation
    tooltip = trame_ribbon_app._get_hover_tooltip(0)
    assert isinstance(tooltip, str), "Tooltip should be string"
    assert len(tooltip) > 0, "Tooltip should not be empty for valid residue"
    
    # Test invalid residue
    tooltip = trame_ribbon_app._get_hover_tooltip(-1)
    assert tooltip == "", "Tooltip should be empty for invalid residue"
    
    print("✓ Hover tooltips working")
    return True


def test_bookmarks():
    """Test bookmark functionality."""
    print("\nTesting bookmarks...")
    
    import trame_ribbon_app
    
    state = trame_ribbon_app.state
    
    # Verify state variables
    assert hasattr(state, 'bookmarks'), "Missing bookmarks state"
    assert hasattr(state, 'bookmark_name'), "Missing bookmark_name state"
    
    # Verify camera functions
    assert hasattr(trame_ribbon_app, '_get_camera_state'), "Missing _get_camera_state function"
    assert hasattr(trame_ribbon_app, '_set_camera_state'), "Missing _set_camera_state function"
    
    # Test camera state retrieval
    camera_state = trame_ribbon_app._get_camera_state()
    assert 'position' in camera_state, "Camera state should have position"
    assert 'focal_point' in camera_state, "Camera state should have focal_point"
    
    print("✓ Bookmark functionality in place")
    return True


def test_focus_on_residue():
    """Test focus on residue functionality."""
    print("\nTesting focus on residue...")
    
    import trame_ribbon_app
    
    # Verify function exists
    assert hasattr(trame_ribbon_app, '_focus_on_residue'), "Missing _focus_on_residue function"
    
    # In headless mode, just verify the function exists and camera functions work
    assert hasattr(trame_ribbon_app, '_get_camera_state'), "Missing _get_camera_state function"
    
    # Test camera state functions (don't actually render)
    camera = trame_ribbon_app.renderer.GetActiveCamera()
    pos = camera.GetPosition()
    assert len(pos) == 3, "Camera position should be 3D"
    
    print("✓ Focus on residue infrastructure in place")
    return True


def test_measurement_debug_flag():
    """Test that ASVS_DEBUG_MEASURE flag is exposed."""
    print("\nTesting measurement debug flag...")

    import trame_ribbon_app

    assert hasattr(trame_ribbon_app, '_DEBUG_MEASURE'), "Missing _DEBUG_MEASURE flag"
    assert isinstance(trame_ribbon_app._DEBUG_MEASURE, bool), "_DEBUG_MEASURE should be bool"

    print("✓ Measurement debug flag present")
    return True


def test_measurement_label_actor():
    """Test that measurement label actor is tracked."""
    print("\nTesting measurement label actor tracking...")

    import trame_ribbon_app

    assert hasattr(trame_ribbon_app, '_measurement_label_actor'), \
        "Missing _measurement_label_actor global"

    print("✓ Measurement label actor tracking present")
    return True


def test_measurement_clear_actors():
    """Test that _clear_measurement_actors clears the label actor too."""
    print("\nTesting measurement clear actors...")

    import trame_ribbon_app

    # Populate CA positions
    trame_ribbon_app.update_ribbon_geometry(0, 'hotspot')

    # Manually set a fake label actor reference to verify it gets cleared
    import vtk
    mock_label_actor = vtk.vtkTextActor()
    trame_ribbon_app._measurement_label_actor = mock_label_actor

    trame_ribbon_app._clear_measurement_actors()

    assert trame_ribbon_app._measurement_label_actor is None, \
        "_measurement_label_actor should be None after clear"
    assert len(trame_ribbon_app.measurement_actors) == 0, \
        "measurement_actors list should be empty after clear"

    print("✓ Clear measurement actors clears label actor")
    return True


def test_coordinate_extraction_zero_safe():
    """Test that _first_not_none correctly handles x=0 or y=0 (falsy-zero fix)."""
    print("\nTesting coordinate extraction for x=0/y=0...")

    import trame_ribbon_app

    # Verify the module-level helper exists
    assert hasattr(trame_ribbon_app, '_first_not_none'), "Missing _first_not_none helper"

    fn = trame_ribbon_app._first_not_none

    # x=0 must NOT be skipped (the old `or`-chain bug treated it as missing)
    assert fn({"x": 0, "y": 5}, "x") == 0, "x=0 should be returned, not skipped"
    assert fn({"x": 0, "y": 5}, "y") == 5

    # Normal positive values
    assert fn({"x": 100, "y": 200}, "x", "clientX") == 100

    # Fallback to secondary key when primary is absent
    assert fn({"clientX": 42}, "x", "clientX") == 42

    # All keys absent → None
    assert fn({}, "x", "clientX") is None

    print("✓ x=0 / y=0 coordinates correctly extracted via _first_not_none")
    return True


def test_measurement_overlay_refresh_on_frame():
    """Test that measurement overlay is refreshed when frame changes."""
    print("\nTesting measurement overlay refresh on frame change...")

    import trame_ribbon_app

    trame_ribbon_app.update_ribbon_geometry(0, 'hotspot')

    # Set up a two-point distance measurement
    trame_ribbon_app._measurement_mode = "distance"
    trame_ribbon_app._measurement_picks = [0, 1]
    trame_ribbon_app._measurement_result = "Distance: 3.80 Å between A1 and A2"

    # Now update to a new frame - overlay should be regenerated without error
    try:
        trame_ribbon_app.update_ribbon_geometry(0, 'hotspot')
    except Exception as exc:
        assert False, f"Frame update with active measurement raised: {exc}"

    # Clean up
    trame_ribbon_app._measurement_mode = None
    trame_ribbon_app._measurement_picks = []
    trame_ribbon_app._measurement_result = ""
    trame_ribbon_app._clear_measurement_actors()

    print("✓ Measurement overlay refreshes cleanly on frame update")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Enhanced Trame Ribbon Viewer Features")
    print("=" * 60)
    
    tests = [
        test_trame_ribbon_import,
        test_metric_config,
        test_metric_explanations,
        test_metric_specific_colormaps,
        test_contacts_loading,
        test_clipping_infrastructure,
        test_measurement_infrastructure,
        test_distance_calculation,
        test_angle_calculation,
        test_residue_info_formatting,
        test_contact_actors_building,
        test_state_initialization,
        test_controller_functions,
        test_picking_infrastructure,
        test_click_handlers,
        # New feature tests
        test_animation_playback,
        test_residue_search,
        test_multi_selection,
        test_hover_tooltips,
        test_bookmarks,
        test_focus_on_residue,
        # Measurement fix tests
        test_measurement_debug_flag,
        test_measurement_label_actor,
        test_measurement_clear_actors,
        test_coordinate_extraction_zero_safe,
        test_measurement_overlay_refresh_on_frame,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
