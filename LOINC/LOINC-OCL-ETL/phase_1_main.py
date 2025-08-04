"""
Main Entry Point for LOINC to OCL Transformation - Phase 1: Foundation & Data Loading

This module provides the main entry point and orchestration for Phase 1 of the
LOINC to OCL transformation project. Phase 1 focuses on:

1. Configuration management and validation
2. File loading and parsing with error handling  
3. Data validation and integrity checks
4. Cross-reference table creation
5. Foundation setup for subsequent phases

Usage:
    python phase_1_main.py [options]

Author: LOINC OCL Transform Project
Date: July 2025
"""

import sys
import argparse
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

# Import Phase 1 modules
from config_manager import ConfigManager
from file_handler import FileHandler  
from validator import DataValidator
from data_loader import DataLoader
from logger import TransformationLogger


def setup_command_line_args() -> argparse.ArgumentParser:
    """Set up command line argument parsing"""
    
    parser = argparse.ArgumentParser(
        description="LOINC to OCL Transformation - Phase 1: Foundation & Data Loading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python phase_1_main.py                          # Run with default settings
    python phase_1_main.py --config ./config       # Use specific config directory
    python phase_1_main.py --log-level DEBUG       # Enable debug logging
    python phase_1_main.py --skip-validation       # Skip data validation (faster)
    python phase_1_main.py --test-mode             # Run in test mode with sample data
        """
    )
    
    # Configuration options
    parser.add_argument(
        '--config', '--config-dir',
        type=str,
        help='Directory containing configuration files (default: current directory)'
    )
    
    # Logging options
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    # Processing options
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip comprehensive data validation (speeds up processing)'
    )
    
    parser.add_argument(
        '--skip-cross-refs',
        action='store_true', 
        help='Skip cross-reference table creation'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode with limited data processing'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Override output directory from configuration'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimize console output (errors only)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration and files without processing data'
    )
    
    return parser


def validate_environment() -> bool:
    """Validate that the environment is ready for processing"""
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or higher is required")
        return False
    
    # Check required modules
    required_modules = ['pandas', 'chardet', 'yaml']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"ERROR: Missing required modules: {', '.join(missing_modules)}")
        print("Please install them using: pip install " + " ".join(missing_modules))
        return False
    
    return True


def run_phase1_foundation(args: argparse.Namespace) -> bool:
    """
    Run Phase 1: Foundation & Data Loading
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        bool: True if successful, False otherwise
    """
    
    logger_system = None
    
    try:
        # Initialize logging system
        log_level = 'ERROR' if args.quiet else args.log_level
        logger_system = TransformationLogger(log_level=log_level)
        logger = logger_system.get_logger('main')
        
        logger.info("Starting Phase 1: Foundation & Data Loading")
        
        # Phase 1.1: Configuration Loading
        with logger_system.phase_context("Configuration Loading"):
            logger.info("Loading configuration files...")
            data_loader = DataLoader(args.config)
            
            if not data_loader.config_manager.load_all_configs():
                logger.error("Failed to load configuration files")
                return False
            
            # Override output directory if specified
            if args.output_dir:
                data_loader.config_manager.paths.output_dir = Path(args.output_dir)
                data_loader.config_manager.paths.create_directories()
            
                logger.info("[OK] Configuration loaded successfully")
            logger_system.log_statistics("Configuration", {
                "Input Directory": str(data_loader.config_manager.paths.input_dir),
                "Output Directory": str(data_loader.config_manager.paths.output_dir),
                "LOINC Version": data_loader.config_manager.settings.get('loinc_version', 'Unknown'),
                "Transformation Rules Version": data_loader.config_manager.settings.get('transformation_rules_version', 'Unknown')
            })
        
        # Phase 1.2: Data Loading and Validation
        if not args.dry_run:
            with logger_system.phase_context("Data Loading & Validation"):
                logger.info("Loading LOINC data files...")
                logger.debug("About to create DataLoader instance...")
                
                # Run data loading with options
                loading_summary = data_loader.load_all_data(
                    validate_data=not args.skip_validation,
                    create_cross_refs=not args.skip_cross_refs
                )
                
                logger.debug(f"DataLoader completed. Success: {loading_summary.is_successful}")
                logger.debug(f"Errors: {loading_summary.errors}")
                logger.debug(f"Files processed: {loading_summary.total_files_processed}")
                
                if not loading_summary.is_successful:
                    logger.error("Data loading failed")
                    logger.error("Errors encountered:")
                    for error in loading_summary.errors:
                        logger.error(f"  - {error}")
                    return False
                
                logger.info("[OK] Data loading completed successfully")
                
                # Log loading statistics
                logger_system.log_statistics("Data Loading Results", {
                    "Files Processed": loading_summary.successful_files,
                    "Total Rows Loaded": loading_summary.total_rows_loaded,
                    "Processing Time (seconds)": loading_summary.duration_seconds,
                    "Cross-reference Tables Created": len(loading_summary.cross_references),
                    "Validation Errors": loading_summary.validation_report.error_count if loading_summary.validation_report else 0,
                    "Validation Warnings": loading_summary.validation_report.warning_count if loading_summary.validation_report else 0
                })
                
                # Log dataset details
                logger.info("Loaded datasets:")
                for name, dataset in loading_summary.datasets.items():
                    logger.info(f"  {name}: {dataset.row_count:,} rows, {dataset.column_count} columns")
                
                # Log cross-reference tables
                if loading_summary.cross_references:
                    logger.info("Cross-reference tables created:")
                    for name, cross_ref in loading_summary.cross_references.items():
                        entry_count = len(cross_ref.lookup_dict)
                        logger.info(f"  {cross_ref.name}: {entry_count:,} entries")
        
        # Phase 1.3: Foundation Readiness Check
        with logger_system.phase_context("Foundation Readiness Check"):
            logger.info("Verifying Phase 1 foundation readiness...")
            
            readiness_checks = {
                "Configuration Loaded": data_loader.config_manager.settings is not None,
                "Transformation Rules Loaded": data_loader.config_manager.transformation_rules is not None,
                "Output Directory Created": data_loader.config_manager.paths.output_dir.exists(),
            }
            
            if not args.dry_run:
                readiness_checks.update({
                    "Data Successfully Loaded": len(data_loader.datasets) > 0,
                    "No Critical Validation Errors": loading_summary.validation_report is None or loading_summary.validation_report.error_count == 0,
                })
                
                if not args.skip_cross_refs:
                    readiness_checks["Cross-references Created"] = len(data_loader.cross_references) > 0
            
            # Check all conditions
            all_ready = all(readiness_checks.values())
            
            logger.info("Foundation readiness check:")
            for check, status in readiness_checks.items():
                status_symbol = "[OK]" if status else "[FAIL]"
                logger.info(f"  {status_symbol} {check}")
            
            if all_ready:
                logger.info("[OK] Phase 1 foundation is ready for Phase 2 development")
            else:
                logger.error("[FAIL] Phase 1 foundation has issues that need to be resolved")
                return False
        
        return True
        
    except Exception as e:
        if logger_system:
            logger_system.log_error("critical_error", f"Critical error in Phase 1: {str(e)}", exc_info=True)
        else:
            print(f"CRITICAL ERROR: {str(e)}")
            traceback.print_exc()
        return False
    
    finally:
        if logger_system:
            logger_system.finalize_session()


def run_test_mode(args: argparse.Namespace) -> bool:
    """
    Run in test mode with limited processing for development/testing
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        bool: True if successful, False otherwise
    """
    
    print("=" * 60)
    print("RUNNING IN TEST MODE")
    print("=" * 60)
    
    try:
        # Test configuration loading
        print("Testing configuration loading...")
        config_mgr = ConfigManager(args.config)
        
        if config_mgr.load_all_configs():
            print("[OK] Configuration loading: PASSED")
            print(f"  Input directory: {config_mgr.paths.input_dir}")
            print(f"  Output directory: {config_mgr.paths.output_dir}")
        else:
            print("[FAIL] Configuration loading: FAILED")
            return False
        
        # Test file discovery
        print("\nTesting file discovery...")
        file_handler = FileHandler(config_mgr)
        
        input_dir = config_mgr.paths.input_dir
        
        # Use the same LOINC file structure as data_loader
        loinc_file_locations = [
            ('Loinc.csv', 'LoincTable/Loinc.csv'),
            ('Part.csv', 'AccessoryFiles/PartFile/Part.csv'),
            ('AnswerList.csv', 'AccessoryFiles/AnswerFile/AnswerList.csv'),
            ('LoincAnswerListLink.csv', 'AccessoryFiles/AnswerFile/LoincAnswerListLink.csv'),
            ('PanelsAndForms.csv', 'AccessoryFiles/PanelsAndForms/PanelsAndForms.csv'),
            ('MapTo.csv', 'LoincTable/MapTo.csv')
        ]
        
        found_files = []
        for file_name, relative_path in loinc_file_locations:
            file_path = input_dir / relative_path
            if file_path.exists():
                found_files.append((file_name, relative_path))
        
        if found_files:
            print(f"[OK] File discovery: Found {len(found_files)} LOINC files")
            for file_name, relative_path in found_files:
                print(f"  - {file_name}")
                print(f"    Location: {relative_path}")
        else:
            print("[FAIL] File discovery: No LOINC files found in expected locations")
            print("\nChecking expected locations:")
            for file_name, relative_path in loinc_file_locations:
                full_path = input_dir / relative_path
                exists = "[OK]" if full_path.exists() else "[FAIL]"
                print(f"  {exists} {file_name}")
                print(f"    Expected: {relative_path}")
                print(f"    Full path: {full_path}")
                
            # Also check what's actually in the base directory
            print(f"\nActual contents of {input_dir}:")
            try:
                import os
                for item in sorted(os.listdir(input_dir)):
                    item_path = input_dir / item
                    item_type = "DIR" if item_path.is_dir() else "FILE"
                    print(f"  {item_type}: {item}")
            except Exception as e:
                print(f"  Error listing directory: {e}")
                
            return False
        
        # Test file analysis on first found file
        if found_files:
            first_file_name, first_relative_path = found_files[0]
            first_file_path = input_dir / first_relative_path
            print(f"\nTesting file analysis on {first_file_name}...")
            try:
                file_info = file_handler.analyze_file(first_file_path)
                print("[OK] File analysis: PASSED")
                print(f"  Encoding: {file_info.encoding}")
                print(f"  Delimiter: '{file_info.delimiter}'")
                print(f"  Columns: {file_info.column_count}")
                print(f"  Estimated rows: {file_info.row_count:,}")
                print(f"  Sample columns: {file_info.columns[:5]}")
            except Exception as e:
                print(f"[FAIL] File analysis: FAILED - {str(e)}")
                return False
        
        # Test validation setup
        print("\nTesting validation setup...")
        validator = DataValidator(config_mgr)
        print(f"[OK] Validation setup: {len(validator.validation_rules)} rules loaded")
        
        print("\n" + "=" * 60)
        print("TEST MODE COMPLETED SUCCESSFULLY")
        print("Phase 1 components are ready for full processing")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Test mode failed: {str(e)}")
        traceback.print_exc()
        return False


def main() -> int:
    """
    Main entry point for Phase 1 processing
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    
    # Parse command line arguments
    parser = setup_command_line_args()
    args = parser.parse_args()
    
    # Validate environment
    if not validate_environment():
        return 1
    
    # Show banner
    if not args.quiet:
        print("=" * 60)
        print("LOINC TO OCL TRANSFORMATION")
        print("Phase 1: Foundation & Data Loading")
        print("=" * 60)
    
    try:
        # Run in test mode or full processing mode
        if args.test_mode:
            success = run_test_mode(args)
        else:
            success = run_phase1_foundation(args)
        
        if success:
            if not args.quiet:
                print("\n[OK] Phase 1 completed successfully!")
                print("The foundation is ready for Phase 2 development.")
            return 0
        else:
            if not args.quiet:
                print("\n[FAIL] Phase 1 failed!")
                print("Please check the logs for details.")
            return 1
            
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n\nProcess interrupted by user")
        return 1
    
    except Exception as e:
        if not args.quiet:
            print(f"\nUnexpected error: {str(e)}")
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())