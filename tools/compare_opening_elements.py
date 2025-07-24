#!/usr/bin/env python3
"""
Compare Opening Elements Tool

Compares IfcOpeningElement entities between two IFC files, focusing on
geometry, placement, and relationship differences.

Usage:
    python compare_opening_elements.py <ifc_file1.ifc> <ifc_file2.ifc> <opening_name>
    
Examples:
    python compare_opening_elements.py file1.ifc file2.ifc "OG-Fenster-1"
    
Description:
    Deep comparison of IfcOpeningElement geometry, shape representations, 
    placement, and void/fill relationships between two IFC files
"""

import sys
from pathlib import Path

try:
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.geom
    IFCOPENSHELL_AVAILABLE = True
except ImportError:
    IFCOPENSHELL_AVAILABLE = False

def analyze_opening_geometry(opening_element):
    """Analyze opening element geometry in detail"""
    geometry_info = {
        'representations': [],
        'placement': None,
        'geometry_summary': {}
    }
    
    # Get shape representations
    if hasattr(opening_element, 'Representation') and opening_element.Representation:
        if hasattr(opening_element.Representation, 'Representations'):
            representations = opening_element.Representation.Representations
            for rep in representations:
                rep_info = {
                    'identifier': getattr(rep, 'RepresentationIdentifier', 'Unknown'),
                    'type': getattr(rep, 'RepresentationType', 'Unknown'),
                    'items': []
                }
                
                # Analyze representation items
                if hasattr(rep, 'Items'):
                    for item in rep.Items:
                        item_info = {
                            'type': item.__class__.__name__,
                            'details': {}
                        }
                        
                        # Analyze specific item types
                        if item.__class__.__name__ == 'IfcExtrudedAreaSolid':
                            if hasattr(item, 'Depth'):
                                item_info['details']['depth'] = item.Depth
                            if hasattr(item, 'SweptArea'):
                                item_info['details']['swept_area_type'] = item.SweptArea.__class__.__name__
                                if hasattr(item.SweptArea, 'OuterBoundary'):
                                    boundary = item.SweptArea.OuterBoundary
                                    if hasattr(boundary, 'Points'):
                                        item_info['details']['boundary_points'] = len(boundary.Points)
                        
                        elif item.__class__.__name__ == 'IfcBoundingBox':
                            if hasattr(item, 'XDim'):
                                item_info['details']['dimensions'] = [item.XDim, item.YDim, item.ZDim]
                        
                        rep_info['items'].append(item_info)
                
                geometry_info['representations'].append(rep_info)
    
    # Get placement information
    if hasattr(opening_element, 'ObjectPlacement') and opening_element.ObjectPlacement:
        placement = opening_element.ObjectPlacement
        placement_info = {
            'type': placement.__class__.__name__,
            'details': {}
        }
        
        if hasattr(placement, 'RelativePlacement'):
            rel_placement = placement.RelativePlacement
            if hasattr(rel_placement, 'Location') and hasattr(rel_placement.Location, 'Coordinates'):
                placement_info['details']['location'] = list(rel_placement.Location.Coordinates)
            if hasattr(rel_placement, 'Axis') and rel_placement.Axis and hasattr(rel_placement.Axis, 'DirectionRatios'):
                placement_info['details']['axis'] = list(rel_placement.Axis.DirectionRatios)
            if hasattr(rel_placement, 'RefDirection') and rel_placement.RefDirection and hasattr(rel_placement.RefDirection, 'DirectionRatios'):
                placement_info['details']['ref_direction'] = list(rel_placement.RefDirection.DirectionRatios)
        
        geometry_info['placement'] = placement_info
    
    return geometry_info

