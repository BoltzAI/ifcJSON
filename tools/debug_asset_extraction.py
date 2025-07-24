#!/usr/bin/env python3
"""
Debug Asset Extraction and Recreation

Traces the asset extraction process (Step 2) and recreation process (Step 3)
to identify where Body-Brep geometry is lost or converted to other types.

This tool specifically helps debug TODO #70 by showing:
1. What geometry types are extracted into assets
2. What geometry types are recreated from assets  
3. Where the conversion/loss occurs
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

def load_json_data(file_path: str) -> List[Dict[str, Any]]:
    """Load entities from JSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data.get('data', [])

def load_simplified_data(file_path: str) -> Dict[str, Any]:
    """Load simplified JSON data"""
    with open(file_path, 'r') as f:
        return json.load(f)

def find_element_by_name(entities: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Find element by name"""
    for entity in entities:
        if entity.get('name') == name:
            return entity
    return None

def find_element_by_id(entities: List[Dict[str, Any]], global_id: str) -> Optional[Dict[str, Any]]:
    """Find element by GlobalId"""
    for entity in entities:
        if entity.get('globalId') == global_id:
            return entity
    return None

def analyze_element_asset_flow(step1_entities: List[Dict[str, Any]], 
                               simplified_data: Dict[str, Any],
                               step3_entities: List[Dict[str, Any]],
                               assets_dir: str,
                               element_name: str) -> None:
    """Trace an element through the asset extraction and recreation flow"""
    
    print(f"🔍 ASSET FLOW ANALYSIS: {element_name}")
    print("="*70)
    
    # Step 1: Find element in original ifcJSON
    step1_element = find_element_by_name(step1_entities, element_name)
    if not step1_element:
        print(f"❌ Element '{element_name}' not found in Step 1")
        return
    
    element_id = step1_element.get('globalId')
    element_type = step1_element.get('type')
    
    print(f"✅ Step 1 Element: {element_name} ({element_type})")
    print(f"   GlobalId: {element_id}")
    
    # Analyze Step 1 geometry
    step1_geometry = analyze_element_geometry(step1_entities, step1_element, "STEP 1 (Original)")
    
    # Step 2: Find element in simplified JSON and trace to asset
    simplified_element, asset_id = find_element_in_simplified(simplified_data, element_id)
    if not simplified_element:
        print(f"❌ Element not found in simplified JSON")
        return
        
    print(f"✅ Step 2 Simplified: Found element with asset {asset_id}")
    
    # Analyze asset content
    asset_path = Path(assets_dir) / f"{asset_id}.json" 
    if not asset_path.exists():
        print(f"❌ Asset file not found: {asset_path}")
        return
        
    asset_geometry = analyze_asset_geometry(str(asset_path), f"STEP 2 ASSET ({asset_id})")
    
    # Step 3: Find element in recreated ifcJSON
    step3_element = find_element_by_id(step3_entities, element_id)
    if not step3_element:
        print(f"❌ Element not found in Step 3")
        return
        
    step3_geometry = analyze_element_geometry(step3_entities, step3_element, "STEP 3 (Recreated)")
    
    # Compare the flow
    compare_geometry_flow(step1_geometry, asset_geometry, step3_geometry, element_name)

def find_element_in_simplified(simplified_data: Dict[str, Any], element_id: str) -> tuple:
    """Find element in simplified JSON and return its asset ID"""
    
    building = simplified_data.get('building', {})
    storeys = building.get('storeys', [])
    
    for storey in storeys:
        elements = storey.get('elements', {})
        for element_type, element_list in elements.items():
            for element in element_list:
                if element.get('globalId') == element_id:
                    geometry = element.get('geometry', {})
                    asset_id = geometry.get('assetId')
                    return element, asset_id
                    
    return None, None

def analyze_element_geometry(entities: List[Dict[str, Any]], element: Dict[str, Any], stage: str) -> Dict[str, Any]:
    """Analyze geometry of an element"""
    
    print(f"\n📐 {stage} GEOMETRY")
    print("-" * 50)
    
    representation = element.get('representation', {})
    if representation.get('type') != 'IfcProductDefinitionShape':
        print("❌ No IfcProductDefinitionShape found")
        return {'representations': 0, 'geometry_types': set(), 'has_brep': False}
    
    representations = representation.get('representations', [])
    geometry_types = set()
    has_brep = False
    brep_count = 0
    
    print(f"📊 Shape representations: {len(representations)}")
    
    for i, rep_ref in enumerate(representations):
        ref_id = rep_ref.get('ref')
        shape_rep = find_element_by_id(entities, ref_id)
        
        if shape_rep and shape_rep.get('type') == 'IfcShapeRepresentation':
            rep_id = shape_rep.get('representationIdentifier')
            rep_type = shape_rep.get('representationType')
            
            print(f"  🔸 Rep {i+1}: {rep_id}-{rep_type}")
            
            if rep_id == 'Body' and rep_type == 'Brep':
                has_brep = True
                brep_count += 1
                print(f"    ✅ BODY-BREP FOUND")
            
            # Analyze items in this representation
            items = shape_rep.get('items', [])
            for j, item_ref in enumerate(items):
                geom_type = get_geometry_type(entities, item_ref)
                geometry_types.add(geom_type)
                print(f"    Item {j+1}: {geom_type}")
                
                if geom_type == 'IfcFacetedBrep':
                    print(f"      🟢 FACETED BREP FOUND")
    
    analysis = {
        'representations': len(representations),
        'geometry_types': geometry_types,
        'has_brep': has_brep,
        'brep_count': brep_count
    }
    
    print(f"📦 Geometry types: {', '.join(sorted(geometry_types))}")
    return analysis

def analyze_asset_geometry(asset_path: str, stage: str) -> Dict[str, Any]:
    """Analyze geometry in an asset file"""
    
    print(f"\n📦 {stage} GEOMETRY")
    print("-" * 50)
    
    asset_data = load_json_data(asset_path)
    
    geometry_types = set()
    shape_reps = []
    has_brep = False
    faceted_brep_count = 0
    
    for entity in asset_data:
        entity_type = entity.get('type')
        geometry_types.add(entity_type)
        
        if entity_type == 'IfcShapeRepresentation':
            rep_id = entity.get('representationIdentifier')
            rep_type = entity.get('representationType')
            shape_reps.append(f"{rep_id}-{rep_type}")
            
            if rep_id == 'Body' and rep_type == 'Brep':
                has_brep = True
                print(f"✅ Asset contains Body-Brep representation")
                
        elif entity_type == 'IfcFacetedBrep':
            faceted_brep_count += 1
    
    print(f"📊 Total entities: {len(asset_data)}")
    print(f"📊 Shape representations: {shape_reps}")
    print(f"📦 Geometry types: {', '.join(sorted(geometry_types))}")
    
    if faceted_brep_count > 0:
        print(f"🟢 IfcFacetedBrep entities: {faceted_brep_count}")
    
    return {
        'total_entities': len(asset_data),
        'geometry_types': geometry_types,
        'shape_reps': shape_reps,
        'has_brep': has_brep,
        'faceted_brep_count': faceted_brep_count
    }

def get_geometry_type(entities: List[Dict[str, Any]], item_ref: Any) -> str:
    """Get the geometry type of an item reference"""
    
    if isinstance(item_ref, dict):
        if 'ref' in item_ref:
            ref_id = item_ref.get('ref')
            geom_entity = find_element_by_id(entities, ref_id)
            if geom_entity:
                return geom_entity.get('type', 'unknown')
        else:
            return item_ref.get('type', 'inline_unknown')
    
    return 'unknown'

def compare_geometry_flow(step1_analysis: Dict[str, Any], 
                         asset_analysis: Dict[str, Any],
                         step3_analysis: Dict[str, Any],
                         element_name: str) -> None:
    """Compare geometry through the flow"""
    
    print(f"\n📊 GEOMETRY FLOW COMPARISON: {element_name}")
    print("="*70)
    
    print(f"Body-Brep representations:")
    print(f"  Step 1: {'✅' if step1_analysis.get('has_brep') else '❌'} ({step1_analysis.get('brep_count', 0)} found)")
    print(f"  Asset:  {'✅' if asset_analysis.get('has_brep') else '❌'} ({asset_analysis.get('faceted_brep_count', 0)} IfcFacetedBrep)")  
    print(f"  Step 3: {'✅' if step3_analysis.get('has_brep') else '❌'} ({step3_analysis.get('brep_count', 0)} found)")
    
    print(f"\nGeometry types evolution:")
    step1_types = step1_analysis.get('geometry_types', set())
    asset_types = asset_analysis.get('geometry_types', set())
    step3_types = step3_analysis.get('geometry_types', set())
    
    print(f"  Step 1: {', '.join(sorted(step1_types))}")
    print(f"  Asset:  {', '.join(sorted(asset_types))}")
    print(f"  Step 3: {', '.join(sorted(step3_types))}")
    
    # Identify where loss occurs
    if step1_analysis.get('has_brep') and not asset_analysis.get('has_brep'):
        print(f"\n🚨 ISSUE IDENTIFIED: Body-Brep lost during ASSET EXTRACTION (Step 1→2)")
        print(f"   Original had Body-Brep, but asset does not contain Body-Brep representation")
        
    elif asset_analysis.get('has_brep') and not step3_analysis.get('has_brep'):
        print(f"\n🚨 ISSUE IDENTIFIED: Body-Brep lost during RECREATION (Step 2→3)")
        print(f"   Asset contains Body-Brep, but recreated element does not")
        
    elif not step1_analysis.get('has_brep') and not step3_analysis.get('has_brep'):
        print(f"\n✅ CONSISTENT: Element never had Body-Brep representation")
        
    else:
        print(f"\n✅ SUCCESS: Body-Brep preserved through entire flow")
    
    # Check for IfcFacetedBrep specifically
    has_step1_faceted = 'IfcFacetedBrep' in step1_types
    has_asset_faceted = asset_analysis.get('faceted_brep_count', 0) > 0
    has_step3_faceted = 'IfcFacetedBrep' in step3_types
    
    print(f"\nIfcFacetedBrep tracking:")
    print(f"  Step 1: {'✅' if has_step1_faceted else '❌'}")
    print(f"  Asset:  {'✅' if has_asset_faceted else '❌'} ({asset_analysis.get('faceted_brep_count', 0)} entities)")
    print(f"  Step 3: {'✅' if has_step3_faceted else '❌'}")
    
    if has_step1_faceted and not has_asset_faceted:
        print(f"🚨 IfcFacetedBrep lost in asset extraction!")
    elif has_asset_faceted and not has_step3_faceted:
        print(f"🚨 IfcFacetedBrep lost in asset recreation!")

def analyze_all_body_brep_elements(step1_entities: List[Dict[str, Any]], 
                                   simplified_data: Dict[str, Any],
                                   step3_entities: List[Dict[str, Any]],
                                   assets_dir: str) -> None:
    """Analyze all elements that have Body-Brep in Step 1"""
    
    print(f"\n🔍 ANALYZING ALL BODY-BREP ELEMENTS")
    print("="*70)
    
    # Find all Body-Brep elements in Step 1
    brep_elements = []
    
    for entity in step1_entities:
        if entity.get('type') in ['IfcWall', 'IfcWallStandardCase', 'IfcWindow', 'IfcDoor', 'IfcOpeningElement', 'IfcSlab', 'IfcBeam', 'IfcColumn']:
            representation = entity.get('representation', {})
            if representation.get('type') == 'IfcProductDefinitionShape':
                representations = representation.get('representations', [])
                
                for rep_ref in representations:
                    ref_id = rep_ref.get('ref')
                    shape_rep = find_element_by_id(step1_entities, ref_id)
                    
                    if (shape_rep and shape_rep.get('type') == 'IfcShapeRepresentation' and
                        shape_rep.get('representationIdentifier') == 'Body' and
                        shape_rep.get('representationType') == 'Brep'):
                        
                        brep_elements.append({
                            'element': entity,
                            'name': entity.get('name', 'unnamed'),
                            'type': entity.get('type'),
                            'globalId': entity.get('globalId')
                        })
                        break
    
    print(f"Found {len(brep_elements)} elements with Body-Brep in Step 1")
    
    # Analyze each one
    success_count = 0
    for i, elem_info in enumerate(brep_elements[:10]):  # Limit to first 10 for performance
        print(f"\n[{i+1}/{min(10, len(brep_elements))}] Analyzing: {elem_info['name']}")
        print("-" * 50)
        
        # Quick check if this element preserves Body-Brep
        step3_element = find_element_by_id(step3_entities, elem_info['globalId'])
        if step3_element:
            step3_has_brep = element_has_body_brep(step3_entities, step3_element)
            if step3_has_brep:
                success_count += 1
                print(f"✅ Body-Brep preserved")
            else:
                print(f"❌ Body-Brep lost")
                # Detailed analysis for failed elements
                analyze_element_asset_flow(step1_entities, simplified_data, step3_entities, assets_dir, elem_info['name'])
    
    print(f"\n📊 SUMMARY")
    print(f"Elements analyzed: {min(10, len(brep_elements))}")
    print(f"Body-Brep preserved: {success_count}")
    print(f"Success rate: {(success_count/min(10, len(brep_elements)))*100:.1f}%")

def element_has_body_brep(entities: List[Dict[str, Any]], element: Dict[str, Any]) -> bool:
    """Check if an element has Body-Brep representation"""
    
    representation = element.get('representation', {})
    if representation.get('type') != 'IfcProductDefinitionShape':
        return False
    
    representations = representation.get('representations', [])
    for rep_ref in representations:
        ref_id = rep_ref.get('ref')
        shape_rep = find_element_by_id(entities, ref_id)
        
        if (shape_rep and shape_rep.get('type') == 'IfcShapeRepresentation' and
            shape_rep.get('representationIdentifier') == 'Body' and
            shape_rep.get('representationType') == 'Brep'):
            return True
    
    return False

def main():
    if len(sys.argv) < 5:
        print("Usage: python debug_asset_extraction.py <step1_json> <simplified_json> <step3_json> <assets_dir> [element_name]")
        print("Example: python debug_asset_extraction.py step1.json simplified.json step3.json ./assets 'Wand-Ext-OG-1'")
        sys.exit(1)
    
    step1_file = sys.argv[1]
    simplified_file = sys.argv[2]
    step3_file = sys.argv[3]
    assets_dir = sys.argv[4]
    element_name = sys.argv[5] if len(sys.argv) > 5 else None
    
    print("🔍 DEBUG ASSET EXTRACTION AND RECREATION")
    print("="*70)
    
    # Load data
    step1_entities = load_json_data(step1_file)
    simplified_data = load_simplified_data(simplified_file)
    step3_entities = load_json_data(step3_file)
    
    print(f"✅ Loaded Step 1: {len(step1_entities)} entities")
    print(f"✅ Loaded Step 3: {len(step3_entities)} entities")
    print(f"📦 Assets directory: {assets_dir}")
    
    if element_name:
        # Analyze specific element
        analyze_element_asset_flow(step1_entities, simplified_data, step3_entities, assets_dir, element_name)
    else:
        # Analyze all Body-Brep elements
        analyze_all_body_brep_elements(step1_entities, simplified_data, step3_entities, assets_dir)

if __name__ == "__main__":
    main()