#!/usr/bin/env python3
"""
Simple tool to find all IfcSlab entities in ifcJSON files
"""

import json
import sys
from pathlib import Path

def find_slabs(ifcjson_path):
    """Find all IfcSlab entities in an ifcJSON file"""
    
    print(f"🔍 Searching for IfcSlab entities in: {ifcjson_path}")
    
    with open(ifcjson_path, 'r') as f:
        data = json.load(f)
    
    if 'data' not in data:
        print("❌ No 'data' key found in JSON")
        return
    
    slabs = []
    total_entities = len(data['data'])
    
    for entity in data['data']:
        if entity.get('type') == 'IfcSlab':
            slabs.append(entity)
    
    print(f"📊 Found {len(slabs)} IfcSlab entities out of {total_entities} total entities")
    print()
    
    if not slabs:
        print("🔍 No IfcSlab entities found. Let's check for floor-related elements:")
        
        # Look for elements with floor-related names
        floor_elements = []
        for entity in data['data']:
            name = entity.get('name', '')
            if any(keyword in name.lower() for keyword in ['floor', '楼板', '瓷砖', '门廊']):
                floor_elements.append(entity)
        
        print(f"📋 Found {len(floor_elements)} floor-related elements:")
        for i, elem in enumerate(floor_elements, 1):
            print(f"  {i}. {elem.get('type', 'Unknown')} - {elem.get('name', 'No name')} (ID: {elem.get('globalId', 'No ID')})")
        
        return
    
    print("📋 IfcSlab entities found:")
    for i, slab in enumerate(slabs, 1):
        globalId = slab.get('globalId', 'No ID')
        name = slab.get('name', 'No name')
        predefinedType = slab.get('predefinedType', 'No type')
        
        print(f"  {i}. GlobalId: {globalId}")
        print(f"     Name: {name}")
        print(f"     PredefinedType: {predefinedType}")
        print()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python find_slabs.py <ifcjson_file>")
        sys.exit(1)
    
    ifcjson_path = sys.argv[1]
    
    if not Path(ifcjson_path).exists():
        print(f"❌ File not found: {ifcjson_path}")
        sys.exit(1)
    
    find_slabs(ifcjson_path)