"""
Complete Mapping Orchestrator for LOINC to OCL Transformation - Phase 3

Orchestrates the complete Phase 3 mapping creation process by running all FIVE
Round 1 transformers in sequence and producing consolidated output.

Transformers Managed:
1. Panel-Test Mapping Transformer (~91,993 "has element" mappings)
2. Question-Answer Mapping Transformer (~29,018 "has answer" mappings)
3. Code Evolution Mapping Transformer (~4,643 "Map To" mappings)
4. Ask at Order Entry Mapping Transformer (TBD "Ask At Order Entry" mappings)
5. Associated Observations Mapping Transformer (TBD "Associated Observation" mappings)

Target Output: ~125,000+ OCL mapping objects ready for bulk import

Features:
- Sequential transformer execution with error recovery
- Combined output file generation
- Comprehensive transformation reporting
- Performance monitoring and statistics
- Quality validation and compliance checking

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from phase1_2_data_processing.config_manager import ConfigManager
from phase3_mapping_creation.phase3_ocl_models import MappingCollection, TransformationResult, MappingTransformationMetadata
from phase3_mapping_creation.phase3_panel_transformer import PanelTestMappingTransformer
from phase3_mapping_creation.phase3_question_answer_transformer import QuestionAnswerMappingTransformer
from phase3_mapping_creation.phase3_code_evolution_transformer import CodeEvolutionMappingTransformer
from phase3_mapping_creation.phase3_ask_order_entry_transformer import AskAtOrderEntryMappingTransformer
from phase3_mapping_creation.phase3_associated_observations_transformer import AssociatedObservationsMappingTransformer


@dataclass
class OrchestrationResult:
    """Result of the complete mapping orchestration"""
    transformers_run: List[str] = field(default_factory=list)
    transformers_successful: List[str] = field(default_factory=list)
    transformer_results: Dict[str, TransformationResult] = field(default_factory=dict)
    combined_mappings: Optional[MappingCollection] = None
    total_mappings_created: int = 0
    total_errors: int = 0
    total_processing_time: float = 0.0
    output_files: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Overall success rate as percentage"""
        if not self.transformers_run:
            return 0.0
        return (len(self.transformers_successful) / len(self.transformers_run)) * 100
    
    @property
    def is_successful(self) -> bool:
        """Whether the orchestration was successful (all 5 transformers completed)"""
        return len(self.transformers_successful) >= 5  # All five Round 1 transformers


