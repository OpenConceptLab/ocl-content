#!/usr/bin/env python3
"""
Phase 3 Main Entry Point - LOINC to OCL Mapping Creation

Main execution script for Phase 3 of the LOINC to OCL transformation project.
Provides a simple, unified interface for running the complete mapping creation process.

Target Output:
- ~125,000+ OCL Mapping objects (3 relationship types)
- Panel-to-test mappings: ~91,993 ("has element")
- Question-answer mappings: ~29,018 ("has answer")  
- Code evolution mappings: ~4,643 ("Map To")
- JSON-lines format ready for OCL bulk import
- Processing time: <60 seconds target

Usage:
    python phase3_main.py [options]

Options:
    --test              Run in test mode with limited data
    --quick             Quick validation test only
    --limit N           Limit records per transformer (for testing)
    --output-dir PATH   Custom output directory
    --validate-only     Validate prerequisites without processing
    --individual TYPE   Run specific transformer only (panel|qa|evolution)

Examples:
    python phase3_main.py                    # Complete production run
    python phase3_main.py --test             # Test run with limited data
    python phase3_main.py --validate-only    # Check prerequisites only
    python phase3_main.py --individual panel # Panel mappings only

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import sys
import argparse
import logging
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from phase3_mapping_creation.phase3_mapping_orchestrator import MappingOrchestrator
from phase3_complete_test import Phase3CompleteTest


def setup_logging(log_level: str = "INFO", log_file: bool = True) -> None:
    """Setup logging configuration"""
    handlers = [logging.StreamHandler()]
    
    if log_file:
        log_dir = Path("logs/phase3")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / f"phase3_main_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        handlers.append(logging.FileHandler(log_file_path, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def validate_prerequisites() -> bool:
    """Validate Phase 3 prerequisites"""
    print("🔍 Validating Phase 3 Prerequisites...")
    
    try:
        # Quick validation using the test framework
        tester = Phase3CompleteTest()
        
        # Just run prerequisite test
        result = tester.test_prerequisites()
        
        if result:
            print("✅ All prerequisites validated successfully")
            return True
        else:
            print("❌ Prerequisites validation failed")
            print("   Make sure Phase 1 and Phase 2 are completed")
            return False
            
    except Exception as e:
        print(f"❌ Prerequisites validation error: {e}")
        return False


def run_individual_transformer(transformer_type: str, limit: int = None, output_dir: str = None) -> bool:
    """Run a specific individual transformer"""
    print(f"🔧 Running {transformer_type.title()} Transformer...")
    
    try:
        # Import and create the specific transformer
        if transformer_type == "panel":
            from phase3_mapping_creation.phase3_panel_transformer import PanelTestMappingTransformer
            transformer = PanelTestMappingTransformer()
        elif transformer_type == "qa":
            from phase3_mapping_creation.phase3_question_answer_transformer import QuestionAnswerMappingTransformer
            transformer = QuestionAnswerMappingTransformer()
        elif transformer_type == "evolution":
            from phase3_mapping_creation.phase3_code_evolution_transformer import CodeEvolutionMappingTransformer
            transformer = CodeEvolutionMappingTransformer()
        else:
            print(f"❌ Unknown transformer type: {transformer_type}")
            return False
        
        # Progress callback
        def progress_callback(progress: float, status: str):
            if progress % 20 == 0 or progress >= 99:
                print(f"   Progress: {progress:.1f}% - {status}")
        
        # Run transformation
        start_time = time.time()
        result = transformer.run_transformation(limit=limit, progress_callback=progress_callback)
        processing_time = time.time() - start_time
        
        if result.success_count > 0:
            # Write output files
            from phase3_mapping_creation.phase3_ocl_models import MappingCollection
            
            collection = MappingCollection()
            result.add_to_collection(collection)
            
            output_path = Path(output_dir) if output_dir else Path("output/phase3_mappings")
            output_files = collection.write_jsonl_files(
                output_path, 
                base_filename=f"{transformer_type}_mappings"
            )
            
            # Print summary
            print(f"\n🎉 {transformer.get_transformer_name()} Completed!")
            print(f"Records processed: {result.source_records_processed:,}")
            print(f"Mappings created: {result.success_count:,}")
            print(f"Processing time: {processing_time:.1f} seconds")
            print(f"Success rate: {result.success_rate:.1f}%")
            
            if result.error_count > 0:
                print(f"Errors: {result.error_count}")
            
            print(f"\nOutput files:")
            for file_path in output_files:
                print(f"  {file_path}")
            
            return True
        else:
            print(f"❌ No mappings were created by {transformer_type} transformer")
            return False
            
    except Exception as e:
        print(f"❌ {transformer_type.title()} transformer failed: {e}")
        return False


def run_quick_test() -> bool:
    """Run quick validation test"""
    print("⚡ Running Quick Validation Test...")
    
    try:
        tester = Phase3CompleteTest()
        
        # Run quick test suite
        success = tester.run_complete_test_suite(
            quick_mode=True,
            limit=50,
            cleanup=True
        )
        
        if success:
            print("\n✅ Quick test completed successfully!")
            print("🚀 Phase 3 system is ready for production use")
        else:
            print("\n❌ Quick test failed")
            print("⚠️  Phase 3 system needs attention")
        
        return success
        
    except Exception as e:
        print(f"❌ Quick test error: {e}")
        return False


def run_complete_mapping_creation(test_mode: bool = False, limit: int = None, output_dir: str = None) -> bool:
    """Run complete mapping creation process"""
    mode_label = "TEST MODE" if test_mode else "PRODUCTION MODE" 
    print(f"🚀 Starting Phase 3 Complete Mapping Creation - {mode_label}")
    
    if limit:
        print(f"📊 Record limit: {limit:,} per transformer")
    
    try:
        # Create orchestrator
        orchestrator = MappingOrchestrator()
        
        if output_dir:
            orchestrator.output_dir = Path(output_dir)
        
        # Progress callback
        last_reported = 0
        def progress_callback(progress: float, status: str):
            nonlocal last_reported
            # Report every 5% or at key milestones
            if progress - last_reported >= 5 or progress >= 99 or progress <= 5:
                print(f"Progress: {progress:.1f}% - {status}")
                last_reported = progress
        
        # Run orchestration
        start_time = time.time()
        result = orchestrator.run_complete_orchestration(
            limit=limit,
            test_mode=test_mode,
            progress_callback=progress_callback
        )
        total_time = time.time() - start_time
        
        # Print results
        print(f"\n🎉 Phase 3 Mapping Creation Completed!")
        print("=" * 60)
        print(f"Total processing time: {total_time:.1f} seconds")
        print(f"Transformers successful: {len(result.transformers_successful)}/{len(result.transformers_run)}")
        print(f"Total mappings created: {result.total_mappings_created:,}")
        
        if result.total_errors > 0:
            print(f"Total errors: {result.total_errors:,}")
        
        print(f"Average throughput: {result.total_mappings_created / total_time:.0f} mappings/second")
        
        print(f"\nMapping Types Created:")
        for transformer_name, transformer_result in result.transformer_results.items():
            transformer = orchestrator.transformers[transformer_name]
            map_type = transformer.get_ocl_map_type()
            count = transformer_result.success_count
            print(f"  {map_type}: {count:,} mappings")
        
        print(f"\nOutput Files ({len(result.output_files)}):")
        for file_path in result.output_files:
            file_name = Path(file_path).name
            print(f"  {file_name}")
        
        if result.is_successful:
            print(f"\n🎯 PHASE 3 STATUS: COMPLETE & SUCCESSFUL!")
            print(f"🚀 Ready for OCL bulk import!")
            
            if not test_mode:
                print(f"\nNext Steps:")
                print(f"  1. Validate output files for OCL import")
                print(f"  2. Import mappings to OCL instance")
                print(f"  3. Begin Phase 4 (Hierarchy Creation)")
            
            return True
        else:
            print(f"\n⚠️  PHASE 3 STATUS: PARTIAL SUCCESS")
            print(f"Some transformers failed - check logs for details")
            return False
            
    except Exception as e:
        print(f"❌ Mapping creation failed: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Phase 3: LOINC to OCL Mapping Creation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python phase3_main.py                     # Complete production run
  python phase3_main.py --test              # Test run with limited data  
  python phase3_main.py --quick             # Quick validation test
  python phase3_main.py --validate-only     # Check prerequisites only
  python phase3_main.py --individual panel  # Panel mappings only
  python phase3_main.py --limit 1000        # Limit to 1000 records per transformer
        """
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--test', action='store_true',
                           help='Run in test mode with limited data')
    mode_group.add_argument('--quick', action='store_true',
                           help='Run quick validation test only')
    mode_group.add_argument('--validate-only', action='store_true',
                           help='Validate prerequisites without processing')
    mode_group.add_argument('--individual', choices=['panel', 'qa', 'evolution'],
                           help='Run specific transformer only')
    
    # Configuration options
    parser.add_argument('--limit', type=int,
                       help='Limit number of records per transformer (for testing)')
    parser.add_argument('--output-dir', type=str,
                       help='Custom output directory (default: output/phase3_mappings)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level (default: INFO)')
    parser.add_argument('--no-log-file', action='store_true',
                       help='Disable log file creation')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, not args.no_log_file)
    
    # Print header
    print("🔗 LOINC to OCL Transformation - Phase 3: Mapping Creation")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Handle different modes
        if args.validate_only:
            success = validate_prerequisites()
            
        elif args.quick:
            success = run_quick_test()
            
        elif args.individual:
            # First validate prerequisites
            if not validate_prerequisites():
                return 1
            success = run_individual_transformer(
                args.individual, 
                limit=args.limit, 
                output_dir=args.output_dir
            )
            
        else:
            # Complete mapping creation (test or production)
            # First validate prerequisites
            if not validate_prerequisites():
                return 1
                
            success = run_complete_mapping_creation(
                test_mode=args.test,
                limit=args.limit,
                output_dir=args.output_dir
            )
        
        # Final status
        print()
        if success:
            print("✅ Phase 3 execution completed successfully!")
        else:
            print("❌ Phase 3 execution failed!")
            print("Check logs for detailed error information")
        
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Execution interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logging.exception("Unexpected error in main execution")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
