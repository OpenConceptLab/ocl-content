#!/usr/bin/env python3
"""
Debug Container Concepts Transformer Error

This script helps identify exactly where the 'list' object has no attribute 'get' error
is occurring in the Container Concepts transformer.

Usage: python debug_container_error.py
"""

import pandas as pd
import sys
import traceback
from pathlib import Path

# Add current directory for imports
sys.path.append(str(Path(__file__).parent))

from phase1_2_data_processing.config_manager import ConfigManager
from phase1_2_data_processing.data_loader import DataLoader
from phase1_2_data_processing.container_transformer import ContainerConceptsTransformer
from phase1_2_data_processing.base_transformer import TransformationContext


def debug_container_transformer():
    """Debug Container Concepts transformer step by step"""
    print("🔍 Debugging Container Concepts Transformer")
    print("=" * 60)
    
    try:
        # Step 1: Load data and setup
        print("📋 Step 1: Loading data...")
        config_manager = ConfigManager()
        config_manager.load_all_configs()
        
        data_loader = DataLoader(config_manager.config_dir)
        loading_summary = data_loader.load_all_data(validate_data=False)
        
        # Apply dataset aliases
        datasets = loading_summary.datasets
        if 'Loinc.csv' in datasets and 'loinc_terms' not in datasets:
            datasets['loinc_terms'] = datasets['Loinc.csv']
        
        print(f"✅ Data loaded successfully")
        print(f"Available datasets: {list(datasets.keys())[:5]}...")
        
        # Step 2: Check the specific dataset we'll be accessing
        print("\n🔍 Step 2: Checking loinc_terms dataset...")
        loinc_data = datasets.get('loinc_terms')
        
        print(f"Dataset type: {type(loinc_data)}")
        if hasattr(loinc_data, 'data'):
            print(f"Has .data attribute: True")
            print(f"Data type: {type(loinc_data.data)}")
            actual_data = loinc_data.data
        else:
            print(f"Has .data attribute: False")
            actual_data = loinc_data
        
        if hasattr(actual_data, 'columns'):
            print(f"Columns available: {list(actual_data.columns)[:5]}...")
        
        # Step 3: Create transformation context
        print("\n⚙️ Step 3: Setting up transformer...")
        context = TransformationContext(
            config_manager=config_manager,
            transformation_rules=config_manager.transformation_rules,
            source_datasets=datasets,
            language_datasets={},
            cross_references=loading_summary.cross_references,
            batch_size=100
        )
        
        # Step 4: Initialize transformer
        print("\n🏗️ Step 4: Initializing Container Concepts transformer...")
        transformer = ContainerConceptsTransformer(context)
        print("✅ Transformer initialized")
        
        # Step 5: Test the safe dataset access method
        print("\n🧪 Step 5: Testing safe dataset access...")
        test_dataset = transformer._get_dataset_safely('loinc_terms')
        print(f"Safe dataset access result: {type(test_dataset)}")
        
        if test_dataset is not None:
            if hasattr(test_dataset, 'columns'):
                print(f"Dataset columns: {list(test_dataset.columns)[:5]}...")
                print(f"Dataset shape: {test_dataset.shape}")
            else:
                print(f"Dataset is not a DataFrame: {type(test_dataset)}")
        else:
            print("❌ Safe dataset access returned None")
            return False
        
        # Step 6: Test prerequisite validation
        print("\n✅ Step 6: Testing prerequisite validation...")
        try:
            prereq_result = transformer.validate_prerequisites()
            print(f"Prerequisites validation: {'✅ PASS' if prereq_result else '❌ FAIL'}")
        except Exception as e:
            print(f"❌ Prerequisites validation failed: {e}")
            traceback.print_exc()
            return False
        
        # Step 7: Test container creation (this is where the error likely occurs)
        print("\n🎯 Step 7: Testing container creation...")
        
        # Test each container type individually
        container_methods = [
            ('Component Containers', transformer._create_component_containers),
            ('Property Containers', transformer._create_property_containers),
            ('System Containers', transformer._create_system_containers),
            ('Class Containers', transformer._create_class_containers),
            ('Root Containers', transformer._create_root_containers)
        ]
        
        for container_type, method in container_methods:
            print(f"\n   Testing {container_type}...")
            try:
                containers = method()
                print(f"   ✅ {container_type}: Created {len(containers)} containers")
            except Exception as e:
                print(f"   ❌ {container_type} failed: {e}")
                print(f"   Full error:")
                traceback.print_exc()
                return False
        
        # Step 8: Test full container creation
        print("\n🚀 Step 8: Testing full container creation...")
        try:
            all_containers = transformer.create_all_container_concepts()
            print(f"✅ Full container creation successful: {len(all_containers)} containers")
            return True
        except Exception as e:
            print(f"❌ Full container creation failed: {e}")
            print(f"Full error:")
            traceback.print_exc()
            return False
    
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        traceback.print_exc()
        return False


def suggest_additional_fixes():
    """Suggest additional fixes if the debug reveals issues"""
    print(f"\n🔧 Additional Debugging Steps:")
    print("-" * 50)
    
    print("1. **Check for other .get() calls**: Search for any remaining .get() calls in container_transformer.py")
    print("2. **Verify dataset structure**: Ensure datasets are properly converted to DataFrames")
    print("3. **Check transformation rules**: Verify transformation_rules object structure")
    print("4. **Add more error handling**: Wrap suspect code in try-catch blocks")
    
    print(f"\n💡 Quick fix suggestions:")
    print("- Add print statements to identify exactly where the error occurs")
    print("- Check if any other methods are accessing datasets incorrectly")
    print("- Verify that all datasets are properly aliased")


if __name__ == "__main__":
    print("🚀 Starting Container Concepts Debug")
    
    success = debug_container_transformer()
    
    if not success:
        suggest_additional_fixes()
        
    print(f"\n{'✅ Debug completed successfully' if success else '❌ Debug found issues'}")
