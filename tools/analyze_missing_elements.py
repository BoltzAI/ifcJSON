#!/usr/bin/env python3
"""
Analyze missing elements in IFC round-trip pipeline
This tool identifies which elements are lost during the pipeline and categorizes them by type.
"""

import ifcopenshell
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

def extract_element_info(ifc_file: ifcopenshell.file) -> Dict[str, Dict]:
    """Extract element information from IFC file"""
    elements = {}
    
    for element in ifc_file.by_type("IfcBuildingElement"):
        if hasattr(element, 'Name') and element.Name:
            element_name = element.Name
            
            # Check if element has hierarchical placement
            has_hierarchy = False
            placement_type = None
            if hasattr(element, 'ObjectPlacement') and element.ObjectPlacement:
                placement_type = element.ObjectPlacement.is_a()
                if hasattr(element.ObjectPlacement, 'PlacementRelTo') and element.ObjectPlacement.PlacementRelTo:
                    has_hierarchy = True
            
            elements[element_name] = {
                'type': element.is_a(),
                'has_hierarchy': has_hierarchy,
                'placement_type': placement_type,
                'global_id': element.GlobalId if hasattr(element, 'GlobalId') else None
            }
    
    return elements

def analyze_missing_elements(original_elements: Dict, roundtrip_elements: Dict) -> Dict:
    """Analyze missing elements and categorize them"""
    
    # Identify missing elements
    original_names = set(original_elements.keys())
    roundtrip_names = set(roundtrip_elements.keys())
    missing_names = original_names - roundtrip_names
    recovered_names = original_names & roundtrip_names
    
    # Categorize missing elements by type
    missing_by_type = defaultdict(lambda: {'total': 0, 'hierarchical': 0, 'elements': []})
    recovered_by_type = defaultdict(lambda: {'total': 0, 'hierarchical': 0, 'elements': []})
    
    for name in missing_names:
        elem_info = original_elements[name]
        elem_type = elem_info['type']
        
        missing_by_type[elem_type]['total'] += 1
        missing_by_type[elem_type]['elements'].append(name)
        if elem_info['has_hierarchy']:
            missing_by_type[elem_type]['hierarchical'] += 1
    
    for name in recovered_names:
        elem_info = original_elements[name]
        elem_type = elem_info['type']
        
        recovered_by_type[elem_type]['total'] += 1
        recovered_by_type[elem_type]['elements'].append(name)
        if elem_info['has_hierarchy']:
            recovered_by_type[elem_type]['hierarchical'] += 1
    
    return {
        'missing_by_type': dict(missing_by_type),
        'recovered_by_type': dict(recovered_by_type),
        'missing_names': missing_names,
        'recovered_names': recovered_names,
        'total_original': len(original_names),
        'total_missing': len(missing_names),
        'total_recovered': len(recovered_names)
    }

