#!/usr/bin/env python3
"""
Geometry Pipeline Flow Tracer

Traces wall geometry through the complete pipeline: Step 1 → Step 2 → Step 3
to identify exactly when and where geometry differences occur.
"""

import json
import sys
import os
from typing import Dict, List, Any, Optional, Tuple

def load_json_data(file_path: str) -> Dict[str, Any]:
    """Load JSON data from file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error loading {file_path}: {e}")
        sys.exit(1)

def find_wall_step1(entities: List[Dict], wall_name: str) -> Optional[Dict[str, Any]]:
    """Find wall in Step 1 ifcJSON entities"""
    for entity in entities:
        if entity.get('name') == wall_name:
            return entity
    return None

def find_wall_step2(data: Dict[str, Any], wall_name: str) -> Optional[Dict[str, Any]]:
    """Find wall in Step 2 simplified JSON"""
    for storey in data.get('building', {}).get('storeys', []):
        for wall in storey.get('elements', {}).get('walls', []):
            if wall.get('name') == wall_name:
                return wall
    return None

def find_wall_step3(entities: List[Dict], wall_name: str) -> Optional[Dict[str, Any]]:
    """Find wall in Step 3 ifcJSON entities"""
    for entity in entities:
        if entity.get('name') == wall_name:
            return entity
    return None

def analyze_step1_geometry(wall: Dict[str, Any], entity_lookup: Dict[str, Dict]) -> Dict[str, Any]:
    """Analyze wall geometry in Step 1 ifcJSON"""
    
    result = {
        'representations': [],
        'total_entities': 0,
        'boolean_operations': 0,
        'circular_polylines': 0,
        'geometry_types': set()
    }
    
    # Get representation
    representation = wall.get('representation', {})
    if 'ref' in representation:
        prod_def = entity_lookup.get(representation['ref'])
        if prod_def:
            shape_reps = prod_def.get('representations', [])
            
            for rep_ref in shape_reps:
                if isinstance(rep_ref, dict) and 'ref' in rep_ref:
                    shape_rep = entity_lookup.get(rep_ref['ref'])
                    if shape_rep:
                        rep_id = shape_rep.get('representationIdentifier', 'unknown')
                        rep_type = shape_rep.get('representationType', 'unknown')
                        items = shape_rep.get('items', [])
                        
                        rep_analysis = {
                            'identifier': rep_id,
                            'type': rep_type,
                            'item_count': len(items)
                        }
                        
                        # Analyze items
                        for item_ref in items:
                            if isinstance(item_ref, dict) and 'ref' in item_ref:
                                item_entity = entity_lookup.get(item_ref['ref'])
                                if item_entity:
                                    item_type = item_entity.get('type')
                                    result['geometry_types'].add(item_type)
                                    
                                    if item_type == 'IfcBooleanClippingResult':
                                        result['boolean_operations'] += 1
                        
                        result['representations'].append(rep_analysis)
    
    elif representation.get('type') == 'IfcProductDefinitionShape':
        # Handle embedded representation
        reps = representation.get('representations', [])
        result['representations'] = [{'identifier': 'embedded', 'item_count': len(reps)}]
    
    return result

def analyze_step2_geometry(wall: Dict[str, Any], assets_dir: str) -> Dict[str, Any]:
    """Analyze wall geometry in Step 2 simplified JSON"""
    
    result = {
        'geometry_type': 'unknown',
        'asset_id': None,
        'asset_found': False,
        'asset_entities': 0,
        'asset_boolean_ops': 0,
        'asset_circular_polylines': 0,
        'dimensions': None
    }
    
    geometry = wall.get('geometry', {})
    geometry_type = geometry.get('geometryType', 'unknown')
    result['geometry_type'] = geometry_type
    
    if geometry_type == 'asset_library':
        asset_id = geometry.get('assetId')
        result['asset_id'] = asset_id
        
        # Check instance parameters
        instance_params = geometry.get('instanceParameters', {})
        if 'overallDimensions' in instance_params:
            result['dimensions'] = instance_params['overallDimensions']
        
        # Analyze asset file
        if assets_dir and asset_id:
            for file in os.listdir(assets_dir):
                if asset_id in file and file.endswith('.json'):
                    asset_file = os.path.join(assets_dir, file)
                    try:
                        asset_data = load_json_data(asset_file)
                        entities = asset_data.get('data', [])
                        
                        result['asset_found'] = True
                        result['asset_entities'] = len(entities)
                        
                        for entity in entities:
                            entity_type = entity.get('type', 'unknown')
                            if entity_type == 'IfcBooleanClippingResult':
                                result['asset_boolean_ops'] += 1
                            elif entity_type == 'IfcPolyline':
                                points = entity.get('points', [])
                                if len(points) > 20:
                                    result['asset_circular_polylines'] += 1
                        
                        break
                    except:
                        pass
    
    return result

def analyze_step3_geometry(wall: Dict[str, Any], entity_lookup: Dict[str, Dict]) -> Dict[str, Any]:
    """Analyze wall geometry in Step 3 ifcJSON"""
    
    result = {
        'representations': [],
        'total_entities': 0,
        'boolean_operations': 0,
        'geometry_types': set()
    }
    
    # Get representation (similar to Step 1 analysis)
    representation = wall.get('representation', {})
    if 'ref' in representation:
        prod_def = entity_lookup.get(representation['ref'])
        if prod_def:
            shape_reps = prod_def.get('representations', [])
            
            for rep_ref in shape_reps:
                if isinstance(rep_ref, dict) and 'ref' in rep_ref:
                    shape_rep = entity_lookup.get(rep_ref['ref'])
                    if shape_rep:
                        rep_id = shape_rep.get('representationIdentifier', 'unknown')
                        rep_type = shape_rep.get('representationType', 'unknown')
                        items = shape_rep.get('items', [])
                        
                        rep_analysis = {
                            'identifier': rep_id,
                            'type': rep_type,
                            'item_count': len(items)
                        }
                        
                        # Analyze items
                        for item_ref in items:
                            if isinstance(item_ref, dict) and 'ref' in item_ref:
                                item_entity = entity_lookup.get(item_ref['ref'])
                                if item_entity:
                                    item_type = item_entity.get('type')
                                    result['geometry_types'].add(item_type)
                                    
                                    if item_type == 'IfcBooleanClippingResult':
                                        result['boolean_operations'] += 1
                        
                        result['representations'].append(rep_analysis)
    
    elif representation.get('type') == 'IfcProductDefinitionShape':
        # Handle embedded representation
        reps = representation.get('representations', [])
        result['representations'] = [{'identifier': 'embedded', 'item_count': len(reps)}]
    
    return result

def trace_pipeline_flow(step1_path: str, step2_path: str, step3_path: str, assets_dir: str, wall_name: str) -> None:
    """Main pipeline flow tracing function"""
    
    print(f"🔍 TRACING GEOMETRY PIPELINE FLOW")
    print(f"Wall: {wall_name}")
    print(f"Step 1: {os.path.basename(step1_path)}")
    print(f"Step 2: {os.path.basename(step2_path)}")
    print(f"Step 3: {os.path.basename(step3_path)}")
    print(f"Assets: {os.path.basename(assets_dir)}")
    print("=" * 100)
    
    # Load all data
    step1_data = load_json_data(step1_path)
    step2_data = load_json_data(step2_path)
    step3_data = load_json_data(step3_path)
    
    step1_entities = step1_data.get('data', [])
    step3_entities = step3_data.get('data', [])
    
    step1_lookup = {entity.get('globalId'): entity for entity in step1_entities if entity.get('globalId')}
    step3_lookup = {entity.get('globalId'): entity for entity in step3_entities if entity.get('globalId')}
    
    # Find wall in each step
    wall1 = find_wall_step1(step1_entities, wall_name)
    wall2 = find_wall_step2(step2_data, wall_name)  
    wall3 = find_wall_step3(step3_entities, wall_name)
    
    if not wall1:
        print(f"❌ Wall '{wall_name}' not found in Step 1")
        return
    if not wall2:
        print(f"❌ Wall '{wall_name}' not found in Step 2")
        return
    if not wall3:
        print(f"❌ Wall '{wall_name}' not found in Step 3")
        return
    
    print(f"✅ Wall found in all pipeline steps")
    print(f"   GlobalId: {wall1.get('globalId')}")
    
    # Analyze each step
    print(f"\\n📊 STEP 1 ANALYSIS (Original ifcJSON)")
    print("-" * 60)
    step1_analysis = analyze_step1_geometry(wall1, step1_lookup)
    
    print(f"Representations: {len(step1_analysis['representations'])}")
    for rep in step1_analysis['representations']:
        print(f"  • {rep['identifier']}: {rep['item_count']} items")
    
    print(f"Boolean operations: {step1_analysis['boolean_operations']}")
    print(f"Geometry types: {', '.join(step1_analysis['geometry_types'])}")
    
    print(f"\\n📊 STEP 2 ANALYSIS (Simplified JSON)")
    print("-" * 60)
    step2_analysis = analyze_step2_geometry(wall2, assets_dir)
    
    print(f"Geometry type: {step2_analysis['geometry_type']}")
    if step2_analysis['asset_id']:
        print(f"Asset ID: {step2_analysis['asset_id']}")
        print(f"Asset found: {'✅' if step2_analysis['asset_found'] else '❌'}")
        if step2_analysis['asset_found']:
            print(f"Asset entities: {step2_analysis['asset_entities']}")
            print(f"Asset boolean ops: {step2_analysis['asset_boolean_ops']}")
            print(f"Asset circular polylines: {step2_analysis['asset_circular_polylines']}")
    
    if step2_analysis['dimensions']:
        dims = step2_analysis['dimensions']
        print(f"Dimensions: {dims.get('width')}×{dims.get('height')}×{dims.get('thickness')}")
    
    print(f"\\n📊 STEP 3 ANALYSIS (Reconstructed ifcJSON)")
    print("-" * 60)
    step3_analysis = analyze_step3_geometry(wall3, step3_lookup)
    
    print(f"Representations: {len(step3_analysis['representations'])}")
    for rep in step3_analysis['representations']:
        print(f"  • {rep['identifier']}: {rep['item_count']} items")
    
    print(f"Boolean operations: {step3_analysis['boolean_operations']}")
    print(f"Geometry types: {', '.join(step3_analysis['geometry_types'])}")
    
    # Compare and identify differences
    print(f"\\n🔍 PIPELINE COMPARISON ANALYSIS")
    print("=" * 100)
    
    print(f"\\n📈 REPRESENTATION COUNT:")
    print(f"  Step 1 → Step 2: {len(step1_analysis['representations'])} representations → asset library")
    print(f"  Step 2 → Step 3: asset library → {len(step3_analysis['representations'])} representations")
    
    if len(step1_analysis['representations']) != len(step3_analysis['representations']):
        lost_reps = len(step1_analysis['representations']) - len(step3_analysis['representations'])
        print(f"  ⚠️  REPRESENTATION LOSS: {lost_reps} representations lost")
        print(f"     Step 1 had: {[r['identifier'] for r in step1_analysis['representations']]}")
        print(f"     Step 3 has: {[r['identifier'] for r in step3_analysis['representations']]}")
    
    print(f"\\n🔧 BOOLEAN OPERATIONS:")
    print(f"  Step 1: {step1_analysis['boolean_operations']} boolean operations")
    print(f"  Step 2: {step2_analysis['asset_boolean_ops']} boolean operations (in asset)")
    print(f"  Step 3: {step3_analysis['boolean_operations']} boolean operations")
    
    if step1_analysis['boolean_operations'] != step3_analysis['boolean_operations']:
        print(f"  ⚠️  BOOLEAN OPERATION LOSS: {step1_analysis['boolean_operations']} → {step3_analysis['boolean_operations']}")
    
    print(f"\\n⭕ CIRCULAR GEOMETRY:")
    print(f"  Step 1: Not directly measurable (parametric)")
    print(f"  Step 2: {step2_analysis['asset_circular_polylines']} high-resolution polylines")
    print(f"  Step 3: Not directly measurable (parametric)")
    
    if step2_analysis['asset_circular_polylines'] > 0:
        print(f"  ✅ CIRCULAR GEOMETRY PRESERVED in Step 2 assets")
    else:
        print(f"  ⚠️  NO CIRCULAR GEOMETRY detected in Step 2 assets")
    
    print(f"\\n💡 KEY FINDINGS:")
    if not step2_analysis['asset_found']:
        print(f"  🚨 CRITICAL: Asset not found - geometry lost in Step 1→2")
    elif step2_analysis['asset_entities'] == 0:
        print(f"  🚨 CRITICAL: Empty asset - geometry extraction failed in Step 1→2")
    elif len(step1_analysis['representations']) > len(step3_analysis['representations']):
        print(f"  ⚠️  Representation filtering occurred in Step 2→3")
    elif step1_analysis['boolean_operations'] > step3_analysis['boolean_operations']:
        print(f"  ⚠️  Boolean operations lost in Step 2→3")
    else:
        print(f"  ✅ Structure preserved - differences likely in tessellation quality")

def main():
    """Main entry point"""
    
    if len(sys.argv) < 6:
        print("Usage: python trace_geometry_pipeline_flow.py <step1.json> <step2.json> <step3.json> <assets_dir> <wall_name>")
        print()
        print("Examples:")
        print("  python trace_geometry_pipeline_flow.py \\")
        print("    ../../../out-todo70/step1_official_json/OrangeHouse.json \\")
        print("    ../../../out-todo70/step2_simplified_json/OrangeHouse_simplified.json \\")
        print("    ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json \\")
        print("    ../../../out-todo70/assets/OrangeHouse \\")
        print("    'Wand-Ext-OG-1'")
        print()
        print("Description:")
        print("  Traces wall geometry through complete pipeline to identify where differences occur")
        sys.exit(1)
    
    step1_path = sys.argv[1]
    step2_path = sys.argv[2]
    step3_path = sys.argv[3]
    assets_dir = sys.argv[4]
    wall_name = sys.argv[5]
    
    trace_pipeline_flow(step1_path, step2_path, step3_path, assets_dir, wall_name)

if __name__ == "__main__":
    main()