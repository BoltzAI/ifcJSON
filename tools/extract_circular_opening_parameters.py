#!/usr/bin/env python3
"""
Extract Circular Opening Parameters Tool

Analyzes circular opening geometry to extract the exact parameters needed
for Step 2 storage and Step 3 recreation.

Usage:
    python extract_circular_opening_parameters.py <ifcjson_file> <opening_id>
    
Examples:
    python extract_circular_opening_parameters.py step1.json "80ac816-0d23-1e5d-f88a-bb0645892c3"
    
Description:
    Extracts geometric parameters from circular IfcFacetedBrep openings to determine
    what information Step 2 needs to store for proper Step 3 recreation.
"""

import sys
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

def load_ifcjson(file_path: str) -> Dict[str, Any]:
    """Load ifcJSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_entity_by_id(data: Dict[str, Any], target_id: str) -> Optional[Dict[str, Any]]:
    """Find entity by globalId"""
    entities = data.get('data', [])
    for entity in entities:
        if entity.get('globalId') == target_id:
            return entity
    return None

def find_entities_by_type(data: Dict[str, Any], entity_type: str) -> List[Dict[str, Any]]:
    """Find all entities of specific type"""
    entities = data.get('data', [])
    return [entity for entity in entities if entity.get('type') == entity_type]

def resolve_reference(data: Dict[str, Any], ref_id: str) -> Optional[Dict[str, Any]]:
    """Resolve reference to actual entity"""
    return find_entity_by_id(data, ref_id)

def extract_cartesian_points(entity: Dict[str, Any], data: Dict[str, Any]) -> List[List[float]]:
    """Extract all cartesian points from an entity recursively"""
    points = []
    
    def collect_points(obj):
        if isinstance(obj, dict):
            if obj.get('type') == 'IfcCartesianPoint':
                coords = obj.get('Coordinates', [])
                if coords:
                    points.append(coords)
            elif 'ref' in obj:
                # Resolve reference
                ref_entity = resolve_reference(data, obj['ref'])
                if ref_entity:
                    collect_points(ref_entity)
            else:
                # Recursively check all values
                for value in obj.values():
                    collect_points(value)
        elif isinstance(obj, list):
            for item in obj:
                collect_points(item)
    
    collect_points(entity)
    return points

def analyze_circle_from_points(points: List[List[float]]) -> Optional[Dict[str, Any]]:
    """Analyze points to determine if they form a circle and extract parameters"""
    if len(points) < 3:
        return None
    
    # Convert to 2D points (assume Z is constant for circular profile)
    points_2d = [(p[0], p[1]) for p in points if len(p) >= 2]
    
    if len(points_2d) < 3:
        return None
    
    # Find center by averaging points (rough approximation)
    center_x = sum(p[0] for p in points_2d) / len(points_2d)
    center_y = sum(p[1] for p in points_2d) / len(points_2d)
    
    # Calculate distances from center
    distances = [math.sqrt((p[0] - center_x)**2 + (p[1] - center_y)**2) for p in points_2d]
    
    # Check if distances are roughly equal (circular)
    avg_radius = sum(distances) / len(distances)
    max_deviation = max(abs(d - avg_radius) for d in distances)
    
    # Consider it circular if deviation is less than 5% of radius
    is_circular = max_deviation < (avg_radius * 0.05) if avg_radius > 0 else False
    
    # Check Z coordinates for depth
    z_coords = [p[2] for p in points if len(p) >= 3]
    depth = max(z_coords) - min(z_coords) if z_coords else 0.0
    
    return {
        'is_circular': is_circular,
        'center': [center_x, center_y],
        'radius': avg_radius,
        'depth': depth,
        'point_count': len(points_2d),
        'max_radius_deviation': max_deviation,
        'all_points_2d': points_2d,
        'z_range': [min(z_coords), max(z_coords)] if z_coords else [0.0, 0.0]
    }

def extract_opening_geometry_details(data: Dict[str, Any], opening_id: str) -> Dict[str, Any]:
    """Extract detailed geometry parameters from opening element"""
    
    print(f"🔍 EXTRACTING CIRCULAR OPENING PARAMETERS")
    print(f"Opening ID: {opening_id}")
    print("=" * 70)
    
    # Find the opening element
    opening = find_entity_by_id(data, opening_id)
    if not opening:
        print(f"❌ Opening element {opening_id} not found")
        return {}
    
    print(f"✅ Found opening: {opening.get('type')} - {opening.get('Name', 'Unnamed')}")
    
    results = {
        'opening_info': {
            'globalId': opening_id,
            'type': opening.get('type'),
            'name': opening.get('Name', 'Unnamed')
        },
        'shape_representations': [],
        'geometry_analysis': {},
        'recommended_step2_storage': {}
    }
    
    # Find representation
    if 'Representation' in opening:
        repr_ref = opening['Representation']
        if 'ref' in repr_ref:
            product_def_shape = resolve_reference(data, repr_ref['ref'])
            if product_def_shape and 'Representations' in product_def_shape:
                representations = product_def_shape['Representations']
                
                print(f"📊 Found {len(representations)} shape representations")
                
                for i, repr_ref in enumerate(representations):
                    if 'ref' in repr_ref:
                        shape_repr = resolve_reference(data, repr_ref['ref'])
                        if shape_repr:
                            repr_id = shape_repr.get('RepresentationIdentifier', 'Unknown')
                            repr_type = shape_repr.get('RepresentationType', 'Unknown')
                            
                            print(f"  📐 Representation {i+1}: {repr_id} ({repr_type})")
                            
                            # Extract geometry details
                            repr_analysis = {
                                'identifier': repr_id,
                                'type': repr_type,
                                'items': []
                            }
                            
                            if 'Items' in shape_repr:
                                items = shape_repr['Items']
                                print(f"    🔧 {len(items)} geometry items")
                                
                                for j, item in enumerate(items):
                                    if 'ref' in item:
                                        geom_item = resolve_reference(data, item['ref'])
                                        if geom_item:
                                            item_type = geom_item.get('type')
                                            print(f"      Item {j+1}: {item_type}")
                                            
                                            item_analysis = {
                                                'type': item_type,
                                                'globalId': geom_item.get('globalId')
                                            }
                                            
                                            # Analyze specific geometry types
                                            if item_type == 'IfcExtrudedAreaSolid':
                                                # Extract extrusion parameters
                                                depth = geom_item.get('Depth')
                                                item_analysis['depth'] = depth
                                                print(f"        Depth: {depth}")
                                                
                                                # Analyze swept area (profile)
                                                if 'SweptArea' in geom_item and 'ref' in geom_item['SweptArea']:
                                                    profile = resolve_reference(data, geom_item['SweptArea']['ref'])
                                                    if profile:
                                                        profile_type = profile.get('type')
                                                        print(f"        Profile: {profile_type}")
                                                        item_analysis['profile_type'] = profile_type
                                                        
                                                        if 'OuterBoundary' in profile and 'ref' in profile['OuterBoundary']:
                                                            boundary = resolve_reference(data, profile['OuterBoundary']['ref'])
                                                            if boundary:
                                                                boundary_type = boundary.get('type')
                                                                print(f"        Boundary: {boundary_type}")
                                                                
                                                                # Extract points from boundary
                                                                points = extract_cartesian_points(boundary, data)
                                                                print(f"        Points found: {len(points)}")
                                                                
                                                                if points:
                                                                    # Analyze for circular properties
                                                                    circle_analysis = analyze_circle_from_points(points)
                                                                    if circle_analysis:
                                                                        print(f"        🎯 Circle Analysis:")
                                                                        print(f"          Is Circular: {circle_analysis['is_circular']}")
                                                                        print(f"          Center: {circle_analysis['center']}")
                                                                        print(f"          Radius: {circle_analysis['radius']:.3f}")
                                                                        print(f"          Point Count: {circle_analysis['point_count']}")
                                                                        print(f"          Max Deviation: {circle_analysis['max_radius_deviation']:.4f}")
                                                                        
                                                                        item_analysis['circle_analysis'] = circle_analysis
                                                                        
                                                                        # Store for Step 2 recommendations
                                                                        if circle_analysis['is_circular']:
                                                                            results['recommended_step2_storage'] = {
                                                                                'geometryType': 'circular_opening',
                                                                                'openingShape': 'circular',
                                                                                'dimensions': {
                                                                                    'radius': round(circle_analysis['radius'], 4),
                                                                                    'depth': depth,
                                                                                    'center_offset': circle_analysis['center']
                                                                                },
                                                                                'tessellation': {
                                                                                    'point_count': circle_analysis['point_count'],
                                                                                    'quality': 'high' if circle_analysis['point_count'] >= 16 else 'medium'
                                                                                },
                                                                                'originalGeometryType': 'IfcExtrudedAreaSolid',
                                                                                'profileType': profile_type,
                                                                                'boundaryType': boundary_type
                                                                            }
                                                            
                                            elif item_type == 'IfcFacetedBrep':
                                                # Extract faceted brep parameters
                                                points = extract_cartesian_points(geom_item, data)
                                                print(f"        IfcFacetedBrep points: {len(points)}")
                                                
                                                # Analyze outer shell
                                                if 'Outer' in geom_item and 'ref' in geom_item['Outer']:
                                                    shell = resolve_reference(data, geom_item['Outer']['ref'])
                                                    if shell and 'CfsFaces' in shell:
                                                        face_count = len(shell['CfsFaces'])
                                                        print(f"        Faces: {face_count}")
                                                        item_analysis['face_count'] = face_count
                                                        
                                                        if points:
                                                            circle_analysis = analyze_circle_from_points(points)
                                                            if circle_analysis:
                                                                print(f"        🎯 IfcFacetedBrep Circle Analysis:")
                                                                print(f"          Is Circular: {circle_analysis['is_circular']}")
                                                                print(f"          Radius: {circle_analysis['radius']:.3f}")
                                                                print(f"          Face Count: {face_count}")
                                                                
                                                                item_analysis['circle_analysis'] = circle_analysis
                                                                
                                                                # Store high-detail recommendation for IfcFacetedBrep
                                                                if circle_analysis['is_circular']:
                                                                    results['recommended_step2_storage'] = {
                                                                        'geometryType': 'circular_opening_detailed',
                                                                        'openingShape': 'circular',
                                                                        'dimensions': {
                                                                            'radius': round(circle_analysis['radius'], 4),
                                                                            'depth': circle_analysis['depth'],
                                                                            'center_offset': circle_analysis['center']
                                                                        },
                                                                        'tessellation': {
                                                                            'face_count': face_count,
                                                                            'point_count': circle_analysis['point_count'],
                                                                            'quality': 'very_high' if face_count >= 100 else 'high'
                                                                        },
                                                                        'originalGeometryType': 'IfcFacetedBrep',
                                                                        'mesh_complexity': 'high_detail_circular'
                                                                    }
                                            
                                            repr_analysis['items'].append(item_analysis)
                            
                            results['shape_representations'].append(repr_analysis)
    
    return results

def main():
    if len(sys.argv) != 3:
        print("Usage: python extract_circular_opening_parameters.py <ifcjson_file> <opening_id>")
        print("\nExamples:")
        print("  python extract_circular_opening_parameters.py step1.json '80ac816-0d23-1e5d-f88a-bb0645892c3'")
        print("\nDescription:")
        print("  Extracts geometric parameters needed for Step 2 storage and Step 3 recreation")
        return
    
    ifcjson_file = sys.argv[1]
    opening_id = sys.argv[2]
    
    try:
        data = load_ifcjson(ifcjson_file)
        results = extract_opening_geometry_details(data, opening_id)
        
        if results.get('recommended_step2_storage'):
            print(f"\n🎯 RECOMMENDED STEP 2 STORAGE")
            print("=" * 50)
            print(json.dumps(results['recommended_step2_storage'], indent=2))
            
            print(f"\n📋 STEP 3 RECREATION REQUIREMENTS")
            print("=" * 50)
            storage = results['recommended_step2_storage']
            if storage.get('geometryType') == 'circular_opening_detailed':
                print("✅ Generate IfcFacetedBrep with:")
                print(f"  • Radius: {storage['dimensions']['radius']}")
                print(f"  • Depth: {storage['dimensions']['depth']}")  
                print(f"  • Face count: {storage['tessellation']['face_count']}")
                print(f"  • Tessellation quality: {storage['tessellation']['quality']}")
            elif storage.get('geometryType') == 'circular_opening':
                print("✅ Generate IfcExtrudedAreaSolid with circular profile:")
                print(f"  • Radius: {storage['dimensions']['radius']}")
                print(f"  • Depth: {storage['dimensions']['depth']}")
                print(f"  • Profile points: {storage['tessellation']['point_count']}")
        
        else:
            print(f"\n❌ No circular geometry detected or insufficient parameters extracted")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()