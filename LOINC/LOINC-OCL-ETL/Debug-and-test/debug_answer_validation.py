#!/usr/bin/env python3
"""
Debug Answer Lists Validation Issues

Identifies and fixes the root causes of Answer Lists validation failures.
Creates a sample Answer List concept and validates it step-by-step to find issues.

Usage: python debug_answer_validation.py
"""

import pandas as pd
import sys
from pathlib import Path

# Add current directory for imports
sys.path.append(str(Path(__file__).parent))

from phase1_2_data_processing.config_manager import ConfigManager
from phase1_2_data_processing.data_loader import DataLoader
from phase1_2_data_processing.answer_transformer import AnswerListsTransformer
from phase1_2_data_processing.base_transformer import TransformationContext
from phase1_2_data_processing.ocl_models import OCLConcept
from phase1_2_data_processing.ocl_validator import OCLConceptValidator


def debug_answer_lists_validation():
    """Debug Answer Lists validation step by step"""
    print("🔍 Debugging Answer Lists Validation Issues")
    print("=" * 60)
    
    try:
        # Step 1: Load data and setup
        print("📋 Step 1: Loading data...")
        config_manager = ConfigManager()
        config_manager.load_all_configs()
        
        data_loader = DataLoader(config_manager.config_dir)
        loading_summary = data_loader.load_all_data(validate_data=False)
        
        # Apply dataset aliases (same fix that worked for main script)
        datasets = loading_summary.datasets
        if 'AnswerList.csv' in datasets and 'answer_lists' not in datasets:
            # Handle LoadedDataset objects properly
            answer_data = datasets['AnswerList.csv']
            if hasattr(answer_data, 'data'):
                datasets['answer_lists'] = answer_data.data
            else:
                datasets['answer_lists'] = answer_data
        
        # Get the actual data for length calculation
        answer_lists_data = datasets['answer_lists']
        if hasattr(answer_lists_data, 'data'):
            answer_lists_data = answer_lists_data.data
            
        print(f"✅ Data loaded: {len(answer_lists_data)} answer lists")
        
        # Step 2: Create transformation context
        print("\n⚙️ Step 2: Setting up transformer...")
        context = TransformationContext(
            config_manager=config_manager,
            transformation_rules=config_manager.transformation_rules,
            source_datasets=datasets,
            language_datasets={},
            cross_references=loading_summary.cross_references,
            batch_size=100
        )
        
        transformer = AnswerListsTransformer(context)
        print("✅ Transformer initialized")
        
        # Step 3: Test single record transformation
        print("\n🧪 Step 3: Testing single record transformation...")
        answer_lists_df = datasets['answer_lists']
        
        # Use .data if it's a LoadedDataset, otherwise use directly
        if hasattr(answer_lists_df, 'data'):
            answer_lists_df = answer_lists_df.data
            
        sample_record = answer_lists_df.iloc[0]
        print(f"Sample record fields: {list(sample_record.index)}")
        print(f"Sample record preview:")
        for field in ['AnswerListId', 'AnswerListName'][:2]:
            if field in sample_record:
                print(f"  {field}: {sample_record[field]}")
        
        try:
            concept = transformer.transform_record(sample_record)
            print("✅ Record transformation successful")
            
            # Step 4: Validate the created concept
            print("\n🔍 Step 4: Validating created concept...")
            print(f"Concept ID: {concept.id}")
            print(f"Concept class: {concept.concept_class}")
            print(f"Names: {len(concept.names)}")
            print(f"Owner: {concept.owner}")
            print(f"Source: {concept.source}")
            
            # Check required fields
            print("\n📋 Required field check:")
            required_fields = ['id', 'concept_class', 'owner', 'source']
            for field in required_fields:
                value = getattr(concept, field, None)
                status = "✅" if value else "❌"
                print(f"  {field}: {status} {value}")
            
            # Check names
            print(f"\n📝 Names check:")
            if concept.names:
                for i, name in enumerate(concept.names):
                    print(f"  Name {i+1}: {name.name[:50]}...")
                    print(f"    Locale: {name.locale}")
                    print(f"    Name type: {name.name_type}")
            else:
                print("  ❌ No names found")
            
            # Step 5: Run OCL validation
            print("\n🔍 Step 5: Running OCL validation...")
            validator = OCLConceptValidator(strict_mode=True)
            
            # Test individual concept validation
            validation_errors = concept.get_validation_errors()
            if validation_errors:
                print("❌ Concept validation errors:")
                for error in validation_errors:
                    print(f"  - {error}")
            else:
                print("✅ Individual concept validation passed")
            
            # Test validator validation
            from phase1_2_data_processing.ocl_models import ConceptCollection
            collection = ConceptCollection("Test")
            collection.add_concept(concept)
            
            report = validator.validate_collection(collection)
            print(f"Validator results: {report.valid_concepts} valid, {report.invalid_concepts} invalid")
            
            if report.has_errors:
                errors = report.get_errors()
                print("❌ Validator errors:")
                for error in errors:
                    print(f"  - {error.concept_id}: {error.message}")
            else:
                print("✅ Validator validation passed")
                
        except Exception as e:
            print(f"❌ Record transformation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 6: Test multiple records
        print(f"\n📊 Step 6: Testing multiple records...")
        test_size = min(10, len(answer_lists_df))
        valid_count = 0
        invalid_count = 0
        
        for i in range(test_size):
            try:
                test_record = answer_lists_df.iloc[i]
                test_concept = transformer.transform_record(test_record)
                
                # Quick validation check
                if test_concept.is_valid():
                    valid_count += 1
                else:
                    invalid_count += 1
                    if invalid_count <= 3:  # Show first 3 errors
                        errors = test_concept.get_validation_errors()
                        print(f"  Invalid concept {test_concept.id}: {errors[0] if errors else 'Unknown error'}")
                        
            except Exception as e:
                invalid_count += 1
                if invalid_count <= 3:
                    print(f"  Transform error for record {i}: {e}")
        
        print(f"Results: {valid_count}/{test_size} valid concepts")
        
        if invalid_count > 0:
            print(f"\n💡 Common validation fixes needed:")
            print("1. Check required fields are populated")
            print("2. Ensure concept_class is valid OCL class")  
            print("3. Verify names array is not empty")
            print("4. Check owner and source fields")
            print("5. Validate data types")
            
        return valid_count > invalid_count
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def suggest_fixes():
    """Suggest specific fixes for Answer Lists validation issues"""
    print(f"\n🔧 Suggested Fixes for Answer Lists Transformer:")
    print("-" * 50)
    
    print("1. **Fix Required Fields**: Ensure these are never None/empty:")
    print("   - concept.id (from AnswerListId)")
    print("   - concept.concept_class (should be 'AnswerList' or 'Reference Set')")
    print("   - concept.owner (should be 'LOINC')")
    print("   - concept.source (should be 'LOINC')")
    
    print("\n2. **Fix Names Array**: Every concept needs at least one name:")
    print("   - Check AnswerListName is not None/empty")
    print("   - Ensure name_type is valid ('Fully Specified', 'Short', etc.)")
    print("   - Verify locale is valid ('en', 'fr', etc.)")
    
    print("\n3. **Fix Data Types**: Ensure proper types:")
    print("   - concept.id should be string")
    print("   - concept.retired should be boolean")
    print("   - names should be list of OCLName objects")
    
    print("\n4. **Handle Missing Data**: Add fallbacks:")
    print("   - Use AnswerListId as name if AnswerListName is missing")
    print("   - Set default concept_class if not determinable") 
    print("   - Handle None/NaN values gracefully")


if __name__ == "__main__":
    print("🚀 Starting Answer Lists Validation Debug")
    
    success = debug_answer_lists_validation()
    
    if not success:
        suggest_fixes()
        
    print(f"\n{'✅ Debug completed successfully' if success else '❌ Debug found issues'}")
    print("Apply the suggested fixes to answer_transformer.py to resolve validation failures")