#!/usr/bin/env python3
"""
Wall Geometry Chain Tracer

Traces the complete geometry chain from wall element through all referenced entities,
specifically looking for boolean operations, polylines, and circular geometry.
"""

import json
import sys
from typing import Dict, List, Any, Optional, Set

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

def trace_geometry_chain(wall_name: str, file_path: str) -> Dict[str, Any]:
    """Trace complete geometry chain for a wall"""
    
    print(f"🔍 TRACING GEOMETRY CHAIN: {wall_name}")
    print(f"File: {file_path}")
    print("=" * 60)
    
    data = load_json_data(file_path)
    entities = data.get('data', [])
    entity_lookup = {entity.get('globalId'): entity for entity in entities if entity.get('globalId')}
    
    # Find wall
    wall = find_element_by_name(entities, wall_name)
    if not wall:
        print(f"❌ Wall '{wall_name}' not found")
        return {}
    
    print(f"✅ Found wall: {wall.get('globalId')}")
    
    # Trace geometry chain
    geometry_entities = {}
    visited = set()
    
    def collect_entity(entity_id: str, depth: int = 0):
        if entity_id in visited or depth > 20:
            return
        
        visited.add(entity_id)
        entity = entity_lookup.get(entity_id)
        
        if not entity:
            return
        
        entity_type = entity.get('type')
        indent = "  " * depth
        print(f"{indent}{entity_type} ({entity_id[:8]}...)")
        
        # Store relevant geometry entities
        if entity_type in ['IfcBooleanClippingResult', 'IfcPolyline', 'IfcCartesianPoint', 
                          'IfcExtrudedAreaSolid', 'IfcArbitraryClosedProfileDef',
                          'IfcPolygonalBoundedHalfSpace', 'IfcShapeRepresentation']:
            geometry_entities[entity_id] = {
                'type': entity_type,
                'entity': entity,
                'depth': depth
            }
            
            # Analyze specific types
            if entity_type == 'IfcPolyline':
                points = entity.get('points', [])
                print(f"{indent}  📐 {len(points)} points")
                if len(points) > 20:
                    print(f"{indent}  ⭕ HIGH RESOLUTION - Likely circular!")
                    
            elif entity_type == 'IfcBooleanClippingResult':
                print(f"{indent}  🔧 Boolean operation detected!")
                
            elif entity_type == 'IfcExtrudedAreaSolid':
                depth_val = entity.get('depth', 0)
                print(f"{indent}  📦 Extrusion depth: {depth_val}")
        
        # Recursively collect references
        for key, value in entity.items():
            if isinstance(value, dict) and 'ref' in value:
                collect_entity(value['ref'], depth + 1)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'ref' in item:
                        collect_entity(item['ref'], depth + 1)
    
    # Start from wall representation
    representation = wall.get('representation', {})
    if 'ref' in representation:
        collect_entity(representation['ref'], 0)
    elif representation.get('type') == 'IfcProductDefinitionShape':
        # Handle embedded ProductDefinitionShape
        print(f"📐 Embedded ProductDefinitionShape found")
        reps = representation.get('representations', [])
        for rep_ref in reps:
            if isinstance(rep_ref, dict) and 'ref' in rep_ref:
                collect_entity(rep_ref['ref'], 0)
    
    print(f"\n📊 GEOMETRY SUMMARY")
    print("-" * 30)
    
    # Count by type
    type_counts = {}
    circular_polylines = []
    boolean_ops = []
    
    for entity_id, info in geometry_entities.items():
        entity_type = info['type']
        entity = info['entity']
        
        type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        if entity_type == 'IfcPolyline':
            points = entity.get('points', [])
            point_count = len(points)
            if point_count > 20:
                circular_polylines.append({
                    'id': entity_id,
                    'points': point_count,
                    'entity': entity
                })
        
        elif entity_type == 'IfcBooleanClippingResult':
            boolean_ops.append({
                'id': entity_id,
                'entity': entity
            })
    
    # Print summary
    for entity_type, count in sorted(type_counts.items()):
        print(f"{entity_type}: {count}")
    
    # Analyze circular geometry
    if circular_polylines:
        print(f"\n⭕ CIRCULAR POLYLINES DETECTED: {len(circular_polylines)}")
        for poly in circular_polylines:
            print(f"  • {poly['points']} points ({poly['id'][:8]}...)")
            
            # Extract actual coordinates for the first few points
            points_list = poly['entity'].get('points', [])
            if len(points_list) > 0:
                print(f"    First 3 points reference IDs:")
                for i, point_ref in enumerate(points_list[:3]):
                    if isinstance(point_ref, dict) and 'ref' in point_ref:
                        point_entity = entity_lookup.get(point_ref['ref'])
                        if point_entity:
                            coords = point_entity.get('coordinates', [])
                            print(f"      {i+1}: {coords}")
    else:
        print(f"\n❌ NO CIRCULAR POLYLINES FOUND")
    
    # Analyze boolean operations
    if boolean_ops:
        print(f"\n🔧 BOOLEAN OPERATIONS: {len(boolean_ops)}")
        for op in boolean_ops:
            entity = op['entity']
            first_op = entity.get('firstOperand', {})
            second_op = entity.get('secondOperand', {})
            
            first_type = "unknown"
            second_type = "unknown"
            
            if 'ref' in first_op:
                first_entity = entity_lookup.get(first_op['ref'])
                if first_entity:
                    first_type = first_entity.get('type', 'unknown')
            
            if 'ref' in second_op:
                second_entity = entity_lookup.get(second_op['ref'])
                if second_entity:
                    second_type = second_entity.get('type', 'unknown')
            
            print(f"  • {first_type} - {second_type} ({op['id'][:8]}...)")
    
    return {
        'total_geometry_entities': len(geometry_entities),
        'type_counts': type_counts,
        'circular_polylines': len(circular_polylines),
        'boolean_operations': len(boolean_ops),
        'circular_details': circular_polylines,
        'boolean_details': boolean_ops
    }

