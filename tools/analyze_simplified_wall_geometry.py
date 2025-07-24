#!/usr/bin/env python3
"""
Simplified JSON Wall Geometry Analyzer

Analyzes wall geometry in Step 2 simplified JSON format, focusing on:
- Asset library references and geometry type
- Asset geometry content analysis 
- Comparison with Step 1 ifcJSON geometry
"""

import json
import sys
import os
from typing import Dict, List, Any, Optional

def load_json_data(file_path: str) -> Dict[str, Any]:
    """Load JSON data from file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error loading JSON file: {e}")
        sys.exit(1)

def find_wall_in_simplified(data: Dict[str, Any], wall_name: str) -> Optional[Dict[str, Any]]:
    """Find wall in simplified JSON structure"""
    
    for storey in data.get('building', {}).get('storeys', []):
        for wall in storey.get('elements', {}).get('walls', []):
            if wall.get('name') == wall_name:
                return {
                    'wall': wall,
                    'storey_name': storey.get('name'),
                    'storey_globalId': storey.get('globalId')
                }
    return None

def analyze_asset_geometry(asset_id: str, assets_dir: str) -> Dict[str, Any]:
    """Analyze geometry content in asset file"""
    
    result = {
        'asset_found': False,
        'geometry_entities': 0,
        'face_count': 0,
        'entity_types': {},
        'boolean_operations': 0,
        'circular_polylines': []
    }
    
    # Find asset file
    asset_file = None
    for file in os.listdir(assets_dir):
        if asset_id in file and file.endswith('.json'):
            asset_file = os.path.join(assets_dir, file)
            break
    
    if not asset_file:
        print(f"    ❌ Asset file not found for {asset_id}")
        return result
    
    result['asset_found'] = True
    asset_data = load_json_data(asset_file)
    entities = asset_data.get('data', [])
    result['geometry_entities'] = len(entities)
    
    print(f"    📄 Asset file: {os.path.basename(asset_file)}")
    print(f"    🔢 Geometry entities: {len(entities)}")
    
    # Analyze entities
    for entity in entities:
        entity_type = entity.get('type', 'unknown')
        result['entity_types'][entity_type] = result['entity_types'].get(entity_type, 0) + 1
        
        # Check for boolean operations
        if entity_type == 'IfcBooleanClippingResult':
            result['boolean_operations'] += 1
            print(f"    🔧 Boolean operation found: {entity.get('globalId', 'inline')[:8]}...")
        
        # Check for polylines (circular geometry indicators)
        elif entity_type == 'IfcPolyline':
            points = entity.get('points', [])
            point_count = len(points)
            if point_count > 20:
                result['circular_polylines'].append({
                    'id': entity.get('globalId', 'inline'),
                    'points': point_count
                })
                print(f"    ⭕ High-resolution polyline: {point_count} points (likely circular)")
        
        # Check for mesh geometry
        elif entity_type == 'IfcFacetedBrep':
            # Try to count faces if possible
            faces = entity.get('outer', {}).get('cfsFaces', [])
            if faces:
                result['face_count'] += len(faces)
                print(f"    🔺 IfcFacetedBrep with {len(faces)} faces")
    
    return result

def analyze_simplified_wall(simplified_path: str, assets_dir: str, wall_name: str) -> None:
    """Main analysis function for simplified JSON wall geometry"""
    
    print(f"🔍 ANALYZING SIMPLIFIED WALL GEOMETRY")
    print(f"Wall: {wall_name}")
    print(f"Simplified JSON: {simplified_path}")
    print(f"Assets directory: {assets_dir}")
    print("=" * 80)
    
    # Load simplified JSON
    data = load_json_data(simplified_path)
    
    # Find wall
    wall_data = find_wall_in_simplified(data, wall_name)
    if not wall_data:
        print(f"❌ Wall '{wall_name}' not found in simplified JSON")
        return
    
    wall = wall_data['wall']
    storey_name = wall_data['storey_name']
    
    print(f"✅ Found wall in storey: {storey_name}")
    print(f"📍 Wall GlobalId: {wall.get('globalId')}")
    print(f"🏗️  Wall Type: {wall.get('type')}")
    
    # Analyze geometry
    geometry = wall.get('geometry', {})
    geometry_type = geometry.get('geometryType', 'unknown')
    
    print(f"\\n📐 GEOMETRY ANALYSIS")
    print(f"  Geometry type: {geometry_type}")
    
    if geometry_type == 'asset_library':
        asset_id = geometry.get('assetId')
        library_source = geometry.get('librarySource', 'unknown')
        
        print(f"  Asset ID: {asset_id}")
        print(f"  Library source: {library_source}")
        
        # Check instance parameters
        instance_params = geometry.get('instanceParameters', {})
        if 'overallDimensions' in instance_params:
            dims = instance_params['overallDimensions']
            print(f"  Dimensions: {dims.get('width')}x{dims.get('height')}x{dims.get('thickness')}")
        
        if 'transformation' in instance_params:
            transform = instance_params['transformation']
            origin = transform.get('origin', [0, 0, 0])
            print(f"  Origin: {origin}")
        
        # Analyze asset geometry content
        if assets_dir and asset_id:
            print(f"\\n🔍 ASSET GEOMETRY ANALYSIS")
            asset_analysis = analyze_asset_geometry(asset_id, assets_dir)
            
            if asset_analysis['asset_found']:
                print(f"\\n📊 ASSET SUMMARY:")
                for entity_type, count in asset_analysis['entity_types'].items():
                    print(f"  {entity_type}: {count}")
                
                if asset_analysis['boolean_operations'] > 0:
                    print(f"\\n🔧 Boolean operations: {asset_analysis['boolean_operations']}")
                    print("  💡 This indicates wall has openings/voids")
                
                if asset_analysis['circular_polylines']:
                    print(f"\\n⭕ Circular polylines detected: {len(asset_analysis['circular_polylines'])}")
                    for poly in asset_analysis['circular_polylines']:
                        print(f"    • {poly['points']} points")
                    print("  💡 This indicates circular/curved geometry")
                
                if asset_analysis['face_count'] > 0:
                    print(f"\\n🔺 Total faces in asset: {asset_analysis['face_count']}")
    
    else:
        print(f"  ⚠️  Non-asset geometry type: {geometry_type}")
        if 'dimensions' in geometry:
            dims = geometry['dimensions']
            print(f"  Dimensions: {dims}")

def main():
    """Main entry point"""
    
    if len(sys.argv) < 4:
        print("Usage: python analyze_simplified_wall_geometry.py <simplified.json> <assets_dir> <wall_name>")
        print()
        print("Examples:")
        print("  python analyze_simplified_wall_geometry.py ../../../out-todo70/step2_simplified_json/OrangeHouse_simplified.json ../../../out-todo70/assets/OrangeHouse 'Wand-Ext-OG-1'")
        print()
        print("Description:")
        print("  Analyzes wall geometry in Step 2 simplified JSON format")
        print("  Examines asset library references and geometry content")
        sys.exit(1)
    
    simplified_path = sys.argv[1]
    assets_dir = sys.argv[2] 
    wall_name = sys.argv[3]
    
    analyze_simplified_wall(simplified_path, assets_dir, wall_name)

if __name__ == "__main__":
    main()