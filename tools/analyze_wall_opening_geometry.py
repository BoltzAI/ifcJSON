#!/usr/bin/env python3
"""
Wall Opening Geometry Analyzer

Analyzes wall geometry differences between ifcJSON files, focusing on:
- Boolean operations (openings/voids)
- Opening element details
- Polyline/curve definitions
- Geometric parameters that affect circular vs rectangular appearance
"""

import json
import sys
from typing import Dict, List, Any, Optional, Tuple

def load_json_data(file_path: str) -> Dict[str, Any]:
    """Load JSON data from file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error loading JSON file: {e}")
        sys.exit(1)

def find_element_by_name(entities: List[Dict], element_name: str) -> Optional[Dict[str, Any]]:
    """Find element by name in entities list"""
    for entity in entities:
        if entity.get('name') == element_name:
            return entity
    return None

def trace_boolean_operations(entity: Dict[str, Any], entity_lookup: Dict[str, Dict], depth: int = 0) -> Dict[str, Any]:
    """Trace through boolean operations to find opening geometry"""
    
    indent = "  " * depth
    result = {
        'type': entity.get('type'),
        'id': entity.get('globalId', 'inline'),
        'operations': []
    }
    
    if entity.get('type') == 'IfcBooleanClippingResult':
        print(f"{indent}🔧 Boolean Clipping Operation:")
        
        # First operand (usually the base geometry)
        first_operand = entity.get('firstOperand', {})
        if 'ref' in first_operand:
            first_entity = entity_lookup.get(first_operand['ref'])
            if first_entity:
                print(f"{indent}  First: {first_entity.get('type')} ({first_operand['ref'][:8]}...)")
                first_analysis = trace_boolean_operations(first_entity, entity_lookup, depth + 1)
                result['operations'].append(('first', first_analysis))
        
        # Second operand (the cutting geometry - THIS IS THE OPENING!)
        second_operand = entity.get('secondOperand', {})
        if 'ref' in second_operand:
            second_entity = entity_lookup.get(second_operand['ref'])
            if second_entity:
                print(f"{indent}  Second (OPENING): {second_entity.get('type')} ({second_operand['ref'][:8]}...)")
                opening_analysis = analyze_opening_geometry(second_entity, entity_lookup, depth + 1)
                result['operations'].append(('opening', opening_analysis))
        
    elif entity.get('type') == 'IfcExtrudedAreaSolid':
        print(f"{indent}📦 Extruded Solid")
        profile_analysis = analyze_swept_area(entity, entity_lookup, depth + 1)
        result['profile'] = profile_analysis
        
    elif entity.get('type') == 'IfcPolygonalBoundedHalfSpace':
        print(f"{indent}🔲 Polygonal Half Space (Opening Definition)")
        boundary_analysis = analyze_boundary_polygon(entity, entity_lookup, depth + 1)
        result['boundary'] = boundary_analysis
    
    return result

def analyze_opening_geometry(entity: Dict[str, Any], entity_lookup: Dict[str, Dict], depth: int = 0) -> Dict[str, Any]:
    """Analyze the geometry used to create an opening"""
    
    indent = "  " * depth
    entity_type = entity.get('type')
    
    if entity_type == 'IfcPolygonalBoundedHalfSpace':
        return analyze_boundary_polygon(entity, entity_lookup, depth)
    elif entity_type == 'IfcExtrudedAreaSolid':
        return analyze_swept_area(entity, entity_lookup, depth)
    elif entity_type == 'IfcHalfSpaceSolid':
        print(f"{indent}➖ Half Space Solid (simple planar cut)")
        return {'type': 'planar_cut'}
    else:
        print(f"{indent}❓ Unknown opening type: {entity_type}")
        return {'type': entity_type}

def analyze_boundary_polygon(entity: Dict[str, Any], entity_lookup: Dict[str, Dict], depth: int = 0) -> Dict[str, Any]:
    """Analyze polygonal boundary (opening shape)"""
    
    indent = "  " * depth
    result = {'type': 'polygonal_boundary', 'points': 0, 'shape': 'unknown'}
    
    # Get the boundary polyline
    boundary = entity.get('polygonalBoundary', {})
    if 'ref' in boundary:
        polyline_entity = entity_lookup.get(boundary['ref'])
        if polyline_entity and polyline_entity.get('type') == 'IfcPolyline':
            points = analyze_polyline(polyline_entity, entity_lookup, depth)
            result['points'] = len(points)
            result['coordinates'] = points
            result['shape'] = classify_polyline_shape(points)
            
            print(f"{indent}🔷 Boundary Polygon: {result['points']} points - {result['shape']}")
            if result['shape'] == 'circular' or result['shape'] == 'curved':
                print(f"{indent}   ⭕ CIRCULAR/CURVED OPENING DETECTED!")
    
    return result

def analyze_swept_area(entity: Dict[str, Any], entity_lookup: Dict[str, Dict], depth: int = 0) -> Dict[str, Any]:
    """Analyze swept area profile (for extruded solids)"""
    
    indent = "  " * depth
    result = {'type': 'swept_area', 'profile': 'unknown', 'points': 0}
    
    swept_area = entity.get('sweptArea', {})
    if 'ref' in swept_area:
        profile_entity = entity_lookup.get(swept_area['ref'])
        if profile_entity:
            profile_type = profile_entity.get('type')
            print(f"{indent}📐 Profile: {profile_type}")
            
            if profile_type == 'IfcArbitraryClosedProfileDef':
                # Get the outer curve
                outer_curve = profile_entity.get('outerCurve', {})
                if 'ref' in outer_curve:
                    curve_entity = entity_lookup.get(outer_curve['ref'])
                    if curve_entity and curve_entity.get('type') == 'IfcPolyline':
                        points = analyze_polyline(curve_entity, entity_lookup, depth + 1)
                        result['points'] = len(points)
                        result['coordinates'] = points
                        result['shape'] = classify_polyline_shape(points)
                        
                        print(f"{indent}  🔸 Profile Points: {result['points']} - {result['shape']}")
                        if result['shape'] == 'circular' or result['shape'] == 'curved':
                            print(f"{indent}     ⭕ CIRCULAR PROFILE DETECTED!")
            
            elif profile_type == 'IfcRectangleProfileDef':
                x_dim = profile_entity.get('xDim', 0)
                y_dim = profile_entity.get('yDim', 0)
                result['profile'] = 'rectangle'
                result['dimensions'] = {'x': x_dim, 'y': y_dim}
                print(f"{indent}  📏 Rectangle: {x_dim} x {y_dim}")
            
            elif profile_type == 'IfcCircleProfileDef':
                radius = profile_entity.get('radius', 0)
                result['profile'] = 'circle'
                result['radius'] = radius
                print(f"{indent}  ⭕ Circle: radius {radius}")
    
    return result

def analyze_polyline(polyline_entity: Dict[str, Any], entity_lookup: Dict[str, Dict], depth: int = 0) -> List[Tuple[float, float]]:
    """Extract points from an IfcPolyline"""
    
    points = []
    polyline_points = polyline_entity.get('points', [])
    
    for point_ref in polyline_points:
        if isinstance(point_ref, dict) and 'ref' in point_ref:
            point_entity = entity_lookup.get(point_ref['ref'])
            if point_entity and point_entity.get('type') == 'IfcCartesianPoint':
                coordinates = point_entity.get('coordinates', [])
                if len(coordinates) >= 2:
                    points.append((coordinates[0], coordinates[1]))
    
    return points

def classify_polyline_shape(points: List[Tuple[float, float]]) -> str:
    """Classify the shape of a polyline based on its points"""
    
    if len(points) < 3:
        return 'line'
    elif len(points) == 4:
        # Check if it's a rectangle
        if is_rectangle(points):
            return 'rectangular'
        else:
            return 'quadrilateral'
    elif len(points) > 20:
        # High point count suggests circular or curved
        if is_circular(points):
            return 'circular'
        else:
            return 'curved'
    else:
        return f'polygon_{len(points)}'

def is_rectangle(points: List[Tuple[float, float]]) -> bool:
    """Check if 4 points form a rectangle"""
    if len(points) != 4:
        return False
    
    # Check if opposite sides are parallel and equal
    # Simplified check - could be enhanced
    return True

def is_circular(points: List[Tuple[float, float]]) -> bool:
    """Check if points form a circular shape"""
    if len(points) < 20:
        return False
    
    # Calculate center
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    
    # Calculate distances from center
    distances = [((p[0] - cx)**2 + (p[1] - cy)**2)**0.5 for p in points]
    
    # Check if all distances are similar (within 10% tolerance)
    avg_dist = sum(distances) / len(distances)
    max_deviation = max(abs(d - avg_dist) for d in distances)
    
    return max_deviation < (avg_dist * 0.1)

def analyze_wall_openings(file1_path: str, file2_path: str, wall_name: str) -> None:
    """Main analysis function to compare wall opening geometry between two files"""
    
    print(f"🔍 ANALYZING WALL OPENING GEOMETRY")
    print(f"Wall: {wall_name}")
    print(f"File 1: {file1_path}")
    print(f"File 2: {file2_path}")
    print("=" * 80)
    
    # Load data
    data1 = load_json_data(file1_path)
    data2 = load_json_data(file2_path)
    
    entities1 = data1.get('data', [])
    entities2 = data2.get('data', [])
    
    # Create entity lookups
    lookup1 = {entity.get('globalId'): entity for entity in entities1 if entity.get('globalId')}
    lookup2 = {entity.get('globalId'): entity for entity in entities2 if entity.get('globalId')}
    
    # Find the wall
    wall1 = find_element_by_name(entities1, wall_name)
    wall2 = find_element_by_name(entities2, wall_name)
    
    if not wall1:
        print(f"❌ Wall '{wall_name}' not found in File 1")
        return
    if not wall2:
        print(f"❌ Wall '{wall_name}' not found in File 2")
        return
    
    print(f"✅ Found wall in both files\n")
    
    # Analyze each file
    for file_num, (wall, entities, lookup) in enumerate([(wall1, entities1, lookup1), (wall2, entities2, lookup2)], 1):
        print(f"📁 FILE {file_num} ANALYSIS")
        print("-" * 40)
        
        # Get wall representation
        representation = wall.get('representation', {})
        if 'ref' in representation:
            prod_def = lookup.get(representation['ref'])
            if prod_def:
                shape_reps = prod_def.get('representations', [])
                
                # Find Body representation
                for shape_rep_ref in shape_reps:
                    if isinstance(shape_rep_ref, dict) and 'ref' in shape_rep_ref:
                        shape_rep = lookup.get(shape_rep_ref['ref'])
                        if shape_rep and shape_rep.get('representationIdentifier') == 'Body':
                            print(f"🎯 Body Representation: {shape_rep.get('representationType')}")
                            
                            # Analyze items
                            items = shape_rep.get('items', [])
                            for i, item_ref in enumerate(items):
                                if isinstance(item_ref, dict) and 'ref' in item_ref:
                                    item_entity = lookup.get(item_ref['ref'])
                                    if item_entity:
                                        print(f"\nItem {i+1}: {item_entity.get('type')}")
                                        
                                        # Trace boolean operations to find openings
                                        if item_entity.get('type') == 'IfcBooleanClippingResult':
                                            trace_boolean_operations(item_entity, lookup, 1)
        
        print(f"\n{'=' * 40}\n")
    
    # Summary comparison
    print("📊 COMPARISON SUMMARY")
    print("-" * 40)
    print("🔍 Check the analysis above for:")
    print("  • Number of boolean operations (openings)")
    print("  • Polyline point counts (high = circular, low = rectangular)")
    print("  • Profile types (circle, rectangle, arbitrary)")
    print("  • Opening geometry differences between files")

def main():
    """Main entry point"""
    
    if len(sys.argv) < 4:
        print("Usage: python analyze_wall_opening_geometry.py <file1.json> <file2.json> <wall_name>")
        print()
        print("Examples:")
        print("  python analyze_wall_opening_geometry.py official.json pipeline.json 'Wand-Ext-OG-1'")
        print()
        print("Description:")
        print("  Analyzes wall geometry differences in ifcJSON files, focusing on:")
        print("  - Boolean operations that create openings")
        print("  - Polyline definitions (circular vs rectangular)")
        print("  - Opening element geometry details")
        sys.exit(1)
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    wall_name = sys.argv[3]
    
    analyze_wall_openings(file1, file2, wall_name)

if __name__ == "__main__":
    main()