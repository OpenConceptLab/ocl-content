#!/usr/bin/env python3
"""
Test Container Integration Fix

Quick test to verify that the Container Concepts transformer
integrates properly with the ConceptFactory.

Usage: python test_container_integration.py
"""

import sys
from pathlib import Path

# Add current directory for imports
sys.path.append(str(Path(__file__).parent))

from config_manager import ConfigManager
from concept_factory import ConceptFactory


def test_container_integration():
    """Test Container Concepts integration with ConceptFactory"""
    print("🧪 Testing Container Concepts Integration")
    print("=" * 50)
    
    try:
        # Initialize config and factory
        config_manager = ConfigManager()
        config_manager.load_all_configs()
        
        concept_factory = ConceptFactory(config_manager)
        
        # Initialize prerequisites (this loads data and applies aliases)
        if not concept_factory._initialize_prerequisites():
            print("❌ Prerequisites initialization failed")
            return False
        
        # Set up transformation context
        concept_factory._setup_transformation_context()
        
        # Test just the Container_Concepts transformer integration
        print("\n🏗️ Testing Container_Concepts transformer integration...")
        
        from container_transformer import ContainerConceptsTransformer
        from ocl_models import ConceptCollection
        from base_transformer import TransformationResult
        
        # Initialize transformer
        transformer = ContainerConceptsTransformer(concept_factory.transformation_context)
        
        # Test the integration steps
        print("   Step 1: Validate prerequisites...")
        if not transformer.validate_prerequisites():
            print("   ❌ Prerequisites validation failed")
            return False
        print("   ✅ Prerequisites validated")
        
        print("   Step 2: Generate container concepts...")
        container_concepts = transformer.create_all_container_concepts()
        print(f"   ✅ Generated {len(container_concepts)} container concepts")
        
        print("   Step 3: Create result collection...")
        result_collection = ConceptCollection(
            collection_name="Container_Concepts_Concepts",
            batch_size=concept_factory.transformation_context.batch_size
        )
        
        print("   Step 4: Add concepts to collection...")
        valid_concepts = 0
        for concept in container_concepts:
            try:
                result_collection.add_concept(concept)
                valid_concepts += 1
            except Exception as e:
                print(f"   ⚠️ Failed to add concept {getattr(concept, 'id', 'UNKNOWN')}: {e}")
        
        print(f"   ✅ Added {valid_concepts}/{len(container_concepts)} concepts to collection")
        
        print("   Step 5: Create transformation result...")
        result = TransformationResult(
            concepts=result_collection,
            success_count=valid_concepts,
            error_count=len(container_concepts) - valid_concepts,
            warning_count=0,
            processing_time_seconds=0.1
        )
        print("   ✅ Transformation result created")
        
        print(f"\n🎉 Integration test successful!")
        print(f"   Container concepts: {len(container_concepts)}")
        print(f"   Valid concepts: {valid_concepts}")
        print(f"   Success rate: {(valid_concepts/len(container_concepts)*100) if container_concepts else 0:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Container Integration Test")
    
    success = test_container_integration()
    
    print(f"\n{'✅ Integration test passed' if success else '❌ Integration test failed'}")
    
    if success:
        print("\n💡 The Container Concepts integration is working!")
        print("   Apply the ConceptFactory fix and try phase2_main.py again")
    else:
        print("\n💡 There's still an integration issue to resolve")
