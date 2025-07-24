#!/usr/bin/env python3
"""
Detect Circular Openings From ifcJSON

Analyzes IfcOpeningElement profile geometry in ifcJSON files to detect circular openings
directly from the IfcArbitraryClosedProfileDef polyline coordinates.

Usage:
    python detect_circular_openings_from_ifcjson.py <ifcjson_file>
    
Examples:
    python detect_circular_openings_from_ifcjson.py /path/to/OrangeHouse.json
    
Description:
    Direct analysis of opening profile geometry without tessellation face counting.
    More accurate than analyzing IfcFacetedBrep since it uses original design coordinates.
"""

import sys
import json
import math
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

def load_ifcjson(file_path: str) -> Dict[str, Any]:
    """Load ifcJSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_entities_by_type(data: Dict[str, Any], entity_type: str) -> List[Dict[str, Any]]:
    """Find all entities of specific type"""
    entities = data.get('data', [])
    return [entity for entity in entities if entity.get('type') == entity_type]

def resolve_reference(data: Dict[str, Any], ref_obj: Any) -> Optional[Dict[str, Any]]:
    """Resolve reference to actual entity"""
    if isinstance(ref_obj, dict):
        if 'ref' in ref_obj:
            ref_id = ref_obj['ref']
        elif 'globalId' in ref_obj:
            # Already resolved
            return ref_obj
        else:
            return ref_obj
    else:
        ref_id = str(ref_obj)
    
    # Find entity by ref (could be globalId or internal reference)
    entities = data.get('data', [])
    for entity in entities:
        if entity.get('globalId') == ref_id:
            return entity
    return None

def extract_curve_points(curve_entity: Dict[str, Any], data: Dict[str, Any]) -> Tuple[List[List[float]], Dict[str, Any]]:
    """
    Extract coordinate points from IfcPolyline or IfcIndexedPolyCurve entity
    Returns: (points, curve_info) where curve_info contains additional metadata
    """
    points = []
    curve_info = {'type': curve_entity.get('type'), 'is_parametric': False, 'segments': []}
    curve_type = curve_entity.get('type')
    
    if curve_type == 'IfcPolyline':
        # Extract from IfcPolyline
        point_refs = curve_entity.get('points', [])
        for point_ref in point_refs:
            point_entity = resolve_reference(data, point_ref)
            if point_entity and point_entity.get('type') == 'IfcCartesianPoint':
                coords = point_entity.get('coordinates', [])
                if len(coords) >= 2:
                    points.append([coords[0], coords[1]])  # Use 2D coordinates
    
    elif curve_type == 'IfcIndexedPolyCurve':
        # Extract from IfcIndexedPolyCurve 
        points_ref = curve_entity.get('points')
        if points_ref:
            points_entity = resolve_reference(data, points_ref)
            if points_entity and points_entity.get('type') == 'IfcCartesianPointList2D':
                coord_list = points_entity.get('coordList', [])
                for coord_pair in coord_list:
                    if len(coord_pair) >= 2:
                        points.append([coord_pair[0], coord_pair[1]])
        
        # Check for parametric segments (IfcArcIndex)
        segments = curve_entity.get('segments', [])
        curve_info['segments'] = segments
        
        # Detect if this is a parametric circle (has IfcArcIndex segments)
        arc_segments = [s for s in segments if s.get('type') == 'IfcArcIndex']
        if len(arc_segments) >= 2:  # Circular curves typically have 2 arc segments
            curve_info['is_parametric'] = True
            curve_info['arc_segments'] = len(arc_segments)
    
    return points, curve_info

def analyze_circular_pattern(points: List[List[float]]) -> Optional[Dict[str, Any]]:
    """
    Analyze points to determine if they form a circular pattern
    Uses least squares circle fitting
    """
    if len(points) < 8:  # Need minimum points for circle fitting
        return None
    
    try:
        # Convert to numpy array
        points_array = np.array(points)
        x = points_array[:, 0]
        y = points_array[:, 1]
        
        # Least squares circle fitting
        # Fit circle equation: (x-a)² + (y-b)² = r²
        # Expand to: x² + y² - 2ax - 2by + (a² + b² - r²) = 0
        A = np.column_stack([2*x, 2*y, np.ones(len(x))])
        B = x**2 + y**2
        
        # Solve using least squares
        params, residuals, rank, s = np.linalg.lstsq(A, B, rcond=None)
        
        if len(params) != 3:
            return None
        
        center_x, center_y, c = params
        radius_squared = center_x**2 + center_y**2 - c
        
        if radius_squared <= 0:
            return None
        
        radius = np.sqrt(radius_squared)
        
        # Validate circle fit quality
        distances = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        avg_distance = np.mean(distances)
        distance_std = np.std(distances)
        
        # Check consistency (circular tolerance)
        circular_tolerance = 0.10  # 10% tolerance for ifcJSON analysis
        relative_deviation = distance_std / avg_distance if avg_distance > 0 else 1.0
        
        if relative_deviation > circular_tolerance:
            return None
        
        # Validate reasonable radius (10mm to 2000mm for building openings)
        if radius < 0.01 or radius > 2.0:  # Assuming meters
            return None
        
        return {
            'center': [float(center_x), float(center_y)],
            'radius': float(radius),
            'point_count': len(points),
            'fit_quality': float(relative_deviation),
            'avg_radius': float(avg_distance),
            'radius_std': float(distance_std)
        }
        
    except Exception as e:
        print(f"  ⚠️ Error in circular analysis: {e}")
        return None

def analyze_parametric_circle(points: List[List[float]], curve_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analyze parametric circular curve (IfcIndexedPolyCurve with IfcArcIndex segments)
    For 4-point circles: Right, Top, Left, Bottom
    """
    if not curve_info.get('is_parametric') or len(points) != 4:
        return None
    
    try:
        # For parametric circles with 4 points, calculate center and radius
        # Assume points are ordered: Right, Top, Left, Bottom
        points_array = np.array(points)
        
        # Method 1: Center should be equidistant from all 4 points
        # Calculate center as average of opposite points
        center_x = (points_array[0, 0] + points_array[2, 0]) / 2  # Right + Left
        center_y = (points_array[1, 1] + points_array[3, 1]) / 2  # Top + Bottom
        
        # Calculate radius from center to any point
        distances = []
        for point in points:
            dist = np.sqrt((point[0] - center_x)**2 + (point[1] - center_y)**2)
            distances.append(dist)
        
        # Check if all distances are approximately equal (circular)
        avg_radius = np.mean(distances)
        distance_std = np.std(distances)
        relative_deviation = distance_std / avg_radius if avg_radius > 0 else 1.0
        
        # More lenient tolerance for parametric circles (they should be exact)
        parametric_tolerance = 0.01  # 1% tolerance
        if relative_deviation > parametric_tolerance:
            print(f"     ❌ Parametric points not circular (std: {distance_std:.3f}, avg: {avg_radius:.3f})")
            return None
        
        # Validate reasonable radius (0.01 to 2000 units - could be mm or meters)
        if avg_radius < 0.01 or avg_radius > 2000.0:  # 0.01 to 2000 units
            print(f"     ❌ Unreasonable radius: {avg_radius:.3f} units")
            return None
        
        # Note potential unit scale
        unit_scale = "mm" if avg_radius > 10 else "m" if avg_radius > 0.1 else "units"
        print(f"     📏 Detected radius: {avg_radius:.3f} {unit_scale}")
        
        return {
            'center': [float(center_x), float(center_y)],
            'radius': float(avg_radius),
            'point_count': len(points),
            'fit_quality': float(relative_deviation),
            'avg_radius': float(avg_radius),
            'radius_std': float(distance_std),
            'detection_method': 'parametric'
        }
        
    except Exception as e:
        print(f"     ⚠️ Error in parametric circular analysis: {e}")
        return None

