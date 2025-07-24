#!/usr/bin/env python3
"""
Geometry Context Analysis Tool

This tool analyzes the IfcGeometricRepresentationContext and IfcGeometricRepresentationSubContext 
handling issues in the round-trip conversion pipeline, specifically focusing on why asset files 
have empty geometry data arrays.

The tool investigates:
1. How IfcGeometricRepresentationContext is handled in Step 1 (IFC→JSON)
2. How geometry extraction works in Step 2 (JSON→Simplified+Assets)
3. How geometry restoration works in Step 3 (Simplified+Assets→JSON)
4. How IfcGeometricRepresentationContext is restored in Step 4 (JSON→IFC)

Usage:
    python analyze_geometry_context_issues.py /path/to/test/files
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import traceback

class GeometryContextAnalyzer:
    def __init__(self, test_dir: str):
        self.test_dir = Path(test_dir)
        self.issues = []
        
    def analyze_pipeline(self, file_stem: str) -> Dict[str, Any]:
        """Analyze the complete pipeline for geometry context issues"""
        results = {
            'file_stem': file_stem,
            'step1_contexts': {},
            'step2_assets': {},
            'step3_contexts': {},
            'step4_contexts': {},
            'issues': [],
            'summary': {}
        }
        
        print(f"\n🔍 Analyzing {file_stem} - Geometry Context Pipeline")
        print("=" * 80)
        
        try:
            # Step 1: Analyze original ifcJSON contexts
            step1_file = self.test_dir / "step1_official_json" / f"{file_stem}.json"
            if step1_file.exists():
                results['step1_contexts'] = self._analyze_step1_contexts(step1_file)
                print(f"✅ Step 1 Analysis: {len(results['step1_contexts']['contexts'])} contexts found")
            else:
                results['issues'].append("Step 1 file not found")
                print(f"❌ Step 1 file not found: {step1_file}")
            
            # Step 2: Analyze simplified JSON and assets
            step2_file = self.test_dir / "step2_simplified_json" / f"{file_stem}_simplified.json"
            assets_dir = self.test_dir / "assets" / file_stem
            if step2_file.exists() and assets_dir.exists():
                results['step2_assets'] = self._analyze_step2_assets(step2_file, assets_dir)
                print(f"✅ Step 2 Analysis: {len(results['step2_assets']['asset_files'])} assets created")
            else:
                results['issues'].append("Step 2 files not found")
                print(f"❌ Step 2 files not found: {step2_file} or {assets_dir}")
            
            # Step 3: Analyze restored ifcJSON contexts
            step3_file = self.test_dir / "step3_expanded_json" / f"{file_stem}_expanded.json"
            if step3_file.exists():
                results['step3_contexts'] = self._analyze_step3_contexts(step3_file)
                print(f"✅ Step 3 Analysis: {len(results['step3_contexts']['contexts'])} contexts found")
            else:
                results['issues'].append("Step 3 file not found")
                print(f"❌ Step 3 file not found: {step3_file}")
            
            # Compare and identify issues
            results['summary'] = self._compare_and_summarize(results)
            
            return results
            
        except Exception as e:
            results['issues'].append(f"Analysis error: {str(e)}")
            print(f"❌ Analysis error: {str(e)}")
            traceback.print_exc()
            return results
    
    def _analyze_step1_contexts(self, step1_file: Path) -> Dict[str, Any]:
        """Analyze IfcGeometricRepresentationContext in Step 1 ifcJSON"""
        print(f"\n📊 Step 1: Analyzing {step1_file}")
        
        with open(step1_file, 'r') as f:
            data = json.load(f)
        
        contexts = []
        sub_contexts = []
        shape_representations = []
        
        for entity in data.get('data', []):
            entity_type = entity.get('type', '')
            
            if entity_type == 'IfcGeometricRepresentationContext':
                contexts.append({
                    'globalId': entity.get('globalId'),
                    'contextType': entity.get('contextType'),
                    'coordinateSpaceDimension': entity.get('coordinateSpaceDimension'),
                    'precision': entity.get('precision'),
                    'worldCoordinateSystem': entity.get('worldCoordinateSystem'),
                    'representationsInContext': entity.get('representationsInContext', [])
                })
            elif entity_type == 'IfcGeometricRepresentationSubContext':
                sub_contexts.append({
                    'globalId': entity.get('globalId'),
                    'contextIdentifier': entity.get('contextIdentifier'),
                    'contextType': entity.get('contextType'),
                    'parentContext': entity.get('parentContext'),
                    'representationsInContext': entity.get('representationsInContext', [])
                })
            elif entity_type == 'IfcShapeRepresentation':
                shape_representations.append({
                    'globalId': entity.get('globalId'),
                    'representationIdentifier': entity.get('representationIdentifier'),
                    'representationType': entity.get('representationType'),
                    'contextOfItems': entity.get('contextOfItems'),
                    'items': entity.get('items', [])
                })
        
        print(f"   📋 Found {len(contexts)} IfcGeometricRepresentationContext entities")
        print(f"   📋 Found {len(sub_contexts)} IfcGeometricRepresentationSubContext entities")
        print(f"   📋 Found {len(shape_representations)} IfcShapeRepresentation entities")
        
        return {
            'contexts': contexts,
            'sub_contexts': sub_contexts,
            'shape_representations': shape_representations,
            'total_entities': len(data.get('data', [])),
            'file_size': step1_file.stat().st_size
        }
    
    def _analyze_step2_assets(self, step2_file: Path, assets_dir: Path) -> Dict[str, Any]:
        """Analyze asset creation in Step 2"""
        print(f"\n📊 Step 2: Analyzing {step2_file} and {assets_dir}")
        
        # Analyze simplified JSON
        with open(step2_file, 'r') as f:
            simplified_data = json.load(f)
        
        elements_with_assets = []
        total_elements = 0
        
        # Count elements with geometry assets
        for storey in simplified_data.get('building', {}).get('storeys', []):
            for element_type, elements in storey.get('elements', {}).items():
                for element in elements:
                    total_elements += 1
                    if 'geometry' in element and element['geometry'].get('geometryType') == 'asset_library':
                        elements_with_assets.append({
                            'element_type': element_type,
                            'element_name': element.get('name'),
                            'asset_id': element['geometry'].get('assetId'),
                            'library_source': element['geometry'].get('librarySource')
                        })
        
        # Analyze asset files
        asset_files = []
        empty_assets = []
        
        for asset_file in assets_dir.glob('*.json'):
            try:
                with open(asset_file, 'r') as f:
                    asset_data = json.load(f)
                
                data_entities = asset_data.get('data', [])
                file_info = {
                    'file_name': asset_file.name,
                    'file_size': asset_file.stat().st_size,
                    'entity_count': len(data_entities),
                    'entity_types': {}
                }
                
                for entity in data_entities:
                    entity_type = entity.get('type', 'Unknown')
                    file_info['entity_types'][entity_type] = file_info['entity_types'].get(entity_type, 0) + 1
                
                asset_files.append(file_info)
                
                if len(data_entities) == 0:
                    empty_assets.append(asset_file.name)
                    
            except Exception as e:
                print(f"   ⚠️  Error reading {asset_file}: {e}")
        
        print(f"   📋 Found {len(elements_with_assets)} elements with asset geometry")
        print(f"   📋 Found {len(asset_files)} asset files")
        print(f"   📋 Found {len(empty_assets)} empty asset files")
        
        return {
            'elements_with_assets': elements_with_assets,
            'total_elements': total_elements,
            'asset_files': asset_files,
            'empty_assets': empty_assets,
            'simplified_file_size': step2_file.stat().st_size
        }
    
    def _analyze_step3_contexts(self, step3_file: Path) -> Dict[str, Any]:
        """Analyze IfcGeometricRepresentationContext in Step 3 expanded JSON"""
        print(f"\n📊 Step 3: Analyzing {step3_file}")
        
        with open(step3_file, 'r') as f:
            data = json.load(f)
        
        contexts = []
        sub_contexts = []
        shape_representations = []
        
        for entity in data.get('data', []):
            entity_type = entity.get('type', '')
            
            if entity_type == 'IfcGeometricRepresentationContext':
                contexts.append({
                    'globalId': entity.get('globalId'),
                    'contextType': entity.get('contextType'),
                    'coordinateSpaceDimension': entity.get('coordinateSpaceDimension'),
                    'precision': entity.get('precision')
                })
            elif entity_type == 'IfcGeometricRepresentationSubContext':
                sub_contexts.append({
                    'globalId': entity.get('globalId'),
                    'contextIdentifier': entity.get('contextIdentifier'),
                    'contextType': entity.get('contextType'),
                    'parentContext': entity.get('parentContext')
                })
            elif entity_type == 'IfcShapeRepresentation':
                shape_representations.append({
                    'globalId': entity.get('globalId'),
                    'representationIdentifier': entity.get('representationIdentifier'),
                    'representationType': entity.get('representationType'),
                    'contextOfItems': entity.get('contextOfItems')
                })
        
        print(f"   📋 Found {len(contexts)} IfcGeometricRepresentationContext entities")
        print(f"   📋 Found {len(sub_contexts)} IfcGeometricRepresentationSubContext entities")
        print(f"   📋 Found {len(shape_representations)} IfcShapeRepresentation entities")
        
        return {
            'contexts': contexts,
            'sub_contexts': sub_contexts,
            'shape_representations': shape_representations,
            'total_entities': len(data.get('data', [])),
            'file_size': step3_file.stat().st_size
        }
    
    def _compare_and_summarize(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare results across steps and identify issues"""
        print(f"\n🔍 Comparing Results and Identifying Issues")
        
        step1_contexts = results['step1_contexts']
        step2_assets = results['step2_assets']
        step3_contexts = results['step3_contexts']
        
        summary = {
            'context_loss': {},
            'asset_issues': {},
            'geometry_loss': {},
            'critical_issues': []
        }
        
        # Compare contexts between Step 1 and Step 3
        if step1_contexts and step3_contexts:
            step1_count = len(step1_contexts['contexts']) + len(step1_contexts['sub_contexts'])
            step3_count = len(step3_contexts['contexts']) + len(step3_contexts['sub_contexts'])
            
            summary['context_loss'] = {
                'step1_total': step1_count,
                'step3_total': step3_count,
                'lost_contexts': step1_count - step3_count,
                'loss_percentage': ((step1_count - step3_count) / step1_count * 100) if step1_count > 0 else 0
            }
            
            if step1_count > step3_count:
                summary['critical_issues'].append(f"Lost {step1_count - step3_count} geometric contexts")
        
        # Analyze asset issues
        if step2_assets:
            empty_count = len(step2_assets['empty_assets'])
            total_count = len(step2_assets['asset_files'])
            
            summary['asset_issues'] = {
                'total_assets': total_count,
                'empty_assets': empty_count,
                'empty_percentage': (empty_count / total_count * 100) if total_count > 0 else 0
            }
            
            if empty_count > 0:
                summary['critical_issues'].append(f"{empty_count} out of {total_count} assets are empty")
        
        # Analyze geometry loss
        if step1_contexts and step3_contexts:
            step1_shapes = len(step1_contexts['shape_representations'])
            step3_shapes = len(step3_contexts['shape_representations'])
            
            summary['geometry_loss'] = {
                'step1_shapes': step1_shapes,
                'step3_shapes': step3_shapes,
                'lost_shapes': step1_shapes - step3_shapes,
                'loss_percentage': ((step1_shapes - step3_shapes) / step1_shapes * 100) if step1_shapes > 0 else 0
            }
            
            if step1_shapes > step3_shapes:
                summary['critical_issues'].append(f"Lost {step1_shapes - step3_shapes} shape representations")
        
        # Print summary
        print(f"   📊 Context Loss: {summary.get('context_loss', {}).get('lost_contexts', 0)} contexts")
        print(f"   📊 Asset Issues: {summary.get('asset_issues', {}).get('empty_assets', 0)} empty assets")
        print(f"   📊 Geometry Loss: {summary.get('geometry_loss', {}).get('lost_shapes', 0)} shape representations")
        print(f"   📊 Critical Issues: {len(summary['critical_issues'])}")
        
        return summary
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a detailed analysis report"""
        report = f"""
