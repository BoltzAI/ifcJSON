#!/usr/bin/env python3
"""
Compare Wall Dimensions and Orientation

Compares wall geometry (dimensions, orientation, extrusion) between two IFC or ifcJSON files.
Extracts detailed information about placement, extrusion profiles, directions, and opening geometry.

Features:
- Wall geometry analysis (extrusion depth, direction, profile dimensions)
- Comprehensive opening detection via IfcRelVoidsElement and direct search
- Opening geometry analysis (IfcExtrudedAreaSolid, IfcFacetedBrep, IfcBooleanClippingResult)
- Shape classification (rectangular, circular, circular_tessellated, circular_mesh, complex)
- Circular opening detection for both parametric (IfcIndexedPolyCurve) and tessellated (IfcPolyline, IfcFacetedBrep)
- Filled element detection (windows/doors via IfcRelFillsElement)

Usage:
    # Two-file comparison
    python compare_wall_dimensions.py <file1> <file2> <wall_name>
    
    # Single-file analysis
    python compare_wall_dimensions.py <file> <wall_name>
    
Examples:
    python compare_wall_dimensions.py original.ifc roundtrip.ifc "Wand-Ext-OG-1"
    python compare_wall_dimensions.py step1.json step3.json "Wand-Ext-OG-3"
    python compare_wall_dimensions.py OrangeHouse.ifc "Wand-Ext-OG-1"
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

try:
    import ifcopenshell
    import ifcopenshell.util.placement
    import ifcopenshell.util.element
    IFCOPENSHELL_AVAILABLE = True
except ImportError:
    IFCOPENSHELL_AVAILABLE = False
    print("⚠️ Warning: ifcopenshell not available, IFC file analysis limited")

def load_file(file_path: str) -> Tuple[Any, str]:
    """Load IFC or ifcJSON file and return data with format type"""
    path = Path(file_path)
    
    if path.suffix.lower() == '.ifc':
        if not IFCOPENSHELL_AVAILABLE:
            raise ImportError("ifcopenshell required for IFC files")
        return ifcopenshell.open(file_path), 'ifc'
    elif path.suffix.lower() == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f), 'json'
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

def extract_wall_from_ifc(ifc_file, wall_name: str) -> Optional[Dict[str, Any]]:
    """Extract wall information from IFC file"""
    wall = None
    for element in ifc_file.by_type('IfcWallStandardCase'):
        if element.Name == wall_name:
            wall = element
            break
    
    if not wall:
        return None
    
    info = {
        'globalId': wall.GlobalId,
        'name': wall.Name,
        'type': wall.is_a(),
        'placement': {},
        'geometry': {},
        'openings': []
    }
    
    # Extract placement
    if wall.ObjectPlacement:
        matrix = ifcopenshell.util.placement.get_local_placement(wall.ObjectPlacement)
        location = matrix[:3, 3]
        x_axis = matrix[:3, 0]
        y_axis = matrix[:3, 1]
        z_axis = matrix[:3, 2]
        
        info['placement'] = {
            'location': location.tolist(),
            'x_axis': x_axis.tolist(),
            'y_axis': y_axis.tolist(),
            'z_axis': z_axis.tolist(),
            'matrix': matrix.tolist()
        }
    
    # Extract geometry
    if wall.Representation:
        for rep in wall.Representation.Representations:
            if rep.RepresentationIdentifier == 'Body':
                info['geometry']['body_type'] = rep.RepresentationType
                info['geometry']['representation_count'] = len(wall.Representation.Representations)
                
                for item in rep.Items:
                    item_type = item.is_a()
                    
                    if item_type == 'IfcExtrudedAreaSolid':
                        info['geometry']['type'] = 'IfcExtrudedAreaSolid'
                        info['geometry']['depth'] = float(item.Depth)
                        info['geometry']['direction'] = list(item.ExtrudedDirection.DirectionRatios)
                        
                        # Extract position
                        if item.Position:
                            info['geometry']['extrusion_position'] = list(item.Position.Location.Coordinates)
                            if item.Position.Axis:
                                info['geometry']['extrusion_axis'] = list(item.Position.Axis.DirectionRatios)
                            if item.Position.RefDirection:
                                info['geometry']['extrusion_ref_direction'] = list(item.Position.RefDirection.DirectionRatios)
                        
                        # Extract profile
                        if item.SweptArea:
                            profile = item.SweptArea
                            info['geometry']['profile_type'] = profile.is_a()
                            
                            if profile.is_a('IfcRectangleProfileDef'):
                                info['geometry']['profile'] = {
                                    'type': 'rectangle',
                                    'width': float(profile.XDim),
                                    'height': float(profile.YDim)
                                }
                            elif profile.is_a('IfcArbitraryClosedProfileDef'):
                                info['geometry']['profile'] = {
                                    'type': 'arbitrary',
                                    'curve_type': profile.OuterCurve.is_a() if profile.OuterCurve else None
                                }
                                
                                # Extract polyline points if available
                                if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                    points = []
                                    for point in profile.OuterCurve.Points:
                                        coords = list(point.Coordinates)
                                        points.append(coords)
                                    
                                    if points:
                                        info['geometry']['profile']['point_count'] = len(points)
                                        # Calculate bounding box
                                        if len(points) >= 3:
                                            x_coords = [p[0] for p in points if len(p) >= 2]
                                            y_coords = [p[1] for p in points if len(p) >= 2]
                                            if x_coords and y_coords:
                                                info['geometry']['profile']['width'] = max(x_coords) - min(x_coords)
                                                info['geometry']['profile']['height'] = max(y_coords) - min(y_coords)
                    
                    elif item_type == 'IfcBooleanClippingResult':
                        info['geometry']['type'] = 'IfcBooleanClippingResult'
                        
                        # Extract from first operand
                        def extract_from_operand(operand):
                            if operand.is_a('IfcExtrudedAreaSolid'):
                                info['geometry']['base_type'] = 'IfcExtrudedAreaSolid_from_boolean'
                                info['geometry']['depth'] = float(operand.Depth)
                                info['geometry']['direction'] = list(operand.ExtrudedDirection.DirectionRatios)
                                
                                # Extract position
                                if operand.Position:
                                    info['geometry']['extrusion_position'] = list(operand.Position.Location.Coordinates)
                                    if operand.Position.Axis:
                                        info['geometry']['extrusion_axis'] = list(operand.Position.Axis.DirectionRatios)
                                    if operand.Position.RefDirection:
                                        info['geometry']['extrusion_ref_direction'] = list(operand.Position.RefDirection.DirectionRatios)
                                
                                # Extract profile
                                if operand.SweptArea:
                                    profile = operand.SweptArea
                                    info['geometry']['profile_type'] = profile.is_a()
                                    
                                    if profile.is_a('IfcRectangleProfileDef'):
                                        info['geometry']['profile'] = {
                                            'type': 'rectangle',
                                            'width': float(profile.XDim),
                                            'height': float(profile.YDim)
                                        }
                                    elif profile.is_a('IfcArbitraryClosedProfileDef'):
                                        info['geometry']['profile'] = {
                                            'type': 'arbitrary',
                                            'curve_type': profile.OuterCurve.is_a() if profile.OuterCurve else None
                                        }
                                        
                                        # Extract polyline points
                                        if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                            points = []
                                            for point in profile.OuterCurve.Points:
                                                coords = list(point.Coordinates)
                                                points.append(coords)
                                            
                                            if points:
                                                info['geometry']['profile']['point_count'] = len(points)
                                                # Calculate bounding box
                                                if len(points) >= 3:
                                                    x_coords = [p[0] for p in points if len(p) >= 2]
                                                    y_coords = [p[1] for p in points if len(p) >= 2]
                                                    if x_coords and y_coords:
                                                        info['geometry']['profile']['width'] = max(x_coords) - min(x_coords)
                                                        info['geometry']['profile']['height'] = max(y_coords) - min(y_coords)
                                return operand
                            elif operand.is_a('IfcBooleanClippingResult'):
                                # Handle nested boolean
                                return extract_from_operand(operand.FirstOperand)
                            return None
                        
                        extract_from_operand(item.FirstOperand)
    
    # Extract openings with detailed geometry
    # Method 1: Through void relationships (primary method)
    for rel in ifc_file.by_type('IfcRelVoidsElement'):
        if rel.RelatingBuildingElement == wall:
            opening = rel.RelatedOpeningElement
            opening_info = {
                'globalId': opening.GlobalId,
                'name': opening.Name or 'Unnamed',
                'type': opening.is_a(),
                'placement': {},
                'geometry': {},
                'found_via': 'IfcRelVoidsElement'
            }
            
            # Extract placement
            if opening.ObjectPlacement:
                matrix = ifcopenshell.util.placement.get_local_placement(opening.ObjectPlacement)
                opening_info['placement']['location'] = matrix[:3, 3].tolist()
                opening_info['placement']['x_axis'] = matrix[:3, 0].tolist()
                opening_info['placement']['y_axis'] = matrix[:3, 1].tolist()
                opening_info['placement']['z_axis'] = matrix[:3, 2].tolist()
            
            # Extract geometry
            if opening.Representation:
                for rep in opening.Representation.Representations:
                    if rep.RepresentationIdentifier == 'Body':
                        opening_info['geometry']['body_type'] = rep.RepresentationType
                        
                        for item in rep.Items:
                            item_type = item.is_a()
                            opening_info['geometry']['type'] = item_type
                            
                            if item_type == 'IfcExtrudedAreaSolid':
                                opening_info['geometry']['depth'] = float(item.Depth)
                                opening_info['geometry']['direction'] = list(item.ExtrudedDirection.DirectionRatios)
                                
                                # Extract position
                                if item.Position:
                                    opening_info['geometry']['extrusion_position'] = list(item.Position.Location.Coordinates)
                                    if item.Position.Axis:
                                        opening_info['geometry']['extrusion_axis'] = list(item.Position.Axis.DirectionRatios)
                                    if item.Position.RefDirection:
                                        opening_info['geometry']['extrusion_ref_direction'] = list(item.Position.RefDirection.DirectionRatios)
                                
                                # Extract profile for shape detection
                                if item.SweptArea:
                                    profile = item.SweptArea
                                    opening_info['geometry']['profile_type'] = profile.is_a()
                                    
                                    if profile.is_a('IfcRectangleProfileDef'):
                                        opening_info['geometry']['profile'] = {
                                            'type': 'rectangle',
                                            'width': float(profile.XDim),
                                            'height': float(profile.YDim)
                                        }
                                        opening_info['geometry']['shape'] = 'rectangular'
                                    elif profile.is_a('IfcCircleProfileDef'):
                                        opening_info['geometry']['profile'] = {
                                            'type': 'circle',
                                            'radius': float(profile.Radius)
                                        }
                                        opening_info['geometry']['shape'] = 'circular'
                                    elif profile.is_a('IfcArbitraryClosedProfileDef'):
                                        opening_info['geometry']['profile'] = {
                                            'type': 'arbitrary',
                                            'curve_type': profile.OuterCurve.is_a() if profile.OuterCurve else None
                                        }
                                        
                                        # Analyze curve for circular pattern
                                        if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                            points = []
                                            for point in profile.OuterCurve.Points:
                                                coords = list(point.Coordinates)
                                                points.append(coords)
                                            
                                            if points:
                                                opening_info['geometry']['profile']['point_count'] = len(points)
                                                
                                                # Simple circular detection (high point count + equal distances from center)
                                                if len(points) > 20:  # High tessellation suggests circular
                                                    # Calculate centroid
                                                    cx = sum(p[0] for p in points) / len(points)
                                                    cy = sum(p[1] for p in points) / len(points)
                                                    
                                                    # Calculate distances from centroid
                                                    distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points]
                                                    avg_radius = sum(distances) / len(distances)
                                                    radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                    
                                                    # If standard deviation is small relative to radius, likely circular
                                                    if radius_std / avg_radius < 0.1:  # 10% tolerance
                                                        opening_info['geometry']['shape'] = 'circular_tessellated'
                                                        opening_info['geometry']['profile']['estimated_radius'] = avg_radius
                                                        opening_info['geometry']['profile']['center'] = [cx, cy]
                                                        opening_info['geometry']['profile']['radius_std_ratio'] = radius_std / avg_radius
                                                    else:
                                                        opening_info['geometry']['shape'] = 'complex'
                                                        opening_info['geometry']['profile']['radius_std_ratio'] = radius_std / avg_radius
                                                else:
                                                    opening_info['geometry']['shape'] = 'polygonal'
                                        
                                        # Handle IfcIndexedPolyCurve (parametric arcs)
                                        elif profile.OuterCurve and profile.OuterCurve.is_a('IfcIndexedPolyCurve'):
                                            curve = profile.OuterCurve
                                            opening_info['geometry']['profile']['curve_type'] = 'IfcIndexedPolyCurve'
                                            
                                            # Check for arc segments
                                            if hasattr(curve, 'Segments') and curve.Segments:
                                                arc_count = sum(1 for seg in curve.Segments if hasattr(seg, 'is_a') and seg.is_a('IfcArcIndex'))
                                                opening_info['geometry']['profile']['arc_segments'] = arc_count
                                                opening_info['geometry']['profile']['total_segments'] = len(curve.Segments)
                                                
                                                if arc_count > 0:
                                                    opening_info['geometry']['shape'] = 'circular_parametric'
                                                    
                                                    # Try to extract radius from arc segments
                                                    if curve.Points and len(curve.Points.CoordList) >= 4:
                                                        points = curve.Points.CoordList
                                                        opening_info['geometry']['profile']['control_points'] = len(points)
                                                        
                                                        # For circular arcs, estimate radius from control points
                                                        if len(points) >= 3:
                                                            p1, p2, p3 = points[0], points[1], points[2]
                                                            # Simple radius estimation from 3 points on circle
                                                            dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
                                                            dx2, dy2 = p3[0] - p2[0], p3[1] - p2[1]
                                                            
                                                            # Calculate approximate radius
                                                            chord1 = (dx1**2 + dy1**2)**0.5
                                                            chord2 = (dx2**2 + dy2**2)**0.5
                                                            opening_info['geometry']['profile']['estimated_radius'] = (chord1 + chord2) / 2
                                        
                                        # Add bounding box calculation for arbitrary profiles
                                        if opening_info['geometry']['profile'].get('point_count', 0) > 0:
                                            points = []
                                            if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                                for point in profile.OuterCurve.Points:
                                                    points.append(list(point.Coordinates))
                                            
                                            if points and len(points) >= 3:
                                                x_coords = [p[0] for p in points if len(p) >= 2]
                                                y_coords = [p[1] for p in points if len(p) >= 2]
                                                if x_coords and y_coords:
                                                    opening_info['geometry']['profile']['width'] = max(x_coords) - min(x_coords)
                                                    opening_info['geometry']['profile']['height'] = max(y_coords) - min(y_coords)
                                                    opening_info['geometry']['profile']['center_x'] = (max(x_coords) + min(x_coords)) / 2
                                                    opening_info['geometry']['profile']['center_y'] = (max(y_coords) + min(y_coords)) / 2
                            
                            elif item_type == 'IfcFacetedBrep':
                                # Handle tessellated mesh geometry (common for complex/circular openings)
                                opening_info['geometry']['mesh_type'] = 'IfcFacetedBrep'
                                
                                if hasattr(item, 'Outer') and item.Outer:
                                    shell = item.Outer
                                    if hasattr(shell, 'CfsFaces') and shell.CfsFaces:
                                        face_count = len(shell.CfsFaces)
                                        opening_info['geometry']['face_count'] = face_count
                                        
                                        # Collect all vertices to analyze shape
                                        all_vertices = []
                                        for face in shell.CfsFaces:
                                            if hasattr(face, 'Bounds'):
                                                for bound in face.Bounds:
                                                    if hasattr(bound, 'Bound') and hasattr(bound.Bound, 'Polygon'):
                                                        for point in bound.Bound.Polygon:
                                                            if hasattr(point, 'Coordinates'):
                                                                all_vertices.append(list(point.Coordinates))
                                        
                                        if all_vertices:
                                            opening_info['geometry']['vertex_count'] = len(all_vertices)
                                            
                                            # Analyze if this could be a circular opening based on face/vertex count
                                            if face_count > 50:  # High face count suggests circular tessellation
                                                # Extract unique vertices (remove duplicates)
                                                unique_vertices = []
                                                for v in all_vertices:
                                                    is_duplicate = False
                                                    for uv in unique_vertices:
                                                        if all(abs(v[i] - uv[i]) < 1e-6 for i in range(min(len(v), len(uv)))):
                                                            is_duplicate = True
                                                            break
                                                    if not is_duplicate:
                                                        unique_vertices.append(v)
                                                
                                                if unique_vertices and len(unique_vertices) > 10:
                                                    # Project to 2D (assume extrusion along one axis)
                                                    points_2d = [(v[0], v[1]) for v in unique_vertices if len(v) >= 2]
                                                    
                                                    if len(points_2d) > 10:
                                                        # Calculate centroid and radius distribution
                                                        cx = sum(p[0] for p in points_2d) / len(points_2d)
                                                        cy = sum(p[1] for p in points_2d) / len(points_2d)
                                                        
                                                        distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points_2d]
                                                        avg_radius = sum(distances) / len(distances)
                                                        radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                        
                                                        opening_info['geometry']['estimated_radius'] = avg_radius
                                                        opening_info['geometry']['radius_std_ratio'] = radius_std / avg_radius if avg_radius > 0 else 0
                                                        opening_info['geometry']['center'] = [cx, cy]
                                                        
                                                        # Classify based on radius standard deviation
                                                        if radius_std / avg_radius < 0.15:  # 15% tolerance for mesh
                                                            opening_info['geometry']['shape'] = 'circular_mesh'
                                                        else:
                                                            opening_info['geometry']['shape'] = 'complex_mesh'
                                                    else:
                                                        opening_info['geometry']['shape'] = 'mesh_low_detail'
                                            else:
                                                opening_info['geometry']['shape'] = 'simple_mesh'
                            
                            elif item_type == 'IfcBooleanClippingResult':
                                # Handle boolean operations on openings
                                opening_info['geometry']['boolean_type'] = 'IfcBooleanClippingResult'
                                # Could recursively analyze the operands, but for now just note the type
                                opening_info['geometry']['shape'] = 'boolean_operation'
                            
                            else:
                                # Handle other geometry types
                                opening_info['geometry']['shape'] = f'unknown_{item_type}'
                                            
                            # Check for filled elements (windows/doors) with DETAILED GEOMETRY ANALYSIS
                            filled_elements = []
                            for fill_rel in ifc_file.by_type('IfcRelFillsElement'):
                                if fill_rel.RelatingOpeningElement == opening:
                                    element = fill_rel.RelatedBuildingElement
                                    filled_info = {
                                        'globalId': element.GlobalId,
                                        'name': element.Name or 'Unnamed',
                                        'type': element.is_a(),
                                        'geometry': {}
                                    }
                                    
                                    # EXTRACT DETAILED GEOMETRY from filled element (window/door)
                                    if element.Representation:
                                        for rep in element.Representation.Representations:
                                            if rep.RepresentationIdentifier == 'Body':
                                                filled_info['geometry']['body_type'] = rep.RepresentationType
                                                filled_info['geometry']['representation_count'] = len(element.Representation.Representations)
                                                
                                                for item in rep.Items:
                                                    item_type = item.is_a()
                                                    filled_info['geometry']['type'] = item_type
                                                    
                                                    if item_type == 'IfcExtrudedAreaSolid':
                                                        filled_info['geometry']['depth'] = float(item.Depth)
                                                        filled_info['geometry']['direction'] = list(item.ExtrudedDirection.DirectionRatios)
                                                        
                                                        # Extract position
                                                        if item.Position:
                                                            filled_info['geometry']['extrusion_position'] = list(item.Position.Location.Coordinates)
                                                            if item.Position.Axis:
                                                                filled_info['geometry']['extrusion_axis'] = list(item.Position.Axis.DirectionRatios)
                                                            if item.Position.RefDirection:
                                                                filled_info['geometry']['extrusion_ref_direction'] = list(item.Position.RefDirection.DirectionRatios)
                                                        
                                                        # Extract profile for shape detection
                                                        if item.SweptArea:
                                                            profile = item.SweptArea
                                                            filled_info['geometry']['profile_type'] = profile.is_a()
                                                            
                                                            if profile.is_a('IfcRectangleProfileDef'):
                                                                filled_info['geometry']['profile'] = {
                                                                    'type': 'rectangle',
                                                                    'width': float(profile.XDim),
                                                                    'height': float(profile.YDim)
                                                                }
                                                                filled_info['geometry']['shape'] = 'rectangular'
                                                            elif profile.is_a('IfcCircleProfileDef'):
                                                                filled_info['geometry']['profile'] = {
                                                                    'type': 'circle',
                                                                    'radius': float(profile.Radius)
                                                                }
                                                                filled_info['geometry']['shape'] = 'circular'
                                                            elif profile.is_a('IfcArbitraryClosedProfileDef'):
                                                                filled_info['geometry']['profile'] = {
                                                                    'type': 'arbitrary',
                                                                    'curve_type': profile.OuterCurve.is_a() if profile.OuterCurve else None
                                                                }
                                                                
                                                                # Analyze curve for circular pattern
                                                                if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                                                    points = []
                                                                    for point in profile.OuterCurve.Points:
                                                                        coords = list(point.Coordinates)
                                                                        points.append(coords)
                                                                    
                                                                    if points:
                                                                        filled_info['geometry']['profile']['point_count'] = len(points)
                                                                        
                                                                        # Simple circular detection (high point count + equal distances from center)
                                                                        if len(points) > 20:  # High tessellation suggests circular
                                                                            # Calculate centroid
                                                                            cx = sum(p[0] for p in points) / len(points)
                                                                            cy = sum(p[1] for p in points) / len(points)
                                                                            
                                                                            # Calculate distances from centroid
                                                                            distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points]
                                                                            avg_radius = sum(distances) / len(distances)
                                                                            radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                                            
                                                                            # If standard deviation is small relative to radius, likely circular
                                                                            if radius_std / avg_radius < 0.1:  # 10% tolerance
                                                                                filled_info['geometry']['shape'] = 'circular_tessellated'
                                                                                filled_info['geometry']['profile']['estimated_radius'] = avg_radius
                                                                                filled_info['geometry']['profile']['center'] = [cx, cy]
                                                                                filled_info['geometry']['profile']['radius_std_ratio'] = radius_std / avg_radius
                                                                            else:
                                                                                filled_info['geometry']['shape'] = 'complex'
                                                                                filled_info['geometry']['profile']['radius_std_ratio'] = radius_std / avg_radius
                                                                        else:
                                                                            filled_info['geometry']['shape'] = 'polygonal'
                                                                
                                                                # Handle IfcIndexedPolyCurve (parametric arcs)
                                                                elif profile.OuterCurve and profile.OuterCurve.is_a('IfcIndexedPolyCurve'):
                                                                    curve = profile.OuterCurve
                                                                    filled_info['geometry']['profile']['curve_type'] = 'IfcIndexedPolyCurve'
                                                                    
                                                                    # Check for arc segments
                                                                    if hasattr(curve, 'Segments') and curve.Segments:
                                                                        arc_count = sum(1 for seg in curve.Segments if hasattr(seg, 'is_a') and seg.is_a('IfcArcIndex'))
                                                                        filled_info['geometry']['profile']['arc_segments'] = arc_count
                                                                        filled_info['geometry']['profile']['total_segments'] = len(curve.Segments)
                                                                        
                                                                        if arc_count > 0:
                                                                            filled_info['geometry']['shape'] = 'circular_parametric'
                                                                            
                                                                            # Try to extract radius from arc segments
                                                                            if curve.Points and len(curve.Points.CoordList) >= 4:
                                                                                points = curve.Points.CoordList
                                                                                filled_info['geometry']['profile']['control_points'] = len(points)
                                                                                
                                                                                # For circular arcs, estimate radius from control points
                                                                                if len(points) >= 3:
                                                                                    p1, p2, p3 = points[0], points[1], points[2]
                                                                                    # Simple radius estimation from 3 points on circle
                                                                                    dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
                                                                                    dx2, dy2 = p3[0] - p2[0], p3[1] - p2[1]
                                                                                    
                                                                                    # Calculate approximate radius
                                                                                    chord1 = (dx1**2 + dy1**2)**0.5
                                                                                    chord2 = (dx2**2 + dy2**2)**0.5
                                                                                    filled_info['geometry']['profile']['estimated_radius'] = (chord1 + chord2) / 2
                                                                
                                                                # Add bounding box calculation for arbitrary profiles
                                                                if filled_info['geometry']['profile'].get('point_count', 0) > 0:
                                                                    points = []
                                                                    if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                                                        for point in profile.OuterCurve.Points:
                                                                            points.append(list(point.Coordinates))
                                                                    
                                                                    if points and len(points) >= 3:
                                                                        x_coords = [p[0] for p in points if len(p) >= 2]
                                                                        y_coords = [p[1] for p in points if len(p) >= 2]
                                                                        if x_coords and y_coords:
                                                                            filled_info['geometry']['profile']['width'] = max(x_coords) - min(x_coords)
                                                                            filled_info['geometry']['profile']['height'] = max(y_coords) - min(y_coords)
                                                                            filled_info['geometry']['profile']['center_x'] = (max(x_coords) + min(x_coords)) / 2
                                                                            filled_info['geometry']['profile']['center_y'] = (max(y_coords) + min(y_coords)) / 2
                                                    
                                                    elif item_type == 'IfcFacetedBrep':
                                                        # Handle tessellated mesh geometry (common for complex/circular windows)
                                                        filled_info['geometry']['mesh_type'] = 'IfcFacetedBrep'
                                                        
                                                        if hasattr(item, 'Outer') and item.Outer:
                                                            shell = item.Outer
                                                            if hasattr(shell, 'CfsFaces') and shell.CfsFaces:
                                                                face_count = len(shell.CfsFaces)
                                                                filled_info['geometry']['face_count'] = face_count
                                                                
                                                                # Collect all vertices to analyze shape
                                                                all_vertices = []
                                                                for face in shell.CfsFaces:
                                                                    if hasattr(face, 'Bounds'):
                                                                        for bound in face.Bounds:
                                                                            if hasattr(bound, 'Bound') and hasattr(bound.Bound, 'Polygon'):
                                                                                for point in bound.Bound.Polygon:
                                                                                    if hasattr(point, 'Coordinates'):
                                                                                        all_vertices.append(list(point.Coordinates))
                                                                
                                                                if all_vertices:
                                                                    filled_info['geometry']['vertex_count'] = len(all_vertices)
                                                                    
                                                                    # Analyze if this could be a circular window based on face/vertex count
                                                                    if face_count > 50:  # High face count suggests circular tessellation
                                                                        # Extract unique vertices (remove duplicates)
                                                                        unique_vertices = []
                                                                        for v in all_vertices:
                                                                            is_duplicate = False
                                                                            for uv in unique_vertices:
                                                                                if all(abs(v[i] - uv[i]) < 1e-6 for i in range(min(len(v), len(uv)))):
                                                                                    is_duplicate = True
                                                                                    break
                                                                            if not is_duplicate:
                                                                                unique_vertices.append(v)
                                                                        
                                                                        if unique_vertices and len(unique_vertices) > 10:
                                                                            # Project to 2D (assume extrusion along one axis)
                                                                            points_2d = [(v[0], v[1]) for v in unique_vertices if len(v) >= 2]
                                                                            
                                                                            if len(points_2d) > 10:
                                                                                # Calculate centroid and radius distribution
                                                                                cx = sum(p[0] for p in points_2d) / len(points_2d)
                                                                                cy = sum(p[1] for p in points_2d) / len(points_2d)
                                                                                
                                                                                distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points_2d]
                                                                                avg_radius = sum(distances) / len(distances)
                                                                                radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                                                
                                                                                filled_info['geometry']['estimated_radius'] = avg_radius
                                                                                filled_info['geometry']['radius_std_ratio'] = radius_std / avg_radius if avg_radius > 0 else 0
                                                                                filled_info['geometry']['center'] = [cx, cy]
                                                                                
                                                                                # Classify based on radius standard deviation
                                                                                if radius_std / avg_radius < 0.15:  # 15% tolerance for mesh
                                                                                    filled_info['geometry']['shape'] = 'circular_mesh'
                                                                                else:
                                                                                    filled_info['geometry']['shape'] = 'complex_mesh'
                                                                            else:
                                                                                filled_info['geometry']['shape'] = 'mesh_low_detail'
                                                            else:
                                                                filled_info['geometry']['shape'] = 'simple_mesh'
                                                                
                                                                # For simple meshes, still try to analyze overall shape
                                                                if all_vertices and len(all_vertices) > 4:
                                                                    # Extract unique vertices (remove duplicates) for basic analysis
                                                                    unique_vertices = []
                                                                    for v in all_vertices:
                                                                        is_duplicate = False
                                                                        for uv in unique_vertices:
                                                                            if all(abs(v[i] - uv[i]) < 1e-6 for i in range(min(len(v), len(uv)))):
                                                                                is_duplicate = True
                                                                                break
                                                                        if not is_duplicate:
                                                                            unique_vertices.append(v)
                                                                    
                                                                    if unique_vertices and len(unique_vertices) >= 4:
                                                                        # Project to 2D and check basic shape properties
                                                                        points_2d = [(v[0], v[1]) for v in unique_vertices if len(v) >= 2]
                                                                        
                                                                        if len(points_2d) >= 4:
                                                                            # Calculate bounding box aspect ratio
                                                                            x_coords = [p[0] for p in points_2d]
                                                                            y_coords = [p[1] for p in points_2d]
                                                                            
                                                                            if x_coords and y_coords:
                                                                                width = max(x_coords) - min(x_coords)
                                                                                height = max(y_coords) - min(y_coords)
                                                                                filled_info['geometry']['bounding_box'] = {
                                                                                    'width': width,
                                                                                    'height': height,
                                                                                    'aspect_ratio': width / height if height > 0 else 0
                                                                                }
                                                                                
                                                                                # Calculate centroid and radius distribution for shape hints
                                                                                cx = sum(x_coords) / len(x_coords)
                                                                                cy = sum(y_coords) / len(y_coords)
                                                                                
                                                                                distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points_2d]
                                                                                avg_radius = sum(distances) / len(distances)
                                                                                radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                                                
                                                                                filled_info['geometry']['shape_analysis'] = {
                                                                                    'center': [cx, cy],
                                                                                    'avg_radius': avg_radius,
                                                                                    'radius_std_ratio': radius_std / avg_radius if avg_radius > 0 else 0,
                                                                                    'unique_vertices': len(unique_vertices)
                                                                                }
                                                                                
                                                                                # Shape hints based on analysis
                                                                                aspect_ratio = width / height if height > 0 else 0
                                                                                radius_consistency = radius_std / avg_radius if avg_radius > 0 else 1
                                                                                
                                                                                if 0.8 <= aspect_ratio <= 1.2 and radius_consistency < 0.2:
                                                                                    filled_info['geometry']['shape_hint'] = 'likely_circular'
                                                                                elif 0.8 <= aspect_ratio <= 1.2:
                                                                                    filled_info['geometry']['shape_hint'] = 'likely_square'
                                                                                elif aspect_ratio > 1.5 or aspect_ratio < 0.67:
                                                                                    filled_info['geometry']['shape_hint'] = 'likely_rectangular'
                                                                                else:
                                                                                    filled_info['geometry']['shape_hint'] = 'irregular'
                                                    
                                                    elif item_type == 'IfcBooleanClippingResult':
                                                        # Handle boolean operations on windows/doors
                                                        filled_info['geometry']['boolean_type'] = 'IfcBooleanClippingResult'
                                                        filled_info['geometry']['shape'] = 'boolean_operation'
                                                    
                                                    else:
                                                        # Handle other geometry types
                                                        filled_info['geometry']['shape'] = f'unknown_{item_type}'
                                    
                                    filled_elements.append(filled_info)
                            opening_info['filled_by'] = filled_elements
            
            info['openings'].append(opening_info)
    
    # Method 2: Direct search for IfcOpeningElement (backup method)
    # This helps identify if there are openings not properly linked via relationships
    all_openings = ifc_file.by_type('IfcOpeningElement')
    found_opening_ids = {o['globalId'] for o in info['openings']}
    
    # Check if there are any orphaned openings that might be related to this wall
    for opening in all_openings:
        if opening.GlobalId not in found_opening_ids:
            # Check if this opening might be spatially related to the wall
            # by examining its placement relative to the wall
            if opening.ObjectPlacement and wall.ObjectPlacement:
                try:
                    wall_matrix = ifcopenshell.util.placement.get_local_placement(wall.ObjectPlacement)
                    opening_matrix = ifcopenshell.util.placement.get_local_placement(opening.ObjectPlacement)
                    
                    # Calculate distance between wall and opening
                    wall_pos = wall_matrix[:3, 3]
                    opening_pos = opening_matrix[:3, 3]
                    distance = np.linalg.norm(opening_pos - wall_pos)
                    
                    # If opening is very close to wall (within 1m), it might be related
                    # More restrictive distance to avoid picking up openings from other walls
                    if distance < 1.0:
                        # Additional check: opening name should relate to the wall
                        opening_name = opening.Name or 'Unnamed'
                        wall_name_part = wall.Name.split('-')[-1] if wall.Name else ''  # e.g., "OG-1" from "Wand-Ext-OG-1"
                        
                        # Only include if opening name contains similar pattern or is very close (< 0.5m)
                        include_opening = False
                        if distance < 0.5:  # Very close, likely related
                            include_opening = True
                        elif wall_name_part and wall_name_part in opening_name:  # Name pattern match
                            include_opening = True
                        
                        if include_opening:
                            opening_info = {
                                'globalId': opening.GlobalId,
                                'name': opening_name,
                                'type': opening.is_a(),
                                'placement': {},
                                'geometry': {},
                                'found_via': 'Direct_IfcOpeningElement_search',
                                'distance_to_wall': float(distance),
                                'warning': f'Found via direct search - may not be properly linked (distance: {distance:.2f}m)'
                            }
                            
                            # Add basic placement info
                            opening_info['placement']['location'] = opening_pos.tolist()
                            opening_info['placement']['x_axis'] = opening_matrix[:3, 0].tolist()
                            opening_info['placement']['y_axis'] = opening_matrix[:3, 1].tolist()
                            opening_info['placement']['z_axis'] = opening_matrix[:3, 2].tolist()
                            
                            # Extract geometry (same logic as Method 1)
                            if opening.Representation:
                                for rep in opening.Representation.Representations:
                                    if rep.RepresentationIdentifier == 'Body':
                                        opening_info['geometry']['body_type'] = rep.RepresentationType
                                        
                                        for item in rep.Items:
                                            item_type = item.is_a()
                                            opening_info['geometry']['type'] = item_type
                                            
                                            if item_type == 'IfcExtrudedAreaSolid':
                                                opening_info['geometry']['depth'] = float(item.Depth)
                                                opening_info['geometry']['direction'] = list(item.ExtrudedDirection.DirectionRatios)
                                                
                                                # Extract position
                                                if item.Position:
                                                    opening_info['geometry']['extrusion_position'] = list(item.Position.Location.Coordinates)
                                                    if item.Position.Axis:
                                                        opening_info['geometry']['extrusion_axis'] = list(item.Position.Axis.DirectionRatios)
                                                    if item.Position.RefDirection:
                                                        opening_info['geometry']['extrusion_ref_direction'] = list(item.Position.RefDirection.DirectionRatios)
                                                
                                                # Extract profile for shape detection
                                                if item.SweptArea:
                                                    profile = item.SweptArea
                                                    opening_info['geometry']['profile_type'] = profile.is_a()
                                                    
                                                    if profile.is_a('IfcRectangleProfileDef'):
                                                        opening_info['geometry']['profile'] = {
                                                            'type': 'rectangle',
                                                            'width': float(profile.XDim),
                                                            'height': float(profile.YDim)
                                                        }
                                                        opening_info['geometry']['shape'] = 'rectangular'
                                                    elif profile.is_a('IfcCircleProfileDef'):
                                                        opening_info['geometry']['profile'] = {
                                                            'type': 'circle',
                                                            'radius': float(profile.Radius)
                                                        }
                                                        opening_info['geometry']['shape'] = 'circular'
                                                    elif profile.is_a('IfcArbitraryClosedProfileDef'):
                                                        opening_info['geometry']['profile'] = {
                                                            'type': 'arbitrary',
                                                            'curve_type': profile.OuterCurve.is_a() if profile.OuterCurve else None
                                                        }
                                                        
                                                        # Analyze curve for circular pattern
                                                        if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                                            points = []
                                                            for point in profile.OuterCurve.Points:
                                                                coords = list(point.Coordinates)
                                                                points.append(coords)
                                                            
                                                            if points:
                                                                opening_info['geometry']['profile']['point_count'] = len(points)
                                                                
                                                                # Simple circular detection (high point count + equal distances from center)
                                                                if len(points) > 20:  # High tessellation suggests circular
                                                                    # Calculate centroid
                                                                    cx = sum(p[0] for p in points) / len(points)
                                                                    cy = sum(p[1] for p in points) / len(points)
                                                                    
                                                                    # Calculate distances from centroid
                                                                    distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points]
                                                                    avg_radius = sum(distances) / len(distances)
                                                                    radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                                    
                                                                    # If standard deviation is small relative to radius, likely circular
                                                                    if radius_std / avg_radius < 0.1:  # 10% tolerance
                                                                        opening_info['geometry']['shape'] = 'circular_tessellated'
                                                                        opening_info['geometry']['profile']['estimated_radius'] = avg_radius
                                                                        opening_info['geometry']['profile']['center'] = [cx, cy]
                                                                        opening_info['geometry']['profile']['radius_std_ratio'] = radius_std / avg_radius
                                                                    else:
                                                                        opening_info['geometry']['shape'] = 'complex'
                                                                        opening_info['geometry']['profile']['radius_std_ratio'] = radius_std / avg_radius
                                                                else:
                                                                    opening_info['geometry']['shape'] = 'polygonal'
                                                        
                                                        # Handle IfcIndexedPolyCurve (parametric arcs)
                                                        elif profile.OuterCurve and profile.OuterCurve.is_a('IfcIndexedPolyCurve'):
                                                            curve = profile.OuterCurve
                                                            opening_info['geometry']['profile']['curve_type'] = 'IfcIndexedPolyCurve'
                                                            
                                                            # Check for arc segments
                                                            if hasattr(curve, 'Segments') and curve.Segments:
                                                                arc_count = sum(1 for seg in curve.Segments if hasattr(seg, 'is_a') and seg.is_a('IfcArcIndex'))
                                                                opening_info['geometry']['profile']['arc_segments'] = arc_count
                                                                opening_info['geometry']['profile']['total_segments'] = len(curve.Segments)
                                                                
                                                                if arc_count > 0:
                                                                    opening_info['geometry']['shape'] = 'circular_parametric'
                                                                    
                                                                    # Try to extract radius from arc segments
                                                                    if curve.Points and len(curve.Points.CoordList) >= 4:
                                                                        points = curve.Points.CoordList
                                                                        opening_info['geometry']['profile']['control_points'] = len(points)
                                                                        
                                                                        # For circular arcs, estimate radius from control points
                                                                        if len(points) >= 3:
                                                                            p1, p2, p3 = points[0], points[1], points[2]
                                                                            # Simple radius estimation from 3 points on circle
                                                                            dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
                                                                            dx2, dy2 = p3[0] - p2[0], p3[1] - p2[1]
                                                                            
                                                                            # Calculate approximate radius
                                                                            chord1 = (dx1**2 + dy1**2)**0.5
                                                                            chord2 = (dx2**2 + dy2**2)**0.5
                                                                            opening_info['geometry']['profile']['estimated_radius'] = (chord1 + chord2) / 2
                                                        
                                                        # Add bounding box calculation for arbitrary profiles
                                                        if opening_info['geometry']['profile'].get('point_count', 0) > 0:
                                                            points = []
                                                            if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                                                for point in profile.OuterCurve.Points:
                                                                    points.append(list(point.Coordinates))
                                                            
                                                            if points and len(points) >= 3:
                                                                x_coords = [p[0] for p in points if len(p) >= 2]
                                                                y_coords = [p[1] for p in points if len(p) >= 2]
                                                                if x_coords and y_coords:
                                                                    opening_info['geometry']['profile']['width'] = max(x_coords) - min(x_coords)
                                                                    opening_info['geometry']['profile']['height'] = max(y_coords) - min(y_coords)
                                                                    opening_info['geometry']['profile']['center_x'] = (max(x_coords) + min(x_coords)) / 2
                                                                    opening_info['geometry']['profile']['center_y'] = (max(y_coords) + min(y_coords)) / 2
                                            
                                            elif item_type == 'IfcFacetedBrep':
                                                # Handle tessellated mesh geometry (common for complex/circular openings)
                                                opening_info['geometry']['mesh_type'] = 'IfcFacetedBrep'
                                                
                                                if hasattr(item, 'Outer') and item.Outer:
                                                    shell = item.Outer
                                                    if hasattr(shell, 'CfsFaces') and shell.CfsFaces:
                                                        face_count = len(shell.CfsFaces)
                                                        opening_info['geometry']['face_count'] = face_count
                                                        
                                                        # Collect all vertices to analyze shape
                                                        all_vertices = []
                                                        for face in shell.CfsFaces:
                                                            if hasattr(face, 'Bounds'):
                                                                for bound in face.Bounds:
                                                                    if hasattr(bound, 'Bound') and hasattr(bound.Bound, 'Polygon'):
                                                                        for point in bound.Bound.Polygon:
                                                                            if hasattr(point, 'Coordinates'):
                                                                                all_vertices.append(list(point.Coordinates))
                                                        
                                                        if all_vertices:
                                                            opening_info['geometry']['vertex_count'] = len(all_vertices)
                                                            
                                                            # Analyze if this could be a circular opening based on face/vertex count
                                                            if face_count > 50:  # High face count suggests circular tessellation
                                                                # Extract unique vertices (remove duplicates)
                                                                unique_vertices = []
                                                                for v in all_vertices:
                                                                    is_duplicate = False
                                                                    for uv in unique_vertices:
                                                                        if all(abs(v[i] - uv[i]) < 1e-6 for i in range(min(len(v), len(uv)))):
                                                                            is_duplicate = True
                                                                            break
                                                                    if not is_duplicate:
                                                                        unique_vertices.append(v)
                                                                
                                                                if unique_vertices and len(unique_vertices) > 10:
                                                                    # Project to 2D (assume extrusion along one axis)
                                                                    points_2d = [(v[0], v[1]) for v in unique_vertices if len(v) >= 2]
                                                                    
                                                                    if len(points_2d) > 10:
                                                                        # Calculate centroid and radius distribution
                                                                        cx = sum(p[0] for p in points_2d) / len(points_2d)
                                                                        cy = sum(p[1] for p in points_2d) / len(points_2d)
                                                                        
                                                                        distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points_2d]
                                                                        avg_radius = sum(distances) / len(distances)
                                                                        radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                                        
                                                                        opening_info['geometry']['estimated_radius'] = avg_radius
                                                                        opening_info['geometry']['radius_std_ratio'] = radius_std / avg_radius if avg_radius > 0 else 0
                                                                        opening_info['geometry']['center'] = [cx, cy]
                                                                        
                                                                        # Classify based on radius standard deviation
                                                                        if radius_std / avg_radius < 0.15:  # 15% tolerance for mesh
                                                                            opening_info['geometry']['shape'] = 'circular_mesh'
                                                                        else:
                                                                            opening_info['geometry']['shape'] = 'complex_mesh'
                                                                    else:
                                                                        opening_info['geometry']['shape'] = 'mesh_low_detail'
                                                            else:
                                                                opening_info['geometry']['shape'] = 'simple_mesh'
                                            
                                            elif item_type == 'IfcBooleanClippingResult':
                                                # Handle boolean operations on openings
                                                opening_info['geometry']['boolean_type'] = 'IfcBooleanClippingResult'
                                                # Could recursively analyze the operands, but for now just note the type
                                                opening_info['geometry']['shape'] = 'boolean_operation'
                                            
                                            else:
                                                # Handle other geometry types
                                                opening_info['geometry']['shape'] = f'unknown_{item_type}'
                            
                            # Check for filled elements (windows/doors) with DETAILED GEOMETRY ANALYSIS
                            filled_elements = []
                            for fill_rel in ifc_file.by_type('IfcRelFillsElement'):
                                if fill_rel.RelatingOpeningElement == opening:
                                    element = fill_rel.RelatedBuildingElement
                                    filled_info = {
                                        'globalId': element.GlobalId,
                                        'name': element.Name or 'Unnamed',
                                        'type': element.is_a(),
                                        'geometry': {}
                                    }
                                    
                                    # EXTRACT DETAILED GEOMETRY from filled element (window/door)
                                    if element.Representation:
                                        for rep in element.Representation.Representations:
                                            if rep.RepresentationIdentifier == 'Body':
                                                filled_info['geometry']['body_type'] = rep.RepresentationType
                                                filled_info['geometry']['representation_count'] = len(element.Representation.Representations)
                                                
                                                for item in rep.Items:
                                                    item_type = item.is_a()
                                                    filled_info['geometry']['type'] = item_type
                                                    
                                                    if item_type == 'IfcExtrudedAreaSolid':
                                                        filled_info['geometry']['depth'] = float(item.Depth)
                                                        filled_info['geometry']['direction'] = list(item.ExtrudedDirection.DirectionRatios)
                                                        
                                                        # Extract position
                                                        if item.Position:
                                                            filled_info['geometry']['extrusion_position'] = list(item.Position.Location.Coordinates)
                                                            if item.Position.Axis:
                                                                filled_info['geometry']['extrusion_axis'] = list(item.Position.Axis.DirectionRatios)
                                                            if item.Position.RefDirection:
                                                                filled_info['geometry']['extrusion_ref_direction'] = list(item.Position.RefDirection.DirectionRatios)
                                                        
                                                        # Extract profile for shape detection
                                                        if item.SweptArea:
                                                            profile = item.SweptArea
                                                            filled_info['geometry']['profile_type'] = profile.is_a()
                                                            
                                                            if profile.is_a('IfcRectangleProfileDef'):
                                                                filled_info['geometry']['profile'] = {
                                                                    'type': 'rectangle',
                                                                    'width': float(profile.XDim),
                                                                    'height': float(profile.YDim)
                                                                }
                                                                filled_info['geometry']['shape'] = 'rectangular'
                                                            elif profile.is_a('IfcCircleProfileDef'):
                                                                filled_info['geometry']['profile'] = {
                                                                    'type': 'circle',
                                                                    'radius': float(profile.Radius)
                                                                }
                                                                filled_info['geometry']['shape'] = 'circular'
                                                            elif profile.is_a('IfcArbitraryClosedProfileDef'):
                                                                filled_info['geometry']['profile'] = {
                                                                    'type': 'arbitrary',
                                                                    'curve_type': profile.OuterCurve.is_a() if profile.OuterCurve else None
                                                                }
                                                                
                                                                # Analyze curve for circular pattern
                                                                if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                                                    points = []
                                                                    for point in profile.OuterCurve.Points:
                                                                        coords = list(point.Coordinates)
                                                                        points.append(coords)
                                                                    
                                                                    if points:
                                                                        filled_info['geometry']['profile']['point_count'] = len(points)
                                                                        
                                                                        # Simple circular detection (high point count + equal distances from center)
                                                                        if len(points) > 20:  # High tessellation suggests circular
                                                                            # Calculate centroid
                                                                            cx = sum(p[0] for p in points) / len(points)
                                                                            cy = sum(p[1] for p in points) / len(points)
                                                                            
                                                                            # Calculate distances from centroid
                                                                            distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points]
                                                                            avg_radius = sum(distances) / len(distances)
                                                                            radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                                            
                                                                            # If standard deviation is small relative to radius, likely circular
                                                                            if radius_std / avg_radius < 0.1:  # 10% tolerance
                                                                                filled_info['geometry']['shape'] = 'circular_tessellated'
                                                                                filled_info['geometry']['profile']['estimated_radius'] = avg_radius
                                                                                filled_info['geometry']['profile']['center'] = [cx, cy]
                                                                                filled_info['geometry']['profile']['radius_std_ratio'] = radius_std / avg_radius
                                                                            else:
                                                                                filled_info['geometry']['shape'] = 'complex'
                                                                                filled_info['geometry']['profile']['radius_std_ratio'] = radius_std / avg_radius
                                                                        else:
                                                                            filled_info['geometry']['shape'] = 'polygonal'
                                                                
                                                                # Handle IfcIndexedPolyCurve (parametric arcs)
                                                                elif profile.OuterCurve and profile.OuterCurve.is_a('IfcIndexedPolyCurve'):
                                                                    curve = profile.OuterCurve
                                                                    filled_info['geometry']['profile']['curve_type'] = 'IfcIndexedPolyCurve'
                                                                    
                                                                    # Check for arc segments
                                                                    if hasattr(curve, 'Segments') and curve.Segments:
                                                                        arc_count = sum(1 for seg in curve.Segments if hasattr(seg, 'is_a') and seg.is_a('IfcArcIndex'))
                                                                        filled_info['geometry']['profile']['arc_segments'] = arc_count
                                                                        filled_info['geometry']['profile']['total_segments'] = len(curve.Segments)
                                                                        
                                                                        if arc_count > 0:
                                                                            filled_info['geometry']['shape'] = 'circular_parametric'
                                                                            
                                                                            # Try to extract radius from arc segments
                                                                            if curve.Points and len(curve.Points.CoordList) >= 4:
                                                                                points = curve.Points.CoordList
                                                                                filled_info['geometry']['profile']['control_points'] = len(points)
                                                                                
                                                                                # For circular arcs, estimate radius from control points
                                                                                if len(points) >= 3:
                                                                                    p1, p2, p3 = points[0], points[1], points[2]
                                                                                    # Simple radius estimation from 3 points on circle
                                                                                    dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
                                                                                    dx2, dy2 = p3[0] - p2[0], p3[1] - p2[1]
                                                                                    
                                                                                    # Calculate approximate radius
                                                                                    chord1 = (dx1**2 + dy1**2)**0.5
                                                                                    chord2 = (dx2**2 + dy2**2)**0.5
                                                                                    filled_info['geometry']['profile']['estimated_radius'] = (chord1 + chord2) / 2
                                                                
                                                                # Add bounding box calculation for arbitrary profiles
                                                                if filled_info['geometry']['profile'].get('point_count', 0) > 0:
                                                                    points = []
                                                                    if profile.OuterCurve and profile.OuterCurve.is_a('IfcPolyline'):
                                                                        for point in profile.OuterCurve.Points:
                                                                            points.append(list(point.Coordinates))
                                                                    
                                                                    if points and len(points) >= 3:
                                                                        x_coords = [p[0] for p in points if len(p) >= 2]
                                                                        y_coords = [p[1] for p in points if len(p) >= 2]
                                                                        if x_coords and y_coords:
                                                                            filled_info['geometry']['profile']['width'] = max(x_coords) - min(x_coords)
                                                                            filled_info['geometry']['profile']['height'] = max(y_coords) - min(y_coords)
                                                                            filled_info['geometry']['profile']['center_x'] = (max(x_coords) + min(x_coords)) / 2
                                                                            filled_info['geometry']['profile']['center_y'] = (max(y_coords) + min(y_coords)) / 2
                                                    
                                                    elif item_type == 'IfcFacetedBrep':
                                                        # Handle tessellated mesh geometry (common for complex/circular windows)
                                                        filled_info['geometry']['mesh_type'] = 'IfcFacetedBrep'
                                                        
                                                        if hasattr(item, 'Outer') and item.Outer:
                                                            shell = item.Outer
                                                            if hasattr(shell, 'CfsFaces') and shell.CfsFaces:
                                                                face_count = len(shell.CfsFaces)
                                                                filled_info['geometry']['face_count'] = face_count
                                                                
                                                                # Collect all vertices to analyze shape
                                                                all_vertices = []
                                                                for face in shell.CfsFaces:
                                                                    if hasattr(face, 'Bounds'):
                                                                        for bound in face.Bounds:
                                                                            if hasattr(bound, 'Bound') and hasattr(bound.Bound, 'Polygon'):
                                                                                for point in bound.Bound.Polygon:
                                                                                    if hasattr(point, 'Coordinates'):
                                                                                        all_vertices.append(list(point.Coordinates))
                                                                
                                                                if all_vertices:
                                                                    filled_info['geometry']['vertex_count'] = len(all_vertices)
                                                                    
                                                                    # Analyze if this could be a circular window based on face/vertex count
                                                                    if face_count > 50:  # High face count suggests circular tessellation
                                                                        # Extract unique vertices (remove duplicates)
                                                                        unique_vertices = []
                                                                        for v in all_vertices:
                                                                            is_duplicate = False
                                                                            for uv in unique_vertices:
                                                                                if all(abs(v[i] - uv[i]) < 1e-6 for i in range(min(len(v), len(uv)))):
                                                                                    is_duplicate = True
                                                                                    break
                                                                            if not is_duplicate:
                                                                                unique_vertices.append(v)
                                                                        
                                                                        if unique_vertices and len(unique_vertices) > 10:
                                                                            # Project to 2D (assume extrusion along one axis)
                                                                            points_2d = [(v[0], v[1]) for v in unique_vertices if len(v) >= 2]
                                                                            
                                                                            if len(points_2d) > 10:
                                                                                # Calculate centroid and radius distribution
                                                                                cx = sum(p[0] for p in points_2d) / len(points_2d)
                                                                                cy = sum(p[1] for p in points_2d) / len(points_2d)
                                                                                
                                                                                distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points_2d]
                                                                                avg_radius = sum(distances) / len(distances)
                                                                                radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                                                
                                                                                filled_info['geometry']['estimated_radius'] = avg_radius
                                                                                filled_info['geometry']['radius_std_ratio'] = radius_std / avg_radius if avg_radius > 0 else 0
                                                                                filled_info['geometry']['center'] = [cx, cy]
                                                                                
                                                                                # Classify based on radius standard deviation
                                                                                if radius_std / avg_radius < 0.15:  # 15% tolerance for mesh
                                                                                    filled_info['geometry']['shape'] = 'circular_mesh'
                                                                                else:
                                                                                    filled_info['geometry']['shape'] = 'complex_mesh'
                                                                            else:
                                                                                filled_info['geometry']['shape'] = 'mesh_low_detail'
                                                            else:
                                                                filled_info['geometry']['shape'] = 'simple_mesh'
                                                                
                                                                # For simple meshes, still try to analyze overall shape
                                                                if all_vertices and len(all_vertices) > 4:
                                                                    # Extract unique vertices (remove duplicates) for basic analysis
                                                                    unique_vertices = []
                                                                    for v in all_vertices:
                                                                        is_duplicate = False
                                                                        for uv in unique_vertices:
                                                                            if all(abs(v[i] - uv[i]) < 1e-6 for i in range(min(len(v), len(uv)))):
                                                                                is_duplicate = True
                                                                                break
                                                                        if not is_duplicate:
                                                                            unique_vertices.append(v)
                                                                    
                                                                    if unique_vertices and len(unique_vertices) >= 4:
                                                                        # Project to 2D and check basic shape properties
                                                                        points_2d = [(v[0], v[1]) for v in unique_vertices if len(v) >= 2]
                                                                        
                                                                        if len(points_2d) >= 4:
                                                                            # Calculate bounding box aspect ratio
                                                                            x_coords = [p[0] for p in points_2d]
                                                                            y_coords = [p[1] for p in points_2d]
                                                                            
                                                                            if x_coords and y_coords:
                                                                                width = max(x_coords) - min(x_coords)
                                                                                height = max(y_coords) - min(y_coords)
                                                                                filled_info['geometry']['bounding_box'] = {
                                                                                    'width': width,
                                                                                    'height': height,
                                                                                    'aspect_ratio': width / height if height > 0 else 0
                                                                                }
                                                                                
                                                                                # Calculate centroid and radius distribution for shape hints
                                                                                cx = sum(x_coords) / len(x_coords)
                                                                                cy = sum(y_coords) / len(y_coords)
                                                                                
                                                                                distances = [((p[0]-cx)**2 + (p[1]-cy)**2)**0.5 for p in points_2d]
                                                                                avg_radius = sum(distances) / len(distances)
                                                                                radius_std = (sum((d - avg_radius)**2 for d in distances) / len(distances))**0.5
                                                                                
                                                                                filled_info['geometry']['shape_analysis'] = {
                                                                                    'center': [cx, cy],
                                                                                    'avg_radius': avg_radius,
                                                                                    'radius_std_ratio': radius_std / avg_radius if avg_radius > 0 else 0,
                                                                                    'unique_vertices': len(unique_vertices)
                                                                                }
                                                                                
                                                                                # Shape hints based on analysis
                                                                                aspect_ratio = width / height if height > 0 else 0
                                                                                radius_consistency = radius_std / avg_radius if avg_radius > 0 else 1
                                                                                
                                                                                if 0.8 <= aspect_ratio <= 1.2 and radius_consistency < 0.2:
                                                                                    filled_info['geometry']['shape_hint'] = 'likely_circular'
                                                                                elif 0.8 <= aspect_ratio <= 1.2:
                                                                                    filled_info['geometry']['shape_hint'] = 'likely_square'
                                                                                elif aspect_ratio > 1.5 or aspect_ratio < 0.67:
                                                                                    filled_info['geometry']['shape_hint'] = 'likely_rectangular'
                                                                                else:
                                                                                    filled_info['geometry']['shape_hint'] = 'irregular'
                                                    
                                                    elif item_type == 'IfcBooleanClippingResult':
                                                        # Handle boolean operations on windows/doors
                                                        filled_info['geometry']['boolean_type'] = 'IfcBooleanClippingResult'
                                                        filled_info['geometry']['shape'] = 'boolean_operation'
                                                    
                                                    else:
                                                        # Handle other geometry types
                                                        filled_info['geometry']['shape'] = f'unknown_{item_type}'
                                    
                                    filled_elements.append(filled_info)
                            opening_info['filled_by'] = filled_elements
                            
                            # Add to the list with a warning
                            info['openings'].append(opening_info)
                except Exception as e:
                    # If placement calculation fails, skip this opening
                    continue
    
    return info

def extract_wall_from_json(json_data: Dict, wall_name: str) -> Optional[Dict[str, Any]]:
    """Extract wall information from ifcJSON"""
    entities = json_data.get('data', [])
    entities_by_id = {e.get('globalId'): e for e in entities if e.get('globalId')}
    entities_by_ref = {str(i): e for i, e in enumerate(entities)}
    
    def resolve_ref(ref_obj):
        if isinstance(ref_obj, dict) and 'ref' in ref_obj:
            ref_id = ref_obj['ref']
            return entities_by_id.get(ref_id) or entities_by_ref.get(str(ref_id))
        return ref_obj
    
    def resolve_deep(ref_obj, max_depth=10):
        """Recursively resolve references"""
        current = ref_obj
        depth = 0
        while isinstance(current, dict) and 'ref' in current and depth < max_depth:
            ref_id = current['ref']
            current = entities_by_id.get(ref_id) or entities_by_ref.get(str(ref_id))
            if not current:
                break
            depth += 1
        return current
    
    # Find wall
    wall = None
    for entity in entities:
        if entity.get('name') == wall_name and entity.get('type') == 'IfcWallStandardCase':
            wall = entity
            break
    
    if not wall:
        return None
    
    info = {
        'globalId': wall.get('globalId'),
        'name': wall.get('name'),
        'type': wall.get('type'),
        'placement': {},
        'geometry': {},
        'openings': []
    }
    
    # Extract placement
    placement_ref = wall.get('objectPlacement')
    if placement_ref:
        placement = resolve_ref(placement_ref)
        if placement:
            # Traverse placement hierarchy to get final location
            current_placement = placement
            locations = []
            
            while current_placement:
                rel_placement = resolve_ref(current_placement.get('relativePlacement'))
                if rel_placement:
                    location = resolve_ref(rel_placement.get('location'))
                    if location and location.get('coordinates'):
                        locations.append(location.get('coordinates'))
                    
                    # Get axes
                    axis = resolve_ref(rel_placement.get('axis'))
                    ref_dir = resolve_ref(rel_placement.get('refDirection'))
                    
                    if len(locations) == 1:  # First level placement
                        info['placement']['location'] = location.get('coordinates')
                        if axis:
                            info['placement']['z_axis'] = axis.get('directionRatios')
                        if ref_dir:
                            info['placement']['x_axis'] = ref_dir.get('directionRatios')
                
                # Move to parent placement
                parent_ref = current_placement.get('placementRelTo')
                current_placement = resolve_ref(parent_ref) if parent_ref else None
    
    # Extract geometry
    repr_ref = wall.get('representation')
    if repr_ref:
        prod_def = resolve_deep(repr_ref)
        if prod_def:
            if prod_def.get('type') == 'IfcProductDefinitionShape':
                reps = prod_def.get('representations', [])
                info['geometry']['representation_count'] = len(reps)
            
                for rep_ref in reps:
                    shape_rep = resolve_deep(rep_ref)
                    if shape_rep:
                        rep_id = shape_rep.get('representationIdentifier', '')
                        rep_type = shape_rep.get('representationType', '')
                        
                        if rep_id == 'Body':
                            info['geometry']['body_type'] = rep_type
                            items = shape_rep.get('items', [])
                            
                            for item_ref in items:
                                item = resolve_deep(item_ref)
                                if item:
                                    item_type = item.get('type', '')
                                    
                                    if item_type == 'IfcExtrudedAreaSolid':
                                        info['geometry']['type'] = 'IfcExtrudedAreaSolid'
                                        info['geometry']['depth'] = item.get('depth')
                                        
                                    elif item_type == 'IfcBooleanClippingResult':
                                        # Extract the base solid (FirstOperand) - can be nested
                                        first_operand = item.get('firstOperand')
                                        
                                        if first_operand:
                                            # Handle nested boolean operations
                                            if first_operand.get('type') == 'IfcBooleanClippingResult':
                                                inner_operand = first_operand.get('firstOperand')
                                                if inner_operand and inner_operand.get('type') == 'IfcExtrudedAreaSolid':
                                                    info['geometry']['type'] = 'IfcExtrudedAreaSolid_from_nested_boolean'
                                                    info['geometry']['depth'] = inner_operand.get('depth')
                                                    item = inner_operand
                                            elif first_operand.get('type') == 'IfcExtrudedAreaSolid':
                                                info['geometry']['type'] = 'IfcExtrudedAreaSolid_from_boolean'
                                                info['geometry']['depth'] = first_operand.get('depth')
                                                item = first_operand
                                    
                                    # Extract geometry details from the extrusion (regardless of boolean or direct)
                                    if info['geometry'].get('type', '').startswith('IfcExtrudedAreaSolid'):
                                        # Extrusion direction
                                        ext_dir_ref = item.get('extrudedDirection')
                                        if ext_dir_ref:
                                            ext_dir = resolve_deep(ext_dir_ref)
                                            if ext_dir and ext_dir.get('type') == 'IfcDirection':
                                                info['geometry']['direction'] = ext_dir.get('directionRatios')
                                        
                                        # Position (for extrusion placement)
                                        position_ref = item.get('position')
                                        if position_ref:
                                            position = resolve_deep(position_ref)
                                            if position and position.get('type') == 'IfcAxis2Placement3D':
                                                # Get location
                                                loc_ref = position.get('location')
                                                if loc_ref:
                                                    loc = resolve_deep(loc_ref)
                                                    if loc and loc.get('type') == 'IfcCartesianPoint':
                                                        info['geometry']['extrusion_position'] = loc.get('coordinates')
                                                
                                                # Get axis (local Z)
                                                axis_ref = position.get('axis')
                                                if axis_ref:
                                                    axis = resolve_deep(axis_ref)
                                                    if axis and axis.get('type') == 'IfcDirection':
                                                        info['geometry']['extrusion_axis'] = axis.get('directionRatios')
                                                
                                                # Get refDirection (local X)
                                                ref_dir_ref = position.get('refDirection')
                                                if ref_dir_ref:
                                                    ref_dir = resolve_deep(ref_dir_ref)
                                                    if ref_dir and ref_dir.get('type') == 'IfcDirection':
                                                        info['geometry']['extrusion_ref_direction'] = ref_dir.get('directionRatios')
                                        
                                        # Profile extraction (moved inside extrusion block)
                                        swept_area_ref = item.get('sweptArea')
                                        if swept_area_ref:
                                            swept_area = resolve_deep(swept_area_ref)
                                            if swept_area:
                                                info['geometry']['profile_type'] = swept_area.get('type')
                                                
                                                if swept_area.get('type') == 'IfcRectangleProfileDef':
                                                    info['geometry']['profile'] = {
                                                        'type': 'rectangle',
                                                        'width': swept_area.get('xDim'),
                                                        'height': swept_area.get('yDim')
                                                    }
                                                elif swept_area.get('type') == 'IfcArbitraryClosedProfileDef':
                                                    curve_ref = swept_area.get('outerCurve')
                                                    if curve_ref:
                                                        curve = resolve_deep(curve_ref)
                                                        info['geometry']['profile'] = {
                                                            'type': 'arbitrary',
                                                            'curve_type': curve.get('type') if curve else None
                                                        }
                                                        
                                                        # Extract polyline points if available
                                                        if curve and curve.get('type') == 'IfcPolyline':
                                                            points = []
                                                            for point_ref in curve.get('points', []):
                                                                point = resolve_deep(point_ref)
                                                                if point and point.get('type') == 'IfcCartesianPoint':
                                                                    coords = point.get('coordinates', [])
                                                                    points.append(coords)
                                                            
                                                            if points:
                                                                info['geometry']['profile']['point_count'] = len(points)
                                                                # Calculate bounding box
                                                                if len(points) >= 3:
                                                                    x_coords = [p[0] for p in points if len(p) >= 2]
                                                                    y_coords = [p[1] for p in points if len(p) >= 2]
                                                                    if x_coords and y_coords:
                                                                        info['geometry']['profile']['width'] = max(x_coords) - min(x_coords)
                                                                        info['geometry']['profile']['height'] = max(y_coords) - min(y_coords)
    
    # Extract openings
    # Method 1: Through void relationships (primary method)
    for entity in entities:
        if entity.get('type') == 'IfcRelVoidsElement':
            relating_ref = entity.get('relatingBuildingElement')
            if relating_ref:
                relating = resolve_deep(relating_ref)
                if relating and relating.get('globalId') == wall.get('globalId'):
                    opening_ref = entity.get('relatedOpeningElement')
                    if opening_ref:
                        opening = resolve_deep(opening_ref)
                        if opening:
                            opening_info = {
                                'globalId': opening.get('globalId'),
                                'name': opening.get('name', 'Unnamed'),
                                'type': opening.get('type'),
                                'found_via': 'IfcRelVoidsElement'
                            }
                            info['openings'].append(opening_info)
    
    # Method 2: Direct search for IfcOpeningElement (backup method)
    found_opening_ids = {o['globalId'] for o in info['openings']}
    
    for entity in entities:
        if entity.get('type') == 'IfcOpeningElement':
            opening_id = entity.get('globalId')
            if opening_id not in found_opening_ids:
                # This is an opening not found through relationships
                opening_info = {
                    'globalId': opening_id,
                    'name': entity.get('name', 'Unnamed'),
                    'type': entity.get('type'),
                    'found_via': 'Direct_IfcOpeningElement_search',
                    'warning': 'Found via direct search - may not be properly linked to this wall'
                }
                info['openings'].append(opening_info)
    
    return info

def compare_vectors(v1: List[float], v2: List[float], tolerance: float = 1e-6) -> Tuple[bool, float]:
    """Compare two vectors and return if they match within tolerance"""
    if not v1 or not v2 or len(v1) != len(v2):
        return False, float('inf')
    
    diff = np.linalg.norm(np.array(v1) - np.array(v2))
    return diff < tolerance, diff

def compare_walls(wall1: Dict[str, Any], wall2: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two wall structures"""
    comparison = {
        'placement': {},
        'geometry': {},
        'openings': {}
    }
    
    # Compare placement
    if wall1.get('placement') and wall2.get('placement'):
        loc1 = wall1['placement'].get('location', [])
        loc2 = wall2['placement'].get('location', [])
        
        if loc1 and loc2:
            match, diff = compare_vectors(loc1, loc2)
            comparison['placement']['location'] = {
                'file1': loc1,
                'file2': loc2,
                'match': match,
                'difference': diff
            }
        
        # Compare axes
        for axis in ['x_axis', 'y_axis', 'z_axis']:
            if axis in wall1['placement'] and axis in wall2['placement']:
                v1 = wall1['placement'][axis]
                v2 = wall2['placement'][axis]
                match, diff = compare_vectors(v1, v2)
                comparison['placement'][axis] = {
                    'file1': v1,
                    'file2': v2,
                    'match': match,
                    'difference': diff
                }
    
    # Compare geometry
    if wall1.get('geometry') and wall2.get('geometry'):
        # Extrusion depth
        depth1 = wall1['geometry'].get('depth')
        depth2 = wall2['geometry'].get('depth')
        if depth1 is not None and depth2 is not None:
            comparison['geometry']['depth'] = {
                'file1': depth1,
                'file2': depth2,
                'match': abs(depth1 - depth2) < 1e-6,
                'difference': abs(depth1 - depth2)
            }
        
        # Extrusion direction
        dir1 = wall1['geometry'].get('direction', [])
        dir2 = wall2['geometry'].get('direction', [])
        if dir1 and dir2:
            match, diff = compare_vectors(dir1, dir2)
            comparison['geometry']['direction'] = {
                'file1': dir1,
                'file2': dir2,
                'match': match,
                'difference': diff
            }
        
        # Extrusion position
        pos1 = wall1['geometry'].get('extrusion_position', [])
        pos2 = wall2['geometry'].get('extrusion_position', [])
        if pos1 and pos2:
            match, diff = compare_vectors(pos1, pos2)
            comparison['geometry']['extrusion_position'] = {
                'file1': pos1,
                'file2': pos2,
                'match': match,
                'difference': diff
            }
        
        # Extrusion axis (local Z)
        axis1 = wall1['geometry'].get('extrusion_axis', [])
        axis2 = wall2['geometry'].get('extrusion_axis', [])
        if axis1 and axis2:
            match, diff = compare_vectors(axis1, axis2)
            comparison['geometry']['extrusion_axis'] = {
                'file1': axis1,
                'file2': axis2,
                'match': match,
                'difference': diff
            }
        
        # Extrusion reference direction (local X)
        ref1 = wall1['geometry'].get('extrusion_ref_direction', [])
        ref2 = wall2['geometry'].get('extrusion_ref_direction', [])
        if ref1 and ref2:
            match, diff = compare_vectors(ref1, ref2)
            comparison['geometry']['extrusion_ref_direction'] = {
                'file1': ref1,
                'file2': ref2,
                'match': match,
                'difference': diff
            }
        
        # Profile
        profile1 = wall1['geometry'].get('profile', {})
        profile2 = wall2['geometry'].get('profile', {})
        if profile1.get('type') == 'rectangle' and profile2.get('type') == 'rectangle':
            comparison['geometry']['profile'] = {
                'width': {
                    'file1': profile1.get('width'),
                    'file2': profile2.get('width'),
                    'match': abs(profile1.get('width', 0) - profile2.get('width', 0)) < 1e-6
                },
                'height': {
                    'file1': profile1.get('height'),
                    'file2': profile2.get('height'),
                    'match': abs(profile1.get('height', 0) - profile2.get('height', 0)) < 1e-6
                }
            }
    
    # Compare openings
    openings1 = {o['globalId']: o for o in wall1.get('openings', [])}
    openings2 = {o['globalId']: o for o in wall2.get('openings', [])}
    
    comparison['openings']['count'] = {
        'file1': len(openings1),
        'file2': len(openings2),
        'match': len(openings1) == len(openings2)
    }
    
    comparison['openings']['only_in_file1'] = list(set(openings1.keys()) - set(openings2.keys()))
    comparison['openings']['only_in_file2'] = list(set(openings2.keys()) - set(openings1.keys()))
    comparison['openings']['in_both'] = list(set(openings1.keys()) & set(openings2.keys()))
    
    # Compare opening details by name (since GlobalIds change)
    openings1_by_name = {o['name']: o for o in wall1.get('openings', [])}
    openings2_by_name = {o['name']: o for o in wall2.get('openings', [])}
    
    comparison['openings']['detailed_comparison'] = {}
    all_opening_names = set(openings1_by_name.keys()) | set(openings2_by_name.keys())
    
    for name in all_opening_names:
        opening1 = openings1_by_name.get(name)
        opening2 = openings2_by_name.get(name)
        
        opening_comp = {
            'in_file1': opening1 is not None,
            'in_file2': opening2 is not None,
            'name': name
        }
        
        if opening1 and opening2:
            # Compare placement
            if 'placement' in opening1 and 'placement' in opening2:
                loc1 = opening1['placement'].get('location', [])
                loc2 = opening2['placement'].get('location', [])
                if loc1 and loc2:
                    match, diff = compare_vectors(loc1, loc2)
                    opening_comp['placement'] = {
                        'location_match': match,
                        'location_diff': diff,
                        'location1': loc1,
                        'location2': loc2
                    }
            
            # Compare geometry
            if 'geometry' in opening1 and 'geometry' in opening2:
                geom1 = opening1['geometry']
                geom2 = opening2['geometry']
                
                opening_comp['geometry'] = {}
                
                # Compare shape
                shape1 = geom1.get('shape', 'unknown')
                shape2 = geom2.get('shape', 'unknown')
                opening_comp['geometry']['shape'] = {
                    'file1': shape1,
                    'file2': shape2,
                    'match': shape1 == shape2
                }
                
                # Compare dimensions
                if 'profile' in geom1 and 'profile' in geom2:
                    profile1 = geom1['profile']
                    profile2 = geom2['profile']
                    
                    if profile1.get('type') == 'rectangle' and profile2.get('type') == 'rectangle':
                        opening_comp['geometry']['profile'] = {
                            'type': 'rectangle',
                            'width_match': abs(profile1.get('width', 0) - profile2.get('width', 0)) < 1e-6,
                            'height_match': abs(profile1.get('height', 0) - profile2.get('height', 0)) < 1e-6,
                            'width1': profile1.get('width'),
                            'width2': profile2.get('width'),
                            'height1': profile1.get('height'),
                            'height2': profile2.get('height')
                        }
                    elif profile1.get('type') == 'circle' and profile2.get('type') == 'circle':
                        opening_comp['geometry']['profile'] = {
                            'type': 'circle',
                            'radius_match': abs(profile1.get('radius', 0) - profile2.get('radius', 0)) < 1e-6,
                            'radius1': profile1.get('radius'),
                            'radius2': profile2.get('radius')
                        }
                    elif 'estimated_radius' in profile1 and 'estimated_radius' in profile2:
                        opening_comp['geometry']['profile'] = {
                            'type': 'circular_tessellated',
                            'radius_match': abs(profile1.get('estimated_radius', 0) - profile2.get('estimated_radius', 0)) < 1e-3,
                            'radius1': profile1.get('estimated_radius'),
                            'radius2': profile2.get('estimated_radius'),
                            'points1': profile1.get('point_count'),
                            'points2': profile2.get('point_count')
                        }
                
                # Compare extrusion depth
                depth1 = geom1.get('depth')
                depth2 = geom2.get('depth')
                if depth1 is not None and depth2 is not None:
                    opening_comp['geometry']['depth'] = {
                        'match': abs(depth1 - depth2) < 1e-6,
                        'diff': abs(depth1 - depth2),
                        'depth1': depth1,
                        'depth2': depth2
                    }
        
        comparison['openings']['detailed_comparison'][name] = opening_comp
    
    return comparison

