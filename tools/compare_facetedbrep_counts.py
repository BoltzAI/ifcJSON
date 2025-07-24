#!/usr/bin/env python3
"""
Compare IfcFacetedBrep face counts between official 2-step pipeline and our 4-step pipeline.
This script helps identify if there are differences in tessellation between pipelines.
"""

import json
import sys
from collections import Counter
import os
import glob

def analyze_file_for_breps(file_path):
    """Analyze a single ifcJSON file for IfcFacetedBrep entities"""
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return []
    
    # Extract data array
    entities = data.get('data', [])
    
    # Find all IfcFacetedBrep entities (both top-level and nested)
    faceted_breps = []
    
    def find_nested_breps(obj, path=""):
        """Recursively find IfcFacetedBrep entities in nested structures"""
        if isinstance(obj, dict):
            if obj.get('type') == 'IfcFacetedBrep':
                # Get the outer shell and count faces
                outer = obj.get('outer')
                if outer:
                    cfs_faces = outer.get('cfsFaces', [])
                    face_count = len(cfs_faces)
                    faceted_breps.append({
                        'face_count': face_count,
                        'path': path,
                        'file': os.path.basename(file_path)
                    })
            
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
    
    return faceted_breps

def analyze_asset_directory(directory_path):
    """Analyze all asset files in a directory for IfcFacetedBrep entities"""
    
    asset_pattern = os.path.join(directory_path, "extracted_*.json")
    asset_files = glob.glob(asset_pattern)
    
    all_breps = []
    
    for file_path in asset_files:
        breps = analyze_file_for_breps(file_path)
        all_breps.extend(breps)
    
    return all_breps

def main():
    print("🔍 COMPARING IfcFacetedBrep FACE COUNTS BETWEEN PIPELINES")
    print("=" * 80)
    
    # Official 2-step pipeline (Step 1 output)
    official_file = "/Users/leixu/Documents/work_now/genai/genai-bim-ifc/out-todo70/step1_official_json/OrangeHouse.json"
    
    # Our 4-step pipeline (asset library)
    our_pipeline_dir = "/Users/leixu/Documents/work_now/genai/genai-bim-ifc/out-todo70/assets/OrangeHouse/"
    
    print("🔶 ANALYZING OFFICIAL 2-STEP PIPELINE (Step 1 Output)")
    print("-" * 50)
    
    if os.path.exists(official_file):
        official_breps = analyze_file_for_breps(official_file)
        print(f"Found {len(official_breps)} IfcFacetedBrep entities")
        
        # Count face distributions
        official_face_counts = [brep['face_count'] for brep in official_breps]
        official_counter = Counter(official_face_counts)
        
        print("Face count distribution:")
        for count, frequency in sorted(official_counter.items()):
            print(f"  {count} faces: {frequency} entities")
        
        # Circular opening candidates
        circular_candidates_official = [brep for brep in official_breps if 125 <= brep['face_count'] <= 140]
        print(f"\n🎯 Circular opening candidates (125-140 faces): {len(circular_candidates_official)}")
        for candidate in circular_candidates_official:
            print(f"  {candidate['face_count']} faces (file: {candidate['file']})")
    else:
        print(f"❌ Official file not found: {official_file}")
        official_breps = []
        official_counter = Counter()
        circular_candidates_official = []
    
    print("\n🔷 ANALYZING OUR 4-STEP PIPELINE (Asset Library)")
    print("-" * 50)
    
    if os.path.exists(our_pipeline_dir):
        our_breps = analyze_asset_directory(our_pipeline_dir)
        print(f"Found {len(our_breps)} IfcFacetedBrep entities")
        
        # Count face distributions
        our_face_counts = [brep['face_count'] for brep in our_breps]
        our_counter = Counter(our_face_counts)
        
        print("Face count distribution:")
        for count, frequency in sorted(our_counter.items()):
            print(f"  {count} faces: {frequency} entities")
        
        # Circular opening candidates
        circular_candidates_ours = [brep for brep in our_breps if 125 <= brep['face_count'] <= 140]
        print(f"\n🎯 Circular opening candidates (125-140 faces): {len(circular_candidates_ours)}")
        for candidate in circular_candidates_ours:
            print(f"  {candidate['face_count']} faces (file: {candidate['file']})")
    else:
        print(f"❌ Our pipeline directory not found: {our_pipeline_dir}")
        our_breps = []
        our_counter = Counter()
        circular_candidates_ours = []
    
    print("\n📊 COMPARISON RESULTS")
    print("=" * 50)
    
    print(f"Total IfcFacetedBrep entities:")
    print(f"  Official pipeline: {len(official_breps)}")
    print(f"  Our pipeline: {len(our_breps)}")
    
    print(f"\nCircular opening candidates (125-140 faces):")
    print(f"  Official pipeline: {len(circular_candidates_official)}")
    print(f"  Our pipeline: {len(circular_candidates_ours)}")
    
    # Check for 130-face and 135-face entities specifically
    official_130 = official_counter.get(130, 0)
    official_135 = official_counter.get(135, 0)
    our_130 = our_counter.get(130, 0)
    our_135 = our_counter.get(135, 0)
    
    print(f"\nSpecific face counts:")
    print(f"  130 faces - Official: {official_130}, Ours: {our_130}")
    print(f"  135 faces - Official: {official_135}, Ours: {our_135}")
    
    # Analysis conclusion
    print("\n🏁 CONCLUSION")
    print("=" * 30)
    
    if official_130 > 0 and our_130 > 0 and official_135 == 0 and our_135 == 0:
        print("✅ FINDING: Both pipelines generate 130-face IfcFacetedBrep entities for circular openings")
        print("✅ RESULT: Our pipeline is CONSISTENT with the official 2-step pipeline")
        print("📝 NOTE: The expected '135-face' result might be incorrect")
    elif official_135 > 0 and our_130 > 0:
        print("⚠️  FINDING: Official pipeline generates 135-face entities, ours generates 130-face")
        print("❗ RESULT: There is a discrepancy that needs investigation")
    elif official_130 == 0 and official_135 == 0:
        print("🤔 FINDING: Official pipeline doesn't contain circular opening candidates")
        print("📝 NOTE: May need to check different pipeline steps")
    else:
        print("🔍 FINDING: Mixed results - further investigation needed")
    
    # Show all unique face counts for comparison
    all_official_counts = set(official_counter.keys())
    all_our_counts = set(our_counter.keys())
    
    print(f"\nAll unique face counts:")
    print(f"  Official: {sorted(all_official_counts)}")
    print(f"  Ours: {sorted(all_our_counts)}")
    
    # Differences
    only_official = all_official_counts - all_our_counts
    only_ours = all_our_counts - all_official_counts
    
    if only_official:
        print(f"  Only in official: {sorted(only_official)}")
    if only_ours:
        print(f"  Only in ours: {sorted(only_ours)}")
    
    print(f"\n✅ Analysis complete!")

if __name__ == "__main__":
    main()