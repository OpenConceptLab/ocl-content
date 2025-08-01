"""
Data Loader Module for LOINC to OCL Transformation

This module orchestrates the complete data loading process including:
- Configuration management and validation
- File loading and parsing with error handling
- Data validation and integrity checks
- Cross-reference table creation
- Memory management and optimization
- Progress tracking and reporting

Author: LOINC OCL Transform Project
Date: July 2025
"""

import os
import time
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

# Import our custom modules
from config_manager import ConfigManager, ProjectPaths, ProcessingConfig
from file_handler import FileHandler, ParseResult, FileInfo
from validator import DataValidator, ValidationReport, ValidationIssue


@dataclass
class LoadedDataset:
    """Data class for a completely loaded and validated dataset"""
    name: str
    data: pd.DataFrame
    file_info: FileInfo
    row_count: int
    column_count: int
    key_column: Optional[str] = None
    validation_errors: int = 0
    validation_warnings: int = 0
    load_time_seconds: float = 0.0


@dataclass
class CrossReferenceTable:
    """Data class for cross-reference lookup tables"""
    name: str
    description: str
    source_file: str
    key_column: str
    value_columns: List[str]
    lookup_dict: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get_value(self, key: str, column: str = None) -> Any:
        """Get value(s) for a given key"""
        if key not in self.lookup_dict:
            return None
        
        if column:
            return self.lookup_dict[key].get(column)
        else:
            return self.lookup_dict[key]


@dataclass
class LoadingSummary:
    """Data class for loading process summary"""
    start_time: float
    end_time: float
    total_files_processed: int
    total_rows_loaded: int
    successful_files: int
    failed_files: int
    datasets: Dict[str, LoadedDataset] = field(default_factory=dict)
    cross_references: Dict[str, CrossReferenceTable] = field(default_factory=dict)
    validation_report: Optional[ValidationReport] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def is_successful(self) -> bool:
        return len(self.errors) == 0 and self.failed_files == 0
    
    def add_error(self, error: str) -> None:
        """Add error message to summary"""
        self.errors.append(error)
        
    def add_warning(self, warning: str) -> None:
        """Add warning message to summary"""
        self.warnings.append(warning)


