#!/usr/bin/env python3
"""
Trace Step 3 Boolean Processing

Actually runs the Step 3 converter with debug output to trace what happens to boolean operations.

Usage:
    python trace_step3_boolean_processing.py <simplified.json> <assets_dir> <output.json>
    
Example:
    python trace_step3_boolean_processing.py \
        ../../out-temp/step2_simplified_json/OrangeHouse_simplified.json \
        ../../out-temp/assets/OrangeHouse \
        ./debug_step3_output.json
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from simplified_to_ifcjson import SimplifiedToIfcJsonConverter

def count_boolean_operations(ifcjson_data: dict) -> int:
    """Count boolean operations in ifcJSON data"""
    if not isinstance(ifcjson_data, dict):
        return 0
    
    entities = ifcjson_data.get('data', [])
    if not isinstance(entities, list):
        return 0
    
    count = 0
    for entity in entities:
        if isinstance(entity, dict) and entity.get('type') == 'IfcBooleanClippingResult':
            count += 1
    
    return count

def count_entities_by_type(ifcjson_data: dict) -> dict:
    """Count all entity types in ifcJSON data"""
    if not isinstance(ifcjson_data, dict):
        return {}
    
    entities = ifcjson_data.get('data', [])
    if not isinstance(entities, list):
        return {}
    
    counts = {}
    for entity in entities:
        if isinstance(entity, dict):
            entity_type = entity.get('type', 'Unknown')
            counts[entity_type] = counts.get(entity_type, 0) + 1
    
    return counts

class DebugSimplifiedToIfcJsonConverter(SimplifiedToIfcJsonConverter):
    """Debug version that traces boolean operation processing"""
    
    def __init__(self, assets_dir: str = "./assets"):
        super().__init__(assets_dir)
        self.debug_boolean_ops = []
        
    def _load_asset_geometry(self, asset_id: str):
        """Override to trace boolean operations in assets"""
        print(f"🔍 Loading asset geometry: {asset_id}")
        
        geometry_entities = super()._load_asset_geometry(asset_id)
        
        if geometry_entities:
            boolean_count = 0
            for entity in geometry_entities:
                if entity.get('type') == 'IfcBooleanClippingResult':
                    boolean_count += 1
                    print(f"  ✅ Found boolean operation: {entity.get('globalId', 'NO-ID')}")
                    self.debug_boolean_ops.append({
                        'asset_id': asset_id,
                        'entity_globalId': entity.get('globalId'),
                        'operator': entity.get('operator'),
                        'stage': 'loaded_from_asset'
                    })
            
            print(f"  📊 Asset {asset_id}: {len(geometry_entities)} entities, {boolean_count} boolean operations")
        else:
            print(f"  ❌ No geometry entities loaded from asset {asset_id}")
        
        return geometry_entities
    
    def _create_shape_representation_from_asset(self, shape_repr_id: str, geometry_entities, target_shape_repr=None):
        """Override to trace boolean operations during shape representation creation"""
        
        boolean_count_before = 0
        for entity in geometry_entities:
            if entity.get('type') == 'IfcBooleanClippingResult':
                boolean_count_before += 1
        
        print(f"🎭 Creating shape representation {shape_repr_id}")
        print(f"   Input entities: {len(geometry_entities)}, boolean ops: {boolean_count_before}")
        
        success = super()._create_shape_representation_from_asset(shape_repr_id, geometry_entities, target_shape_repr)
        
        # Count boolean operations that were added to main entities list
        boolean_count_in_entities = 0
        for entity in self.entities:
            if entity.get('type') == 'IfcBooleanClippingResult':
                boolean_count_in_entities += 1
        
        print(f"   Success: {success}")
        print(f"   Total boolean ops in entities list: {boolean_count_in_entities}")
        
        return success
    
    def convert(self, simplified_path: str, output_path: str = None):
        """Override to add debug output"""
        print(f"🚀 Starting Step 3 conversion with debug tracing...")
        
        result = super().convert(simplified_path, output_path)
        
        print(f"\n📊 DEBUG SUMMARY")
        print("-" * 60)
        print(f"Boolean operations found in assets: {len(self.debug_boolean_ops)}")
        
        final_boolean_count = count_boolean_operations(result)
        print(f"Boolean operations in final output: {final_boolean_count}")
        
        if len(self.debug_boolean_ops) > 0 and final_boolean_count == 0:
            print("⚠️  ISSUE CONFIRMED: Boolean operations lost during conversion!")
        elif len(self.debug_boolean_ops) == final_boolean_count:
            print("✅ All boolean operations preserved!")
        else:
            print(f"⚠️  Partial loss: {len(self.debug_boolean_ops)} → {final_boolean_count}")
        
        # Show entity type summary
        entity_counts = count_entities_by_type(result)
        print(f"\n📋 Final entity types:")
        for entity_type, count in sorted(entity_counts.items()):
            if 'Boolean' in entity_type:
                print(f"   {entity_type}: {count} ⭐")
            else:
                print(f"   {entity_type}: {count}")
        
        return result

def main():
    if len(sys.argv) != 4:
        print("Usage: python trace_step3_boolean_processing.py <simplified.json> <assets_dir> <output.json>")
        print("\nExamples:")
        print("  python trace_step3_boolean_processing.py \\")
        print("    ../../out-temp/step2_simplified_json/OrangeHouse_simplified.json \\")
        print("    ../../out-temp/assets/OrangeHouse \\")
        print("    ./debug_step3_output.json")
        print("\nDescription:")
        print("  Runs Step 3 converter with debug tracing to see what happens to boolean operations")
        return
    
    simplified_file, assets_dir, output_file = sys.argv[1:4]
    
    print(f"🔍 TRACE STEP 3 BOOLEAN PROCESSING")
    print(f"Simplified: {simplified_file}")
    print(f"Assets: {assets_dir}")
    print(f"Output: {output_file}")
    print("=" * 100)
    
    try:
        converter = DebugSimplifiedToIfcJsonConverter(assets_dir)
        result = converter.convert(simplified_file, output_file)
        
        print(f"\n✅ Conversion completed. Check {output_file} for results.")
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()