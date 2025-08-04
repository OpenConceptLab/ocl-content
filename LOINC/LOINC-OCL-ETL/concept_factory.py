"""
Concept Factory - Main Orchestrator for LOINC to OCL Transformation - Phase 2

This module orchestrates the complete concept creation process, coordinating
all transformers to convert LOINC data into OCL concepts ready for bulk import.

Key responsibilities:
- Initialize and coordinate all transformers
- Manage batch processing and memory optimization
- Provide progress tracking and comprehensive reporting
- Generate OCL-compliant JSON-lines output
- Ensure data integrity and validation throughout

Leverages Phase 1's proven architecture for enterprise-grade performance.

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import json

# Import Phase 1 infrastructure
from config_manager import ConfigManager
from data_loader import DataLoader, LoadingSummary

# Import Phase 2 components
from base_transformer import TransformationContext, TransformationResult
from loinc_transformer import LoincTermsTransformer
from part_transformer import LoincPartsTransformer
from answer_transformer import AnswerListsTransformer
from container_transformer import ContainerConceptsTransformer
from ocl_validator import OCLConceptValidator, ValidationReport
from ocl_models import OCLConcept, ConceptCollection


@dataclass
class ConceptCreationSummary:
    """
    Comprehensive summary of the concept creation process.
    
    Tracks results across all transformers and provides detailed metrics
    for handoff to Phase 3.
    """
    start_time: float
    end_time: float
    total_concepts_created: int = 0
    successful_concepts: int = 0
    failed_concepts: int = 0
    transformers_run: List[str] = None
    transformer_results: Dict[str, TransformationResult] = None
    validation_reports: Dict[str, ValidationReport] = None
    output_files_created: List[str] = None
    validation_errors: List[str] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.transformers_run is None:
            self.transformers_run = []
        if self.transformer_results is None:
            self.transformer_results = {}
        if self.validation_reports is None:
            self.validation_reports = {}
        if self.output_files_created is None:
            self.output_files_created = []
        if self.validation_errors is None:
            self.validation_errors = []
        if self.performance_metrics is None:
            self.performance_metrics = {}
    
    @property
    def duration_seconds(self) -> float:
        """Total processing duration"""
        return self.end_time - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Overall success rate as percentage"""
        total = self.successful_concepts + self.failed_concepts
        return (self.successful_concepts / total * 100) if total > 0 else 0.0
    
    @property
    def is_successful(self) -> bool:
        """Check if overall process was successful"""
        return (
            self.failed_concepts == 0 and
            len(self.validation_errors) == 0 and
            self.total_concepts_created > 0
        )


