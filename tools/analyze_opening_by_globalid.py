#!/usr/bin/env python3
"""
Analyze Opening By GlobalId Tool

Analyzes opening elements by GlobalId to extract geometric parameters
for Step 2 storage requirements.
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

def analyze_opening_geometry(ifc_file: str, global_id: str):
    """Analyze opening geometry by GlobalId"""
    
    print(f"🔍 ANALYZING OPENING GEOMETRY BY GLOBALID")
    print(f"File: {ifc_file}")
    print(f"GlobalId: {global_id}")
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
    
    # Find element by GlobalId
    try:
        element = model.by_guid(global_id)
        print(f"✅ Found element: {element.is_a()} - {getattr(element, 'Name', 'Unnamed')}")
    except Exception as e:
        print(f"❌ Element with GlobalId '{global_id}' not found: {e}")
        return
    
    # Analyze element type and properties
    element_type = element.is_a()
    element_name = getattr(element, 'Name', 'Unnamed')
    
    print(f"\n📊 ELEMENT ANALYSIS")
    print("-" * 50)
    print(f"Type: {element_type}")
    print(f"Name: {element_name}")
    print(f"ID: {element.id()}")
    
    # Check if it has representation
    if hasattr(element, 'Representation') and element.Representation:
        print(f"✅ Has representation")
        
        # Get shape representations
        representations = element.Representation.Representations
        print(f"📐 Shape representations: {len(representations)}")
        
        for i, rep in enumerate(representations):
            rep_id = getattr(rep, 'RepresentationIdentifier', 'Unknown')
            rep_type = getattr(rep, 'RepresentationType', 'Unknown')
            item_count = len(rep.Items) if hasattr(rep, 'Items') else 0
            
            print(f"  {i+1}. {rep_id} ({rep_type}, {item_count} items)")
            
            # Analyze items in detail
            if hasattr(rep, 'Items'):
                for j, item in enumerate(rep.Items):
                    item_type = item.is_a()
                    print(f"    Item {j+1}: {item_type}")
                    
                    # Detailed analysis based on geometry type
                    if item_type == 'IfcExtrudedAreaSolid':
                        depth = getattr(item, 'Depth', 'Unknown')
                        print(f"      Extrusion depth: {depth}")
                        
                        # Analyze profile
                        if hasattr(item, 'SweptArea'):
                            profile = item.SweptArea
                            profile_type = profile.is_a()
                            print(f"      Profile type: {profile_type}")
                            
                            if profile_type == 'IfcArbitraryClosedProfileDef':
                                if hasattr(profile, 'OuterBoundary'):
                                    boundary = profile.OuterBoundary
                                    boundary_type = boundary.is_a()
                                    print(f"      Boundary type: {boundary_type}")
                                    
                                    if boundary_type == 'IfcPolyline' and hasattr(boundary, 'Points'):
                                        point_count = len(boundary.Points)
                                        print(f"      Polyline points: {point_count}")
                                        
                                        # Extract actual coordinates
                                        points = []
                                        for point in boundary.Points:
                                            coords = point.Coordinates
                                            points.append([coords[0], coords[1], coords[2] if len(coords) > 2 else 0.0])
                                        
                                        print(f"      📍 First few points:")
                                        for k, point in enumerate(points[:5]):
                                            print(f"        Point {k+1}: [{point[0]:.4f}, {point[1]:.4f}, {point[2]:.4f}]")
                                        if len(points) > 5:
                                            print(f"        ... and {len(points)-5} more points")
                                        
                                        # Analyze for circular pattern
                                        if point_count >= 8:  # Minimum for circle detection
                                            center_x = sum(p[0] for p in points) / len(points)
                                            center_y = sum(p[1] for p in points) / len(points)
                                            
                                            # Calculate radii
                                            radii = []
                                            for point in points:
                                                radius = ((point[0] - center_x)**2 + (point[1] - center_y)**2)**0.5
                                                radii.append(radius)
                                            
                                            avg_radius = sum(radii) / len(radii)
                                            max_deviation = max(abs(r - avg_radius) for r in radii)
                                            deviation_percent = (max_deviation / avg_radius * 100) if avg_radius > 0 else 100
                                            
                                            is_circular = deviation_percent < 5.0  # 5% tolerance
                                            
                                            print(f"      🎯 CIRCULAR ANALYSIS:")
                                            print(f"        Center: [{center_x:.4f}, {center_y:.4f}]")
                                            print(f"        Avg radius: {avg_radius:.4f}")
                                            print(f"        Max deviation: {max_deviation:.4f} ({deviation_percent:.2f}%)")
                                            print(f"        Is circular: {'✅ YES' if is_circular else '❌ NO'}")
                                            
                                            if is_circular:
                                                print(f"\n🎯 RECOMMENDED STEP 2 STORAGE:")
                                                print(f"  geometryType: 'circular_opening'")
                                                print(f"  openingShape: 'circular'")
                                                print(f"  dimensions:")
                                                print(f"    radius: {avg_radius:.4f}")
                                                print(f"    depth: {depth}")
                                                print(f"    center_offset: [{center_x:.4f}, {center_y:.4f}]")
                                                print(f"  tessellation:")
                                                print(f"    point_count: {point_count}")
                                                print(f"    quality: '{'very_high' if point_count >= 32 else 'high' if point_count >= 16 else 'medium'}'")
                                                print(f"  originalGeometryType: 'IfcExtrudedAreaSolid'")
                                                print(f"  profileType: '{profile_type}'")
                            
                            elif profile_type == 'IfcCircleProfileDef':
                                if hasattr(profile, 'Radius'):
                                    radius = profile.Radius
                                    print(f"      Circle radius: {radius}")
                                    
                                    print(f"\n🎯 RECOMMENDED STEP 2 STORAGE:")
                                    print(f"  geometryType: 'circular_opening_simple'")
                                    print(f"  openingShape: 'circular'")
                                    print(f"  dimensions:")
                                    print(f"    radius: {radius}")
                                    print(f"    depth: {depth}")
                                    print(f"  tessellation:")
                                    print(f"    quality: 'parametric'  # Use IfcCircleProfileDef")
                                    print(f"  originalGeometryType: 'IfcExtrudedAreaSolid'")
                                    print(f"  profileType: 'IfcCircleProfileDef'")
                    
                    elif item_type == 'IfcFacetedBrep':
                        print(f"      🔷 IfcFacetedBrep detected")
                        
                        # Count faces and analyze tessellation
                        if hasattr(item, 'Outer') and item.Outer:
                            shell = item.Outer
                            if hasattr(shell, 'CfsFaces'):
                                face_count = len(shell.CfsFaces)
                                print(f"      Face count: {face_count}")
                                
                                if face_count >= 100:  # High tessellation
                                    print(f"      🎯 High-detail tessellated geometry detected")
                                    print(f"\n🎯 RECOMMENDED STEP 2 STORAGE:")
                                    print(f"  geometryType: 'circular_opening_tessellated'")
                                    print(f"  openingShape: 'circular'")
                                    print(f"  tessellation:")
                                    print(f"    face_count: {face_count}")
                                    print(f"    quality: 'very_high'")
                                    print(f"  originalGeometryType: 'IfcFacetedBrep'")
                                    print(f"  mesh_complexity: 'high_detail_circular'")
                                    print(f"  recreation_strategy: 'preserve_tessellation'")
    
    else:
        print(f"❌ No representation found")
    
    # Also try to get actual geometry using ifcopenshell.geom
    try:
        print(f"\n🔧 IFCOPENSHELL GEOMETRY ANALYSIS")
        print("-" * 50)
        
        settings = ifcopenshell.geom.settings()
        shape = ifcopenshell.geom.create_shape(settings, element)
        
        if shape:
            geometry = shape.geometry
            faces_count = len(geometry.faces) // 3  # faces are stored as triplets
            vertices_count = len(geometry.verts) // 3  # vertices are stored as triplets
            
            print(f"Actual face count: {faces_count}")
            print(f"Actual vertex count: {vertices_count}")
            
            # Determine complexity
            if faces_count >= 100:
                complexity = "very_high"
            elif faces_count >= 50:
                complexity = "high"  
            elif faces_count >= 20:
                complexity = "medium"
            else:
                complexity = "low"
                
            print(f"Geometry complexity: {complexity}")
            print(f"Tessellation quality: {'Circular (high detail)' if faces_count >= 100 else 'Standard'}")
            
    except Exception as e:
        print(f"⚠️  Could not analyze geometry with ifcopenshell.geom: {e}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python analyze_opening_by_globalid.py <ifc_file> <global_id>")
        print("\nExamples:")
        print("  python analyze_opening_by_globalid.py file.ifc '0e2iWM3ICUNVYAkmP5YImx'")
        print("  python analyze_opening_by_globalid.py file.ifc '80ac816-0d23-1e5d-f88a-bb0645892c3'")
        return
    
    ifc_file = sys.argv[1]
    global_id = sys.argv[2]
    
    analyze_opening_geometry(ifc_file, global_id)

if __name__ == "__main__":
    main()