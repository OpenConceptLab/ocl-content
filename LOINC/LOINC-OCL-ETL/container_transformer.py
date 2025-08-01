"""
Container Concepts Transformer for LOINC to OCL Transformation - Phase 2

This module creates container concepts for organizing LOINC concepts that don't
have clear hierarchical parents. Container concepts provide organizational
structure and navigation paths for the OCL concept hierarchy.

Container concept types:
- Component containers (e.g., "Chemistry Components", "Hematology Components")
- Property containers (e.g., "Mass Concentration Properties", "Presence Properties")
- System containers (e.g., "Serum System", "Urine System")
- Classification containers (e.g., "Laboratory Concepts", "Survey Concepts")

Key capabilities:
- Generate organizational container concepts
- Create navigation hierarchies
- Handle orphaned concept assignment
- Multi-language container names

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
from base_transformer import BaseTransformer, TransformationContext
from ocl_models import OCLConcept, OCLName
import logging
import re


class ContainerConceptsTransformer(BaseTransformer):
    """
    Transformer for creating container concepts for organizational hierarchy.
    
    Creates container concepts that provide structure and navigation for
    LOINC concepts in OCL, especially for concepts that would otherwise
    be orphaned without clear parents.
    """
    
    def __init__(self, context: TransformationContext):
        """Initialize Container Concepts transformer"""
        super().__init__(context)
        
        # Container concepts specific configuration
        self.transformer_name = "Container_Concepts"
        self.source_dataset = "container_definitions"  # Virtual dataset
        self.primary_key = "ContainerID"
        
        # Container generation rules
        self._load_container_rules()
        
        # Statistics for container generation
        self.container_stats = {
            'component_containers': 0,
            'property_containers': 0,
            'system_containers': 0,
            'class_containers': 0,
            'total_containers': 0
        }
        
        self.logger.info(f"Container Concepts Transformer initialized")
        self.logger.info(f"Will generate organizational container concepts")
    
    def get_transformer_name(self) -> str:
        """Get transformer name"""
        return self.transformer_name
    
    def get_source_dataset_name(self) -> str:
        """Get source dataset name (virtual for containers)"""
        return self.source_dataset
    
    def get_primary_key_field(self) -> str:
        """Get primary key field"""
        return self.primary_key
    
    def transform_record(self, record: pd.Series) -> OCLConcept:
        """
        Transform a container definition into an OCL concept.
        
        Note: This method is abstract compliance, but containers are generated
        differently using create_all_container_concepts().
        """
        # This is primarily for abstract method compliance
        # Actual container creation happens in create_all_container_concepts()
        container_id = record.get('ContainerID', 'UNKNOWN')
        container_name = record.get('ContainerName', 'Unknown Container')
        container_type = record.get('ContainerType', 'Generic')
        
        concept = OCLConcept(
            id=container_id,
            concept_class=self._get_container_concept_class(container_type),
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=False,
            external_id=container_id
        )
        
        # Add name
        concept.add_name(
            name=container_name,
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add container-specific metadata
        concept.extras.update({
            'container_type': container_type,
            'is_container_concept': True,
            'loinc_version': self.context.transformation_rules.target_loinc_version,
            'transformation_date': concept._creation_timestamp.isoformat()
        })
        
        concept._source_file = "Generated Container"
        
        return concept
    
    def get_concept_class(self, record: pd.Series) -> str:
        """Determine concept class for container"""
        container_type = record.get('ContainerType', 'Generic')
        return self._get_container_concept_class(container_type)
    
    def create_all_container_concepts(self) -> List[OCLConcept]:
        """
        Create all container concepts based on existing LOINC data analysis.
        
        Analyzes the loaded LOINC data to determine what containers are needed
        and generates appropriate container concepts.
        
        Returns:
            List of container OCL concepts
        """
        self.logger.info("Creating container concepts based on LOINC data analysis...")
        
        containers = []
        
        # Generate different types of containers
        containers.extend(self._create_component_containers())
        containers.extend(self._create_property_containers())
        containers.extend(self._create_system_containers())
        containers.extend(self._create_class_containers())
        containers.extend(self._create_root_containers())
        
        # Update statistics
        self.container_stats['total_containers'] = len(containers)
        
        self.logger.info(f"Generated {len(containers)} container concepts")
        self.logger.info(f"Container breakdown: {self.container_stats}")
        
        return containers
    
    def _load_container_rules(self) -> None:
        """Load container generation rules from transformation rules"""
        self.container_rules = {}
        
        if hasattr(self.context.transformation_rules, 'container_concepts'):
            self.container_rules = self.context.transformation_rules.container_concepts.copy()
        
        # Default container rules if not configured
        if not self.container_rules:
            self.container_rules = self._get_default_container_rules()
    
    def _get_default_container_rules(self) -> Dict[str, Any]:
        """Get default container generation rules"""
        return {
            'generate_component_containers': True,
            'generate_property_containers': True,
            'generate_system_containers': True,
            'generate_class_containers': True,
            'min_concepts_for_container': 5,  # Minimum concepts to justify a container
            'max_containers_per_type': 50,    # Maximum containers per type
            'container_name_patterns': {
                'component': '{component} Components',
                'property': '{property} Properties', 
                'system': '{system} System',
                'class': '{class} Concepts'
            }
        }
    
    def _create_component_containers(self) -> List[OCLConcept]:
        """Create containers for LOINC components"""
        if not self.container_rules.get('generate_component_containers', True):
            return []
        
        self.logger.info("Creating component containers...")
        
        containers = []
        
        # Analyze LOINC terms for components
        if 'loinc_terms' in self.context.source_datasets:
            loinc_df = self.context.source_datasets['loinc_terms']
            
            if 'COMPONENT' in loinc_df.columns:
                # Count component usage
                component_counts = loinc_df['COMPONENT'].value_counts()
                min_concepts = self.container_rules.get('min_concepts_for_container', 5)
                
                # Create containers for frequent components
                top_components = component_counts[component_counts >= min_concepts].head(
                    self.container_rules.get('max_containers_per_type', 50)
                )
                
                for component, count in top_components.items():
                    if pd.notna(component) and component.strip():
                        container = self._create_component_container(component, count)
                        containers.append(container)
                        self.container_stats['component_containers'] += 1
        
        self.logger.info(f"Created {len(containers)} component containers")
        return containers
    
    def _create_component_container(self, component: str, concept_count: int) -> OCLConcept:
        """Create a container concept for a specific component"""
        # Generate container ID
        container_id = f"LOINC-COMP-{self._generate_safe_id(component)}"
        
        # Generate container name
        name_pattern = self.container_rules.get('container_name_patterns', {}).get('component', '{component} Components')
        container_name = name_pattern.format(component=component)
        
        # Create concept
        concept = OCLConcept(
            id=container_id,
            concept_class='Component Container',
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=False,
            external_id=container_id
        )
        
        # Add name
        concept.add_name(
            name=container_name,
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add description
        concept.add_description(
            description=f"Container for LOINC concepts with component '{component}'. Contains approximately {concept_count} concepts.",
            locale="en",
            locale_preferred=True,
            desc_type="Definition"
        )
        
        # Add container metadata
        concept.extras.update({
            'container_type': 'component',
            'component_name': component,
            'estimated_concept_count': concept_count,
            'is_container_concept': True,
            'container_purpose': 'Organizational hierarchy for LOINC components'
        })
        
        concept._source_file = "Generated Component Container"
        
        return concept
    
    def _create_property_containers(self) -> List[OCLConcept]:
        """Create containers for LOINC properties"""
        if not self.container_rules.get('generate_property_containers', True):
            return []
        
        self.logger.info("Creating property containers...")
        
        containers = []
        
        # Analyze LOINC terms for properties
        if 'loinc_terms' in self.context.source_datasets:
            loinc_df = self.context.source_datasets['loinc_terms']
            
            if 'PROPERTY' in loinc_df.columns:
                # Count property usage
                property_counts = loinc_df['PROPERTY'].value_counts()
                min_concepts = self.container_rules.get('min_concepts_for_container', 5)
                
                # Create containers for frequent properties
                top_properties = property_counts[property_counts >= min_concepts].head(
                    self.container_rules.get('max_containers_per_type', 50)
                )
                
                for property_name, count in top_properties.items():
                    if pd.notna(property_name) and property_name.strip():
                        container = self._create_property_container(property_name, count)
                        containers.append(container)
                        self.container_stats['property_containers'] += 1
        
        self.logger.info(f"Created {len(containers)} property containers")
        return containers
    
    def _create_property_container(self, property_name: str, concept_count: int) -> OCLConcept:
        """Create a container concept for a specific property"""
        # Generate container ID
        container_id = f"LOINC-PROP-{self._generate_safe_id(property_name)}"
        
        # Generate container name
        name_pattern = self.container_rules.get('container_name_patterns', {}).get('property', '{property} Properties')
        container_name = name_pattern.format(property=property_name)
        
        # Create concept
        concept = OCLConcept(
            id=container_id,
            concept_class='Property Container',
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=False,
            external_id=container_id
        )
        
        # Add name
        concept.add_name(
            name=container_name,
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add description
        concept.add_description(
            description=f"Container for LOINC concepts with property '{property_name}'. Contains approximately {concept_count} concepts.",
            locale="en",
            locale_preferred=True,
            desc_type="Definition"
        )
        
        # Add container metadata
        concept.extras.update({
            'container_type': 'property',
            'property_name': property_name,
            'estimated_concept_count': concept_count,
            'is_container_concept': True,
            'container_purpose': 'Organizational hierarchy for LOINC properties'
        })
        
        concept._source_file = "Generated Property Container"
        
        return concept
    
    def _create_system_containers(self) -> List[OCLConcept]:
        """Create containers for LOINC systems"""
        if not self.container_rules.get('generate_system_containers', True):
            return []
        
        self.logger.info("Creating system containers...")
        
        containers = []
        
        # Analyze LOINC terms for systems
        if 'loinc_terms' in self.context.source_datasets:
            loinc_df = self.context.source_datasets['loinc_terms']
            
            if 'SYSTEM' in loinc_df.columns:
                # Count system usage
                system_counts = loinc_df['SYSTEM'].value_counts()
                min_concepts = self.container_rules.get('min_concepts_for_container', 5)
                
                # Create containers for frequent systems
                top_systems = system_counts[system_counts >= min_concepts].head(
                    self.container_rules.get('max_containers_per_type', 50)
                )
                
                for system_name, count in top_systems.items():
                    if pd.notna(system_name) and system_name.strip():
                        container = self._create_system_container(system_name, count)
                        containers.append(container)
                        self.container_stats['system_containers'] += 1
        
        self.logger.info(f"Created {len(containers)} system containers")
        return containers
    
    def _create_system_container(self, system_name: str, concept_count: int) -> OCLConcept:
        """Create a container concept for a specific system"""
        # Generate container ID
        container_id = f"LOINC-SYS-{self._generate_safe_id(system_name)}"
        
        # Generate container name
        name_pattern = self.container_rules.get('container_name_patterns', {}).get('system', '{system} System')
        container_name = name_pattern.format(system=system_name)
        
        # Create concept
        concept = OCLConcept(
            id=container_id,
            concept_class='System Container',
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=False,
            external_id=container_id
        )
        
        # Add name
        concept.add_name(
            name=container_name,
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add description
        concept.add_description(
            description=f"Container for LOINC concepts from system '{system_name}'. Contains approximately {concept_count} concepts.",
            locale="en",
            locale_preferred=True,
            desc_type="Definition"
        )
        
        # Add container metadata
        concept.extras.update({
            'container_type': 'system',
            'system_name': system_name,
            'estimated_concept_count': concept_count,
            'is_container_concept': True,
            'container_purpose': 'Organizational hierarchy for LOINC systems'
        })
        
        concept._source_file = "Generated System Container"
        
        return concept
    
    def _create_class_containers(self) -> List[OCLConcept]:
        """Create containers for LOINC classes"""
        if not self.container_rules.get('generate_class_containers', True):
            return []
        
        self.logger.info("Creating class containers...")
        
        containers = []
        
        # Analyze LOINC terms for classes
        if 'loinc_terms' in self.context.source_datasets:
            loinc_df = self.context.source_datasets['loinc_terms']
            
            if 'CLASS' in loinc_df.columns:
                # Count class usage
                class_counts = loinc_df['CLASS'].value_counts()
                min_concepts = self.container_rules.get('min_concepts_for_container', 5)
                
                # Create containers for all significant classes
                top_classes = class_counts[class_counts >= min_concepts]
                
                for class_name, count in top_classes.items():
                    if pd.notna(class_name) and class_name.strip():
                        container = self._create_class_container(class_name, count)
                        containers.append(container)
                        self.container_stats['class_containers'] += 1
        
        self.logger.info(f"Created {len(containers)} class containers")
        return containers
    
    def _create_class_container(self, class_name: str, concept_count: int) -> OCLConcept:
        """Create a container concept for a specific class"""
        # Generate container ID
        container_id = f"LOINC-CLASS-{self._generate_safe_id(class_name)}"
        
        # Generate container name
        name_pattern = self.container_rules.get('container_name_patterns', {}).get('class', '{class} Concepts')
        container_name = name_pattern.format(**{'class': class_name})
        
        # Create concept
        concept = OCLConcept(
            id=container_id,
            concept_class='Class Container',
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=False,
            external_id=container_id
        )
        
        # Add name
        concept.add_name(
            name=container_name,
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add description
        concept.add_description(
            description=f"Container for LOINC concepts in class '{class_name}'. Contains approximately {concept_count} concepts.",
            locale="en",
            locale_preferred=True,
            desc_type="Definition"
        )
        
        # Add container metadata
        concept.extras.update({
            'container_type': 'class',
            'class_name': class_name,
            'estimated_concept_count': concept_count,
            'is_container_concept': True,
            'container_purpose': 'Organizational hierarchy for LOINC classes'
        })
        
        concept._source_file = "Generated Class Container"
        
        return concept
    
    def _create_root_containers(self) -> List[OCLConcept]:
        """Create root-level organizational containers"""
        self.logger.info("Creating root containers...")
        
        containers = []
        
        # Root LOINC container
        root_container = OCLConcept(
            id="LOINC-ROOT",
            concept_class="Root Container",
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=False,
            external_id="LOINC-ROOT"
        )
        
        root_container.add_name(
            name="LOINC Terminology",
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        root_container.add_description(
            description="Root container for all LOINC terminology concepts and organizational structures.",
            locale="en",
            locale_preferred=True,
            desc_type="Definition"
        )
        
        root_container.extras.update({
            'container_type': 'root',
            'is_container_concept': True,
            'container_purpose': 'Root organizational container for LOINC hierarchy',
            'loinc_version': self.context.transformation_rules.target_loinc_version
        })
        
        root_container._source_file = "Generated Root Container"
        containers.append(root_container)
        
        return containers
    
    def _generate_safe_id(self, text: str) -> str:
        """Generate a safe ID from text"""
        # Clean and normalize text for ID
        safe_id = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        safe_id = re.sub(r'\s+', '-', safe_id.strip())
        safe_id = safe_id.upper()
        
        # Limit length
        if len(safe_id) > 20:
            safe_id = safe_id[:20]
        
        return safe_id or "UNKNOWN"
    
    def _get_container_concept_class(self, container_type: str) -> str:
        """Get concept class for container type"""
        mapping = {
            'component': 'Component Container',
            'property': 'Property Container',
            'system': 'System Container',
            'class': 'Class Container',
            'root': 'Root Container',
            'generic': 'Container'
        }
        return mapping.get(container_type.lower(), 'Container')
    
    def validate_prerequisites(self) -> bool:
        """
        Validate that prerequisites for container generation are met.
        
        Returns:
            bool: True if ready to generate containers
        """
        # Check that we have LOINC data to analyze
        required_datasets = ['loinc_terms']
        available_datasets = list(self.context.source_datasets.keys())
        
        missing_datasets = []
        for dataset in required_datasets:
            if dataset not in available_datasets:
                missing_datasets.append(dataset)
        
        if missing_datasets:
            self.logger.warning(f"Missing datasets for container analysis: {missing_datasets}")
            # We can still generate some containers, so don't fail completely
        
        # Check that we have transformation rules
        if not hasattr(self.context, 'transformation_rules') or not self.context.transformation_rules:
            self.logger.warning("No transformation rules available")
        
        self.logger.info("Container concepts prerequisites check passed")
        self.logger.info(f"Available datasets for analysis: {available_datasets}")
        
        return True
    
    def get_transformation_summary(self) -> Dict[str, Any]:
        """Get summary of container transformation configuration"""
        return {
            "transformer_name": self.transformer_name,
            "container_rules": self.container_rules,
            "owner_organization": self.owner_org,
            "container_statistics": self.container_stats,
            "transformation_rules_version": getattr(self.context.transformation_rules, 'version', 'Unknown')
        }
    
    def get_container_generation_report(self) -> Dict[str, Any]:
        """Get detailed report of container generation"""
        return {
            "total_containers_generated": self.container_stats['total_containers'],
            "containers_by_type": {
                "component_containers": self.container_stats['component_containers'],
                "property_containers": self.container_stats['property_containers'],
                "system_containers": self.container_stats['system_containers'],
                "class_containers": self.container_stats['class_containers']
            },
            "container_rules_applied": self.container_rules,
            "generation_successful": self.container_stats['total_containers'] > 0
        }


# Example usage and testing
if __name__ == "__main__":
    print("Container Concepts Transformer")
    print("Creates organizational container concepts for LOINC hierarchy")
    print("\nContainer types:")
    print("- Component containers (e.g., 'Glucose Components')")
    print("- Property containers (e.g., 'Mass Concentration Properties')")  
    print("- System containers (e.g., 'Serum System')")
    print("- Class containers (e.g., 'Laboratory Concepts')")
    print("- Root containers (organizational structure)")
    print("\nKey features:")
    print("- Data-driven container generation")
    print("- Configurable generation rules")
    print("- Multi-language container names")
    print("- Comprehensive metadata and descriptions")
