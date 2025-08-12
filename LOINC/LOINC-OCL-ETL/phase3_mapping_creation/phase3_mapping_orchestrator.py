"""
Complete Mapping Orchestrator for LOINC to OCL Transformation - Phase 3

Orchestrates the complete Phase 3 mapping creation process by running all three
core transformers in sequence and producing consolidated output.

Transformers Managed:
1. Panel-Test Mapping Transformer (~91,993 "has element" mappings)
2. Question-Answer Mapping Transformer (~29,018 "has answer" mappings)
3. Code Evolution Mapping Transformer (~4,643 "Map To" mappings)

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
from phase3_panel_transformer import PanelTestMappingTransformer
from phase3_question_answer_transformer import QuestionAnswerMappingTransformer
from phase3_code_evolution_transformer import CodeEvolutionMappingTransformer


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
        """Whether the orchestration was successful"""
        return len(self.transformers_successful) >= 3  # All three core transformers


class MappingOrchestrator:
    """
    Orchestrator for the complete Phase 3 mapping creation process.
    
    Manages all mapping transformers and produces consolidated output
    files ready for OCL bulk import.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize mapping orchestrator.
        
        Args:
            config_manager: Optional configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)
        
        # Initialize transformers
        self.transformers = {
            'panel_test': PanelTestMappingTransformer(self.config_manager),
            'question_answer': QuestionAnswerMappingTransformer(self.config_manager),
            'code_evolution': CodeEvolutionMappingTransformer(self.config_manager)
        }
        
        # Output configuration
        self.output_dir = Path("output/phase3_mappings")
        self.logs_dir = Path("logs/phase3")
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Processing settings
        self.chunk_size = 10000  # Mappings per output file
    
    def validate_prerequisites(self) -> bool:
        """Validate all Phase 3 prerequisites"""
        self.logger.info("🔍 Validating Phase 3 prerequisites...")
        
        try:
            # Check Phase 2 concept files
            concept_files = []
            for search_dir in ["output", "output/phase2_concepts"]:
                if Path(search_dir).exists():
                    concept_files.extend(list(Path(search_dir).glob("loinc_concepts_*.jsonl")))
            
            if not concept_files:
                self.logger.error("❌ No Phase 2 concept files found")
                return False
            
            self.logger.info(f"✅ Phase 2 concept files: {len(concept_files)} found")
            
            # Check Phase 1 data availability
            from phase1_2_data_processing.data_loader import DataLoader
            data_loader = DataLoader()
            if not hasattr(data_loader, 'datasets') or not data_loader.datasets:
                self.logger.info("Loading Phase 1 data...")
                data_loader.load_all_data()
            
            required_files = [
                "PanelsAndForms.csv",
                "LoincAnswerListLink.csv", 
                "MapTo.csv"
            ]
            
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
        Run all mapping transformers in sequence.
        
        Args:
            limit: Optional limit on records to process (for testing)
            progress_callback: Optional progress reporting function
            
        Returns:
            Dictionary of transformer results by transformer name
        """
        results = {}
        transformer_names = list(self.transformers.keys())
        
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
                else:
                    self.logger.error(f"❌ Failed to run {transformer_name}")
                    
            except Exception as e:
                self.logger.error(f"❌ Failed to run {transformer_name}: {str(e)}")
                continue
        
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
        
        for transformer_name, result in results.items():
            self.logger.info(f"Adding {result.success_count:,} mappings from {transformer_name}")
            result.add_to_collection(combined_collection)
        
        # Add metadata to collection
        combined_collection.metadata = {
            'created_at': datetime.now().isoformat(),
            'transformers_used': list(results.keys()),
            'total_mappings': len(combined_collection.mappings),
            'phase': 'Phase 3: Mapping Creation'
        }
        
        return combined_collection
    
    def write_mapping_files(self, mapping_collection: MappingCollection) -> List[str]:
        """
        Write mapping collection to JSON Lines files.
        
        Args:
            mapping_collection: Collection of mappings to write
            
        Returns:
            List of output file paths
        """
        self.logger.info(f"Writing {len(mapping_collection.mappings):,} mappings to output files...")
        
        output_files = mapping_collection.write_jsonl_files(
            self.output_dir,
            chunk_size=self.chunk_size,
            base_filename="loinc_mappings"
        )
        
        for file_path in output_files:
            self.logger.info(f"  ✅ {file_path.name}")
        
        return [str(f) for f in output_files]
    
    def generate_orchestration_report(self, result: OrchestrationResult) -> str:
        """
        Generate comprehensive orchestration report.
        
        Args:
            result: Orchestration result
            
        Returns:
            Path to generated report file
        """
        try:
            report_data = {
                "phase": "Phase 3: Complete Mapping Creation Orchestration",
                "timestamp": datetime.now().isoformat(),
                "orchestration_summary": {
                    "transformers_run": len(result.transformers_run),
                    "transformers_successful": len(result.transformers_successful),
                    "success_rate": result.success_rate,
                    "total_processing_time_seconds": round(result.total_processing_time, 2),
                    "total_mappings_created": result.total_mappings_created,
                    "total_errors": result.total_errors,
                    "average_mappings_per_second": round(result.total_mappings_created / result.total_processing_time, 1) if result.total_processing_time > 0 else 0
                },
                "transformer_results": {},
                "mapping_type_breakdown": {},
                "output_files": result.output_files,
                "phase3_status": "COMPLETE" if result.is_successful else "PARTIAL"
            }
            
            # Add detailed transformer results
            for transformer_name, transformer_result in result.transformer_results.items():
                transformer = self.transformers[transformer_name]
                report_data["transformer_results"][transformer_name] = {
                    "transformer_class": transformer.__class__.__name__,
                    "mapping_type": transformer.get_mapping_type(),
                    "ocl_map_type": transformer.get_ocl_map_type(),
                    "source_file": transformer.get_source_file(),
                    "records_processed": transformer_result.source_records_processed,
                    "mappings_created": transformer_result.success_count,
                    "errors": transformer_result.error_count,
                    "success_rate": transformer_result.success_rate,
                    "processing_time_seconds": round(transformer_result.processing_time, 2),
                    "statistics": transformer_result.statistics
                }
                
                # Add to mapping type breakdown
                ocl_map_type = transformer.get_ocl_map_type()
                report_data["mapping_type_breakdown"][ocl_map_type] = transformer_result.success_count
            
            # Add collection statistics if available
            if result.combined_mappings:
                collection_stats = result.combined_mappings.get_statistics()
                report_data["collection_statistics"] = collection_stats
            
            # Write report
            report_file = self.output_dir / "phase3_orchestration_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Orchestration report: {report_file}")
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate orchestration report: {str(e)}")
            return ""
    
    def run_complete_orchestration(self, limit: Optional[int] = None, test_mode: bool = False,
                                 progress_callback: Optional[Callable[[float, str], None]] = None) -> OrchestrationResult:
        """
        Execute complete Phase 3 mapping orchestration.
        
        Args:
            limit: Optional limit on records to process (for testing)
            test_mode: Whether running in test mode
            progress_callback: Optional progress reporting function
            
        Returns:
            OrchestrationResult with complete results and metadata
        """
        start_time = time.time()
        
        self.logger.info("🚀 Phase 3: Complete LOINC to OCL Mapping Creation")
        self.logger.info("=" * 70)
        self.logger.info("Orchestrating All Three Core Transformers:")
        self.logger.info("  • Panel-Test Mapping Transformer")
        self.logger.info("  • Question-Answer Mapping Transformer")
        self.logger.info("  • Code Evolution Mapping Transformer")
        self.logger.info("")
        
        if test_mode:
            self.logger.info("🧪 Running in TEST MODE with limited data")
        if limit:
            self.logger.info(f"📊 Processing limited to {limit:,} records per transformer")
        self.logger.info("")
        
        try:
            # Validate prerequisites
            if progress_callback:
                progress_callback(5, "Validating prerequisites...")
            
            if not self.validate_prerequisites():
                raise RuntimeError("Prerequisites validation failed")
            
            # Run all transformers
            if progress_callback:
                progress_callback(10, "Starting transformer orchestration...")
            
            transformer_results = self.run_all_transformers(
                limit=limit,
                progress_callback=lambda p, s: progress_callback(10 + (p * 0.7), s) if progress_callback else None
            )
            
            if not transformer_results:
                raise RuntimeError("No transformers completed successfully")
            
            # Combine all mappings
            if progress_callback:
                progress_callback(85, "Combining mappings from all transformers...")
            
            combined_mappings = self.combine_all_mappings(transformer_results)
            
            # Write output files
            if progress_callback:
                progress_callback(90, "Writing output files...")
            
            output_files = self.write_mapping_files(combined_mappings)
            
            # Calculate final statistics
            total_mappings = len(combined_mappings.mappings)
            total_errors = sum(len(result.errors) for result in transformer_results.values())
            processing_time = time.time() - start_time
            
            # Create orchestration result
            result = OrchestrationResult(
                transformers_run=list(transformer_results.keys()),
                transformers_successful=[name for name, result in transformer_results.items() if result.success_count > 0],
                transformer_results=transformer_results,
                combined_mappings=combined_mappings,
                total_mappings_created=total_mappings,
                total_errors=total_errors,
                total_processing_time=processing_time,
                output_files=output_files
            )
            
            # Generate comprehensive report
            if progress_callback:
                progress_callback(95, "Generating orchestration report...")
            
            report_file = self.generate_orchestration_report(result)
            if report_file:
                result.output_files.append(report_file)
            
            if progress_callback:
                progress_callback(100, "Phase 3 orchestration complete!")
            
            # Print comprehensive summary
            self.logger.info("")
            self.logger.info("🎉 Phase 3 Orchestration Completed!")
            self.logger.info("=" * 70)
            self.logger.info(f"Processing time: {processing_time:.1f} seconds")
            self.logger.info(f"Transformers successful: {len(result.transformers_successful)}/{len(result.transformers_run)}")
            self.logger.info(f"Total mappings created: {result.total_mappings_created:,}")
            self.logger.info(f"Total errors: {result.total_errors:,}")
            self.logger.info(f"Average throughput: {result.total_mappings_created / processing_time:.0f} mappings/second")
            self.logger.info("")
            
            # Individual transformer results
            for transformer_name, transformer_result in result.transformer_results.items():
                transformer = self.transformers[transformer_name]
                status_emoji = "✅" if transformer_result.success_count > 0 else "❌"
                self.logger.info(f"{status_emoji} {transformer.get_mapping_type()}: {transformer_result.success_count:,} mappings")
            
            self.logger.info("")
            self.logger.info("📄 Output Files:")
            for file_path in result.output_files:
                self.logger.info(f"  {Path(file_path).name}")
            
            if result.is_successful:
                self.logger.info("")
                self.logger.info("🎯 PHASE 3 STATUS: COMPLETE & SUCCESSFUL!")
                self.logger.info("🚀 Ready for OCL bulk import!")
            else:
                self.logger.info("")
                self.logger.info("⚠️  PHASE 3 STATUS: PARTIAL SUCCESS")
                self.logger.info(f"   {len(result.transformers_successful)}/{len(result.transformers_run)} transformers completed successfully")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ Orchestration failed: {str(e)}")
            
            # Return partial result even on failure
            return OrchestrationResult(
                total_processing_time=processing_time
            )


def main():
    """Main orchestration function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Phase 3 Complete Mapping Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python phase3_mapping_orchestrator.py                    # Run complete production orchestration
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
    
    try:
        # Create orchestrator
        orchestrator = MappingOrchestrator()
        
        if args.output_dir:
            orchestrator.output_dir = Path(args.output_dir)
        
        # Determine processing limit
        limit = args.limit
        if args.test_mode and not limit:
            limit = 1000
        
        # Progress callback for user feedback
        def progress_callback(progress: float, status: str):
            if progress % 10 == 0 or progress >= 99:  # Show every 10% or at completion
                print(f"Progress: {progress:.1f}% - {status}")
        
        # Run orchestration
        result = orchestrator.run_complete_orchestration(
            limit=limit,
            test_mode=args.test_mode,
            progress_callback=progress_callback
        )
        
        return 0 if result.is_successful else 1
        
    except Exception as e:
        logging.error(f"Orchestration failed: {str(e)}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)
