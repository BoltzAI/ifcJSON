#!/usr/bin/env python3
"""
IFC Round-trip Batch Testing Script

Tests IFC → JSON → IFC conversion pipeline using official ifcJSON tools
with the minimal compatibility patches applied.

Usage:
    python batch_roundtrip_test.py input_folder output_folder [--verbose]

Examples:
    # Test all IFC files in ifcJSON/Samples/IFC_4.0/BuildingSMARTSpec/
    python batch_roundtrip_test.py ./ifcJSON/Samples/IFC_4.0/BuildingSMARTSpec/ ./batch_test_results/

    # Test with verbose output
    python batch_roundtrip_test.py ./ifc_files/ ./results/ --verbose
"""

import sys
import os
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
import traceback


class IFCRoundtripTester:
    def __init__(self, input_folder: str, output_folder: str, verbose: bool = False):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.verbose = verbose
        
        # Tools paths
        self.ifc2json_tool = "file_converters/ifc2json.py"
        self.json2ifc_tool = "file_converters/json2ifc.py"
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'conversion_times': [],
            'file_sizes': {},
            'errors': []
        }
        
        # Results storage
        self.results = []
        
    def setup_output_directory(self):
        """Create output directory structure"""
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.output_folder / "json_outputs").mkdir(exist_ok=True)
        (self.output_folder / "ifc_outputs").mkdir(exist_ok=True)
        (self.output_folder / "reports").mkdir(exist_ok=True)
        
        if self.verbose:
            print(f"📁 Created output directory structure: {self.output_folder}")
    
    def find_ifc_files(self) -> List[Path]:
        """Find all IFC files in input directory"""
        ifc_files = []
        for ext in ['*.ifc', '*.IFC']:
            ifc_files.extend(self.input_folder.glob(ext))
        
        if self.verbose:
            print(f"🔍 Found {len(ifc_files)} IFC files in {self.input_folder}")
            for ifc_file in ifc_files:
                print(f"   - {ifc_file.name}")
        
        return sorted(ifc_files)
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes"""
        try:
            return file_path.stat().st_size
        except:
            return 0
    
    def run_conversion_step(self, command: List[str], step_name: str) -> Tuple[bool, str, float]:
        """Run a conversion command and measure execution time"""
        start_time = time.perf_counter()
        
        try:
            if self.verbose:
                print(f"   🔄 Running: {' '.join(command)}")
            
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            if result.returncode == 0:
                return True, result.stdout.strip(), execution_time
            else:
                error_msg = f"Command failed with code {result.returncode}\\nSTDOUT: {result.stdout}\\nSTDERR: {result.stderr}"
                return False, error_msg, execution_time
                
        except subprocess.TimeoutExpired:
            return False, f"{step_name} timed out after 5 minutes", 300.0
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            return False, f"{step_name} failed: {str(e)}", execution_time
    
    def validate_ifc_file(self, ifc_path: Path) -> Dict[str, any]:
        """Basic validation of IFC file format"""
        validation = {
            'valid_format': False,
            'has_header': False,
            'has_entities': False,
            'entity_count': 0,
            'file_size': 0
        }
        
        try:
            validation['file_size'] = self.get_file_size(ifc_path)
            
            with open(ifc_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check IFC format
            validation['has_header'] = content.startswith('ISO-10303-21;')
            validation['has_entities'] = '#' in content and '=' in content
            validation['entity_count'] = content.count('#')
            validation['valid_format'] = (
                validation['has_header'] and 
                content.endswith('END-ISO-10303-21;\\n') and
                validation['has_entities']
            )
            
        except Exception as e:
            validation['error'] = str(e)
        
        return validation
    
    def test_single_file(self, ifc_file: Path) -> Dict[str, any]:
        """Test complete round-trip conversion for a single IFC file (IFC→JSON→IFC)"""
        file_stem = ifc_file.stem
        
        # Output paths
        json_output = self.output_folder / "json_outputs" / f"{file_stem}.json"
        ifc_output = self.output_folder / "ifc_outputs" / f"{file_stem}_roundtrip.ifc"
        
        # Initialize result record
        result = {
            'input_file': str(ifc_file),
            'file_name': ifc_file.name,
            'file_size_original': self.get_file_size(ifc_file),
            'success': False,
            'steps': {},
            'validation': {},
            'total_time': 0,
            'error': None
        }
        
        start_total_time = time.perf_counter()
        
        try:
            if self.verbose:
                print(f"🔄 Testing complete round-trip: {ifc_file.name}")
            
            # Step 1: IFC → JSON
            if self.verbose:
                print(f"   🔄 Step 1: IFC → JSON")
            
            step1_cmd = [
                'python', self.ifc2json_tool,
                '-i', str(ifc_file),
                '-o', str(json_output),
                '-v', '4'  # Use version 4 format
            ]
            
            success, output, exec_time = self.run_conversion_step(step1_cmd, "IFC→JSON")
            result['steps']['ifc_to_json'] = {
                'success': success,
                'execution_time': exec_time,
                'output': output
            }
            
            if not success:
                result['error'] = f"Step 1 failed: {output}"
                return result
            
            # Check JSON was created and get size
            if json_output.exists():
                result['file_size_json'] = self.get_file_size(json_output)
                if self.verbose:
                    print(f"   ✅ Step 1 complete: JSON created ({result['file_size_json']:,} bytes)")
            else:
                result['error'] = "Step 1: JSON file was not created"
                return result
            
            # Step 2: JSON → IFC (complete the round-trip)
            if self.verbose:
                print(f"   🔄 Step 2: JSON → IFC")
            
            step2_cmd = [
                'python', self.json2ifc_tool,
                '-i', str(json_output),
                '-o', str(ifc_output)
            ]
            
            success, output, exec_time = self.run_conversion_step(step2_cmd, "JSON→IFC")
            result['steps']['json_to_ifc'] = {
                'success': success,
                'execution_time': exec_time,
                'output': output
            }
            
            if not success:
                result['error'] = f"Step 2 failed: {output}"
                return result
            
            # Check IFC was created and validate
            if ifc_output.exists():
                result['file_size_roundtrip'] = self.get_file_size(ifc_output)
                result['validation'] = self.validate_ifc_file(ifc_output)
                
                if self.verbose:
                    print(f"   ✅ Step 2 complete: Round-trip IFC created ({result['file_size_roundtrip']:,} bytes)")
                    print(f"   📊 Valid format: {result['validation']['valid_format']}")
                    print(f"   📊 Entity count: {result['validation']['entity_count']}")
            else:
                result['error'] = "Step 2: Round-trip IFC file was not created"
                return result
            
            # Calculate size ratios
            if result['file_size_original'] > 0:
                result['json_size_ratio'] = result['file_size_json'] / result['file_size_original']
                result['roundtrip_size_ratio'] = result['file_size_roundtrip'] / result['file_size_original']
            
            result['success'] = True
            if self.verbose:
                print(f"   ✅ Complete round-trip successful!")
            
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
            result['traceback'] = traceback.format_exc()
            if self.verbose:
                print(f"   ❌ Error: {result['error']}")
        
        finally:
            end_total_time = time.perf_counter()
            result['total_time'] = end_total_time - start_total_time
        
        return result
    
    def generate_summary_report(self) -> str:
        """Generate summary statistics report"""
        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]
        
        report = f"""