class MappingOrchestrator:
    """
    Orchestrator for the complete Phase 3 mapping creation process.
    
    Manages all five Round 1 mapping transformers and produces consolidated 
    output files ready for OCL bulk import.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize mapping orchestrator.
        
        Args:
            config_manager: Optional configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Output configuration
        self.output_dir = Path("output/phase3_mappings")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create all five Round 1 transformers
        self.transformers = {
            "panel_test": PanelTestMappingTransformer(config_manager),
            "question_answer": QuestionAnswerMappingTransformer(config_manager),
            "code_evolution": CodeEvolutionMappingTransformer(config_manager),
            "ask_order_entry": AskAtOrderEntryMappingTransformer(config_manager),
            "associated_observations": AssociatedObservationsMappingTransformer(config_manager)
        }
        
        self.logger.info(f"🎼 Orchestrator initialized with {len(self.transformers)} transformers")
        
        # Processing statistics
        self.stats = {
            'orchestration_started': None,
            'orchestration_completed': None,
            'transformers_attempted': 0,
            'transformers_successful': 0,
            'total_processing_time': 0.0
        }
    
    def validate_prerequisites(self) -> bool:
        """
        Validate that all prerequisites for Phase 3 are available.
        
        Returns:
            bool: True if all prerequisites are met
        """
        self.logger.info("🔍 Validating Phase 3 prerequisites...")
        
        try:
            # Import DataLoader for validation
            from phase1_2_data_processing.data_loader import DataLoader
            
            # Validate Phase 1 data files
            data_loader = DataLoader()
            data_loader.load_all_data()
            
            # Check for required Phase 1 files
            required_files = ["Loinc.csv", "PanelsAndForms.csv", "LoincAnswerListLink.csv", "MapTo.csv"]
            missing_files = []
            file_stats = {}
            
            for file_name in required_files:
                if file_name not in data_loader.datasets:
                    missing_files.append(file_name)
                else:
                    dataset = data_loader.datasets[file_name]
                    file_stats[file_name] = len(dataset.data)
            
            if missing_files:
                self.logger.error(f"❌ Missing Phase 1 files: {missing_files}")
                return False
            
            self.logger.info("✅ Phase 1 data files available:")
            for file_name, record_count in file_stats.items():
                self.logger.info(f"   {file_name}: {record_count:,} records")
            
            # Validate Phase 2 concept files (if required)
            concept_files_found = 0
            for search_dir in ["output", "output/phase2_concepts"]:
                search_path = Path(search_dir)
                if search_path.exists():
                    concept_files = list(search_path.glob("*concept*.jsonl"))
                    concept_files_found += len(concept_files)
            
            if concept_files_found > 0:
                self.logger.info(f"✅ Found {concept_files_found} Phase 2 concept files")
            else:
                self.logger.warning("⚠️  No Phase 2 concept files found - URL resolution may fail")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Prerequisites validation failed: {str(e)}")
            return False
    
    def run_transformer(self, transformer_name: str, limit: Optional[int] = None,
                       progress_callback: Optional[Callable[[float, str], None]] = None) -> Optional[TransformationResult]:
        """
        Run a specific mapping transformer.
        
        Args:
            transformer_name: Name of transformer to run
            limit: Optional limit on records to process (for testing)
            progress_callback: Optional progress reporting function
            
        Returns:
            TransformationResult or None if failed
        """
        if transformer_name not in self.transformers:
            self.logger.error(f"❌ Unknown transformer: {transformer_name}")
            return None
        
        transformer = self.transformers[transformer_name]
        self.logger.info(f"🔗 Running {transformer.get_transformer_name()}...")
        
        try:
            # Create progress wrapper if callback provided
            def transformer_progress(progress: float, status: str):
                if progress_callback:
                    transformer_status = f"{transformer_name}: {status}"
                    progress_callback(progress, transformer_status)
            
            result = transformer.run_transformation(
                limit=limit,
                progress_callback=transformer_progress if progress_callback else None
            )
            
            self.logger.info(f"✅ {transformer_name} completed: {result.success_count:,} mappings")
            if result.error_count > 0:
                self.logger.warning(f"⚠️  {transformer_name} had {result.error_count} errors")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error running {transformer_name}: {str(e)}")
            return None
    
    def run_all_transformers(self, limit: Optional[int] = None,
                           progress_callback: Optional[Callable[[float, str], None]] = None) -> Dict[str, TransformationResult]:
        """
        Run all five mapping transformers in sequence.
        
        Args:
            limit: Optional limit on records to process (for testing)
            progress_callback: Optional progress reporting function
            
        Returns:
            Dictionary of transformer results by transformer name
        """
        results = {}
        transformer_names = list(self.transformers.keys())
        
        self.logger.info(f"🚀 Running {len(transformer_names)} transformers in sequence...")
        
        for i, transformer_name in enumerate(transformer_names):
            try:
                # Create progress wrapper for individual transformer
                def individual_progress(progress: float, status: str):
                    if progress_callback:
                        # Calculate overall progress across all transformers
                        transformer_progress = progress / 100.0
                        overall_progress = ((i + transformer_progress) / len(transformer_names)) * 100
                        overall_status = f"Transformer {i+1}/{len(transformer_names)}: {status}"
                        progress_callback(overall_progress, overall_status)
                
                result = self.run_transformer(
                    transformer_name, 
                    limit=limit,
                    progress_callback=individual_progress if progress_callback else None
                )
                
                if result:
                    results[transformer_name] = result
                    self.logger.info(f"✅ {transformer_name}: {result.success_count:,} mappings created")
                else:
                    self.logger.error(f"❌ Failed to run {transformer_name}")
                    
            except Exception as e:
                self.logger.error(f"❌ Failed to run {transformer_name}: {str(e)}")
                continue
        
        self.logger.info(f"🎯 Completed {len(results)}/{len(transformer_names)} transformers successfully")
        return results
    
    def combine_all_mappings(self, results: Dict[str, TransformationResult]) -> MappingCollection:
        """
        Combine mappings from all transformers into a single collection.
        
        Args:
            results: Results from all transformers
            
        Returns:
            Combined mapping collection
        """
        combined_collection = MappingCollection()
        
        self.logger.info("🔗 Combining mappings from all transformers...")
        
        for transformer_name, result in results.items():
            self.logger.info(f"   Adding {result.success_count:,} mappings from {transformer_name}")
            result.add_to_collection(combined_collection)
        
        # Add comprehensive metadata to collection
        combined_collection.metadata = {
            'created_at': datetime.now().isoformat(),
            'phase': 'Phase 3: Mapping Creation - Round 1 Complete',
            'transformers_used': list(results.keys()),
            'total_mappings': len(combined_collection.mappings),
            'mapping_types_created': {
                transformer_name: self.transformers[transformer_name].get_ocl_map_type()
                for transformer_name in results.keys()
            },
            'round_1_completion_status': len(results) >= 5,
            'target_count_achieved': len(combined_collection.mappings) >= 125000
        }
        
        self.logger.info(f"✅ Combined collection: {len(combined_collection.mappings):,} total mappings")
        return combined_collection
    
    def write_mapping_files(self, mapping_collection: MappingCollection) -> List[str]:
        """
        Write mapping collection to JSON Lines files.
        
        Args:
            mapping_collection: Combined collection of all mappings
            
        Returns:
            List of output file paths
        """
        self.logger.info(f"📄 Writing {len(mapping_collection.mappings):,} mappings to files...")
        
        try:
            output_files = mapping_collection.write_jsonl_files(
                output_dir=self.output_dir,
                base_filename="loinc_mappings_round1"
            )
            
            self.logger.info(f"✅ Created {len(output_files)} mapping files:")
            for file_path in output_files:
                file_name = Path(file_path).name
                self.logger.info(f"   📄 {file_name}")
            
            return output_files
            
        except Exception as e:
            self.logger.error(f"❌ Failed to write mapping files: {str(e)}")
            return []
    
    def generate_orchestration_report(self, result: OrchestrationResult) -> str:
        """
        Generate comprehensive orchestration report.
        
        Args:
            result: Orchestration result to report on
            
        Returns:
            Path to generated report file
        """
        try:
            report_data = {
                'orchestration_summary': {
                    'started_at': self.stats['orchestration_started'],
                    'completed_at': self.stats['orchestration_completed'],
                    'total_processing_time': result.total_processing_time,
                    'transformers_run': len(result.transformers_run),
                    'transformers_successful': len(result.transformers_successful),
                    'success_rate': result.success_rate,
                    'round_1_complete': result.is_successful
                },
                'transformer_results': {},
                'mapping_statistics': {
                    'total_mappings_created': result.total_mappings_created,
                    'total_errors': result.total_errors,
                    'average_throughput_per_second': (
                        result.total_mappings_created / result.total_processing_time
                        if result.total_processing_time > 0 else 0
                    )
                },
                'output_files': result.output_files,
                'round_1_mapping_types': {}
            }
            
            # Add detailed transformer results
            for transformer_name, transformer_result in result.transformer_results.items():
                transformer = self.transformers[transformer_name]
                report_data['transformer_results'][transformer_name] = {
                    'transformer_display_name': transformer.get_transformer_name(),
                    'source_file': transformer.get_source_file(),
                    'mapping_type': transformer.get_mapping_type(),
                    'ocl_map_type': transformer.get_ocl_map_type(),
                    'records_processed': transformer_result.source_records_processed,
                    'mappings_created': transformer_result.success_count,
                    'errors': transformer_result.error_count,
                    'success_rate': transformer_result.success_rate,
                    'processing_time': transformer_result.processing_time
                }
                
                # Track Round 1 mapping types
                report_data['round_1_mapping_types'][transformer.get_ocl_map_type()] = transformer_result.success_count
            
            # Write report file
            report_file = self.output_dir / "phase3_round1_orchestration_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📊 Generated orchestration report: {report_file}")
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate report: {str(e)}")
            return ""
    
    def run_complete_orchestration(self, limit: Optional[int] = None, test_mode: bool = False,
                                 progress_callback: Optional[Callable[[float, str], None]] = None) -> OrchestrationResult:
        """
        Run the complete Phase 3 Round 1 mapping orchestration.
        
        Args:
            limit: Optional limit on records to process (for testing)
            test_mode: Whether to run in test mode
            progress_callback: Optional progress reporting function
            
        Returns:
            OrchestrationResult with complete results
        """
        start_time = time.time()
        self.stats['orchestration_started'] = datetime.now().isoformat()
        
        self.logger.info("🚀 Starting Phase 3 Round 1 Complete Orchestration")
        self.logger.info("=" * 70)
        
        if test_mode:
            self.logger.info("🧪 Running in TEST MODE")
        if limit:
            self.logger.info(f"📊 Record limit: {limit:,} per transformer")
        
        result = OrchestrationResult()
        
        try:
            # Validate prerequisites
            if progress_callback:
                progress_callback(5.0, "Validating prerequisites")
            
            if not self.validate_prerequisites():
                raise Exception("Prerequisites validation failed")
            
            # Run all transformers
            if progress_callback:
                progress_callback(10.0, "Starting transformer execution")
            
            transformer_results = self.run_all_transformers(
                limit=limit,
                progress_callback=lambda p, s: progress_callback(10 + (p * 0.7), s) if progress_callback else None
            )
            
            # Update result with transformer information
            result.transformers_run = list(self.transformers.keys())
            result.transformers_successful = list(transformer_results.keys())
            result.transformer_results = transformer_results
            
            # Calculate totals
            result.total_mappings_created = sum(r.success_count for r in transformer_results.values())
            result.total_errors = sum(r.error_count for r in transformer_results.values())
            
            # Combine all mappings
            if progress_callback:
                progress_callback(85.0, "Combining mappings")
            
            if transformer_results:
                result.combined_mappings = self.combine_all_mappings(transformer_results)
                
                # Write output files
                if progress_callback:
                    progress_callback(90.0, "Writing output files")
                
                result.output_files = self.write_mapping_files(result.combined_mappings)
            
            # Generate report
            if progress_callback:
                progress_callback(95.0, "Generating report")
            
            result.total_processing_time = time.time() - start_time
            self.stats['orchestration_completed'] = datetime.now().isoformat()
            
            report_file = self.generate_orchestration_report(result)
            if report_file:
                result.output_files.append(report_file)
            
            # Final status
            if progress_callback:
                progress_callback(100.0, "Orchestration completed")
            
            self.logger.info("")
            self.logger.info("🎉 Phase 3 Round 1 Orchestration COMPLETED!")
            self.logger.info("=" * 70)
            self.logger.info(f"Total processing time: {result.total_processing_time:.1f} seconds")
            self.logger.info(f"Transformers successful: {len(result.transformers_successful)}/{len(result.transformers_run)}")
            self.logger.info(f"Total mappings created: {result.total_mappings_created:,}")
            self.logger.info(f"Output files generated: {len(result.output_files)}")
            
            if result.is_successful:
                self.logger.info("")
                self.logger.info("🎯 ROUND 1 STATUS: COMPLETE & SUCCESSFUL!")
                self.logger.info("🚀 Ready for OCL bulk import!")
            else:
                self.logger.info("")
                self.logger.info("⚠️  ROUND 1 STATUS: PARTIAL SUCCESS")
                self.logger.info(f"   {len(result.transformers_successful)}/{len(result.transformers_run)} transformers completed successfully")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ Orchestration failed: {str(e)}")
            
            # Return partial result even on failure
            result.total_processing_time = processing_time
            return result


# For standalone execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Phase 3 Complete Round 1 Mapping Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python phase3_mapping_orchestrator.py                    # Run complete Round 1 production orchestration
  python phase3_mapping_orchestrator.py --test-mode        # Run with limited test data
  python phase3_mapping_orchestrator.py --limit 1000       # Process max 1000 records per transformer
        """
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run with limited data for testing (1000 records per transformer)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of records to process per transformer (for testing)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Custom output directory (default: output/phase3_mappings)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = getattr(logging, args.log_level)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path("logs/phase3") / "orchestration.log", encoding='utf-8')
        ]
    )
    
    # Create orchestrator
    orchestrator = MappingOrchestrator()
    
    if args.output_dir:
        orchestrator.output_dir = Path(args.output_dir)
    
    # Progress callback
    def progress_callback(progress: float, status: str):
        print(f"Progress: {progress:.1f}% - {status}")
    
    # Run orchestration
    limit = args.limit if args.limit else (1000 if args.test_mode else None)
    
    result = orchestrator.run_complete_orchestration(
        limit=limit,
        test_mode=args.test_mode,
        progress_callback=progress_callback
    )
    
    # Exit with appropriate code
    exit_code = 0 if result.is_successful else 1
    sys.exit(exit_code)