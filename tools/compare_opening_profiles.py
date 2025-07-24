#!/usr/bin/env python3
"""
Compare Opening Profiles Tool

Compares the detailed profile geometry between two IFC files for a specific opening element.
Extracts exact polyline points to determine circular vs rectangular differences.
"""

import sys
import math
from pathlib import Path

try:
    import ifcopenshell
    IFCOPENSHELL_AVAILABLE = True
except ImportError:
    IFCOPENSHELL_AVAILABLE = False

def extract_opening_profile_points(ifc_file: str, global_id: str):
    """Extract detailed profile points from opening element"""
    
    if not IFCOPENSHELL_AVAILABLE:
        print("❌ Error: ifcopenshell not available")
        return None
    
    try:
        model = ifcopenshell.open(ifc_file)
        element = model.by_guid(global_id)
    except Exception as e:
        print(f"❌ Error loading element: {e}")
        return None
    
    profiles = []
    
    if hasattr(element, 'Representation') and element.Representation:
        representations = element.Representation.Representations
        
        for rep in representations:
            if hasattr(rep, 'RepresentationIdentifier') and rep.RepresentationIdentifier == 'Body':
                if hasattr(rep, 'Items'):
                    for i, item in enumerate(rep.Items):
                        if item.is_a() == 'IfcExtrudedAreaSolid':
                            print(f"  Extrusion {i+1}:")
                            print(f"    Depth: {getattr(item, 'Depth', 'Unknown')}")
                            
                            # Extract profile
                            if hasattr(item, 'SweptArea'):
                                profile = item.SweptArea
                                profile_info = {
                                    'extrusion_index': i + 1,
                                    'profile_type': profile.is_a(),
                                    'depth': getattr(item, 'Depth', 0.0),
                                    'points': []
                                }
                                
                                print(f"    Profile: {profile.is_a()}")
                                
                                # Try OuterBoundary first, then OuterCurve
                                boundary = None
                                if hasattr(profile, 'OuterBoundary'):
                                    boundary = profile.OuterBoundary
                                elif hasattr(profile, 'OuterCurve'):
                                    boundary = profile.OuterCurve
                                
                                if boundary:
                                    boundary_type = boundary.is_a()
                                    print(f"    Boundary: {boundary_type}")
                                    
                                    if boundary_type == 'IfcPolyline' and hasattr(boundary, 'Points'):
                                        point_count = len(boundary.Points)
                                        print(f"    Point count: {point_count}")
                                        
                                        # Extract all points with high precision
                                        for j, point in enumerate(boundary.Points):
                                            coords = point.Coordinates
                                            point_data = [
                                                coords[0], 
                                                coords[1], 
                                                coords[2] if len(coords) > 2 else 0.0
                                            ]
                                            profile_info['points'].append(point_data)
                                            print(f"      Point {j+1:2d}: [{point_data[0]:10.6f}, {point_data[1]:10.6f}, {point_data[2]:6.6f}]")
                                    
                                    elif boundary_type == 'IfcIndexedPolyCurve':
                                        print(f"    IfcIndexedPolyCurve detected")
                                        
                                        # Extract points from Points attribute of the indexed poly curve
                                        if hasattr(boundary, 'Points') and hasattr(boundary.Points, 'CoordList'):
                                            coord_list = boundary.Points.CoordList
                                            point_count = len(coord_list)
                                            print(f"    Point count: {point_count}")
                                            
                                            for j, coords in enumerate(coord_list):
                                                point_data = [
                                                    coords[0],
                                                    coords[1], 
                                                    coords[2] if len(coords) > 2 else 0.0
                                                ]
                                                profile_info['points'].append(point_data)
                                                print(f"      Point {j+1:2d}: [{point_data[0]:10.6f}, {point_data[1]:10.6f}, {point_data[2]:6.6f}]")
                                        else:
                                            print(f"    ⚠️  Could not extract points from IfcIndexedPolyCurve")
                                            if hasattr(boundary, 'Points'):
                                                print(f"    Points type: {boundary.Points.is_a() if hasattr(boundary.Points, 'is_a') else type(boundary.Points)}")
                                                print(f"    Points attributes: {[attr for attr in dir(boundary.Points) if not attr.startswith('_')]}")
                                        
                                        # Also check segments for additional info
                                        if hasattr(boundary, 'Segments'):
                                            segments = boundary.Segments
                                            print(f"    Segments: {len(segments)}")
                                            for k, segment in enumerate(segments):
                                                segment_type = segment.is_a() if hasattr(segment, 'is_a') else type(segment)
                                                print(f"      Segment {k+1}: {segment_type}")
                                                if hasattr(segment, 'Radius'):
                                                    print(f"        Radius: {segment.Radius}")
                                                    # This is likely a circular arc!
                                                    profile_info['circle_radius'] = segment.Radius
                                    else:
                                        print(f"    ⚠️  Boundary type {boundary_type} not supported or no Points attribute")
                                        
                                        # Try to handle other boundary types
                                        if hasattr(boundary, 'Segments'):
                                            print(f"    Found Segments: {len(boundary.Segments)}")
                                        if hasattr(boundary, 'Curves'):
                                            print(f"    Found Curves: {len(boundary.Curves)}")
                                else:
                                    print(f"    ❌ No boundary found (OuterBoundary or OuterCurve)")
                                    
                                    # Debug: print all available attributes
                                    print(f"    Available attributes: {[attr for attr in dir(profile) if not attr.startswith('_') and not attr.startswith('attribute') and not attr.startswith('method') and not attr.startswith('get_info')]}")
                                
                                profiles.append(profile_info)
    
    return profiles

