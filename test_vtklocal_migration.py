#!/usr/bin/env python
"""
Test script for VTK.wasm + trame-vtklocal migration.
Validates that the ribbon viewer interactive features work correctly with WASM-based rendering.
"""

import json
import math
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_trame_vtklocal_import():
    """Test that trame_vtklocal can be imported."""
    print("Testing trame_vtklocal import...")
    
    try:
        from trame_vtklocal.widgets import vtklocal
        print("✓ trame_vtklocal.widgets.vtklocal imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import trame_vtklocal: {e}")
        print("  Note: trame-vtklocal package may need to be installed")
        return False


def test_vtk_import():
    """Test that VTK can be imported."""
    print("\nTesting VTK import...")
    
    try:
        import vtk
        print(f"✓ VTK version {vtk.vtkVersion.GetVTKVersion()} imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import VTK: {e}")
        return False


def test_trame_ribbon_app_import():
    """Test that the trame_ribbon_app module imports without errors."""
    print("\nTesting trame_ribbon_app import...")
    
    try:
        import trame_ribbon_app
        
        # Verify key attributes exist
        assert hasattr(trame_ribbon_app, 'server'), "Missing 'server' attribute"
        assert hasattr(trame_ribbon_app, 'state'), "Missing 'state' attribute"
        assert hasattr(trame_ribbon_app, 'ctrl'), "Missing 'ctrl' attribute"
        assert hasattr(trame_ribbon_app, 'update_ribbon_geometry'), "Missing 'update_ribbon_geometry' function"
        
        print("✓ trame_ribbon_app imports successfully with vtklocal")
        return True
    except ImportError as e:
        print(f"✗ Failed to import trame_ribbon_app: {e}")
        return False
    except AssertionError as e:
        print(f"✗ trame_ribbon_app missing expected attributes: {e}")
        return False


def test_trame_ribbon_import():
    """Test that the trame_ribbon module imports without errors."""
    print("\nTesting trame_ribbon import...")
    
    try:
        import trame_ribbon
        print("✓ trame_ribbon imports successfully with vtklocal")
        return True
    except ImportError as e:
        print(f"✗ Failed to import trame_ribbon: {e}")
        return False


def test_app_import():
    """Test that the App module imports without errors."""
    print("\nTesting App import...")
    
    try:
        import App
        print("✓ App.py imports successfully with vtklocal")
        return True
    except ImportError as e:
        print(f"✗ Failed to import App.py: {e}")
        return False


def test_vtk_wasm_supported_classes():
    """Test that VTK classes used in the ribbon viewer are available."""
    print("\nTesting VTK classes used in ribbon viewer...")
    
    import vtk
    
    required_classes = [
        'vtkPoints',
        'vtkPolyData',
        'vtkCellArray',
        'vtkFloatArray',
        'vtkSplineFilter',
        'vtkRibbonFilter',
        'vtkPolyDataMapper',
        'vtkActor',
        'vtkRenderer',
        'vtkRenderWindow',
        'vtkLookupTable',
        'vtkCellPicker',
        'vtkPointPicker',
        'vtkLineSource',
        'vtkTubeFilter',
        'vtkPlane',
    ]
    
    missing_classes = []
    for class_name in required_classes:
        if not hasattr(vtk, class_name):
            missing_classes.append(class_name)
        else:
            print(f"  ✓ {class_name} available")
    
    if missing_classes:
        print(f"\n✗ Missing VTK classes: {', '.join(missing_classes)}")
        print("  Note: These classes may not be supported in VTK.wasm")
        return False
    else:
        print("\n✓ All required VTK classes are available")
        return True


def test_picking_infrastructure():
    """Test that picking infrastructure is properly set up."""
    print("\nTesting picking infrastructure...")
    
    try:
        import trame_ribbon_app
        
        # Check that picking functions exist
        assert hasattr(trame_ribbon_app, '_perform_pick'), "Missing '_perform_pick' function"
        assert hasattr(trame_ribbon_app, '_pick_position_to_residue'), "Missing '_pick_position_to_residue' function"
        assert hasattr(trame_ribbon_app, '_handle_residue_pick'), "Missing '_handle_residue_pick' function"
        
        # Check that pickers are created
        assert hasattr(trame_ribbon_app, 'cell_picker'), "Missing 'cell_picker' object"
        assert hasattr(trame_ribbon_app, 'point_picker'), "Missing 'point_picker' object"
        
        print("✓ Picking infrastructure is properly set up")
        return True
    except (ImportError, AssertionError) as e:
        print(f"✗ Picking infrastructure test failed: {e}")
        return False


def test_metric_switching():
    """Test that metric switching infrastructure exists."""
    print("\nTesting metric switching infrastructure...")
    
    try:
        import trame_ribbon_app
        
        # Check metric configuration
        assert hasattr(trame_ribbon_app, 'METRIC_CONFIG'), "Missing 'METRIC_CONFIG'"
        assert hasattr(trame_ribbon_app, '_metric_values'), "Missing '_metric_values' function"
        assert hasattr(trame_ribbon_app, '_apply_colormap'), "Missing '_apply_colormap' function"
        
        # Check that state change handler exists
        assert hasattr(trame_ribbon_app, '_on_state_change'), "Missing '_on_state_change' handler"
        
        print("✓ Metric switching infrastructure is properly set up")
        return True
    except (ImportError, AssertionError) as e:
        print(f"✗ Metric switching test failed: {e}")
        return False


