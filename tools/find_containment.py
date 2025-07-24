#!/usr/bin/env python3
"""
Find containment relationships for specific elements in ifcJSON files
"""

import json
import sys
from pathlib import Path

def find_containment_for_elements(ifcjson_path, element_ids):
    """Find containment relationships for specific elements"""
    
    print(f"🔍 Searching for containment relationships in: {ifcjson_path}")
    
    with open(ifcjson_path, 'r') as f:
        data = json.load(f)
    
    if 'data' not in data:
        print("❌ No 'data' key found in JSON")
        return
    
    # Find the elements first
    elements = {}
    for entity in data['data']:
        entity_id = entity.get('globalId') or entity.get('GlobalId')
        if entity_id in element_ids:
            elements[entity_id] = entity
    
    print(f"\n📋 Found {len(elements)} out of {len(element_ids)} requested elements:")
    for element_id in element_ids:
        if element_id in elements:
            elem = elements[element_id]
            print(f"  ✅ {element_id} - {elem.get('type')} - {elem.get('name', 'No name')}")
        else:
            print(f"  ❌ {element_id} - NOT FOUND")
    
    # Find containment relationships
    containment_rels = []
    for entity in data['data']:
        if entity.get('type') == 'IfcRelContainedInSpatialStructure':
            containment_rels.append(entity)
    
    print(f"\n🔗 Found {len(containment_rels)} containment relationships")
    
    # Check if our elements are contained
    for element_id in element_ids:
        found_containment = False
        for rel in containment_rels:
            related_elements = rel.get('relatedElements', [])
            for rel_elem in related_elements:
                ref_id = None
                if isinstance(rel_elem, dict):
                    if 'ref' in rel_elem:
                        # Look up the referenced element
                        ref_id = rel_elem['ref']
                        for entity in data['data']:
                            if entity.get('globalId') == ref_id or entity.get('GlobalId') == ref_id:
                                ref_id = entity.get('globalId') or entity.get('GlobalId')
                                break
                    else:
                        ref_id = rel_elem.get('globalId') or rel_elem.get('GlobalId')
                elif isinstance(rel_elem, str):
                    ref_id = rel_elem
                
                if ref_id == element_id:
                    relating_structure = rel.get('relatingStructure', {})
                    structure_ref = relating_structure.get('ref') if isinstance(relating_structure, dict) else relating_structure
                    
                    # Find the structure name
                    structure_name = "Unknown"
                    if structure_ref:
                        for entity in data['data']:
                            if (entity.get('globalId') == structure_ref or 
                                entity.get('GlobalId') == structure_ref):
                                structure_name = entity.get('name', 'No name')
                                break
                    
                    print(f"  📍 {element_id} is contained in: {structure_name} ({structure_ref})")
                    found_containment = True
                    break
            
            if found_containment:
                break
        
        if not found_containment:
            print(f"  ❌ {element_id} has NO containment relationship")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python find_containment.py <ifcjson_file> <element_id1> [element_id2] ...")
        sys.exit(1)
    
    ifcjson_path = sys.argv[1]
    element_ids = sys.argv[2:]
    
    if not Path(ifcjson_path).exists():
        print(f"❌ File not found: {ifcjson_path}")
        sys.exit(1)
    
    find_containment_for_elements(ifcjson_path, element_ids)