def compare_opening_elements(ifc_file1: str, ifc_file2: str, target_opening_name: str):
    """Compare IfcOpeningElement between two IFC files"""
    
    print(f"🔍 COMPARING OPENING ELEMENTS")
    print(f"File 1: {Path(ifc_file1).name}")
    print(f"File 2: {Path(ifc_file2).name}")
    print(f"Target: {target_opening_name}")
    print("=" * 80)
    
    if not IFCOPENSHELL_AVAILABLE:
        print("❌ Error: ifcopenshell not available")
        return
    
    try:
        model1 = ifcopenshell.open(ifc_file1)
        model2 = ifcopenshell.open(ifc_file2)
        print("✅ Both IFC files loaded successfully")
    except Exception as e:
        print(f"❌ Error loading IFC files: {e}")
        return
    
    # Find target opening in both files
    opening1 = None
    opening2 = None
    
    for opening in model1.by_type('IfcOpeningElement'):
        name = getattr(opening, 'Name', 'Unnamed')
        if name == target_opening_name:
            opening1 = opening
            break
    
    for opening in model2.by_type('IfcOpeningElement'):
        name = getattr(opening, 'Name', 'Unnamed')
        if name == target_opening_name:
            opening2 = opening
            break
    
    if not opening1:
        print(f"❌ Opening '{target_opening_name}' not found in file 1")
        return
    
    if not opening2:
        print(f"❌ Opening '{target_opening_name}' not found in file 2")
        return
    
    print(f"✅ Found '{target_opening_name}' in both files")
    
    # Compare basic properties
    print(f"\n📋 BASIC PROPERTIES COMPARISON")
    print("-" * 50)
    
    global_id1 = getattr(opening1, 'GlobalId', 'No-GlobalId')
    global_id2 = getattr(opening2, 'GlobalId', 'No-GlobalId')
    
    print(f"GlobalId:")
    print(f"  File 1: {global_id1}")
    print(f"  File 2: {global_id2}")
    print(f"  Match: {'✅' if global_id1 == global_id2 else '❌'}")
    
    # Analyze geometry in detail
    print(f"\n🔍 GEOMETRY ANALYSIS")
    print("-" * 50)
    
    geom1 = analyze_opening_geometry(opening1)
    geom2 = analyze_opening_geometry(opening2)
    
    # Compare representations
    print(f"Shape Representations:")
    print(f"  File 1: {len(geom1['representations'])} representations")
    print(f"  File 2: {len(geom2['representations'])} representations")
    
    for i, (rep1, rep2) in enumerate(zip(geom1['representations'], geom2['representations'])):
        print(f"\n  Representation {i+1}:")
        print(f"    Identifier: {rep1['identifier']} vs {rep2['identifier']} {'✅' if rep1['identifier'] == rep2['identifier'] else '❌'}")
        print(f"    Type: {rep1['type']} vs {rep2['type']} {'✅' if rep1['type'] == rep2['type'] else '❌'}")
        print(f"    Items: {len(rep1['items'])} vs {len(rep2['items'])} {'✅' if len(rep1['items']) == len(rep2['items']) else '❌'}")
        
        # Compare items in detail
        for j, (item1, item2) in enumerate(zip(rep1['items'], rep2['items'])):
            print(f"      Item {j+1}: {item1['type']} vs {item2['type']} {'✅' if item1['type'] == item2['type'] else '❌'}")
            if item1['details'] != item2['details']:
                print(f"        Details differ:")
                print(f"          File 1: {item1['details']}")
                print(f"          File 2: {item2['details']}")
            else:
                print(f"        Details: ✅ Identical")
    
    # Compare placement
    print(f"\n📍 PLACEMENT COMPARISON")
    print("-" * 50)
    
    if geom1['placement'] and geom2['placement']:
        place1 = geom1['placement']
        place2 = geom2['placement']
        print(f"Placement Type: {place1['type']} vs {place2['type']} {'✅' if place1['type'] == place2['type'] else '❌'}")
        
        if 'location' in place1['details'] and 'location' in place2['details']:
            loc1 = place1['details']['location']
            loc2 = place2['details']['location']
            print(f"Location: {loc1} vs {loc2}")
            location_match = all(abs(a - b) < 0.001 for a, b in zip(loc1, loc2))
            print(f"Location Match: {'✅' if location_match else '❌'}")
        
        if 'axis' in place1['details'] and 'axis' in place2['details']:
            axis1 = place1['details']['axis']
            axis2 = place2['details']['axis']
            print(f"Axis: {axis1} vs {axis2}")
            axis_match = all(abs(a - b) < 0.001 for a, b in zip(axis1, axis2))
            print(f"Axis Match: {'✅' if axis_match else '❌'}")
    else:
        print("Placement information missing in one or both files")
    
    # Check void relationships
    print(f"\n🔗 VOID RELATIONSHIP ANALYSIS")
    print("-" * 50)
    
    void_rels1 = [rel for rel in model1.by_type('IfcRelVoidsElement') 
                  if hasattr(rel, 'RelatedOpeningElement') and rel.RelatedOpeningElement == opening1]
    void_rels2 = [rel for rel in model2.by_type('IfcRelVoidsElement') 
                  if hasattr(rel, 'RelatedOpeningElement') and rel.RelatedOpeningElement == opening2]
    
    print(f"Void relationships found: {len(void_rels1)} vs {len(void_rels2)} {'✅' if len(void_rels1) == len(void_rels2) else '❌'}")
    
    if void_rels1 and void_rels2:
        wall1_name = getattr(void_rels1[0].RelatingBuildingElement, 'Name', 'Unnamed')
        wall2_name = getattr(void_rels2[0].RelatingBuildingElement, 'Name', 'Unnamed')
        print(f"Creates void in: {wall1_name} vs {wall2_name} {'✅' if wall1_name == wall2_name else '❌'}")
    
    # Check fill relationships
    print(f"\n🔗 FILL RELATIONSHIP ANALYSIS")
    print("-" * 50)
    
    fill_rels1 = [rel for rel in model1.by_type('IfcRelFillsElement') 
                  if hasattr(rel, 'RelatingOpeningElement') and rel.RelatingOpeningElement == opening1]
    fill_rels2 = [rel for rel in model2.by_type('IfcRelFillsElement') 
                  if hasattr(rel, 'RelatingOpeningElement') and rel.RelatingOpeningElement == opening2]
    
    print(f"Fill relationships found: {len(fill_rels1)} vs {len(fill_rels2)} {'✅' if len(fill_rels1) == len(fill_rels2) else '❌'}")
    
    if fill_rels1 and fill_rels2:
        filler1_name = getattr(fill_rels1[0].RelatedBuildingElement, 'Name', 'Unnamed')
        filler2_name = getattr(fill_rels2[0].RelatedBuildingElement, 'Name', 'Unnamed')
        filler1_type = fill_rels1[0].RelatedBuildingElement.__class__.__name__
        filler2_type = fill_rels2[0].RelatedBuildingElement.__class__.__name__
        print(f"Filled by: {filler1_name} ({filler1_type}) vs {filler2_name} ({filler2_type})")
        print(f"Filler Match: {'✅' if filler1_name == filler2_name and filler1_type == filler2_type else '❌'}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python compare_opening_elements.py <ifc_file1.ifc> <ifc_file2.ifc> <opening_name>")
        print("\nExamples:")
        print("  python compare_opening_elements.py file1.ifc file2.ifc 'OG-Fenster-1'")
        print("\nDescription:")
        print("  Deep comparison of IfcOpeningElement geometry, placement, and relationships")
        return
    
    ifc_file1 = sys.argv[1]
    ifc_file2 = sys.argv[2]
    opening_name = sys.argv[3]
    
    compare_opening_elements(ifc_file1, ifc_file2, opening_name)

if __name__ == "__main__":
    main()