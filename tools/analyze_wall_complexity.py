#!/usr/bin/env python3
"""
Analyze Wall Geometry Complexity

Specifically analyzes the wall "Wand-Ext-OG-1" to understand the actual vertex count
and geometry complexity in Step 1 vs Step 3.
"""

import json
import sys
from typing import Dict, List, Any, Tuple

def load_json_data(file_path: str) -> List[Dict[str, Any]]:
    """Load entities from JSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data.get('data', [])

def analyze_wall_complexity(step1_file: str, step3_file: str, wall_name: str = "Wand-Ext-OG-1") -> None:
    """Analyze wall geometry complexity between steps"""
    
    print(f"🔍 ANALYZING WALL GEOMETRY COMPLEXITY: {wall_name}")
    print("="*70)
    
    # Load data
    step1_entities = load_json_data(step1_file)
    step3_entities = load_json_data(step3_file)
    
    # Create lookups
    step1_lookup = {entity.get('globalId'): entity for entity in step1_entities if entity.get('globalId')}
    step3_lookup = {entity.get('globalId'): entity for entity in step3_entities if entity.get('globalId')}
    
    # Find wall by name
    wall_element = None
    for entity in step1_entities:
        if entity.get('name') == wall_name:
            wall_element = entity
            break
    
    if not wall_element:
        print(f"❌ Wall '{wall_name}' not found")
        return
    
    wall_id = wall_element.get('globalId')
    print(f"Wall GlobalId: {wall_id}")
    
    # Analyze Step 1 geometry
    step1_faces, step1_vertices = analyze_element_geometry(step1_entities, step1_lookup, wall_element, "STEP 1")
    
    # Analyze Step 3 geometry
    step3_element = step3_lookup.get(wall_id)
    if step3_element:
        step3_faces, step3_vertices = analyze_element_geometry(step3_entities, step3_lookup, step3_element, "STEP 3")
    else:
        print("❌ Wall not found in Step 3")
        return
    
    # Compare results
    print(f"\n📊 GEOMETRY COMPLEXITY COMPARISON")
    print("="*70)
    print(f"                 │  Faces  │ Vertices │")
    print(f"─────────────────┼─────────┼──────────┤")
    print(f"Step 1 (Original)│ {step1_faces:7} │ {step1_vertices:8} │")
    print(f"Step 3 (Pipeline)│ {step3_faces:7} │ {step3_vertices:8} │")
    print(f"─────────────────┼─────────┼──────────┤")
    print(f"Change           │ {step3_faces-step1_faces:+7} │ {step3_vertices-step1_vertices:+8} │")
    
    if step1_vertices > 0:
        vertex_loss_pct = ((step1_vertices - step3_vertices) / step1_vertices) * 100
        print(f"Vertex loss: {vertex_loss_pct:.1f}%")
        
        if step1_vertices == 394:
            print("✅ CONFIRMED: Original wall has 394 vertices as reported")
        else:
            print(f"⚠️  Original wall has {step1_vertices} vertices (you reported 394)")

def analyze_element_geometry(entities: List[Dict[str, Any]], lookup: Dict[str, Any], 
                           element: Dict[str, Any], stage: str) -> Tuple[int, int]:
    """Analyze geometry complexity of an element"""
    
    print(f"\n🔍 {stage} GEOMETRY ANALYSIS")
    print("-" * 50)
    
    representation = element.get('representation', {})
    if representation.get('type') != 'IfcProductDefinitionShape':
        print("❌ No IfcProductDefinitionShape found")
        return 0, 0
    
    representations = representation.get('representations', [])
    print(f"Shape representations: {len(representations)}")
    
    total_faces = 0
    total_vertices = 0
    
    for i, rep_ref in enumerate(representations):
        ref_id = rep_ref.get('ref')
        shape_rep = lookup.get(ref_id)
        
        if shape_rep and shape_rep.get('type') == 'IfcShapeRepresentation':
            rep_id = shape_rep.get('representationIdentifier')
            rep_type = shape_rep.get('representationType')
            items = shape_rep.get('items', [])
            
            print(f"  Rep {i+1}: {rep_id}-{rep_type} ({len(items)} items)")
            
            if rep_id == 'Body':
                print(f"    🎯 Analyzing Body representation...")
                
                for j, item_ref in enumerate(items):
                    faces, vertices = analyze_geometry_item(entities, lookup, item_ref, f"    Item {j+1}")
                    total_faces += faces
                    total_vertices += vertices
    
    print(f"📦 Total complexity: {total_faces} faces, {total_vertices} vertices")
    return total_faces, total_vertices

def analyze_geometry_item(entities: List[Dict[str, Any]], lookup: Dict[str, Any], 
                         item_ref: Any, label: str) -> Tuple[int, int]:
    """Analyze a single geometry item"""
    
    if isinstance(item_ref, dict):
        if 'ref' in item_ref:
            # Referenced geometry
            ref_id = item_ref.get('ref')
            geom_entity = lookup.get(ref_id)
            if geom_entity:
                geom_type = geom_entity.get('type')
                faces, vertices = count_geometry_complexity(geom_entity, lookup)
                print(f"{label}: {geom_type} ({faces} faces, {vertices} vertices)")
                return faces, vertices
        else:
            # Inline geometry
            geom_type = item_ref.get('type', 'unknown')
            faces, vertices = count_geometry_complexity(item_ref, lookup)
            print(f"{label}: {geom_type} (inline) ({faces} faces, {vertices} vertices)")
            return faces, vertices
    
    print(f"{label}: Unknown geometry type")
    return 0, 0

def count_geometry_complexity(geom_entity: Dict[str, Any], lookup: Dict[str, Any]) -> Tuple[int, int]:
    """Count faces and vertices in a geometry entity"""
    
    entity_type = geom_entity.get('type')
    
    if entity_type == 'IfcFacetedBrep':
        return count_faceted_brep_complexity(geom_entity, lookup)
    elif entity_type == 'IfcBooleanClippingResult':
        return count_boolean_complexity(geom_entity, lookup)
    elif entity_type == 'IfcExtrudedAreaSolid':
        return count_extruded_solid_complexity(geom_entity, lookup)
    
    return 0, 0

def count_faceted_brep_complexity(brep_entity: Dict[str, Any], lookup: Dict[str, Any]) -> Tuple[int, int]:
    """Count complexity of IfcFacetedBrep"""
    
    outer = brep_entity.get('outer', {})
    if isinstance(outer, dict):
        if 'ref' in outer:
            # Referenced shell
            shell_entity = lookup.get(outer['ref'])
            if shell_entity and shell_entity.get('type') == 'IfcClosedShell':
                faces = shell_entity.get('cfsFaces', [])
                vertices = count_vertices_in_faces(faces, lookup)
                return len(faces), vertices
        else:
            # Inline shell
            if outer.get('type') == 'IfcClosedShell':
                faces = outer.get('cfsFaces', [])
                vertices = count_vertices_in_faces(faces, lookup)
                return len(faces), vertices
    
    return 0, 0

def count_boolean_complexity(bool_entity: Dict[str, Any], lookup: Dict[str, Any]) -> Tuple[int, int]:
    """Count complexity of IfcBooleanClippingResult"""
    
    first_operand = bool_entity.get('firstOperand', {})
    second_operand = bool_entity.get('secondOperand', {})
    
    first_faces, first_vertices = analyze_boolean_operand(first_operand, lookup)
    second_faces, second_vertices = analyze_boolean_operand(second_operand, lookup)
    
    # For boolean operations, we sum the complexity of operands
    # (in reality, the result might be different, but this gives us the input complexity)
    return first_faces + second_faces, first_vertices + second_vertices

def analyze_boolean_operand(operand: Dict[str, Any], lookup: Dict[str, Any]) -> Tuple[int, int]:
    """Analyze a boolean operand"""
    
    if isinstance(operand, dict):
        if 'ref' in operand:
            # Referenced operand
            ref_entity = lookup.get(operand['ref'])
            if ref_entity:
                return count_geometry_complexity(ref_entity, lookup)
        else:
            # Inline operand
            return count_geometry_complexity(operand, lookup)
    
    return 0, 0

def count_extruded_solid_complexity(extrude_entity: Dict[str, Any], lookup: Dict[str, Any]) -> Tuple[int, int]:
    """Estimate complexity of IfcExtrudedAreaSolid"""
    
    swept_area = extrude_entity.get('sweptArea', {})
    if isinstance(swept_area, dict):
        if 'ref' in swept_area:
            profile_entity = lookup.get(swept_area['ref'])
            if profile_entity:
                return estimate_profile_complexity(profile_entity, lookup)
        else:
            return estimate_profile_complexity(swept_area, lookup)
    
    return 6, 8  # Default rectangular extrusion

def estimate_profile_complexity(profile_entity: Dict[str, Any], lookup: Dict[str, Any]) -> Tuple[int, int]:
    """Estimate complexity based on profile"""
    
    if profile_entity.get('type') == 'IfcArbitraryClosedProfileDef':
        outer_curve = profile_entity.get('outerCurve', {})
        if isinstance(outer_curve, dict):
            if 'ref' in outer_curve:
                curve_entity = lookup.get(outer_curve['ref'])
                if curve_entity and curve_entity.get('type') == 'IfcPolyline':
                    points = curve_entity.get('points', [])
                    # Extruded solid: 2 faces for top/bottom + sides
                    estimated_faces = len(points) + 2 if points else 6
                    estimated_vertices = len(points) * 2 if points else 8
                    return estimated_faces, estimated_vertices
            else:
                if outer_curve.get('type') == 'IfcPolyline':
                    points = outer_curve.get('points', [])
                    estimated_faces = len(points) + 2 if points else 6
                    estimated_vertices = len(points) * 2 if points else 8
                    return estimated_faces, estimated_vertices
    
    return 6, 8  # Default

def count_vertices_in_faces(faces: List[Any], lookup: Dict[str, Any]) -> int:
    """Count unique vertices in face list"""
    
    vertex_refs = set()
    
    for face_ref in faces:
        if isinstance(face_ref, dict):
            if 'ref' in face_ref:
                # Referenced face
                face_entity = lookup.get(face_ref['ref'])
                if face_entity and face_entity.get('type') == 'IfcFace':
                    bounds = face_entity.get('bounds', [])
                    for bound_ref in bounds:
                        vertices = extract_vertices_from_bound(bound_ref, lookup)
                        vertex_refs.update(vertices)
            else:
                # Inline face
                if face_ref.get('type') == 'IfcFace':
                    bounds = face_ref.get('bounds', [])
                    for bound_ref in bounds:
                        vertices = extract_vertices_from_bound(bound_ref, lookup)
                        vertex_refs.update(vertices)
    
    return len(vertex_refs)

def extract_vertices_from_bound(bound_ref: Any, lookup: Dict[str, Any]) -> set:
    """Extract vertex references from a face bound"""
    
    vertex_refs = set()
    
    if isinstance(bound_ref, dict):
        if 'ref' in bound_ref:
            bound_entity = lookup.get(bound_ref['ref'])
            if bound_entity:
                loop_ref = bound_entity.get('bound', {})
                vertices = extract_vertices_from_loop(loop_ref, lookup)
                vertex_refs.update(vertices)
        else:
            if bound_ref.get('type') in ['IfcFaceOuterBound', 'IfcFaceBound']:
                loop_ref = bound_ref.get('bound', {})
                vertices = extract_vertices_from_loop(loop_ref, lookup)
                vertex_refs.update(vertices)
    
    return vertex_refs

def extract_vertices_from_loop(loop_ref: Any, lookup: Dict[str, Any]) -> set:
    """Extract vertex references from a loop"""
    
    vertex_refs = set()
    
    if isinstance(loop_ref, dict):
        if 'ref' in loop_ref:
            loop_entity = lookup.get(loop_ref['ref'])
            if loop_entity and loop_entity.get('type') == 'IfcPolyLoop':
                polygon = loop_entity.get('polygon', [])
                for point_ref in polygon:
                    if isinstance(point_ref, dict):
                        point_id = point_ref.get('ref') or str(point_ref.get('globalId', ''))
                        vertex_refs.add(point_id)
        else:
            if loop_ref.get('type') == 'IfcPolyLoop':
                polygon = loop_ref.get('polygon', [])
                for point_ref in polygon:
                    if isinstance(point_ref, dict):
                        point_id = point_ref.get('ref') or str(point_ref.get('globalId', ''))
                        vertex_refs.add(point_id)
    
    return vertex_refs

def main():
    if len(sys.argv) < 3:
        print("Usage: python analyze_wall_complexity.py <step1_json> <step3_json> [wall_name]")
        print("Example: python analyze_wall_complexity.py step1.json step3.json 'Wand-Ext-OG-1'")
        sys.exit(1)
    
    step1_file = sys.argv[1]
    step3_file = sys.argv[2]
    wall_name = sys.argv[3] if len(sys.argv) > 3 else "Wand-Ext-OG-1"
    
    analyze_wall_complexity(step1_file, step3_file, wall_name)

if __name__ == "__main__":
    main()