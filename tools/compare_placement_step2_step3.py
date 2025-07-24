#!/usr/bin/env python3
"""
Compare Placement Structures Between Step 2 and Step 3

This script tracks specific elements by ID to compare how placement structures
change from simplified JSON (Step 2) to expanded JSON (Step 3).
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load JSON file with error handling"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        sys.exit(1)


def extract_step2_placement_info(step2_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract placement info from Step 2 simplified JSON"""
    placements = {}
    
    # Navigate to storeys and elements
    for storey in step2_data.get('building', {}).get('storeys', []):
        storey_id = storey.get('globalId')  # Use globalId instead of storey_id
        storey_name = storey.get('name')
        elements = storey.get('elements', {})
        
        # Check all element types
        for element_type in ['walls', 'windows', 'doors', 'slabs', 'beams', 'columns']:
            if element_type in elements:
                for element in elements[element_type]:
                    element_id = element.get('globalId')  # Use globalId instead of element_id
                    element_name = element.get('name')    # Use name instead of element_name
                    
                    placement = element.get('placement', {})
                    # Check for hierarchical placement by looking for parent_placement
                    has_hierarchical = bool(placement.get('parent_placement'))
                    
                    placement_info = {
                        'element_name': element_name,
                        'element_id': element_id,
                        'element_type': element_type,
                        'storey_id': storey_id,
                        'storey_name': storey_name,
                        'placement': placement,
                        'has_hierarchical_placement': has_hierarchical
                    }
                    
                    placements[element_id] = placement_info
    
    return placements


def find_element_in_step3(step3_data: Dict[str, Any], element_id: str) -> Optional[Dict[str, Any]]:
    """Find element by ID in Step 3 expanded JSON"""
    
    # Step 3 has entities in data array
    entities = step3_data.get('data', [])
    
    for entity in entities:
        if entity.get('globalId') == element_id:
            return entity
    
    return None


def find_placement_in_step3(step3_data: Dict[str, Any], placement_id: str) -> Optional[Dict[str, Any]]:
    """Find placement entity by ID in Step 3 expanded JSON"""
    
    entities = step3_data.get('data', [])
    
    for entity in entities:
        if entity.get('globalId') == placement_id:
            return entity
    
    return None


