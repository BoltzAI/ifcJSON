#!/usr/bin/env python3
"""
Find IfcFacetedBrep Assets Tool

Searches through asset library files to find IfcFacetedBrep entities and analyze their complexity.
Useful for debugging geometry simplification issues in the pipeline.
"""

import json
import os
import sys
import glob
from typing import Dict, List, Any, Tuple

def analyze_ifcfacetedbrep_in_assets(assets_directory: str) -> None:
    """Analyze IfcFacetedBrep entities in asset library files"""
    
    print(f"🔍 SEARCHING FOR IfcFacetedBrep IN ASSET LIBRARY")
    print(f"Directory: {assets_directory}")
    print("=" * 70)
    
    if not os.path.exists(assets_directory):
        print(f"❌ Directory not found: {assets_directory}")
        return
    
    # Find all asset files
    asset_pattern = os.path.join(assets_directory, "extracted_*.json")
    asset_files = glob.glob(asset_pattern)
    
    if not asset_files:
        print(f"❌ No asset files found matching pattern: {asset_pattern}")
        return
    
    print(f"📂 Found {len(asset_files)} asset files to analyze")
    print()
    
    total_breps = 0
    face_count_distribution = {}
    brep_details = []
    
    for asset_file in sorted(asset_files):
        asset_name = os.path.basename(asset_file)
        breps_in_file = analyze_asset_file(asset_file)
        
        if breps_in_file:
            total_breps += len(breps_in_file)
            print(f"📄 {asset_name}: {len(breps_in_file)} IfcFacetedBrep(s)")
            
            for brep_info in breps_in_file:
                face_count = brep_info['face_count']
                vertex_count = brep_info['vertex_count']
                global_id = brep_info['global_id']
                
                print(f"    🔸 {global_id}: {face_count} faces, {vertex_count} vertices")
                
                # Track distribution
                if face_count not in face_count_distribution:
                    face_count_distribution[face_count] = 0
                face_count_distribution[face_count] += 1
                
                brep_details.append({
                    'asset_file': asset_name,
                    'global_id': global_id,
                    'face_count': face_count,
                    'vertex_count': vertex_count
                })
            print()
    
    # Summary report
    print("📊 IFCFACETEDBREP ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"Total IfcFacetedBrep entities found: {total_breps}")
    
    if total_breps > 0:
        print(f"Files containing IfcFacetedBrep: {len([f for f in asset_files if analyze_asset_file(f)])}")
        
        print("\n📈 Face Count Distribution:")
        for face_count in sorted(face_count_distribution.keys()):
            count = face_count_distribution[face_count]
            print(f"    {face_count} faces: {count} entity(ies)")
        
        # Highlight specific face counts of interest
        target_counts = [130, 135, 394]
        print(f"\n🎯 Target Face Counts Analysis:")
        for target in target_counts:
            if target in face_count_distribution:
                count = face_count_distribution[target]
                print(f"    ✅ {target} faces: {count} entity(ies) found")
                
                # Show details for target counts
                matching_breps = [b for b in brep_details if b['face_count'] == target]
                for brep in matching_breps:
                    print(f"        📁 {brep['asset_file']} | {brep['global_id']} | {brep['vertex_count']} vertices")
            else:
                print(f"    ❌ {target} faces: 0 entities found")
        
        # Show complexity statistics
        face_counts = [b['face_count'] for b in brep_details]
        vertex_counts = [b['vertex_count'] for b in brep_details]
        
        print(f"\n📏 Complexity Statistics:")
        print(f"    Face counts - Min: {min(face_counts)}, Max: {max(face_counts)}, Avg: {sum(face_counts)/len(face_counts):.1f}")
        print(f"    Vertex counts - Min: {min(vertex_counts)}, Max: {max(vertex_counts)}, Avg: {sum(vertex_counts)/len(vertex_counts):.1f}")
        
        # Show most complex entities
        print(f"\n🏆 Most Complex IfcFacetedBrep Entities:")
        sorted_by_faces = sorted(brep_details, key=lambda x: x['face_count'], reverse=True)
        for i, brep in enumerate(sorted_by_faces[:5]):
            print(f"    {i+1}. {brep['global_id']}: {brep['face_count']} faces, {brep['vertex_count']} vertices")
            print(f"       📁 {brep['asset_file']}")
    
    else:
        print("❌ No IfcFacetedBrep entities found in asset library")
        print("    This might indicate:")
        print("    - Geometry is using IfcExtrudedAreaSolid instead")
        print("    - Complex geometry was simplified during extraction")
        print("    - Assets are stored in a different format")

def analyze_asset_file(file_path: str) -> List[Dict[str, Any]]:
    """Analyze a single asset file for IfcFacetedBrep entities"""
    
    try:
        with open(file_path, 'r') as f:
            asset_data = json.load(f)
        
        # Check if this is valid ifcJSON asset format
        if not isinstance(asset_data, dict) or 'data' not in asset_data:
            return []
        
        entities = asset_data.get('data', [])
        brep_entities = []
        
        for entity in entities:
            if entity.get('type') == 'IfcFacetedBrep':
                brep_info = analyze_faceted_brep(entity, entities)
                if brep_info:
                    brep_entities.append(brep_info)
        
        return brep_entities
        
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        # Silently skip invalid files
        return []

def analyze_faceted_brep(brep_entity: Dict[str, Any], all_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze an IfcFacetedBrep entity to count faces and vertices"""
    
    # Create lookup for referenced entities
    entity_lookup = {entity.get('globalId'): entity for entity in all_entities if entity.get('globalId')}
    
    global_id = brep_entity.get('globalId', 'unknown')
    face_count = 0
    vertex_count = 0
    
    # Analyze the outer shell
    outer = brep_entity.get('outer', {})
    
    if isinstance(outer, dict):
        if 'ref' in outer:
            # Referenced shell
            shell_entity = entity_lookup.get(outer['ref'])
            if shell_entity and shell_entity.get('type') == 'IfcClosedShell':
                faces = shell_entity.get('cfsFaces', [])
                face_count = len(faces)
                vertex_count = count_unique_vertices(faces, entity_lookup)
        else:
            # Inline shell
            if outer.get('type') == 'IfcClosedShell':
                faces = outer.get('cfsFaces', [])
                face_count = len(faces)
                vertex_count = count_unique_vertices(faces, entity_lookup)
    
    return {
        'global_id': global_id,
        'face_count': face_count,
        'vertex_count': vertex_count
    }

def count_unique_vertices(faces: List[Any], entity_lookup: Dict[str, Any]) -> int:
    """Count unique vertices across all faces"""
    
    unique_vertices = set()
    
    for face_ref in faces:
        vertices = extract_vertices_from_face(face_ref, entity_lookup)
        unique_vertices.update(vertices)
    
    return len(unique_vertices)

def extract_vertices_from_face(face_ref: Any, entity_lookup: Dict[str, Any]) -> set:
    """Extract unique vertex coordinates from a face"""
    
    vertices = set()
    
    # Resolve face entity
    face_entity = None
    if isinstance(face_ref, dict):
        if 'ref' in face_ref:
            face_entity = entity_lookup.get(face_ref['ref'])
        else:
            if face_ref.get('type') == 'IfcFace':
                face_entity = face_ref
    
    if not face_entity or face_entity.get('type') != 'IfcFace':
        return vertices
    
    # Process face bounds
    bounds = face_entity.get('bounds', [])
    for bound_ref in bounds:
        bound_vertices = extract_vertices_from_bound(bound_ref, entity_lookup)
        vertices.update(bound_vertices)
    
    return vertices

def extract_vertices_from_bound(bound_ref: Any, entity_lookup: Dict[str, Any]) -> set:
    """Extract vertices from a face bound"""
    
    vertices = set()
    
    # Resolve bound entity
    bound_entity = None
    if isinstance(bound_ref, dict):
        if 'ref' in bound_ref:
            bound_entity = entity_lookup.get(bound_ref['ref'])
        else:
            if bound_ref.get('type') in ['IfcFaceOuterBound', 'IfcFaceBound']:
                bound_entity = bound_ref
    
    if not bound_entity:
        return vertices
    
    # Get the loop
    loop_ref = bound_entity.get('bound', {})
    loop_vertices = extract_vertices_from_loop(loop_ref, entity_lookup)
    vertices.update(loop_vertices)
    
    return vertices

def extract_vertices_from_loop(loop_ref: Any, entity_lookup: Dict[str, Any]) -> set:
    """Extract vertices from a loop (polygon)"""
    
    vertices = set()
    
    # Resolve loop entity
    loop_entity = None
    if isinstance(loop_ref, dict):
        if 'ref' in loop_ref:
            loop_entity = entity_lookup.get(loop_ref['ref'])
        else:
            if loop_ref.get('type') == 'IfcPolyLoop':
                loop_entity = loop_ref
    
    if not loop_entity or loop_entity.get('type') != 'IfcPolyLoop':
        return vertices
    
    # Extract coordinates from polygon points
    polygon = loop_entity.get('polygon', [])
    for point_ref in polygon:
        coordinates = extract_point_coordinates(point_ref, entity_lookup)
        if coordinates:
            vertices.add(coordinates)
    
    return vertices

def extract_point_coordinates(point_ref: Any, entity_lookup: Dict[str, Any]) -> tuple:
    """Extract coordinates from a point reference"""
    
    # Resolve point entity
    point_entity = None
    if isinstance(point_ref, dict):
        if 'ref' in point_ref:
            point_entity = entity_lookup.get(point_ref['ref'])
        else:
            if point_ref.get('type') == 'IfcCartesianPoint':
                point_entity = point_ref
    
    if not point_entity or point_entity.get('type') != 'IfcCartesianPoint':
        return None
    
    coordinates = point_entity.get('coordinates', [])
    if coordinates and len(coordinates) >= 3:
        return tuple(coordinates[:3])
    
    return None

def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python find_ifcfacetedbrep_assets.py <assets_directory>")
        print()
        print("Examples:")
        print("  python find_ifcfacetedbrep_assets.py /path/to/assets/OrangeHouse/")
        print("  python find_ifcfacetedbrep_assets.py ../../../out-todo70/assets/OrangeHouse/")
        print()
        print("Description:")
        print("  Searches asset library files for IfcFacetedBrep entities and analyzes their complexity")
        print("  Useful for debugging geometry simplification in BIM pipelines")
        sys.exit(1)
    
    assets_directory = sys.argv[1]
    analyze_ifcfacetedbrep_in_assets(assets_directory)

if __name__ == "__main__":
    main()