def format_comparison(wall_name: str, file1: str, file2: str, 
                     wall1: Optional[Dict], wall2: Optional[Dict],
                     comparison: Optional[Dict]) -> None:
    """Format and print comparison results"""
    print(f"\n{'='*80}")
    print(f"WALL COMPARISON: {wall_name}")
    print(f"{'='*80}")
    print(f"File 1: {file1}")
    print(f"File 2: {file2}")
    print()
    
    if not wall1:
        print(f"❌ Wall '{wall_name}' not found in File 1")
        return
    if not wall2:
        print(f"❌ Wall '{wall_name}' not found in File 2")
        return
    
    print(f"✅ Wall found in both files")
    print(f"   GlobalId 1: {wall1['globalId']}")
    print(f"   GlobalId 2: {wall2['globalId']}")
    
    if not comparison:
        return
    
    # Placement comparison
    print(f"\n📍 PLACEMENT COMPARISON")
    print("-" * 40)
    
    if 'location' in comparison['placement']:
        loc = comparison['placement']['location']
        print(f"Location:")
        print(f"  File 1: {loc['file1']}")
        print(f"  File 2: {loc['file2']}")
        print(f"  Match: {'✅' if loc['match'] else '❌'} (diff: {loc['difference']:.6f})")
    
    for axis in ['x_axis', 'y_axis', 'z_axis']:
        if axis in comparison['placement']:
            ax = comparison['placement'][axis]
            print(f"\n{axis.upper()}:")
            print(f"  File 1: {ax['file1']}")
            print(f"  File 2: {ax['file2']}")
            print(f"  Match: {'✅' if ax['match'] else '❌'} (diff: {ax['difference']:.6f})")
    
    # Geometry comparison
    print(f"\n📐 GEOMETRY COMPARISON")
    print("-" * 40)
    
    if 'depth' in comparison['geometry']:
        depth = comparison['geometry']['depth']
        print(f"Extrusion Depth:")
        print(f"  File 1: {depth['file1']}")
        print(f"  File 2: {depth['file2']}")
        print(f"  Match: {'✅' if depth['match'] else '❌'} (diff: {depth['difference']:.6f})")
    
    if 'direction' in comparison['geometry']:
        direction = comparison['geometry']['direction']
        print(f"\nExtrusion Direction:")
        print(f"  File 1: {direction['file1']}")
        print(f"  File 2: {direction['file2']}")
        print(f"  Match: {'✅' if direction['match'] else '❌'} (diff: {direction['difference']:.6f})")
    
    if 'extrusion_position' in comparison['geometry']:
        pos = comparison['geometry']['extrusion_position']
        print(f"\nExtrusion Position (Local Origin):")
        print(f"  File 1: {pos['file1']}")
        print(f"  File 2: {pos['file2']}")
        print(f"  Match: {'✅' if pos['match'] else '❌'} (diff: {pos['difference']:.6f})")
    
    if 'extrusion_axis' in comparison['geometry']:
        axis = comparison['geometry']['extrusion_axis']
        print(f"\nExtrusion Axis (Local Z):")
        print(f"  File 1: {axis['file1']}")
        print(f"  File 2: {axis['file2']}")
        print(f"  Match: {'✅' if axis['match'] else '❌'} (diff: {axis['difference']:.6f})")
    
    if 'extrusion_ref_direction' in comparison['geometry']:
        ref_dir = comparison['geometry']['extrusion_ref_direction']
        print(f"\nExtrusion Ref Direction (Local X):")
        print(f"  File 1: {ref_dir['file1']}")
        print(f"  File 2: {ref_dir['file2']}")
        print(f"  Match: {'✅' if ref_dir['match'] else '❌'} (diff: {ref_dir['difference']:.6f})")
    
    if 'profile' in comparison['geometry']:
        profile = comparison['geometry']['profile']
        if 'width' in profile:
            print(f"\nProfile Width:")
            print(f"  File 1: {profile['width']['file1']}")
            print(f"  File 2: {profile['width']['file2']}")
            print(f"  Match: {'✅' if profile['width']['match'] else '❌'}")
        if 'height' in profile:
            print(f"\nProfile Height:")
            print(f"  File 1: {profile['height']['file1']}")
            print(f"  File 2: {profile['height']['file2']}")
            print(f"  Match: {'✅' if profile['height']['match'] else '❌'}")
    
    # Profile comparison (including arbitrary profiles)
    profile1 = wall1['geometry'].get('profile', {})
    profile2 = wall2['geometry'].get('profile', {})
    if profile1.get('type') == 'arbitrary' and profile2.get('type') == 'arbitrary':
        print(f"\nProfile Details:")
        print(f"  File 1: {profile1.get('curve_type')} ({profile1.get('point_count', 0)} points)")
        print(f"  File 2: {profile2.get('curve_type')} ({profile2.get('point_count', 0)} points)")
        if 'width' in profile1 and 'width' in profile2:
            print(f"  Width 1: {profile1['width']:.3f}, Width 2: {profile2['width']:.3f}")
        if 'height' in profile1 and 'height' in profile2:
            print(f"  Height 1: {profile1['height']:.3f}, Height 2: {profile2['height']:.3f}")
    
    # Openings comparison
    print(f"\n🚪 OPENINGS COMPARISON")
    print("-" * 40)
    
    if 'count' in comparison['openings']:
        count = comparison['openings']['count']
        print(f"Opening Count:")
        print(f"  File 1: {count['file1']}")
        print(f"  File 2: {count['file2']}")
        print(f"  Match: {'✅' if count['match'] else '❌'}")
        
        if comparison['openings']['only_in_file1']:
            print(f"\nOnly in File 1:")
            for gid in comparison['openings']['only_in_file1']:
                print(f"  - {gid}")
        
        if comparison['openings']['only_in_file2']:
            print(f"\nOnly in File 2:")
            for gid in comparison['openings']['only_in_file2']:
                print(f"  - {gid}")
    
    # Show opening detection methods
    print(f"\n🔍 OPENING DETECTION METHODS")
    print("-" * 40)
    if wall1 and wall1.get('openings'):
        print(f"File 1 openings:")
        for opening in wall1['openings']:
            method = opening.get('found_via', 'unknown')
            name = opening.get('name', 'Unnamed')
            print(f"  • {name}: {method}")
            if 'warning' in opening:
                print(f"    ⚠️  {opening['warning']}")
    
    if wall2 and wall2.get('openings'):
        print(f"File 2 openings:")
        for opening in wall2['openings']:
            method = opening.get('found_via', 'unknown')
            name = opening.get('name', 'Unnamed')
            print(f"  • {name}: {method}")
            if 'warning' in opening:
                print(f"    ⚠️  {opening['warning']}")
    
    # Detailed opening comparison
    if 'detailed_comparison' in comparison['openings']:
        detailed = comparison['openings']['detailed_comparison']
        if detailed:
            print(f"\n🔍 DETAILED OPENING ANALYSIS")
            print("=" * 50)
            
            for name, opening_comp in detailed.items():
                print(f"\n📋 Opening: {name}")
                print("-" * 30)
                
                if opening_comp['in_file1'] and opening_comp['in_file2']:
                    print("✅ Present in both files")
                    
                    # Placement comparison
                    if 'placement' in opening_comp:
                        placement = opening_comp['placement']
                        print(f"📍 Location: {'✅' if placement['location_match'] else '❌'}")
                        if not placement['location_match']:
                            print(f"  File 1: {placement['location1']}")
                            print(f"  File 2: {placement['location2']}")
                            print(f"  Difference: {placement['location_diff']:.6f}")
                    
                    # Geometry comparison
                    if 'geometry' in opening_comp:
                        geom = opening_comp['geometry']
                        
                        # Shape comparison
                        if 'shape' in geom:
                            shape = geom['shape']
                            print(f"🔺 Shape: {'✅' if shape['match'] else '❌'}")
                            print(f"  File 1: {shape['file1']}")
                            print(f"  File 2: {shape['file2']}")
                        
                        # Profile comparison
                        if 'profile' in geom:
                            profile = geom['profile']
                            profile_type = profile.get('type', 'unknown')
                            
                            if profile_type == 'rectangle':
                                print(f"📐 Rectangle Profile:")
                                print(f"  Width: {'✅' if profile['width_match'] else '❌'} ({profile['width1']:.3f} vs {profile['width2']:.3f})")
                                print(f"  Height: {'✅' if profile['height_match'] else '❌'} ({profile['height1']:.3f} vs {profile['height2']:.3f})")
                            
                            elif profile_type == 'circle':
                                print(f"⭕ Circle Profile:")
                                print(f"  Radius: {'✅' if profile['radius_match'] else '❌'} ({profile['radius1']:.3f} vs {profile['radius2']:.3f})")
                            
                            elif profile_type == 'circular_tessellated':
                                print(f"⭕ Tessellated Circle Profile:")
                                print(f"  Radius: {'✅' if profile['radius_match'] else '❌'} ({profile['radius1']:.3f} vs {profile['radius2']:.3f})")
                                print(f"  Points: {profile['points1']} vs {profile['points2']}")
                        
                        # Depth comparison
                        if 'depth' in geom:
                            depth = geom['depth']
                            print(f"📏 Extrusion Depth: {'✅' if depth['match'] else '❌'}")
                            if not depth['match']:
                                print(f"  File 1: {depth['depth1']:.3f}")
                                print(f"  File 2: {depth['depth2']:.3f}")
                                print(f"  Difference: {depth['diff']:.6f}")
                
                elif opening_comp['in_file1']:
                    print("❌ Only in File 1")
                elif opening_comp['in_file2']:
                    print("❌ Only in File 2")