def print_analysis_results(analysis: Dict):
    """Print detailed analysis results"""
    
    print("📊 MISSING ELEMENTS ANALYSIS")
    print("=" * 60)
    
    print(f"📈 SUMMARY:")
    print(f"   Total elements in original: {analysis['total_original']}")
    print(f"   Recovered elements: {analysis['total_recovered']}")
    print(f"   Missing elements: {analysis['total_missing']}")
    print(f"   Recovery rate: {analysis['total_recovered']/analysis['total_original']*100:.1f}%")
    
    print(f"\n❌ MISSING ELEMENTS BY TYPE:")
    print("-" * 40)
    
    total_missing_hierarchical = 0
    for elem_type, info in sorted(analysis['missing_by_type'].items()):
        print(f"   {elem_type}:")
        print(f"      Total missing: {info['total']}")
        print(f"      Hierarchical: {info['hierarchical']}")
        print(f"      Elements: {', '.join(info['elements'][:5])}")
        if len(info['elements']) > 5:
            print(f"                ... and {len(info['elements'])-5} more")
        total_missing_hierarchical += info['hierarchical']
    
    print(f"\n✅ RECOVERED ELEMENTS BY TYPE:")
    print("-" * 40)
    
    total_recovered_hierarchical = 0
    for elem_type, info in sorted(analysis['recovered_by_type'].items()):
        print(f"   {elem_type}:")
        print(f"      Total recovered: {info['total']}")
        print(f"      Hierarchical: {info['hierarchical']}")
        print(f"      Elements: {', '.join(info['elements'][:3])}")
        if len(info['elements']) > 3:
            print(f"                ... and {len(info['elements'])-3} more")
        total_recovered_hierarchical += info['hierarchical']
    
    print(f"\n🔗 HIERARCHY ANALYSIS:")
    print("-" * 40)
    total_hierarchical = total_missing_hierarchical + total_recovered_hierarchical
    print(f"   Total hierarchical elements: {total_hierarchical}")
    print(f"   Recovered hierarchical: {total_recovered_hierarchical}")
    print(f"   Missing hierarchical: {total_missing_hierarchical}")
    print(f"   Current hierarchy rate: {total_recovered_hierarchical/analysis['total_original']*100:.1f}%")
    print(f"   Potential hierarchy rate: {total_hierarchical/analysis['total_original']*100:.1f}%")
    
    print(f"\n🎯 TODO #38.4 IMPACT ANALYSIS:")
    print("-" * 40)
    potential_hierarchy_pct = (total_hierarchical/analysis['total_original']*100)
    print(f"   Target: 60-70% hierarchy")
    print(f"   Current: {total_recovered_hierarchical/analysis['total_original']*100:.1f}%")
    print(f"   Potential with all elements: {potential_hierarchy_pct:.1f}%")
    
    if potential_hierarchy_pct >= 60:
        print(f"   ✅ TARGET ACHIEVABLE: Need to recover {total_missing_hierarchical} hierarchical elements")
        print(f"   📈 Element recovery would increase hierarchy by {total_missing_hierarchical/analysis['total_original']*100:.1f}%")
        
        # Show which element types are most important for hierarchy
        print(f"\n🎯 PRIORITY ELEMENT TYPES FOR RECOVERY:")
        hierarchy_impact = []
        for elem_type, info in analysis['missing_by_type'].items():
            if info['hierarchical'] > 0:
                hierarchy_impact.append((elem_type, info['hierarchical'], info['total']))
        
        hierarchy_impact.sort(key=lambda x: x[1], reverse=True)
        for elem_type, hierarchical, total in hierarchy_impact:
            print(f"   {elem_type}: {hierarchical} hierarchical ({hierarchical/total*100:.1f}% of type)")
    else:
        print(f"   ❌ TARGET NOT ACHIEVABLE: Even with all elements, max hierarchy is {potential_hierarchy_pct:.1f}%")

def main():
    parser = argparse.ArgumentParser(description="Analyze missing elements in IFC round-trip pipeline")
    parser.add_argument("original_ifc", help="Original IFC file path")
    parser.add_argument("roundtrip_ifc", help="Round-trip IFC file path")
    parser.add_argument("--detailed", action="store_true", help="Show detailed element lists")
    
    args = parser.parse_args()
    
    # Check if files exist
    if not Path(args.original_ifc).exists():
        print(f"❌ Original IFC file not found: {args.original_ifc}")
        sys.exit(1)
    
    if not Path(args.roundtrip_ifc).exists():
        print(f"❌ Round-trip IFC file not found: {args.roundtrip_ifc}")
        sys.exit(1)
    
    try:
        print(f"🔍 Analyzing missing elements...")
        print(f"   Original: {args.original_ifc}")
        print(f"   Roundtrip: {args.roundtrip_ifc}")
        
        # Load IFC files
        original_file = ifcopenshell.open(args.original_ifc)
        roundtrip_file = ifcopenshell.open(args.roundtrip_ifc)
        
        # Extract element information
        original_elements = extract_element_info(original_file)
        roundtrip_elements = extract_element_info(roundtrip_file)
        
        # Analyze missing elements
        analysis = analyze_missing_elements(original_elements, roundtrip_elements)
        
        # Print results
        print_analysis_results(analysis)
        
        if args.detailed:
            print(f"\n📋 DETAILED MISSING ELEMENTS LIST:")
            print("-" * 60)
            for name in sorted(analysis['missing_names']):
                elem_info = original_elements[name]
                hierarchy_str = "🔗" if elem_info['has_hierarchy'] else "📍"
                print(f"   {hierarchy_str} {name} ({elem_info['type']})")
        
    except Exception as e:
        print(f"❌ Error analyzing files: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()