# IFC Round-trip Testing Results

## Summary Statistics
- **Total Files Tested**: {len(self.results)}
- **Successful Conversions**: {len(successful)}
- **Failed Conversions**: {len(failed)}
- **Success Rate**: {(len(successful)/len(self.results)*100):.1f}%

## Performance Statistics
"""
        
        if successful:
            total_times = [r['total_time'] for r in successful]
            avg_time = sum(total_times) / len(total_times)
            
            report += f"""
- **Average Conversion Time**: {avg_time:.2f} seconds
- **Fastest Conversion**: {min(total_times):.2f} seconds  
- **Slowest Conversion**: {max(total_times):.2f} seconds
"""
            
            # Size analysis
            size_ratios_json = [r.get('json_size_ratio', 0) for r in successful if 'json_size_ratio' in r]
            size_ratios_roundtrip = [r.get('roundtrip_size_ratio', 0) for r in successful if 'roundtrip_size_ratio' in r]
            
            if size_ratios_json:
                avg_json_ratio = sum(size_ratios_json) / len(size_ratios_json)
                report += f"\\n- **Average JSON Size Ratio**: {avg_json_ratio:.2f}x original"
            
            if size_ratios_roundtrip:
                avg_roundtrip_ratio = sum(size_ratios_roundtrip) / len(size_ratios_roundtrip)
                report += f"\\n- **Average Round-trip Size Ratio**: {avg_roundtrip_ratio:.2f}x original"
        
        # Successful files
        if successful:
            report += "\\n\\n## ✅ Successful Conversions\\n"
            for result in successful:
                report += f"- **{result['file_name']}**: {result['total_time']:.2f}s"
                if 'validation' in result:
                    report += f" ({result['validation']['entity_count']} entities)"
                report += "\\n"
        
        # Failed files
        if failed:
            report += "\\n\\n## ❌ Failed Conversions\\n"
            for result in failed:
                report += f"- **{result['file_name']}**: {result.get('error', 'Unknown error')}\\n"
        
        return report
    
    def save_detailed_results(self):
        """Save detailed JSON results"""
        results_file = self.output_folder / "reports" / "detailed_results.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📊 Detailed results saved: {results_file}")
    
    def save_summary_report(self):
        """Save summary report"""
        summary_file = self.output_folder / "reports" / "summary_report.md"
        
        summary = self.generate_summary_report()
        
        with open(summary_file, 'w') as f:
            f.write(summary)
        
        print(f"📊 Summary report saved: {summary_file}")
    
    def run_batch_test(self):
        """Run batch testing on all IFC files - processing each file completely before moving to the next"""
        print(f"🚀 Starting IFC Round-trip Batch Testing")
        print(f"📁 Input folder: {self.input_folder}")
        print(f"📁 Output folder: {self.output_folder}")
        print(f"🔄 Processing Strategy: Complete round-trip per file (IFC→JSON→IFC)")
        
        # Setup
        self.setup_output_directory()
        ifc_files = self.find_ifc_files()
        
        if not ifc_files:
            print("❌ No IFC files found in input directory!")
            return False
        
        print(f"\\n🔄 Testing {len(ifc_files)} files...")
        print(f"📋 Each file will be processed through complete round-trip before moving to next file")
        
        # Test each file through complete round-trip
        for i, ifc_file in enumerate(ifc_files, 1):
            print(f"\\n[{i}/{len(ifc_files)}] {ifc_file.name}")
            print(f"   🔄 Starting complete round-trip transformation...")
            
            result = self.test_single_file(ifc_file)
            self.results.append(result)
            
            # Show completion status for this file
            if result['success']:
                print(f"   ✅ Round-trip completed successfully ({result['total_time']:.2f}s)")
            else:
                print(f"   ❌ Round-trip failed: {result.get('error', 'Unknown error')}")
        
        # Generate reports
        print(f"\\n📊 Generating reports...")
        self.save_detailed_results()
        self.save_summary_report()
        
        # Print summary
        successful_count = sum(1 for r in self.results if r['success'])
        print(f"\\n🎉 Batch testing completed!")
        print(f"✅ {successful_count}/{len(ifc_files)} files converted successfully")
        print(f"📁 Results saved in: {self.output_folder}")
        
        return successful_count == len(ifc_files)


def main():
    parser = argparse.ArgumentParser(
        description='Batch test IFC → JSON → IFC round-trip conversion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('input_folder', 
                       help='Input folder containing IFC files')
    
    parser.add_argument('output_folder',
                       help='Output folder for results and reports')
    
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate input folder
    if not Path(args.input_folder).exists():
        print(f"❌ Input folder does not exist: {args.input_folder}")
        sys.exit(1)
    
    # Run batch testing
    tester = IFCRoundtripTester(args.input_folder, args.output_folder, args.verbose)
    success = tester.run_batch_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()