def analyze_single_wall(file_path: str, wall_name: str) -> None:
    """Analyze a single wall in one file"""
    print(f"\n{'='*80}")
    print(f"SINGLE WALL ANALYSIS: {wall_name}")
    print(f"{'='*80}")
    print(f"File: {file_path}")
    print()
    
    try:
        # Load file
        data, file_format = load_file(file_path)
        
        # Extract wall information
        if file_format == 'ifc':
            wall = extract_wall_from_ifc(data, wall_name)
        else:
            wall = extract_wall_from_json(data, wall_name)
        
        if not wall:
            print(f"❌ Wall '{wall_name}' not found in file")
            return
        
        print(f"✅ Wall found: {wall['name']} (ID: {wall['globalId']})")
        print(f"   Type: {wall['type']}")
        
        # Display placement
        if wall.get('placement'):
            placement = wall['placement']
            print(f"\n📍 PLACEMENT INFORMATION")
            print("-" * 40)
            if 'location' in placement:
                print(f"Location: {placement['location']}")
            if 'x_axis' in placement:
                print(f"X-Axis: {placement['x_axis']}")
            if 'y_axis' in placement:
                print(f"Y-Axis: {placement['y_axis']}")
            if 'z_axis' in placement:
                print(f"Z-Axis: {placement['z_axis']}")
        
        # Display geometry
        if wall.get('geometry'):
            geometry = wall['geometry']
            print(f"\n📐 GEOMETRY INFORMATION")
            print("-" * 40)
            
            if 'type' in geometry:
                print(f"Geometry Type: {geometry['type']}")
            if 'body_type' in geometry:
                print(f"Body Type: {geometry['body_type']}")
            if 'depth' in geometry:
                print(f"Extrusion Depth: {geometry['depth']}")
            if 'direction' in geometry:
                print(f"Extrusion Direction: {geometry['direction']}")
            if 'extrusion_position' in geometry:
                print(f"Extrusion Position: {geometry['extrusion_position']}")
            if 'extrusion_axis' in geometry:
                print(f"Extrusion Axis (Local Z): {geometry['extrusion_axis']}")
            if 'extrusion_ref_direction' in geometry:
                print(f"Extrusion Ref Direction (Local X): {geometry['extrusion_ref_direction']}")
            
            # Profile information
            if 'profile' in geometry:
                profile = geometry['profile']
                print(f"\nProfile Type: {geometry.get('profile_type', 'Unknown')}")
                
                if profile.get('type') == 'rectangle':
                    print(f"  Rectangle: {profile['width']} × {profile['height']}")
                elif profile.get('type') == 'arbitrary':
                    print(f"  Arbitrary: {profile.get('curve_type', 'Unknown')} curve")
                    if 'point_count' in profile:
                        print(f"  Points: {profile['point_count']}")
                    if 'width' in profile and 'height' in profile:
                        print(f"  Bounding Box: {profile['width']:.3f} × {profile['height']:.3f}")
        
        # Display openings
        if wall.get('openings'):
            openings = wall['openings']
            print(f"\n🚪 OPENINGS ANALYSIS ({len(openings)} found)")
            print("=" * 50)
            
            for i, opening in enumerate(openings, 1):
                print(f"\n📋 Opening {i}: {opening.get('name', 'Unnamed')}")
                print("-" * 30)
                print(f"   GlobalId: {opening.get('globalId', 'Unknown')}")
                print(f"   Type: {opening.get('type', 'Unknown')}")
                print(f"   Detection: {opening.get('found_via', 'Unknown')}")
                
                if 'warning' in opening:
                    print(f"   ⚠️  {opening['warning']}")
                
                # Placement
                if 'placement' in opening and opening['placement']:
                    placement = opening['placement']
                    if 'location' in placement:
                        print(f"   Location: {placement['location']}")
                
                # Geometry
                if 'geometry' in opening and opening['geometry']:
                    geom = opening['geometry']
                    
                    if 'shape' in geom:
                        print(f"   Shape: {geom['shape']}")
                    
                    if 'depth' in geom:
                        print(f"   Extrusion Depth: {geom['depth']}")
                    
                    if 'profile' in geom:
                        profile = geom['profile']
                        profile_type = profile.get('type', 'unknown')
                        
                        if profile_type == 'rectangle':
                            print(f"   📐 Rectangle: {profile.get('width', 0):.3f} × {profile.get('height', 0):.3f}")
                        elif profile_type == 'circle':
                            print(f"   ⭕ Circle: radius {profile.get('radius', 0):.3f}")
                        elif 'estimated_radius' in profile:
                            print(f"   ⭕ Tessellated Circle: radius {profile.get('estimated_radius', 0):.3f}")
                            print(f"      Points: {profile.get('point_count', 0)}")
                            if 'center' in profile:
                                print(f"      Center: {profile['center']}")
                
                # Filled elements with DETAILED GEOMETRY
                if 'filled_by' in opening and opening['filled_by']:
                    print(f"   🔧 Filled by:")
                    for element in opening['filled_by']:
                        print(f"      • {element['name']} ({element['type']})")
                        
                        # Show filled element geometry details
                        if 'geometry' in element and element['geometry']:
                            geom = element['geometry']
                            if 'shape' in geom:
                                print(f"        🎯 Shape: {geom['shape']}")
                            
                            if 'type' in geom:
                                print(f"        📦 Geometry: {geom['type']}")
                            
                            if 'depth' in geom:
                                print(f"        📏 Depth: {geom['depth']:.3f}")
                            
                            if 'profile' in geom:
                                profile = geom['profile']
                                profile_type = profile.get('type', 'unknown')
                                
                                if profile_type == 'rectangle':
                                    print(f"        📐 Window Profile: {profile.get('width', 0):.3f} × {profile.get('height', 0):.3f}")
                                elif profile_type == 'circle':
                                    print(f"        ⭕ Window Profile: radius {profile.get('radius', 0):.3f}")
                                elif 'estimated_radius' in profile:
                                    print(f"        ⭕ Window Profile: tessellated circle, radius {profile.get('estimated_radius', 0):.3f}")
                                    print(f"           Points: {profile.get('point_count', 0)}")
                            
                            # Show mesh analysis for IfcFacetedBrep
                            if geom.get('type') == 'IfcFacetedBrep':
                                if 'face_count' in geom:
                                    print(f"        📊 Mesh: {geom['face_count']} faces")
                                if 'vertex_count' in geom:
                                    print(f"        📊 Vertices: {geom['vertex_count']} total")
                                
                                # Show enhanced shape analysis
                                if 'shape_hint' in geom:
                                    print(f"        🔍 Shape Analysis: {geom['shape_hint']}")
                                
                                if 'bounding_box' in geom:
                                    bbox = geom['bounding_box']
                                    print(f"        📏 Bounding Box: {bbox.get('width', 0):.3f} × {bbox.get('height', 0):.3f}")
                                    print(f"        📊 Aspect Ratio: {bbox.get('aspect_ratio', 0):.2f}")
                                
                                if 'shape_analysis' in geom:
                                    analysis = geom['shape_analysis']
                                    print(f"        🎯 Radius Consistency: {analysis.get('radius_std_ratio', 0):.3f}")
                                    print(f"        📍 Unique Vertices: {analysis.get('unique_vertices', 0)}")
                            
                            # Highlight geometry mismatch with opening
                            opening_shape = opening.get('geometry', {}).get('shape', 'unknown')
                            filled_shape = geom.get('shape', 'unknown')
                            if opening_shape != 'unknown' and filled_shape != 'unknown':
                                if 'circular' in opening_shape and 'rectangular' in filled_shape:
                                    print(f"        ⚠️  MISMATCH: Opening is {opening_shape} but window is {filled_shape}")
                                elif 'rectangular' in opening_shape and 'circular' in filled_shape:
                                    print(f"        ⚠️  MISMATCH: Opening is {opening_shape} but window is {filled_shape}")
                        else:
                            print(f"        ❌ No geometry information available")
        else:
            print(f"\n🚪 OPENINGS: None found")
        
        # Summary
        print(f"\n📊 SUMMARY")
        print("=" * 20)
        geometry_count = 1 if wall.get('geometry') else 0
        opening_count = len(wall.get('openings', []))
        print(f"✅ Wall geometry: {'Found' if geometry_count else 'Not found'}")
        print(f"🚪 Openings: {opening_count} found")
        
        if opening_count > 0:
            method_counts = {}
            for opening in wall['openings']:
                method = opening.get('found_via', 'Unknown')
                method_counts[method] = method_counts.get(method, 0) + 1
            
            print(f"   Detection methods:")
            for method, count in method_counts.items():
                print(f"   • {method}: {count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage:")
        print("  Single file analysis:")
        print("    python compare_wall_dimensions.py <file> <wall_name>")
        print("  Two file comparison:")
        print("    python compare_wall_dimensions.py <file1> <file2> <wall_name>")
        print()
        print("Examples:")
        print("  python compare_wall_dimensions.py input/OrangeHouse.ifc \"Wand-Ext-OG-1\"")
        print("  python compare_wall_dimensions.py original.ifc roundtrip.ifc \"Wand-Ext-OG-3\"")
        sys.exit(1)
    
    if len(sys.argv) == 3:
        # Single file analysis
        file_path = sys.argv[1]
        wall_name = sys.argv[2]
        analyze_single_wall(file_path, wall_name)
        return
    
    # Two file comparison (existing functionality)
    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    wall_name = sys.argv[3]
    
    try:
        # Load files
        data1, format1 = load_file(file1_path)
        data2, format2 = load_file(file2_path)
        
        # Extract wall information
        if format1 == 'ifc':
            wall1 = extract_wall_from_ifc(data1, wall_name)
        else:
            wall1 = extract_wall_from_json(data1, wall_name)
        
        if format2 == 'ifc':
            wall2 = extract_wall_from_ifc(data2, wall_name)
        else:
            wall2 = extract_wall_from_json(data2, wall_name)
        
        # Compare walls
        if wall1 and wall2:
            comparison = compare_walls(wall1, wall2)
        else:
            comparison = None
        
        # Format and display results
        format_comparison(wall_name, file1_path, file2_path, wall1, wall2, comparison)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()