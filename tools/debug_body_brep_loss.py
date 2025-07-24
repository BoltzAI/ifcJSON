#!/usr/bin/env python3
"""
Debug Body-Brep Representation Loss

Systematically identifies which elements lose Body-Brep representations
between Step 1 (original ifcJSON) and Step 3 (recreated ifcJSON).

This tool helps diagnose TODO #70: why only 10/21 Body-Brep representations
are preserved through the 4-step pipeline.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

def load_json_data(file_path: str) -> List[Dict[str, Any]]:
    """Load entities from ifcJSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data.get('data', [])

def find_body_brep_representations(entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Find all Body-Brep representations and their associated elements"""
    body_brep_reps = {}
    
    # First, find all IfcShapeRepresentation with Body-Brep
    shape_reps = {}
    for entity in entities:
        if (entity.get('type') == 'IfcShapeRepresentation' and 
            entity.get('representationIdentifier') == 'Body' and 
            entity.get('representationType') == 'Brep'):
            rep_id = entity.get('globalId')
            if rep_id:
                shape_reps[rep_id] = entity
    
    # Then, find elements that reference these representations
    for entity in entities:
        if entity.get('type') in ['IfcWall', 'IfcWallStandardCase', 'IfcWindow', 'IfcDoor', 'IfcOpeningElement', 'IfcSlab', 'IfcBeam', 'IfcColumn']:
            representation = entity.get('representation', {})
            if representation.get('type') == 'IfcProductDefinitionShape':
                representations = representation.get('representations', [])
                for rep_ref in representations:
                    ref_id = rep_ref.get('ref')
                    if ref_id in shape_reps:
                        element_id = entity.get('globalId')
                        element_name = entity.get('name', 'unnamed')
                        element_type = entity.get('type')
                        
                        body_brep_reps[element_id] = {
                            'element_name': element_name,
                            'element_type': element_type,
                            'shape_rep_id': ref_id,
                            'shape_rep': shape_reps[ref_id],
                            'element': entity
                        }
    
    return body_brep_reps

def analyze_representation_changes(step1_file: str, step3_file: str) -> Dict[str, Any]:
    """Analyze what happens to Body-Brep representations between Step 1 and Step 3"""
    
    print(f"🔍 Loading Step 1: {step1_file}")
    step1_entities = load_json_data(step1_file)
    print(f"✅ Loaded {len(step1_entities)} entities from Step 1")
    
    print(f"🔍 Loading Step 3: {step3_file}")
    step3_entities = load_json_data(step3_file)
    print(f"✅ Loaded {len(step3_entities)} entities from Step 3")
    
    # Find Body-Brep representations in both steps
    step1_breps = find_body_brep_representations(step1_entities)
    step3_breps = find_body_brep_representations(step3_entities)
    
    print(f"\n📊 BODY-BREP ANALYSIS")
    print("="*60)
    print(f"Step 1 Body-Brep representations: {len(step1_breps)}")
    print(f"Step 3 Body-Brep representations: {len(step3_breps)}")
    print(f"Lost representations: {len(step1_breps) - len(step3_breps)}")
    
    # Identify preserved, lost, and converted elements
    preserved = set(step1_breps.keys()) & set(step3_breps.keys())
    lost = set(step1_breps.keys()) - set(step3_breps.keys())
    
    results = {
        'step1_count': len(step1_breps),
        'step3_count': len(step3_breps),
        'preserved': preserved,
        'lost': lost,
        'step1_breps': step1_breps,
        'step3_breps': step3_breps,
        'step1_entities': step1_entities,
        'step3_entities': step3_entities
    }
    
    return results

def analyze_lost_elements(results: Dict[str, Any]) -> None:
    """Analyze what happened to lost Body-Brep elements"""
    
    lost_ids = results['lost']
    step1_breps = results['step1_breps']
    step3_entities = results['step3_entities']
    
    if not lost_ids:
        print("✅ No Body-Brep representations were lost!")
        return
        
    print(f"\n🔍 ANALYZING {len(lost_ids)} LOST BODY-BREP REPRESENTATIONS")
    print("="*60)
    
    # Create lookup for Step 3 entities
    step3_lookup = {entity.get('globalId'): entity for entity in step3_entities if entity.get('globalId')}
    
    for element_id in lost_ids:
        step1_info = step1_breps[element_id]
        element_name = step1_info['element_name']
        element_type = step1_info['element_type']
        
        print(f"\n❌ LOST: {element_name} ({element_type})")
        print(f"   GlobalId: {element_id}")
        
        # Check what happened to this element in Step 3
        step3_element = step3_lookup.get(element_id)
        if step3_element:
            step3_rep = step3_element.get('representation', {})
            if step3_rep.get('type') == 'IfcProductDefinitionShape':
                step3_reps = step3_rep.get('representations', [])
                print(f"   Step 3 representations: {len(step3_reps)}")
                
                # Find what representation types it has now
                for i, rep_ref in enumerate(step3_reps):
                    ref_id = rep_ref.get('ref')
                    # Find the referenced representation
                    for entity in step3_entities:
                        if entity.get('globalId') == ref_id and entity.get('type') == 'IfcShapeRepresentation':
                            rep_id = entity.get('representationIdentifier')
                            rep_type = entity.get('representationType')
                            print(f"     Rep {i+1}: {rep_id}-{rep_type}")
                            
                            if rep_id == 'Body' and rep_type != 'Brep':
                                print(f"       🔄 CONVERTED: Body-Brep → Body-{rep_type}")
            else:
                print("   ❌ No representation found in Step 3")
        else:
            print("   ❌ Element not found in Step 3")

def analyze_geometry_complexity(results: Dict[str, Any], target_element: str = None) -> None:
    """Analyze geometry complexity (faces/vertices) for specific elements"""
    
    step1_entities = results['step1_entities'] 
    step3_entities = results['step3_entities']
    
    print(f"\n🔍 GEOMETRY COMPLEXITY ANALYSIS")
    print("="*60)
    
    # Create lookups
    step1_lookup = {entity.get('globalId'): entity for entity in step1_entities if entity.get('globalId')}
    step3_lookup = {entity.get('globalId'): entity for entity in step3_entities if entity.get('globalId')}
    
    elements_to_check = []
    if target_element:
        # Find element by name
        for entity in step1_entities:
            if entity.get('name') == target_element:
                elements_to_check.append(entity.get('globalId'))
    else:
        # Check all wall elements
        for entity in step1_entities:
            if entity.get('type') in ['IfcWall', 'IfcWallStandardCase']:
                elements_to_check.append(entity.get('globalId'))
    
    for element_id in elements_to_check[:5]:  # Limit to first 5 for readability
        step1_element = step1_lookup.get(element_id)
        step3_element = step3_lookup.get(element_id)
        
        if not step1_element or not step3_element:
            continue
            
        element_name = step1_element.get('name', 'unnamed')
        element_type = step1_element.get('type')
        
        print(f"\n🏗️  {element_name} ({element_type})")
        
        # Count geometry complexity in Step 1
        step1_faces, step1_vertices = count_geometry_complexity(step1_entities, step1_element)
        step3_faces, step3_vertices = count_geometry_complexity(step3_entities, step3_element) 
        
        print(f"   Step 1: {step1_faces} faces, {step1_vertices} vertices")
        print(f"   Step 3: {step3_faces} faces, {step3_vertices} vertices")
        
        if step1_faces > step3_faces:
            face_loss = ((step1_faces - step3_faces) / step1_faces * 100) if step1_faces > 0 else 0
            vertex_loss = ((step1_vertices - step3_vertices) / step1_vertices * 100) if step1_vertices > 0 else 0
            print(f"   📉 GEOMETRY LOSS: {face_loss:.1f}% faces, {vertex_loss:.1f}% vertices")
            
            if face_loss > 50:
                print(f"   🚨 CRITICAL GEOMETRY SIMPLIFICATION DETECTED")

def count_geometry_complexity(entities: List[Dict[str, Any]], element: Dict[str, Any]) -> Tuple[int, int]:
    """Count faces and vertices for an element's geometry"""
    
    total_faces = 0
    total_vertices = 0
    
    representation = element.get('representation', {})
    if representation.get('type') != 'IfcProductDefinitionShape':
        return 0, 0
        
    representations = representation.get('representations', [])
    for rep_ref in representations:
        ref_id = rep_ref.get('ref')
        
        # Find the shape representation
        for entity in entities:
            if entity.get('globalId') == ref_id and entity.get('type') == 'IfcShapeRepresentation':
                items = entity.get('items', [])
                for item_ref in items:
                    if isinstance(item_ref, dict) and 'ref' in item_ref:
                        item_id = item_ref.get('ref')
                        # Find the geometry item
                        for geom_entity in entities:
                            if geom_entity.get('globalId') == item_id:
                                faces, vertices = count_brep_complexity(geom_entity)
                                total_faces += faces
                                total_vertices += vertices
    
    return total_faces, total_vertices

def count_brep_complexity(geom_entity: Dict[str, Any]) -> Tuple[int, int]:
    """Count faces and vertices in a geometry entity"""
    
    entity_type = geom_entity.get('type')
    
    if entity_type == 'IfcFacetedBrep':
        outer = geom_entity.get('outer', {})
        if outer.get('type') == 'IfcClosedShell':
            faces = outer.get('cfsFaces', [])
            vertices = set()
            
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
            
            return len(faces), len(vertices)
    
    return 0, 0

def main():
    if len(sys.argv) < 3:
        print("Usage: python debug_body_brep_loss.py <step1_json> <step3_json> [target_element_name]")
        print("Example: python debug_body_brep_loss.py step1.json step3.json 'Wand-Ext-OG-1'")
        sys.exit(1)
    
    step1_file = sys.argv[1]
    step3_file = sys.argv[2]
    target_element = sys.argv[3] if len(sys.argv) > 3 else None
    
    print("🔍 DEBUG BODY-BREP REPRESENTATION LOSS")
    print("="*60)
    print(f"Analyzing representation changes from Step 1 to Step 3")
    print(f"Target element: {target_element or 'All elements'}")
    
    # Main analysis
    results = analyze_representation_changes(step1_file, step3_file)
    
    # Detailed analysis of lost elements
    analyze_lost_elements(results)
    
    # Geometry complexity analysis
    analyze_geometry_complexity(results, target_element)
    
    print(f"\n🎯 SUMMARY")
    print("="*60)
    print(f"Body-Brep representations: {results['step1_count']} → {results['step3_count']}")
    print(f"Success rate: {(results['step3_count']/results['step1_count']*100):.1f}%" if results['step1_count'] > 0 else "No Body-Brep representations found")
    print(f"Elements losing Body-Brep: {len(results['lost'])}")
    
    if target_element:
        print(f"Target element '{target_element}' analysis completed")

if __name__ == "__main__":
    main()