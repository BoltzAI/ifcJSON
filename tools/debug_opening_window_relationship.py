#!/usr/bin/env python3
"""
Debug Opening-Window Relationship Analysis

Specifically analyzes the window OG-Fenster-2 and its associated opening element
to understand why circular geometry may be lost. This focuses on the relationship
between IfcOpeningElement and IfcWindow that should have matching geometry.

Key focus: Why does the wall lose 135→37 faces and 394→100 vertices?
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

def load_json_data(file_path: str) -> List[Dict[str, Any]]:
    """Load entities from ifcJSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data.get('data', [])

def find_element_by_name(entities: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Find element by name"""
    for entity in entities:
        if entity.get('name') == name:
            return entity
    return None

def find_element_by_id(entities: List[Dict[str, Any]], global_id: str) -> Optional[Dict[str, Any]]:
    """Find element by GlobalId"""
    for entity in entities:
        if entity.get('globalId') == global_id:
            return entity
    return None

def analyze_void_fill_relationships(entities: List[Dict[str, Any]], window_element: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze void-fill relationships for a window"""
    
    window_id = window_element.get('globalId')
    window_name = window_element.get('name')
    
    print(f"\n🔗 VOID-FILL RELATIONSHIP ANALYSIS: {window_name}")
    print("="*60)
    
    relationships = {
        'fills_void': None,
        'opening_element': None,
        'voids_wall': None,
        'wall_element': None
    }
    
    # Find IfcRelFillsElement where this window fills a void
    for entity in entities:
        if (entity.get('type') == 'IfcRelFillsElement' and 
            entity.get('relatedBuildingElement', {}).get('ref') == window_id):
            relationships['fills_void'] = entity
            
            # Get the opening element
            opening_ref = entity.get('relatingOpeningElement', {}).get('ref')
            if opening_ref:
                opening_element = find_element_by_id(entities, opening_ref)
                relationships['opening_element'] = opening_element
                print(f"✅ Window fills opening: {opening_element.get('name')} ({opening_ref})")
                
                # Find what the opening voids (should be a wall)
                for void_rel in entities:
                    if (void_rel.get('type') == 'IfcRelVoidsElement' and 
                        void_rel.get('relatedOpeningElement', {}).get('ref') == opening_ref):
                        relationships['voids_wall'] = void_rel
                        
                        wall_ref = void_rel.get('relatingBuildingElement', {}).get('ref')
                        if wall_ref:
                            wall_element = find_element_by_id(entities, wall_ref)
                            relationships['wall_element'] = wall_element
                            print(f"✅ Opening voids wall: {wall_element.get('name')} ({wall_ref})")
                            break
                break
    
    return relationships

def analyze_geometry_representations(entities: List[Dict[str, Any]], element: Dict[str, Any], label: str) -> Dict[str, Any]:
    """Analyze geometry representations for an element"""
    
    element_name = element.get('name', 'unnamed')
    element_type = element.get('type')
    
    print(f"\n📐 GEOMETRY ANALYSIS: {label} - {element_name} ({element_type})")
    print("-" * 50)
    
    representation = element.get('representation', {})
    if representation.get('type') != 'IfcProductDefinitionShape':
        print("❌ No IfcProductDefinitionShape found")
        return {}
    
    representations = representation.get('representations', [])
    print(f"📊 Shape representations: {len(representations)}")
    
    analysis = {
        'total_representations': len(representations),
        'representations': [],
        'total_faces': 0,
        'total_vertices': 0,
        'geometry_types': set()
    }
    
    for i, rep_ref in enumerate(representations):
        ref_id = rep_ref.get('ref')
        
        # Find the shape representation
        shape_rep = find_element_by_id(entities, ref_id)
        if shape_rep and shape_rep.get('type') == 'IfcShapeRepresentation':
            rep_id = shape_rep.get('representationIdentifier')
            rep_type = shape_rep.get('representationType')
            items = shape_rep.get('items', [])
            
            print(f"  🔸 Rep {i+1}: {rep_id}-{rep_type} ({len(items)} items)")
            
            rep_analysis = {
                'identifier': rep_id,
                'type': rep_type,
                'items_count': len(items),
                'geometry_types': [],
                'faces': 0,
                'vertices': 0
            }
            
            # Analyze each geometry item
            for j, item_ref in enumerate(items):
                geom_type, faces, vertices = analyze_geometry_item(entities, item_ref, f"    Item {j+1}")
                rep_analysis['geometry_types'].append(geom_type)
                rep_analysis['faces'] += faces
                rep_analysis['vertices'] += vertices
                analysis['geometry_types'].add(geom_type)
            
            analysis['representations'].append(rep_analysis)
            analysis['total_faces'] += rep_analysis['faces']
            analysis['total_vertices'] += rep_analysis['vertices']
    
    print(f"📊 TOTAL GEOMETRY: {analysis['total_faces']} faces, {analysis['total_vertices']} vertices")
    print(f"📦 Geometry types used: {', '.join(analysis['geometry_types'])}")
    
    return analysis

def analyze_geometry_item(entities: List[Dict[str, Any]], item_ref: Any, label: str) -> tuple:
    """Analyze a single geometry item"""
    
    if isinstance(item_ref, dict):
        if 'ref' in item_ref:
            # Referenced geometry
            ref_id = item_ref.get('ref')
            geom_entity = find_element_by_id(entities, ref_id)
            if geom_entity:
                geom_type = geom_entity.get('type')
                faces, vertices = count_geometry_complexity(geom_entity)
                print(f"{label}: {geom_type} ({faces} faces, {vertices} vertices)")
                return geom_type, faces, vertices
        else:
            # Inline geometry
            geom_type = item_ref.get('type', 'unknown')
            faces, vertices = count_geometry_complexity(item_ref)
            print(f"{label}: {geom_type} (inline) ({faces} faces, {vertices} vertices)")
            return geom_type, faces, vertices
    
    print(f"{label}: Unknown geometry type")
    return 'unknown', 0, 0

def count_geometry_complexity(geom_entity: Dict[str, Any]) -> tuple:
    """Count faces and vertices in a geometry entity"""
    
    entity_type = geom_entity.get('type')
    
    if entity_type == 'IfcFacetedBrep':
        return count_faceted_brep_complexity(geom_entity)
    elif entity_type == 'IfcExtrudedAreaSolid':
        return count_extruded_solid_complexity(geom_entity)
    elif entity_type == 'IfcBooleanClippingResult':
        return count_boolean_complexity(geom_entity)
    
    return 0, 0

def count_faceted_brep_complexity(brep_entity: Dict[str, Any]) -> tuple:
    """Count complexity of IfcFacetedBrep"""
    
    outer = brep_entity.get('outer', {})
    if outer.get('type') != 'IfcClosedShell':
        return 0, 0
    
    faces = outer.get('cfsFaces', [])
    vertices = set()
    
    # Count faces directly
    face_count = len(faces)
    
    # Count unique vertices by collecting all point references
    for face in faces:
        if isinstance(face, dict):
            bounds = face.get('bounds', [])
            for bound in bounds:
                if isinstance(bound, dict):
                    bound_entity = bound.get('bound', {})
                    if bound_entity.get('type') == 'IfcPolyLoop':
                        polygon = bound_entity.get('polygon', [])
                        for point_ref in polygon:
                            if isinstance(point_ref, dict):
                                point_id = point_ref.get('ref') or str(point_ref.get('globalId', ''))
                                vertices.add(point_id)
    
    return face_count, len(vertices)

def count_extruded_solid_complexity(extrude_entity: Dict[str, Any]) -> tuple:
    """Estimate complexity of IfcExtrudedAreaSolid (simpler geometry)"""
    # ExtrudedAreaSolid is much simpler - estimate based on profile
    swept_area = extrude_entity.get('sweptArea', {})
    
    if swept_area.get('type') == 'IfcArbitraryClosedProfileDef':
        outer_curve = swept_area.get('outerCurve', {})
        if outer_curve.get('type') == 'IfcPolyline':
            points = outer_curve.get('points', [])
            # Extruded solid: 2 faces for top/bottom + sides
            # Simple estimate: (points-1) side faces + 2 end faces  
            estimated_faces = len(points) + 2 if points else 6
            estimated_vertices = len(points) * 2 if points else 8
            return estimated_faces, estimated_vertices
    
    # Default rectangular extrusion
    return 6, 8

def count_boolean_complexity(bool_entity: Dict[str, Any]) -> tuple:
    """Estimate complexity of IfcBooleanClippingResult"""
    # Boolean operations can be complex - this is an approximation
    # In practice, would need to analyze the operands
    return 10, 20  # Rough estimate

def compare_window_opening_geometry(step1_entities: List[Dict[str, Any]], 
                                  step3_entities: List[Dict[str, Any]],
                                  window_name: str = "OG-Fenster-2") -> None:
    """Compare window and opening geometry between steps"""
    
    print(f"🔍 WINDOW-OPENING COMPARISON: {window_name}")
    print("="*70)
    
    # Find window in both steps
    step1_window = find_element_by_name(step1_entities, window_name)
    step3_window = find_element_by_name(step3_entities, window_name)
    
    if not step1_window or not step3_window:
        print("❌ Window not found in both steps")
        return
    
    # Analyze relationships in Step 1
    step1_relationships = analyze_void_fill_relationships(step1_entities, step1_window)
    
    # Analyze relationships in Step 3  
    step3_relationships = analyze_void_fill_relationships(step3_entities, step3_window)
    
    # Compare geometries
    elements_to_compare = [
        (step1_window, step3_window, "WINDOW"),
        (step1_relationships.get('opening_element'), step3_relationships.get('opening_element'), "OPENING"),
        (step1_relationships.get('wall_element'), step3_relationships.get('wall_element'), "WALL")
    ]
    
    print(f"\n📊 GEOMETRY COMPARISON")
    print("="*70)
    
    for step1_elem, step3_elem, label in elements_to_compare:
        if step1_elem and step3_elem:
            print(f"\n{label}: {step1_elem.get('name', 'unnamed')}")
            
            step1_analysis = analyze_geometry_representations(step1_entities, step1_elem, f"Step 1 {label}")
            step3_analysis = analyze_geometry_representations(step3_entities, step3_elem, f"Step 3 {label}")
            
            # Compare
            faces_change = step3_analysis['total_faces'] - step1_analysis['total_faces']
            vertices_change = step3_analysis['total_vertices'] - step1_analysis['total_vertices']
            
            print(f"\n📈 CHANGES:")
            print(f"   Faces: {step1_analysis['total_faces']} → {step3_analysis['total_faces']} ({faces_change:+d})")
            print(f"   Vertices: {step1_analysis['total_vertices']} → {step3_analysis['total_vertices']} ({vertices_change:+d})")
            
            if step1_analysis['total_faces'] > 0:
                face_loss_pct = (faces_change / step1_analysis['total_faces']) * 100
                if face_loss_pct < -30:
                    print(f"   🚨 CRITICAL GEOMETRY LOSS: {face_loss_pct:.1f}%")
                elif face_loss_pct < -10:
                    print(f"   ⚠️  Significant geometry reduction: {face_loss_pct:.1f}%")
            
            # Compare geometry types
            step1_types = set(step1_analysis['geometry_types'])
            step3_types = set(step3_analysis['geometry_types'])
            
            if step1_types != step3_types:
                lost_types = step1_types - step3_types
                gained_types = step3_types - step1_types
                if lost_types:
                    print(f"   📉 Lost geometry types: {', '.join(lost_types)}")
                if gained_types:
                    print(f"   📈 Gained geometry types: {', '.join(gained_types)}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python debug_opening_window_relationship.py <step1_json> <step3_json> [window_name]")
        print("Example: python debug_opening_window_relationship.py step1.json step3.json 'OG-Fenster-2'")
        sys.exit(1)
    
    step1_file = sys.argv[1]
    step3_file = sys.argv[2]
    window_name = sys.argv[3] if len(sys.argv) > 3 else "OG-Fenster-2"
    
    print("🔍 DEBUG OPENING-WINDOW RELATIONSHIP")
    print("="*70)
    print(f"Analyzing window: {window_name}")
    print(f"Comparing: {step1_file} vs {step3_file}")
    
    # Load data
    step1_entities = load_json_data(step1_file)
    step3_entities = load_json_data(step3_file)
    
    # Main analysis
    compare_window_opening_geometry(step1_entities, step3_entities, window_name)

if __name__ == "__main__":
    main()