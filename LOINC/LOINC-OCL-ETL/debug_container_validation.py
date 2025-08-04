#!/usr/bin/env python3
"""
Debug Container Concepts Validation Issues

Identifies why all 469 container concepts are failing OCL validation.
Tests individual container concepts to find validation problems.

Usage: python debug_container_validation.py
"""

import pandas as pd
import sys
from pathlib import Path

# Add current directory for imports
sys.path.append(str(Path(__file__).parent))

from config_manager import ConfigManager
from data_loader import DataLoader
from container_transformer import ContainerConceptsTransformer
from base_transformer import TransformationContext
from ocl_validator import OCLConceptValidator


def debug_container_validation():
    """Debug Container Concepts validation step by step"""
    print("🔍 Debugging Container Concepts Validation")
    print("=" * 60)
    
    try:
        # Step 1: Setup
        config_manager = ConfigManager()
        config_manager.load_all_configs()
        
        data_loader = DataLoader(config_manager.config_dir)
        loading_summary = data_loader.load_all_data(validate_data=False)
        
        # Apply dataset aliases
        datasets = loading_summary.datasets
        if 'Loinc.csv' in datasets and 'loinc_terms' not in datasets:
            datasets['loinc_terms'] = datasets['Loinc.csv']
        
        # Step 2: Create transformer
        context = TransformationContext(
            config_manager=config_manager,
            transformation_rules=config_manager.transformation_rules,
            source_datasets=datasets,
            language_datasets={},
            cross_references=loading_summary.cross_references,
            batch_size=100
        )
        
        transformer = ContainerConceptsTransformer(context)
        
        # Step 3: Create container concepts
        print("🏗️ Creating container concepts...")
        container_concepts = transformer.create_all_container_concepts()
        print(f"✅ Created {len(container_concepts)} container concepts")
        
        # Step 4: Test first few concepts individually
        print("\n🧪 Testing individual container concept validation...")
        
        validator = OCLConceptValidator(strict_mode=True)
        
        for i, concept in enumerate(container_concepts[:5]):  # Test first 5
            print(f"\n   Container Concept {i+1}: {concept.id}")
            print(f"   Name: {concept.names[0].name if concept.names else 'NO NAMES'}")
            print(f"   Concept Class: {concept.concept_class}")
            print(f"   Owner: {concept.owner}")
            print(f"   Source: {concept.source}")
            
            # Test individual validation
            validation_errors = concept.get_validation_errors()
            if validation_errors:
                print(f"   ❌ Validation Errors:")
                for error in validation_errors:
                    print(f"      - {error}")
            else:
                print(f"   ✅ Individual validation passed")
            
            # Test OCL validator
            from ocl_models import ConceptCollection
            test_collection = ConceptCollection("Test")
            test_collection.add_concept(concept)
            
            validation_report = validator.validate_collection(test_collection)
            if validation_report.has_errors:
                errors = validation_report.get_errors()
                print(f"   ❌ OCL Validator Errors:")
                for error in errors:
                    print(f"      - {error.concept_id}: {error.message}")
            else:
                print(f"   ✅ OCL validator passed")
            
            # Inspect concept structure
            print(f"   📋 Concept Structure:")
            print(f"      ID: {concept.id}")
            print(f"      Concept Class: {concept.concept_class}")
            print(f"      Owner: {concept.owner}")
            print(f"      Source: {concept.source}")
            print(f"      Names count: {len(concept.names)}")
            print(f"      Descriptions count: {len(concept.descriptions)}")
            print(f"      Retired: {concept.retired}")
            print(f"      External ID: {concept.external_id}")
            
            if concept.names:
                first_name = concept.names[0]
                print(f"      First name: '{first_name.name}'")
                print(f"      Name locale: {first_name.locale}")
                print(f"      Name type: {first_name.name_type}")
                print(f"      Name preferred: {first_name.locale_preferred}")
            
            # Show JSON structure
            try:
                json_str = concept.to_json()
                print(f"      JSON length: {len(json_str)} characters")
                # Show first 200 characters
                print(f"      JSON preview: {json_str[:200]}...")
            except Exception as e:
                print(f"      ❌ JSON serialization failed: {e}")
        
        # Step 5: Common validation issues check
        print(f"\n🔧 Common Container Concept Issues Check:")
        
        issues_found = []
        
        for concept in container_concepts[:10]:  # Check first 10
            # Check required fields
            if not concept.id:
                issues_found.append("Missing concept.id")
            if not concept.concept_class:
                issues_found.append("Missing concept.concept_class")
            if not concept.owner:
                issues_found.append("Missing concept.owner")
            if not concept.source:
                issues_found.append("Missing concept.source")
            if not concept.names:
                issues_found.append("Missing concept.names")
            
            # Check names structure
            for name in concept.names:
                if not name.name:
                    issues_found.append("Empty name.name")
                if not name.locale:
                    issues_found.append("Missing name.locale")
                if not name.name_type:
                    issues_found.append("Missing name.name_type")
                if name.locale_preferred is None:
                    issues_found.append("Missing name.locale_preferred")
        
        if issues_found:
            print("   ❌ Common issues found:")
            unique_issues = list(set(issues_found))
            for issue in unique_issues:
                count = issues_found.count(issue)
                print(f"      - {issue} (found {count} times)")
        else:
            print("   ✅ No common validation issues found")
        
        return len(issues_found) == 0
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def suggest_container_validation_fixes():
    """Suggest specific fixes for container concept validation"""
    print(f"\n🔧 Container Concept Validation Fixes:")
    print("-" * 50)
    
    print("1. **Check Required Fields**: Ensure all containers have:")
    print("   - concept.id (not None/empty)")
    print("   - concept.concept_class (valid OCL class)")
    print("   - concept.owner (should be 'LOINC')")
    print("   - concept.source (should be 'LOINC')")
    print("   - concept.names (at least one name)")
    
    print("\n2. **Fix Names Structure**: Each name must have:")
    print("   - name.name (not None/empty)")
    print("   - name.locale ('en' for English)")
    print("   - name.name_type ('Fully Specified')")
    print("   - name.locale_preferred (True for primary name)")
    
    print("\n3. **Check Concept Classes**: Container classes might be invalid")
    print("   - Try 'Concept' instead of 'Component Container'")
    print("   - Check OCL-supported concept classes")
    
    print("\n4. **Fix Boolean Fields**: Ensure proper boolean types:")
    print("   - concept.retired should be True/False, not None")
    print("   - name.locale_preferred should be True/False")


if __name__ == "__main__":
    print("🚀 Starting Container Concepts Validation Debug")
    
    success = debug_container_validation()
    
    if not success:
        suggest_container_validation_fixes()
        
    print(f"\n{'✅ Validation debug completed' if success else '❌ Validation issues found'}")