def analyze_profile_geometry(points):
    """Analyze if points form a circle and extract parameters"""
    if len(points) < 4:
        return None
    
    # Use 2D points for circle analysis
    points_2d = [(p[0], p[1]) for p in points]
    
    # Calculate center
    center_x = sum(p[0] for p in points_2d) / len(points_2d)
    center_y = sum(p[1] for p in points_2d) / len(points_2d)
    
    # Calculate radii
    radii = []
    for p in points_2d:
        radius = math.sqrt((p[0] - center_x)**2 + (p[1] - center_y)**2)
        radii.append(radius)
    
    avg_radius = sum(radii) / len(radii)
    max_deviation = max(abs(r - avg_radius) for r in radii)
    deviation_percent = (max_deviation / avg_radius * 100) if avg_radius > 0 else 100
    
    # Check if it's circular (within 5% tolerance)
    is_circular = deviation_percent < 5.0
    
    # Detect if it's rectangular (4 corners with right angles)
    is_rectangular = False
    if len(points_2d) == 5:  # Rectangle should have 5 points (start = end)
        # Check for right angles
        angles = []
        for i in range(len(points_2d) - 1):
            p1 = points_2d[i]
            p2 = points_2d[(i + 1) % (len(points_2d) - 1)]
            p3 = points_2d[(i + 2) % (len(points_2d) - 1)]
            
            # Calculate vectors
            v1 = (p1[0] - p2[0], p1[1] - p2[1])
            v2 = (p3[0] - p2[0], p3[1] - p2[1])
            
            # Calculate angle
            dot_product = v1[0] * v2[0] + v1[1] * v2[1]
            magnitude1 = math.sqrt(v1[0]**2 + v1[1]**2)
            magnitude2 = math.sqrt(v2[0]**2 + v2[1]**2)
            
            if magnitude1 > 0 and magnitude2 > 0:
                cos_angle = dot_product / (magnitude1 * magnitude2)
                cos_angle = max(-1, min(1, cos_angle))  # Clamp to valid range
                angle = math.degrees(math.acos(cos_angle))
                angles.append(angle)
        
        # Check if angles are close to 90 degrees
        right_angle_count = sum(1 for angle in angles if abs(angle - 90) < 10)
        is_rectangular = right_angle_count >= 3
    
    return {
        'is_circular': is_circular,
        'is_rectangular': is_rectangular,
        'center': [center_x, center_y],
        'avg_radius': avg_radius,
        'max_deviation': max_deviation,
        'deviation_percent': deviation_percent,
        'point_count': len(points_2d),
        'shape_classification': 'circular' if is_circular else ('rectangular' if is_rectangular else 'complex')
    }

