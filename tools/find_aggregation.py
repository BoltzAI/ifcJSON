#!/usr/bin/env python3
"""
Find aggregation relationships for specific elements in ifcJSON files
"""

import json
import sys
from pathlib import Path

def find_aggregation_for_elements(ifcjson_path, element_ids):
    """Find aggregation relationships for specific elements"""
    
    print(f"🔍 Searching for aggregation relationships in: {ifcjson_path}")
    
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
    
    # Find aggregation relationships
    aggregation_rels = []
    for entity in data['data']:
        if entity.get('type') == 'IfcRelAggregates':
            aggregation_rels.append(entity)
    
    print(f"\n🔗 Found {len(aggregation_rels)} aggregation relationships")
    
    # Check if our elements are aggregated
    for element_id in element_ids:
        found_aggregation = False
        
        # Check if this element is a parent (relating object)
        for rel in aggregation_rels:
            relating_object = rel.get('relatingObject', {})
            relating_ref = relating_object.get('ref') if isinstance(relating_object, dict) else relating_object
            
            if relating_ref == element_id:
                related_objects = rel.get('relatedObjects', [])
                print(f"  📊 {element_id} AGGREGATES {len(related_objects)} children:")
                for i, obj in enumerate(related_objects):
                    obj_ref = obj.get('ref') if isinstance(obj, dict) else obj
                    # Find the child name
                    child_name = "Unknown"
                    for entity in data['data']:
                        if (entity.get('globalId') == obj_ref or entity.get('GlobalId') == obj_ref):
                            child_name = entity.get('name', 'No name')
                            break
                    print(f"    {i+1}. {obj_ref} - {child_name}")
                found_aggregation = True
                break
        
        # Check if this element is a child (related object)
        if not found_aggregation:
            for rel in aggregation_rels:
                related_objects = rel.get('relatedObjects', [])
                for obj in related_objects:
                    obj_ref = obj.get('ref') if isinstance(obj, dict) else obj
                    if obj_ref == element_id:
                        relating_object = rel.get('relatingObject', {})
                        parent_ref = relating_object.get('ref') if isinstance(relating_object, dict) else relating_object
                        
                        # Find the parent name
                        parent_name = "Unknown"
                        if parent_ref:
                            for entity in data['data']:
                                if (entity.get('globalId') == parent_ref or entity.get('GlobalId') == parent_ref):
                                    parent_name = entity.get('name', 'No name')
                                    break
                        
                        print(f"  📍 {element_id} is AGGREGATED BY: {parent_name} ({parent_ref})")
                        found_aggregation = True
                        break
                
                if found_aggregation:
                    break
        
        if not found_aggregation:
            print(f"  ❌ {element_id} has NO aggregation relationship")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python find_aggregation.py <ifcjson_file> <element_id1> [element_id2] ...")
        sys.exit(1)
    
    ifcjson_path = sys.argv[1]
    element_ids = sys.argv[2:]
    
    if not Path(ifcjson_path).exists():
        print(f"❌ File not found: {ifcjson_path}")
        sys.exit(1)
    
    find_aggregation_for_elements(ifcjson_path, element_ids)