class DataLoader:
    """
    Orchestrates the complete LOINC data loading process.
    
    This class coordinates:
    1. Configuration loading and validation
    2. File discovery and analysis
    3. Data loading with proper encoding and parsing
    4. Comprehensive data validation
    5. Cross-reference table creation
    6. Memory optimization and cleanup
    
    The result is a validated, ready-to-transform dataset.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize DataLoader
        
        Args:
            config_dir: Optional directory containing configuration files
        """
        self.config_manager = ConfigManager(config_dir)
        self.file_handler = FileHandler(self.config_manager)
        self.validator = DataValidator(self.config_manager)
        self.logger = logging.getLogger(__name__)
        
        # Storage for loaded data
        self.datasets: Dict[str, LoadedDataset] = {}
        self.cross_references: Dict[str, CrossReferenceTable] = {}
        self.loading_summary: Optional[LoadingSummary] = None
        
        # File processing order with correct LOINC folder structure
        self.file_mappings = {
            'Loinc.csv': 'LoincTable/Loinc.csv',
            'Part.csv': 'AccessoryFiles/PartFile/Part.csv',
            'AnswerList.csv': 'AccessoryFiles/AnswerFile/AnswerList.csv',
            'LoincAnswerListLink.csv': 'AccessoryFiles/AnswerFile/LoincAnswerListLink.csv',
            'PanelsAndForms.csv': 'AccessoryFiles/PanelsAndForms/PanelsAndForms.csv',
            'MapTo.csv': 'LoincTable/MapTo.csv'
        }
        
        # File processing order (dependencies first)
        self.file_load_order = [
            'Loinc.csv',           # Main LOINC terms - no dependencies
            'Part.csv',            # LOINC parts - no dependencies  
            'AnswerList.csv',      # Answer lists - no dependencies
            'LoincAnswerListLink.csv',  # Links LOINC terms to answer lists
            'PanelsAndForms.csv',  # Panel relationships
            'MapTo.csv'            # Code evolution mappings
        ]
    
    def load_all_data(self, validate_data: bool = True, 
                     create_cross_refs: bool = True) -> LoadingSummary:
        """
        Load all LOINC data files with comprehensive validation.
        
        Args:
            validate_data: Whether to run data validation (default: True)
            create_cross_refs: Whether to create cross-reference tables (default: True)
            
        Returns:
            LoadingSummary: Complete summary of loading process
        """
        start_time = time.time()
        
        # Initialize summary
        summary = LoadingSummary(
            start_time=start_time,
            end_time=0.0,  # Will be set at the end
            total_files_processed=0,
            total_rows_loaded=0,
            successful_files=0,
            failed_files=0
        )
        
        self.logger.debug(f"Starting load_all_data with validate_data={validate_data}, create_cross_refs={create_cross_refs}")
        
        try:
            self.logger.info("Starting LOINC data loading process...")
            
            # Step 1: Load and validate configuration
            self.logger.debug("Step 1: Loading configuration...")
            if not self._load_configuration(summary):
                self.logger.error("Configuration loading failed")
                return summary
            
            # Step 2: Discover and analyze available files
            self.logger.debug("Step 2: Discovering files...")
            available_files = self._discover_files(summary)
            if not available_files:
                summary.add_error("No LOINC files found to process")
                self.logger.error("No LOINC files found to process")
                return summary
            
            # Step 3: Load files in dependency order
            self._load_files_in_order(available_files, summary)
            
            # Step 4: Run comprehensive data validation
            if validate_data and summary.successful_files > 0:
                self._validate_loaded_data(summary)
            
            # Step 5: Create cross-reference lookup tables
            if create_cross_refs and summary.successful_files > 0:
                self._create_cross_reference_tables(summary)
            
            # Step 6: Memory optimization
            self._optimize_memory_usage(summary)
            
            # Finalize summary
            summary.end_time = time.time()
            summary.datasets = self.datasets
            summary.cross_references = self.cross_references
            
            self.loading_summary = summary
            
            # Log final results
            self._log_loading_summary(summary)
            
        except Exception as e:
            summary.add_error(f"Critical error during data loading: {str(e)}")
            summary.end_time = time.time()
            self.logger.error(f"Data loading failed: {str(e)}")
        
        return summary
    
    def _load_configuration(self, summary: LoadingSummary) -> bool:
        """Load and validate all configuration files"""
        try:
            self.logger.info("Loading configuration files...")
            
            if not self.config_manager.load_all_configs():
                summary.add_error("Failed to load configuration files")
                return False
            
            # Validate input directory exists
            if not self.config_manager.paths.input_dir.exists():
                summary.add_error(f"Input directory not found: {self.config_manager.paths.input_dir}")
                return False
            
            # Validate that required files exist
            file_status = self.config_manager.validate_input_files()
            missing_required = [f for f, exists in file_status.items() if not exists]
            
            if missing_required:
                for missing_file in missing_required:
                    summary.add_warning(f"Input file not found: {missing_file}")
            
            self.logger.info("Configuration loaded successfully")
            return True
            
        except Exception as e:
            summary.add_error(f"Configuration loading failed: {str(e)}")
            return False
    
    def _discover_files(self, summary: LoadingSummary) -> Dict[str, Path]:
        """Discover available LOINC files in input directory with correct folder structure"""
        available_files = {}
        
        try:
            input_dir = self.config_manager.paths.input_dir
            self.logger.info(f"Discovering files in {input_dir}")
            
            # Debug: Show what file mappings we're using
            self.logger.debug(f"Using file mappings: {self.file_mappings}")
            
            # Check for files using the LOINC folder structure
            for file_name, relative_path in self.file_mappings.items():
                file_path = input_dir / relative_path
                self.logger.debug(f"Checking for {file_name} at {file_path}")
                
                if file_path.exists():
                    available_files[file_name] = file_path
                    self.logger.info(f"Found: {file_name} at {relative_path}")
                else:
                    self.logger.debug(f"Not found: {file_name} at {relative_path}")
            
            # Also check for any additional CSV files in common locations
            additional_locations = [
                'LoincTable',
                'AccessoryFiles/PartFile', 
                'AccessoryFiles/AnswerFile',
                'AccessoryFiles/PanelsAndForms',
                'AccessoryFiles/LinguisticVariants'
            ]
            
            for location in additional_locations:
                location_path = input_dir / location
                if location_path.exists():
                    for csv_file in location_path.glob("*.csv"):
                        simple_name = csv_file.name
                        if simple_name not in available_files:
                            available_files[simple_name] = csv_file
                            self.logger.debug(f"Additional file found: {simple_name} at {location}")
            
            if available_files:
                self.logger.info(f"Discovered {len(available_files)} files to process")
                for name, path in available_files.items():
                    self.logger.info(f"  - {name}: {path}")
            else:
                self.logger.warning("No files discovered - this might indicate a path issue")
                self.logger.info(f"Input directory exists: {input_dir.exists()}")
                if input_dir.exists():
                    try:
                        contents = list(input_dir.iterdir())
                        self.logger.info(f"Input directory contents: {[item.name for item in contents[:10]]}")
                    except Exception as e:
                        self.logger.error(f"Could not list input directory: {e}")
            
            return available_files
            
        except Exception as e:
            summary.add_error(f"File discovery failed: {str(e)}")
            self.logger.error(f"File discovery error: {str(e)}")
            return {}
    
    def _load_files_in_order(self, available_files: Dict[str, Path], 
                           summary: LoadingSummary) -> None:
        """Load files in dependency order with error handling"""
        
        # Determine which files to load
        files_to_load = []
        
        # First, add files in preferred order if they exist
        for file_name in self.file_load_order:
            if file_name in available_files:
                files_to_load.append((file_name, available_files[file_name]))
        
        # Then add any additional files
        for file_name, file_path in available_files.items():
            if file_name not in self.file_load_order:
                files_to_load.append((file_name, file_path))
        
        summary.total_files_processed = len(files_to_load)
        
        # Load each file
        for file_name, file_path in files_to_load:
            self._load_single_file(file_name, file_path, summary)
    
    def _load_single_file(self, file_name: str, file_path: Path, 
                         summary: LoadingSummary) -> None:
        """Load a single file with comprehensive error handling"""
        
        load_start = time.time()
        
        try:
            self.logger.info(f"Loading {file_name}...")
            
            # Parse the file
            parse_result = self.file_handler.read_csv_file(file_path, use_pandas=True)
            
            if not parse_result.success:
                summary.add_error(f"Failed to parse {file_name}: {'; '.join(parse_result.errors)}")
                summary.failed_files += 1
                return
            
            # Create dataset record
            dataset = LoadedDataset(
                name=file_name,
                data=parse_result.data,
                file_info=parse_result.file_info,
                row_count=len(parse_result.data),
                column_count=len(parse_result.data.columns),
                load_time_seconds=time.time() - load_start
            )
            
            # Set key column if known
            file_config = self.config_manager.file_mappings.get('loinc_files', {}).get(file_name, {})
            dataset.key_column = file_config.get('key_field')
            
            # Store dataset
            self.datasets[file_name] = dataset
            summary.total_rows_loaded += dataset.row_count
            summary.successful_files += 1
            
            # Log warnings if any
            for warning in parse_result.warnings:
                summary.add_warning(f"{file_name}: {warning}")
            
            self.logger.info(f"✓ Loaded {file_name}: {dataset.row_count:,} rows, {dataset.column_count} columns")
            
        except Exception as e:
            summary.add_error(f"Error loading {file_name}: {str(e)}")
            summary.failed_files += 1
            self.logger.error(f"Failed to load {file_name}: {str(e)}")
    
    def _validate_loaded_data(self, summary: LoadingSummary) -> None:
        """Run comprehensive validation on all loaded data"""
        try:
            self.logger.info("Running data validation...")
            
            # Prepare data for validation
            validation_data = {name: dataset.data for name, dataset in self.datasets.items()}
            
            # Run validation
            validation_report = self.validator.validate_data(validation_data)
            summary.validation_report = validation_report
            
            # Update dataset records with validation results
            for file_name, file_summary in validation_report.file_summaries.items():
                if file_name in self.datasets:
                    self.datasets[file_name].validation_errors = file_summary.get('error_count', 0)
                    self.datasets[file_name].validation_warnings = file_summary.get('warning_count', 0)
            
            # Add validation issues to summary
            if validation_report.error_count > 0:
                summary.add_error(f"Data validation found {validation_report.error_count} errors")
            
            if validation_report.warning_count > 0:
                summary.add_warning(f"Data validation found {validation_report.warning_count} warnings")
            
            self.logger.info(f"Validation complete: {validation_report.error_count} errors, {validation_report.warning_count} warnings")
            
        except Exception as e:
            summary.add_error(f"Data validation failed: {str(e)}")
            self.logger.error(f"Validation error: {str(e)}")
    
    def _create_cross_reference_tables(self, summary: LoadingSummary) -> None:
        """Create cross-reference lookup tables for efficient data access"""
        try:
            self.logger.info("Creating cross-reference tables...")
            
            # Create LOINC code lookup
            if 'Loinc.csv' in self.datasets:
                self._create_loinc_lookup()
            
            # Create Part lookup
            if 'Part.csv' in self.datasets:
                self._create_part_lookup()
            
            # Create Answer List lookup
            if 'AnswerList.csv' in self.datasets:
                self._create_answer_list_lookup()
            
            # Create additional lookups based on available data
            self._create_additional_lookups()
            
            self.logger.info(f"Created {len(self.cross_references)} cross-reference tables")
            
        except Exception as e:
            summary.add_error(f"Cross-reference creation failed: {str(e)}")
            self.logger.error(f"Cross-reference error: {str(e)}")
    
    def _create_loinc_lookup(self) -> None:
        """Create LOINC code lookup table"""
        loinc_data = self.datasets['Loinc.csv'].data
        
        lookup_dict = {}
        for _, row in loinc_data.iterrows():
            loinc_code = str(row['LOINC_NUM'])
            lookup_dict[loinc_code] = row.to_dict()
        
        cross_ref = CrossReferenceTable(
            name="loinc_lookup",
            description="LOINC code to details lookup",
            source_file="Loinc.csv",
            key_column="LOINC_NUM",
            value_columns=list(loinc_data.columns),
            lookup_dict=lookup_dict
        )
        
        self.cross_references["loinc_lookup"] = cross_ref
        self.logger.debug(f"Created LOINC lookup with {len(lookup_dict)} entries")
    
    def _create_part_lookup(self) -> None:
        """Create LOINC Part lookup table"""
        part_data = self.datasets['Part.csv'].data
        
        lookup_dict = {}
        for _, row in part_data.iterrows():
            part_number = str(row['PartNumber'])
            lookup_dict[part_number] = row.to_dict()
        
        cross_ref = CrossReferenceTable(
            name="part_lookup",
            description="LOINC part number to details lookup",
            source_file="Part.csv",
            key_column="PartNumber",
            value_columns=list(part_data.columns),
            lookup_dict=lookup_dict
        )
        
        self.cross_references["part_lookup"] = cross_ref
        self.logger.debug(f"Created Part lookup with {len(lookup_dict)} entries")
    
    def _create_answer_list_lookup(self) -> None:
        """Create Answer List lookup table"""
        answer_data = self.datasets['AnswerList.csv'].data
        
        lookup_dict = {}
        for _, row in answer_data.iterrows():
            answer_id = str(row['AnswerListId'])
            lookup_dict[answer_id] = row.to_dict()
        
        cross_ref = CrossReferenceTable(
            name="answer_list_lookup",
            description="Answer list ID to details lookup",
            source_file="AnswerList.csv",
            key_column="AnswerListId",
            value_columns=list(answer_data.columns),
            lookup_dict=lookup_dict
        )
        
        self.cross_references["answer_list_lookup"] = cross_ref
        self.logger.debug(f"Created Answer List lookup with {len(lookup_dict)} entries")
    
    def _create_additional_lookups(self) -> None:
        """Create additional specialized lookup tables"""
        
        # Create status lookup for quick status checks
        if 'Loinc.csv' in self.datasets:
            loinc_data = self.datasets['Loinc.csv'].data
            status_lookup = defaultdict(list)
            
            for _, row in loinc_data.iterrows():
                status = row['STATUS']
                loinc_code = str(row['LOINC_NUM'])
                status_lookup[status].append(loinc_code)
            
            # Convert to regular dict
            status_dict = {status: codes for status, codes in status_lookup.items()}
            
            cross_ref = CrossReferenceTable(
                name="status_lookup",
                description="LOINC codes grouped by status",
                source_file="Loinc.csv",
                key_column="STATUS",
                value_columns=["LOINC_CODES"],
                lookup_dict=status_dict
            )
            
            self.cross_references["status_lookup"] = cross_ref
    
    def _optimize_memory_usage(self, summary: LoadingSummary) -> None:
        """Optimize memory usage of loaded datasets"""
        try:
            self.logger.info("Optimizing memory usage...")
            
            for dataset_name, dataset in self.datasets.items():
                # Convert string columns to category where appropriate
                data = dataset.data
                
                for column in data.columns:
                    if data[column].dtype == 'object':
                        # If column has relatively few unique values, convert to category
                        unique_ratio = data[column].nunique() / len(data)
                        if unique_ratio < 0.5:  # Less than 50% unique values
                            data[column] = data[column].astype('category')
                
                # Update dataset
                dataset.data = data
            
            self.logger.info("Memory optimization complete")
            
        except Exception as e:
            summary.add_warning(f"Memory optimization failed: {str(e)}")
    
    def _log_loading_summary(self, summary: LoadingSummary) -> None:
        """Log comprehensive loading summary"""
        
        self.logger.info("=" * 60)
        self.logger.info("LOINC DATA LOADING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Duration: {summary.duration_seconds:.2f} seconds")
        self.logger.info(f"Files Processed: {summary.total_files_processed}")
        self.logger.info(f"Successful: {summary.successful_files}")
        self.logger.info(f"Failed: {summary.failed_files}")
        self.logger.info(f"Total Rows Loaded: {summary.total_rows_loaded:,}")
        self.logger.info(f"Cross-references Created: {len(summary.cross_references)}")
        
        if summary.validation_report:
            val_report = summary.validation_report
            self.logger.info(f"Validation Errors: {val_report.error_count}")
            self.logger.info(f"Validation Warnings: {val_report.warning_count}")
        
        # Log dataset details
        self.logger.info("\nDATASET DETAILS:")
        for name, dataset in summary.datasets.items():
            self.logger.info(f"  {name}: {dataset.row_count:,} rows, {dataset.column_count} cols, {dataset.load_time_seconds:.2f}s")
        
        # Log errors and warnings
        if summary.errors:
            self.logger.info(f"\nERRORS ({len(summary.errors)}):")
            for error in summary.errors:
                self.logger.error(f"  {error}")
        
        if summary.warnings:
            self.logger.info(f"\nWARNINGS ({len(summary.warnings)}):")
            for warning in summary.warnings:
                self.logger.warning(f"  {warning}")
        
        status = "SUCCESS" if summary.is_successful else "FAILED"
        self.logger.info(f"\nLOADING STATUS: {status}")
        self.logger.info("=" * 60)
    
    def get_dataset(self, file_name: str) -> Optional[pd.DataFrame]:
        """Get loaded dataset by file name"""
        if file_name in self.datasets:
            return self.datasets[file_name].data
        return None
    
    def get_cross_reference(self, ref_name: str) -> Optional[CrossReferenceTable]:
        """Get cross-reference table by name"""
        return self.cross_references.get(ref_name)
    
    def lookup_loinc_details(self, loinc_code: str) -> Optional[Dict[str, Any]]:
        """Quick lookup of LOINC code details"""
        loinc_lookup = self.get_cross_reference("loinc_lookup")
        if loinc_lookup:
            return loinc_lookup.get_value(loinc_code)
        return None
    
    def get_loading_summary(self) -> Optional[LoadingSummary]:
        """Get the most recent loading summary"""
        return self.loading_summary


