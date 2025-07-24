#!/usr/bin/env python3
"""
Extract hierarchical placement information from ifcJSON format.
This tool parses step1 or step3 ifcJSON to extract placement hierarchy data.

Usage:
    python extract_hierarchy_from_ifcjson.py <ifcjson_file> <output_hierarchy_json>
    python extract_hierarchy_from_ifcjson.py input.ifcjson hierarchy.json
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
        "placements": {},
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
    
    # First pass: Extract all placement entities (nested inline)
    placement_entities = {}
    placement_counter = 0
    
    def extract_nested_placements(obj, parent_key=""):
        nonlocal placement_counter
        if isinstance(obj, dict):
            if obj.get('type') == 'IfcLocalPlacement':
                placement_id = f"placement_{placement_counter}"
                placement_entities[placement_id] = obj
                placement_counter += 1
                return placement_id
            else:
                for key, value in obj.items():
                    extract_nested_placements(value, f"{parent_key}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                extract_nested_placements(item, f"{parent_key}[{i}]")
    
    # Extract nested placements from all entities
    for entity_id, entity in ifcjson_data.items():
        extract_nested_placements(entity, entity_id)
    
    print(f"📍 Found {len(placement_entities)} placement entities")
    
    # Second pass: Process placement hierarchy
    for placement_id, placement_entity in placement_entities.items():
        placement_info = {
            "placement_id": placement_id,
            "type": placement_entity.get('type', 'Unknown'),
            "parent_placement": None,
            "relative_placement": None,
            "hierarchy_level": 0,
            "local_data": {}
        }
        
        # Extract parent placement reference (nested structure)
        if 'placementRelTo' in placement_entity:
            parent_placement = placement_entity['placementRelTo']
            if parent_placement and parent_placement.get('type') == 'IfcLocalPlacement':
                placement_info['parent_placement'] = f"parent_of_{placement_id}"
                results['hierarchy_summary']['placement_references'] += 1
        
        # Extract relative placement (nested structure)
        if 'relativePlacement' in placement_entity:
            rel_placement = placement_entity['relativePlacement']
            if rel_placement and rel_placement.get('type') == 'IfcAxis2Placement3D':
                placement_info['relative_placement'] = f"relative_of_{placement_id}"
                
                # Extract location
                if 'location' in rel_placement:
                    location_entity = rel_placement['location']
                    if location_entity and location_entity.get('type') == 'IfcCartesianPoint':
                        if 'coordinates' in location_entity:
                            placement_info['local_data']['location'] = location_entity['coordinates']
                
                # Extract reference direction
                if 'refDirection' in rel_placement:
                    ref_dir_entity = rel_placement['refDirection']
                    if ref_dir_entity and ref_dir_entity.get('type') == 'IfcDirection':
                        if 'directionRatios' in ref_dir_entity:
                            placement_info['local_data']['ref_direction'] = ref_dir_entity['directionRatios']
                
                # Extract axis direction
                if 'axis' in rel_placement:
                    axis_entity = rel_placement['axis']
                    if axis_entity and axis_entity.get('type') == 'IfcDirection':
                        if 'directionRatios' in axis_entity:
                            placement_info['local_data']['axis'] = axis_entity['directionRatios']
        
        results['placements'][placement_id] = placement_info
    
    # Calculate hierarchy levels
    def calculate_hierarchy_level(placement_id, visited=None):
        if visited is None:
            visited = set()
        
        if placement_id in visited:
            return 0  # Circular reference
        
        visited.add(placement_id)
        
        placement = results['placements'].get(placement_id)
        if not placement:
            return 0
        
        parent_id = placement.get('parent_placement')
        if parent_id:
            return 1 + calculate_hierarchy_level(parent_id, visited.copy())
        else:
            return 0
    
    # Update hierarchy levels
    for placement_id in results['placements']:
        level = calculate_hierarchy_level(placement_id)
        results['placements'][placement_id]['hierarchy_level'] = level
        
        if level not in results['hierarchy_summary']['hierarchy_levels']:
            results['hierarchy_summary']['hierarchy_levels'][level] = 0
        results['hierarchy_summary']['hierarchy_levels'][level] += 1
    
    # Third pass: Find elements that use these placements
    for entity in ifcjson_data_list:
        entity_type = entity.get('type', '')
        entity_id = entity.get('globalId', '')
        
        # Check if this is a building element
        if any(element_type in entity_type for element_type in 
               ['IfcWall', 'IfcSlab', 'IfcDoor', 'IfcWindow', 'IfcBeam', 'IfcColumn', 'IfcOpening']):
            
            results['hierarchy_summary']['total_elements'] += 1
            
            element_info = {
                "element_id": entity_id,
                "element_type": entity_type,
                "element_name": entity.get('name', 'Unknown'),
                "placement_id": None,
                "placement_hierarchy": None,
                "has_hierarchical_placement": False
            }
            
            # Find placement reference (nested structure)
            if 'objectPlacement' in entity:
                placement_obj = entity['objectPlacement']
                if placement_obj and placement_obj.get('type') == 'IfcLocalPlacement':
                    # Extract coordinates directly from the element's immediate placement
                    immediate_coords = None
                    parent_placement = None
                    
                    # Get immediate placement coordinates
                    if 'relativePlacement' in placement_obj:
                        rel_placement = placement_obj['relativePlacement']
                        if rel_placement and rel_placement.get('type') == 'IfcAxis2Placement3D':
                            if 'location' in rel_placement:
                                location_entity = rel_placement['location']
                                if location_entity and location_entity.get('type') == 'IfcCartesianPoint':
                                    if 'coordinates' in location_entity:
                                        immediate_coords = location_entity['coordinates']
                    
                    # Get parent placement reference
                    if 'placementRelTo' in placement_obj:
                        parent_placement = placement_obj['placementRelTo']
                    
                    # Create element-specific placement info
                    element_placement = {
                        'type': 'IfcLocalPlacement',
                        'parent_placement': f"parent_of_{entity_id}" if parent_placement else None,
                        'relative_placement': f"relative_of_{entity_id}",
                        'hierarchy_level': 1 if parent_placement else 0,
                        'local_data': {
                            'location': immediate_coords if immediate_coords else [0.0, 0.0, 0.0]
                        }
                    }
                    
                    # Add reference direction and axis if available
                    if 'relativePlacement' in placement_obj:
                        rel_placement = placement_obj['relativePlacement']
                        if 'refDirection' in rel_placement:
                            ref_dir = rel_placement['refDirection']
                            if ref_dir and ref_dir.get('type') == 'IfcDirection':
                                if 'directionRatios' in ref_dir:
                                    element_placement['local_data']['ref_direction'] = ref_dir['directionRatios']
                        
                        if 'axis' in rel_placement:
                            axis = rel_placement['axis']
                            if axis and axis.get('type') == 'IfcDirection':
                                if 'directionRatios' in axis:
                                    element_placement['local_data']['axis'] = axis['directionRatios']
                    
                    # Store element placement
                    element_info['placement_id'] = f"placement_{entity_id}"
                    element_info['placement_hierarchy'] = element_placement
                    
                    # Check if this placement has hierarchical structure
                    if parent_placement:
                        element_info['has_hierarchical_placement'] = True
                        results['hierarchy_summary']['elements_with_placement'] += 1
            
            # Store element info with priority system for duplicate names
            element_key = element_info['element_name'] if element_info['element_name'] != 'Unknown' else entity_id
            
            # Priority system: IfcWindow > IfcDoor > IfcOpeningElement
            # Only overwrite if new element has higher priority
            should_store = True
            if element_key in results['elements']:
                existing_type = results['elements'][element_key]['element_type']
                new_type = element_info['element_type']
                
                # Define priority order (higher number = higher priority)
                type_priority = {
                    'IfcOpeningElement': 1,
                    'IfcDoor': 2,
                    'IfcWindow': 3
                }
                
                existing_priority = type_priority.get(existing_type, 0)
                new_priority = type_priority.get(new_type, 0)
                
                # Only store if new element has higher or equal priority
                should_store = new_priority >= existing_priority
                
                if not should_store:
                    print(f"   Skipping {new_type} '{element_key}' - {existing_type} has higher priority")
                else:
                    print(f"   Replacing {existing_type} '{element_key}' with {new_type} (higher priority)")
            
            if should_store:
                results['elements'][element_key] = element_info
    
    # Print summary
    print(f"\n📊 HIERARCHY EXTRACTION SUMMARY:")
    print(f"   Total elements: {results['hierarchy_summary']['total_elements']}")
    print(f"   Elements with hierarchical placement: {results['hierarchy_summary']['elements_with_placement']}")
    print(f"   Placement references: {results['hierarchy_summary']['placement_references']}")
    print(f"   Hierarchy levels: {results['hierarchy_summary']['hierarchy_levels']}")
    print(f"   Total placements: {len(results['placements'])}")
    
    # Show elements with hierarchy
    hierarchical_elements = [name for name, elem in results['elements'].items() 
                           if elem['has_hierarchical_placement']]
    
    print(f"\n🔗 ELEMENTS WITH HIERARCHICAL PLACEMENT:")
    for elem_name in sorted(hierarchical_elements):
        elem = results['elements'][elem_name]
        if elem['placement_hierarchy']:
            hierarchy = elem['placement_hierarchy']
            print(f"   {elem_name}:")
            print(f"     Placement ID: {elem['placement_id']}")
            print(f"     Parent: {hierarchy.get('parent_placement', 'None')}")
            print(f"     Level: {hierarchy.get('hierarchy_level', 0)}")
            print(f"     Location: {hierarchy.get('local_data', {}).get('location', 'None')}")
    
    # Save results
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Hierarchy data saved to: {output_path}")
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_hierarchy_from_ifcjson.py <ifcjson_file> [output_hierarchy_json]")
        print("Example: python extract_hierarchy_from_ifcjson.py input.ifcjson hierarchy.json")
        sys.exit(1)
    
    ifcjson_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(ifcjson_path).exists():
        print(f"❌ ifcJSON file not found: {ifcjson_path}")
        sys.exit(1)
    
    try:
        results = extract_placement_hierarchy_from_ifcjson(ifcjson_path, output_path)
        
        if not output_path:
            # Print detailed results if no output file specified
            print(f"\n📋 DETAILED HIERARCHY STRUCTURE:")
            print("=" * 60)
            
            for elem_name, elem_data in sorted(results['elements'].items()):
                if elem_data['has_hierarchical_placement']:
                    hierarchy = elem_data['placement_hierarchy']
                    print(f"\n{elem_name} ({elem_data['element_type']}):")
                    print(f"  Placement ID: {elem_data['placement_id']}")
                    print(f"  Parent: {hierarchy.get('parent_placement', 'None')}")
                    print(f"  Level: {hierarchy.get('hierarchy_level', 0)}")
                    print(f"  Location: {hierarchy.get('local_data', {}).get('location', 'None')}")
                    print(f"  Ref Direction: {hierarchy.get('local_data', {}).get('ref_direction', 'None')}")
                    print(f"  Axis: {hierarchy.get('local_data', {}).get('axis', 'None')}")
        
        print(f"\n✅ Hierarchy extraction completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()