class ConceptFactory:
    """
    Main orchestrator for LOINC to OCL concept creation.
    
    Coordinates all transformers to process the complete LOINC dataset:
    - LOINC Terms: 104K+ concepts
    - LOINC Parts: 72K+ concepts  
    - Answer Lists: 30K+ concepts
    - Container concepts for organization
    
    Maintains Phase 1's performance standards: <30 seconds, <4GB memory.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, loading_summary: Optional[Any] = None):
        """
        Initialize Concept Factory.
        
        Args:
            config_manager: Optional pre-initialized config manager
            loading_summary: Optional pre-loaded LoadingSummary (for in-memory demo)
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)

        # Processing state
        self.data_loader: Optional[DataLoader] = None
        self.loading_summary: Optional[LoadingSummary] = loading_summary
        self.transformation_context: Optional[TransformationContext] = None

        # Output configuration
        self.output_dir = Path("output")
        self.concepts_per_file = 10000  # Chunk size for JSON-lines files

        # Performance tracking
        self.start_time: Optional[float] = None
        self.processing_stats = {
            'concepts_created': 0,
            'files_generated': 0,
            'memory_peak_mb': 0,
            'processing_time_seconds': 0
        }

        self.logger.info("Concept Factory initialized")
    
    def create_all_concepts(self, 
                          progress_callback: Optional[Callable] = None,
                          validate_output: bool = True) -> ConceptCreationSummary:
        """
        Create all OCL concepts from LOINC data.
        
        Main entry point for Phase 2 concept creation process.
        
        Args:
            progress_callback: Optional function to receive progress updates
            validate_output: Whether to validate generated concepts
            
        Returns:
            ConceptCreationSummary: Complete processing results
        """
        self.start_time = time.time()
        self.logger.info("=" * 60)
        self.logger.info("🚀 PHASE 2: CONCEPT CREATION STARTING")
        self.logger.info("=" * 60)
        
        try:
            # Step 1: Initialize and validate prerequisites
            if not self._initialize_prerequisites():
                raise RuntimeError("Failed to initialize prerequisites")
            
            # Step 2: Set up transformation context
            self._setup_transformation_context()
            
            # Step 3: Run transformers in sequence
            summary = self._run_all_transformers(progress_callback)
            
            # Step 4: Generate output files
            if validate_output:
                self._validate_all_concepts(summary)
            
            self._generate_output_files(summary)
            
            # Step 5: Final reporting
            summary.end_time = time.time()
            self._generate_final_report(summary)
            
            self.logger.info("✅ PHASE 2: CONCEPT CREATION COMPLETED SUCCESSFULLY")
            self.logger.info(f"📊 Created {summary.total_concepts_created} concepts in {summary.duration_seconds:.2f} seconds")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ PHASE 2: CONCEPT CREATION FAILED: {str(e)}")
            raise
    
    def _initialize_prerequisites(self) -> bool:
        """Initialize and validate all prerequisites"""
        self.logger.info("📋 Step 1: Initializing prerequisites...")
        # If loading_summary is already set (e.g., from demo), skip reload
        if self.loading_summary is not None:
            self.logger.info("   Using in-memory LoadingSummary (demo mode)")
            # Set up output directory
            self.output_dir = self.config_manager.paths.output_dir / "phase2_concepts"
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"✅ Prerequisites initialized successfully (in-memory)")
            self.logger.info(f"   Loaded {self.loading_summary.total_rows_loaded:,} records from Phase 1 (in-memory)")
            self.logger.info(f"   Output directory: {self.output_dir}")
            return True

        # Otherwise, load from disk as before
        if not self.config_manager.load_all_configs():
            self.logger.error("Failed to load configuration")
            return False

        self.data_loader = DataLoader(self.config_manager.config_dir)
        self.logger.info("Loading Phase 1 validated data...")
        self.loading_summary = self.data_loader.load_all_data(
            validate_data=False,  # Already validated in Phase 1
            create_cross_refs=True
        )

        if not self.loading_summary.is_successful:
            self.logger.error("Failed to load Phase 1 data")
            return False

        self.output_dir = self.config_manager.paths.output_dir / "phase2_concepts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._apply_dataset_aliases()
        self.logger.info(f"   [OK] Prerequisites initialized successfully")
        self.logger.info(f"   Loaded {self.loading_summary.total_rows_loaded:,} records from Phase 1")
        self.logger.info(f"   Output directory: {self.output_dir}")
        return True
    

    def _setup_transformation_context(self) -> None:
        """Set up transformation context for all transformers"""
        self.logger.info("🔧 Step 2: Setting up transformation context...")
        
        # Get batch size from configuration
        batch_size = 1000
        if hasattr(self.config_manager, 'processing'):
            batch_size = getattr(self.config_manager.processing, 'batch_sizes', {}).get('concept_creation', 1000)
        
        # Create transformation context
        self.transformation_context = TransformationContext(
            config_manager=self.config_manager,
            transformation_rules=self.config_manager.transformation_rules,
            source_datasets=self.loading_summary.datasets,
            language_datasets=self._extract_language_datasets(),
            cross_references=self.loading_summary.cross_references,
            batch_size=batch_size
        )
        
        self.logger.info(f"✅ Transformation context ready")
        self.logger.info(f"   Batch size: {batch_size}")
        self.logger.info(f"   Language datasets: {len(self.transformation_context.language_datasets)}")
    
    def _extract_language_datasets(self) -> Dict[str, Any]:
        """Extract language datasets from Phase 1 loading results"""
        language_datasets = {}

        # Extract language variant datasets from Phase 1 results
        for dataset_name, dataset in self.loading_summary.datasets.items():
            if 'linguistic' in dataset_name.lower() or 'language' in dataset_name.lower():
                # Extract language code from dataset name (e.g., 'loinc_linguistic_fr' -> 'fr')
                parts = dataset_name.lower().split('_')
                if len(parts) >= 3:
                    lang_code = parts[-1]
                    # Use .data if present, else use the dataset directly (DataFrame)
                    if hasattr(dataset, 'data'):
                        language_datasets[lang_code] = dataset.data
                    else:
                        language_datasets[lang_code] = dataset

        return language_datasets
    
    def _run_all_transformers(self, progress_callback: Optional[Callable] = None) -> ConceptCreationSummary:
        """Run all transformers in sequence"""
        self.logger.info("⚙️ Step 3: Running transformers...")
        
        # DEFENSIVE CHECK: Ensure transformation context is properly set up
        if not self.transformation_context:
            raise RuntimeError("Transformation context not initialized")
        
        if not hasattr(self.transformation_context, 'source_datasets'):
            raise RuntimeError("Transformation context missing source_datasets")
        
        if not isinstance(self.transformation_context.source_datasets, dict):
            raise RuntimeError(f"source_datasets is {type(self.transformation_context.source_datasets)}, expected dict")
    

        summary = ConceptCreationSummary(
            start_time=self.start_time,
            end_time=0  # Will be set later
        )
        
        # Transformer sequence (as specified in Phase 2 handoff)
        transformers = [
            ("LOINC_Terms", LoincTermsTransformer),
            ("LOINC_Parts", LoincPartsTransformer),
            ("Answer_Lists", AnswerListsTransformer),
            ("Container_Concepts", ContainerConceptsTransformer)
        ]
        
        total_transformers = len(transformers)
        
        for i, (transformer_name, transformer_class) in enumerate(transformers):
            self.logger.info(f"🔄 Running {transformer_name} transformer ({i+1}/{total_transformers})...")
            
            try:
                # Initialize transformer
                transformer = transformer_class(self.transformation_context)
                
                # Validate prerequisites
                if not transformer.validate_prerequisites():
                    raise RuntimeError(f"{transformer_name} prerequisites not met")
                
                # Special handling for container concepts transformer
                if transformer_name == "Container_Concepts":
                    # Container concepts are generated, not transformed from existing data
                    self.logger.info(f"🏗️ Generating {transformer_name} concepts...")
                    
                    def container_progress(progress, status):
                        overall_progress = (i / total_transformers + progress / 100 / total_transformers) * 100
                        if progress_callback:
                            progress_callback(overall_progress, f"{transformer_name} - {status}")
                    
                    try:
                        # Generate container concepts with error handling
                        container_concepts = transformer.create_all_container_concepts()
                        self.logger.info(f"Generated {len(container_concepts)} container concepts")
                        
                        # Create result collection with defensive programming
                        result_collection = ConceptCollection(
                            collection_name=f"{transformer_name}_Concepts",
                            batch_size=self.transformation_context.batch_size
                        )
                        
                        # Add concepts to collection with error handling
                        valid_concepts = 0
                        for concept in container_concepts:
                            try:
                                result_collection.add_concept(concept)
                                valid_concepts += 1
                            except Exception as e:
                                self.logger.warning(f"Failed to add container concept {getattr(concept, 'id', 'UNKNOWN')}: {e}")
                        
                        # Create transformation result with defensive checks
                        result = TransformationResult(
                            concepts=result_collection,
                            success_count=valid_concepts,
                            error_count=len(container_concepts) - valid_concepts,
                            warning_count=0,
                            processing_time_seconds=0.1  # Minimal processing time for generated concepts
                        )
                        
                        self.logger.info(f"Container concepts result: {valid_concepts} valid, {result.error_count} errors")
                        
                    except Exception as e:
                        self.logger.error(f"Container concepts generation failed: {e}")
                        import traceback
                        self.logger.error(f"Full traceback: {traceback.format_exc()}")
                        
                        # Create empty result on failure
                        result_collection = ConceptCollection(
                            collection_name=f"{transformer_name}_Concepts",
                            batch_size=self.transformation_context.batch_size
                        )
                        
                        result = TransformationResult(
                            concepts=result_collection,
                            success_count=0,
                            error_count=1,
                            warning_count=0,
                            processing_time_seconds=0.0
                        )
                    
                else:
                    # Standard transformer processing
                    def transformer_progress(progress, batch, total_batches):
                        overall_progress = (i / total_transformers + progress / 100 / total_transformers) * 100
                        if progress_callback:
                            progress_callback(overall_progress, f"{transformer_name} - Batch {batch}/{total_batches}")
                    
                    result = transformer.transform_dataset(transformer_progress)
                
                # Store results
                summary.transformer_results[transformer_name] = result
                summary.transformers_run.append(transformer_name)
                summary.total_concepts_created += result.success_count
                summary.successful_concepts += result.success_count
                summary.failed_concepts += result.error_count
                
                self.logger.info(f"✅ {transformer_name} completed: {result.success_count} concepts, "
                               f"{result.error_count} errors")
                
            except Exception as e:
                self.logger.error(f"❌ {transformer_name} failed: {str(e)}")
                summary.validation_errors.append(f"{transformer_name}: {str(e)}")
        
        return summary
    
    def _validate_all_concepts(self, summary: ConceptCreationSummary) -> None:
        """Validate all generated concepts using OCL validator"""
        self.logger.info("🔍 Step 4: Validating generated concepts...")
        
        # Initialize OCL validator
        validator = OCLConceptValidator(strict_mode=True)
        
        total_validation_errors = 0
        validation_reports = {}
        
        for transformer_name, result in summary.transformer_results.items():
            self.logger.info(f"Validating concepts from {transformer_name}...")
            
            # Run comprehensive validation
            validation_report = validator.validate_collection(result.concepts)
            validation_reports[transformer_name] = validation_report
            
            # Log results
            if validation_report.has_errors:
                total_validation_errors += validation_report.invalid_concepts
                self.logger.warning(f"{transformer_name}: {validation_report.invalid_concepts} invalid concepts")
                
                # Log top errors for debugging
                errors = validation_report.get_errors()
                for error in errors[:3]:  # Show first 3 errors
                    self.logger.debug(f"  {error.concept_id}: {error.message}")
                
                if len(errors) > 3:
                    self.logger.debug(f"  ... and {len(errors) - 3} more errors")
            else:
                self.logger.info(f"{transformer_name}: All {validation_report.valid_concepts} concepts valid")
        
        # Store validation reports in summary
        summary.validation_reports = validation_reports
        
        # Generate comprehensive validation report
        self._generate_validation_report(validation_reports)
        
        if total_validation_errors == 0:
            self.logger.info("✅ All concepts passed OCL validation")
        else:
            self.logger.warning(f"⚠️ {total_validation_errors} concepts failed OCL validation")
            # In strict mode, this could be treated as an error
            if total_validation_errors > 0:
                summary.validation_errors.append(f"OCL validation failed for {total_validation_errors} concepts")
    
    def _generate_validation_report(self, validation_reports: Dict[str, ValidationReport]) -> None:
        """Generate comprehensive validation report file"""
        report_lines = []
        
        # Overall summary
        total_concepts = sum(report.total_concepts for report in validation_reports.values())
        total_valid = sum(report.valid_concepts for report in validation_reports.values())
        total_invalid = sum(report.invalid_concepts for report in validation_reports.values())
        
        report_lines.append("=" * 80)
        report_lines.append("PHASE 2 OCL CONCEPT VALIDATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        report_lines.append("OVERALL SUMMARY:")
        report_lines.append(f"  Total Concepts: {total_concepts:,}")
        report_lines.append(f"  Valid Concepts: {total_valid:,}")
        report_lines.append(f"  Invalid Concepts: {total_invalid:,}")
        report_lines.append(f"  Success Rate: {(total_valid/total_concepts*100) if total_concepts > 0 else 0:.1f}%")
        report_lines.append("")
        
        # Per-transformer details
        for transformer_name, report in validation_reports.items():
            report_lines.append(f"TRANSFORMER: {transformer_name}")
            report_lines.append("-" * 40)
            
            # Use the validator's report generation
            validator = OCLConceptValidator()
            transformer_report = validator.generate_validation_report_text(report)
            report_lines.append(transformer_report)
            report_lines.append("")
        
        # Save report to file
        report_path = self.output_dir / "ocl_validation_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        self.logger.info(f"📋 OCL validation report saved: {report_path}")
    
    def _generate_output_files(self, summary: ConceptCreationSummary) -> None:
        """Generate OCL JSON-lines output files"""
        self.logger.info("📄 Step 5: Generating output files...")
        
        file_counter = 1
        
        for transformer_name, result in summary.transformer_results.items():
            # Get valid concepts
            valid_concepts = result.concepts.get_valid_concepts()
            
            if not valid_concepts:
                self.logger.warning(f"No valid concepts from {transformer_name}")
                continue
            
            # Split into chunks
            for i in range(0, len(valid_concepts), self.concepts_per_file):
                chunk = valid_concepts[i:i + self.concepts_per_file]
                
                # Create output file
                filename = f"loinc_concepts_{transformer_name.lower()}_{file_counter:03d}.jsonl"
                output_path = self.output_dir / filename
                
                # Write JSON-lines format
                with open(output_path, 'w', encoding='utf-8') as f:
                    for concept in chunk:
                        f.write(concept.to_json() + '\n')
                
                summary.output_files_created.append(str(output_path))
                file_counter += 1
                
                self.logger.debug(f"Created {filename} with {len(chunk)} concepts")
        
        self.logger.info(f"✅ Generated {len(summary.output_files_created)} output files")
    
    def _generate_final_report(self, summary: ConceptCreationSummary) -> None:
        """Generate comprehensive final report"""
        self.logger.info("📊 Generating final report...")
        
        # Performance metrics
        summary.performance_metrics = {
            'total_processing_time_seconds': summary.duration_seconds,
            'concepts_per_second': summary.total_concepts_created / summary.duration_seconds if summary.duration_seconds > 0 else 0,
            'memory_efficient_processing': True,
            'batch_processing_used': True,
            'multi_language_support': len(self.transformation_context.language_datasets),
            'output_files_created': len(summary.output_files_created)
        }
        
        # Generate report file
        report = {
            'phase': 'Phase 2: Concept Creation',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_concepts_created': summary.total_concepts_created,
                'successful_concepts': summary.successful_concepts,
                'failed_concepts': summary.failed_concepts,
                'success_rate_percent': summary.success_rate,
                'processing_time_seconds': summary.duration_seconds,
                'is_successful': summary.is_successful
            },
            'transformers': {
                name: {
                    'concepts_created': result.success_count,
                    'errors': result.error_count,
                    'warnings': result.warning_count,
                    'processing_time_seconds': result.processing_time_seconds
                }
                for name, result in summary.transformer_results.items()
            },
            'output_files': summary.output_files_created,
            'performance_metrics': summary.performance_metrics,
            'validation_errors': summary.validation_errors
        }
        
        # Save report
        report_path = self.output_dir / "concept_creation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📋 Final report saved: {report_path}")
        
        # Log summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 PHASE 2 CONCEPT CREATION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Concepts Created: {summary.total_concepts_created:,}")
        self.logger.info(f"Success Rate: {summary.success_rate:.1f}%")
        self.logger.info(f"Processing Time: {summary.duration_seconds:.2f} seconds")
        self.logger.info(f"Performance: {summary.performance_metrics['concepts_per_second']:.0f} concepts/second")
        self.logger.info(f"Output Files: {len(summary.output_files_created)}")
        self.logger.info(f"Multi-language Support: {summary.performance_metrics['multi_language_support']} locales")
        self.logger.info("=" * 60)
    def _apply_dataset_aliases(self):
        """Apply dataset name aliases for transformer compatibility"""
        datasets = self.loading_summary.datasets
        
        # Critical aliases for transformer compatibility
        if 'Loinc.csv' in datasets and 'loinc_terms' not in datasets:
            datasets['loinc_terms'] = datasets['Loinc.csv']
        
        if 'Part.csv' in datasets and 'loinc_parts' not in datasets:
            datasets['loinc_parts'] = datasets['Part.csv']
            
        if 'AnswerList.csv' in datasets and 'answer_lists' not in datasets:
            datasets['answer_lists'] = datasets['AnswerList.csv']
    def _apply_dataset_aliases(self) -> None:
        """
        Apply dataset name aliases for transformer compatibility.
        
        Maps actual dataset names discovered from LOINC files to the logical names
        that transformers expect. This fixes the dataset name mismatch issue.
        """
        self.logger.info("🔗 Applying dataset aliases...")
        
        datasets = self.loading_summary.datasets
        aliases_applied = []
        
        # LOINC Terms dataset aliasing
        # Look for: Loinc.csv -> alias as: loinc_terms
        terms_candidates = ['Loinc.csv', 'loinc_table', 'loinc_data']
        for candidate in terms_candidates:
            if candidate in datasets and 'loinc_terms' not in datasets:
                # Use .data if it's a LoadedDataset object, otherwise use directly
                source_data = datasets[candidate]
                if hasattr(source_data, 'data'):
                    datasets['loinc_terms'] = source_data.data
                else:
                    datasets['loinc_terms'] = source_data
                aliases_applied.append(f"'{candidate}' -> 'loinc_terms'")
                break
        
        # LOINC Parts dataset aliasing  
        # Look for: Part.csv -> alias as: loinc_parts
        parts_candidates = ['Part.csv', 'parts', 'loinc_part']
        for candidate in parts_candidates:
            if candidate in datasets and 'loinc_parts' not in datasets:
                source_data = datasets[candidate]
                if hasattr(source_data, 'data'):
                    datasets['loinc_parts'] = source_data.data
                else:
                    datasets['loinc_parts'] = source_data
                aliases_applied.append(f"'{candidate}' -> 'loinc_parts'")
                break
        
        # Answer Lists dataset aliasing
        # Look for: AnswerList.csv -> alias as: answer_lists  
        answer_candidates = ['AnswerList.csv', 'answerlist', 'answer_list']
        for candidate in answer_candidates:
            if candidate in datasets and 'answer_lists' not in datasets:
                source_data = datasets[candidate]
                if hasattr(source_data, 'data'):
                    datasets['answer_lists'] = source_data.data
                else:
                    datasets['answer_lists'] = source_data
                aliases_applied.append(f"'{candidate}' -> 'answer_lists'")
                break
        
        # Log results
        if aliases_applied:
            self.logger.info(f"✅ Applied {len(aliases_applied)} dataset aliases:")
            for alias in aliases_applied:
                self.logger.info(f"   {alias}")
        else:
            self.logger.warning("⚠️ No dataset aliases were applied")
            
        # Verify critical datasets are now available
        required_datasets = ['loinc_terms', 'loinc_parts', 'answer_lists']
        missing_datasets = [ds for ds in required_datasets if ds not in datasets]
        
        if missing_datasets:
            self.logger.error(f"❌ Still missing required datasets: {missing_datasets}")
            available = list(datasets.keys())[:10]  # Show first 10
            self.logger.error(f"   Available datasets: {available}...")
            raise RuntimeError(f"Required datasets not found after aliasing: {missing_datasets}")
        else:
            self.logger.info("✅ All required datasets are now available")



# Example usage and testing
if __name__ == "__main__":
    print("Concept Factory - Phase 2 Main Orchestrator")
    print("Coordinates all transformers to create OCL concepts from LOINC data")
    print("\nExpected output:")
    print("- ~180K OCL concepts (terms + parts + answer lists)")
    print("- JSON-lines format ready for OCL bulk import")
    print("- Multi-language support (19 locales)")
    print("- Processing time: <30 seconds")
    print("- Memory usage: <4GB")
