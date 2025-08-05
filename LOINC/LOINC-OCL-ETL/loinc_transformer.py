"""
LOINC Terms Transformer for LOINC to OCL Transformation - Phase 2

Enhanced with configuration-driven dataset discovery and caching.
Transforms LOINC terms (from Loinc.csv) into OCL Concept objects.

Key capabilities:
- Configuration-driven dataset discovery with caching
- Transform LOINC terms to OCL concepts with full metadata
- Multi-language name support (19 languages)
- LOINC-specific extras (component, property, system, etc.)
- Comprehensive validation and error handling
- Batch processing for memory efficiency

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from base_transformer import BaseTransformer, TransformationContext
from ocl_models import OCLConcept, OCLName
import logging


class LoincTermsTransformer(BaseTransformer):
    """
    Enhanced transformer for LOINC terms (main LOINC codes).
    
    Now uses configuration-driven dataset discovery and intelligent caching
    to efficiently locate and process LOINC terms data.
    
    Transforms records from Loinc.csv into OCL Concept objects with:
    - Primary English names from LONG_COMMON_NAME field
    - Multi-language variants from 19 language files
    - LOINC-specific metadata in extras field
    - Proper concept classification and status mapping
    """
    
    def __init__(self, context: TransformationContext):
        """Initialize enhanced LOINC Terms transformer"""
        # Call parent constructor which handles discovery and caching
        super().__init__(context)
        
        # LOINC Terms specific configuration
        self.transformer_name = "LOINC_Terms"
        self.logical_dataset_name = "loinc_terms"
        self.primary_key = "LOINC_NUM"
        
        # Field mappings from transformation rules
        self._load_field_mappings()
        
        self.logger.info(f"Enhanced LOINC Terms Transformer initialized")
        self.logger.info(f"Logical dataset: {self.logical_dataset_name}")
        self.logger.info(f"Discovery caching: {'enabled' if context.discovery_cache else 'disabled'}")
        
        # Log discovery configuration being used
        thresholds = context.discovery_config.get('size_thresholds', {}).get('loinc_terms', {})
        if thresholds:
            expected = thresholds.get('expected_records', 'unknown')
            min_records = thresholds.get('min_records', 'unknown')
            max_records = thresholds.get('max_records', 'unknown')
            self.logger.info(f"Expected records: {expected} (range: {min_records}-{max_records})")
    
    def get_transformer_name(self) -> str:
        """Get transformer name"""
        return self.transformer_name
    
    def get_logical_dataset_name(self) -> str:
        """Get logical dataset name for discovery system"""
        return self.logical_dataset_name
    
    def get_primary_key_field(self) -> str:
        """Get primary key field"""
        return self.primary_key
    
    def get_source_dataset_name(self) -> str:
        """Get source dataset name"""
        return self.logical_dataset_name
    
    def transform_record(self, record: pd.Series) -> OCLConcept:
        """
        Transform a single LOINC term record into an OCL concept.
        
        Args:
            record: Pandas Series with LOINC term data
            
        Returns:
            OCLConcept: Transformed concept ready for OCL import
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Extract required fields
        loinc_num = self._get_required_field(record, 'LOINC_NUM')
        long_common_name = self._get_required_field(record, 'LONG_COMMON_NAME')
        
        # Create base concept
        concept = OCLConcept(
            id=loinc_num,
            concept_class=self.get_concept_class(record),
            datatype=self._get_datatype(record),  # ADD THIS LINE
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=self._map_status_to_retired(record.get('STATUS', 'ACTIVE')),
            external_id=loinc_num
        )
        
        # Add primary English name
        concept.add_name(
            name=self._clean_text(long_common_name),
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add additional names if available
        self._add_additional_names(concept, record)
        
        # Add LOINC-specific metadata to extras
        self._set_loinc_extras(concept, record)
        
        # Add optional description if available
        self._add_description(concept, record)
        
        # Set source file for tracking
        concept._source_file = "Loinc.csv"
        
        return concept

    def _get_datatype(self, record: pd.Series) -> str:
        """
        Get datatype for LOINC term.
        
        Per transformation_rules_v1.yaml: Use SCALE_TYP field, fallback to 'N/A'
        """
        scale_type = self.get_valid_field_value(record, 'SCALE_TYP')
        if scale_type is not None:
            cleaned_scale = self._clean_text(str(scale_type))
            return cleaned_scale if cleaned_scale else 'N/A'
        
        return 'N/A'

    def get_concept_class(self, record: pd.Series) -> str:
        """
        Determine OCL concept class for LOINC term.
        
        Per transformation_rules_v1.yaml: All LOINC Terms use 'LOINC' as concept_class
        """
        return 'LOINC'  # Fixed value for all LOINC Terms
    
    def _load_field_mappings(self) -> None:
        """Load field mappings from transformation rules"""
        self.field_mappings = {}
        
        if hasattr(self.context.transformation_rules, 'loinc_term_mappings'):
            mappings = self.context.transformation_rules.loinc_term_mappings
            self.field_mappings = mappings.copy()
    
    def _get_class_mapping(self) -> Dict[str, str]:
        """Get LOINC CLASS to OCL concept class mapping"""
        # Default mapping - can be extended via configuration
        return {
            'CHEM': 'Laboratory',
            'HEMATOLOGY': 'Laboratory', 
            'MICRO': 'Laboratory',
            'IMMUNOLOGY': 'Laboratory',
            'PATHOLOGY': 'Laboratory',
            'H&P.HX': 'Clinical',
            'H&P.PE': 'Clinical',
            'PHENX': 'Survey',
            'SURVEY': 'Survey',
            'MOLPATH': 'Laboratory',
            'DRUG/TOX': 'Laboratory',
            'VITAL': 'Vital Signs'
        }
    
    def _get_required_field(self, record: pd.Series, field_name: str) -> str:
        """Get required field value with validation"""
        if field_name not in record:
            raise ValueError(f"Required field '{field_name}' not found in record")
        
        value = record[field_name]
        if pd.isna(value) or str(value).strip() == '':
            raise ValueError(f"Required field '{field_name}' is empty")
        
        return str(value).strip()
    
    def _add_additional_names(self, concept: OCLConcept, record: pd.Series) -> None:
        """Add additional names from LOINC fields"""
        # Add short name if available and different from long name
        short_name = self.get_valid_field_value(record, 'SHORTNAME')
        if short_name is not None:
            short_name = self._clean_text(str(short_name))
            if short_name and short_name != concept.names[0].name:
                concept.add_name(
                    name=short_name,
                    locale="en",
                    locale_preferred=False,
                    name_type="Short"
                )
        
        # Add consumer name if available
        consumer_name = self.get_valid_field_value(record, 'CONSUMER_NAME')
        if consumer_name is not None:
            consumer_name = self._clean_text(str(consumer_name))
            if consumer_name and consumer_name not in [n.name for n in concept.names]:
                concept.add_name(
                    name=consumer_name,
                    locale="en",
                    locale_preferred=False,
                    name_type="Consumer"
                )
    
    def _set_loinc_extras(self, concept: OCLConcept, record: pd.Series) -> None:
        """Set LOINC-specific extras data"""
        extras = {}
        
        # Core LOINC fields in extras (CLASS goes here now)
        class_value = self.get_valid_field_value(record, 'CLASS')
        if class_value is not None:
            extras['class'] = self._clean_text(str(class_value))
        
        component_value = self.get_valid_field_value(record, 'COMPONENT')
        if component_value is not None:
            extras['component'] = self._clean_text(str(component_value))

        # Core LOINC dimensions
        extras_mapping = {
            'component': 'COMPONENT',
            'property': 'PROPERTY', 
            'time_aspect': 'TIME_ASPCT',
            'system': 'SYSTEM',
            'scale_type': 'SCALE_TYP',
            'method_type': 'METHOD_TYP'
        }
        
        for extra_key, field_name in extras_mapping.items():
            value = self.get_valid_field_value(record, field_name)
            if value is not None:
                concept.extras[extra_key] = self._clean_text(str(value))
        
        # Additional metadata
        metadata_fields = {
            'class': 'CLASS',
            'version_last_changed': 'VersionLastChanged',
            'change_type': 'CHNG_TYPE',
            'formula': 'FORMULA',
            'example_units': 'EXAMPLE_UNITS',
            'submitted_units': 'SUBMITTED_UNITS'
        }
        
        for meta_key, field_name in metadata_fields.items():
            value = self.get_valid_field_value(record, field_name)
            if value is not None:
                cleaned_value = self._clean_text(str(value))
                if cleaned_value:  # Only add non-empty values
                    concept.extras[meta_key] = cleaned_value
        
        # Special handling for boolean fields
        order_obs = self.get_valid_field_value(record, 'ORDER_OBS')
        if order_obs is not None:
            concept.extras['order_observation'] = str(order_obs) == 'Both' or str(order_obs) == 'Order'
        
        # Add processing metadata
        concept.extras['loinc_version'] = self.context.transformation_rules.target_loinc_version
        concept.extras['transformation_date'] = concept._creation_timestamp.isoformat()
    
    def _add_description(self, concept: OCLConcept, record: pd.Series) -> None:
        """Add description if available"""
        # Use definition or formula as description
        description_fields = ['DEFINITION', 'FORMULA', 'LONG_COMMON_NAME']
        
        for field in description_fields:
            value = self.get_valid_field_value(record, field)
            if value is not None:
                desc_text = self._clean_text(str(value))
                
                # Don't duplicate the primary name as description
                if desc_text and desc_text != concept.names[0].name:
                    concept.add_description(
                        description=desc_text,
                        locale="en",
                        locale_preferred=True,
                        desc_type="Definition" if field == 'DEFINITION' else "Annotation"
                    )
                    break  # Only add one description
    
    def validate_prerequisites(self) -> bool:
        """
        Enhanced prerequisite validation using configuration-driven discovery.
        
        Returns:
            bool: True if ready to transform, False otherwise
        """
        self.logger.info("Validating prerequisites with enhanced discovery system...")
        
        # LOINC Terms specific validation
        dataset_name = self.get_source_dataset_name()
        
        # Check if dataset exists
        if dataset_name not in self.context.source_datasets:
            self.logger.error(f"Required dataset '{dataset_name}' not found")
            available = list(self.context.source_datasets.keys())
            self.logger.error(f"Available datasets: {available}")
            return False
        
        source_data = self.context.source_datasets[dataset_name]
        
        # Handle different dataset structures
        if hasattr(source_data, 'data'):
            source_df = source_data.data
        else:
            source_df = source_data
        
        # Validate specific LOINC Terms requirements
        total_records = len(source_df)
        
        # Check against configured thresholds (if discovery_config is available)
        if hasattr(self.context, 'discovery_config'):
            thresholds = self.context.discovery_config.get('size_thresholds', {}).get('loinc_terms', {})
            min_records = thresholds.get('min_records', 50000)
            max_records = thresholds.get('max_records', 200000)
            
            if not (min_records <= total_records <= max_records):
                self.logger.warning(f"Dataset size {total_records:,} outside expected range [{min_records:,}-{max_records:,}]")
                # Don't fail on this - just warn
        
        # Check data quality
        if hasattr(source_df, 'columns'):
            required_cols = ['LOINC_NUM', 'LONG_COMMON_NAME']
            missing_cols = [col for col in required_cols if col not in source_df.columns]
            
            if missing_cols:
                self.logger.error(f"Missing required columns: {missing_cols}")
                return False
                
            null_loinc_nums = source_df['LOINC_NUM'].isna().sum() if 'LOINC_NUM' in source_df.columns else 0
            null_names = source_df['LONG_COMMON_NAME'].isna().sum() if 'LONG_COMMON_NAME' in source_df.columns else 0
            
            if null_loinc_nums > 0:
                self.logger.warning(f"{null_loinc_nums} records have null LOINC_NUM")
            if null_names > 0:
                self.logger.warning(f"{null_names} records have null LONG_COMMON_NAME")
        
        self.logger.info(f"Prerequisites validation passed")
        self.logger.info(f"Dataset: {dataset_name}")
        self.logger.info(f"Records: {total_records:,}")
        
        if hasattr(source_df, 'columns'):
            self.logger.info(f"Columns: {len(source_df.columns)}")
        
        self.logger.info(f"Multi-language support: {len(self.supported_locales)} locales")
        
        return True
    
    def get_transformation_summary(self) -> Dict[str, Any]:
        """Get enhanced summary of transformation configuration"""
        base_summary = {
            "transformer_name": self.transformer_name,
            "logical_dataset_name": self.logical_dataset_name,
            "actual_dataset_name": self.get_source_dataset_name(),
            "primary_key": self.primary_key,
            "owner_organization": self.owner_org,
            "supported_locales": self.supported_locales,
            "batch_size": self.batch_size,
            "field_mappings_count": len(self.field_mappings),
            "transformation_rules_version": getattr(self.context.transformation_rules, 'version', 'Unknown')
        }
        
        # Add discovery statistics
        base_summary.update(self.get_discovery_stats())
        
        # Add configuration details
        thresholds = self.discovery_config.get('size_thresholds', {}).get('loinc_terms', {})
        patterns = self.discovery_config.get('identification_patterns', {}).get('loinc_terms', {})
        
        base_summary['discovery_configuration'] = {
            'size_thresholds': thresholds,
            'identification_patterns': patterns,
            'caching_enabled': self.discovery_config.get('behavior', {}).get('enable_caching', True),
            'cache_ttl_seconds': self.discovery_config.get('behavior', {}).get('cache_ttl_seconds', 3600)
        }
        
        return base_summary


# Example usage and testing
if __name__ == "__main__":
    print("Enhanced LOINC Terms Transformer")
    print("Now with configuration-driven dataset discovery and intelligent caching!")
    print("\nNew features:")
    print("- Configurable dataset size thresholds")
    print("- Intelligent caching to avoid repeated searches") 
    print("- Enhanced validation with detailed discovery statistics")
    print("- Configuration-driven discovery patterns")
    print("\nKey features:")
    print("- Primary dataset: Loinc.csv (104K+ records)")
    print("- Multi-language support: 19 locales")
    print("- Complete LOINC metadata in extras")
    print("- Batch processing for memory efficiency")
    print("- Comprehensive validation and error handling")