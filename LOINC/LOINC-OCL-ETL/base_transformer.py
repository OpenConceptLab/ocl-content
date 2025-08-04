"""
Base Transformer Abstract Class for LOINC to OCL Transformation - Phase 2

This module defines the abstract base class for all LOINC to OCL transformers.
Provides common functionality, validation patterns, and the transformation
interface that all specific transformers must implement.

Leverages Phase 1 infrastructure:
- ConfigManager for settings and transformation rules
- Enhanced validation patterns
- Proven batch processing architecture
- Multi-language support for 19 languages

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Iterator
from dataclasses import dataclass, field
import pandas as pd
import logging
from pathlib import Path
import time

# Import Phase 1 infrastructure
from config_manager import ConfigManager, TransformationRules
from ocl_models import OCLConcept, OCLName, ConceptCollection

@dataclass
class DatasetDiscoveryCache:
    """
    Cache for dataset discovery results to avoid repeated searches.
    """
    logical_to_actual_names: Dict[str, str] = field(default_factory=dict)
    discovery_timestamps: Dict[str, float] = field(default_factory=dict)
    cache_ttl_seconds: float = 3600  # 1 hour default
    
    def get_cached_name(self, logical_name: str) -> Optional[str]:
        """Get cached actual dataset name if still valid"""
        if logical_name not in self.logical_to_actual_names:
            return None
        
        # Check if cache entry is still valid
        timestamp = self.discovery_timestamps.get(logical_name, 0)
        if time.time() - timestamp > self.cache_ttl_seconds:
            # Cache expired, remove entries
            self.logical_to_actual_names.pop(logical_name, None)
            self.discovery_timestamps.pop(logical_name, None)
            return None
        
        return self.logical_to_actual_names[logical_name]
    
    def cache_discovery(self, logical_name: str, actual_name: str) -> None:
        """Cache a discovery result"""
        self.logical_to_actual_names[logical_name] = actual_name
        self.discovery_timestamps[logical_name] = time.time()
    
    def clear_cache(self) -> None:
        """Clear all cached discoveries"""
        self.logical_to_actual_names.clear()
        self.discovery_timestamps.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        valid_entries = sum(
            1 for timestamp in self.discovery_timestamps.values()
            if current_time - timestamp <= self.cache_ttl_seconds
        )
        
        return {
            "total_entries": len(self.logical_to_actual_names),
            "valid_entries": valid_entries,
            "expired_entries": len(self.logical_to_actual_names) - valid_entries,
            "cache_ttl_seconds": self.cache_ttl_seconds
        }


@dataclass
class TransformationContext:
    """
    Context information for transformation operations.
    
    Provides access to configuration, data sources, and processing state
    that transformers need during concept creation.
    """
    config_manager: ConfigManager
    transformation_rules: TransformationRules
    source_datasets: Dict[str, pd.DataFrame]
    language_datasets: Dict[str, pd.DataFrame]  # 19 language variants
    cross_references: Dict[str, Any]
    batch_size: int = 1000
    current_batch: int = 0
    total_batches: int = 0
    discovery_cache: DatasetDiscoveryCache = field(default_factory=DatasetDiscoveryCache)
    discovery_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformationResult:
    """
    Result of a transformation operation.
    
    Contains the generated concepts, validation results, and processing statistics.
    """
    concepts: ConceptCollection
    success_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    processing_time_seconds: float = 0.0
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    @property
    def is_successful(self) -> bool:
        """Check if transformation was successful (no critical errors)"""
        return self.error_count == 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        total = self.success_count + self.error_count
        return (self.success_count / total * 100) if total > 0 else 0.0


class BaseTransformer(ABC):
    """
    Abstract base class for all LOINC to OCL transformers.
    
    Provides common functionality and defines the interface that specific
    transformers (LOINC terms, parts, answer lists) must implement.
    
    Leverages Phase 1's proven architecture for:
    - Configuration management
    - Batch processing
    - Multi-language support  
    - Error handling and validation
    """
    
    def __init__(self, context: TransformationContext):
        """
        Initialize base transformer.
        
        Args:
            context: Transformation context with config and data access
        """
        self.context = context
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Transformer-specific configuration
        self.batch_size = context.batch_size
        self.owner_org = self._get_owner_organization()
        self.source_name = "LOINC"
        
        # Statistics tracking
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.warning_count = 0
        
        # Multi-language support (19 languages from Phase 1)
        self.supported_locales = self._get_supported_locales()
        
        self.logger.info(f"Initialized {self.__class__.__name__} transformer")
        self.logger.info(f"Batch size: {self.batch_size}")
        self.logger.info(f"Supported locales: {len(self.supported_locales)}")
    
    @abstractmethod
    def get_transformer_name(self) -> str:
        """Get the name of this transformer (e.g., 'LOINC_Terms')"""
        pass
    
    @abstractmethod
    def get_source_dataset_name(self) -> str:
        """Get the name of the primary source dataset (e.g., 'loinc_terms')"""
        pass
    
    @abstractmethod
    def get_primary_key_field(self) -> str:
        """Get the primary key field name (e.g., 'LOINC_NUM', 'PartNumber')"""
        pass
    
    @abstractmethod
    def transform_record(self, record: pd.Series) -> OCLConcept:
        """
        Transform a single record into an OCL concept.
        
        Args:
            record: Pandas Series representing a single row
            
        Returns:
            OCLConcept: Transformed concept object
            
        Raises:
            ValueError: If record cannot be transformed
        """
        pass
    
    @abstractmethod
    def get_concept_class(self, record: pd.Series) -> str:
        """
        Determine the OCL concept class for a record.
        
        Args:
            record: Source data record
            
        Returns:
            str: OCL concept class (e.g., 'Laboratory', 'Component')
        """
        pass
    
    def transform_dataset(self, progress_callback: Optional[callable] = None) -> TransformationResult:
        """
        Transform the entire dataset using batch processing.
        
        Args:
            progress_callback: Optional function to call with progress updates
            
        Returns:
            TransformationResult: Complete transformation results
        """
        import time
        start_time = time.time()
        
        self.logger.info(f"Starting {self.get_transformer_name()} transformation")
        
        # Get source dataset
        dataset_name = self.get_source_dataset_name()
        if dataset_name not in self.context.source_datasets:
            raise ValueError(f"Source dataset '{dataset_name}' not found")
        
        source_df = self.context.source_datasets[dataset_name]
        total_records = len(source_df)
        
        self.logger.info(f"Processing {total_records} records in batches of {self.batch_size}")
        
        # Initialize result collection
        result_collection = ConceptCollection(
            collection_name=f"{self.get_transformer_name()}_Concepts",
            batch_size=self.batch_size
        )
        
        # Process in batches
        total_batches = (total_records + self.batch_size - 1) // self.batch_size
        self.context.total_batches = total_batches
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_records)
            batch_df = source_df.iloc[start_idx:end_idx]
            
            self.context.current_batch = batch_num + 1
            
            self.logger.debug(f"Processing batch {batch_num + 1}/{total_batches} "
                            f"(records {start_idx + 1}-{end_idx})")
            
            # Transform batch
            batch_concepts = self._transform_batch(batch_df)
            for concept in batch_concepts:
                result_collection.add_concept(concept)
            
            # Progress callback
            if progress_callback:
                progress = (batch_num + 1) / total_batches * 100
                progress_callback(progress, batch_num + 1, total_batches)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create result summary
        result = TransformationResult(
            concepts=result_collection,
            success_count=self.success_count,
            error_count=self.error_count,
            warning_count=self.warning_count,
            processing_time_seconds=processing_time
        )
        
        self.logger.info(f"Transformation complete: {self.success_count} success, "
                        f"{self.error_count} errors, {self.warning_count} warnings")
        self.logger.info(f"Processing time: {processing_time:.2f} seconds")
        
        return result
    
    def _transform_batch(self, batch_df: pd.DataFrame) -> List[OCLConcept]:
        """Transform a batch of records"""
        concepts = []
        
        for _, record in batch_df.iterrows():
            try:
                concept = self.transform_record(record)
                
                # Add multi-language names
                self._add_multilingual_names(concept, record)
                
                # Validate concept
                if concept.is_valid():
                    concepts.append(concept)
                    self.success_count += 1
                else:
                    self.error_count += 1
                    errors = concept.get_validation_errors()
                    self.logger.error(f"Invalid concept {concept.id}: {errors}")
                
                self.processed_count += 1
                
            except Exception as e:
                self.error_count += 1
                primary_key = self._get_record_key(record)
                self.logger.error(f"Failed to transform record {primary_key}: {str(e)}")
        
        return concepts
    
    def _add_multilingual_names(self, concept: OCLConcept, record: pd.Series) -> None:
        """
        Add multi-language names to concept from the 19 language variants.
        
        Uses the language datasets loaded in Phase 1 to find translated names
        for the concept in supported locales.
        """
        primary_key = self._get_record_key(record)
        
        # Add names from language variant files
        for locale, lang_df in self.context.language_datasets.items():
            if locale == 'en':  # English is already added in primary transformation
                continue
            
            # Find matching record in language dataset
            if primary_key in lang_df.index:
                lang_record = lang_df.loc[primary_key]
                translated_name = self._extract_translated_name(lang_record, locale)
                
                if translated_name and translated_name.strip():
                    concept.add_name(
                        name=translated_name.strip(),
                        locale=locale,
                        locale_preferred=False,
                        name_type="Fully Specified"
                    )
    
    def _extract_translated_name(self, lang_record: pd.Series, locale: str) -> Optional[str]:
        """
        Extract translated name from language variant record.
        
        Different language files may have different column structures.
        This method handles the variations found in Phase 1 data.
        """
        # Common name fields in language variants
        name_fields = [
            'LONG_COMMON_NAME',
            'DisplayName', 
            'COMPONENT',
            'PartDisplayName',
            'TranslatedName'
        ]
        
        for field in name_fields:
            if field in lang_record and pd.notna(lang_record[field]):
                return str(lang_record[field])
        
        return None
    
    def _get_record_key(self, record: pd.Series) -> str:
        """Get the primary key value for a record"""
        key_field = self.get_primary_key_field()
        return str(record[key_field]) if key_field in record else "UNKNOWN"
    
    def _get_owner_organization(self) -> str:
        """Get the owner organization from configuration"""
        if hasattr(self.context.transformation_rules, 'loinc_term_mappings'):
            mappings = self.context.transformation_rules.loinc_term_mappings
            return mappings.get('owner', 'LOINC_ORG')
        return 'LOINC_ORG'
    
    def _get_supported_locales(self) -> List[str]:
        """Get list of supported locales from language datasets"""
        locales = ['en']  # English is always supported
        locales.extend(self.context.language_datasets.keys())
        return sorted(list(set(locales)))
    
    def _map_status_to_retired(self, status: str) -> bool:
        """
        Map LOINC STATUS field to OCL retired boolean.
        
        Uses the status mappings from transformation rules.
        """
        if not hasattr(self.context.transformation_rules, 'status_mappings'):
            # Default mapping if not configured
            return status.upper() in ['DEPRECATED', 'DISCOURAGED', 'TRIAL']
        
        status_mappings = self.context.transformation_rules.status_mappings
        
        # Check if status should be retired
        retired_statuses = status_mappings.get('retired', [])
        return status.upper() in [s.upper() for s in retired_statuses]
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for OCL"""
        if not text or pd.isna(text):
            return ""
        
        # Convert to string and strip whitespace
        clean_text = str(text).strip()
        
        # Remove excessive whitespace
        import re
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        return clean_text
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return {
            "transformer_name": self.get_transformer_name(),
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "success_rate": (self.success_count / max(self.processed_count, 1)) * 100,
            "supported_locales": len(self.supported_locales)
        }


# Example usage for testing
if __name__ == "__main__":
    print("BaseTransformer - Abstract class for LOINC to OCL transformation")
    print("This class provides the foundation for specific transformers:")
    print("- LOINC Terms Transformer")
    print("- LOINC Parts Transformer") 
    print("- Answer Lists Transformer")
    print("- Container Concepts Generator")