# Geometry Context Analysis Report

## File: {results['file_stem']}

### Summary
"""
        
        if results['summary']:
            summary = results['summary']
            
            # Context Loss Section
            if 'context_loss' in summary:
                context_loss = summary['context_loss']
                report += f"""
### Context Loss Analysis
- **Step 1 Total Contexts**: {context_loss.get('step1_total', 0)}
- **Step 3 Total Contexts**: {context_loss.get('step3_total', 0)}
- **Lost Contexts**: {context_loss.get('lost_contexts', 0)}
- **Loss Percentage**: {context_loss.get('loss_percentage', 0):.1f}%
"""
            
            # Asset Issues Section
            if 'asset_issues' in summary:
                asset_issues = summary['asset_issues']
                report += f"""
### Asset Issues Analysis
- **Total Assets**: {asset_issues.get('total_assets', 0)}
- **Empty Assets**: {asset_issues.get('empty_assets', 0)}
- **Empty Percentage**: {asset_issues.get('empty_percentage', 0):.1f}%
"""
            
            # Geometry Loss Section
            if 'geometry_loss' in summary:
                geometry_loss = summary['geometry_loss']
                report += f"""
### Geometry Loss Analysis
- **Step 1 Shape Representations**: {geometry_loss.get('step1_shapes', 0)}
- **Step 3 Shape Representations**: {geometry_loss.get('step3_shapes', 0)}
- **Lost Shape Representations**: {geometry_loss.get('lost_shapes', 0)}
- **Loss Percentage**: {geometry_loss.get('loss_percentage', 0):.1f}%
"""
            
            # Critical Issues Section
            if 'critical_issues' in summary and summary['critical_issues']:
                report += f"""
