#!/usr/bin/env python3
"""
Test Enhanced Validation System - Fixed Version

This script tests the enhanced LOINC validation system to ensure it provides
meaningful validation based on the LOINC Model requirements without being
overly strict on non-critical fields.

This version works with your actual DataLoader implementation.

Usage:
    python test_enhanced_validation.py [--detailed] [--save-report]

Author: LOINC OCL Transform Project
Date: July 2025
"""

import sys
import argparse
from pathlib import Path
import logging

# Add current directory to path to import our modules
sys.path.append(str(Path(__file__).parent))

try:
    from config_manager import ConfigManager
    from data_loader import DataLoader
    from logger import TransformationLogger
    from validator import DataValidator  # This will be our enhanced validator
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the correct directory with all Python files present.")
    sys.exit(1)


def test_enhanced_validation(detailed: bool = False, save_report: bool = False):
    """
    Test the enhanced validation system
    
    Args:
        detailed: If True, show detailed validation results
        save_report: If True, save detailed report to file
    """
    print("🧪 Testing Enhanced LOINC Validation System")
    print("=" * 60)
    
    # Setup logging
    logger_system = TransformationLogger(log_level="INFO")
    logger = logger_system.get_logger("test_validation")
    
    try:
        # 1. Initialize configuration
        print("📋 Step 1: Loading configuration...")
        config_manager = ConfigManager()
        
        if not config_manager.load_settings():
            print("❌ Failed to load settings")
            return False
            
        if not config_manager.load_transformation_rules():
            print("❌ Failed to load transformation rules")
            return False
            
        if not config_manager.load_file_mappings():
            print("❌ Failed to load file mappings")
            return False
            
        print("✅ Configuration loaded successfully")
        
        # 2. Initialize components  
        print("\n🔧 Step 2: Initializing components...")
        data_loader = DataLoader()  # DataLoader creates its own components
        validator = DataValidator(config_manager)  # Enhanced validator
        
        print("✅ Components initialized")
        
        # 3. Load data using DataLoader
        print("\n📊 Step 3: Loading LOINC data...")
        print("   This may take a moment for large datasets...")
        
        # Load all data (this will discover files, load them, and create cross-references)
        loading_summary = data_loader.load_all_data(
            validate_data=False,  # We'll do validation separately
            create_cross_refs=True
        )
        
        if not loading_summary.is_successful:
            print("❌ Failed to load data")
            for error in loading_summary.errors:
                print(f"   Error: {error}")
            return False
            
        total_records = loading_summary.total_rows_loaded
        print(f"✅ Data loaded successfully:")
        print(f"   - Files: {loading_summary.successful_files}")
        print(f"   - Total records: {total_records:,}")
        
        # Get loaded data for validation
        loaded_data = {}
        for file_name, dataset in loading_summary.datasets.items():
            loaded_data[file_name] = dataset.data
        
        # 4. Run enhanced validation
        print("\n🔍 Step 4: Running enhanced validation...")
        print("   This may take a moment for large datasets...")
        
        validation_report = validator.validate_data(loaded_data)
        
        # 5. Display results
        print("\n📈 Step 5: Validation Results")
        print("=" * 40)
        print(f"Files validated: {validation_report.total_files_validated}")
        print(f"Total records: {validation_report.total_rows_validated:,}")
        print(f"Overall result: {'✅ PASSED' if validation_report.is_valid() else '❌ FAILED'}")
        print()
        print(f"Issue Summary:")
        print(f"  🔴 Critical Errors: {validation_report.error_count:,}")
        print(f"  🟡 Quality Warnings: {validation_report.warning_count:,}")
        print(f"  🔵 Informational: {validation_report.info_count:,}")
        print(f"  📊 Total Issues: {validation_report.total_issues:,}")
        
        # 6. Show detailed results if requested
        if detailed:
            print("\n📋 Detailed Issues:")
            print("-" * 40)
            
            # Show critical errors first
            errors = [issue for issue in validation_report.issues if issue.severity == "ERROR"]
            if errors:
                print("\n🔴 CRITICAL ERRORS (Must fix):")
                for error in errors:
                    print(f"   {error.file_name}: {error.message}")
                    if error.count > 1:
                        print(f"     (Count: {error.count})")
            else:
                print("\n✅ No critical errors found!")
            
            # Show some warnings
            warnings = [issue for issue in validation_report.issues if issue.severity == "WARNING"]
            if warnings:
                print(f"\n🟡 QUALITY WARNINGS (Top 5 of {len(warnings)}):")
                for warning in warnings[:5]:
                    print(f"   {warning.file_name}: {warning.message}")
                    if warning.count > 1:
                        print(f"     (Count: {warning.count})")
            
            # Show info items
            info_items = [issue for issue in validation_report.issues if issue.severity == "INFO"]
            if info_items:
                print(f"\n🔵 STATISTICS ({len(info_items)} items):")
                for info in info_items:
                    print(f"   {info.file_name}: {info.message}")
        
        # 7. Save detailed report if requested
        if save_report:
            print("\n💾 Step 6: Saving detailed report...")
            report_path = Path("logs") / "enhanced_validation_report.txt"
            validator.save_detailed_report(validation_report, report_path)
            print(f"✅ Detailed report saved to: {report_path}")
        
        # 8. Summary and recommendations
        print("\n🎯 Summary & Next Steps:")
        print("=" * 40)
        
        if validation_report.is_valid():
            print("✅ VALIDATION PASSED!")
            print("   Your LOINC data is ready for Phase 2 (OCL Concept Creation)")
            print("   The enhanced validation focuses on transformation-critical issues only.")
            print()
            print("📊 Comparison with old validation:")
            print("   - Old system: 224,326 errors (too strict)")
            print(f"   - New system: {validation_report.error_count:,} critical errors + {validation_report.warning_count:,} quality warnings")
            print("   - Result: More realistic and actionable validation")
        else:
            print("❌ VALIDATION FAILED")
            print(f"   Found {validation_report.error_count:,} critical errors that must be resolved")
            print("   These are genuine data quality issues that would block OCL transformation")
            print()
            print("🔧 Recommended actions:")
            print("   1. Review critical errors above")
            print("   2. Check source LOINC data files")
            print("   3. Fix any data format or integrity issues")
            print("   4. Re-run validation")
        
        print()
        print("🚀 Ready for Phase 2?")
        if validation_report.is_valid():
            print("   YES - You can now run: python phase_1_main.py")
        else:
            print("   NO - Fix critical errors first, then re-test")
        
        return validation_report.is_valid()
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Test enhanced LOINC validation system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_enhanced_validation.py                    # Basic test
  python test_enhanced_validation.py --detailed         # Show detailed results
  python test_enhanced_validation.py --save-report      # Save report to file
  python test_enhanced_validation.py --detailed --save-report  # Both options
        """
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed validation results'
    )
    
    parser.add_argument(
        '--save-report',
        action='store_true', 
        help='Save detailed validation report to file'
    )
    
    args = parser.parse_args()
    
    # Run the test
    success = test_enhanced_validation(
        detailed=args.detailed,
        save_report=args.save_report
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()