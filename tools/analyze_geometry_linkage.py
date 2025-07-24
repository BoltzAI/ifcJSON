#!/usr/bin/env python3
"""
Analyze how geometry is linked in ifcJSON files
Find the actual connection between building elements and their shape representations
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

def trace_geometry_linkage(file_path: str) -> Dict[str, Any]:
    """Trace how building elements are linked to their geometry representations"""
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Index all entities by ID/ref
    entities_by_id = {}
    for entity in data.get('data', []):
        if 'id' in entity:
            entities_by_id[entity['id']] = entity
    
    # Find building elements
    building_elements = []
    for entity in data.get('data', []):
        entity_type = entity.get('type', '')
        if entity_type.startswith('Ifc') and any(elem_type in entity_type for elem_type in ['Wall', 'Window', 'Door', 'Slab', 'Beam', 'Column', 'Opening']):
            building_elements.append(entity)
    
    # Trace geometry for each building element
    geometry_traces = {}
    
    for element in building_elements:
        element_name = element.get('name', element.get('type', 'Unknown'))
        element_id = element.get('id', 'no-id')
        
        trace = {
            'element': element,
            'representation_path': [],
            'shape_representations': []
        }
        
        # Check if element has representation directly
        if 'representation' in element:
            representation_ref = element['representation']
            
            # Follow the representation reference
            if isinstance(representation_ref, dict) and 'ref' in representation_ref:
                rep_id = representation_ref['ref']
                trace['representation_path'].append(f"Element -> representation.ref: {rep_id}")
                
                # Find the referenced ProductDefinitionShape
                if rep_id in entities_by_id:
                    prod_def_shape = entities_by_id[rep_id]
                    trace['representation_path'].append(f"ProductDefinitionShape: {prod_def_shape.get('type')}")
                    
                    # Get representations from ProductDefinitionShape
                    if 'representations' in prod_def_shape:
                        for rep in prod_def_shape['representations']:
                            if isinstance(rep, dict) and 'ref' in rep:
                                shape_rep_id = rep['ref']
                                trace['representation_path'].append(f"-> representations[].ref: {shape_rep_id}")
                                
                                # Find the actual shape representation
                                if shape_rep_id in entities_by_id:
                                    shape_rep = entities_by_id[shape_rep_id]
                                    trace['shape_representations'].append(shape_rep)
                                    trace['representation_path'].append(f"IfcShapeRepresentation: {shape_rep.get('representationIdentifier')} - {shape_rep.get('representationType')}")
            elif isinstance(representation_ref, dict):
                # Direct embedded representation
                trace['representation_path'].append("Element -> representation (embedded)")
                if representation_ref.get('type') == 'IfcProductDefinitionShape':
                    for rep in representation_ref.get('representations', []):
                        if isinstance(rep, dict) and rep.get('type') == 'IfcShapeRepresentation':
                            trace['shape_representations'].append(rep)
                            trace['representation_path'].append(f"IfcShapeRepresentation: {rep.get('representationIdentifier')} - {rep.get('representationType')}")
        
        geometry_traces[element_name] = trace
    
    return {
        'building_elements': building_elements,
        'geometry_traces': geometry_traces,
        'total_entities': len(entities_by_id),
        'entities_by_id': entities_by_id
    }

def compare_geometry_linkage(official_path: str, expanded_path: str):
    """Compare geometry linkage between official and expanded files"""
    
    print("🔗 GEOMETRY LINKAGE ANALYSIS")
    print("=" * 50)
    
    # Analyze official file
    print(f"\n📄 OFFICIAL JSON: {Path(official_path).name}")
    official_analysis = trace_geometry_linkage(official_path)
    
    print(f"  Building Elements: {len(official_analysis['building_elements'])}")
    print(f"  Total Entities: {official_analysis['total_entities']}")
    
    for element_name, trace in official_analysis['geometry_traces'].items():
        print(f"\n  🏗️ {element_name}")
        print(f"    Type: {trace['element'].get('type')}")
        if trace['representation_path']:
            print(f"    Geometry Path:")
            for step in trace['representation_path']:
                print(f"      {step}")
        print(f"    Shape Representations Found: {len(trace['shape_representations'])}")
        for shape_rep in trace['shape_representations']:
            rep_id = shape_rep.get('representationIdentifier', 'Unknown')
            rep_type = shape_rep.get('representationType', 'Unknown')
            items_count = len(shape_rep.get('items', []))
            print(f"      - {rep_id}: {rep_type} ({items_count} items)")
    
    # Analyze expanded file
    print(f"\n📄 EXPANDED JSON: {Path(expanded_path).name}")
    expanded_analysis = trace_geometry_linkage(expanded_path)
    
    print(f"  Building Elements: {len(expanded_analysis['building_elements'])}")
    print(f"  Total Entities: {expanded_analysis['total_entities']}")
    
    for element_name, trace in expanded_analysis['geometry_traces'].items():
        print(f"\n  🏗️ {element_name}")
        print(f"    Type: {trace['element'].get('type')}")
        if trace['representation_path']:
            print(f"    Geometry Path:")
            for step in trace['representation_path']:
                print(f"      {step}")
        print(f"    Shape Representations Found: {len(trace['shape_representations'])}")
        for shape_rep in trace['shape_representations']:
            rep_id = shape_rep.get('representationIdentifier', 'Unknown')
            rep_type = shape_rep.get('representationType', 'Unknown')
            items_count = len(shape_rep.get('items', []))
            print(f"      - {rep_id}: {rep_type} ({items_count} items)")
    
    # Summary comparison
    print(f"\n📊 COMPARISON SUMMARY")
    official_shape_count = sum(len(trace['shape_representations']) for trace in official_analysis['geometry_traces'].values())
    expanded_shape_count = sum(len(trace['shape_representations']) for trace in expanded_analysis['geometry_traces'].values())
    
    print(f"  Official total shape representations used by elements: {official_shape_count}")
    print(f"  Expanded total shape representations used by elements: {expanded_shape_count}")
    
    if official_shape_count != expanded_shape_count:
        print(f"  ⚠️  MISMATCH: {expanded_shape_count - official_shape_count} difference")
    else:
        print(f"  ✅ MATCH: Both files use same number of shape representations")

def main():
    parser = argparse.ArgumentParser(description='Analyze geometry linkage in ifcJSON files')
    parser.add_argument('official_json', help='Path to official ifcJSON file')
    parser.add_argument('expanded_json', help='Path to expanded ifcJSON file')
    
    args = parser.parse_args()
    
    compare_geometry_linkage(args.official_json, args.expanded_json)

if __name__ == '__main__':
    main()