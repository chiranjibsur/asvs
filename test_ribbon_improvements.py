#!/usr/bin/env python
"""
Test script for ribbon visualization improvements.
Validates that secondary structure computation and enhanced ribbon geometry work correctly.
"""

import json
import math
from app import app
from trajectory_adapter import get_adapter

def test_secondary_structure_api():
    """Test that secondary structure API endpoint works correctly."""
    print("Testing secondary structure API endpoint...")
    
    client = app.test_client()
    response = client.get('/api/trajectory/secondary_structure/0')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.get_json()
    assert 'frame' in data, "Response missing 'frame' field"
    assert 'residues' in data, "Response missing 'residues' field"
    assert data['frame'] == 0, f"Expected frame 0, got {data['frame']}"
    
    residues = data['residues']
    assert len(residues) > 0, "No residues in response"
    
    # Validate structure of residue data
    for r in residues[:5]:  # Check first 5
        assert 'index' in r, "Residue missing 'index'"
        assert 'resnum' in r, "Residue missing 'resnum'"
        assert 'resname' in r, "Residue missing 'resname'"
        assert 'ss' in r, "Residue missing 'ss'"
        assert r['ss'] in ['H', 'E', 'C'], f"Invalid SS type: {r['ss']}"
    
    print(f"✓ Secondary structure API works correctly ({len(residues)} residues)")
    return True

def test_backbone_api():
    """Test that backbone atoms API endpoint works correctly."""
    print("\nTesting backbone atoms API endpoint...")
    
    client = app.test_client()
    response = client.get('/api/trajectory/backbone/0')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.get_json()
    assert 'frame' in data, "Response missing 'frame' field"
    assert 'residues' in data, "Response missing 'residues' field"
    
    residues = data['residues']
    assert len(residues) > 0, "No residues in response"
    
    # Validate structure of backbone data
    for r in residues[:5]:  # Check first 5
        assert 'index' in r, "Residue missing 'index'"
        assert 'resnum' in r, "Residue missing 'resnum'"
        assert 'resname' in r, "Residue missing 'resname'"
        assert 'N' in r, "Residue missing 'N'"
        assert 'CA' in r, "Residue missing 'CA'"
        assert 'C' in r, "Residue missing 'C'"
    
    print(f"✓ Backbone atoms API works correctly ({len(residues)} residues)")
    return True

def test_backbone_reconstruction():
    """Test that backbone atoms are reconstructed when only CA is available."""
    print("\nTesting backbone reconstruction from CA-only topology...")
    
    adapter = get_adapter()
    backbone = adapter.get_backbone_atoms(0)
    
    assert len(backbone) > 0, "No backbone data"
    
    # Count how many residues have reconstructed N, CA, and C positions
    has_n = sum(1 for r in backbone if r.get('N') is not None)
    has_ca = sum(1 for r in backbone if r.get('CA') is not None)
    has_c = sum(1 for r in backbone if r.get('C') is not None)
    
    total = len(backbone)
    print(f"  Total residues: {total}")
    print(f"  With N position: {has_n} ({100*has_n/total:.1f}%)")
    print(f"  With CA position: {has_ca} ({100*has_ca/total:.1f}%)")
    print(f"  With C position: {has_c} ({100*has_c/total:.1f}%)")
    
    # All residues should have CA since we have CA-only topology
    assert has_ca == total, f"Expected all residues to have CA, got {has_ca}"
    
    # Check if N and C were reconstructed (they should be for CA-only topology)
    # Note: The topology may be CA-only, so reconstruction should provide N and C
    assert has_n >= total * 0.9, f"Expected N positions for most residues, got {has_n}"
    assert has_c >= total * 0.9, f"Expected C positions for most residues, got {has_c}"
    
    # Verify the reconstructed positions are reasonable
    # N should be "behind" CA and C should be "ahead" along backbone
    for i, r in enumerate(backbone[:10]):  # Check first 10
        if r['N'] and r['CA'] and r['C']:
            n = r['N']
            ca = r['CA']
            c = r['C']
            
            # Calculate N-CA and CA-C distances
            n_ca_dist = math.sqrt(sum((n[j]-ca[j])**2 for j in range(3)))
            ca_c_dist = math.sqrt(sum((ca[j]-c[j])**2 for j in range(3)))
            
            # Standard bond lengths: N-CA ~1.47Å, CA-C ~1.52Å
            assert 1.2 < n_ca_dist < 1.8, f"N-CA distance {n_ca_dist:.2f} out of range for residue {i}"
            assert 1.3 < ca_c_dist < 1.8, f"CA-C distance {ca_c_dist:.2f} out of range for residue {i}"
    
    print("✓ Backbone reconstruction produces valid positions")
    return True

