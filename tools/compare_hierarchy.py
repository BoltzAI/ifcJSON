#!/usr/bin/env python3
"""
Compare hierarchical placement information across different pipeline steps.
This tool compares hierarchy data from step1 (ifcJSON), step2 (simplified JSON), and step3 (ifcJSON).

Usage:
    python compare_hierarchy.py <step1_hierarchy.json> <step2_hierarchy.json> [step3_hierarchy.json]
    python compare_hierarchy.py original.json simplified.json restored.json
"""

import json
import sys
from pathlib import Path

def load_hierarchy_data(file_path):
    """Load hierarchy data from JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def compare_hierarchy_preservation(step1_data, step2_data, step3_data=None):
    """Compare hierarchy preservation across pipeline steps"""
    
    print("🔍 HIERARCHICAL PLACEMENT COMPARISON")
    print("=" * 70)
    
    # Extract element names for comparison
    step1_elements = set(step1_data.get('elements', {}).keys())
    step2_elements = set(step2_data.get('elements', {}).keys())
    step3_elements = set(step3_data.get('elements', {}).keys()) if step3_data else set()
    
    print(f"\n📊 ELEMENT COUNT COMPARISON:")
    print(f"   Step 1 (Original ifcJSON): {len(step1_elements)} elements")
    print(f"   Step 2 (Simplified JSON): {len(step2_elements)} elements")
    if step3_data:
        print(f"   Step 3 (Restored ifcJSON): {len(step3_elements)} elements")
    
    # Find common elements
    common_12 = step1_elements & step2_elements
    common_13 = step1_elements & step3_elements if step3_data else set()
    common_23 = step2_elements & step3_elements if step3_data else set()
    common_all = common_12 & common_13 if step3_data else common_12
    
    print(f"\n🔗 COMMON ELEMENTS:")
    print(f"   Step 1 & 2: {len(common_12)} elements")
    if step3_data:
        print(f"   Step 1 & 3: {len(common_13)} elements")
        print(f"   Step 2 & 3: {len(common_23)} elements")
        print(f"   All steps: {len(common_all)} elements")
    
    # Compare hierarchy information
    print(f"\n🏗️  HIERARCHY PRESERVATION ANALYSIS:")
    print("=" * 70)
    
    hierarchy_comparison = {
        "step1_to_step2": {"preserved": 0, "lost": 0, "details": []},
        "step2_to_step3": {"preserved": 0, "lost": 0, "details": []},
        "step1_to_step3": {"preserved": 0, "lost": 0, "details": []},
        "elements_analyzed": len(common_all)
    }
    
    for element_name in sorted(common_all):
        step1_elem = step1_data['elements'].get(element_name, {})
        step2_elem = step2_data['elements'].get(element_name, {})
        step3_elem = step3_data['elements'].get(element_name, {}) if step3_data else {}
        
        print(f"\n🔍 {element_name}:")
        
        # Step 1 hierarchy info
        step1_has_hierarchy = step1_elem.get('has_hierarchical_placement', False)
        step1_hierarchy = step1_elem.get('placement_hierarchy', {})
        step1_parent = step1_hierarchy.get('parent_placement', 'None')
        step1_level = step1_hierarchy.get('hierarchy_level', 0)
        step1_location = step1_hierarchy.get('local_data', {}).get('location', 'None')
        
        print(f"   Step 1: Hierarchy={step1_has_hierarchy}, Parent={step1_parent}, Level={step1_level}")
        print(f"           Location={step1_location}")
        
        # Step 2 hierarchy info
        step2_has_hierarchy = step2_elem.get('has_hierarchical_placement', False)
        step2_hierarchy = step2_elem.get('hierarchical_info', {})
        step2_parent = step2_hierarchy.get('parent_placement', 'None')
        step2_level = step2_hierarchy.get('placement_hierarchy_level', 'None')
        step2_local = step2_hierarchy.get('local_coordinates', 'None')
        step2_is_absolute = step2_hierarchy.get('is_absolute', True)
        
        print(f"   Step 2: Hierarchy={step2_has_hierarchy}, Parent={step2_parent}, Level={step2_level}")
        print(f"           Local Coords={step2_local}, Is_Absolute={step2_is_absolute}")
        
        # Step 1 to Step 2 comparison - detailed value comparison
        if step1_has_hierarchy and step2_has_hierarchy:
            # Check if hierarchy values match
            parent_preserved = (step1_parent != 'None' and step2_parent != 'None')
            level_preserved = (step1_level > 0 and step2_level != 'None')
            
            # Compare coordinate values if available
            coordinates_match = True
            coordinate_details = []
            
            if step1_location != 'None' and step2_local != 'None':
                if isinstance(step1_location, list) and isinstance(step2_local, list):
                    if len(step1_location) == len(step2_local):
                        for i, (v1, v2) in enumerate(zip(step1_location, step2_local)):
                            if abs(v1 - v2) > 0.001:  # tolerance for floating point comparison
                                coordinates_match = False
                                coordinate_details.append(f"coord[{i}]: {v1} → {v2}")
                    else:
                        coordinates_match = False
                        coordinate_details.append(f"length: {len(step1_location)} → {len(step2_local)}")
            
            # Overall preservation check
            if parent_preserved and level_preserved and coordinates_match:
                hierarchy_comparison['step1_to_step2']['preserved'] += 1
                status_12 = "✅ PRESERVED"
            else:
                hierarchy_comparison['step1_to_step2']['lost'] += 1
                status_12 = "❌ LOST"
                details = []
                if not parent_preserved:
                    details.append(f"parent: {step1_parent} → {step2_parent}")
                if not level_preserved:
                    details.append(f"level: {step1_level} → {step2_level}")
                if not coordinates_match:
                    details.extend(coordinate_details)
                hierarchy_comparison['step1_to_step2']['details'].append(f"{element_name}: {'; '.join(details)}")
            
            # Show detailed comparison
            if not coordinates_match:
                print(f"           ⚠️  Coordinate mismatch: {coordinate_details}")
        elif step1_has_hierarchy and not step2_has_hierarchy:
            hierarchy_comparison['step1_to_step2']['lost'] += 1
            status_12 = "❌ LOST"
            hierarchy_comparison['step1_to_step2']['details'].append(f"{element_name}: Had hierarchy → No hierarchy")
        elif not step1_has_hierarchy and step2_has_hierarchy:
            hierarchy_comparison['step1_to_step2']['preserved'] += 1
            status_12 = "✅ ADDED"
        else:
            hierarchy_comparison['step1_to_step2']['preserved'] += 1
            status_12 = "✅ CONSISTENT (no hierarchy)"
        
        print(f"   Step 1→2: {status_12}")
        
        # Step 3 analysis (if available)
        if step3_data:
            step3_has_hierarchy = step3_elem.get('has_hierarchical_placement', False)
            step3_hierarchy = step3_elem.get('placement_hierarchy', {})
            step3_parent = step3_hierarchy.get('parent_placement', 'None')
            step3_level = step3_hierarchy.get('hierarchy_level', 0)
            step3_location = step3_hierarchy.get('local_data', {}).get('location', 'None')
            
            print(f"   Step 3: Hierarchy={step3_has_hierarchy}, Parent={step3_parent}, Level={step3_level}")
            print(f"           Location={step3_location}")
            
            # Step 2 to Step 3 comparison - detailed value comparison
            if step2_has_hierarchy and step3_has_hierarchy:
                parent_preserved = (step2_parent != 'None' and step3_parent != 'None')
                level_preserved = (step2_level != 'None' and step3_level > 0)
                
                # Compare coordinate values if available
                coordinates_match = True
                coordinate_details = []
                
                if step2_local != 'None' and step3_location != 'None':
                    if isinstance(step2_local, list) and isinstance(step3_location, list):
                        if len(step2_local) == len(step3_location):
                            for i, (v2, v3) in enumerate(zip(step2_local, step3_location)):
                                if abs(v2 - v3) > 0.001:  # tolerance for floating point comparison
                                    coordinates_match = False
                                    coordinate_details.append(f"coord[{i}]: {v2} → {v3}")
                        else:
                            coordinates_match = False
                            coordinate_details.append(f"length: {len(step2_local)} → {len(step3_location)}")
                
                # Overall preservation check
                if parent_preserved and level_preserved and coordinates_match:
                    hierarchy_comparison['step2_to_step3']['preserved'] += 1
                    status_23 = "✅ PRESERVED"
                else:
                    hierarchy_comparison['step2_to_step3']['lost'] += 1
                    status_23 = "❌ LOST"
                    details = []
                    if not parent_preserved:
                        details.append(f"parent: {step2_parent} → {step3_parent}")
                    if not level_preserved:
                        details.append(f"level: {step2_level} → {step3_level}")
                    if not coordinates_match:
                        details.extend(coordinate_details)
                    hierarchy_comparison['step2_to_step3']['details'].append(f"{element_name}: {'; '.join(details)}")
                
                # Show detailed comparison
                if not coordinates_match:
                    print(f"           ⚠️  Coordinate mismatch: {coordinate_details}")
            elif step2_has_hierarchy and not step3_has_hierarchy:
                hierarchy_comparison['step2_to_step3']['lost'] += 1
                status_23 = "❌ LOST"
                hierarchy_comparison['step2_to_step3']['details'].append(f"{element_name}: Had hierarchy → No hierarchy")
            elif not step2_has_hierarchy and step3_has_hierarchy:
                hierarchy_comparison['step2_to_step3']['preserved'] += 1
                status_23 = "✅ ADDED"
            else:
                hierarchy_comparison['step2_to_step3']['preserved'] += 1
                status_23 = "✅ CONSISTENT (no hierarchy)"
            
            print(f"   Step 2→3: {status_23}")
            
            # Step 1 to Step 3 overall comparison - detailed round-trip validation
            if step1_has_hierarchy and step3_has_hierarchy:
                # Check if original hierarchy is fully restored
                parent_preserved = (step1_parent != 'None' and step3_parent != 'None')
                level_preserved = (step1_level > 0 and step3_level > 0)
                
                # Compare coordinate values for round-trip preservation
                coordinates_match = True
                coordinate_details = []
                
                if step1_location != 'None' and step3_location != 'None':
                    if isinstance(step1_location, list) and isinstance(step3_location, list):
                        if len(step1_location) == len(step3_location):
                            for i, (v1, v3) in enumerate(zip(step1_location, step3_location)):
                                if abs(v1 - v3) > 0.001:  # tolerance for floating point comparison
                                    coordinates_match = False
                                    coordinate_details.append(f"coord[{i}]: {v1} → {v3}")
                        else:
                            coordinates_match = False
                            coordinate_details.append(f"length: {len(step1_location)} → {len(step3_location)}")
                
                # Overall round-trip preservation check
                if parent_preserved and level_preserved and coordinates_match:
                    hierarchy_comparison['step1_to_step3']['preserved'] += 1
                    status_13 = "✅ ROUND-TRIP PRESERVED"
                else:
                    hierarchy_comparison['step1_to_step3']['lost'] += 1
                    status_13 = "❌ ROUND-TRIP LOST"
                    details = []
                    if not parent_preserved:
                        details.append(f"parent: {step1_parent} → {step3_parent}")
                    if not level_preserved:
                        details.append(f"level: {step1_level} → {step3_level}")
                    if not coordinates_match:
                        details.extend(coordinate_details)
                    hierarchy_comparison['step1_to_step3']['details'].append(f"{element_name}: {'; '.join(details)}")
                
                # Show detailed comparison
                if not coordinates_match:
                    print(f"           ⚠️  Round-trip coordinate mismatch: {coordinate_details}")
            elif step1_has_hierarchy and not step3_has_hierarchy:
                hierarchy_comparison['step1_to_step3']['lost'] += 1
                status_13 = "❌ ROUND-TRIP LOST"
                hierarchy_comparison['step1_to_step3']['details'].append(f"{element_name}: Had hierarchy → No hierarchy")
            else:
                hierarchy_comparison['step1_to_step3']['preserved'] += 1
                status_13 = "✅ ROUND-TRIP CONSISTENT"
            
            print(f"   Step 1→3: {status_13}")
    
    # Summary results
    print(f"\n🎯 HIERARCHY PRESERVATION SUMMARY:")
    print("=" * 70)
    
    total_analyzed = hierarchy_comparison['elements_analyzed']
    
    print(f"📊 Step 1 → Step 2 (ifcJSON → Simplified JSON):")
    preserved_12 = hierarchy_comparison['step1_to_step2']['preserved']
    lost_12 = hierarchy_comparison['step1_to_step2']['lost']
    print(f"   ✅ Preserved: {preserved_12}/{total_analyzed} ({100*preserved_12/total_analyzed:.1f}%)")
    print(f"   ❌ Lost: {lost_12}/{total_analyzed} ({100*lost_12/total_analyzed:.1f}%)")
    
    if step3_data:
        print(f"\n📊 Step 2 → Step 3 (Simplified JSON → ifcJSON):")
        preserved_23 = hierarchy_comparison['step2_to_step3']['preserved']
        lost_23 = hierarchy_comparison['step2_to_step3']['lost']
        print(f"   ✅ Preserved: {preserved_23}/{total_analyzed} ({100*preserved_23/total_analyzed:.1f}%)")
        print(f"   ❌ Lost: {lost_23}/{total_analyzed} ({100*lost_23/total_analyzed:.1f}%)")
        
        print(f"\n📊 Step 1 → Step 3 (Overall Round-trip):")
        preserved_13 = hierarchy_comparison['step1_to_step3']['preserved']
        lost_13 = hierarchy_comparison['step1_to_step3']['lost']
        print(f"   ✅ Preserved: {preserved_13}/{total_analyzed} ({100*preserved_13/total_analyzed:.1f}%)")
        print(f"   ❌ Lost: {lost_13}/{total_analyzed} ({100*lost_13/total_analyzed:.1f}%)")
    
    # Show detailed failure analysis
    if hierarchy_comparison['step1_to_step2']['details']:
        print(f"\n🚨 Step 1→2 Hierarchy Losses:")
        for detail in hierarchy_comparison['step1_to_step2']['details']:
            print(f"   - {detail}")
    
    if step3_data and hierarchy_comparison['step2_to_step3']['details']:
        print(f"\n🚨 Step 2→3 Hierarchy Losses:")
        for detail in hierarchy_comparison['step2_to_step3']['details']:
            print(f"   - {detail}")
    
    if step3_data and hierarchy_comparison['step1_to_step3']['details']:
        print(f"\n🚨 Step 1→3 Round-trip Losses:")
        for detail in hierarchy_comparison['step1_to_step3']['details']:
            print(f"   - {detail}")
    
    # Final verdict
    print(f"\n🏁 FINAL VERDICT:")
    print("=" * 40)
    
    if lost_12 == 0:
        print("✅ HIERARCHY PRESERVED in Step 1→2")
    else:
        print("❌ HIERARCHY LOST in Step 1→2: {lost_12}/{total_analyzed} elements")
    
    if step3_data:
        if lost_23 == 0:
            print("✅ HIERARCHY PRESERVED in Step 2→3")
        else:
            print(f"❌ HIERARCHY LOST in Step 2→3: {lost_23}/{total_analyzed} elements")
        
        if lost_13 == 0:
            print("✅ ROUND-TRIP HIERARCHY PRESERVED")
        else:
            print(f"❌ ROUND-TRIP HIERARCHY LOST: {lost_13}/{total_analyzed} elements")
    
    return hierarchy_comparison

def compare_hierarchy_values(elem_name, step1_data, step2_data, step3_data=None):
    """Compare specific hierarchy values for a single element"""
    print(f"\n🔍 DETAILED VALUE COMPARISON FOR: {elem_name}")
    print("=" * 50)
    
    # Extract hierarchy data
    step1_elem = step1_data.get('elements', {}).get(elem_name, {})
    step2_elem = step2_data.get('elements', {}).get(elem_name, {})
    step3_elem = step3_data.get('elements', {}).get(elem_name, {}) if step3_data else {}
    
    # Step 1 values
    step1_hierarchy = step1_elem.get('placement_hierarchy', {})
    step1_location = step1_hierarchy.get('local_data', {}).get('location', [])
    step1_ref_dir = step1_hierarchy.get('local_data', {}).get('ref_direction', [])
    step1_axis = step1_hierarchy.get('local_data', {}).get('axis', [])
    step1_parent = step1_hierarchy.get('parent_placement', 'None')
    step1_level = step1_hierarchy.get('hierarchy_level', 0)
    
    # Step 2 values
    step2_hierarchy = step2_elem.get('hierarchical_info', {})
    step2_location = step2_hierarchy.get('local_coordinates', [])
    step2_parent = step2_hierarchy.get('parent_placement', 'None')
    step2_level = step2_hierarchy.get('placement_hierarchy_level', 0)
    step2_is_absolute = step2_hierarchy.get('is_absolute', True)
    
    # Absolute placement values from step2
    step2_placement = step2_elem.get('placement', {})
    step2_abs_location = step2_placement.get('location', [])
    step2_abs_x_axis = step2_placement.get('x_axis', [])
    step2_abs_z_axis = step2_placement.get('z_axis', [])
    
    print(f"📍 COORDINATE VALUES:")
    print(f"   Step 1 Location: {step1_location}")
    print(f"   Step 2 Local:    {step2_location}")  
    print(f"   Step 2 Absolute: {step2_abs_location}")
    
    print(f"\n🔗 HIERARCHY VALUES:")
    print(f"   Step 1 Parent: {step1_parent}")
    print(f"   Step 2 Parent: {step2_parent}")
    print(f"   Step 1 Level:  {step1_level}")
    print(f"   Step 2 Level:  {step2_level}")
    print(f"   Step 2 Is_Absolute: {step2_is_absolute}")
    
    print(f"\n🧭 DIRECTION VALUES:")
    print(f"   Step 1 Ref Direction: {step1_ref_dir}")
    print(f"   Step 2 X-Axis:        {step2_abs_x_axis}")
    print(f"   Step 1 Axis:          {step1_axis}")
    print(f"   Step 2 Z-Axis:        {step2_abs_z_axis}")
    
    if step3_data:
        # Step 3 values
        step3_hierarchy = step3_elem.get('placement_hierarchy', {})
        step3_location = step3_hierarchy.get('local_data', {}).get('location', [])
        step3_parent = step3_hierarchy.get('parent_placement', 'None')
        step3_level = step3_hierarchy.get('hierarchy_level', 0)
        
        print(f"\n📍 STEP 3 VALUES:")
        print(f"   Step 3 Location: {step3_location}")
        print(f"   Step 3 Parent: {step3_parent}")
        print(f"   Step 3 Level:  {step3_level}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_hierarchy.py <step1_hierarchy.json> <step2_hierarchy.json> [step3_hierarchy.json] [--element <element_name>]")
        print("Example: python compare_hierarchy.py original.json simplified.json restored.json")
        print("Example: python compare_hierarchy.py original.json simplified.json --element 'Wand-Int-ERDG-1'")
        sys.exit(1)
    
    # Parse command line arguments
    step1_file = sys.argv[1]
    step2_file = sys.argv[2]
    step3_file = None
    element_name = None
    
    # Parse optional arguments
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--element' and i + 1 < len(sys.argv):
            element_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i].startswith('--'):
            i += 1
        else:
            # This is the step3 file
            step3_file = sys.argv[i]
            i += 1
    
    # Check file existence
    for file_path in [step1_file, step2_file] + ([step3_file] if step3_file else []):
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
    
    print(f"📁 Comparing hierarchy across pipeline steps:")
    print(f"   Step 1: {step1_file}")
    print(f"   Step 2: {step2_file}")
    if step3_file:
        print(f"   Step 3: {step3_file}")
    
    try:
        # Load data
        step1_data = load_hierarchy_data(step1_file)
        step2_data = load_hierarchy_data(step2_file)
        step3_data = load_hierarchy_data(step3_file) if step3_file else None
        
        # If specific element requested, show detailed comparison
        if element_name:
            compare_hierarchy_values(element_name, step1_data, step2_data, step3_data)
        else:
            # Compare hierarchy preservation
            comparison_results = compare_hierarchy_preservation(step1_data, step2_data, step3_data)
            
            # Final verdict
            print(f"\n🏁 FINAL VERDICT:")
            print("=" * 40)
            
            if step3_data:
                total_elements = comparison_results['elements_analyzed']
                roundtrip_preserved = comparison_results['step1_to_step3']['preserved']
                roundtrip_lost = comparison_results['step1_to_step3']['lost']
                
                if roundtrip_lost == 0:
                    print(f"✅ HIERARCHY FULLY PRESERVED through complete pipeline")
                else:
                    print(f"❌ HIERARCHY PARTIALLY LOST: {roundtrip_lost}/{total_elements} elements")
                    
                    # Identify where the loss occurred
                    step12_lost = comparison_results['step1_to_step2']['lost']
                    step23_lost = comparison_results['step2_to_step3']['lost']
                    
                    if step12_lost > 0 and step23_lost == 0:
                        print(f"   → Loss occurred in Step 1→2 (ifcJSON → Simplified JSON)")
                    elif step12_lost == 0 and step23_lost > 0:
                        print(f"   → Loss occurred in Step 2→3 (Simplified JSON → ifcJSON)")
                    else:
                        print(f"   → Loss occurred in both steps")
            else:
                total_elements = comparison_results['elements_analyzed']
                step12_preserved = comparison_results['step1_to_step2']['preserved']
                step12_lost = comparison_results['step1_to_step2']['lost']
                
                if step12_lost == 0:
                    print(f"✅ HIERARCHY PRESERVED in Step 1→2")
                else:
                    print(f"❌ HIERARCHY LOST in Step 1→2: {step12_lost}/{total_elements} elements")
        
        print(f"\n✅ Hierarchy comparison completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()