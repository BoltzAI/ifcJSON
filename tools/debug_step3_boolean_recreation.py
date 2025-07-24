#!/usr/bin/env python3
"""
Debug Step 3 Boolean Recreation

Investigates why boolean operations from assets aren't appearing in Step 3 output.
Specifically examines how _create_shape_representation_from_asset processes boolean operations.

Usage:
    python debug_step3_boolean_recreation.py <simplified.json> <assets_dir> <wall_name>
    
Example:
    python debug_step3_boolean_recreation.py \
        ../../out-temp/step2_simplified_json/OrangeHouse_simplified.json \
        ../../out-temp/assets/OrangeHouse \
        'Wand-Ext-OG-3'
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

def find_wall_in_simplified(simplified_data: Dict[str, Any], wall_name: str) -> Optional[Dict[str, Any]]:
    """Find wall in simplified JSON"""
    for storey in simplified_data.get('building', {}).get('storeys', []):
        for wall in storey.get('elements', {}).get('walls', []):
            if wall.get('name') == wall_name:
                return wall
    return None

def analyze_asset_content(asset_id: str, assets_dir: str) -> Dict[str, Any]:
    """Analyze asset content"""
    asset_file = Path(assets_dir) / f"{asset_id}.json"
    
    if not asset_file.exists():
        return {"error": "Asset file not found"}
    
    with open(asset_file, 'r') as f:
        asset_data = json.load(f)
    
    entities = asset_data.get('data', [])
    boolean_ops = []
    shape_reprs = []
    all_entity_types = {}
    
    for entity in entities:
        entity_type = entity.get('type', 'Unknown')
        all_entity_types[entity_type] = all_entity_types.get(entity_type, 0) + 1
        
        if entity_type == 'IfcBooleanClippingResult':
            boolean_ops.append({
                'globalId': entity.get('globalId'),
                'operator': entity.get('operator'),
                'hasFirstOperand': 'firstOperand' in entity,
                'hasSecondOperand': 'secondOperand' in entity
            })
        elif entity_type == 'IfcShapeRepresentation':
            shape_reprs.append({
                'globalId': entity.get('globalId'),
                'representationIdentifier': entity.get('representationIdentifier'),
                'itemCount': len(entity.get('items', [])),
                'items': [item.get('type') if isinstance(item, dict) else 'embedded' for item in entity.get('items', [])]
            })
    
    return {
        'total_entities': len(entities),
        'entity_types': all_entity_types,
        'boolean_operations': boolean_ops,
        'shape_representations': shape_reprs
    }

def simulate_step3_processing(wall_data: Dict[str, Any], asset_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate how Step 3 processes the asset"""
    
    # Step 3 processes geometry as asset_library
    if wall_data.get('geometry', {}).get('geometryType') != 'asset_library':
        return {"error": "Wall doesn't use asset library"}
    
    asset_id = wall_data['geometry']['assetId']
    
    # Simulate _create_shape_representation_from_asset logic
    
    # 1. It loads all entities from asset (which we analyzed)
    total_entities_loaded = asset_analysis['total_entities']
    boolean_ops_loaded = len(asset_analysis['boolean_operations'])
    
    # 2. It assigns new globalIds (simulation)
    globalid_mapping_count = total_entities_loaded
    
    # 3. It finds target representation (Body)
    body_representations = [rep for rep in asset_analysis['shape_representations'] 
                           if rep['representationIdentifier'] == 'Body']
    
    # 4. It adds ALL entities to main entities list
    entities_added_to_main_list = total_entities_loaded
    
    # 5. The problem: What happens to boolean operations?
    # Are they properly linked to the target representation?
    
    # Check if Body representation references boolean operations
    body_rep_items = []
    if body_representations:
        body_rep = body_representations[0]
        body_rep_items = body_rep.get('items', [])
    
    return {
        'asset_id': asset_id,
        'entities_loaded': total_entities_loaded,
        'boolean_ops_loaded': boolean_ops_loaded,
        'globalid_mappings_created': globalid_mapping_count,
        'body_representations_found': len(body_representations),
        'body_representation_items': body_rep_items,
        'entities_added_to_main_list': entities_added_to_main_list,
        'potential_issue': 'Boolean operations loaded but may not be referenced by Body representation'
    }

