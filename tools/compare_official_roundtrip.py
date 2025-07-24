#!/usr/bin/env python3
"""
Compare placement hierarchy between original IFC and official round-trip IFC
"""

import ifcopenshell
import numpy as np
from typing import Dict, List, Tuple, Optional

def extract_placement_info(ifc_file: ifcopenshell.file) -> Dict[str, Dict]:
    """Extract placement information from IFC file"""
    results = {}
    
    for element in ifc_file.by_type("IfcBuildingElement"):
        if hasattr(element, 'Name') and element.Name:
            element_name = element.Name
            
            # Extract placement information
            placement_info = {
                'type': element.is_a(),
                'has_placement': False,
                'has_hierarchical_placement': False,
                'placement_type': None,
                'parent_placement': None,
                'position': None,
                'hierarchy_level': 0
            }
            
            if hasattr(element, 'ObjectPlacement') and element.ObjectPlacement:
                placement = element.ObjectPlacement
                placement_info['has_placement'] = True
                placement_info['placement_type'] = placement.is_a()
                
                if placement.is_a('IfcLocalPlacement'):
                    # Check for hierarchical placement
                    if hasattr(placement, 'PlacementRelTo') and placement.PlacementRelTo:
                        placement_info['has_hierarchical_placement'] = True
                        placement_info['parent_placement'] = str(placement.PlacementRelTo)
                        
                        # Count hierarchy levels
                        current = placement
                        level = 0
                        while hasattr(current, 'PlacementRelTo') and current.PlacementRelTo:
                            level += 1
                            current = current.PlacementRelTo
                        placement_info['hierarchy_level'] = level
                    
                    # Extract position
                    if hasattr(placement, 'RelativePlacement') and placement.RelativePlacement:
                        rel_placement = placement.RelativePlacement
                        if rel_placement.is_a('IfcAxis2Placement3D'):
                            if hasattr(rel_placement, 'Location') and rel_placement.Location:
                                location = rel_placement.Location
                                if hasattr(location, 'Coordinates'):
                                    placement_info['position'] = list(location.Coordinates)
            
            results[element_name] = placement_info
    
    return results

def compare_placements(original_info: Dict, roundtrip_info: Dict) -> Dict:
    """Compare placement information between two IFC files"""
    
    comparison = {
        'total_elements_original': len(original_info),
        'total_elements_roundtrip': len(roundtrip_info),
        'common_elements': 0,
        'placement_matches': 0,
        'hierarchy_matches': 0,
        'position_matches': 0,
        'mismatches': []
    }
    
    # Find common elements
    common_elements = set(original_info.keys()) & set(roundtrip_info.keys())
    comparison['common_elements'] = len(common_elements)
    
    for element_name in common_elements:
        orig = original_info[element_name]
        rt = roundtrip_info[element_name]
        
        # Check placement preservation
        if orig['has_placement'] == rt['has_placement']:
            comparison['placement_matches'] += 1
            
            # Check hierarchy preservation
            if orig['has_hierarchical_placement'] == rt['has_hierarchical_placement']:
                if orig['hierarchy_level'] == rt['hierarchy_level']:
                    comparison['hierarchy_matches'] += 1
            
            # Check position preservation
            if orig['position'] and rt['position']:
                if len(orig['position']) == len(rt['position']):
                    max_diff = max(abs(a - b) for a, b in zip(orig['position'], rt['position']))
                    if max_diff < 0.001:  # 1mm tolerance
                        comparison['position_matches'] += 1
                    else:
                        comparison['mismatches'].append({
                            'element': element_name,
                            'type': 'position',
                            'original': orig['position'],
                            'roundtrip': rt['position'],
                            'max_diff': max_diff
                        })
    
    return comparison

def main():
    # File paths
    original_ifc = "../../../ifc_files/OrangeHouse.ifc"
    roundtrip_ifc = "../../../out-official/ifc_outputs/OrangeHouse_roundtrip.ifc"
    
    print("🔍 Comparing Official Round-Trip Placement Hierarchy")
    print("=" * 60)
    print(f"Original:   {original_ifc}")
    print(f"Roundtrip:  {roundtrip_ifc}")
    print()
    
    # Open IFC files
    try:
        original = ifcopenshell.open(original_ifc)
        roundtrip = ifcopenshell.open(roundtrip_ifc)
    except Exception as e:
        print(f"❌ Error opening IFC files: {e}")
        return
    
    # Extract placement information
    print("📊 Extracting placement information...")
    original_info = extract_placement_info(original)
    roundtrip_info = extract_placement_info(roundtrip)
    
    # Compare placements
    comparison = compare_placements(original_info, roundtrip_info)
    
    # Print results
    print("\n📈 COMPARISON RESULTS:")
    print(f"   Elements in original:     {comparison['total_elements_original']}")
    print(f"   Elements in roundtrip:    {comparison['total_elements_roundtrip']}")
    print(f"   Common elements:          {comparison['common_elements']}")
    print()
    print(f"✅ Placement preservation:   {comparison['placement_matches']}/{comparison['common_elements']} ({100*comparison['placement_matches']/comparison['common_elements']:.1f}%)")
    print(f"✅ Hierarchy preservation:   {comparison['hierarchy_matches']}/{comparison['common_elements']} ({100*comparison['hierarchy_matches']/comparison['common_elements']:.1f}%)")
    print(f"✅ Position preservation:    {comparison['position_matches']}/{comparison['common_elements']} ({100*comparison['position_matches']/comparison['common_elements']:.1f}%)")
    
    # Show mismatches if any
    if comparison['mismatches']:
        print(f"\n⚠️  POSITION MISMATCHES: {len(comparison['mismatches'])}")
        for mismatch in comparison['mismatches'][:5]:  # Show first 5
            print(f"   {mismatch['element']}: max diff = {mismatch['max_diff']:.3f}")
            print(f"      Original:  {mismatch['original']}")
            print(f"      Roundtrip: {mismatch['roundtrip']}")
    
    # Check hierarchy details
    print("\n🔗 HIERARCHY ANALYSIS:")
    orig_hierarchical = sum(1 for e in original_info.values() if e['has_hierarchical_placement'])
    rt_hierarchical = sum(1 for e in roundtrip_info.values() if e['has_hierarchical_placement'])
    print(f"   Original hierarchical elements:   {orig_hierarchical}")
    print(f"   Roundtrip hierarchical elements:  {rt_hierarchical}")
    
    # Show hierarchy levels
    orig_levels = {}
    rt_levels = {}
    for info in original_info.values():
        level = info['hierarchy_level']
        orig_levels[level] = orig_levels.get(level, 0) + 1
    for info in roundtrip_info.values():
        level = info['hierarchy_level']
        rt_levels[level] = rt_levels.get(level, 0) + 1
    
    print(f"\n   Original hierarchy levels:  {dict(sorted(orig_levels.items()))}")
    print(f"   Roundtrip hierarchy levels: {dict(sorted(rt_levels.items()))}")
    
    # Final verdict
    print("\n🏁 FINAL VERDICT:")
    if (comparison['placement_matches'] == comparison['common_elements'] and
        comparison['hierarchy_matches'] == comparison['common_elements'] and
        comparison['position_matches'] == comparison['common_elements']):
        print("   ✅ PERFECT ROUND-TRIP: All placements, hierarchy, and positions preserved!")
    else:
        print("   ❌ IMPERFECT ROUND-TRIP: Some placement information was lost")

if __name__ == "__main__":
    main()