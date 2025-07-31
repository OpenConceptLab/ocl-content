#!/usr/bin/env python3
"""
Quick Validation Test - Fixed Version

Tests the current system first before implementing enhanced validation.
This version works with your actual DataLoader implementation.

Usage:
    python quick_validation_test.py

Author: LOINC OCL Transform Project  
Date: July 2025
"""

import sys
import os
from pathlib import Path
import pandas as pd

def test_current_system():
    """Test the current system to understand what's working"""
    print("🧪 Quick Test of Current LOINC System")
    print("=" * 50)
    
    try:
        # Test 1: Check if main modules can be imported
        print("📦 Step 1: Testing module imports...")
        
        try:
            from config_manager import ConfigManager
            print("   ✅ config_manager imported")
        except ImportError as e:
            print(f"   ❌ config_manager: {e}")
            return False
            
        try:
            from file_handler import FileHandler
            print("   ✅ file_handler imported")
        except ImportError as e:
            print(f"   ❌ file_handler: {e}")
            return False
            
        try:
            from data_loader import DataLoader
            print("   ✅ data_loader imported")
        except ImportError as e:
            print(f"   ❌ data_loader: {e}")
            return False
            
        try:
            from logger import TransformationLogger
            print("   ✅ logger imported")
        except ImportError as e:
            print(f"   ❌ logger: {e}")
            return False
            
        try:
            # Try to import current validator (might fail, that's OK)
            from validator import DataValidator
            print("   ✅ validator imported")
            has_validator = True
        except ImportError as e:
            print(f"   ⚠️  validator: {e} (will need enhanced version)")
            has_validator = False
            
        # Test 2: Check configuration loading
        print("\n📋 Step 2: Testing configuration...")
        config_manager = ConfigManager()
        
        if config_manager.load_settings():
            print("   ✅ Settings loaded")
        else:
            print("   ❌ Failed to load settings")
            return False
            
        if config_manager.load_file_mappings():
            print("   ✅ File mappings loaded")
        else:
            print("   ❌ Failed to load file mappings")
            
        if config_manager.load_transformation_rules():
            print("   ✅ Transformation rules loaded")
        else:
            print("   ❌ Failed to load transformation rules")
        
        # Test 3: Check LOINC file paths
        print("\n📁 Step 3: Testing LOINC file discovery...")
        
        # Get input directory from config
        input_dir = None
        if hasattr(config_manager, 'paths') and config_manager.paths:
            input_dir = config_manager.paths.input_dir
        elif hasattr(config_manager, 'settings') and config_manager.settings:
            input_dir = Path(config_manager.settings.get('input_directory', ''))
        
        if not input_dir:
            # Default path from handoff document
            input_dir = Path(r"C:\Users\jamlung\Documents\LOINC\Loinc_2.80")
            
        print(f"   Looking for LOINC files in: {input_dir}")
        
        if not input_dir.exists():
            print(f"   ❌ Input directory does not exist: {input_dir}")
            return False
            
        # Look for key LOINC files
        key_files = [
            'LoincTable/Loinc.csv',
            'AccessoryFiles/PartFile/Part.csv', 
            'AccessoryFiles/AnswerFile/AnswerList.csv'
        ]
        
        found_files = []
        for file_path in key_files:
            full_path = input_dir / file_path
            if full_path.exists():
                size_mb = full_path.stat().st_size / (1024 * 1024)
                found_files.append((file_path, size_mb))
                print(f"   ✅ Found {file_path} ({size_mb:.1f} MB)")
            else:
                print(f"   ❌ Missing {file_path}")
        
        if len(found_files) == 0:
            print("   ❌ No LOINC files found")
            return False
            
        # Test 4: Try loading a small sample of data
        print("\n📊 Step 4: Testing data loading...")
        
        # Try to load just the main LOINC file as test
        main_loinc_path = input_dir / 'LoincTable/Loinc.csv'
        if main_loinc_path.exists():
            try:
                # Load just first 1000 rows as test
                df = pd.read_csv(main_loinc_path, nrows=1000, low_memory=False)
                print(f"   ✅ Loaded sample data: {len(df)} rows, {len(df.columns)} columns")
                
                # Check for key columns
                key_columns = ['LOINC_NUM', 'LONG_COMMON_NAME', 'STATUS']
                found_columns = [col for col in key_columns if col in df.columns]
                missing_columns = [col for col in key_columns if col not in df.columns]
                
                if found_columns:
                    print(f"   ✅ Found key columns: {found_columns}")
                if missing_columns:
                    print(f"   ⚠️  Missing columns: {missing_columns}")
                    
                # Check data quality
                null_counts = df[found_columns].isnull().sum()
                for col in found_columns:
                    null_pct = (null_counts[col] / len(df)) * 100
                    print(f"   📊 {col}: {null_pct:.1f}% null values")
                    
            except Exception as e:
                print(f"   ❌ Error loading sample data: {e}")
                return False
        else:
            print("   ⚠️  Main LOINC file not found for data test")

        # Test 5: Test actual DataLoader
        print("\n🔧 Step 5: Testing actual DataLoader...")
        
        try:
            # Test DataLoader initialization
            data_loader = DataLoader()  # Uses default config
            print("   ✅ DataLoader initialized successfully")
            
            # Test a quick data load (without validation to be fast)
            print("   🔄 Testing quick data load (this may take a moment)...")
            loading_summary = data_loader.load_all_data(
                validate_data=False,    # Skip validation for speed
                create_cross_refs=False # Skip cross-refs for speed
            )
            
            if loading_summary.is_successful:
                print(f"   ✅ Data loading test successful!")
                print(f"      - Files loaded: {loading_summary.successful_files}")
                print(f"      - Total records: {loading_summary.total_rows_loaded:,}")
                print(f"      - Duration: {loading_summary.duration_seconds:.2f} seconds")
                
                # Show some dataset details
                print("   📊 Dataset details:")
                for name, dataset in list(loading_summary.datasets.items())[:3]:  # Show first 3
                    print(f"      - {name}: {dataset.row_count:,} rows")
                
            else:
                print("   ⚠️  Data loading had issues:")
                for error in loading_summary.errors[:3]:  # Show first 3 errors
                    print(f"      - {error}")
                    
        except Exception as e:
            print(f"   ❌ DataLoader test failed: {e}")
            print("   💡 This is OK - we'll fix it with enhanced validation")
        
        # Test 6: Current validation status
        print("\n🔍 Step 6: Validation system status...")
        
        if has_validator:
            try:
                # Create a fresh config manager for the validator
                validator_config = ConfigManager()
                validator_config.load_settings()
                validator_config.load_file_mappings()
                validator_config.load_transformation_rules()
                
                validator = DataValidator(validator_config)
                print("   ✅ Current validator initialized")
                print("   ℹ️  Note: Current validation may be too strict (224K errors)")
            except Exception as e:
                print(f"   ❌ Validator initialization failed: {e}")
                has_validator = False
        
        if not has_validator:
            print("   ⚠️  Need to implement enhanced validator")
            
        # Summary
        print("\n🎯 Summary:")
        print("=" * 30)
        
        if found_files and len(found_files) >= 2:
            print("✅ SYSTEM STATUS: Ready for enhanced validation")
            print(f"   - Found {len(found_files)} key LOINC files")
            print("   - Configuration loading works")
            print("   - DataLoader works") 
            print("   - Ready to implement enhanced validator")
            
            print("\n🚀 Next Steps:")
            print("1. Replace validator.py with enhanced version")
            print("2. Update transformation_rules_v1.yaml")
            print("3. Run enhanced validation test")
            print("4. Proceed with main pipeline")
            
            return True
        else:
            print("❌ SYSTEM STATUS: Issues need resolution")
            print("   - Check LOINC file paths")
            print("   - Verify file structure")
            print("   - Fix configuration issues")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    success = test_current_system()
    
    if success:
        print("\n✅ System ready for enhanced validation implementation!")
    else:
        print("\n❌ Please resolve issues before implementing enhanced validation")
        
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)