def compare_geometry_chains(wall_name: str, file1_path: str, file2_path: str):
    """Compare geometry chains between two files"""
    
    print(f"🔍 COMPARING GEOMETRY CHAINS FOR: {wall_name}")
    print("=" * 80)
    
    print(f"\n📁 FILE 1: {file1_path}")
    result1 = trace_geometry_chain(wall_name, file1_path)
    
    print(f"\n📁 FILE 2: {file2_path}")
    result2 = trace_geometry_chain(wall_name, file2_path)
    
    print(f"\n📊 COMPARISON RESULTS")
    print("=" * 50)
    
    print(f"Total geometry entities:")
    print(f"  File 1: {result1.get('total_geometry_entities', 0)}")
    print(f"  File 2: {result2.get('total_geometry_entities', 0)}")
    
    print(f"\nCircular polylines:")
    print(f"  File 1: {result1.get('circular_polylines', 0)}")
    print(f"  File 2: {result2.get('circular_polylines', 0)}")
    
    print(f"\nBoolean operations:")
    print(f"  File 1: {result1.get('boolean_operations', 0)}")
    print(f"  File 2: {result2.get('boolean_operations', 0)}")
    
    # Check for geometry loss
    if result1.get('circular_polylines', 0) > result2.get('circular_polylines', 0):
        print(f"\n⚠️  CIRCULAR GEOMETRY LOSS DETECTED!")
        print(f"   {result1['circular_polylines']} → {result2['circular_polylines']} circular polylines")
        
        # Show details of lost circular geometry
        if result1.get('circular_details'):
            print(f"\n🔍 LOST CIRCULAR GEOMETRY DETAILS:")
            for poly in result1['circular_details']:
                print(f"   • {poly['points']} points (high resolution)")
    
    if result1.get('total_geometry_entities', 0) > result2.get('total_geometry_entities', 0):
        entities_lost = result1['total_geometry_entities'] - result2['total_geometry_entities']
        print(f"\n⚠️  GEOMETRY ENTITY LOSS: {entities_lost} entities lost")

def main():
    """Main entry point"""
    
    if len(sys.argv) < 4:
        print("Usage: python trace_wall_geometry_chain.py <file1.json> <file2.json> <wall_name>")
        print()
        print("Examples:")
        print("  python trace_wall_geometry_chain.py official.json pipeline.json 'Wand-Ext-OG-1'")
        sys.exit(1)
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    wall_name = sys.argv[3]
    
    compare_geometry_chains(wall_name, file1, file2)

if __name__ == "__main__":
    main()