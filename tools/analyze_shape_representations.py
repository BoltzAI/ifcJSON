#!/usr/bin/env python3
"""
Analyze shape representations in IFC pipeline assets
This tool helps debug why embedded converters create too many shape representations
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

def analyze_ifcjson_shape_representations(file_path: str) -> Dict[str, Any]:
    """Analyze shape representations in an ifcJSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    shape_reps = []
    contexts = []
    product_def_shapes = []
    mapped_items = []
    elements = []
    
    for entity in data.get('data', []):
        entity_type = entity.get('type', '')
        
        if entity_type == 'IfcShapeRepresentation':
            shape_reps.append(entity)
        elif entity_type == 'IfcGeometricRepresentationContext':
            contexts.append(entity)
        elif entity_type == 'IfcProductDefinitionShape':
            product_def_shapes.append(entity)
        elif entity_type == 'IfcMappedItem':
            mapped_items.append(entity)
        elif entity_type.startswith('Ifc') and entity_type.endswith(('Wall', 'Window', 'Door', 'Slab', 'Beam', 'Column')):
            elements.append(entity)
    
    return {
        'shape_representations': shape_reps,
        'contexts': contexts,
        'product_definition_shapes': product_def_shapes,
        'mapped_items': mapped_items,
        'building_elements': elements,
        'counts': {
            'shape_representations': len(shape_reps),
            'contexts': len(contexts),
            'product_definition_shapes': len(product_def_shapes),
            'mapped_items': len(mapped_items),
            'building_elements': len(elements)
        }
    }

def analyze_asset_files(asset_dir: str) -> Dict[str, Any]:
    """Analyze all asset files in a directory"""
    asset_path = Path(asset_dir)
    asset_results = {}
    
    for asset_file in asset_path.glob("extracted_*.json"):
        result = analyze_ifcjson_shape_representations(str(asset_file))
        asset_results[asset_file.name] = result
    
    return asset_results

def compare_shape_rep_structures(official_path: str, expanded_path: str, assets_dir: str):
    """Compare shape representation structures between official, expanded, and assets"""
    
    print("🔍 SHAPE REPRESENTATION ANALYSIS")
    print("=" * 50)
    
    # Analyze official JSON
    print(f"\n📄 OFFICIAL JSON: {Path(official_path).name}")
    official = analyze_ifcjson_shape_representations(official_path)
    print(f"  Shape Representations: {official['counts']['shape_representations']}")
    print(f"  Product Definition Shapes: {official['counts']['product_definition_shapes']}")
    print(f"  Building Elements: {official['counts']['building_elements']}")
    
    # Analyze expanded JSON
    print(f"\n📄 EXPANDED JSON: {Path(expanded_path).name}")
    expanded = analyze_ifcjson_shape_representations(expanded_path)
    print(f"  Shape Representations: {expanded['counts']['shape_representations']}")
    print(f"  Product Definition Shapes: {expanded['counts']['product_definition_shapes']}")
    print(f"  Mapped Items: {expanded['counts']['mapped_items']}")
    print(f"  Building Elements: {expanded['counts']['building_elements']}")
    
    # Analyze assets
    print(f"\n📁 ASSETS DIRECTORY: {Path(assets_dir).name}")
    assets = analyze_asset_files(assets_dir)
    
    total_asset_shape_reps = 0
    for asset_name, asset_data in assets.items():
        count = asset_data['counts']['shape_representations']
        total_asset_shape_reps += count
        print(f"  {asset_name}: {count} shape representations")
    
    print(f"\n📊 SUMMARY")
    print(f"  Official has {official['counts']['shape_representations']} shape representations")
    print(f"  Expanded has {expanded['counts']['shape_representations']} shape representations")
    print(f"  Assets have {total_asset_shape_reps} total shape representations across {len(assets)} files")
    
    # Detailed analysis of first asset
    if assets:
        first_asset = list(assets.values())[0]
        print(f"\n🔬 DETAILED ANALYSIS OF FIRST ASSET:")
        print(f"  Shape Representations: {len(first_asset['shape_representations'])}")
        
        for i, shape_rep in enumerate(first_asset['shape_representations']):
            rep_id = shape_rep.get('representationIdentifier', 'Unknown')
            rep_type = shape_rep.get('representationType', 'Unknown')
            items_count = len(shape_rep.get('items', []))
            print(f"    [{i+1}] {rep_id} - {rep_type} ({items_count} items)")
    
    # Analysis of shape rep types in official vs expanded
    print(f"\n🏗️ SHAPE REPRESENTATION TYPES:")
    
    # Official shape rep types
    official_types = defaultdict(int)
    for shape_rep in official['shape_representations']:
        rep_type = shape_rep.get('representationType', 'Unknown')
        rep_id = shape_rep.get('representationIdentifier', 'Unknown')
        official_types[f"{rep_id}-{rep_type}"] += 1
    
    print(f"  Official:")
    for rep_type, count in official_types.items():
        print(f"    {rep_type}: {count}")
    
    # Expanded shape rep types
    expanded_types = defaultdict(int)
    for shape_rep in expanded['shape_representations']:
        rep_type = shape_rep.get('representationType', 'Unknown')
        rep_id = shape_rep.get('representationIdentifier', 'Unknown')
        expanded_types[f"{rep_id}-{rep_type}"] += 1
    
    print(f"  Expanded:")
    for rep_type, count in expanded_types.items():
        print(f"    {rep_type}: {count}")

def main():
    parser = argparse.ArgumentParser(description='Analyze shape representations in IFC pipeline')
    parser.add_argument('official_json', help='Path to official ifcJSON file')
    parser.add_argument('expanded_json', help='Path to expanded ifcJSON file')
    parser.add_argument('assets_dir', help='Path to assets directory')
    
    args = parser.parse_args()
    
    compare_shape_rep_structures(args.official_json, args.expanded_json, args.assets_dir)

if __name__ == '__main__':
    main()