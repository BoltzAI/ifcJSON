#!/usr/bin/env python3
"""
Find IfcOpeningElement Tool

Finds and analyzes IfcOpeningElement entities in IFC files, including their relationships
with walls and filled elements (windows/doors).

Usage:
    python find_opening_elements.py <ifc_file.ifc> [opening_name]
    
Examples:
    python find_opening_elements.py ../../ifc_files/OrangeHouse.ifc
    python find_opening_elements.py ../../out-temp/step4_final_ifc/OrangeHouse_roundtrip.ifc "OG-Fenster-1"
    
Description:
    Analyzes IfcOpeningElement entities and their void/fill relationships with walls and windows/doors
"""

import sys
from pathlib import Path

try:
    import ifcopenshell
    import ifcopenshell.util.element
    IFCOPENSHELL_AVAILABLE = True
except ImportError:
    IFCOPENSHELL_AVAILABLE = False

def find_opening_elements(ifc_file: str, target_opening_name: str = None):
    """Find and analyze IfcOpeningElement entities"""
    
    print(f"🔍 FINDING OPENING ELEMENTS")
    print(f"File: {ifc_file}")
    if target_opening_name:
        print(f"Target: {target_opening_name}")
    print("=" * 70)
    
    if not IFCOPENSHELL_AVAILABLE:
        print("❌ Error: ifcopenshell not available")
        return
    
    try:
        model = ifcopenshell.open(ifc_file)
        print("✅ IFC file loaded successfully")
    except Exception as e:
        print(f"❌ Error loading IFC file: {e}")
        return
    
    # Find all opening elements
    opening_elements = model.by_type('IfcOpeningElement')
    print(f"📊 Found {len(opening_elements)} IfcOpeningElement entities")
    
    if len(opening_elements) == 0:
        print("❌ No IfcOpeningElement entities found in file")
        return
    
    # Find void relationships (openings in walls)
    void_relationships = model.by_type('IfcRelVoidsElement')
    void_map = {}  # opening_id -> wall_id
    for rel in void_relationships:
        if hasattr(rel, 'RelatedOpeningElement') and hasattr(rel, 'RelatingBuildingElement'):
            opening_id = rel.RelatedOpeningElement.GlobalId if hasattr(rel.RelatedOpeningElement, 'GlobalId') else str(rel.RelatedOpeningElement)
            wall_id = rel.RelatingBuildingElement.GlobalId if hasattr(rel.RelatingBuildingElement, 'GlobalId') else str(rel.RelatingBuildingElement)
            wall_name = getattr(rel.RelatingBuildingElement, 'Name', 'Unnamed') if hasattr(rel.RelatingBuildingElement, 'Name') else 'Unknown'
            void_map[opening_id] = {'wall_id': wall_id, 'wall_name': wall_name}
    
    # Find fill relationships (windows/doors in openings)
    fill_relationships = model.by_type('IfcRelFillsElement')
    fill_map = {}  # opening_id -> filler_id
    for rel in fill_relationships:
        if hasattr(rel, 'RelatingOpeningElement') and hasattr(rel, 'RelatedBuildingElement'):
            opening_id = rel.RelatingOpeningElement.GlobalId if hasattr(rel.RelatingOpeningElement, 'GlobalId') else str(rel.RelatingOpeningElement)
            filler_id = rel.RelatedBuildingElement.GlobalId if hasattr(rel.RelatedBuildingElement, 'GlobalId') else str(rel.RelatedBuildingElement)
            filler_name = getattr(rel.RelatedBuildingElement, 'Name', 'Unnamed') if hasattr(rel.RelatedBuildingElement, 'Name') else 'Unknown'
            filler_type = rel.RelatedBuildingElement.__class__.__name__ if hasattr(rel.RelatedBuildingElement, '__class__') else 'Unknown'
            fill_map[opening_id] = {'filler_id': filler_id, 'filler_name': filler_name, 'filler_type': filler_type}
    
    target_found = False
    
    for i, opening in enumerate(opening_elements, 1):
        name = getattr(opening, 'Name', 'Unnamed')
        global_id = getattr(opening, 'GlobalId', 'No-GlobalId')
        
        # Skip if looking for specific opening and this isn't it
        if target_opening_name and name != target_opening_name:
            continue
            
        target_found = True
        
        print(f"\n🏗️  {i}. {name}")
        print(f"   GlobalId: {global_id}")
        print(f"   Type: {opening.__class__.__name__}")
        
        # Get geometry information
        try:
            # Get representation directly from the opening element
            if hasattr(opening, 'Representation') and opening.Representation:
                if hasattr(opening.Representation, 'Representations'):
                    representations = opening.Representation.Representations
                    print(f"   Shape representations: {len(representations)}")
                    for j, rep in enumerate(representations):
                        rep_id = getattr(rep, 'RepresentationIdentifier', 'Unknown')
                        rep_type = getattr(rep, 'RepresentationType', 'Unknown')
                        item_count = len(getattr(rep, 'Items', []))
                        print(f"     {j+1}. {rep_id} ({rep_type}, {item_count} items)")
                else:
                    print("   Shape representations: No representations found")
            else:
                print("   Shape representations: No representation attribute")
        except Exception as e:
            print(f"   Geometry error: {e}")
        
        # Show void relationship (which wall contains this opening)
        if global_id in void_map:
            wall_info = void_map[global_id]
            print(f"   🔗 Creates void in: {wall_info['wall_name']} ({wall_info['wall_id']})")
        else:
            print("   ❌ No void relationship found")
        
        # Show fill relationship (what fills this opening)
        if global_id in fill_map:
            filler_info = fill_map[global_id]
            print(f"   🔗 Filled by: {filler_info['filler_name']} ({filler_info['filler_type']})")
        else:
            print("   ❌ No fill relationship found")
    
    if target_opening_name and not target_found:
        print(f"\n❌ Target opening '{target_opening_name}' not found")
        print("Available openings:")
        for opening in opening_elements:
            name = getattr(opening, 'Name', 'Unnamed')
            print(f"  - {name}")
    
    # Summary
    print(f"\n📊 SUMMARY")
    print("-" * 50)
    print(f"Total IfcOpeningElement entities: {len(opening_elements)}")
    print(f"Void relationships found: {len(void_map)}")
    print(f"Fill relationships found: {len(fill_map)}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python find_opening_elements.py <ifc_file.ifc> [opening_name]")
        print("\nExamples:")
        print("  python find_opening_elements.py ../../ifc_files/OrangeHouse.ifc")
        print("  python find_opening_elements.py ../../out-temp/step4_final_ifc/OrangeHouse_roundtrip.ifc 'OG-Fenster-1'")
        print("\nDescription:")
        print("  Analyzes IfcOpeningElement entities and their void/fill relationships")
        return
    
    ifc_file = sys.argv[1]
    target_opening_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    find_opening_elements(ifc_file, target_opening_name)

if __name__ == "__main__":
    main()