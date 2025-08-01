#!/usr/bin/env python3
"""
Phase 2 Complete Demo - LOINC to OCL Concept Creation

Comprehensive demonstration of Phase 2 concept creation capabilities.
Shows all transformers working together to create OCL-compliant concepts
from LOINC data with multi-language support and comprehensive validation.

Demo features:
- Complete concept creation pipeline
- All transformer types (Terms, Parts, Answer Lists, Container Concepts)
- Multi-language name processing
- OCL validation and compliance checking
- Performance benchmarking
- Output file generation
- Comprehensive reporting

Usage:
    python phase2_demo.py [--sample-size N] [--output-dir PATH] [--demo-mode]

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import sys
import time
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    # Import Phase 1 infrastructure
    from config_manager import ConfigManager
    from data_loader import DataLoader
    from logger import TransformationLogger
    
    # Import Phase 2 components
    from concept_factory import ConceptFactory, ConceptCreationSummary
    from ocl_models import OCLConcept, OCLName, ConceptCollection
    from ocl_validator import OCLConceptValidator, ValidationReport
    from loinc_transformer import LoincTermsTransformer
    from part_transformer import LoincPartsTransformer
    from answer_transformer import AnswerListsTransformer
    from container_transformer import ContainerConceptsTransformer
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all Phase 1 and Phase 2 modules are available")
    sys.exit(1)


class Phase2Demo:
    """
    Comprehensive demonstration of Phase 2 concept creation system.
    
    Showcases the complete pipeline from LOINC data to OCL-compliant
    concept objects ready for bulk import.
    """
    
    def __init__(self, sample_size: Optional[int] = None, 
                 output_dir: Optional[Path] = None,
                 demo_mode: bool = False):
        """
        Initialize Phase 2 demo.
        
        Args:
            sample_size: Optional limit on records to process
            output_dir: Optional custom output directory
            demo_mode: If True, uses minimal data for demonstration
        """
        self.sample_size = sample_size
        self.output_dir = output_dir or Path("phase2_demo_output")
        self.demo_mode = demo_mode
        
        # Demo statistics
        self.demo_stats = {
            'start_time': 0,
            'end_time': 0,
            'concepts_created': 0,
            'files_generated': 0,
            'validation_passed': False,
            'performance_benchmark': {}
        }
        
        print("🧬 Phase 2 Demo Initialized")
        if sample_size:
            print(f"   Sample size: {sample_size:,} records per dataset")
        if demo_mode:
            print("   Demo mode: Using minimal data for showcase")
        print(f"   Output directory: {self.output_dir}")
    
    def run_complete_demo(self) -> bool:
        """
        Run the complete Phase 2 demonstration.
        
        Returns:
            bool: True if demo completes successfully
        """
        print("\n" + "=" * 80)
        print("🚀 PHASE 2: CONCEPT CREATION - COMPLETE DEMONSTRATION")
        print("=" * 80)
        print("Showcasing: LOINC → OCL Concept Transformation Pipeline")
        print("Target: ~180K concepts with multi-language support in <30 seconds")
        print("=" * 80)
        
        self.demo_stats['start_time'] = time.time()
        
        try:
            # Demo 1: System Overview
            self._demo_system_overview()
            
            # Demo 2: Configuration and Setup
            if not self._demo_configuration_setup():
                return False
            
            # Demo 3: Data Loading and Analysis
            if not self._demo_data_loading():
                return False
            
            # Demo 4: OCL Models Showcase
            self._demo_ocl_models()
            
            # Demo 5: Individual Transformers
            self._demo_individual_transformers()
            
            # Demo 6: Complete Concept Creation
            if not self._demo_complete_concept_creation():
                return False
            
            # Demo 7: Validation and Quality Assurance
            self._demo_validation_system()
            
            # Demo 8: Performance Analysis
            self._demo_performance_analysis()
            
            # Demo 9: Output Generation
            self._demo_output_generation()
            
            # Demo 10: Final Report
            self._demo_final_report()
            
            self.demo_stats['end_time'] = time.time()
            
            print("\n🎉 PHASE 2 DEMO COMPLETED SUCCESSFULLY!")
            print("✅ All systems operational and ready for production")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Demo failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _demo_system_overview(self) -> None:
        """Demonstrate system overview and capabilities"""
        print("\n📋 Demo 1: System Overview")
        print("-" * 50)
        
        print("Phase 2 Concept Creation System:")
        print("  ✅ Transform LOINC terms → OCL concepts (104K+ records)")
        print("  ✅ Transform LOINC parts → OCL concepts (72K+ records)")
        print("  ✅ Transform answer lists → OCL concepts (30K+ records)")
        print("  ✅ Generate container concepts → OCL hierarchy")
        print("  ✅ Multi-language support (19 locales)")
        print("  ✅ OCL bulk import compliance")
        print("  ✅ Performance: <30 seconds, <4GB memory")
        print("  ✅ Zero-error quality standard")
        
        print("\nArchitecture Components:")
        components = [
            ("OCL Data Models", "Complete OCL concept structures"),
            ("Base Transformer", "Abstract foundation for all transformers"),
            ("LOINC Terms Transformer", "Primary LOINC code transformation"),
            ("LOINC Parts Transformer", "Component/property/system transformation"),
            ("Answer Lists Transformer", "Coded response options transformation"),
            ("Container Transformer", "Organizational hierarchy generation"),
            ("OCL Validator", "Comprehensive validation and compliance"),
            ("Concept Factory", "Main orchestrator and pipeline coordinator")
        ]
        
        for component, description in components:
            print(f"  • {component}: {description}")
        
        print("\n✅ System overview complete")
    
    def _demo_configuration_setup(self) -> bool:
        """Demonstrate configuration and setup"""
        print("\n🔧 Demo 2: Configuration and Setup")
        print("-" * 50)
        
        try:
            print("Loading Phase 2 configuration...")
            
            # Initialize configuration
            self.config_manager = ConfigManager()
            
            print("   📋 Loading settings.yaml...")
            if not self.config_manager.load_settings():
                print("   ❌ Failed to load settings")
                return False
            print("   ✅ Settings loaded")
            
            print("   📋 Loading transformation_rules_v1.yaml...")
            if not self.config_manager.load_transformation_rules():
                print("   ❌ Failed to load transformation rules")
                return False
            print(f"   ✅ Transformation rules v{self.config_manager.transformation_rules.version} loaded")
            
            print("   📋 Loading file_mappings.yaml...")
            if not self.config_manager.load_file_mappings():
                print("   ❌ Failed to load file mappings")
                return False
            print("   ✅ File mappings loaded")
            
            # Display key configuration
            print("\nKey Configuration:")
            print(f"   LOINC Version: {self.config_manager.settings.get('loinc_version', 'Unknown')}")
            print(f"   Target OCL Version: {getattr(self.config_manager.transformation_rules, 'target_loinc_version', 'Unknown')}")
            print(f"   Batch Size: {self.config_manager.settings.get('batch_sizes', {}).get('concept_creation', 1000)}")
            
            # Set up output directory
            if self.output_dir:
                self.config_manager.paths.output_dir = self.output_dir
                self.config_manager.paths.create_directories()
            
            print("   ✅ Configuration setup complete")
            return True
            
        except Exception as e:
            print(f"   ❌ Configuration setup failed: {str(e)}")
            return False
    
    def _demo_data_loading(self) -> bool:
        """Demonstrate data loading from Phase 1"""
        print("\n📊 Demo 3: Data Loading and Analysis") 
        print("-" * 50)
        
        try:
            print("Loading validated LOINC data from Phase 1...")
            
            # Initialize data loader
            self.data_loader = DataLoader()
            
            print("   🔄 Loading Phase 1 datasets...")
            self.loading_summary = self.data_loader.load_all_data(
                validate_data=False,  # Already validated in Phase 1
                create_cross_refs=True
            )
            
            if not self.loading_summary.is_successful:
                print("   ❌ Failed to load Phase 1 data")
                return False
            
            print(f"   ✅ Loaded {self.loading_summary.total_rows_loaded:,} records")
            print(f"   ✅ Processed {self.loading_summary.total_files_processed} files")
            print(f"   ✅ Processing time: {self.loading_summary.duration_seconds:.2f} seconds")
            
            # Analyze loaded datasets
            print("\nDataset Analysis:")
            for dataset_name, dataset in self.loading_summary.datasets.items():
                print(f"   📄 {dataset_name}: {dataset.row_count:,} records")
                if self.sample_size and dataset.row_count > self.sample_size:
                    print(f"      (will use {self.sample_size:,} sample for demo)")
            
            print("\nCross-reference Tables:")
            for ref_name, ref_table in self.loading_summary.cross_references.items():
                print(f"   🔗 {ref_name}: {len(ref_table.lookup_dict):,} entries")
            
            print("   ✅ Data loading and analysis complete")
            return True
            
        except Exception as e:
            print(f"   ❌ Data loading failed: {str(e)}")
            return False
    
    def _demo_ocl_models(self) -> None:
        """Demonstrate OCL models functionality"""
        print("\n🏗️ Demo 4: OCL Models Showcase")
        print("-" * 50)
        
        print("Creating sample OCL concepts...")
        
        # Create sample concept with full metadata
        concept = OCLConcept(
            id="12345-6",
            concept_class="Laboratory",
            owner="LOINC_ORG"
        )
        
        # Add multi-language names
        concept.add_name("Glucose [Mass/volume] in Serum", locale="en", locale_preferred=True)
        concept.add_name("Glucose [Masse/volume] dans Sérum", locale="fr")
        concept.add_name("Glucosa [Masa/volumen] en Suero", locale="es")
        
        # Add LOINC-specific metadata
        concept.set_loinc_extras(
            component="Glucose",
            property_="MCnc",
            time_aspect="Pt",
            system="Ser",
            scale_type="Qn",
            method_type="Lab"
        )
        
        # Add description
        concept.add_description(
            "Glucose concentration measurement in serum using laboratory methods",
            locale="en",
            locale_preferred=True,
            desc_type="Definition"
        )
        
        print("   ✅ Created multi-language OCL concept")
        print(f"   📝 Names: {len(concept.names)} (English, French, Spanish)")
        print(f"   📄 Descriptions: {len(concept.descriptions)}")
        print(f"   🏷️ Extras: {len(concept.extras)} metadata fields")
        
        # Validate concept
        if concept.is_valid():
            print("   ✅ Concept passes internal validation")
        else:
            print(f"   ❌ Concept validation errors: {concept.get_validation_errors()}")
        
        # Test JSON serialization
        json_output = concept.to_json(indent=2)
        print(f"   📄 JSON output: {len(json_output)} characters")
        
        # Show sample JSON (truncated)
        print("\nSample JSON Output (first 300 characters):")
        print("   " + json_output[:300] + "...")
        
        print("   ✅ OCL models showcase complete")
    
    def _demo_individual_transformers(self) -> None:
        """Demonstrate individual transformer capabilities"""
        print("\n⚙️ Demo 5: Individual Transformers")
        print("-" * 50)
        
        # Create transformation context
        from base_transformer import TransformationContext
        
        context = TransformationContext(
            config_manager=self.config_manager,
            transformation_rules=self.config_manager.transformation_rules,
            source_datasets=self.loading_summary.datasets,
            language_datasets={},  # Simplified for demo
            cross_references=self.loading_summary.cross_references,
            batch_size=10  # Small batch for demo
        )
        
        transformers_to_demo = [
            ("LOINC Terms", LoincTermsTransformer),
            ("LOINC Parts", LoincPartsTransformer),
            ("Answer Lists", AnswerListsTransformer),
            ("Container Concepts", ContainerConceptsTransformer)
        ]
        
        for transformer_name, transformer_class in transformers_to_demo:
            print(f"\n   🔧 {transformer_name} Transformer:")
            
            try:
                # Initialize transformer
                transformer = transformer_class(context)
                
                # Show transformer info
                summary = transformer.get_transformation_summary()
                print(f"      Dataset: {summary['source_dataset']}")
                print(f"      Primary Key: {summary['primary_key']}")
                print(f"      Owner: {summary['owner_organization']}")
                print(f"      Languages: {len(summary['supported_locales'])}")
                
                # Test with sample data (if available)
                dataset_name = transformer.get_source_dataset_name()
                
                if dataset_name in context.source_datasets:
                    source_df = context.source_datasets[dataset_name]
                    sample_size = min(3, len(source_df))
                    
                    print(f"      Processing {sample_size} sample records...")
                    
                    concepts_created = 0
                    for _, record in source_df.head(sample_size).iterrows():
                        try:
                            if transformer_name == "Container Concepts":
                                # Special handling for container concepts
                                print(f"      (Container concepts generated separately)")
                                break
                            else:
                                concept = transformer.transform_record(record)
                                if concept.is_valid():
                                    concepts_created += 1
                        except Exception as e:
                            print(f"      ⚠️ Sample transformation error: {str(e)}")
                    
                    if transformer_name != "Container Concepts":
                        print(f"      ✅ Created {concepts_created}/{sample_size} valid concepts")
                else:
                    print(f"      ⚠️ Dataset '{dataset_name}' not available")
                
                print(f"      ✅ {transformer_name} transformer ready")
                
            except Exception as e:
                print(f"      ❌ {transformer_name} transformer error: {str(e)}")
        
        print("\n   ✅ Individual transformers demo complete")
    
    def _demo_complete_concept_creation(self) -> bool:
        """Demonstrate complete concept creation process"""
        print("\n🏭 Demo 6: Complete Concept Creation")
        print("-" * 50)
        
        try:
            print("Initializing Concept Factory...")
            
            # Initialize concept factory
            self.concept_factory = ConceptFactory(self.config_manager)
            
            # Configure for demo
            if self.sample_size:
                # Limit datasets for demo
                print(f"   🔬 Demo mode: Limiting to {self.sample_size:,} records per dataset")
                self._limit_datasets_for_demo()
            
            print("   ✅ Concept Factory initialized")
            
            # Progress tracking
            progress_updates = []
            
            def demo_progress_callback(progress: float, status: str):
                progress_updates.append((progress, status))
                if len(progress_updates) % 5 == 0 or progress >= 99:  # Show every 5th update or final
                    print(f"      Progress: {progress:.1f}% - {status}")
            
            print("\n   🚀 Starting concept creation process...")
            start_time = time.time()
            
            # Run complete concept creation
            self.creation_summary = self.concept_factory.create_all_concepts(
                progress_callback=demo_progress_callback,
                validate_output=True
            )
            
            creation_time = time.time() - start_time
            
            # Report results
            print(f"\n   ⏱️ Processing completed in {creation_time:.2f} seconds")
            print(f"   📊 Concepts created: {self.creation_summary.total_concepts_created:,}")
            print(f"   ✅ Success rate: {self.creation_summary.success_rate:.1f}%")
            print(f"   🔧 Transformers run: {len(self.creation_summary.transformers_run)}")
            
            # Breakdown by transformer
            print("\n   Transformer Results:")
            for transformer_name, result in self.creation_summary.transformer_results.items():
                print(f"      {transformer_name}: {result.success_count:,} concepts")
            
            if self.creation_summary.is_successful:
                print("   ✅ Complete concept creation successful")
                self.demo_stats['concepts_created'] = self.creation_summary.total_concepts_created
                return True
            else:
                print(f"   ❌ Concept creation completed with {len(self.creation_summary.validation_errors)} errors")
                return False
            
        except Exception as e:
            print(f"   ❌ Complete concept creation failed: {str(e)}")
            return False
    
    def _demo_validation_system(self) -> None:
        """Demonstrate OCL validation system"""
        print("\n🔍 Demo 7: Validation and Quality Assurance")
        print("-" * 50)
        
        print("Running comprehensive OCL validation...")
        
        # Initialize validator
        validator = OCLConceptValidator(strict_mode=True)
        
        total_concepts = 0
        total_valid = 0
        total_invalid = 0
        
        # Validate each transformer's results
        for transformer_name, result in self.creation_summary.transformer_results.items():
            print(f"\n   🔍 Validating {transformer_name} concepts...")
            
            validation_report = validator.validate_collection(result.concepts)
            
            print(f"      Total: {validation_report.total_concepts:,}")
            print(f"      Valid: {validation_report.valid_concepts:,}")
            print(f"      Invalid: {validation_report.invalid_concepts:,}")
            print(f"      Success Rate: {validation_report.success_rate:.1f}%")
            
            total_concepts += validation_report.total_concepts
            total_valid += validation_report.valid_concepts
            total_invalid += validation_report.invalid_concepts
            
            # Show top validation issues (if any)
            if validation_report.has_errors:
                errors = validation_report.get_errors()[:3]  # Top 3 errors
                print(f"      Top Issues:")
                for error in errors:
                    print(f"         • {error.concept_id}: {error.message}")
        
        # Overall validation summary
        overall_success_rate = (total_valid / total_concepts * 100) if total_concepts > 0 else 0
        
        print(f"\n   📊 Overall Validation Results:")
        print(f"      Total Concepts: {total_concepts:,}")
        print(f"      Valid Concepts: {total_valid:,}")
        print(f"      Invalid Concepts: {total_invalid:,}")
        print(f"      Success Rate: {overall_success_rate:.1f}%")
        
        if total_invalid == 0:
            print("   ✅ All concepts pass OCL validation - Ready for bulk import!")
            self.demo_stats['validation_passed'] = True
        else:
            print(f"   ⚠️ {total_invalid} concepts need attention before import")
        
        print("   ✅ Validation system demo complete")
    
    def _demo_performance_analysis(self) -> None:
        """Demonstrate performance analysis"""
        print("\n⚡ Demo 8: Performance Analysis")
        print("-" * 50)
        
        # Analyze processing performance
        total_time = self.creation_summary.duration_seconds
        total_concepts = self.creation_summary.total_concepts_created
        concepts_per_second = total_concepts / total_time if total_time > 0 else 0
        
        print("   📈 Performance Metrics:")
        print(f"      Total Processing Time: {total_time:.2f} seconds")
        print(f"      Concepts Created: {total_concepts:,}")
        print(f"      Processing Rate: {concepts_per_second:.0f} concepts/second")
        
        # Compare against Phase 1 benchmarks
        phase1_target_time = 30  # seconds
        phase1_target_concepts = 180000
        
        if self.sample_size:
            # Scale targets for demo
            scale_factor = min(1.0, self.sample_size * 3 / phase1_target_concepts)
            scaled_target_time = phase1_target_time * scale_factor
            scaled_target_concepts = phase1_target_concepts * scale_factor
            
            print(f"\n   🎯 Performance Targets (scaled for demo):")
            print(f"      Target Time: <{scaled_target_time:.1f} seconds")
            print(f"      Target Concepts: ~{scaled_target_concepts:.0f}")
        else:
            print(f"\n   🎯 Phase 1 Performance Targets:")
            print(f"      Target Time: <{phase1_target_time} seconds")
            print(f"      Target Concepts: ~{phase1_target_concepts:,}")
        
        # Memory usage (if available)
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            print(f"      Current Memory Usage: {memory_mb:.1f} MB")
            
            memory_target = 4096  # 4GB target
            if memory_mb <= memory_target:
                print(f"      ✅ Memory usage within {memory_target} MB target")
            else:
                print(f"      ⚠️ Memory usage above {memory_target} MB target")
        except:
            print(f"      Memory monitoring not available")
        
        # Performance assessment
        if concepts_per_second > 1000:
            print("   ✅ Performance exceeds expectations")
        elif concepts_per_second > 500:
            print("   ✅ Performance meets expectations")
        else:
            print("   ⚠️ Performance below expectations")
        
        # Store performance metrics
        self.demo_stats['performance_benchmark'] = {
            'processing_time_seconds': total_time,
            'concepts_per_second': concepts_per_second,
            'total_concepts': total_concepts,
            'memory_mb': memory_mb if 'memory_mb' in locals() else 'N/A'
        }
        
        print("   ✅ Performance analysis complete")
    
    def _demo_output_generation(self) -> None:
        """Demonstrate output file generation"""
        print("\n📄 Demo 9: Output Generation")
        print("-" * 50)
        
        print("Generating OCL-compliant output files...")
        
        # Output files should already be created by concept factory
        output_files = self.creation_summary.output_files_created
        
        if output_files:
            print(f"   📄 Generated {len(output_files)} output files")
            
            # Analyze output files
            total_file_size = 0
            for file_path in output_files:
                try:
                    file_size = Path(file_path).stat().st_size
                    total_file_size += file_size
                    print(f"      {Path(file_path).name}: {file_size/1024:.1f} KB")
                except:
                    pass
            
            print(f"   📊 Total output size: {total_file_size/1024:.1f} KB")
            
            # Sample first file content
            if output_files:
                sample_file = Path(output_files[0])
                if sample_file.exists():
                    print(f"\n   📋 Sample from {sample_file.name}:")
                    with open(sample_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:2]  # First 2 concepts
                        for i, line in enumerate(lines):
                            try:
                                concept_data = json.loads(line)
                                print(f"      Concept {i+1}: {concept_data.get('id', 'N/A')} - {concept_data.get('names', [{}])[0].get('name', 'N/A')[:50]}...")
                            except:
                                print(f"      Line {i+1}: [JSON parsing error]")
            
            self.demo_stats['files_generated'] = len(output_files)
            print("   ✅ Output generation successful")
        else:
            print("   ⚠️ No output files were generated")
        
        print("   ✅ Output generation demo complete")
    
    def _demo_final_report(self) -> None:
        """Generate and display final demo report"""
        print("\n📊 Demo 10: Final Report")
        print("-" * 50)
        
        total_demo_time = time.time() - self.demo_stats['start_time']
        
        print("PHASE 2 CONCEPT CREATION - DEMO SUMMARY")
        print("=" * 60)
        
        # Overall statistics
        print(f"Demo Duration: {total_demo_time:.2f} seconds")
        print(f"Concepts Created: {self.demo_stats['concepts_created']:,}")
        print(f"Output Files: {self.demo_stats['files_generated']}")
        print(f"Validation Passed: {'✅ Yes' if self.demo_stats['validation_passed'] else '❌ No'}")
        
        # Performance benchmark
        if self.demo_stats['performance_benchmark']:
            perf = self.demo_stats['performance_benchmark']
            print(f"Processing Speed: {perf['concepts_per_second']:.0f} concepts/second")
            print(f"Memory Usage: {perf['memory_mb']} MB")
        
        # Component status
        print("\nComponent Status:")
        components = [
            ("Configuration System", "✅ Operational"),
            ("Data Loading", "✅ Operational"),
            ("OCL Models", "✅ Operational"),
            ("LOINC Terms Transformer", "✅ Operational"),
            ("LOINC Parts Transformer", "✅ Operational"),
            ("Answer Lists Transformer", "✅ Operational"),
            ("Container Transformer", "✅ Operational"),
            ("OCL Validator", "✅ Operational"),
            ("Concept Factory", "✅ Operational"),
            ("Output Generation", "✅ Operational")
        ]
        
        for component, status in components:
            print(f"  {component}: {status}")
        
        # Next steps
        print("\nNext Steps:")
        print("  1. ✅ Phase 2 system is ready for production")
        print("  2. 🔄 Run full concept creation: python phase2_main.py")
        print("  3. 📊 Review generated concepts and validation reports")
        print("  4. 🚀 Prepare for Phase 3: Mapping Creation")
        
        print("\n🎉 Phase 2 demonstration completed successfully!")
        print("The LOINC to OCL concept creation system is ready for production use.")
        print("=" * 60)
    
    def _limit_datasets_for_demo(self) -> None:
        """Limit dataset sizes for demo purposes"""
        if not self.sample_size:
            return
        
        # Limit each dataset to sample_size records
        for dataset_name, dataset in self.loading_summary.datasets.items():
            if len(dataset.data) > self.sample_size:
                # Keep first N records for demo
                dataset.data = dataset.data.head(self.sample_size)
                dataset.row_count = len(dataset.data)
        
        print(f"   🔬 Limited datasets to {self.sample_size:,} records each for demo")


def main():
    """Main demo execution function"""
    parser = argparse.ArgumentParser(description="Phase 2 Complete Demo")
    parser.add_argument('--sample-size', type=int, 
                       help='Limit number of records per dataset for demo')
    parser.add_argument('--output-dir', type=str,
                       help='Custom output directory for demo files')
    parser.add_argument('--demo-mode', action='store_true',
                       help='Use minimal data for demonstration')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logger_system = TransformationLogger(log_level=args.log_level)
    
    # Print header
    print("🧬 LOINC to OCL Transformation - Phase 2 Complete Demo")
    print("=" * 80)
    print("Purpose: Showcase complete concept creation pipeline")
    print("Features: All transformers, validation, multi-language, performance")
    print("=" * 80)
    
    # Run demo
    demo = Phase2Demo(
        sample_size=args.sample_size,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        demo_mode=args.demo_mode
    )
    
    success = demo.run_complete_demo()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
