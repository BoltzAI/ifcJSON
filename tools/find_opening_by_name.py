#!/usr/bin/env python3
"""
Find Opening By Name Tool

Finds opening elements by name in ifcJSON files.
"""

import sys
import json

def find_openings_by_name(file_path: str, target_name: str):
    """Find all opening-related elements by name"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    entities = data.get('data', [])
    
    opening_types = ['IfcOpeningElement', 'IfcWindow', 'IfcDoor']
    
    found_elements = []
    
    for entity in entities:
        entity_type = entity.get('type')
        entity_name = entity.get('name') or entity.get('Name', '')
        
        if entity_type in opening_types and target_name in str(entity_name):
            found_elements.append({
                'type': entity_type,
                'globalId': entity.get('globalId'),
                'name': entity_name,
                'has_representation': 'representation' in entity or 'Representation' in entity
            })
    
    print(f"🔍 Found {len(found_elements)} elements containing '{target_name}':")
    for elem in found_elements:
        print(f"  {elem['type']} | {elem['globalId']} | {elem['name']} | Repr: {elem['has_representation']}")
    
    return found_elements

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python find_opening_by_name.py <ifcjson_file> <name_pattern>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    name_pattern = sys.argv[2]
    
    find_openings_by_name(file_path, name_pattern)