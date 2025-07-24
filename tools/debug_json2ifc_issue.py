#!/usr/bin/env python3
"""
Debug the JSON2IFC conversion issue - finds which entity is causing the ID 0 problem
"""

import json
import pandas as pd
import sys
from pathlib import Path

def debug_json2ifc_issue(json_file_path):
    """Debug which entity is causing the JSON2IFC converter to fail"""
    
    with open(json_file_path) as f:
        ifcJson = json.load(f)
    
    if 'data' not in ifcJson:
        print("No 'data' section found in JSON")
        return
    
    data = ifcJson['data']
    print(f"Total entities: {len(data)}")
    
    # Simulate the JSON2IFC converter's data processing
    df = pd.DataFrame()
    df["data"] = data
    df['type'] = df['data'].apply(pd.Series)['type']
    df['uuid'] = df['data'].apply(pd.Series)['globalId']
    
    print(f"DataFrame created with {len(df)} rows")
    print("Sample data:")
    print(df[['type', 'uuid']].head())
    
    # Check for problematic entries
    print("\nChecking for issues:")
    
    # Check for missing globalId
    missing_uuid = df['uuid'].isna()
    if missing_uuid.any():
        print(f"Found {missing_uuid.sum()} entities without globalId:")
        problematic = df[missing_uuid]
        for idx, row in problematic.iterrows():
            print(f"  Index {idx}: {row['type']} - {row['data']}")
    
    # Check for duplicate UUIDs
    duplicates = df['uuid'].duplicated()
    if duplicates.any():
        print(f"Found {duplicates.sum()} duplicate UUIDs:")
        dup_uuids = df[duplicates]['uuid'].values
        for uuid_val in dup_uuids:
            print(f"  Duplicate UUID: {uuid_val}")
    
    # Check for empty or problematic types
    missing_type = df['type'].isna()
    if missing_type.any():
        print(f"Found {missing_type.sum()} entities without type:")
        problematic = df[missing_type]
        for idx, row in problematic.iterrows():
            print(f"  Index {idx}: {row['data']}")
    
    # Check for entities with invalid structure
    for idx, row in df.iterrows():
        entity_data = row['data']
        if not isinstance(entity_data, dict):
            print(f"Index {idx}: Entity data is not a dict: {type(entity_data)}")
        elif 'type' not in entity_data:
            print(f"Index {idx}: Entity missing 'type' field: {entity_data}")
        elif 'globalId' not in entity_data:
            print(f"Index {idx}: Entity missing 'globalId' field: {entity_data}")
    
    return df

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_json2ifc_issue.py <json_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    debug_json2ifc_issue(json_file)