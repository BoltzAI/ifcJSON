#!/usr/bin/env python3
"""
Wall Geometry Detail Comparison Tool

Performs deep comparison of wall geometry between ifcJSON files, including:
- All geometric entities referenced by the wall
- Polyline point counts and coordinates
- Boolean operation structures
- Geometric parameter differences
"""

import json
import sys
from typing import Dict, List, Any, Optional, Set, Tuple

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

def collect_all_geometry_references(element: Dict[str, Any], entity_lookup: Dict[str, Dict], 
                                  collected: Set[str] = None, depth: int = 0) -> Set[str]:
    """Recursively collect all geometry entity references"""
    
    if collected is None:
        collected = set()
    
    if depth > 50:  # Prevent infinite recursion
        return collected
    
    # Check for direct references
    for key, value in element.items():
        if isinstance(value, dict):
            if 'ref' in value and value['ref'] not in collected:
                ref_id = value['ref']
                collected.add(ref_id)
                
                # Recursively collect from referenced entity
                ref_entity = entity_lookup.get(ref_id)
                if ref_entity:
                    collect_all_geometry_references(ref_entity, entity_lookup, collected, depth + 1)
            else:
                # Check nested dictionaries
                collect_all_geometry_references(value, entity_lookup, collected, depth + 1)
        elif isinstance(value, list):
            # Check lists for references
            for item in value:
                if isinstance(item, dict):
                    collect_all_geometry_references(item, entity_lookup, collected, depth + 1)
    
    return collected

def analyze_geometry_entity(entity: Dict[str, Any], entity_lookup: Dict[str, Dict]) -> Dict[str, Any]:
    """Analyze a single geometry entity"""
    
    entity_type = entity.get('type', 'unknown')
    entity_id = entity.get('globalId', 'inline')
    
    analysis = {
        'type': entity_type,
        'id': entity_id,
        'details': {}
    }
    
    # Analyze based on type
    if entity_type == 'IfcPolyline':
        points = entity.get('points', [])
        point_count = len(points)
        analysis['details']['point_count'] = point_count
        
        # Extract actual coordinates
        coordinates = []
        for point_ref in points:
            if isinstance(point_ref, dict) and 'ref' in point_ref:
                point_entity = entity_lookup.get(point_ref['ref'])
                if point_entity and point_entity.get('type') == 'IfcCartesianPoint':
                    coords = point_entity.get('coordinates', [])
                    coordinates.append(coords)
        
        analysis['details']['coordinates'] = coordinates
        analysis['details']['shape_hint'] = classify_point_count(point_count)
        
    elif entity_type == 'IfcBooleanClippingResult':
        analysis['details']['operator'] = entity.get('operator', 'DIFFERENCE')
        
        # Analyze operands
        first = entity.get('firstOperand', {})
        second = entity.get('secondOperand', {})
        
        if 'ref' in first:
            first_entity = entity_lookup.get(first['ref'])
            if first_entity:
                analysis['details']['first_operand'] = first_entity.get('type', 'unknown')
        
        if 'ref' in second:
            second_entity = entity_lookup.get(second['ref'])
            if second_entity:
                analysis['details']['second_operand'] = second_entity.get('type', 'unknown')
                
    elif entity_type == 'IfcExtrudedAreaSolid':
        depth = entity.get('depth', 0)
        analysis['details']['extrusion_depth'] = depth
        
        # Check swept area
        swept_area = entity.get('sweptArea', {})
        if 'ref' in swept_area:
            area_entity = entity_lookup.get(swept_area['ref'])
            if area_entity:
                analysis['details']['profile_type'] = area_entity.get('type', 'unknown')
                
    elif entity_type == 'IfcArbitraryClosedProfileDef':
        profile_type = entity.get('profileType', 'unknown')
        analysis['details']['profile_type'] = profile_type
        
        # Check outer curve
        outer_curve = entity.get('outerCurve', {})
        if 'ref' in outer_curve:
            curve_entity = entity_lookup.get(outer_curve['ref'])
            if curve_entity:
                analysis['details']['curve_type'] = curve_entity.get('type', 'unknown')
                
    elif entity_type == 'IfcPolygonalBoundedHalfSpace':
        # Check boundary
        boundary = entity.get('polygonalBoundary', {})
        if 'ref' in boundary:
            boundary_entity = entity_lookup.get(boundary['ref'])
            if boundary_entity and boundary_entity.get('type') == 'IfcPolyline':
                analysis['details']['boundary_points'] = len(boundary_entity.get('points', []))
    
    return analysis

