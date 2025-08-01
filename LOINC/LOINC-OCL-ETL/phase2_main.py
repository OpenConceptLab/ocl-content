"""
Phase 2 Main Entry Point - LOINC to OCL Concept Creation

Main execution script for Phase 2 of the LOINC to OCL transformation project.
Orchestrates the complete concept creation process, transforming validated
LOINC data from Phase 1 into OCL-compliant concept objects.

Target Output:
- ~180K OCL Concept objects (104K terms + 72K parts + 30K answer lists)
- Multi-language support (19 locales)
- JSON-lines format ready for OCL bulk import
- Processing time: <30 seconds (Phase 1 benchmark)
- Memory usage: <4GB (Phase 1 proven)

Usage:
    python phase2_main.py [options]

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import sys
import argparse
import traceback
import time
from pathlib import Path
from typing import Optional

# Import Phase 1 infrastructure (reused)
from config_manager import ConfigManager
from logger import TransformationLogger

# Import Phase 2 components
from concept_factory import ConceptFactory, ConceptCreationSummary


def setup_command_line_args() -> argparse.ArgumentParser:
    """Set up command line argument parsing"""
    
    parser = argparse.ArgumentParser(
        description="LOINC to OCL Transformation - Phase 2: Concept Creation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python phase2_main.py                       # Run with default settings
    python phase2_main.py --config ./config    # Use specific config directory
    python phase2_main.py --log-level DEBUG    # Enable debug logging
    python phase2_main.py --dry-run             # Validate setup without processing
    python phase2_main.py --output-dir ./out   # Specify output directory
        """
    )
    
    # Configuration options
    parser.add_argument(
        '--config', '--config-dir',
        type=str,
        help='Directory containing configuration files (default: current directory)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for generated concept files'
    )
    
    # Processing options
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate setup and prerequisites without running transformation'
    )
    
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip concept validation (faster processing)'
    )
    
    parser.add_argument(
        '--concepts-per-file',
        type=int,
        default=10000,
        help='Number of concepts per output file (default: 10000)'
    )
    
    # Logging options
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimize console output (errors only)'
    )
    
    # Performance options
    parser.add_argument(
        '--batch-size',
        type=int,
        help='Batch size for processing (default: from config)'
    )
    
    return parser


def validate_environment() -> bool:
    """Validate that the environment is ready for Phase 2"""
    print("🔍 Validating Phase 2 environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check required modules
    try:
        import pandas as pd
        import yaml
        print(f"✅ Required modules available (pandas {pd.__version__})")
    except ImportError as e:
        print(f"❌ Missing required module: {e}")
        return False
    
    # Check that we have Phase 1 infrastructure
    required_phase1_files = [
        'config_manager.py',
        'data_loader.py',
        'validator.py',
        'logger.py'
    ]
    
    missing_files = []
    for filename in required_phase1_files:
        if not Path(filename).exists():
            missing_files.append(filename)
    
    if missing_files:
        print(f"❌ Missing Phase 1 files: {missing_files}")
        print("   Please ensure Phase 1 infrastructure is available")
        return False
    
    print("✅ Environment validation passed")
    return True


def run_phase2_transformation(args) -> bool:
    """
    Run the complete Phase 2 concept creation process.
    
    Args:
        args: Command line arguments
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Initialize logging
    log_level = "ERROR" if args.quiet else args.log_level
    logger_system = TransformationLogger(log_level=log_level)
    logger = logger_system.get_logger("phase2_main")
    
    logger.info("🚀 Starting Phase 2: Concept Creation")
    logger.info("=" * 60)
    
    try:
        # Initialize configuration
        with logger_system.phase_context("Configuration Loading"):
            logger.info("Loading configuration...")
            config_manager = ConfigManager(args.config)
            
            if not config_manager.load_all_configs():
                logger.error("Failed to load configuration files")
                return False
            
            # Override output directory if specified
            if args.output_dir:
                config_manager.paths.output_dir = Path(args.output_dir)
                config_manager.paths.create_directories()
            
            logger.info("✅ Configuration loaded successfully")
            logger_system.log_statistics("Configuration", {
                "LOINC Version": config_manager.settings.get('loinc_version', 'Unknown'),
                "Transformation Rules": config_manager.transformation_rules.version,
                "Output Directory": str(config_manager.paths.output_dir),
                "Batch Size": args.batch_size or "From config"
            })
        
        # Initialize Concept Factory
        with logger_system.phase_context("Concept Factory Initialization"):
            logger.info("Initializing Concept Factory...")
            concept_factory = ConceptFactory(config_manager)
            
            # Override settings from command line
            if args.concepts_per_file:
                concept_factory.concepts_per_file = args.concepts_per_file
            
            logger.info("✅ Concept Factory initialized")
        
        # Dry run mode - validate setup only
        if args.dry_run:
            logger.info("🧪 DRY RUN MODE - Validating setup only")
            
            # Test configuration and data access
            if concept_factory._initialize_prerequisites():
                logger.info("✅ Dry run successful - ready for concept creation")
                return True
            else:
                logger.error("❌ Dry run failed - prerequisites not met")
                return False
        
        # Run the complete concept creation process
        with logger_system.phase_context("Concept Creation"):
            def progress_callback(progress: float, status: str):
                logger.info(f"Progress: {progress:.1f}% - {status}")
            
            logger.info("Starting concept creation process...")
            
            summary = concept_factory.create_all_concepts(
                progress_callback=progress_callback,
                validate_output=not args.skip_validation
            )
            
            # Check results
            if summary.is_successful:
                logger.info("✅ Phase 2 completed successfully!")
                
                # Log final statistics
                logger_system.log_statistics("Phase 2 Results", {
                    "Total Concepts Created": f"{summary.total_concepts_created:,}",
                    "Success Rate": f"{summary.success_rate:.1f}%",
                    "Processing Time": f"{summary.duration_seconds:.2f} seconds",
                    "Output Files": len(summary.output_files_created),
                    "Performance": f"{summary.performance_metrics.get('concepts_per_second', 0):.0f} concepts/sec"
                })
                
                return True
            else:
                logger.error("❌ Phase 2 completed with errors")
                logger.error(f"Failed concepts: {summary.failed_concepts}")
                logger.error(f"Validation errors: {len(summary.validation_errors)}")
                return False
    
    except KeyboardInterrupt:
        logger.warning("⚠️ Process interrupted by user")
        return False
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
        return False


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = setup_command_line_args()
    args = parser.parse_args()
    
    # Print header
    print("🧬 LOINC to OCL Transformation - Phase 2: Concept Creation")
    print("=" * 70)
    print("Target: Transform LOINC data into OCL-compliant concept objects")
    print("Expected: ~180K concepts, <30 seconds, multi-language support")
    print("=" * 70)
    
    # Validate environment
    if not validate_environment():
        print("\n❌ Environment validation failed")
        print("Please resolve the issues above before running Phase 2")
        return 1
    
    print()  # Add spacing
    
    # Run the transformation
    try:
        success = run_phase2_transformation(args)
        
        if success:
            print("\n🎉 Phase 2: Concept Creation completed successfully!")
            print("📊 Check the output directory for generated concept files")
            print("🔄 Ready for Phase 3: Mapping Creation")
            return 0
        else:
            print("\n❌ Phase 2: Concept Creation failed")
            print("📋 Check the logs for detailed error information")
            return 1
    
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