def compare_opening_profiles(file1: str, file2: str, global_id: str):
    """Compare opening profiles between two IFC files"""
    
    print(f"🔍 COMPARING OPENING PROFILES")
    print(f"File 1: {Path(file1).name}")
    print(f"File 2: {Path(file2).name}")
    print(f"Opening GlobalId: {global_id}")
    print("=" * 80)
    
    print(f"\n📁 ANALYZING FILE 1: {Path(file1).name}")
    print("-" * 60)
    profiles1 = extract_opening_profile_points(file1, global_id)
    
    print(f"\n📁 ANALYZING FILE 2: {Path(file2).name}")  
    print("-" * 60)
    profiles2 = extract_opening_profile_points(file2, global_id)
    
    if not profiles1 or not profiles2:
        print("❌ Could not extract profiles from both files")
        return
    
    print(f"\n📊 PROFILE COMPARISON")
    print("=" * 80)
    
    for i, (p1, p2) in enumerate(zip(profiles1, profiles2)):
        print(f"\n🔍 Extrusion {i+1} Comparison:")
        print(f"  Depth: {p1['depth']} vs {p2['depth']} {'✅' if abs(p1['depth'] - p2['depth']) < 0.001 else '❌'}")
        print(f"  Points: {len(p1['points'])} vs {len(p2['points'])} {'✅' if len(p1['points']) == len(p2['points']) else '❌'}")
        
        # Analyze geometry of each profile
        analysis1 = analyze_profile_geometry(p1['points']) if p1['points'] else None
        analysis2 = analyze_profile_geometry(p2['points']) if p2['points'] else None
        
        if analysis1 and analysis2:
            print(f"\n  📐 GEOMETRY ANALYSIS:")
            print(f"    File 1 Shape: {analysis1['shape_classification'].upper()}")
            print(f"    File 2 Shape: {analysis2['shape_classification'].upper()}")
            print(f"    Shape Match: {'✅' if analysis1['shape_classification'] == analysis2['shape_classification'] else '❌ DIFFERENT'}")
        else:
            print(f"\n  ❌ Cannot analyze geometry - no points extracted")
        
        if analysis1 and analysis2:
            if analysis1['is_circular'] or analysis2['is_circular']:
                print(f"\n  🎯 CIRCULAR ANALYSIS:")
                print(f"    File 1 - Circular: {'YES' if analysis1['is_circular'] else 'NO'}, Radius: {analysis1['avg_radius']:.4f}, Deviation: {analysis1['deviation_percent']:.2f}%")
                print(f"    File 2 - Circular: {'YES' if analysis2['is_circular'] else 'NO'}, Radius: {analysis2['avg_radius']:.4f}, Deviation: {analysis2['deviation_percent']:.2f}%")
            
            if analysis1['is_rectangular'] or analysis2['is_rectangular']:
                print(f"\n  📦 RECTANGULAR ANALYSIS:")
                print(f"    File 1 - Rectangular: {'YES' if analysis1['is_rectangular'] else 'NO'}")
                print(f"    File 2 - Rectangular: {'YES' if analysis2['is_rectangular'] else 'NO'}")
        
        # Point-by-point comparison
        if len(p1['points']) == len(p2['points']) and len(p1['points']) <= 10:
            print(f"\n  📍 POINT-BY-POINT COMPARISON:")
            max_diff = 0
            for j, (pt1, pt2) in enumerate(zip(p1['points'], p2['points'])):
                diff_x = abs(pt1[0] - pt2[0])
                diff_y = abs(pt1[1] - pt2[1])
                diff_z = abs(pt1[2] - pt2[2])
                max_pt_diff = max(diff_x, diff_y, diff_z)
                max_diff = max(max_diff, max_pt_diff)
                
                status = "✅" if max_pt_diff < 0.001 else "❌"
                print(f"    Point {j+1}: {status} Max diff: {max_pt_diff:.6f}")
            
            print(f"    Overall max difference: {max_diff:.6f}")
        
        # Generate Step 2 storage recommendation
        if analysis1 and analysis2 and analysis1['shape_classification'] != analysis2['shape_classification']:
            print(f"\n🎯 STEP 2 STORAGE RECOMMENDATION:")
            print(f"  # Current issue: {analysis1['shape_classification']} → {analysis2['shape_classification']}")
            
            if analysis1['is_circular']:
                print(f"  geometryType: 'circular_opening'")
                print(f"  openingShape: 'circular'")
                print(f"  dimensions:")
                print(f"    radius: {analysis1['avg_radius']:.6f}")
                print(f"    center_offset: [{analysis1['center'][0]:.6f}, {analysis1['center'][1]:.6f}]")
                print(f"    depth: {p1['depth']}")
                print(f"  tessellation:")
                print(f"    point_count: {analysis1['point_count']}")
                print(f"    quality: '{'high' if analysis1['point_count'] >= 16 else 'medium'}'")
                print(f"  originalProfile: 'preserve_circular_tessellation'")
                print(f"  recreation_strategy: 'generate_circular_polyline'")

def main():
    if len(sys.argv) != 4:
        print("Usage: python compare_opening_profiles.py <ifc_file1> <ifc_file2> <global_id>")
        print("\nExample:")
        print("  python compare_opening_profiles.py file1.ifc file2.ifc '80ac816-0d23-1e5d-f88a-bb0645892c3'")
        return
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]  
    global_id = sys.argv[3]
    
    compare_opening_profiles(file1, file2, global_id)

if __name__ == "__main__":
    main()