### Critical Issues
"""
                for issue in summary['critical_issues']:
                    report += f"- {issue}\n"
        
        # Issues Section
        if results['issues']:
            report += f"""
### Processing Issues
"""
            for issue in results['issues']:
                report += f"- {issue}\n"
        
        return report


def main():
    """Main analysis function"""
    if len(sys.argv) != 2:
        print("Usage: python analyze_geometry_context_issues.py <test_directory>")
        sys.exit(1)
    
    test_dir = sys.argv[1]
    
    if not os.path.exists(test_dir):
        print(f"Error: Directory {test_dir} does not exist")
        sys.exit(1)
    
    analyzer = GeometryContextAnalyzer(test_dir)
    
    # Find all test files
    step1_dir = Path(test_dir) / "step1_official_json"
    if not step1_dir.exists():
        print(f"Error: Step 1 directory {step1_dir} does not exist")
        sys.exit(1)
    
    json_files = list(step1_dir.glob("*.json"))
    if not json_files:
        print(f"Error: No JSON files found in {step1_dir}")
        sys.exit(1)
    
    print(f"🔍 Found {len(json_files)} files to analyze")
    
    # Analyze each file
    all_results = []
    for json_file in json_files:
        file_stem = json_file.stem
        results = analyzer.analyze_pipeline(file_stem)
        all_results.append(results)
        
        # Generate and save report
        report = analyzer.generate_report(results)
        report_file = Path(test_dir) / f"{file_stem}_geometry_context_analysis.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"📋 Report saved: {report_file}")
    
    # Generate overall summary
    print(f"\n🎉 Analysis Complete!")
    print(f"📊 Analyzed {len(all_results)} files")
    
    # Count issues across all files
    total_critical_issues = sum(len(r['summary'].get('critical_issues', [])) for r in all_results)
    print(f"📊 Total Critical Issues: {total_critical_issues}")
    
    if total_critical_issues > 0:
        print("\n🚨 CRITICAL ISSUES FOUND:")
        for result in all_results:
            if result['summary'].get('critical_issues'):
                print(f"   {result['file_stem']}: {len(result['summary']['critical_issues'])} issues")


if __name__ == "__main__":
    main()