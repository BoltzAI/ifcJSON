#!/usr/bin/env python3
"""
Debug broken references in ifcJSON - find refs that point to non-existent entities
"""

import json
import sys
from collections import defaultdict

def find_broken_references(json_file_path):
    """Find references that point to entities that don't exist"""
    
    with open(json_file_path) as f:
        ifcJson = json.load(f)
    
    if 'data' not in ifcJson:
        print("No 'data' section found in JSON")
        return
    
    data = ifcJson['data']
    print(f"Total entities: {len(data)}")
    
    # Collect all entity IDs
    entity_ids = set()
    for entity in data:
        if 'globalId' in entity:
            entity_ids.add(entity['globalId'])
    
    print(f"Total entity IDs: {len(entity_ids)}")
    
    # Find all references
    references = set()
    broken_refs = []
    
    def collect_refs(obj, path=""):
        """Recursively collect all references in the object"""
        if isinstance(obj, dict):
            if 'ref' in obj:
                ref_id = obj['ref']
                references.add(ref_id)
                if ref_id not in entity_ids:
                    broken_refs.append((path, ref_id))
            else:
                for key, value in obj.items():
                    collect_refs(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                collect_refs(item, f"{path}[{i}]" if path else f"[{i}]")
    
    # Check all entities for references
    for i, entity in enumerate(data):
        collect_refs(entity, f"entity[{i}]")
    
    print(f"Total references found: {len(references)}")
    print(f"Broken references: {len(broken_refs)}")
    
    if broken_refs:
        print("\nBroken references (first 10):")
        for path, ref_id in broken_refs[:10]:
            print(f"  {path} -> {ref_id}")
        
        # Group by reference ID to see patterns
        ref_counts = defaultdict(int)
        for _, ref_id in broken_refs:
            ref_counts[ref_id] += 1
        
        print(f"\nMost common broken references:")
        for ref_id, count in sorted(ref_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {ref_id}: {count} references")
    
    # Check for duplicate entity IDs
    id_counts = defaultdict(int)
    for entity in data:
        if 'globalId' in entity:
            id_counts[entity['globalId']] += 1
    
    duplicates = {k: v for k, v in id_counts.items() if v > 1}
    if duplicates:
        print(f"\nDuplicate entity IDs:")
        for entity_id, count in duplicates.items():
            print(f"  {entity_id}: {count} occurrences")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_references.py <json_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    find_broken_references(json_file)