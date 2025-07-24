#!/usr/bin/env python3
"""
Representation Filtering Debugger

Shows exactly which representations get filtered out and why during the pipeline.
Compares Step 1 (original) vs Step 3 (recreated) to identify what filtering logic
removes which representations.
"""

import json
import sys
from typing import Dict, List, Any, Optional, Set

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

def get_element_representations(element: Dict[str, Any], entity_lookup: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """Extract all shape representations for an element"""
    
    representations = []
    
    # Get element's representation
    representation = element.get('representation', {})
    if not representation:
        return representations
    
    # Handle representation reference
    if 'ref' in representation:
        # Referenced ProductDefinitionShape
        prod_def = entity_lookup.get(representation['ref'])
        if not prod_def:
            return representations
        representations_list = prod_def.get('representations', [])
    elif representation.get('type') == 'IfcProductDefinitionShape':
        # Inline ProductDefinitionShape
        representations_list = representation.get('representations', [])
    else:
        return representations
    
    # Extract shape representations
    for shape_rep_ref in representations_list:
        if isinstance(shape_rep_ref, dict) and 'ref' in shape_rep_ref:
            # Referenced shape representation
            shape_rep = entity_lookup.get(shape_rep_ref['ref'])
            if shape_rep:
                representations.append(shape_rep)
        else:
            # Inline shape representation
            representations.append(shape_rep_ref)
    
    return representations

def analyze_representation_complexity(rep: Dict[str, Any], entity_lookup: Dict[str, Dict]) -> Dict[str, Any]:
    """Analyze the complexity and type of a representation"""
    
    rep_id = rep.get('representationIdentifier', 'unknown')
    rep_type = rep.get('representationType', 'unknown')
    items = rep.get('items', [])
    
    geometry_types = set()
    face_count = 0
    is_complex = False
    
    for item in items:
        if isinstance(item, dict):
            if 'ref' in item:
                # Referenced item
                referenced_entity = entity_lookup.get(item['ref'])
                if referenced_entity:
                    item_type = referenced_entity.get('type', 'unknown')
                    geometry_types.add(item_type)
                    
                    if item_type == 'IfcFacetedBrep':
                        is_complex = True
                        face_count += count_faceted_brep_faces(referenced_entity, entity_lookup)
                    elif item_type == 'IfcBooleanClippingResult':
                        is_complex = True
            elif item.get('type'):
                # Inline item
                item_type = item.get('type')
                geometry_types.add(item_type)
                
                if item_type == 'IfcFacetedBrep':
                    is_complex = True
                    face_count += count_faceted_brep_faces(item, entity_lookup)
                elif item_type == 'IfcBooleanClippingResult':
                    is_complex = True
    
    return {
        'identifier': rep_id,
        'type': rep_type,
        'geometry_types': list(geometry_types),
        'face_count': face_count,
        'is_complex': is_complex,
        'item_count': len(items)
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

def debug_representation_filtering(step1_file: str, step3_file: str, element_name: str = None) -> None:
    """Debug representation filtering between Step 1 and Step 3"""
    
    print(f"🔍 DEBUGGING REPRESENTATION FILTERING")
    print(f"Step 1 (Original): {step1_file}")
    print(f"Step 3 (Recreated): {step3_file}")
    if element_name:
        print(f"Element: {element_name}")
    else:
        print("Element: ALL BUILDING ELEMENTS")
    print("=" * 80)
    
    # Load data
    step1_data = load_json_data(step1_file)
    step3_data = load_json_data(step3_file)
    
    step1_entities = step1_data.get('data', [])
    step3_entities = step3_data.get('data', [])
    
    # Create entity lookups
    step1_lookup = {entity.get('globalId'): entity for entity in step1_entities if entity.get('globalId')}
    step3_lookup = {entity.get('globalId'): entity for entity in step3_entities if entity.get('globalId')}
    
    # Find elements to analyze
    if element_name:
        step1_element = find_element_by_name(step1_entities, element_name)
        step3_element = find_element_by_name(step3_entities, element_name)
        
        if not step1_element:
            print(f"❌ Element '{element_name}' not found in Step 1")
            return
        if not step3_element:
            print(f"❌ Element '{element_name}' not found in Step 3")
            return
            
        elements_to_analyze = [(step1_element, step3_element)]
    else:
        # Find common elements between both files
        step1_names = {e.get('name'): e for e in step1_entities if e.get('name') and e.get('representation')}
        step3_names = {e.get('name'): e for e in step3_entities if e.get('name') and e.get('representation')}
        
        common_names = set(step1_names.keys()) & set(step3_names.keys())
        elements_to_analyze = [(step1_names[name], step3_names[name]) for name in common_names]
    
    if not elements_to_analyze:
        print("❌ No common elements with representations found")
        return
    
    print(f"📊 Analyzing {len(elements_to_analyze)} elements\n")
    
    # Analyze each element pair
    total_step1_reps = 0
    total_step3_reps = 0
    filtered_out_count = 0
    complex_filtered_count = 0
    
    for step1_elem, step3_elem in elements_to_analyze:
        result = analyze_element_filtering(step1_elem, step3_elem, step1_lookup, step3_lookup)
        
        total_step1_reps += result['step1_count']
        total_step3_reps += result['step3_count']
        filtered_out_count += len(result['filtered_out'])
        complex_filtered_count += result['complex_filtered']
        
        print_filtering_result(result)
    
    # Summary
    print("📊 REPRESENTATION FILTERING SUMMARY")
    print("=" * 60)
    print(f"Total elements analyzed: {len(elements_to_analyze)}")
    print(f"Step 1 representations: {total_step1_reps}")
    print(f"Step 3 representations: {total_step3_reps}")
    print(f"Representations filtered out: {filtered_out_count}")
    print(f"Complex representations filtered: {complex_filtered_count}")
    
    if total_step1_reps > 0:
        retention_rate = (total_step3_reps / total_step1_reps) * 100
        filtering_rate = (filtered_out_count / total_step1_reps) * 100
        print(f"Representation retention rate: {retention_rate:.1f}%")
        print(f"Representation filtering rate: {filtering_rate:.1f}%")
    
    if complex_filtered_count > 0:
        print(f"⚠️  WARNING: {complex_filtered_count} high-complexity representations were filtered out!")
        print("   This may cause geometry quality loss (circular→rectangular openings)")

def analyze_element_filtering(step1_elem: Dict, step3_elem: Dict, step1_lookup: Dict, step3_lookup: Dict) -> Dict[str, Any]:
    """Analyze filtering for a single element pair"""
    
    element_name = step1_elem.get('name', 'unknown')
    element_type = step1_elem.get('type', 'unknown')
    
    # Get representations from both steps
    step1_reps = get_element_representations(step1_elem, step1_lookup)
    step3_reps = get_element_representations(step3_elem, step3_lookup)
    
    # Analyze each representation
    step1_analysis = [analyze_representation_complexity(rep, step1_lookup) for rep in step1_reps]
    step3_analysis = [analyze_representation_complexity(rep, step3_lookup) for rep in step3_reps]
    
    # Find what was filtered out
    step1_identifiers = {rep['identifier'] for rep in step1_analysis}
    step3_identifiers = {rep['identifier'] for rep in step3_analysis}
    
    filtered_out = []
    complex_filtered = 0
    
    for rep in step1_analysis:
        if rep['identifier'] not in step3_identifiers:
            filtered_out.append(rep)
            if rep['is_complex']:
                complex_filtered += 1
    
    return {
        'element_name': element_name,
        'element_type': element_type,
        'step1_count': len(step1_analysis),
        'step3_count': len(step3_analysis),
        'step1_reps': step1_analysis,
        'step3_reps': step3_analysis,
        'filtered_out': filtered_out,
        'complex_filtered': complex_filtered
    }

def print_filtering_result(result: Dict[str, Any]) -> None:
    """Print filtering analysis result for a single element"""
    
    name = result['element_name']
    elem_type = result['element_type']
    step1_count = result['step1_count']
    step3_count = result['step3_count']
    filtered_count = len(result['filtered_out'])
    
    print(f"🏗️  {name} ({elem_type})")
    print(f"   📐 Step 1: {step1_count} representations → Step 3: {step3_count} representations")
    
    if filtered_count > 0:
        print(f"   ❌ {filtered_count} representations filtered out:")
        
        for filtered_rep in result['filtered_out']:
            identifier = filtered_rep['identifier']
            rep_type = filtered_rep['type']
            geometry_types = ', '.join(filtered_rep['geometry_types'])
            face_count = filtered_rep['face_count']
            
            print(f"      • {identifier}-{rep_type}")
            print(f"        Geometry: {geometry_types}")
            
            if filtered_rep['is_complex']:
                print(f"        🔥 COMPLEX: {face_count} faces (HIGH QUALITY LOSS)")
            else:
                print(f"        📦 Simple: {face_count} faces")
    else:
        print(f"   ✅ No representations filtered out")
    
    # Show what was kept
    if result['step3_reps']:
        print(f"   ✅ Kept representations:")
        for kept_rep in result['step3_reps']:
            identifier = kept_rep['identifier']
            rep_type = kept_rep['type']
            face_count = kept_rep['face_count']
            print(f"      • {identifier}-{rep_type} ({face_count} faces)")
    
    print()

def main():
    """Main entry point"""
    
    if len(sys.argv) < 3:
        print("Usage: python debug_representation_filtering.py <step1_json> <step3_json> [element_name]")
        print()
        print("Examples:")
        print("  python debug_representation_filtering.py step1.json step3.json")
        print("  python debug_representation_filtering.py step1.json step3.json 'Wand-Ext-OG-1'")
        print()
        print("Description:")
        print("  Shows exactly which representations get filtered out during pipeline")
        print("  Identifies geometry quality loss from representation filtering")
        print("  Helps debug why circular openings become rectangular")
        sys.exit(1)
    
    step1_file = sys.argv[1]
    step3_file = sys.argv[2]
    element_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    debug_representation_filtering(step1_file, step3_file, element_name)

if __name__ == "__main__":
    main()