#!/usr/bin/env python
"""
Test script for interactive trame ribbon viewer.
Validates hotspot loading, picking, and measurement functionality.
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_hotspot_data_loading():
    """Test that hotspot data can be loaded."""
    print("Testing hotspot data loading...")
    
    hotspot_file = "viewer/hotspots_residue.json"
    
    if not os.path.exists(hotspot_file):
        print(f"✗ Hotspot file not found: {hotspot_file}")
        return False
    
    try:
        with open(hotspot_file, 'r') as f:
            data = json.load(f)
        
        # Check structure
        assert isinstance(data, dict), "Hotspot data should be a dictionary"
        assert "0" in data, "Should have frame 0 data"
        
        frame_0 = data["0"]
        assert len(frame_0) > 0, "Should have residue data"
        
        # Check a few values
        for key, value in list(frame_0.items())[:5]:
            assert isinstance(key, str), "Keys should be strings"
            assert isinstance(value, (int, float)), "Values should be numeric"
            assert 0.0 <= value <= 1.0, f"Hotspot value {value} out of expected range"
        
        print(f"✓ Loaded {len(frame_0)} residue hotspot scores")
        return True
        
    except Exception as e:
        print(f"✗ Error loading hotspot data: {e}")
        return False


def test_pdb_files_available():
    """Test that PDB files are available."""
    print("\nTesting PDB file availability...")
    
    pdb_paths = [
        "static/examples/1cbs.pdb",
        "viewer/topology.pdb"
    ]
    
    found = False
    for path in pdb_paths:
        if os.path.exists(path):
            print(f"✓ Found PDB file: {path}")
            
            # Check file size
            size = os.path.getsize(path)
            if size > 0:
                print(f"  Size: {size} bytes")
                found = True
            else:
                print(f"  Warning: File is empty")
    
    if not found:
        print("✗ No valid PDB files found")
        return False
    
    return True


def test_trame_ribbon_import():
    """Test that trame_ribbon module can be imported."""
    print("\nTesting trame_ribbon import...")
    
    try:
        import trame_ribbon
        
        # Verify key functions exist
        assert hasattr(trame_ribbon, 'load_hotspot_data'), "Missing load_hotspot_data"
        assert hasattr(trame_ribbon, 'extract_residue_info'), "Missing extract_residue_info"
        assert hasattr(trame_ribbon, 'build_vtk_pipeline'), "Missing build_vtk_pipeline"
        assert hasattr(trame_ribbon, 'pick_residue_at_position'), "Missing pick_residue_at_position"
        assert hasattr(trame_ribbon, 'calculate_distance'), "Missing calculate_distance"
        assert hasattr(trame_ribbon, 'calculate_angle'), "Missing calculate_angle"
        assert hasattr(trame_ribbon, 'add_hotspot_markers'), "Missing add_hotspot_markers"
        
        print("✓ trame_ribbon module imports successfully")
        print("✓ All required functions are present")
        return True
        
    except Exception as e:
        print(f"✗ Error importing trame_ribbon: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hotspot_loading_function():
    """Test the hotspot loading function."""
    print("\nTesting hotspot loading function...")
    
    try:
        import trame_ribbon
        
        # Call the function
        result = trame_ribbon.load_hotspot_data()
        
        if result:
            # Check that global hotspot_data was populated
            assert len(trame_ribbon.hotspot_data) > 0, "Hotspot data should be populated"
            print(f"✓ Loaded {len(trame_ribbon.hotspot_data)} hotspot values")
            
            # Check a sample value
            if "0" in trame_ribbon.hotspot_data:
                value = trame_ribbon.hotspot_data["0"]
                print(f"  Sample: Residue 0 hotspot = {value}")
            
            return True
        else:
            print("✗ load_hotspot_data returned False")
            return False
            
    except Exception as e:
        print(f"✗ Error testing hotspot loading: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_measurement_functions():
    """Test distance and angle calculation functions."""
    print("\nTesting measurement functions...")
    
    try:
        import trame_ribbon
        
        # Test distance calculation
        pos1 = (0.0, 0.0, 0.0)
        pos2 = (3.0, 4.0, 0.0)
        
        distance = trame_ribbon.calculate_distance(pos1, pos2)
        expected_distance = 5.0  # 3-4-5 triangle
        
        assert abs(distance - expected_distance) < 0.01, \
            f"Distance calculation incorrect: expected {expected_distance}, got {distance}"
        
        print(f"✓ Distance calculation: {distance:.2f} Å (expected {expected_distance})")
        
        # Test angle calculation
        pos1 = (1.0, 0.0, 0.0)
        pos2 = (0.0, 0.0, 0.0)
        pos3 = (0.0, 1.0, 0.0)
        
        angle = trame_ribbon.calculate_angle(pos1, pos2, pos3)
        expected_angle = 90.0  # Right angle
        
        assert abs(angle - expected_angle) < 0.01, \
            f"Angle calculation incorrect: expected {expected_angle}, got {angle}"
        
        print(f"✓ Angle calculation: {angle:.1f}° (expected {expected_angle}°)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing measurements: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vtk_imports():
    """Test that required VTK components are available."""
    print("\nTesting VTK imports...")
    
    try:
        import vtk
        
        # Test required VTK classes
        required_classes = [
            'vtkPDBReader',
            'vtkProteinRibbonFilter',
            'vtkPolyDataMapper',
            'vtkActor',
            'vtkRenderer',
            'vtkRenderWindow',
            'vtkCellPicker',
            'vtkSphereSource',
            'vtkUnsignedCharArray'
        ]
        
        for class_name in required_classes:
            assert hasattr(vtk, class_name), f"Missing VTK class: {class_name}"
        
        print(f"✓ All {len(required_classes)} required VTK classes available")
        return True
        
    except Exception as e:
        print(f"✗ Error with VTK imports: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Interactive Trame Ribbon Viewer")
    print("=" * 60)
    
    tests = [
        test_vtk_imports,
        test_pdb_files_available,
        test_hotspot_data_loading,
        test_trame_ribbon_import,
        test_hotspot_loading_function,
        test_measurement_functions,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ All tests passed! The interactive ribbon viewer is ready.")
        print("\nTo run the viewer:")
        print("  python trame_ribbon.py")
        print("\nThen open your browser to: http://localhost:8787")
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