def test_adapter_secondary_structure():
    """Test that adapter's secondary structure computation works."""
    print("\nTesting adapter secondary structure computation...")
    
    adapter = get_adapter()
    ss_data = adapter.get_secondary_structure(0)
    
    assert len(ss_data) > 0, "No secondary structure data"
    
    # Count SS types
    ss_counts = {'H': 0, 'E': 0, 'C': 0}
    for r in ss_data:
        assert 'ss' in r, "Missing 'ss' field"
        assert r['ss'] in ss_counts, f"Invalid SS type: {r['ss']}"
        ss_counts[r['ss']] += 1
    
    total = sum(ss_counts.values())
    print(f"✓ Secondary structure computed for {total} residues")
    print(f"  Distribution: Helix={ss_counts['H']}, Sheet={ss_counts['E']}, Coil={ss_counts['C']}")
    
    return True

def test_frame_consistency():
    """Test that data is consistent across frames."""
    print("\nTesting frame consistency...")
    
    adapter = get_adapter()
    meta = adapter.get_meta()
    n_frames = meta['n_frames']
    n_residues = meta['n_residues']
    
    print(f"  Total frames: {n_frames}")
    print(f"  Total residues: {n_residues}")
    
    # Test a few random frames
    test_frames = [0, n_frames // 4, n_frames // 2, n_frames - 1]
    
    for frame in test_frames:
        ca_data = adapter.get_ca_xyz(frame)
        ss_data = adapter.get_secondary_structure(frame)
        
        assert len(ca_data) == n_residues, f"Frame {frame}: CA count mismatch"
        assert len(ss_data) == n_residues, f"Frame {frame}: SS count mismatch"
    
    print(f"✓ Data is consistent across frames")
    return True

def test_spline_js_exists():
    """Test that spline.js utility file exists and can be accessed."""
    print("\nTesting spline.js utility...")
    
    client = app.test_client()
    response = client.get('/static/js/utils/spline.js')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    content = response.data.decode('utf-8')
    assert 'computeRotationMinimizingFrames' in content, "Missing RMF function"
    assert 'createRibbonGeometry' in content, "Missing ribbon geometry function"
    assert 'SplineUtils' in content, "Missing SplineUtils export"
    
    print("✓ Spline utility file is accessible and contains required functions")
    return True

def test_atoms_full_api():
    """Test that atoms_full API endpoint works correctly."""
    print("\nTesting atoms_full API endpoint...")
    
    client = app.test_client()
    response = client.get('/api/trajectory/atoms_full/0')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.get_json()
    assert 'frame' in data, "Response missing 'frame' field"
    assert 'atoms' in data, "Response missing 'atoms' field"
    assert 'has_full_backbone' in data, "Response missing 'has_full_backbone' field"
    
    atoms = data['atoms']
    assert len(atoms) > 0, "No atoms in response"
    
    # Validate structure of atom data
    for a in atoms[:5]:  # Check first 5
        assert 'index' in a, "Atom missing 'index'"
        assert 'element' in a, "Atom missing 'element'"
        assert 'name' in a, "Atom missing 'name'"
        assert 'resnum' in a, "Atom missing 'resnum'"
        assert 'backbone_type' in a, "Atom missing 'backbone_type'"
        assert 'position' in a, "Atom missing 'position'"
        assert len(a['position']) == 3, "Position should have 3 coordinates"
        assert a['backbone_type'] in ['backbone', 'sidechain'], f"Invalid backbone_type: {a['backbone_type']}"
    
    print(f"✓ Atoms full API works correctly ({len(atoms)} atoms)")
    print(f"  Has full backbone: {data['has_full_backbone']}")
    return True

def test_meta_includes_backbone_flag():
    """Test that meta API includes has_full_backbone flag."""
    print("\nTesting meta API includes backbone flag...")
    
    client = app.test_client()
    response = client.get('/api/trajectory/meta')
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.get_json()
    assert 'has_full_backbone' in data, "Meta missing 'has_full_backbone' field"
    
    print(f"✓ Meta API includes backbone flag: {data['has_full_backbone']}")
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Ribbon Visualization Improvements")
    print("=" * 60)
    
    tests = [
        test_secondary_structure_api,
        test_backbone_api,
        test_backbone_reconstruction,
        test_adapter_secondary_structure,
        test_frame_consistency,
        test_spline_js_exists,
        test_atoms_full_api,
        test_meta_includes_backbone_flag,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
