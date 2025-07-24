#!/usr/bin/env python3
"""
Analyze IfcFacetedBrep entities and their face counts in ifcJSON files.
This script helps identify differences in tessellation between different pipelines.
"""

import json
import sys
from collections import Counter, defaultdict
import os

def analyze_facetedbrep_faces(ifcjson_file_path):
    """Analyze IfcFacetedBrep entities and count their faces"""
    
    print(f"🔍 ANALYZING IfcFacetedBrep FACES")
    print(f"File: {ifcjson_file_path}")
    print("=" * 80)
    
    # Load the ifcJSON file
    try:
        with open(ifcjson_file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    # Extract data array
    entities = data.get('data', [])
    print(f"📊 Total entities in file: {len(entities)}")
    
    # Find all IfcFacetedBrep entities (both top-level and nested)
    faceted_breps = []
    face_sets = {}  # Store IfcFace entities by reference
    
    def find_nested_breps(obj, path=""):
        """Recursively find IfcFacetedBrep entities in nested structures"""
        if isinstance(obj, dict):
            if obj.get('type') == 'IfcFacetedBrep':
                faceted_breps.append((obj, path))
            elif obj.get('type') == 'IfcFace':
                # Store faces for reference lookup
                global_id = obj.get('globalId')
                if global_id:
                    face_sets[global_id] = obj
            # Recursively search in all dict values
            for key, value in obj.items():
                find_nested_breps(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            # Recursively search in all list items
            for i, item in enumerate(obj):
                find_nested_breps(item, f"{path}[{i}]" if path else f"[{i}]")
    
    # Search through all entities and nested structures
    for i, entity in enumerate(entities):
        find_nested_breps(entity, f"entity[{i}]")
    
    print(f"🔷 Found {len(faceted_breps)} IfcFacetedBrep entities")
    print(f"🔷 Found {len(face_sets)} IfcFace entities")
    
    if not faceted_breps:
        print("❌ No IfcFacetedBrep entities found")
        return
    
    # Analyze each IfcFacetedBrep
    face_counts = []
    vertex_counts = []
    brep_details = []
    
    for i, (brep, path) in enumerate(faceted_breps):
        brep_id = brep.get('globalId', f'unknown_{i}')
        
        # Get the outer shell
        outer = brep.get('outer')
        if not outer:
            print(f"⚠️  IfcFacetedBrep {brep_id} has no outer shell")
            continue
            
        # Count faces
        cfs_faces = outer.get('cfsFaces', [])
        face_count = len(cfs_faces)
        face_counts.append(face_count)
        
        # Try to count vertices by analyzing the first few faces
        vertex_set = set()
        face_vertex_counts = []
        
        for j, face_item in enumerate(cfs_faces[:5]):  # Sample first 5 faces to understand structure
            face_entity = None
            
            # Handle both reference and inline face entities
            if isinstance(face_item, dict):
                if 'ref' in face_item:
                    # Referenced face
                    face_id = face_item['ref']
                    face_entity = face_sets.get(face_id)
                elif face_item.get('type') == 'IfcFace':
                    # Inline face
                    face_entity = face_item
            
            if face_entity:
                # Get face bounds
                bounds = face_entity.get('bounds', [])
                for bound in bounds:
                    if isinstance(bound, dict) and bound.get('type') == 'IfcFaceOuterBound':
                        bound_ref = bound.get('bound', {})
                        if bound_ref.get('type') == 'IfcPolyLoop':
                            polygon = bound_ref.get('polygon', [])
                            face_vertex_counts.append(len(polygon))
                            for vertex_ref in polygon:
                                # Handle both reference and inline vertices
                                if isinstance(vertex_ref, dict):
                                    if 'ref' in vertex_ref:
                                        vertex_set.add(vertex_ref['ref'])
                                    elif vertex_ref.get('type') == 'IfcCartesianPoint':
                                        # For inline vertices, use coordinates as identifier
                                        coords = vertex_ref.get('coordinates', [])
                                        vertex_set.add(tuple(coords))
        
        vertex_count = len(vertex_set) if vertex_set else "unknown"
        vertex_counts.append(vertex_count)
        
        avg_vertices_per_face = sum(face_vertex_counts) / len(face_vertex_counts) if face_vertex_counts else "unknown"
        
        brep_details.append({
            'globalId': brep_id,
            'path': path,
            'face_count': face_count,
            'vertex_count': vertex_count,
            'avg_vertices_per_face': avg_vertices_per_face,
            'sample_face_vertex_counts': face_vertex_counts[:5]
        })
        
        print(f"  📋 IfcFacetedBrep {i+1}: {brep_id}")
        print(f"     Path: {path}")
        print(f"     Faces: {face_count}")
        print(f"     Vertices (sampled): {vertex_count}")
        print(f"     Avg vertices per face: {avg_vertices_per_face}")
    
    # Summary statistics
    print("\n📈 SUMMARY STATISTICS")
    print("=" * 40)
    
    face_counter = Counter(face_counts)
    print(f"Face count distribution:")
    for count, frequency in sorted(face_counter.items()):
        print(f"  {count} faces: {frequency} entities")
    
    # Identify circular opening candidates (typically 130-135 faces)
    circular_candidates = [detail for detail in brep_details if 125 <= detail['face_count'] <= 140]
    print(f"\n🎯 CIRCULAR OPENING CANDIDATES (125-140 faces): {len(circular_candidates)}")
    for candidate in circular_candidates:
        print(f"  {candidate['globalId']}: {candidate['face_count']} faces, {candidate['vertex_count']} vertices")
    
    # Statistical summary
    if face_counts:
        print(f"\nFace count statistics:")
        print(f"  Min: {min(face_counts)}")
        print(f"  Max: {max(face_counts)}")
        print(f"  Average: {sum(face_counts)/len(face_counts):.1f}")
        print(f"  Total IfcFacetedBrep entities: {len(face_counts)}")
    
    return {
        'total_breps': len(faceted_breps),
        'face_counts': face_counts,
        'vertex_counts': vertex_counts,
        'brep_details': brep_details,
        'circular_candidates': circular_candidates,
        'face_distribution': dict(face_counter)
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_facetedbrep_faces.py <ifcjson_file_path>")
        sys.exit(1)
    
    ifcjson_file_path = sys.argv[1]
    
    if not os.path.exists(ifcjson_file_path):
        print(f"❌ File not found: {ifcjson_file_path}")
        sys.exit(1)
    
    result = analyze_facetedbrep_faces(ifcjson_file_path)
    
    if result:
        print(f"\n✅ Analysis complete!")

if __name__ == "__main__":
    main()