def analyze_placement_hierarchy(step3_data: Dict[str, Any], placement_entity: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze placement hierarchy in Step 3"""
    
    analysis = {
        'placement_type': placement_entity.get('type'),
        'has_parent': False,
        'parent_placement_id': None,
        'local_coordinates': None,
        'hierarchy_chain': []
    }
    
    # Check if it's IfcLocalPlacement
    if placement_entity.get('type') == 'IfcLocalPlacement':
        # Check for parent placement
        placement_rel_to = placement_entity.get('placementRelTo')
        if placement_rel_to:
            analysis['has_parent'] = True
            analysis['parent_placement_id'] = placement_rel_to.get('globalId')
        
        # Extract local coordinates from relativePlacement
        relative_placement = placement_entity.get('relativePlacement')
        if relative_placement:
            if isinstance(relative_placement, dict):
                # Direct embedded entity
                location = relative_placement.get('location')
                if location and isinstance(location, dict):
                    coordinates = location.get('coordinates')
                    if coordinates:
                        analysis['local_coordinates'] = coordinates
            else:
                # Reference to another entity - need to resolve
                rel_placement_entity = find_placement_in_step3(step3_data, relative_placement.get('globalId'))
                if rel_placement_entity:
                    location = rel_placement_entity.get('location')
                    if location and isinstance(location, dict):
                        coordinates = location.get('coordinates')
                        if coordinates:
                            analysis['local_coordinates'] = coordinates
    
    return analysis


def compare_individual_placement(element_id: str, step2_info: Dict[str, Any], step3_data: Dict[str, Any]):
    """Compare placement for a single element between Step 2 and Step 3"""
    
    print(f"\n🔍 COMPARING ELEMENT: {step2_info['element_name']} ({element_id})")
    print(f"   Element Type: {step2_info['element_type']}")
    print(f"   Storey: {step2_info['storey_name']}")
    
    # Step 2 Analysis
    print(f"\n📋 STEP 2 (Simplified JSON):")
    print(f"   Has Hierarchical Placement: {step2_info['has_hierarchical_placement']}")
    
    if step2_info['placement']:
        placement = step2_info['placement']
        print(f"   World Position: {placement.get('location')}")
        print(f"   X-Axis: {placement.get('x_axis')}")
        print(f"   Z-Axis: {placement.get('z_axis')}")
        
        if step2_info['has_hierarchical_placement']:
            print(f"   Parent Placement: {placement.get('parent_placement')}")
            print(f"   Local Coordinates: {placement.get('local_coordinates')}")
            print(f"   Parent Location: {placement.get('parent_location')}")
            print(f"   Parent X-Axis: {placement.get('parent_x_axis')}")
            print(f"   Parent Z-Axis: {placement.get('parent_z_axis')}")
    
    # Step 3 Analysis
    print(f"\n📋 STEP 3 (Expanded JSON):")
    
    # Find the element in Step 3
    step3_element = find_element_in_step3(step3_data, element_id)
    
    if not step3_element:
        print(f"   ❌ Element not found in Step 3!")
        return
    
    # Find the placement
    object_placement = step3_element.get('objectPlacement')
    if not object_placement:
        print(f"   ❌ No objectPlacement found!")
        return
    
    placement_id = object_placement.get('globalId')
    print(f"   Placement ID: {placement_id}")
    
    # Find the placement entity
    placement_entity = find_placement_in_step3(step3_data, placement_id)
    if not placement_entity:
        print(f"   ❌ Placement entity not found!")
        return
    
    # Analyze the placement hierarchy
    hierarchy_analysis = analyze_placement_hierarchy(step3_data, placement_entity)
    
    print(f"   Placement Type: {hierarchy_analysis['placement_type']}")
    print(f"   Has Parent: {hierarchy_analysis['has_parent']}")
    print(f"   Parent Placement ID: {hierarchy_analysis['parent_placement_id']}")
    print(f"   Local Coordinates: {hierarchy_analysis['local_coordinates']}")
    
    # Comparison Summary
    print(f"\n📊 COMPARISON SUMMARY:")
    step2_has_hierarchy = step2_info['has_hierarchical_placement']
    step3_has_hierarchy = hierarchy_analysis['has_parent']
    
    if step2_has_hierarchy and step3_has_hierarchy:
        print(f"   ✅ Hierarchy preserved: Step 2 → Step 3")
    elif step2_has_hierarchy and not step3_has_hierarchy:
        print(f"   ❌ Hierarchy lost: Step 2 had hierarchy, Step 3 is flat")
    elif not step2_has_hierarchy and step3_has_hierarchy:
        print(f"   ⚠️  Hierarchy added: Step 2 was flat, Step 3 has hierarchy")
    else:
        print(f"   ➡️  No hierarchy in either step")
    
    # Compare coordinates
    step2_coords = step2_info.get('placement', {}).get('local_coordinates') if step2_info.get('has_hierarchical_placement') else None
    step3_coords = hierarchy_analysis.get('local_coordinates')
    
    if step2_coords and step3_coords:
        print(f"   Step 2 Local Coords: {step2_coords}")
        print(f"   Step 3 Local Coords: {step3_coords}")
        if step2_coords == step3_coords:
            print(f"   ✅ Local coordinates match")
        else:
            print(f"   ❌ Local coordinates differ")
    elif step2_coords and not step3_coords:
        print(f"   ❌ Step 2 has local coords ({step2_coords}), Step 3 has none")
    elif not step2_coords and step3_coords:
        print(f"   ⚠️  Step 2 has no local coords, Step 3 has ({step3_coords})")


def main():
    if len(sys.argv) != 3:
        print("Usage: python compare_placement_step2_step3.py <step2_simplified.json> <step3_expanded.json>")
        sys.exit(1)
    
    step2_file = sys.argv[1]
    step3_file = sys.argv[2]
    
    print(f"🔍 Comparing placements between Step 2 and Step 3:")
    print(f"   Step 2: {step2_file}")
    print(f"   Step 3: {step3_file}")
    
    # Load files
    step2_data = load_json_file(step2_file)
    step3_data = load_json_file(step3_file)
    
    # Extract Step 2 placement info
    step2_placements = extract_step2_placement_info(step2_data)
    
    print(f"\n📊 Found {len(step2_placements)} elements in Step 2")
    
    # Filter to elements with hierarchical placement
    hierarchical_elements = {
        element_id: info for element_id, info in step2_placements.items() 
        if info['has_hierarchical_placement']
    }
    
    print(f"📊 Found {len(hierarchical_elements)} elements with hierarchical placement in Step 2")
    
    if not hierarchical_elements:
        print("❌ No hierarchical elements found in Step 2!")
        return
    
    # Compare first few elements in detail
    print(f"\n🔍 Analyzing first 3 hierarchical elements:")
    
    for i, (element_id, element_info) in enumerate(hierarchical_elements.items()):
        if i >= 3:  # Limit to first 3 for detailed analysis
            break
            
        compare_individual_placement(element_id, element_info, step3_data)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total elements analyzed: {min(3, len(hierarchical_elements))}")
    print(f"   Remaining hierarchical elements: {len(hierarchical_elements) - min(3, len(hierarchical_elements))}")


if __name__ == "__main__":
    main()