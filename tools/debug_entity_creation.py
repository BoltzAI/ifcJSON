#!/usr/bin/env python3
"""
Debug which specific entity type is causing ifcopenshell model.create_entity() to fail
"""

import json
import pandas as pd
import sys
import ifcopenshell
from pathlib import Path

def debug_entity_creation(json_file_path):
    """Debug which entity is causing create_entity to return ID 0"""
    
    with open(json_file_path) as f:
        ifcJson = json.load(f)
    
    if 'data' not in ifcJson:
        print("No 'data' section found in JSON")
        return
    
    data = ifcJson['data']
    print(f"Total entities: {len(data)}")
    
    # Simulate the JSON2IFC converter's setup
    schemaIdentifier = ifcJson.get('schemaIdentifier', 'IFC4')
    model = ifcopenshell.file(None, schemaIdentifier)
    
    # Process entities and track which ones fail
    df = pd.DataFrame()
    df["data"] = data
    df['type'] = df['data'].apply(pd.Series)['type']
    df['uuid'] = df['data'].apply(pd.Series)['globalId']
    
    print(f"Testing entity creation with schema: {schemaIdentifier}")
    
    failed_entities = []
    successful_entities = []
    
    for idx, row in df.iterrows():
        entity_type = row['type']
        try:
            entity = model.create_entity(entity_type)
            entity_id = entity.id()
            
            if entity_id == 0:
                failed_entities.append((idx, entity_type, "ID is 0"))
                print(f"FAILED: Index {idx} - {entity_type}: Entity ID is 0")
            else:
                successful_entities.append((idx, entity_type, entity_id))
                if len(successful_entities) <= 10:  # Show first 10 successes
                    print(f"SUCCESS: Index {idx} - {entity_type}: ID {entity_id}")
        except Exception as e:
            failed_entities.append((idx, entity_type, str(e)))
            print(f"ERROR: Index {idx} - {entity_type}: {e}")
    
    print(f"\nSummary:")
    print(f"Successful entities: {len(successful_entities)}")
    print(f"Failed entities: {len(failed_entities)}")
    
    if failed_entities:
        print(f"\nFailed entity details:")
        for idx, entity_type, error in failed_entities[:10]:  # Show first 10 failures
            print(f"  Index {idx}: {entity_type} - {error}")
    
    # Show entity type distribution
    type_counts = df['type'].value_counts()
    print(f"\nEntity type distribution:")
    for entity_type, count in type_counts.head(10).items():
        print(f"  {entity_type}: {count}")
    
    return len(failed_entities) == 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_entity_creation.py <json_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    success = debug_entity_creation(json_file)
    sys.exit(0 if success else 1)