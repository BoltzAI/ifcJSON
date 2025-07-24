#!/usr/bin/env python3
"""
Extract hierarchical placement information from ifcJSON format (FIXED for ref format).
This tool parses step1 or step3 ifcJSON to extract placement hierarchy data.
Fixed to handle both embedded entities and ref format.

Usage:
    python extract_hierarchy_from_ifcjson_fixed.py <ifcjson_file> <output_hierarchy_json>
"""

import json
import sys
from pathlib import Path

def extract_placement_hierarchy_from_ifcjson(ifcjson_path, output_path=None):
    """Extract hierarchical placement information from ifcJSON"""
    
    print(f"🔍 Extracting hierarchy from ifcJSON: {ifcjson_path}")
    
    # Load ifcJSON
    with open(ifcjson_path, 'r') as f:
        data = json.load(f)
    
    results = {
        "source_file": ifcjson_path,
        "source_type": "ifcjson",
        "step": "step1_or_step3",
        "elements": {},
        "hierarchy_summary": {
            "total_elements": 0,
            "elements_with_placement": 0,
            "placement_references": 0,
            "hierarchy_levels": {},
            "placement_types": {}
        }
    }
    
    # Get the data section
    ifcjson_data_list = data.get('data', [])
    
    # Convert data list to dictionary for easier lookup
    ifcjson_data = {}
    for entity in ifcjson_data_list:
        if 'globalId' in entity:
            ifcjson_data[entity['globalId']] = entity
    
    print(f"📍 Found {len(ifcjson_data)} entities in ifcJSON")
    
    # Helper function to resolve references
    def resolve_ref(ref_obj):
        """Resolve a reference object to the actual entity"""
        if isinstance(ref_obj, dict):
            if 'ref' in ref_obj:
                # Reference format: {"ref": "entity_id"}
                ref_id = ref_obj['ref']
                return ifcjson_data.get(ref_id)
            elif 'globalId' in ref_obj:
                # Direct entity
                return ref_obj
        return None
    
    # Find all building elements with placement
    element_types = ['IfcWall', 'IfcWallStandardCase', 'IfcWindow', 'IfcDoor', 'IfcSlab', 'IfcBeam', 'IfcColumn']
    
    for entity_id, entity in ifcjson_data.items():
        entity_type = entity.get('type', '')
        
        if any(element_type in entity_type for element_type in element_types):
            element_name = entity.get('name', 'Unknown')
            
            # Skip openings in favor of doors/windows
            if 'IfcOpeningElement' in entity_type:
                continue
            
            print(f"   Processing element: {element_name} ({entity_type})")
            
            # Check if element has placement
            object_placement = entity.get('objectPlacement')
            if not object_placement:
                print(f"   ⚠️  No objectPlacement found for {element_name}")
                continue
            
            # Resolve the placement entity
            placement_entity = resolve_ref(object_placement)
            if not placement_entity:
                print(f"   ❌ Could not resolve placement for {element_name}")
                continue
            
            placement_id = placement_entity.get('globalId')
            placement_type = placement_entity.get('type', 'Unknown')
            
            print(f"   Found placement: {placement_id} ({placement_type})")
            
            # Analyze placement hierarchy
            hierarchy_info = {
                "type": placement_type,
                "parent_placement": None,
                "relative_placement": None,
                "hierarchy_level": 0,
                "local_data": {}
            }
            
            # Check for parent placement (PlacementRelTo)
            if placement_type == 'IfcLocalPlacement':
                placement_rel_to = placement_entity.get('PlacementRelTo') or placement_entity.get('placementRelTo')
                if placement_rel_to:
                    parent_entity = resolve_ref(placement_rel_to)
                    if parent_entity:
                        hierarchy_info['parent_placement'] = parent_entity.get('globalId')
                        hierarchy_info['hierarchy_level'] = 1
                        results['hierarchy_summary']['placement_references'] += 1
                        print(f"   ✅ Found parent placement: {hierarchy_info['parent_placement']}")
                    else:
                        print(f"   ⚠️  Could not resolve parent placement reference")
                
                # Extract relative placement data
                relative_placement = placement_entity.get('RelativePlacement') or placement_entity.get('relativePlacement')
                if relative_placement:
                    rel_entity = resolve_ref(relative_placement)
                    if rel_entity and rel_entity.get('type') == 'IfcAxis2Placement3D':
                        hierarchy_info['relative_placement'] = rel_entity.get('globalId')
                        
                        # Extract location
                        location_ref = rel_entity.get('Location') or rel_entity.get('location')
                        if location_ref:
                            location_entity = resolve_ref(location_ref)
                            if location_entity and location_entity.get('type') == 'IfcCartesianPoint':
                                coordinates = location_entity.get('Coordinates') or location_entity.get('coordinates')
                                if coordinates:
                                    hierarchy_info['local_data']['location'] = coordinates
                                    print(f"   📍 Local coordinates: {coordinates}")
                        
                        # Extract reference direction
                        ref_dir_ref = rel_entity.get('RefDirection') or rel_entity.get('refDirection')
                        if ref_dir_ref:
                            ref_dir_entity = resolve_ref(ref_dir_ref)
                            if ref_dir_entity and ref_dir_entity.get('type') == 'IfcDirection':
                                dir_ratios = ref_dir_entity.get('DirectionRatios') or ref_dir_entity.get('directionRatios')
                                if dir_ratios:
                                    hierarchy_info['local_data']['ref_direction'] = dir_ratios
                        
                        # Extract axis direction
                        axis_ref = rel_entity.get('Axis') or rel_entity.get('axis')
                        if axis_ref:
                            axis_entity = resolve_ref(axis_ref)
                            if axis_entity and axis_entity.get('type') == 'IfcDirection':
                                dir_ratios = axis_entity.get('DirectionRatios') or axis_entity.get('directionRatios')
                                if dir_ratios:
                                    hierarchy_info['local_data']['axis'] = dir_ratios
            
            # Store element info
            element_info = {
                "element_id": entity_id,
                "element_type": entity_type,
                "element_name": element_name,
                "placement_id": placement_id,
                "placement_hierarchy": hierarchy_info,
                "has_hierarchical_placement": bool(hierarchy_info.get('parent_placement'))
            }
            
            results['elements'][element_name] = element_info
            results['hierarchy_summary']['total_elements'] += 1
            if hierarchy_info.get('parent_placement'):
                results['hierarchy_summary']['elements_with_placement'] += 1
    
    # Calculate hierarchy level distribution
    hierarchy_levels = {}
    for element_name, element_info in results['elements'].items():
        level = element_info['placement_hierarchy']['hierarchy_level']
        hierarchy_levels[level] = hierarchy_levels.get(level, 0) + 1
    
    results['hierarchy_summary']['hierarchy_levels'] = hierarchy_levels
    
    # Print summary
    print(f"\n📊 HIERARCHY EXTRACTION SUMMARY:")
    print(f"   Total elements: {results['hierarchy_summary']['total_elements']}")
    print(f"   Elements with hierarchical placement: {results['hierarchy_summary']['elements_with_placement']}")
    print(f"   Placement references: {results['hierarchy_summary']['placement_references']}")
    print(f"   Hierarchy levels: {hierarchy_levels}")
    
    # Print hierarchical elements
    hierarchical_elements = [
        (name, info) for name, info in results['elements'].items() 
        if info['has_hierarchical_placement']
    ]
    
    if hierarchical_elements:
        print(f"\n🔗 ELEMENTS WITH HIERARCHICAL PLACEMENT:")
        for element_name, element_info in hierarchical_elements:
            parent_id = element_info['placement_hierarchy']['parent_placement']
            local_coords = element_info['placement_hierarchy']['local_data'].get('location', 'N/A')
            print(f"   {element_name} → Parent: {parent_id}, Local: {local_coords}")
    else:
        print(f"\n🔗 No elements with hierarchical placement found")
    
    # Save results
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Hierarchy data saved to: {output_path}")
    
    print(f"\n✅ Hierarchy extraction completed successfully!")
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_hierarchy_from_ifcjson_fixed.py <ifcjson_file> [output_json]")
        sys.exit(1)
    
    ifcjson_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(ifcjson_file).exists():
        print(f"❌ Input file does not exist: {ifcjson_file}")
        sys.exit(1)
    
    extract_placement_hierarchy_from_ifcjson(ifcjson_file, output_file)

if __name__ == "__main__":
    main()