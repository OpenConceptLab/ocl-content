"""
Fixed Container Concepts Transformer for LOINC to OCL Transformation - Phase 2

This module creates the 7 organizational container concepts as defined in 
transformation_rules_v1.yaml. These are simple organizational containers,
not dynamic containers based on data analysis.

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from .base_transformer import BaseTransformer, TransformationContext, TransformationResult
from .ocl_models import OCLConcept, OCLName, ConceptCollection
import logging
import time


class ContainerConceptsTransformer(BaseTransformer):
    """
    Transformer for creating the 7 static container concepts for organizational hierarchy.
    
    Creates exactly 7 container concepts as defined in transformation_rules_v1.yaml:
    - LOINC_COMPONENT, LOINC_PROPERTY, LOINC_TIME, LOINC_SYSTEM, 
    - LOINC_SCALE, LOINC_METHOD, OTHER
    """
    
    def __init__(self, context: TransformationContext):
        """Initialize Container Concepts transformer"""
        super().__init__(context)
        
        # Container concepts specific configuration
        self.transformer_name = "Container_Concepts"
        self.source_dataset = "container_definitions"  # Virtual dataset
        self.primary_key = "ContainerID"
        
        # Load static container definitions
        self._load_container_definitions()
        
        # Set up base transformer attributes
        self.owner_org = "LOINC"
        self.source_name = "LOINC"
        
        # Statistics for container generation
        self.container_stats = {
            'total_containers': 0
        }
        
        self.logger.info(f"Container Concepts Transformer initialized")
        self.logger.info(f"Will generate {len(self.container_definitions)} static container concepts")
    
    def _get_owner_organization(self) -> str:
        """Get owner organization name"""
        return "Regenstrief"
    
    def _get_supported_locales(self) -> List[str]:
        """Get list of supported locales"""
        return ["en"]  # Containers only support English initially
    
    def _load_container_definitions(self) -> None:
        """Load static container definitions from transformation rules"""
        self.container_definitions = []
        
        try:
            if (hasattr(self.context, 'transformation_rules') and 
                self.context.transformation_rules and
                hasattr(self.context.transformation_rules, 'container_concepts')):
                
                containers = self.context.transformation_rules.container_concepts
                
                if isinstance(containers, list):
                    self.container_definitions = containers
                    self.logger.info(f"Loaded {len(containers)} container definitions from transformation rules")
                else:
                    self.logger.warning(f"Container concepts is {type(containers)}, expected list. Using defaults.")
                    self.container_definitions = self._get_default_containers()
            else:
                self.logger.warning("No container_concepts found in transformation rules. Using defaults.")
                self.container_definitions = self._get_default_containers()
                
        except Exception as e:
            self.logger.warning(f"Error loading container definitions: {e}. Using defaults.")
            self.container_definitions = self._get_default_containers()
    
    def _get_default_containers(self) -> List[Dict[str, str]]:
        """Get default container definitions if not found in transformation rules"""
        return [
            {
                "id": "LOINC_COMPONENT",
                "name": "LOINC Component", 
                "description": "Component parts without clear hierarchy",
                "concept_class": "Misc"
            },
            {
                "id": "LOINC_PROPERTY",
                "name": "LOINC Property",
                "description": "Property parts without clear hierarchy", 
                "concept_class": "Misc"
            },
            {
                "id": "LOINC_TIME",
                "name": "LOINC Time",
                "description": "Time aspects without clear hierarchy",
                "concept_class": "Misc"
            },
            {
                "id": "LOINC_SYSTEM", 
                "name": "LOINC System",
                "description": "System parts without clear hierarchy",
                "concept_class": "Misc"
            },
            {
                "id": "LOINC_SCALE",
                "name": "LOINC Scale", 
                "description": "Scale types without clear hierarchy",
                "concept_class": "Misc"
            },
            {
                "id": "LOINC_METHOD",
                "name": "LOINC Method",
                "description": "Method parts without clear hierarchy", 
                "concept_class": "Misc"
            },
            {
                "id": "OTHER",
                "name": "Other",
                "description": "Uncategorized parts and concepts",
                "concept_class": "Misc" 
            }
        ]
    
    def get_virtual_dataset(self) -> pd.DataFrame:
        """
        Create a virtual DataFrame from container definitions for standard transformer interface.
        
        This allows the container transformer to work with the standard batch processing
        pipeline even though it doesn't read from a real CSV file.
        """
        if not self.container_definitions:
            return pd.DataFrame()
        
        # Convert container definitions to DataFrame
        return pd.DataFrame(self.container_definitions)
    
    def process_batch(self, batch_df: pd.DataFrame) -> List[OCLConcept]:
        """
        Process a batch of container definitions (overrides base method).
        
        For containers, we ignore the batch_df and just create all static containers.
        """
        return self.create_all_container_concepts()
    
    def validate_prerequisites(self) -> bool:
        """
        Validate that prerequisites for container concept creation are met.
        
        Returns:
            bool: True if prerequisites are met, False otherwise
        """
        try:
            # Check that we have container definitions
            if not self.container_definitions:
                self.logger.error("No container definitions available")
                return False
            
            # Validate container definition structure
            for i, container in enumerate(self.container_definitions):
                if not isinstance(container, dict):
                    self.logger.error(f"Container definition {i} is not a dict: {type(container)}")
                    return False
                
                required_fields = ['id', 'name', 'concept_class']
                for field in required_fields:
                    if field not in container:
                        self.logger.error(f"Container definition {i} missing required field: {field}")
                        return False
            
            self.logger.info("Container concepts prerequisites validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Prerequisites validation failed: {e}")
            return False
    
    def create_all_container_concepts(self) -> List[OCLConcept]:
        """
        Create all static container concepts as defined in transformation rules.
        
        Returns:
            List of container OCL concepts
        """
        self.logger.info("Creating static container concepts...")
        
        containers = []
        
        for container_def in self.container_definitions:
            try:
                container = self._create_container_concept(container_def)
                containers.append(container)
                self.container_stats['total_containers'] += 1
                
            except Exception as e:
                self.logger.error(f"Failed to create container {container_def.get('id', 'UNKNOWN')}: {e}")
        
        self.logger.info(f"Created {len(containers)} container concepts")
        return containers
    
    def _create_container_concept(self, container_def: Dict[str, str]) -> OCLConcept:
        """Create a single container concept from definition"""
        
        # Create concept with proper fields
        concept = OCLConcept(
            id=container_def['id'],
            concept_class=container_def['concept_class'],
            datatype='N/A',  # NEW: All containers have N/A datatype
            owner=self.owner_org,
            owner_type="Organization", 
            source=self.source_name,
            retired=False,
            external_id=container_def['id']
        )
        
        # Add name
        concept.add_name(
            name=container_def['name'],
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add description if available
        if 'description' in container_def:
            concept.add_description(
                description=container_def['description'],
                locale="en", 
                locale_preferred=True,
                desc_type="Definition"
            )
        
        # Add container metadata
        concept.extras.update({
            'is_container_concept': True,
            'container_purpose': 'Organizational hierarchy for orphaned LOINC items',
            'container_type': 'static'
        })
        
        concept._source_file = "Static Container Definition"
        
        return concept
    
    def get_transformer_name(self) -> str:
        """Get transformer name (required abstract method)"""
        return self.transformer_name
    
    def get_source_dataset_name(self) -> str:
        """Get source dataset name (required abstract method)"""
        return self.source_dataset
    
    def get_primary_key_field(self) -> str:
        """Get primary key field (required abstract method)"""
        return self.primary_key
    
    def get_concept_class(self, record: pd.Series) -> str:
        """Get concept class for record (required abstract method)"""
        # All containers use 'Misc' concept class
        if hasattr(record, 'get') and 'concept_class' in record:
            return record.get('concept_class', 'Misc')
        return 'Misc'
    
    def transform_record(self, record: pd.Series) -> OCLConcept:
        """Transform a single container definition record into OCL concept (required abstract method)"""
        # Handle different record structures
        if hasattr(record, 'get'):
            # Standard pandas Series with get method
            container_def = {
                'id': record.get('id', f'CONTAINER_{self.container_stats["total_containers"]}'),
                'name': record.get('name', f'Container {self.container_stats["total_containers"]}'),
                'description': record.get('description', 'Organizational container concept'),
                'concept_class': record.get('concept_class', 'Misc')
            }
        else:
            # Fallback for other record types
            container_def = {
                'id': getattr(record, 'id', f'CONTAINER_{self.container_stats["total_containers"]}'),
                'name': getattr(record, 'name', f'Container {self.container_stats["total_containers"]}'),
                'description': getattr(record, 'description', 'Organizational container concept'),
                'concept_class': getattr(record, 'concept_class', 'Misc')
            }
        
        return self._create_container_concept(container_def)
    
    def transform_dataset(self, progress_callback: Optional[callable] = None) -> TransformationResult:
        """
        Transform container definitions dataset (overrides base implementation).
        
        Since containers are static definitions rather than records from a CSV,
        we create concepts directly from the transformation rules.
        """
        start_time = time.time()
        
        self.logger.info(f"Starting {self.get_transformer_name()} transformation")
        
        # Initialize result collection
        result_collection = ConceptCollection(
            collection_name=f"{self.get_transformer_name()}_Concepts",
            batch_size=self.context.batch_size if hasattr(self.context, 'batch_size') else 100
        )
        
        # Create all container concepts
        try:
            container_concepts = self.create_all_container_concepts()
            
            # Add concepts to collection
            for concept in container_concepts:
                result_collection.add_concept(concept)
            
            # Update progress if callback provided
            if progress_callback:
                progress_callback(100.0, f"Generated {len(container_concepts)} container concepts")
            
            processing_time = time.time() - start_time
            
            # Create transformation result
            result = TransformationResult(
                concepts=result_collection,
                success_count=len(container_concepts),
                error_count=0,
                warning_count=0,
                processing_time_seconds=processing_time
            )
            
            self.logger.info(f"Container transformation completed: {len(container_concepts)} concepts in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Container transformation failed: {e}")
            
            # Return failed result
            result = TransformationResult(
                concepts=result_collection,
                success_count=0,
                error_count=1,
                warning_count=0,
                processing_time_seconds=processing_time,
                errors=[str(e)]
            )
            return result
    
    def get_transformation_summary(self) -> Dict[str, Any]:
        """Get summary of container transformation configuration"""
        return {
            "transformer_name": self.transformer_name,
            "container_definitions_count": len(self.container_definitions),
            "owner_organization": self.owner_org,
            "container_statistics": self.container_stats
        }


# Example usage and testing
if __name__ == "__main__":
    print("Fixed Container Concepts Transformer")
    print("Creates exactly 7 static organizational container concepts")
    print("\nExpected containers:")
    print("1. LOINC_COMPONENT - LOINC Component")
    print("2. LOINC_PROPERTY - LOINC Property") 
    print("3. LOINC_TIME - LOINC Time")
    print("4. LOINC_SYSTEM - LOINC System")
    print("5. LOINC_SCALE - LOINC Scale")
    print("6. LOINC_METHOD - LOINC Method")
    print("7. OTHER - Other")
    print("\nAll containers use concept_class='Misc' and are organizational only.")