#!/usr/bin/env python3
"""
Debug embedded converter shape representation logic
Analyze which shape representations should be primary vs duplicates
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

def analyze_product_definition_shapes(file_path: str) -> Dict[str, Any]:
    """Analyze which shape representations are referenced by ProductDefinitionShape entities"""
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Find all ProductDefinitionShape entities and their representations
    prod_def_shapes = []
    shape_rep_refs = set()
    
    for entity in data.get('data', []):
        if entity.get('type') == 'IfcProductDefinitionShape':
            prod_def_shapes.append(entity)
            
            # Extract representation references
            representations = entity.get('representations', [])
            for rep in representations:
                if isinstance(rep, dict) and 'ref' in rep:
                    shape_rep_refs.add(rep['ref'])
                elif isinstance(rep, str):
                    shape_rep_refs.add(rep)
    
    # Find all shape representations
    all_shape_reps = {}
    for entity in data.get('data', []):
        if entity.get('type') == 'IfcShapeRepresentation':
            # Use the entity's id or a generated key
            entity_id = entity.get('id', f"shape_rep_{len(all_shape_reps)}")
            all_shape_reps[entity_id] = entity
    
    # Classify shape representations
    primary_reps = {}
    unused_reps = {}
    
    for rep_id, rep_entity in all_shape_reps.items():
        if rep_id in shape_rep_refs:
            primary_reps[rep_id] = rep_entity
        else:
            unused_reps[rep_id] = rep_entity
    
    return {
        'product_definition_shapes': prod_def_shapes,
        'all_shape_representations': all_shape_reps,
        'primary_representations': primary_reps,
        'unused_representations': unused_reps,
        'shape_rep_refs': shape_rep_refs
    }

def analyze_assets_usage_pattern(asset_dir: str) -> Dict[str, Any]:
    """Analyze which shape representations are actually used vs unused in assets"""
    
    asset_path = Path(asset_dir)
    asset_analysis = {}
    
    for asset_file in asset_path.glob("extracted_*.json"):
        analysis = analyze_product_definition_shapes(str(asset_file))
        
        primary_types = defaultdict(int)
        unused_types = defaultdict(int)
        
        for rep in analysis['primary_representations'].values():
            rep_id = rep.get('representationIdentifier', 'Unknown')
            rep_type = rep.get('representationType', 'Unknown')
            primary_types[f"{rep_id}-{rep_type}"] += 1
        
        for rep in analysis['unused_representations'].values():
            rep_id = rep.get('representationIdentifier', 'Unknown')
            rep_type = rep.get('representationType', 'Unknown')
            unused_types[f"{rep_id}-{rep_type}"] += 1
        
        asset_analysis[asset_file.name] = {
            'analysis': analysis,
            'primary_types': dict(primary_types),
            'unused_types': dict(unused_types)
        }
    
    return asset_analysis

def debug_embedded_converter_issue(official_path: str, assets_dir: str):
    """Debug why embedded converter creates too many shape representations"""
    
    print("🐛 EMBEDDED CONVERTER DEBUG ANALYSIS")
    print("=" * 50)
    
    # Analyze official file for reference
    print(f"\n📄 OFFICIAL JSON REFERENCE: {Path(official_path).name}")
    official_analysis = analyze_product_definition_shapes(official_path)
    
    print(f"  Total Shape Representations: {len(official_analysis['all_shape_representations'])}")
    print(f"  Primary (Referenced): {len(official_analysis['primary_representations'])}")
    print(f"  Unused: {len(official_analysis['unused_representations'])}")
    
    if official_analysis['primary_representations']:
        print(f"  Primary Types:")
        for rep in official_analysis['primary_representations'].values():
            rep_id = rep.get('representationIdentifier', 'Unknown')
            rep_type = rep.get('representationType', 'Unknown')
            print(f"    - {rep_id}: {rep_type}")
    
    # Analyze assets
    print(f"\n📁 ASSETS ANALYSIS: {Path(assets_dir).name}")
    assets_analysis = analyze_assets_usage_pattern(assets_dir)
    
    for asset_name, asset_data in assets_analysis.items():
        analysis = asset_data['analysis']
        print(f"\n  📦 {asset_name}")
        print(f"    Total Shape Representations: {len(analysis['all_shape_representations'])}")
        print(f"    Primary (Referenced): {len(analysis['primary_representations'])}")
        print(f"    Unused: {len(analysis['unused_representations'])}")
        
        if asset_data['primary_types']:
            print(f"    Primary Types:")
            for rep_type, count in asset_data['primary_types'].items():
                print(f"      - {rep_type}: {count}")
        
        if asset_data['unused_types']:
            print(f"    Unused Types:")
            for rep_type, count in asset_data['unused_types'].items():
                print(f"      - {rep_type}: {count}")
    
    # Recommendations
    print(f"\n💡 EMBEDDED CONVERTER RECOMMENDATIONS:")
    print(f"  1. Only extract PRIMARY shape representations (those referenced by ProductDefinitionShape)")
    print(f"  2. Skip unused/duplicate shape representations")
    print(f"  3. Expected result: {len(official_analysis['primary_representations'])} representations instead of {sum(len(a['analysis']['all_shape_representations']) for a in assets_analysis.values())}")
    
    # Show which specific representations should be used
    if assets_analysis:
        first_asset = list(assets_analysis.values())[0]
        if first_asset['analysis']['primary_representations']:
            print(f"\n🎯 CORRECT REPRESENTATIONS TO USE (from first asset):")
            for rep_id, rep in first_asset['analysis']['primary_representations'].items():
                rep_id_val = rep.get('representationIdentifier', 'Unknown')
                rep_type = rep.get('representationType', 'Unknown')
                items_count = len(rep.get('items', []))
                print(f"    ✅ {rep_id_val}: {rep_type} ({items_count} items)")
        
        if first_asset['analysis']['unused_representations']:
            print(f"\n❌ REPRESENTATIONS TO SKIP (from first asset):")
            for rep_id, rep in first_asset['analysis']['unused_representations'].items():
                rep_id_val = rep.get('representationIdentifier', 'Unknown')
                rep_type = rep.get('representationType', 'Unknown')
                items_count = len(rep.get('items', []))
                print(f"    ❌ {rep_id_val}: {rep_type} ({items_count} items)")

def main():
    parser = argparse.ArgumentParser(description='Debug embedded converter shape representation logic')
    parser.add_argument('official_json', help='Path to official ifcJSON file')
    parser.add_argument('assets_dir', help='Path to assets directory')
    
    args = parser.parse_args()
    
    debug_embedded_converter_issue(args.official_json, args.assets_dir)

if __name__ == '__main__':
    main()