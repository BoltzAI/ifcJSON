#!/usr/bin/env python3
"""
Final IFC Geometry Extractor

Extracts actual face/vertex counts from final IFC files using ifcopenshell.
This shows the REAL geometry complexity as seen in IFC viewers, not just the JSON structure.
"""

import sys
import ifcopenshell
import ifcopenshell.geom
from typing import Dict, List, Any, Optional, Tuple

def extract_element_geometry(ifc_file_path: str, element_name: str = None) -> None:
    """Extract geometry information from IFC file for specific element or all elements"""
    
    print(f"🔍 EXTRACTING FINAL IFC GEOMETRY")
    print(f"File: {ifc_file_path}")
    if element_name:
        print(f"Element: {element_name}")
    else:
        print("Element: ALL BUILDING ELEMENTS")
    print("=" * 70)
    
    try:
        # Load IFC file
        model = ifcopenshell.open(ifc_file_path)
        print(f"✅ IFC file loaded successfully")
        
        # Setup geometry settings
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        
        # Find target elements
        if element_name:
            elements = [e for e in model.by_type("IfcBuildingElement") if getattr(e, 'Name', None) == element_name]
            if not elements:
                print(f"❌ Element '{element_name}' not found")
                return
        else:
            # Get all building elements
            element_types = [
                "IfcWall", "IfcWallStandardCase", "IfcWindow", "IfcDoor", 
                "IfcSlab", "IfcBeam", "IfcColumn", "IfcStair", "IfcRoof"
            ]
            elements = []
            for elem_type in element_types:
                elements.extend(model.by_type(elem_type))
        
        if not elements:
            print("❌ No building elements found")
            return
        
        print(f"📊 Found {len(elements)} elements to analyze\n")
        
        # Analyze each element
        total_analyzed = 0
        high_complexity_count = 0
        
        for element in elements:
            result = analyze_element_geometry(element, settings)
            if result:
                total_analyzed += 1
                if result['faces'] >= 100:
                    high_complexity_count += 1
                print_element_result(result)
        
        # Summary
        print("📊 GEOMETRY EXTRACTION SUMMARY")
        print("=" * 50)
        print(f"Total elements analyzed: {total_analyzed}")
        print(f"High complexity elements (100+ faces): {high_complexity_count}")
        if total_analyzed > 0:
            complexity_rate = (high_complexity_count / total_analyzed) * 100
            print(f"High complexity rate: {complexity_rate:.1f}%")
        
    except Exception as e:
        print(f"❌ Error processing IFC file: {e}")

def analyze_element_geometry(element, settings) -> Optional[Dict[str, Any]]:
    """Analyze geometry for a single element using ifcopenshell"""
    
    try:
        # Get element basic info
        element_name = getattr(element, 'Name', 'unnamed')
        element_type = element.is_a()
        element_id = element.GlobalId
        
        # Try to create geometry
        shape = ifcopenshell.geom.create_shape(settings, element)
        if not shape:
            return {
                'name': element_name,
                'type': element_type,
                'id': element_id,
                'faces': 0,
                'vertices': 0,
                'error': 'No geometry created'
            }
        
        # Get mesh data
        geometry = shape.geometry
        faces = geometry.faces
        vertices = geometry.verts
        
        # Count faces and vertices
        face_count = len(faces) // 3  # faces are stored as triangles (3 indices per face)
        vertex_count = len(vertices) // 3  # vertices are stored as (x,y,z) triplets
        
        return {
            'name': element_name,
            'type': element_type,
            'id': element_id,
            'faces': face_count,
            'vertices': vertex_count,
            'has_geometry': True
        }
        
    except Exception as e:
        return {
            'name': getattr(element, 'Name', 'unnamed'),
            'type': element.is_a(),
            'id': element.GlobalId,
            'faces': 0,
            'vertices': 0,
            'error': str(e)
        }

def print_element_result(result: Dict[str, Any]) -> None:
    """Print analysis result for a single element"""
    
    name = result['name']
    elem_type = result['type']
    faces = result['faces']
    vertices = result['vertices']
    
    print(f"🏗️  {name} ({elem_type})")
    
    if result.get('error'):
        print(f"   ❌ Error: {result['error']}")
    elif faces > 0:
        print(f"   📐 Faces: {faces}, Vertices: {vertices}")
        
        # Classify complexity
        if faces >= 200:
            print(f"   🔥 VERY HIGH complexity")
        elif faces >= 100:
            print(f"   🎯 HIGH complexity")
        elif faces >= 50:
            print(f"   ⚡ MEDIUM complexity")
        elif faces >= 20:
            print(f"   📦 LOW complexity")
        else:
            print(f"   🔲 MINIMAL complexity")
            
        # Special markers for target face counts
        if faces == 135:
            print(f"   ✨ TARGET MATCH: 135 faces (expected high-quality circular opening)")
        elif faces == 130:
            print(f"   ✅ STANDARD: 130 faces (standard circular opening)")
        elif faces == 37:
            print(f"   ⚠️  SIMPLIFIED: 37 faces (potentially over-simplified)")
            
    else:
        print(f"   🔲 No triangulated geometry")
    
    print()

def find_specific_face_counts(ifc_file_path: str, target_faces: List[int]) -> None:
    """Find elements with specific face counts"""
    
    print(f"🎯 SEARCHING FOR SPECIFIC FACE COUNTS: {target_faces}")
    print(f"File: {ifc_file_path}")
    print("=" * 70)
    
    try:
        model = ifcopenshell.open(ifc_file_path)
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        
        # Get all building elements
        elements = []
        for elem_type in ["IfcWall", "IfcWallStandardCase", "IfcWindow", "IfcDoor", "IfcSlab"]:
            elements.extend(model.by_type(elem_type))
        
        matches = {}
        for target in target_faces:
            matches[target] = []
        
        for element in elements:
            result = analyze_element_geometry(element, settings)
            if result and result['faces'] in target_faces:
                matches[result['faces']].append(result)
        
        # Report matches
        for target in target_faces:
            count = len(matches[target])
            print(f"📊 {target} faces: {count} elements found")
            
            for match in matches[target][:5]:  # Show first 5 matches
                print(f"   • {match['name']} ({match['type']}) - {match['vertices']} vertices")
            
            if len(matches[target]) > 5:
                print(f"   ... and {len(matches[target]) - 5} more")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python extract_final_ifc_geometry.py <ifc_file> [element_name|--search face_counts]")
        print()
        print("Examples:")
        print("  python extract_final_ifc_geometry.py OrangeHouse.ifc")
        print("  python extract_final_ifc_geometry.py OrangeHouse.ifc 'Wand-Ext-OG-1'")
        print("  python extract_final_ifc_geometry.py OrangeHouse.ifc --search 135,130,37")
        print()
        print("Description:")
        print("  Extracts actual face/vertex counts from IFC files using ifcopenshell")
        print("  Shows real geometry complexity as seen in IFC viewers")
        print("  --search mode finds elements with specific face counts")
        sys.exit(1)
    
    ifc_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        if sys.argv[2] == "--search" and len(sys.argv) > 3:
            # Search mode
            try:
                target_faces = [int(x.strip()) for x in sys.argv[3].split(',')]
                find_specific_face_counts(ifc_file, target_faces)
            except ValueError:
                print("❌ Error: Face counts must be comma-separated integers")
                sys.exit(1)
        else:
            # Specific element mode
            element_name = sys.argv[2]
            extract_element_geometry(ifc_file, element_name)
    else:
        # All elements mode
        extract_element_geometry(ifc_file)

if __name__ == "__main__":
    main()