def classify_point_count(count: int) -> str:
    """Classify shape based on point count"""
    if count < 3:
        return 'line'
    elif count == 4:
        return 'rectangular_likely'
    elif count >= 20:
        return 'circular_likely'
    elif count >= 8:
        return 'octagonal_or_curved'
    else:
        return f'polygon_{count}'

def compare_geometry_entities(entities1: Dict[str, Any], entities2: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two sets of geometry entities"""
    
    comparison = {
        'total_entities': {'file1': len(entities1), 'file2': len(entities2)},
        'entity_types': {'file1': {}, 'file2': {}},
        'polyline_analysis': {'file1': [], 'file2': []},
        'boolean_operations': {'file1': 0, 'file2': 0},
        'differences': []
    }
    
    # Analyze file 1 entities
    for entity_id, analysis in entities1.items():
        entity_type = analysis['type']
        comparison['entity_types']['file1'][entity_type] = comparison['entity_types']['file1'].get(entity_type, 0) + 1
        
        if entity_type == 'IfcPolyline':
            point_count = analysis['details'].get('point_count', 0)
            shape = analysis['details'].get('shape_hint', 'unknown')
            comparison['polyline_analysis']['file1'].append({
                'points': point_count,
                'shape': shape
            })
        elif entity_type == 'IfcBooleanClippingResult':
            comparison['boolean_operations']['file1'] += 1
    
    # Analyze file 2 entities
    for entity_id, analysis in entities2.items():
        entity_type = analysis['type']
        comparison['entity_types']['file2'][entity_type] = comparison['entity_types']['file2'].get(entity_type, 0) + 1
        
        if entity_type == 'IfcPolyline':
            point_count = analysis['details'].get('point_count', 0)
            shape = analysis['details'].get('shape_hint', 'unknown')
            comparison['polyline_analysis']['file2'].append({
                'points': point_count,
                'shape': shape
            })
        elif entity_type == 'IfcBooleanClippingResult':
            comparison['boolean_operations']['file2'] += 1
    
    # Find significant differences
    # Check for circular polylines in file1 that become rectangular in file2
    file1_circular = [p for p in comparison['polyline_analysis']['file1'] if 'circular' in p['shape']]
    file2_circular = [p for p in comparison['polyline_analysis']['file2'] if 'circular' in p['shape']]
    
    if len(file1_circular) > len(file2_circular):
        comparison['differences'].append(f"Loss of circular geometry: {len(file1_circular)} → {len(file2_circular)}")
    
    return comparison

def compare_wall_geometry(file1_path: str, file2_path: str, wall_name: str) -> None:
    """Main comparison function"""
    
    print(f"🔍 WALL GEOMETRY DETAIL COMPARISON")
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
    
    # Find walls
    wall1 = find_element_by_name(entities1, wall_name)
    wall2 = find_element_by_name(entities2, wall_name)
    
    if not wall1 or not wall2:
        print(f"❌ Wall not found in one or both files")
        return
    
    # Collect all geometry references
    print("📊 Collecting geometry references...")
    refs1 = collect_all_geometry_references(wall1, lookup1)
    refs2 = collect_all_geometry_references(wall2, lookup2)
    
    print(f"  File 1: {len(refs1)} geometry entities")
    print(f"  File 2: {len(refs2)} geometry entities")
    print()
    
    # Analyze geometry entities
    print("🔬 Analyzing geometry entities...")
    analyzed1 = {}
    analyzed2 = {}
    
    for ref_id in refs1:
        entity = lookup1.get(ref_id)
        if entity:
            analyzed1[ref_id] = analyze_geometry_entity(entity, lookup1)
    
    for ref_id in refs2:
        entity = lookup2.get(ref_id)
        if entity:
            analyzed2[ref_id] = analyze_geometry_entity(entity, lookup2)
    
    # Compare results
    comparison = compare_geometry_entities(analyzed1, analyzed2)
    
    # Print detailed results
    print("\n📊 ENTITY TYPE DISTRIBUTION")
    print("-" * 40)
    print(f"{'Entity Type':<30} {'File 1':>10} {'File 2':>10}")
    print("-" * 40)
    
    all_types = set(comparison['entity_types']['file1'].keys()) | set(comparison['entity_types']['file2'].keys())
    for entity_type in sorted(all_types):
        count1 = comparison['entity_types']['file1'].get(entity_type, 0)
        count2 = comparison['entity_types']['file2'].get(entity_type, 0)
        diff = count2 - count1
        diff_str = f"({diff:+d})" if diff != 0 else ""
        print(f"{entity_type:<30} {count1:>10} {count2:>10} {diff_str}")
    
    print(f"\n🔷 POLYLINE ANALYSIS")
    print("-" * 40)
    print("File 1 Polylines:")
    for poly in comparison['polyline_analysis']['file1']:
        print(f"  • {poly['points']} points - {poly['shape']}")
        if poly['points'] > 20:
            print(f"    ⭕ HIGH RESOLUTION - Likely circular/curved")
    
    print("\nFile 2 Polylines:")
    for poly in comparison['polyline_analysis']['file2']:
        print(f"  • {poly['points']} points - {poly['shape']}")
        if poly['points'] > 20:
            print(f"    ⭕ HIGH RESOLUTION - Likely circular/curved")
    
    print(f"\n🔧 BOOLEAN OPERATIONS")
    print("-" * 40)
    print(f"File 1: {comparison['boolean_operations']['file1']} boolean operations")
    print(f"File 2: {comparison['boolean_operations']['file2']} boolean operations")
    
    if comparison['differences']:
        print(f"\n⚠️  SIGNIFICANT DIFFERENCES")
        print("-" * 40)
        for diff in comparison['differences']:
            print(f"  • {diff}")
    
    # Detailed polyline comparison
    print(f"\n📐 DETAILED POLYLINE COMPARISON")
    print("-" * 40)
    
    # Find high-resolution polylines in file 1
    for ref_id, analysis in analyzed1.items():
        if analysis['type'] == 'IfcPolyline' and analysis['details'].get('point_count', 0) > 20:
            print(f"\nFile 1 - High-res polyline: {analysis['details']['point_count']} points")
            
            # Try to find corresponding polyline in file 2
            found_match = False
            for ref_id2, analysis2 in analyzed2.items():
                if analysis2['type'] == 'IfcPolyline':
                    if analysis2['details'].get('point_count', 0) == analysis['details']['point_count']:
                        print(f"  ✅ Matching polyline found in File 2")
                        found_match = True
                        break
            
            if not found_match:
                print(f"  ❌ No matching high-res polyline in File 2")
                print(f"  ⚠️  POTENTIAL CIRCULAR GEOMETRY LOSS")

def main():
    """Main entry point"""
    
    if len(sys.argv) < 4:
        print("Usage: python compare_wall_geometry_details.py <file1.json> <file2.json> <wall_name>")
        print()
        print("Examples:")
        print("  python compare_wall_geometry_details.py official.json pipeline.json 'Wand-Ext-OG-1'")
        print()
        print("Description:")
        print("  Performs deep comparison of wall geometry between ifcJSON files")
        print("  Identifies polyline simplification and geometry differences")
        sys.exit(1)
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    wall_name = sys.argv[3]
    
    compare_wall_geometry(file1, file2, wall_name)

if __name__ == "__main__":
    main()