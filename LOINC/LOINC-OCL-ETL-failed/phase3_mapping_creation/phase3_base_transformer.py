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
    
    def _create_data_loader(self) -> DataLoader:
        """
        Create and configure a DataLoader instance.
        
        Returns:
            DataLoader: Configured data loader
        """
        try:
            # Ensure config manager is loaded
            if not hasattr(self.config_manager, 'config_dir') or not self.config_manager.config_dir:
                self.config_manager.load_all_configs()
            
            # Create data loader with config directory
            data_loader = DataLoader(self.config_manager.config_dir)
            
            self.logger.debug(f"Created data loader with config dir: {self.config_manager.config_dir}")
            return data_loader
            
        except Exception as e:
            self.logger.error(f"Failed to create data loader: {str(e)}")
            raise
    
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
            concept_id: LOINC code or other concept identifier
            
        Returns:
            OCL concept URL or None if not found
        """
        if not concept_id or concept_id == 'nan':
            return None
        
        # Clean the concept ID
        clean_id = str(concept_id).strip()
        if not clean_id:
            return None
        
        return self.concept_url_cache.get(clean_id)
    
    def load_source_data(self) -> bool:
        """
        Load source data for transformation.
        
        FIXED: Complete implementation with proper error handling
        """
        try:
            self.logger.info(f"Loading source data from {self.get_source_file()}")
            
            # Create data loader if not exists
            if not self.data_loader:
                self.data_loader = self._create_data_loader()
            
            # Load all Phase 1 data
            self.logger.info("Loading Phase 1 data...")
            loading_summary = self.data_loader.load_all_data(validate_data=True)
            
            if not loading_summary or not loading_summary.datasets:
                raise Exception("No datasets loaded from Phase 1")
            
            # Apply dataset aliases for compatibility
            datasets = loading_summary.datasets
            if 'Loinc.csv' in datasets and 'loinc_terms' not in datasets:
                datasets['loinc_terms'] = datasets['Loinc.csv']
            
            # Find the source file we need
            source_file = self.get_source_file()
            
            if source_file in datasets:
                dataset = datasets[source_file]
                # Handle LoadedDataset wrapper
                if hasattr(dataset, 'data'):
                    self.source_data = dataset.data
                else:
                    self.source_data = dataset
            else:
                # Try common variations
                source_variations = [
                    source_file,
                    source_file.replace('.csv', ''),
                    source_file.lower(),
                    source_file.lower().replace('.csv', '')
                ]
                
                found = False
                for variation in source_variations:
                    if variation in datasets:
                        dataset = datasets[variation]
                        if hasattr(dataset, 'data'):
                            self.source_data = dataset.data
                        else:
                            self.source_data = dataset
                        found = True
                        self.logger.info(f"Found source data under key: {variation}")
                        break
                
                if not found:
                    available_keys = list(datasets.keys())[:10]  # First 10 for logging
                    raise Exception(f"Source file {source_file} not found. Available: {available_keys}")
            
            if self.source_data is None or len(self.source_data) == 0:
                raise Exception(f"No data found in {source_file}")
            
            self.logger.info(f"Loaded {len(self.source_data):,} records from {source_file}")
            self.logger.info(f"Source data columns: {list(self.source_data.columns)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load source data: {str(e)}")
            return False
    
    def validate_record(self, record: pd.Series) -> Tuple[bool, List[str]]:
        """
        Validate a single record before transformation.
        
        Default implementation - subclasses should override for specific validation.
        
        Args:
            record: Record to validate
            
        Returns:
            Tuple of (is_valid, errors_list)
        """
        return True, []
    
    def _transform_records(self, limit: Optional[int] = None, 
                          progress_callback: Optional[Callable[[float, str], None]] = None) -> TransformationResult:
        """
        Transform all records in the source data.
        
        Args:
            limit: Optional limit on number of records to process
            progress_callback: Optional progress reporting function
            
        Returns:
            TransformationResult with mappings and statistics
        """
        start_time = time.time()
        
        try:
            # Determine record set
            if limit and limit < len(self.source_data):
                records_to_process = self.source_data.head(limit)
                self.logger.info(f"Processing {limit:,} records (limited from {len(self.source_data):,})")
            else:
                records_to_process = self.source_data
                self.logger.info(f"Processing all {len(records_to_process):,} records")
            
            # Process records in batches
            all_mappings = []
            all_errors = []
            total_records = len(records_to_process)
            
            for batch_start in range(0, total_records, self.batch_size):
                batch_end = min(batch_start + self.batch_size, total_records)
                batch = records_to_process.iloc[batch_start:batch_end]
                
                self.logger.info(f"Processing batch {batch_start//self.batch_size + 1}/{(total_records-1)//self.batch_size + 1}: "
                                f"records {batch_start+1}-{batch_end}")
                
                batch_mappings = []
                batch_errors = []
                
                for idx, record in batch.iterrows():
                    try:
                        self.stats['records_processed'] += 1
                        
                        # Validate record
                        is_valid, validation_errors = self.validate_record(record)
                        if not is_valid:
                            batch_errors.extend(validation_errors)
                            self.stats['errors'] += len(validation_errors)
                            continue
                        
                        # Transform record
                        mapping = self.transform_record(record)
                        if mapping:
                            batch_mappings.append(mapping)
                            self.stats['mappings_created'] += 1
                        else:
                            self.stats['warnings'] += 1
                            
                    except Exception as e:
                        error_msg = f"Failed to process record {idx}: {str(e)}"
                        batch_errors.append(error_msg)
                        self.stats['errors'] += 1
                        self.logger.debug(error_msg)
                
                all_mappings.extend(batch_mappings)
                all_errors.extend(batch_errors)
                
                # Progress reporting
                progress = (batch_end / total_records) * 100
                if progress_callback:
                    status = f"{len(all_mappings)} mappings created, {len(all_errors)} errors"
                    progress_callback(progress, status)
                
                # Log progress
                if batch_start % (self.batch_size * 10) == 0 or batch_end >= total_records:
                    elapsed = time.time() - start_time
                    self.logger.info(f"  Progress: {len(all_mappings)} mappings created, {len(all_errors)} errors, {elapsed:.1f}s elapsed")
            
            # Calculate final statistics
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
    
    def run_transformation(self, limit: Optional[int] = None, 
                          progress_callback: Optional[Callable[[float, str], None]] = None) -> TransformationResult:
        """
        Run the complete transformation process.
        
        FIXED: Complete implementation with proper prerequisite loading
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting {self.get_transformer_name()} transformation...")
            
            # Step 1: Load concept URL cache
            if progress_callback:
                progress_callback(5.0, "Loading concept URL cache")
            
            if not self.load_concept_url_cache():
                raise Exception("Failed to load concept URL cache")
            
            # Step 2: Load source data
            if progress_callback:
                progress_callback(15.0, "Loading source data")
            
            if not self.load_source_data():
                raise Exception("Failed to load source data")
            
            # Step 3: Transform records
            if progress_callback:
                progress_callback(25.0, "Starting record transformation")
            
            return self._transform_records(limit, progress_callback)
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Transformation failed: {str(e)}")
            
            return TransformationResult(
                errors=[f"Transformation failed: {str(e)}"],
                processing_time=processing_time,
                source_records_processed=self.stats['records_processed'],
                statistics=self.stats.copy()
            )