def main():
    if len(sys.argv) != 4:
        print("Usage: python debug_step3_boolean_recreation.py <simplified.json> <assets_dir> <wall_name>")
        print("\nExamples:")
        print("  python debug_step3_boolean_recreation.py \\")
        print("    ../../out-temp/step2_simplified_json/OrangeHouse_simplified.json \\")
        print("    ../../out-temp/assets/OrangeHouse \\")
        print("    'Wand-Ext-OG-3'")
        print("\nDescription:")
        print("  Investigates why boolean operations from assets aren't appearing in Step 3 output")
        return
    
    simplified_file, assets_dir, wall_name = sys.argv[1:4]
    
    print(f"🔍 DEBUG STEP 3 BOOLEAN RECREATION")
    print(f"Wall: {wall_name}")
    print(f"Simplified: {simplified_file}")
    print(f"Assets: {assets_dir}")
    print("=" * 100)
    
    try:
        # Load simplified JSON
        with open(simplified_file, 'r') as f:
            simplified_data = json.load(f)
        
        # Find wall
        wall_data = find_wall_in_simplified(simplified_data, wall_name)
        if not wall_data:
            print(f"❌ Wall '{wall_name}' not found in simplified JSON")
            return
        
        print(f"✅ Found wall: {wall_data.get('globalId')}")
        print(f"🏗️  Wall type: {wall_data.get('type')}")
        
        # Analyze asset
        asset_id = wall_data.get('geometry', {}).get('assetId')
        if not asset_id:
            print(f"❌ Wall has no asset ID")
            return
        
        print(f"📦 Asset ID: {asset_id}")
        
        asset_analysis = analyze_asset_content(asset_id, assets_dir)
        if 'error' in asset_analysis:
            print(f"❌ Asset analysis failed: {asset_analysis['error']}")
            return
        
        print(f"\n📊 ASSET ANALYSIS")
        print("-" * 60)
        print(f"Total entities: {asset_analysis['total_entities']}")
        print(f"Entity types: {asset_analysis['entity_types']}")
        print(f"Boolean operations: {len(asset_analysis['boolean_operations'])}")
        
        if asset_analysis['boolean_operations']:
            print(f"\n🔧 BOOLEAN OPERATIONS DETAILS:")
            for i, bool_op in enumerate(asset_analysis['boolean_operations'], 1):
                print(f"  {i}. ID: {bool_op['globalId']}")
                print(f"     Operator: {bool_op['operator']}")
                print(f"     First operand: {'✅' if bool_op['hasFirstOperand'] else '❌'}")
                print(f"     Second operand: {'✅' if bool_op['hasSecondOperand'] else '❌'}")
        
        print(f"\n🎭 SHAPE REPRESENTATIONS:")
        for i, shape_repr in enumerate(asset_analysis['shape_representations'], 1):
            print(f"  {i}. {shape_repr['representationIdentifier']} ({shape_repr['globalId']})")
            print(f"     Items: {shape_repr['itemCount']} - {shape_repr['items']}")
        
        # Simulate Step 3 processing
        step3_simulation = simulate_step3_processing(wall_data, asset_analysis)
        
        print(f"\n🔬 STEP 3 PROCESSING SIMULATION")
        print("-" * 60)
        for key, value in step3_simulation.items():
            if key != 'potential_issue':
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        if 'potential_issue' in step3_simulation:
            print(f"\n⚠️  POTENTIAL ISSUE:")
            print(f"   {step3_simulation['potential_issue']}")
        
        # Analysis conclusion
        print(f"\n💡 ANALYSIS CONCLUSION")
        print("-" * 60)
        if asset_analysis['boolean_operations']:
            print("✅ Boolean operations ARE present in asset")
            print("⚠️  Issue: Step 3 loads them but they don't appear in final output")
            print("🔍 Next step: Check if Body representation references boolean operations")
            print("🔍 Or check if boolean operations are filtered out later in pipeline")
        else:
            print("❌ No boolean operations found in asset - this is the root issue")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()