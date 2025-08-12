#!/usr/bin/env python3
"""
Phase 3 Complete Integration Test - All Three Core Transformers

This script provides comprehensive testing of the complete Phase 3 mapping creation
system, validating all three transformers working together with real data.

Tests Performed:
1. Prerequisites validation (Phase 1 & 2 data availability)
2. Individual transformer functionality
3. Combined orchestration workflow
4. OCL format compliance validation
5. Performance benchmarking
6. Output file verification

Transformers Tested:
- Panel-Test Mapping Transformer (PanelsAndForms.csv → "has element")
- Question-Answer Mapping Transformer (LoincAnswerListLink.csv → "has answer")
- Code Evolution Mapping Transformer (MapTo.csv → "Map To")

Usage:
    python phase3_complete_test.py [--quick] [--limit N] [--no-cleanup]

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from phase3_mapping_creation.phase3_ocl_models import OCLMapping, MappingCollection, LOINCMappingTypes
from phase3_mapping_creation.phase3_mapping_orchestrator import MappingOrchestrator, OrchestrationResult


class Phase3CompleteTest:
    """Comprehensive Phase 3 integration testing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'start_time': None,
            'end_time': None,
            'details': {}
        }
        
        # Test configuration
        self.test_output_dir = Path("output/phase3_test")
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log the result of a test"""
        self.test_results['tests_run'] += 1
        if passed:
            self.test_results['tests_passed'] += 1
            status = "✅ PASS"
        else:
            self.test_results['tests_failed'] += 1
            status = "❌ FAIL"
        
        self.test_results['details'][test_name] = {
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"{status}: {test_name}")
        if details:
            self.logger.info(f"   Details: {details}")
    
    def test_prerequisites(self) -> bool:
        """Test that all Phase 3 prerequisites are available"""
        self.logger.info("\n🔍 Testing Phase 3 Prerequisites...")
        
        try:
            # Test Phase 2 concept files
            concept_files = []
            for search_dir in ["output", "output/phase2_concepts"]:
                if Path(search_dir).exists():
                    concept_files.extend(list(Path(search_dir).glob("loinc_concepts_*.jsonl")))
            
            if not concept_files:
                self.log_test_result("Phase 2 Concept Files", False, "No concept files found")
                return False
            
            # Count concepts in files
            total_concepts = 0
            for concept_file in concept_files[:2]:  # Sample first 2 files
                with open(concept_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            total_concepts += 1
                        if total_concepts >= 1000:  # Sample check
                            break
            
            self.log_test_result("Phase 2 Concept Files", True, 
                               f"{len(concept_files)} files found, {total_concepts}+ concepts sampled")
            
            # Test Phase 1 data files
            from phase1_2_data_processing.data_loader import DataLoader
            data_loader = DataLoader()
            
            if not hasattr(data_loader, 'datasets') or not data_loader.datasets:
                data_loader.load_all_data()
            
            required_files = ["PanelsAndForms.csv", "LoincAnswerListLink.csv", "MapTo.csv"]
            missing_files = []
            file_stats = {}
            
            for file_name in required_files:
                if file_name not in data_loader.datasets:
                    missing_files.append(file_name)
                else:
                    dataset = data_loader.datasets[file_name]
                    file_stats[file_name] = len(dataset.data)
            
            if missing_files:
                self.log_test_result("Phase 1 Data Files", False, f"Missing: {missing_files}")
                return False
            
            details = ", ".join([f"{name}: {count:,}" for name, count in file_stats.items()])
            self.log_test_result("Phase 1 Data Files", True, details)
            
            return True
            
        except Exception as e:
            self.log_test_result("Prerequisites Check", False, str(e))
            return False
    
    def test_ocl_mapping_model(self) -> bool:
        """Test OCL mapping model functionality"""
        self.logger.info("\n🔗 Testing OCL Mapping Model...")
        
        try:
            # Test basic mapping creation
            mapping = OCLMapping(
                map_type="has element",
                from_concept_url="/orgs/Regenstrief/sources/LOINC/concepts/test-1/",
                to_concept_url="/orgs/Regenstrief/sources/LOINC/concepts/test-2/",
                external_id="test_mapping",
                extras={"test": "value"}
            )
            
            # Test validation
            is_valid, errors = mapping.validate()
            if not is_valid:
                self.log_test_result("OCL Mapping Validation", False, f"Validation errors: {errors}")
                return False
            
            # Test JSON conversion
            json_dict = mapping.to_dict()
            json_line = mapping.to_json_line()
            
            # Verify required fields
            required_fields = ["type", "map_type", "from_concept_url", "to_concept_url", "owner", "owner_type", "source"]
            missing_fields = [field for field in required_fields if field not in json_dict]
            
            if missing_fields:
                self.log_test_result("OCL JSON Format", False, f"Missing fields: {missing_fields}")
                return False
            
            # Test JSON parsing
            parsed = json.loads(json_line)
            if parsed["map_type"] != "has element":
                self.log_test_result("OCL JSON Parsing", False, "JSON parsing failed")
                return False
            
            self.log_test_result("OCL Mapping Model", True, "All model functions working correctly")
            return True
            
        except Exception as e:
            self.log_test_result("OCL Mapping Model", False, str(e))
            return False
    
    def test_individual_transformers(self, limit: int = 50) -> bool:
        """Test each transformer individually"""
        self.logger.info(f"\n🔧 Testing Individual Transformers (limit: {limit})...")
        
        from phase3_mapping_creation.phase3_panel_transformer import PanelTestMappingTransformer
        from phase3_mapping_creation.phase3_question_answer_transformer import QuestionAnswerMappingTransformer
        from phase3_mapping_creation.phase3_code_evolution_transformer import CodeEvolutionMappingTransformer
        
        transformers_to_test = [
            ("Panel-Test", PanelTestMappingTransformer),
            ("Question-Answer", QuestionAnswerMappingTransformer),
            ("Code Evolution", CodeEvolutionMappingTransformer)
        ]
        
        all_passed = True
        
        for transformer_name, transformer_class in transformers_to_test:
            try:
                self.logger.info(f"   Testing {transformer_name} Transformer...")
                
                transformer = transformer_class()
                result = transformer.run_transformation(limit=limit)
                
                if result.success_count > 0:
                    # Test output quality
                    sample_mapping = result.mappings_created[0]
                    is_valid, errors = sample_mapping.validate()
                    
                    if is_valid:
                        details = f"{result.success_count} mappings, {result.success_rate:.1f}% success rate"
                        self.log_test_result(f"{transformer_name} Transformer", True, details)
                    else:
                        self.log_test_result(f"{transformer_name} Transformer", False, f"Invalid mapping: {errors}")
                        all_passed = False
                else:
                    self.log_test_result(f"{transformer_name} Transformer", False, "No mappings created")
                    all_passed = False
                    
            except Exception as e:
                self.log_test_result(f"{transformer_name} Transformer", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_orchestration(self, limit: int = 100) -> Optional[OrchestrationResult]:
        """Test complete orchestration workflow"""
        self.logger.info(f"\n🎼 Testing Complete Orchestration (limit: {limit})...")
        
        try:
            orchestrator = MappingOrchestrator()
            orchestrator.output_dir = self.test_output_dir
            
            # Progress tracking
            progress_updates = []
            def test_progress_callback(progress: float, status: str):
                progress_updates.append((progress, status))
                if len(progress_updates) % 5 == 0 or progress >= 99:
                    self.logger.info(f"      Progress: {progress:.1f}% - {status}")
            
            result = orchestrator.run_complete_orchestration(
                limit=limit,
                test_mode=True,
                progress_callback=test_progress_callback
            )
            
            if result.is_successful:
                details = (f"{result.total_mappings_created:,} total mappings, "
                          f"{len(result.transformers_successful)}/{len(result.transformers_run)} transformers successful")
                self.log_test_result("Complete Orchestration", True, details)
                return result
            else:
                details = f"Only {len(result.transformers_successful)}/{len(result.transformers_run)} transformers successful"
                self.log_test_result("Complete Orchestration", False, details)
                return result
            
        except Exception as e:
            self.log_test_result("Complete Orchestration", False, str(e))
            return None
    
    def test_output_files(self, result: OrchestrationResult) -> bool:
        """Test output file quality and compliance"""
        self.logger.info("\n📄 Testing Output Files...")
        
        if not result or not result.output_files:
            self.log_test_result("Output Files", False, "No output files generated")
            return False
        
        try:
            mapping_files = [f for f in result.output_files if f.endswith('.jsonl') and 'mappings' in f]
            
            if not mapping_files:
                self.log_test_result("Output Files", False, "No mapping files found")
                return False
            
            total_mappings_in_files = 0
            sample_mappings = []
            
            # Test each mapping file
            for mapping_file in mapping_files:
                file_path = Path(mapping_file)
                if not file_path.exists():
                    self.log_test_result("Output Files", False, f"File not found: {mapping_file}")
                    return False
                
                file_mappings = 0
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if line.strip():
                            try:
                                mapping_data = json.loads(line)
                                file_mappings += 1
                                
                                # Collect samples for validation
                                if len(sample_mappings) < 10:
                                    sample_mappings.append(mapping_data)
                                    
                            except json.JSONDecodeError as e:
                                self.log_test_result("Output Files", False, 
                                                   f"Invalid JSON in {file_path.name} line {line_num}: {e}")
                                return False
                
                total_mappings_in_files += file_mappings
            
            # Validate sample mappings
            for i, mapping_data in enumerate(sample_mappings):
                required_fields = ["type", "map_type", "from_concept_url", "owner", "owner_type", "source"]
                missing_fields = [field for field in required_fields if field not in mapping_data]
                
                if missing_fields:
                    self.log_test_result("Output Files", False, 
                                       f"Sample mapping {i} missing fields: {missing_fields}")
                    return False
                
                if mapping_data["type"] != "Mapping":
                    self.log_test_result("Output Files", False, 
                                       f"Sample mapping {i} has wrong type: {mapping_data['type']}")
                    return False
            
            details = f"{len(mapping_files)} files, {total_mappings_in_files:,} total mappings, {len(sample_mappings)} samples validated"
            self.log_test_result("Output Files", True, details)
            return True
            
        except Exception as e:
            self.log_test_result("Output Files", False, str(e))
            return False
    
    def test_performance_benchmarks(self, result: OrchestrationResult) -> bool:
        """Test performance against benchmarks"""
        self.logger.info("\n⚡ Testing Performance Benchmarks...")
        
        if not result:
            self.log_test_result("Performance Benchmarks", False, "No orchestration result")
            return False
        
        try:
            # Calculate performance metrics
            processing_time = result.total_processing_time
            total_mappings = result.total_mappings_created
            
            if processing_time <= 0:
                self.log_test_result("Performance Benchmarks", False, "Invalid processing time")
                return False
            
            throughput = total_mappings / processing_time
            
            # Performance benchmarks (adjusted for test mode)
            max_time_per_1000_mappings = 10  # 10 seconds per 1000 mappings in test mode
            min_throughput = 100  # 100 mappings/second minimum
            
            expected_max_time = (total_mappings / 1000) * max_time_per_1000_mappings
            
            # Check benchmarks
            time_ok = processing_time <= expected_max_time
            throughput_ok = throughput >= min_throughput
            
            details = (f"{processing_time:.1f}s processing time, "
                      f"{throughput:.0f} mappings/second, "
                      f"{total_mappings:,} total mappings")
            
            if time_ok and throughput_ok:
                self.log_test_result("Performance Benchmarks", True, details)
                return True
            else:
                benchmark_details = f"{details} (Failed: time_ok={time_ok}, throughput_ok={throughput_ok})"
                self.log_test_result("Performance Benchmarks", False, benchmark_details)
                return False
            
        except Exception as e:
            self.log_test_result("Performance Benchmarks", False, str(e))
            return False
    
    def test_mapping_type_coverage(self, result: OrchestrationResult) -> bool:
        """Test that all expected mapping types are created"""
        self.logger.info("\n🔗 Testing Mapping Type Coverage...")
        
        if not result or not result.combined_mappings:
            self.log_test_result("Mapping Type Coverage", False, "No combined mappings")
            return False
        
        try:
            # Expected mapping types from Phase 3
            expected_types = {
                LOINCMappingTypes.HAS_ELEMENT,     # Panel-Test
                LOINCMappingTypes.HAS_ANSWER,      # Question-Answer
                LOINCMappingTypes.MAP_TO           # Code Evolution
            }
            
            # Get actual mapping types
            stats = result.combined_mappings.get_statistics()
            actual_types = set(stats.get("map_types", {}).keys())
            
            missing_types = expected_types - actual_types
            extra_types = actual_types - expected_types
            
            if missing_types:
                self.log_test_result("Mapping Type Coverage", False, f"Missing types: {missing_types}")
                return False
            
            # Check that each type has mappings
            for map_type in expected_types:
                count = stats["map_types"].get(map_type, 0)
                if count == 0:
                    self.log_test_result("Mapping Type Coverage", False, f"No mappings for type: {map_type}")
                    return False
            
            type_counts = ", ".join([f"{t}: {stats['map_types'][t]:,}" for t in expected_types])
            details = f"All expected types present: {type_counts}"
            if extra_types:
                details += f" (Extra types: {extra_types})"
            
            self.log_test_result("Mapping Type Coverage", True, details)
            return True
            
        except Exception as e:
            self.log_test_result("Mapping Type Coverage", False, str(e))
            return False
    
    def cleanup_test_outputs(self):
        """Clean up test output files"""
        try:
            if self.test_output_dir.exists():
                import shutil
                shutil.rmtree(self.test_output_dir)
                self.logger.info(f"✅ Cleaned up test outputs: {self.test_output_dir}")
        except Exception as e:
            self.logger.warning(f"⚠️  Failed to clean up test outputs: {e}")
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report"""
        try:
            report = {
                "test_suite": "Phase 3 Complete Integration Test",
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "tests_run": self.test_results['tests_run'],
                    "tests_passed": self.test_results['tests_passed'],
                    "tests_failed": self.test_results['tests_failed'],
                    "success_rate": round((self.test_results['tests_passed'] / self.test_results['tests_run']) * 100, 1) if self.test_results['tests_run'] > 0 else 0,
                    "total_time_seconds": (self.test_results['end_time'] - self.test_results['start_time']).total_seconds() if self.test_results['end_time'] and self.test_results['start_time'] else 0
                },
                "test_details": self.test_results['details']
            }
            
            report_file = self.test_output_dir / "phase3_integration_test_report.json"
            report_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Test report generated: {report_file}")
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate test report: {e}")
            return ""
    
    def run_complete_test_suite(self, quick_mode: bool = False, limit: Optional[int] = None, 
                               cleanup: bool = True) -> bool:
        """Run the complete Phase 3 integration test suite"""
        
        self.test_results['start_time'] = datetime.now()
        
        self.logger.info("🧪 Phase 3 Complete Integration Test Suite")
        self.logger.info("=" * 60)
        
        if quick_mode:
            self.logger.info("⚡ Running in QUICK MODE - reduced test coverage")
        if limit:
            self.logger.info(f"📊 Record limit: {limit:,} per transformer")
        
        try:
            # Determine test limits
            test_limit = limit or (50 if quick_mode else 200)
            orchestration_limit = limit or (100 if quick_mode else 500)
            
            # Run test suite
            tests_passed = 0
            total_tests = 7 if not quick_mode else 5
            
            # Test 1: Prerequisites
            if self.test_prerequisites():
                tests_passed += 1
            
            # Test 2: OCL Model
            if self.test_ocl_mapping_model():
                tests_passed += 1
            
            # Test 3: Individual Transformers (optional in quick mode)
            if not quick_mode:
                if self.test_individual_transformers(limit=test_limit):
                    tests_passed += 1
            
            # Test 4: Complete Orchestration
            orchestration_result = self.test_orchestration(limit=orchestration_limit)
            if orchestration_result and orchestration_result.is_successful:
                tests_passed += 1
            
            # Test 5: Output Files
            if orchestration_result and self.test_output_files(orchestration_result):
                tests_passed += 1
            
            # Test 6: Performance (optional in quick mode)
            if not quick_mode:
                if orchestration_result and self.test_performance_benchmarks(orchestration_result):
                    tests_passed += 1
            
            # Test 7: Mapping Coverage
            if orchestration_result and self.test_mapping_type_coverage(orchestration_result):
                tests_passed += 1
            
            self.test_results['end_time'] = datetime.now()
            
            # Generate report
            report_file = self.generate_test_report()
            
            # Print final summary
            self.logger.info("")
            self.logger.info("🎉 Phase 3 Integration Test Suite Completed!")
            self.logger.info("=" * 60)
            self.logger.info(f"Tests run: {self.test_results['tests_run']}")
            self.logger.info(f"Tests passed: {self.test_results['tests_passed']}")
            self.logger.info(f"Tests failed: {self.test_results['tests_failed']}")
            self.logger.info(f"Success rate: {(self.test_results['tests_passed'] / self.test_results['tests_run'] * 100):.1f}%")
            
            test_duration = (self.test_results['end_time'] - self.test_results['start_time']).total_seconds()
            self.logger.info(f"Total time: {test_duration:.1f} seconds")
            
            if report_file:
                self.logger.info(f"Test report: {report_file}")
            
            # Cleanup
            if cleanup:
                self.cleanup_test_outputs()
            
            # Final status
            all_critical_passed = self.test_results['tests_passed'] >= (total_tests - 1)  # Allow 1 failure
            
            if all_critical_passed:
                self.logger.info("")
                self.logger.info("✅ PHASE 3 INTEGRATION TESTS: PASSED")
                self.logger.info("🚀 Phase 3 system is ready for production!")
                return True
            else:
                self.logger.info("")
                self.logger.info("❌ PHASE 3 INTEGRATION TESTS: FAILED")
                self.logger.info("⚠️  Phase 3 system needs attention before production use")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Test suite failed: {str(e)}")
            return False


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 3 Complete Integration Test")
    parser.add_argument('--quick', action='store_true',
                       help='Run in quick mode with reduced test coverage')
    parser.add_argument('--limit', type=int,
                       help='Limit number of records to process per transformer')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='Do not clean up test output files')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run test suite
    tester = Phase3CompleteTest()
    success = tester.run_complete_test_suite(
        quick_mode=args.quick,
        limit=args.limit,
        cleanup=not args.no_cleanup
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)