def analyze_opening_geometry(opening: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze IfcOpeningElement geometry to detect circular profile"""
    
    result = {
        'globalId': opening.get('globalId', 'unknown'),
        'name': opening.get('name', 'Unnamed'),
        'type': opening.get('type'),
        'shape_detected': 'unknown',
        'analysis_details': {},
        'circular_parameters': None
    }
    
    print(f"  🔍 Analyzing: {result['name']} ({result['globalId']})")
    
    # Get representation
    representation_ref = opening.get('representation')
    if not representation_ref:
        print(f"    ❌ No representation found")
        return result
    
    product_def_shape = resolve_reference(data, representation_ref)
    if not product_def_shape or product_def_shape.get('type') != 'IfcProductDefinitionShape':
        print(f"    ❌ No product definition shape found")
        return result
    
    representations = product_def_shape.get('representations', [])
    print(f"    📊 Found {len(representations)} representations")
    
    # Look for Body representation with SweptSolid
    for i, repr_ref in enumerate(representations):
        shape_repr = resolve_reference(data, repr_ref)
        if not shape_repr:
            continue
            
        repr_id = shape_repr.get('representationIdentifier', 'Unknown')
        repr_type = shape_repr.get('representationType', 'Unknown')
        
        print(f"    📐 Representation {i+1}: {repr_id} ({repr_type})")
        
        if repr_id == 'Body' and repr_type == 'SweptSolid':
            # Analyze items in this representation
            items = shape_repr.get('items', [])
            print(f"      🔧 {len(items)} geometry items")
            
            for j, item_ref in enumerate(items):
                item = resolve_reference(data, item_ref)
                if not item:
                    continue
                
                item_type = item.get('type')
                print(f"        Item {j+1}: {item_type}")
                
                if item_type == 'IfcExtrudedAreaSolid':
                    # Analyze swept area (profile)
                    swept_area_ref = item.get('sweptArea')
                    if swept_area_ref:
                        profile = resolve_reference(data, swept_area_ref)
                        if profile and profile.get('type') == 'IfcArbitraryClosedProfileDef':
                            print(f"          Profile: {profile.get('type')}")
                            
                            # Get outer boundary curve
                            outer_curve_ref = profile.get('outerCurve')
                            if outer_curve_ref:
                                curve = resolve_reference(data, outer_curve_ref)
                                if curve:
                                    curve_type = curve.get('type')
                                    print(f"          Boundary: {curve_type}")
                                    
                                    if curve_type in ['IfcPolyline', 'IfcIndexedPolyCurve']:
                                        # Extract points from curve
                                        points, curve_info = extract_curve_points(curve, data)
                                        print(f"          Points: {len(points)}")
                                        
                                        if curve_info.get('is_parametric'):
                                            print(f"          🎯 Parametric circle detected (IfcArcIndex segments: {curve_info.get('arc_segments', 0)})")
                                        
                                        if len(points) > 0:
                                            circle_analysis = None
                                            
                                            # Try parametric detection first for IfcIndexedPolyCurve with arc segments
                                            if curve_info.get('is_parametric'):
                                                circle_analysis = analyze_parametric_circle(points, curve_info)
                                            
                                            # Fallback to tessellated analysis for high point count curves
                                            if not circle_analysis and len(points) >= 8:
                                                circle_analysis = analyze_circular_pattern(points)
                                                if circle_analysis:
                                                    circle_analysis['detection_method'] = 'tessellated'
                                            
                                            if circle_analysis:
                                                result['shape_detected'] = 'circular'
                                                result['circular_parameters'] = circle_analysis
                                                result['analysis_details'] = {
                                                    'profile_type': 'IfcArbitraryClosedProfileDef',
                                                    'boundary_type': curve_type,
                                                    'point_count': len(points),
                                                    'extrusion_depth': item.get('depth', 'unknown'),
                                                    'is_parametric': curve_info.get('is_parametric', False),
                                                    'detection_method': circle_analysis.get('detection_method', 'unknown')
                                                }
                                                
                                                print(f"          ✅ CIRCULAR DETECTED ({circle_analysis.get('detection_method', 'unknown')}):")
                                                print(f"             Center: ({circle_analysis['center'][0]:.3f}, {circle_analysis['center'][1]:.3f})")
                                                print(f"             Radius: {circle_analysis['radius']:.3f} units")
                                                print(f"             Quality: {circle_analysis['fit_quality']:.4f} (std/avg)")
                                                return result
                                            else:
                                                result['shape_detected'] = 'non_circular'
                                                result['analysis_details'] = {
                                                    'profile_type': 'IfcArbitraryClosedProfileDef',
                                                    'boundary_type': curve_type,
                                                    'point_count': len(points),
                                                    'rejection_reason': 'Failed circular fit test',
                                                    'is_parametric': curve_info.get('is_parametric', False)
                                                }
                                                print(f"          ❌ Not circular (failed fit test)")
                                    else:
                                        print(f"          ❌ Unsupported boundary type: {curve_type}")
                                else:
                                    print(f"          Boundary: Not found")
                            else:
                                print(f"          ❌ No outer curve found")
                        else:
                            print(f"          Profile: {profile.get('type') if profile else 'Not found'}")
                    else:
                        print(f"          ❌ No swept area found")
    
    return result

def detect_circular_openings(ifcjson_file: str) -> Dict[str, Any]:
    """Main function to detect circular openings in ifcJSON file"""
    
    print(f"🔍 DETECTING CIRCULAR OPENINGS FROM ifcJSON")
    print(f"File: {ifcjson_file}")
    print("=" * 80)
    
    try:
        # Load ifcJSON
        data = load_ifcjson(ifcjson_file)
        print(f"✅ Loaded ifcJSON with {len(data.get('data', []))} entities")
        
        # Find all IfcOpeningElement entities
        opening_elements = find_entities_by_type(data, 'IfcOpeningElement')
        print(f"📋 Found {len(opening_elements)} IfcOpeningElement entities")
        
        if len(opening_elements) == 0:
            print("❌ No opening elements found in ifcJSON")
            return {'openings': [], 'summary': {'total': 0, 'circular': 0, 'non_circular': 0}}
        
        # Analyze each opening
        results = []
        circular_count = 0
        non_circular_count = 0
        
        for opening in opening_elements:
            analysis = analyze_opening_geometry(opening, data)
            results.append(analysis)
            
            if analysis['shape_detected'] == 'circular':
                circular_count += 1
            elif analysis['shape_detected'] == 'non_circular':
                non_circular_count += 1
        
        print(f"\n📊 DETECTION SUMMARY")
        print("=" * 50)
        print(f"Total openings: {len(opening_elements)}")
        print(f"Circular detected: {circular_count}")
        print(f"Non-circular: {non_circular_count}")
        print(f"Unknown/failed: {len(opening_elements) - circular_count - non_circular_count}")
        
        if circular_count > 0:
            print(f"\n🎯 CIRCULAR OPENINGS FOUND:")
            print("-" * 40)
            for result in results:
                if result['shape_detected'] == 'circular':
                    params = result['circular_parameters']
                    print(f"  • {result['name']} ({result['globalId']})")
                    print(f"    Center: ({params['center'][0]:.3f}, {params['center'][1]:.3f})")
                    print(f"    Radius: {params['radius']:.3f} units")
                    print(f"    Points: {params['point_count']}")
                    print(f"    Quality: {params['fit_quality']:.4f}")
        
        return {
            'openings': results,
            'summary': {
                'total': len(opening_elements),
                'circular': circular_count,
                'non_circular': non_circular_count,
                'unknown': len(opening_elements) - circular_count - non_circular_count
            }
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

def main():
    if len(sys.argv) != 2:
        print("Usage: python detect_circular_openings_from_ifcjson.py <ifcjson_file>")
        print("\nExamples:")
        print("  python detect_circular_openings_from_ifcjson.py /path/to/OrangeHouse.json")
        print("\nDescription:")
        print("  Detects circular openings by analyzing IfcOpeningElement profile geometry")
        print("  More accurate than tessellation analysis since it uses original coordinates")
        return
    
    ifcjson_file = sys.argv[1]
    
    if not Path(ifcjson_file).exists():
        print(f"❌ File not found: {ifcjson_file}")
        return
    
    results = detect_circular_openings(ifcjson_file)
    
    # Optional: Save results to JSON
    output_file = Path(ifcjson_file).with_suffix('.circular_detection.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

if __name__ == "__main__":
    main()