"""
Base Mapping Transformer for LOINC to OCL Transformation - Phase 3

Abstract base class providing common functionality for all LOINC mapping transformers.
Handles data loading, concept URL resolution, batch processing, and error handling.

Features:
- Integration with Phase 1 DataLoader
- Phase 2 concept URL cache loading
- Batch processing with memory management
- Comprehensive error handling and logging
- Progress tracking and statistics
- Consistent validation patterns

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import sys
import json
import logging
import time
import pandas as pd
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from phase1_2_data_processing.config_manager import ConfigManager
from phase1_2_data_processing.data_loader import DataLoader
from phase3_mapping_creation.phase3_ocl_models import OCLMapping, TransformationResult


class BaseMappingTransformer(ABC):
    """
    Abstract base class for LOINC to OCL mapping transformers.
    
    Provides common infrastructure for:
    - Data loading from Phase 1
    - Concept URL resolution from Phase 2
    - Batch processing with progress tracking
    - Error handling and statistics
    - Validation and quality assurance
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize base transformer with configuration.
        
        Args:
            config_manager: Optional configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Data storage
        self.concept_url_cache: Dict[str, str] = {}
        self.source_data: Optional[pd.DataFrame] = None
        self.data_loader: Optional[DataLoader] = None
        
        # Processing configuration
        self.batch_size = 1000
        self.max_memory_gb = 4
        
        # Statistics tracking
        self.stats = {
            'records_processed': 0,
            'mappings_created': 0,
            'errors': 0,
            'warnings': 0,
            'url_resolution_failures': 0,
            'from_concept_missing': 0,
            'to_concept_missing': 0,
            'processing_time': 0.0
        }
    
    # Abstract methods that must be implemented by subclasses
    
    @abstractmethod
    def get_transformer_name(self) -> str:
        """Return the name of this transformer"""
        pass
    
    @abstractmethod
    def get_source_file(self) -> str:
        """Return the source CSV file containing the mapping data"""
        pass
    
    @abstractmethod
    def get_mapping_type(self) -> str:
        """Return the human-readable mapping type"""
        pass
    
    @abstractmethod
    def get_ocl_map_type(self) -> str:
        """Return the OCL map_type value for this mapping type"""
        pass
    
    @abstractmethod
    def transform_record(self, record: pd.Series) -> Optional['OCLMapping']:
        """
        Transform a single source record into an OCL mapping.
        
        Args:
            record: Pandas Series containing source data
            
        Returns:
            OCLMapping object or None if record should be skipped
        """
        pass
    
    # Common infrastructure methods
    
    def load_concept_url_cache(self) -> bool:
        """Load concept URLs from Phase 2 output for mapping references"""
        try:
            self.logger.info("Loading concept URL cache from Phase 2 output...")
            
            # Find concept files in both possible locations
            concept_files = []
            for search_dir in ["output", "output/phase2_concepts"]:
                search_path = Path(search_dir)
                if search_path.exists():
                    concept_files.extend(list(search_path.glob("loinc_concepts_*.jsonl")))
            
            if not concept_files:
                self.logger.error("No Phase 2 concept files found")
                return False
            
            self.logger.info(f"Found {len(concept_files)} concept files to process")
            
            url_cache = {}
            total_concepts_loaded = 0
            
            for concept_file in concept_files:
                self.logger.info(f"Loading concepts from {concept_file.name}")
                
                file_concepts = 0
                with open(concept_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            if line.strip():
                                concept = json.loads(line.strip())
                                if 'id' in concept and 'owner' in concept and 'source' in concept:
                                    concept_url = f"/orgs/{concept['owner']}/sources/{concept['source']}/concepts/{concept['id']}/"
                                    url_cache[concept['id']] = concept_url
                                    file_concepts += 1
                        except json.JSONDecodeError as e:
                            if line_num <= 5:  # Only log first few errors per file
                                self.logger.warning(f"Invalid JSON in {concept_file.name} line {line_num}: {e}")
                
                total_concepts_loaded += file_concepts
                self.logger.info(f"  Loaded {file_concepts} concepts from {concept_file.name}")
            
            self.concept_url_cache = url_cache
            self.logger.info(f"Successfully loaded {total_concepts_loaded} concept URLs into cache")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load concept URL cache: {str(e)}")
            return False
    
    def get_concept_url(self, concept_id: str) -> Optional[str]:
        """
        Get OCL concept URL for a LOINC concept ID.
        
        Args:
            concept_id: LOINC concept identifier
            
        Returns:
            OCL concept URL or None if not found
        """
        return self.concept_url_cache.get(concept_id)
    
    def load_source_data(self) -> bool:
        """Load and validate source mapping data from Phase 1"""
        try:
            source_file = self.get_source_file()
            self.logger.info(f"Loading source data from {source_file}")
            
            # Use Phase 1 data loader to get validated data
            self.data_loader = DataLoader()
            
            if not hasattr(self.data_loader, 'datasets') or not self.data_loader.datasets:
                self.logger.info("Loading Phase 1 data...")
                self.data_loader.load_all_data()
            
            if source_file not in self.data_loader.datasets:
                raise ValueError(f"Source file {source_file} not found in Phase 1 data")
                
            dataset = self.data_loader.datasets[source_file]
            self.source_data = dataset.data
            
            self.logger.info(f"Loaded {len(self.source_data)} records from {source_file}")
            self.logger.info(f"Source data columns: {list(self.source_data.columns)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load source data: {str(e)}")
            return False
    
    def validate_record(self, record: pd.Series) -> Tuple[bool, List[str]]:
        """
        Validate a source record before transformation.
        Can be overridden by subclasses for specific validation.
        
        Args:
            record: Source record to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Basic validation - subclasses should override for specific checks
        if record.isna().all():
            errors.append("Record is completely empty")
            
        return len(errors) == 0, errors
    
    def process_batch(self, batch_data: pd.DataFrame, 
                     progress_callback: Optional[Callable[[float, str], None]] = None) -> Tuple[List['OCLMapping'], List[str]]:
        """
        Process a batch of source records into OCL mappings.
        
        Args:
            batch_data: Batch of source records
            progress_callback: Optional progress reporting function
            
        Returns:
            Tuple of (mappings_list, errors_list)
        """
        from phase3_mapping_creation.phase3_ocl_models import OCLMapping  # Import here to avoid circular imports
        
        mappings = []
        errors = []
        
        for idx, record in batch_data.iterrows():
            try:
                # Validate record
                is_valid, validation_errors = self.validate_record(record)
                if not is_valid:
                    for error in validation_errors:
                        errors.append(f"Record {idx}: {error}")
                    self.stats['errors'] += 1
                    continue
                
                # Transform record
                mapping = self.transform_record(record)
                if mapping:
                    # Validate mapping
                    is_mapping_valid, mapping_errors = mapping.validate()
                    if is_mapping_valid:
                        mappings.append(mapping)
                        self.stats['mappings_created'] += 1
                    else:
                        for error in mapping_errors:
                            errors.append(f"Mapping from record {idx}: {error}")
                        self.stats['errors'] += 1
                
                self.stats['records_processed'] += 1
                
                # Report progress if callback provided
                if progress_callback and self.stats['records_processed'] % 100 == 0:
                    progress = (self.stats['records_processed'] / len(self.source_data)) * 100
                    progress_callback(progress, f"Processed {self.stats['records_processed']} records")
                
            except Exception as e:
                error_msg = f"Error processing record {idx}: {str(e)}"
                errors.append(error_msg)
                self.stats['errors'] += 1
        
        return mappings, errors
    
    def run_transformation(self, limit: Optional[int] = None, 
                          progress_callback: Optional[Callable[[float, str], None]] = None) -> 'TransformationResult':
        """
        Run the complete mapping transformation process.
        
        Args:
            limit: Optional limit on number of records to process (for testing)
            progress_callback: Optional progress reporting function
            
        Returns:
            TransformationResult with mappings and metadata
        """
        from phase3_mapping_creation.phase3_ocl_models import TransformationResult  # Import here to avoid circular imports
        
        start_time = time.time()
        self.logger.info(f"Starting {self.get_transformer_name()} transformation...")
        
        try:
            # Load concept URL cache
            if not self.load_concept_url_cache():
                raise RuntimeError("Failed to load concept URL cache")
            
            # Load source data
            if not self.load_source_data():
                raise RuntimeError("Failed to load source data")
            
            # Prepare data for processing
            data_to_process = self.source_data
            if limit:
                data_to_process = self.source_data.head(limit)
                self.logger.info(f"Processing limited dataset: {limit} records")
            
            total_records = len(data_to_process)
            self.logger.info(f"Processing {total_records} records in batches of {self.batch_size}")
            
            # Process in batches
            all_mappings = []
            all_errors = []
            
            for i in range(0, total_records, self.batch_size):
                batch_end = min(i + self.batch_size, total_records)
                batch_data = data_to_process.iloc[i:batch_end]
                
                batch_num = (i // self.batch_size) + 1
                total_batches = (total_records + self.batch_size - 1) // self.batch_size
                
                self.logger.info(f"Processing batch {batch_num}/{total_batches}: records {i+1}-{batch_end}")
                
                batch_mappings, batch_errors = self.process_batch(batch_data, progress_callback)
                all_mappings.extend(batch_mappings)
                all_errors.extend(batch_errors)
                
                # Log progress periodically
                if batch_num % 5 == 0 or batch_num == total_batches:
                    elapsed = time.time() - start_time
                    self.logger.info(f"  Progress: {self.stats['mappings_created']} mappings created, "
                                   f"{self.stats['errors']} errors, {elapsed:.1f}s elapsed")
            
            processing_time = time.time() - start_time
            self.stats['processing_time'] = processing_time
            
            # Calculate URL resolution failures
            self.stats['url_resolution_failures'] = self.stats['from_concept_missing'] + self.stats['to_concept_missing']
            
            # Create result
            result = TransformationResult(
                mappings_created=all_mappings,
                errors=all_errors,
                processing_time=processing_time,
                source_records_processed=self.stats['records_processed'],
                statistics=self.stats.copy()
            )
            
            self.logger.info(f"Transformation complete: {len(all_mappings)} mappings created in {processing_time:.1f}s")
            if all_errors:
                self.logger.warning(f"{len(all_errors)} errors encountered")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Transformation failed: {str(e)}")
            
            # Return partial result even on failure
            return TransformationResult(
                errors=[f"Transformation failed: {str(e)}"],
                processing_time=processing_time,
                source_records_processed=self.stats['records_processed'],
                statistics=self.stats.copy()
            )
