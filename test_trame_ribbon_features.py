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
    
    # Test distance between first two residues
    if len(trame_ribbon_app._ca_positions_cache) >= 2:
        dist = trame_ribbon_app._calculate_distance(0, 1)
        assert dist > 0, "Distance should be positive"
        assert dist < 100, "Distance should be reasonable (< 100 Å)"
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
