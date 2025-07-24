#!/usr/bin/env python3
"""
Representation Type Analyzer

Shows WHICH specific representations (Body-Brep, Body-SweptSolid, etc.) are present 
for elements in ifcJSON files. Useful for understanding representation structure
and identifying which geometry types are available.
"""

import json
import sys
from typing import Dict, List, Any, Optional

def load_json_data(file_path: str) -> Dict[str, Any]:
    """Load JSON data from file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error loading JSON file: {e}")
        sys.exit(1)

def find_element_by_name(entities: List[Dict], element_name: str) -> Optional[Dict[str, Any]]:
    """Find element by name in entities list"""
    for entity in entities:
        if entity.get('name') == element_name:
            return entity
    return None

def find_entity_by_id(entities: List[Dict], entity_id: str) -> Optional[Dict[str, Any]]:
    """Find entity by globalId in entities list"""
    for entity in entities:
        if entity.get('globalId') == entity_id:
            return entity
    return None

def analyze_shape_representation(entities: List[Dict], shape_rep: Dict[str, Any], entity_lookup: Dict[str, Dict]) -> Dict[str, Any]:
    """Analyze a single shape representation"""
    
    # Get representation details
    rep_id = shape_rep.get('globalId', 'unknown')
    rep_identifier = shape_rep.get('representationIdentifier', 'unknown')
    rep_type = shape_rep.get('representationType', 'unknown')
    items = shape_rep.get('items', [])
    
    # Analyze items in this representation
    geometry_types = []
    item_count = len(items)
    complex_geometry = False
    face_count = 0
    
    for item in items:
        if isinstance(item, dict):
            if 'ref' in item:
                # Referenced item
                referenced_entity = entity_lookup.get(item['ref'])
                if referenced_entity:
                    item_type = referenced_entity.get('type', 'unknown')
                    geometry_types.append(item_type)
                    
                    # Check for complex geometry
                    if item_type == 'IfcFacetedBrep':
                        complex_geometry = True
                        face_count += count_faceted_brep_faces(referenced_entity, entity_lookup)
                    elif item_type == 'IfcBooleanClippingResult':
                        complex_geometry = True
                else:
                    geometry_types.append(f"ref:{item['ref']} (not found)")
            elif item.get('type'):
                # Inline item
                item_type = item.get('type')
                geometry_types.append(item_type)
                
                if item_type == 'IfcFacetedBrep':
                    complex_geometry = True
                    face_count += count_faceted_brep_faces(item, entity_lookup)
                elif item_type == 'IfcBooleanClippingResult':
                    complex_geometry = True
    
    return {
        'id': rep_id,
        'identifier': rep_identifier,
        'type': rep_type,
        'item_count': item_count,
        'geometry_types': geometry_types,
        'complex_geometry': complex_geometry,
        'face_count': face_count
    }

def count_faceted_brep_faces(brep_entity: Dict[str, Any], entity_lookup: Dict[str, Dict]) -> int:
    """Count faces in an IfcFacetedBrep entity"""
    
    outer = brep_entity.get('outer', {})
    
    if isinstance(outer, dict):
        if 'ref' in outer:
            # Referenced shell
            shell_entity = entity_lookup.get(outer['ref'])
            if shell_entity and shell_entity.get('type') == 'IfcClosedShell':
                return len(shell_entity.get('cfsFaces', []))
        elif outer.get('type') == 'IfcClosedShell':
            # Inline shell
            return len(outer.get('cfsFaces', []))
    
    return 0

def analyze_element_representations(file_path: str, element_name: str = None) -> None:
    """Analyze representations for a specific element or all elements"""
    
    print(f"🔍 ANALYZING REPRESENTATION TYPES")
    print(f"File: {file_path}")
    if element_name:
        print(f"Element: {element_name}")
    else:
        print("Element: ALL ELEMENTS")
    print("=" * 70)
    
    # Load data
    data = load_json_data(file_path)
    entities = data.get('data', [])
    
    # Create entity lookup
    entity_lookup = {entity.get('globalId'): entity for entity in entities if entity.get('globalId')}
    
    # Find target elements
    target_elements = []
    if element_name:
        element = find_element_by_name(entities, element_name)
        if element:
            target_elements = [element]
        else:
            print(f"❌ Element '{element_name}' not found")
            return
    else:
        # Find all elements with representations
        target_elements = [e for e in entities if e.get('representation')]
    
    if not target_elements:
        print("❌ No elements with representations found")
        return
    
    print(f"📊 Found {len(target_elements)} elements with representations\n")
    
    # Analyze each element
    for element in target_elements:
        analyze_single_element(element, entities, entity_lookup)

def analyze_single_element(element: Dict[str, Any], entities: List[Dict], entity_lookup: Dict[str, Dict]) -> None:
    """Analyze representations for a single element"""
    
    element_name = element.get('name', 'unknown')
    element_type = element.get('type', 'unknown')
    element_id = element.get('globalId', 'unknown')
    
    print(f"🏗️  ELEMENT: {element_name} ({element_type})")
    print(f"   GlobalId: {element_id}")
    
    # Get element's representation
    representation = element.get('representation', {})
    if not representation:
        print("   ❌ No representation found")
        print()
        return
    
    # Handle representation reference
    if 'ref' in representation:
        # Referenced ProductDefinitionShape
        prod_def = entity_lookup.get(representation['ref'])
        if not prod_def:
            print(f"   ❌ ProductDefinitionShape {representation['ref']} not found")
            print()
            return
        representations_list = prod_def.get('representations', [])
    elif representation.get('type') == 'IfcProductDefinitionShape':
        # Inline ProductDefinitionShape
        representations_list = representation.get('representations', [])
    else:
        print(f"   ❌ Unknown representation structure: {representation}")
        print()
        return
    
    print(f"   📐 Found {len(representations_list)} shape representations:")
    
    # Analyze each shape representation
    total_faces = 0
    high_complexity_reps = 0
    
    for i, shape_rep_ref in enumerate(representations_list):
        if isinstance(shape_rep_ref, dict) and 'ref' in shape_rep_ref:
            # Referenced shape representation
            shape_rep = entity_lookup.get(shape_rep_ref['ref'])
            if not shape_rep:
                print(f"      {i+1}. ❌ ShapeRepresentation {shape_rep_ref['ref']} not found")
                continue
        else:
            # Inline or direct shape representation
            shape_rep = shape_rep_ref
        
        if not shape_rep:
            continue
        
        analysis = analyze_shape_representation(entities, shape_rep, entity_lookup)
        
        print(f"      {i+1}. {analysis['identifier']}-{analysis['type']}")
        print(f"          Items: {analysis['item_count']} ({', '.join(set(analysis['geometry_types']))})")
        
        if analysis['complex_geometry']:
            print(f"          🔥 Complex geometry: {analysis['face_count']} faces")
            high_complexity_reps += 1
            total_faces += analysis['face_count']
        else:
            print(f"          📦 Simple geometry")
    
    # Summary
    if total_faces > 0:
        print(f"   📊 SUMMARY: {high_complexity_reps} high-complexity representations, {total_faces} total faces")
        if total_faces >= 100:
            print(f"   🎯 HIGH DETAIL: This element has detailed mesh geometry")
        elif total_faces >= 50:
            print(f"   ⚡ MEDIUM DETAIL: This element has moderate mesh geometry")
    else:
        print(f"   📦 SIMPLE GEOMETRY: All representations use parametric geometry")
    
    print()

def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_representation_types.py <ifcjson_file> [element_name]")
        print()
        print("Examples:")
        print("  python analyze_representation_types.py OrangeHouse.json")
        print("  python analyze_representation_types.py OrangeHouse.json 'Wand-Ext-OG-1'")
        print()
        print("Description:")
        print("  Analyzes shape representation types and geometry complexity for elements")
        print("  Shows representationIdentifier (Body-Brep, Body-SweptSolid, etc.) and geometry types")
        sys.exit(1)
    
    file_path = sys.argv[1]
    element_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    analyze_element_representations(file_path, element_name)

if __name__ == "__main__":
    main()