# Example usage and testing
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test data loader
    print("Testing LOINC Data Loader...")
    print("=" * 50)
    
    try:
        # Initialize data loader
        loader = DataLoader()
        
        # Load all data
        summary = loader.load_all_data(
            validate_data=True,
            create_cross_refs=True
        )
        
        # Display results
        print(f"\nLoading completed in {summary.duration_seconds:.2f} seconds")
        print(f"Status: {'SUCCESS' if summary.is_successful else 'FAILED'}")
        print(f"Files loaded: {summary.successful_files}/{summary.total_files_processed}")
        print(f"Total rows: {summary.total_rows_loaded:,}")
        
        if summary.datasets:
            print("\nLoaded datasets:")
            for name, dataset in summary.datasets.items():
                print(f"  {name}: {dataset.row_count:,} rows")
        
        if summary.cross_references:
            print(f"\nCross-references: {len(summary.cross_references)}")
            for name in summary.cross_references:
                print(f"  {name}")
        
        # Test a lookup if data was loaded
        if summary.successful_files > 0:
            print("\nTesting LOINC lookup...")
            # Get first LOINC code from dataset
            loinc_data = loader.get_dataset('Loinc.csv')
            if loinc_data is not None and not loinc_data.empty:
                first_loinc_code = str(loinc_data.iloc[0]['LOINC_NUM'])
                details = loader.lookup_loinc_details(first_loinc_code)
                if details:
                    print(f"  ✓ Successfully looked up {first_loinc_code}")
                    print(f"    Name: {details.get('LONG_COMMON_NAME', 'N/A')}")
                else:
                    print(f"  ✗ Failed to lookup {first_loinc_code}")
        
        if summary.errors:
            print(f"\nErrors: {len(summary.errors)}")
            for error in summary.errors[:5]:  # Show first 5 errors
                print(f"  {error}")
        
        if summary.warnings:
            print(f"\nWarnings: {len(summary.warnings)}")
            for warning in summary.warnings[:5]:  # Show first 5 warnings
                print(f"  {warning}")
                
    except Exception as e:
        print(f"Error testing data loader: {str(e)}")
        import traceback
        traceback.print_exc()