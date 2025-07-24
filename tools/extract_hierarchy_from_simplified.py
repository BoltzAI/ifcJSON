#!/usr/bin/env python3
"""
Extract hierarchical placement information from simplified JSON format.
This tool parses step2 simplified JSON to extract placement hierarchy data.

Usage:
    python extract_hierarchy_from_simplified.py <simplified_json> <output_hierarchy_json>
    python extract_hierarchy_from_simplified.py simplified.json hierarchy.json
"""

import json
import sys
from pathlib import Path

def extract_placement_hierarchy(simplified_json_path, output_path=None):
    """Extract hierarchical placement information from simplified JSON"""
    
    print(f"🔍 Extracting hierarchy from simplified JSON: {simplified_json_path}")
    
    # Load simplified JSON
    with open(simplified_json_path, 'r') as f:
        data = json.load(f)
    
    results = {
        "source_file": simplified_json_path,
        "source_type": "simplified_json",
        "step": "step2",
        "elements": {},
        "hierarchy_summary": {
            "total_elements": 0,
            "elements_with_hierarchy": 0,
            "hierarchy_levels": {},
            "parent_placements": set()
        }
    }
    
    # Process all storeys
    for storey in data.get('building', {}).get('storeys', []):
        storey_name = storey.get('name', 'Unknown')
        elements = storey.get('elements', {})
        
        # Process all element types
        for element_type in ['walls', 'slabs', 'doors', 'windows', 'beams', 'columns', 'openings']:
            if element_type in elements and elements[element_type]:
                for element in elements[element_type]:
                    element_name = element.get('name', 'Unknown')
                    element_id = element.get('globalId', 'Unknown')
                    
                    results['hierarchy_summary']['total_elements'] += 1
                    
                    # Extract placement information
                    placement = element.get('placement', {})
                    
                    element_hierarchy = {
                        "element_name": element_name,
                        "element_id": element_id,
                        "element_type": element.get('type', element_type),
                        "storey": storey_name,
                        "placement": {
                            "location": placement.get('location', []),
                            "x_axis": placement.get('x_axis', []),
                            "z_axis": placement.get('z_axis', [])
                        },
                        "hierarchical_info": {}
                    }
                    
                    # Extract hierarchical placement fields
                    has_hierarchy = False
                    
                    if 'parent_placement' in placement:
                        element_hierarchy['hierarchical_info']['parent_placement'] = placement['parent_placement']
                        results['hierarchy_summary']['parent_placements'].add(placement['parent_placement'])
                        has_hierarchy = True
                    
                    if 'is_absolute' in placement:
                        element_hierarchy['hierarchical_info']['is_absolute'] = placement['is_absolute']
                        has_hierarchy = True
                    
                    if 'local_coordinates' in placement:
                        element_hierarchy['hierarchical_info']['local_coordinates'] = placement['local_coordinates']
                        has_hierarchy = True
                    
                    if 'placement_hierarchy_level' in placement:
                        level = placement['placement_hierarchy_level']
                        element_hierarchy['hierarchical_info']['placement_hierarchy_level'] = level
                        
                        # Track hierarchy levels
                        if level not in results['hierarchy_summary']['hierarchy_levels']:
                            results['hierarchy_summary']['hierarchy_levels'][level] = 0
                        results['hierarchy_summary']['hierarchy_levels'][level] += 1
                        has_hierarchy = True
                    
                    if has_hierarchy:
                        results['hierarchy_summary']['elements_with_hierarchy'] += 1
                        element_hierarchy['has_hierarchical_placement'] = True
                    else:
                        element_hierarchy['has_hierarchical_placement'] = False
                    
                    # Store element hierarchy
                    results['elements'][element_name] = element_hierarchy
    
    # Convert set to list for JSON serialization
    results['hierarchy_summary']['parent_placements'] = list(results['hierarchy_summary']['parent_placements'])
    
    # Print summary
    print(f"\n📊 HIERARCHY EXTRACTION SUMMARY:")
    print(f"   Total elements: {results['hierarchy_summary']['total_elements']}")
    print(f"   Elements with hierarchy: {results['hierarchy_summary']['elements_with_hierarchy']}")
    print(f"   Hierarchy levels: {results['hierarchy_summary']['hierarchy_levels']}")
    print(f"   Parent placements: {len(results['hierarchy_summary']['parent_placements'])}")
    
    # Show elements with hierarchy
    hierarchical_elements = [name for name, elem in results['elements'].items() 
                           if elem['has_hierarchical_placement']]
    
    print(f"\n🔗 ELEMENTS WITH HIERARCHICAL PLACEMENT:")
    for elem_name in sorted(hierarchical_elements):
        elem = results['elements'][elem_name]
        hierarchy = elem['hierarchical_info']
        print(f"   {elem_name}:")
        print(f"     Parent: {hierarchy.get('parent_placement', 'None')}")
        print(f"     Level: {hierarchy.get('placement_hierarchy_level', 'None')}")
        print(f"     Is Absolute: {hierarchy.get('is_absolute', 'None')}")
        print(f"     Local Coords: {hierarchy.get('local_coordinates', 'None')}")
    
    # Save results
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Hierarchy data saved to: {output_path}")
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_hierarchy_from_simplified.py <simplified_json> [output_hierarchy_json]")
        print("Example: python extract_hierarchy_from_simplified.py simplified.json hierarchy.json")
        sys.exit(1)
    
    simplified_json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(simplified_json_path).exists():
        print(f"❌ Simplified JSON file not found: {simplified_json_path}")
        sys.exit(1)
    
    try:
        results = extract_placement_hierarchy(simplified_json_path, output_path)
        
        if not output_path:
            # Print detailed results if no output file specified
            print(f"\n📋 DETAILED HIERARCHY STRUCTURE:")
            print("=" * 60)
            
            for elem_name, elem_data in sorted(results['elements'].items()):
                if elem_data['has_hierarchical_placement']:
                    hierarchy = elem_data['hierarchical_info']
                    print(f"\n{elem_name} ({elem_data['element_type']}):")
                    print(f"  Location: {elem_data['placement']['location']}")
                    print(f"  Parent: {hierarchy.get('parent_placement', 'None')}")
                    print(f"  Local Coords: {hierarchy.get('local_coordinates', 'None')}")
                    print(f"  Level: {hierarchy.get('placement_hierarchy_level', 'None')}")
                    print(f"  Is Absolute: {hierarchy.get('is_absolute', 'None')}")
        
        print(f"\n✅ Hierarchy extraction completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()