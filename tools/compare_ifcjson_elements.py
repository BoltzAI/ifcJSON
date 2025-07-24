#!/usr/bin/env python3
"""
Compare ifcJSON files to find differences in building elements
Analyzes geometry representation, placement, and relationships between two ifcJSON files
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

class IfcJsonComparator:
    def __init__(self, file1_path: str, file2_path: str):
        self.file1_path = file1_path
        self.file2_path = file2_path
        
        # Load both files
        with open(file1_path, 'r') as f:
            self.file1_data = json.load(f)
        
        with open(file2_path, 'r') as f:
            self.file2_data = json.load(f)
        
        # Index entities by globalId for both files
        self.file1_entities = {}
        self.file2_entities = {}
        
        for entity in self.file1_data.get('data', []):
            if 'globalId' in entity:
                self.file1_entities[entity['globalId']] = entity
        
        for entity in self.file2_data.get('data', []):
            if 'globalId' in entity:
                self.file2_entities[entity['globalId']] = entity
                
        print(f"File1 entities: {len(self.file1_entities)}")
        print(f"File2 entities: {len(self.file2_entities)}")
    
    def find_element(self, identifier: str, data: Dict) -> Optional[Dict]:
        """Find an element by name, globalId, or as a ref in the data"""
        # First try to find by name
        for entity in data.get('data', []):
            if entity.get('name') == identifier:
                return entity
        
        # Then try to find by globalId
        for entity in data.get('data', []):
            if entity.get('globalId') == identifier:
                return entity
        
        # If not found, it might be a ref that doesn't have its own entity
        return None
    
    def get_entity_by_id(self, entity_id: str, entities: Dict) -> Optional[Dict]:
        """Get entity by globalId"""
        return entities.get(entity_id)
    
    def resolve_reference(self, ref: Any, entities: Dict) -> Optional[Dict]:
        """Resolve a reference to an entity"""
        if isinstance(ref, dict) and 'ref' in ref:
            return entities.get(ref['ref'])
        return None
    
    def _find_references_to(self, identifier: str, data: Dict) -> List[Dict]:
        """Find all entities that reference the given identifier"""
        references = []
        
        def check_for_ref(obj, parent_entity=None):
            if isinstance(obj, dict):
                if 'ref' in obj and obj['ref'] == identifier:
                    if parent_entity:
                        references.append(parent_entity)
                for value in obj.values():
                    check_for_ref(value, parent_entity)
            elif isinstance(obj, list):
                for item in obj:
                    check_for_ref(item, parent_entity)
        
        for entity in data.get('data', []):
            check_for_ref(entity, entity)
        
        return references
    
    def _show_references_and_referents(self, identifier: str, file1_element: Dict, file2_element: Dict):
        """Show what this element references and what references it"""
        print("\n🔗 Reference Analysis:")
        
        # Find all refs within the element
        def extract_refs(obj, refs_list):
            if isinstance(obj, dict):
                if 'ref' in obj:
                    refs_list.append(obj['ref'])
                for value in obj.values():
                    extract_refs(value, refs_list)
            elif isinstance(obj, list):
                for item in obj:
                    extract_refs(item, refs_list)
        
        # File1 references
        file1_refs = []
        extract_refs(file1_element, file1_refs)
        if file1_refs:
            print(f"File1 - This element references: {len(file1_refs)} entities")
            for ref in file1_refs[:5]:  # Show first 5
                print(f"  → {ref}")
            if len(file1_refs) > 5:
                print(f"  ... and {len(file1_refs) - 5} more")
        
        # File2 references
        file2_refs = []
        extract_refs(file2_element, file2_refs)
        if file2_refs:
            print(f"File2 - This element references: {len(file2_refs)} entities")
            for ref in file2_refs[:5]:  # Show first 5
                print(f"  → {ref}")
            if len(file2_refs) > 5:
                print(f"  ... and {len(file2_refs) - 5} more")
        
        # What references this element
        refs_to_file1 = self._find_references_to(identifier, self.file1_data)
        refs_to_file2 = self._find_references_to(identifier, self.file2_data)
        
        if refs_to_file1:
            print(f"\nFile1 - Referenced by: {len(refs_to_file1)} entities")
            for ref in refs_to_file1[:3]:
                print(f"  ← {ref.get('type', 'Unknown')} ({ref.get('globalId', 'no-id')})")
            if len(refs_to_file1) > 3:
                print(f"  ... and {len(refs_to_file1) - 3} more")
        
        if refs_to_file2:
            print(f"File2 - Referenced by: {len(refs_to_file2)} entities")
            for ref in refs_to_file2[:3]:
                print(f"  ← {ref.get('type', 'Unknown')} ({ref.get('globalId', 'no-id')})")
            if len(refs_to_file2) > 3:
                print(f"  ... and {len(refs_to_file2) - 3} more")
    
    def analyze_element_geometry(self, element: Dict, entities: Dict, file_type: str) -> Dict:
        """Analyze element geometry structure"""
        result = {
            'file_type': file_type,
            'name': element.get('name'),
            'type': element.get('type'),
            'globalId': element.get('globalId'),
            'has_representation': False,
            'representation_type': None,
            'geometry_items': [],
            'placement_info': None
        }
        
        # Check representation
        representation = element.get('representation')
        if representation:
            result['has_representation'] = True
            
            if isinstance(representation, dict):
                if 'type' in representation:
                    # Embedded representation
                    result['representation_type'] = 'embedded'
                    result['geometry_items'] = self._extract_embedded_geometry(representation)
                elif 'ref' in representation:
                    # Referenced representation
                    result['representation_type'] = 'referenced'
                    ref_entity = self.resolve_reference(representation, entities)
                    if ref_entity:
                        result['geometry_items'] = self._extract_referenced_geometry(ref_entity, entities)
        
        # Check placement
        placement = element.get('objectPlacement')
        if placement:
            result['placement_info'] = self._extract_placement_info(placement, entities)
        
        return result
    
    def _extract_embedded_geometry(self, representation: Dict) -> List[Dict]:
        """Extract geometry from embedded representation"""
        items = []
        if 'representations' in representation:
            for repr_item in representation['representations']:
                if isinstance(repr_item, dict):
                    if 'items' in repr_item:
                        for item in repr_item['items']:
                            items.append({
                                'type': item.get('type', 'unknown'),
                                'structure': 'embedded'
                            })
                    elif 'ref' in repr_item:
                        # This is a reference to another representation
                        items.append({
                            'type': 'reference',
                            'structure': 'embedded_reference',
                            'ref': repr_item['ref']
                        })
        return items
    
    def _extract_referenced_geometry(self, representation: Dict, entities: Dict) -> List[Dict]:
        """Extract geometry from referenced representation"""
        items = []
        if 'representations' in representation:
            for repr_ref in representation['representations']:
                repr_entity = self.resolve_reference(repr_ref, entities)
                if repr_entity and 'items' in repr_entity:
                    for item_ref in repr_entity['items']:
                        item_entity = self.resolve_reference(item_ref, entities)
                        if item_entity:
                            items.append({
                                'type': item_entity.get('type', 'unknown'),
                                'structure': 'referenced',
                                'id': item_entity.get('globalId')
                            })
        return items
    
    def _extract_placement_info(self, placement: Any, entities: Dict) -> Dict:
        """Extract placement information"""
        info = {'type': 'unknown'}
        
        if isinstance(placement, dict):
            if 'type' in placement:
                # Embedded placement
                info['type'] = 'embedded'
                info['placement_type'] = placement.get('type')
            elif 'ref' in placement:
                # Referenced placement
                info['type'] = 'referenced'
                placement_entity = self.resolve_reference(placement, entities)
                if placement_entity:
                    info['placement_type'] = placement_entity.get('type')
        
        return info
    
    def analyze_element_openings(self, element_id: str) -> Dict:
        """Analyze element openings in both files"""
        result = {
            'element_id': element_id,
            'file1': {'openings': [], 'filled_by': []},
            'file2': {'openings': [], 'filled_by': []}
        }
        
        # Check file1
        for entity in self.file1_data.get('data', []):
            if entity.get('type') == 'IfcRelVoidsElement':
                if entity.get('relatingBuildingElement', {}).get('ref') == element_id:
                    opening_id = entity.get('relatedOpeningElement', {}).get('ref')
                    result['file1']['openings'].append(opening_id)
                    
                    # Find what fills this opening
                    for fill_entity in self.file1_data.get('data', []):
                        if fill_entity.get('type') == 'IfcRelFillsElement':
                            if fill_entity.get('relatingOpeningElement', {}).get('ref') == opening_id:
                                filler_id = fill_entity.get('relatedBuildingElement', {}).get('ref')
                                filler = self.get_entity_by_id(filler_id, self.file1_entities)
                                if filler:
                                    result['file1']['filled_by'].append({
                                        'opening_id': opening_id,
                                        'filler_id': filler_id,
                                        'filler_name': filler.get('name'),
                                        'filler_type': filler.get('type')
                                    })
        
        # Check file2
        for entity in self.file2_data.get('data', []):
            if entity.get('type') == 'IfcRelVoidsElement':
                if entity.get('relatingBuildingElement', {}).get('ref') == element_id:
                    opening_id = entity.get('relatedOpeningElement', {}).get('ref')
                    result['file2']['openings'].append(opening_id)
                    
                    # Find what fills this opening
                    for fill_entity in self.file2_data.get('data', []):
                        if fill_entity.get('type') == 'IfcRelFillsElement':
                            if fill_entity.get('relatingOpeningElement', {}).get('ref') == opening_id:
                                filler_id = fill_entity.get('relatedBuildingElement', {}).get('ref')
                                filler = self.get_entity_by_id(filler_id, self.file2_entities)
                                if filler:
                                    result['file2']['filled_by'].append({
                                        'opening_id': opening_id,
                                        'filler_id': filler_id,
                                        'filler_name': filler.get('name'),
                                        'filler_type': filler.get('type')
                                    })
        
        return result
    
    def compare_elements(self, identifiers: List[str]):
        """Compare specific elements between files by name, globalId, or ref"""
        print("=" * 80)
        print("ELEMENT COMPARISON")
        print("=" * 80)
        
        for identifier in identifiers:
            print(f"\n--- {identifier} ---")
            
            # Find elements in both files
            file1_element = self.find_element(identifier, self.file1_data)
            file2_element = self.find_element(identifier, self.file2_data)
            
            # If not found as entity, try to find by globalId in indexed entities
            if not file1_element and identifier in self.file1_entities:
                file1_element = self.file1_entities[identifier]
            if not file2_element and identifier in self.file2_entities:
                file2_element = self.file2_entities[identifier]
            
            if not file1_element:
                print(f"❌ {identifier} not found in file1")
                # Check if it's referenced somewhere
                refs_in_file1 = self._find_references_to(identifier, self.file1_data)
                if refs_in_file1:
                    print(f"   But found {len(refs_in_file1)} references to this ID in file1")
                continue
                
            if not file2_element:
                print(f"❌ {identifier} not found in file2")
                # Check if it's referenced somewhere
                refs_in_file2 = self._find_references_to(identifier, self.file2_data)
                if refs_in_file2:
                    print(f"   But found {len(refs_in_file2)} references to this ID in file2")
                continue
            
            print(f"GlobalId: {file1_element.get('globalId')}")
            print(f"Type: {file1_element.get('type')}")
            print(f"Name: {file1_element.get('name', 'NO_NAME')}")
            
            # Show raw representation structure
            print("\nRaw representation structure:")
            print(f"File1: {file1_element.get('representation', {})}")
            print(f"File2: {file2_element.get('representation', {})}")
            
            # Analyze geometry
            file1_geometry = self.analyze_element_geometry(file1_element, self.file1_entities, 'file1')
            file2_geometry = self.analyze_element_geometry(file2_element, self.file2_entities, 'file2')
            
            # Compare
            print(f"\nGeometry analysis:")
            print(f"File1: {file1_geometry['representation_type']} representation, {len(file1_geometry['geometry_items'])} items")
            print(f"File2: {file2_geometry['representation_type']} representation, {len(file2_geometry['geometry_items'])} items")
            
            if file1_geometry['geometry_items'] != file2_geometry['geometry_items']:
                print("⚠️  Geometry items differ:")
                print(f"  File1: {file1_geometry['geometry_items']}")
                print(f"  File2: {file2_geometry['geometry_items']}")
            
            # Check placement
            if file1_geometry['placement_info'] != file2_geometry['placement_info']:
                print("⚠️  Placement differs:")
                print(f"  File1: {file1_geometry['placement_info']}")
                print(f"  File2: {file2_geometry['placement_info']}")
            
            # Show what references this element
            self._show_references_and_referents(identifier, file1_element, file2_element)
            
            # If element can have openings, analyze them
            element_type = file1_element.get('type')
            if element_type in ['IfcWallStandardCase', 'IfcWall', 'IfcSlab']:
                element_id = file1_element.get('globalId')
                openings_analysis = self.analyze_element_openings(element_id)
                
                print(f"\nOpenings Analysis:")
                print(f"File1 openings: {len(openings_analysis['file1']['openings'])}")
                print(f"File2 openings: {len(openings_analysis['file2']['openings'])}")
                
                if openings_analysis['file1']['filled_by']:
                    print(f"\nFile1 filled by:")
                    for filler in openings_analysis['file1']['filled_by']:
                        print(f"  {filler['filler_name']} ({filler['filler_type']})")
                
                if openings_analysis['file2']['filled_by']:
                    print(f"\nFile2 filled by:")
                    for filler in openings_analysis['file2']['filled_by']:
                        print(f"  {filler['filler_name']} ({filler['filler_type']})")

def main():
    parser = argparse.ArgumentParser(description='Compare ifcJSON files to find differences in building elements')
    parser.add_argument('file1', help='First ifcJSON file path')
    parser.add_argument('file2', help='Second ifcJSON file path')
    parser.add_argument('identifiers', nargs='+', help='Element identifiers to compare (can be name, globalId, or ref)')
    
    args = parser.parse_args()
    
    # Validate files exist
    if not Path(args.file1).exists():
        print(f"❌ File1 does not exist: {args.file1}")
        sys.exit(1)
    
    if not Path(args.file2).exists():
        print(f"❌ File2 does not exist: {args.file2}")
        sys.exit(1)
    
    print(f"📁 File1: {args.file1}")
    print(f"📁 File2: {args.file2}")
    print(f"🔍 Identifiers to compare: {args.identifiers}")
    print()
    
    comparator = IfcJsonComparator(args.file1, args.file2)
    comparator.compare_elements(args.identifiers)

if __name__ == "__main__":
    main()