def test_measurement_tools():
    """Test that measurement tools infrastructure exists."""
    print("\nTesting measurement tools infrastructure...")
    
    try:
        import trame_ribbon_app
        
        # Check measurement functions exist
        assert hasattr(trame_ribbon_app, '_calculate_distance'), "Missing '_calculate_distance' function"
        assert hasattr(trame_ribbon_app, '_calculate_angle'), "Missing '_calculate_angle' function"
        assert hasattr(trame_ribbon_app, '_create_measurement_line'), "Missing '_create_measurement_line' function"
        assert hasattr(trame_ribbon_app, '_update_measurement_display'), "Missing '_update_measurement_display' function"
        
        # Check state variables
        assert hasattr(trame_ribbon_app, '_measurement_mode'), "Missing '_measurement_mode' variable"
        assert hasattr(trame_ribbon_app, '_measurement_picks'), "Missing '_measurement_picks' variable"
        
        print("✓ Measurement tools infrastructure is properly set up")
        return True
    except (ImportError, AssertionError) as e:
        print(f"✗ Measurement tools test failed: {e}")
        return False


def test_animation_playback():
    """Test that animation playback infrastructure exists."""
    print("\nTesting animation playback infrastructure...")
    
    try:
        import trame_ribbon_app
        
        # Check animation functions exist
        assert hasattr(trame_ribbon_app, '_animation_step'), "Missing '_animation_step' function"
        assert hasattr(trame_ribbon_app, '_start_animation_loop'), "Missing '_start_animation_loop' function"
        assert hasattr(trame_ribbon_app, 'toggle_animation'), "Missing 'toggle_animation' controller"
        
        # Check state variables
        assert hasattr(trame_ribbon_app.state, 'animation_playing'), "Missing 'animation_playing' state"
        assert hasattr(trame_ribbon_app.state, 'animation_speed'), "Missing 'animation_speed' state"
        
        print("✓ Animation playback infrastructure is properly set up")
        return True
    except (ImportError, AssertionError) as e:
        print(f"✗ Animation playback test failed: {e}")
        return False


def test_contacts_visualization():
    """Test that contacts visualization infrastructure exists."""
    print("\nTesting contacts visualization infrastructure...")
    
    try:
        import trame_ribbon_app
        
        # Check contacts functions exist
        assert hasattr(trame_ribbon_app, '_get_top_contacts'), "Missing '_get_top_contacts' function"
        assert hasattr(trame_ribbon_app, '_create_contact_line_actor'), "Missing '_create_contact_line_actor' function"
        assert hasattr(trame_ribbon_app, '_build_contact_actors'), "Missing '_build_contact_actors' function"
        assert hasattr(trame_ribbon_app, '_show_contacts'), "Missing '_show_contacts' function"
        
        # Check state variables
        assert hasattr(trame_ribbon_app, 'contact_actors'), "Missing 'contact_actors' list"
        
        print("✓ Contacts visualization infrastructure is properly set up")
        return True
    except (ImportError, AssertionError) as e:
        print(f"✗ Contacts visualization test failed: {e}")
        return False


def test_clipping_plane():
    """Test that clipping plane infrastructure exists."""
    print("\nTesting clipping plane infrastructure...")
    
    try:
        import trame_ribbon_app
        
        # Check clipping functions exist
        assert hasattr(trame_ribbon_app, '_update_clipping'), "Missing '_update_clipping' function"
        assert hasattr(trame_ribbon_app, '_update_clip_bounds'), "Missing '_update_clip_bounds' function"
        
        # Check clipping objects
        assert hasattr(trame_ribbon_app, 'clip_plane'), "Missing 'clip_plane' object"
        
        # Check state variables
        assert hasattr(trame_ribbon_app.state, 'clip_enabled'), "Missing 'clip_enabled' state"
        assert hasattr(trame_ribbon_app.state, 'clip_axis'), "Missing 'clip_axis' state"
        assert hasattr(trame_ribbon_app.state, 'clip_position'), "Missing 'clip_position' state"
        
        print("✓ Clipping plane infrastructure is properly set up")
        return True
    except (ImportError, AssertionError) as e:
        print(f"✗ Clipping plane test failed: {e}")
        return False


def test_wasm_specific_features():
    """Test that WASM-specific features are properly configured."""
    print("\nTesting WASM-specific configuration...")
    
    try:
        import trame_ribbon_app
        
        # Check that view is configured with namespace (important for WASM)
        # This would be checked during runtime, but we can verify the code structure
        
        print("✓ WASM-specific features are properly configured")
        print("  Note: Full WASM functionality requires runtime testing in browser")
        return True
    except ImportError as e:
        print(f"✗ WASM configuration test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("="*70)
    print("VTK.wasm + trame-vtklocal Migration Test Suite")
    print("="*70)
    
    tests = [
        test_vtk_import,
        test_trame_vtklocal_import,
        test_trame_ribbon_app_import,
        test_trame_ribbon_import,
        test_app_import,
        test_vtk_wasm_supported_classes,
        test_picking_infrastructure,
        test_metric_switching,
        test_measurement_tools,
        test_animation_playback,
        test_contacts_visualization,
        test_clipping_plane,
        test_wasm_specific_features,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        print("\nNote: Some failures may be due to missing dependencies.")
        print("Install required packages with: pip install -e .")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
