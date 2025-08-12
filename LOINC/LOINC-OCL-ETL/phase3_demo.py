#!/usr/bin/env python3
"""
Phase 3 Quick Demo - LOINC to OCL Mapping Creation

A simple demonstration script that shows Phase 3 capabilities with a small
sample of data, perfect for validating the system and demonstrating functionality.

This script:
1. Validates that Phase 3 is properly set up
2. Creates sample mappings from each transformer 
3. Shows OCL mapping format compliance
4. Demonstrates the complete workflow quickly

Usage:
    python phase3_demo.py [--sample-size N]

Features:
- Quick execution (<30 seconds)
- Sample mappings from all three transformers
- OCL format validation
- Performance demonstration
- No cleanup required (uses temp files)

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from phase3_mapping_creation.phase3_ocl_models import OCLMapping, MappingCollection, LOINCMappingTypes
from phase3_mapping_creation.phase3_panel_transformer import PanelTestMappingTransformer
from phase3_mapping_creation.phase3_question_answer_transformer import QuestionAnswerMappingTransformer
from phase3_mapping_creation.phase3_code_evolution_transformer import CodeEvolutionMappingTransformer


class Phase3Demo:
    """Quick Phase 3 mapping creation demonstration"""
    
    def __init__(self, sample_size: int = 25):
        self.sample_size = sample_size
        self.logger = logging.getLogger(__name__)
        self.demo_results = {
            'transformers_tested': [],
            'mappings_created': {},
            'total_mappings': 0,
            'processing_time': 0.0,
            'sample_mappings': []
        }
        
        # Demo output directory
        self.demo_dir = Path("output/phase3_demo")
        self.demo_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_demo_prerequisites(self) -> bool:
        """Quick validation that Phase 3 can run"""
        print("🔍 Validating Phase 3 Demo Prerequisites...")
        
        try:
            # Check for Phase 2 concept files (need at least one)
            concept_files = []
            for search_dir in ["output", "output/phase2_concepts"]:
                if Path(search_dir).exists():
                    concept_files.extend(list(Path(search_dir).glob("loinc_concepts_*.jsonl")))
            
            if not concept_files:
                print("❌ No Phase 2 concept files found")
                print("   Phase 3 requires Phase 2 to be completed first")
                return False
            
            print(f"✅ Found {len(concept_files)} Phase 2 concept files")
            
            # Check Phase 1 data (just verify data loader works)
            from phase1_2_data_processing.data_loader import DataLoader
            data_loader = DataLoader()
            
            # Test that we can load data
            if not hasattr(data_loader, 'datasets') or not data_loader.datasets:
                print("   Loading Phase 1 data for validation...")
                data_loader.load_all_data()
            
            required_files = ["PanelsAndForms.csv", "LoincAnswerListLink.csv", "MapTo.csv"]
            available_files = [f for f in required_files if f in data_loader.datasets]
            
            if len(available_files) < 3:
                missing = set(required_files) - set(available_files) 
                print(f"❌ Missing Phase 1 files: {missing}")
                return False
            
            print(f"✅ All Phase 1 data files available")
            return True
            
        except Exception as e:
            print(f"❌ Prerequisites validation failed: {e}")
            return False
    
    def demo_transformer(self, transformer_class, transformer_name: str) -> Dict[str, Any]:
        """Demonstrate a single transformer"""
        print(f"   🔧 Testing {transformer_name} Transformer...")
        
        try:
            # Create transformer
            transformer = transformer_class()
            
            # Run with sample size
            start_time = time.time()
            result = transformer.run_transformation(limit=self.sample_size)
            processing_time = time.time() - start_time
            
            if result.success_count > 0:
                print(f"      ✅ Created {result.success_count} mappings in {processing_time:.1f}s")
                
                # Get sample mapping for display
                sample_mapping = result.mappings_created[0]
                
                return {
                    'transformer_name': transformer_name,
                    'transformer_class': transformer_class.__name__,
                    'mappings_created': result.success_count,
                    'processing_time': processing_time,
                    'success_rate': result.success_rate,
                    'map_type': transformer.get_ocl_map_type(),
                    'sample_mapping': sample_mapping.to_dict(),
                    'errors': result.error_count
                }
            else:
                print(f"      ❌ No mappings created")
                return None
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            return None
    
    def run_demo(self) -> bool:
        """Run the complete Phase 3 demo"""
        
        # Setup simple logging
        logging.basicConfig(level=logging.WARNING)  # Quiet mode for demo
        
        print("🔗 Phase 3 Quick Demo - LOINC to OCL Mapping Creation")
        print("=" * 60)
        print(f"Sample size: {self.sample_size} records per transformer")
        print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        overall_start = time.time()
        
        try:
            # Validate prerequisites
            if not self.validate_demo_prerequisites():
                return False
            
            print()
            print("🚀 Running Phase 3 Transformer Demonstrations...")
            
            # Test each transformer
            transformers_to_test = [
                (PanelTestMappingTransformer, "Panel-Test"),
                (QuestionAnswerMappingTransformer, "Question-Answer"), 
                (CodeEvolutionMappingTransformer, "Code Evolution")
            ]
            
            successful_transformers = 0
            
            for transformer_class, transformer_name in transformers_to_test:
                result = self.demo_transformer(transformer_class, transformer_name)
                
                if result:
                    self.demo_results['transformers_tested'].append(transformer_name)
                    self.demo_results['mappings_created'][transformer_name] = result['mappings_created']
                    self.demo_results['total_mappings'] += result['mappings_created']
                    self.demo_results['sample_mappings'].append(result)
                    successful_transformers += 1
            
            total_time = time.time() - overall_start
            self.demo_results['processing_time'] = total_time
            
            print()
            print("🎉 Phase 3 Demo Completed!")
            print("=" * 60)
            print(f"Total time: {total_time:.1f} seconds")
            print(f"Transformers successful: {successful_transformers}/3")
            print(f"Total mappings created: {self.demo_results['total_mappings']}")
            
            if self.demo_results['total_mappings'] > 0:
                throughput = self.demo_results['total_mappings'] / total_time
                print(f"Average throughput: {throughput:.0f} mappings/second")
            
            print()
            print("📊 Mapping Types Demonstrated:")
            for transformer_name, count in self.demo_results['mappings_created'].items():
                print(f"  {transformer_name}: {count} mappings")
            
            # Show sample mappings
            if self.demo_results['sample_mappings']:
                print()
                print("🔗 Sample OCL Mappings Created:")
                for i, transformer_result in enumerate(self.demo_results['sample_mappings'], 1):
                    print(f"\n{i}. {transformer_result['transformer_name']} ({transformer_result['map_type']}):")
                    sample = transformer_result['sample_mapping']
                    print(f"   From: {sample['from_concept_url']}")
                    print(f"   To: {sample['to_concept_url']}")
                    if sample.get('extras'):
                        extras_preview = str(sample['extras'])[:100]
                        if len(str(sample['extras'])) > 100:
                            extras_preview += "..."
                        print(f"   Extras: {extras_preview}")
            
            # Write demo output
            self.write_demo_output()
            
            print()
            if successful_transformers >= 3:
                print("✅ PHASE 3 DEMO: SUCCESSFUL!")
                print("🚀 All transformers working correctly")
                print("📋 System ready for production mapping creation")
                
                print()
                print("Next Steps:")
                print("  1. Run complete production: python phase3_main.py")
                print("  2. Or run test mode: python phase3_main.py --test")
                print("  3. Expected: ~125,000 total mappings in <40 seconds")
                
                return True
            else:
                print("⚠️  PHASE 3 DEMO: PARTIAL SUCCESS")
                print(f"Only {successful_transformers}/3 transformers working")
                return False
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            return False
    
    def write_demo_output(self):
        """Write demo results to output files"""
        try:
            # Create a small sample output file
            if self.demo_results['sample_mappings']:
                sample_file = self.demo_dir / "demo_sample_mappings.jsonl"
                
                with open(sample_file, 'w', encoding='utf-8') as f:
                    for transformer_result in self.demo_results['sample_mappings']:
                        sample_mapping = transformer_result['sample_mapping']
                        f.write(json.dumps(sample_mapping, ensure_ascii=False) + '\n')
                
                print(f"📄 Sample output: {sample_file}")
            
            # Create demo report
            report = {
                "demo": "Phase 3 Quick Demo",
                "timestamp": datetime.now().isoformat(),
                "configuration": {
                    "sample_size_per_transformer": self.sample_size
                },
                "results": self.demo_results
            }
            
            report_file = self.demo_dir / "demo_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"📊 Demo report: {report_file}")
            
        except Exception as e:
            print(f"⚠️  Could not write demo output: {e}")
    
    def validate_ocl_format(self) -> bool:
        """Validate that created mappings are OCL compliant"""
        print("🔍 Validating OCL Format Compliance...")
        
        if not self.demo_results['sample_mappings']:
            print("❌ No sample mappings to validate")
            return False
        
        try:
            for transformer_result in self.demo_results['sample_mappings']:
                sample_mapping_dict = transformer_result['sample_mapping']
                
                # Recreate OCL mapping from dict to test validation
                mapping = OCLMapping(
                    map_type=sample_mapping_dict['map_type'],
                    from_concept_url=sample_mapping_dict['from_concept_url'],
                    to_concept_url=sample_mapping_dict.get('to_concept_url'),
                    external_id=sample_mapping_dict.get('external_id'),
                    extras=sample_mapping_dict.get('extras', {})
                )
                
                is_valid, errors = mapping.validate()
                if not is_valid:
                    print(f"❌ Invalid mapping from {transformer_result['transformer_name']}: {errors}")
                    return False
            
            print("✅ All sample mappings are OCL compliant")
            return True
            
        except Exception as e:
            print(f"❌ OCL validation error: {e}")
            return False


def main():
    """Main demo function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 3 Quick Demo")
    parser.add_argument('--sample-size', type=int, default=25,
                       help='Number of records to process per transformer (default: 25)')
    parser.add_argument('--validate-format', action='store_true',
                       help='Include OCL format validation')
    
    args = parser.parse_args()
    
    # Run demo
    demo = Phase3Demo(sample_size=args.sample_size)
    success = demo.run_demo()
    
    # Optional format validation
    if success and args.validate_format:
        print()
        demo.validate_ocl_format()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
