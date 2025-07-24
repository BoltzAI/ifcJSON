#!/usr/bin/env python3
"""
Compare actual world positions between original IFC and round-trip IFC
This tool calculates the actual 3D world coordinates that affect visual geometry,
not just the local placement coordinates.
"""

import ifcopenshell
import ifcopenshell.util.placement
import numpy as np
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def get_world_position(element) -> Optional[List[float]]:
    """Get the actual world position of an element by traversing placement hierarchy"""
    try:
        if hasattr(element, 'ObjectPlacement') and element.ObjectPlacement:
            # Use ifcopenshell's built-in placement utility to get world matrix
            matrix = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
            # Extract translation from 4x4 transformation matrix
            if matrix is not None:
                return [matrix[0][3], matrix[1][3], matrix[2][3]]
    except Exception as e:
        print(f"Warning: Could not get world position for {element.Name}: {e}")
    return None

def extract_world_positions(ifc_file: ifcopenshell.file) -> Dict[str, Dict]:
    """Extract actual world positions from IFC file"""
    results = {}
    
    for element in ifc_file.by_type("IfcBuildingElement"):
        if hasattr(element, 'Name') and element.Name:
            element_name = element.Name
            
            element_info = {
                'type': element.is_a(),
                'world_position': get_world_position(element),
                'has_placement': False,
                'placement_type': None
            }
            
            if hasattr(element, 'ObjectPlacement') and element.ObjectPlacement:
                element_info['has_placement'] = True
                element_info['placement_type'] = element.ObjectPlacement.is_a()
            
            results[element_name] = element_info
    
    return results

def compare_world_positions(original_info: Dict, roundtrip_info: Dict) -> Dict:
    """Compare world positions between two IFC files"""
    
    comparison = {
        'total_elements_original': len(original_info),
        'total_elements_roundtrip': len(roundtrip_info),
        'common_elements': 0,
        'world_position_matches': 0,
        'mismatches': [],
        'tolerance': 0.001  # 1mm tolerance
    }
    
    # Find common elements
    common_elements = set(original_info.keys()) & set(roundtrip_info.keys())
    comparison['common_elements'] = len(common_elements)
    
    for element_name in common_elements:
        orig = original_info[element_name]
        rt = roundtrip_info[element_name]
        
        # Check world position preservation
        if orig['world_position'] and rt['world_position']:
            orig_pos = orig['world_position']
            rt_pos = rt['world_position']
            
            if len(orig_pos) == len(rt_pos) == 3:
                max_diff = max(abs(a - b) for a, b in zip(orig_pos, rt_pos))
                if max_diff < comparison['tolerance']:
                    comparison['world_position_matches'] += 1
                else:
                    comparison['mismatches'].append({
                        'element': element_name,
                        'type': element.is_a() if 'element' in locals() else orig['type'],
                        'original_world_pos': orig_pos,
                        'roundtrip_world_pos': rt_pos,
                        'max_diff': max_diff
                    })
    
    return comparison

def test_folder(folder_path: str, original_ifc: str, folder_name: str = None):
    """Test a specific output folder"""
    folder_path = Path(folder_path)
    if not folder_name:
        folder_name = folder_path.name
    
    # Derive roundtrip filename from original IFC filename
    original_ifc_path = Path(original_ifc)
    base_name = original_ifc_path.stem  # filename without extension
    roundtrip_filename = f"{base_name}_roundtrip.ifc"
    
    # Determine the roundtrip IFC path based on folder structure
    possible_paths = [
        folder_path / "ifc_outputs" / roundtrip_filename,  # batch_roundtrip_test_official.py structure
        folder_path / "step4_final_ifc" / roundtrip_filename,  # 4-step pipeline structure  
        folder_path / roundtrip_filename  # direct file
    ]
    
    roundtrip_path = None
    for path in possible_paths:
        if path.exists():
            roundtrip_path = path
            break
    
    if not roundtrip_path:
        print(f"❌ Could not find roundtrip IFC file in {folder_path}")
        print(f"   Looked for: {[str(p) for p in possible_paths]}")
        return None
    
    print(f"\n🔍 Testing {folder_name}:")
    print(f"Original:   {original_ifc}")
    print(f"Roundtrip:  {roundtrip_path}")
    
    try:
        # Open IFC files
        original = ifcopenshell.open(original_ifc)
        roundtrip = ifcopenshell.open(roundtrip_path)
        
        # Extract world positions
        print("📊 Extracting world positions...")
        original_info = extract_world_positions(original)
        roundtrip_info = extract_world_positions(roundtrip)
        
        # Compare world positions
        comparison = compare_world_positions(original_info, roundtrip_info)
        
        # Print results
        print(f"\n📈 WORLD POSITION RESULTS ({folder_name}):")
        print(f"   Elements in original:     {comparison['total_elements_original']}")
        print(f"   Elements in roundtrip:    {comparison['total_elements_roundtrip']}")
        print(f"   Common elements:          {comparison['common_elements']}")
        print(f"✅ World position matches:   {comparison['world_position_matches']}/{comparison['common_elements']} ({100*comparison['world_position_matches']/comparison['common_elements']:.1f}%)")
        
        # Show mismatches if any
        if comparison['mismatches']:
            print(f"\n⚠️  WORLD POSITION MISMATCHES: {len(comparison['mismatches'])}")
            for mismatch in comparison['mismatches'][:5]:  # Show first 5
                print(f"   {mismatch['element']}: max diff = {mismatch['max_diff']:.3f}")
                print(f"      Original:  {[round(x, 3) for x in mismatch['original_world_pos']]}")
                print(f"      Roundtrip: {[round(x, 3) for x in mismatch['roundtrip_world_pos']]}")
        
        # Visual quality assessment
        accuracy = 100 * comparison['world_position_matches'] / comparison['common_elements']
        print(f"\n🎨 VISUAL QUALITY ASSESSMENT ({folder_name}):")
        if accuracy >= 90:
            print(f"   ✅ EXCELLENT: {accuracy:.1f}% - Should look visually correct")
        elif accuracy >= 70:
            print(f"   ⚠️  GOOD: {accuracy:.1f}% - Should look mostly correct")
        elif accuracy >= 50:
            print(f"   ❌ POOR: {accuracy:.1f}% - Likely visual issues")
        else:
            print(f"   💥 BROKEN: {accuracy:.1f}% - Severe visual problems expected")
        
        return comparison
        
    except Exception as e:
        print(f"❌ Error testing {folder_name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Compare actual world positions between original IFC and round-trip IFC")
    parser.add_argument("folders", nargs="*", help="Output folders to test (if none specified, tests default folders)")
    parser.add_argument("--original", required=True, help="Original IFC file path")
    parser.add_argument("--all", action="store_true", help="Test all default folders plus any specified folders")
    
    args = parser.parse_args()
    
    print("🌍 Comparing Actual World Positions (Visual Geometry)")
    print("=" * 60)
    
    if not args.folders:
        print("❌ Error: No folders specified. Please provide at least one folder to test.")
        print("Usage: python compare_world_positions.py --original /path/to/original.ifc folder1 [folder2 ...]")
        sys.exit(1)
    
    # Test specified folders
    folders_to_test = [(Path(f).name, f) for f in args.folders]
    
    for folder_name, folder_path in folders_to_test:
        result = test_folder(folder_path, args.original, folder_name)
        if result is None:
            continue

if __name__ == "__main__":
    main()