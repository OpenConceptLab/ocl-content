"""
File Handler Module for LOINC to OCL Transformation

This module handles file I/O operations for LOINC data files including:
- CSV file reading with proper encoding detection
- Data parsing and cleaning
- File validation and integrity checks
- Memory-efficient batch processing
- Error handling and recovery

Author: LOINC OCL Transform Project
Date: July 2025
"""

import csv
import os
import chardet
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator, Tuple, Union
import logging
from dataclasses import dataclass
from io import StringIO


@dataclass
class FileInfo:
    """Data class for file metadata and statistics"""
    filepath: Path
    encoding: str
    size_bytes: int
    row_count: int
    column_count: int
    columns: List[str]
    has_header: bool
    delimiter: str
    sample_rows: List[Dict[str, Any]]


@dataclass
class ParseResult:
    """Data class for file parsing results"""
    success: bool
    data: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]]
    file_info: Optional[FileInfo]
    errors: List[str]
    warnings: List[str]


class FileHandler:
    """
    Handles file I/O operations for LOINC data processing.
    
    Features:
    - Automatic encoding detection
    - Flexible CSV parsing with multiple delimiter support
    - Memory-efficient batch processing
    - Data validation and cleaning
    - Comprehensive error handling
    """
    
    def __init__(self, config_manager=None):
        """
        Initialize FileHandler
        
        Args:
            config_manager: Optional ConfigManager instance for settings
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Default CSV parsing settings
        self.default_csv_settings = {
            'encoding': 'utf-8',
            'delimiter': ',',
            'quotechar': '"',
            'doublequote': True,
            'skipinitialspace': True,
            'strict': False
        }
        
        # Common encodings to try if detection fails
        self.fallback_encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252', 'ascii']
        
        # Common CSV delimiters to detect
        self.common_delimiters = [',', '\t', '|', ';', ':']
    
    def detect_encoding(self, filepath: Path, sample_size: int = 10000) -> str:
        """
        Detect file encoding using chardet library with fallback options.
        
        Args:
            filepath: Path to file
            sample_size: Number of bytes to sample for detection
            
        Returns:
            str: Detected encoding name
        """
        try:
            with open(filepath, 'rb') as f:
                raw_data = f.read(sample_size)
                
            if not raw_data:
                self.logger.warning(f"Empty file: {filepath}")
                return 'utf-8'
            
            # Try chardet detection
            result = chardet.detect(raw_data)
            if result and result['confidence'] > 0.7:  # Lower threshold for UTF-8
                encoding = result['encoding']
                # Always prefer UTF-8 over ASCII for LOINC files
                if encoding and encoding.lower() == 'ascii':
                    # Test if UTF-8 works better for international characters
                    try:
                        raw_data.decode('utf-8')
                        encoding = 'utf-8'
                        self.logger.debug(f"Upgraded ASCII to UTF-8 for {filepath}")
                    except UnicodeDecodeError:
                        pass  # Keep ASCII
                        
                self.logger.debug(f"Detected encoding {encoding} with confidence {result['confidence']:.2f}")
                return encoding or 'utf-8'
            
            # Fallback to trying common encodings, starting with UTF-8
            test_encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252', 'ascii']
            for encoding in test_encodings:
                try:
                    raw_data.decode(encoding)
                    self.logger.debug(f"Using fallback encoding: {encoding}")
                    return encoding
                except UnicodeDecodeError:
                    continue
            
            # Last resort - UTF-8 with error handling
            self.logger.warning(f"Could not detect encoding for {filepath}, using utf-8 with error handling")
            return 'utf-8'
            
        except Exception as e:
            self.logger.error(f"Error detecting encoding for {filepath}: {str(e)}")
            return 'utf-8'  # Default to UTF-8 instead of ASCII
    
    def detect_csv_delimiter(self, filepath: Path, encoding: str, sample_lines: int = 10) -> str:
        """
        Detect CSV delimiter by analyzing sample lines.
        
        Args:
            filepath: Path to CSV file
            encoding: File encoding
            sample_lines: Number of lines to analyze
            
        Returns:
            str: Detected delimiter character
        """
        try:
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                # Read sample lines
                sample_text = ""
                for i, line in enumerate(f):
                    if i >= sample_lines:
                        break
                    sample_text += line
            
            if not sample_text.strip():
                return ','
            
            # Try CSV Sniffer first
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample_text, delimiters=''.join(self.common_delimiters))
                self.logger.debug(f"CSV sniffer detected delimiter: '{dialect.delimiter}'")
                return dialect.delimiter
            except csv.Error:
                pass
            
            # Fallback: count occurrences of common delimiters
            delimiter_counts = {}
            for delimiter in self.common_delimiters:
                count = sample_text.count(delimiter)
                if count > 0:
                    delimiter_counts[delimiter] = count
            
            if delimiter_counts:
                best_delimiter = max(delimiter_counts, key=delimiter_counts.get)
                self.logger.debug(f"Delimiter detection by count: '{best_delimiter}'")
                return best_delimiter
            
            # Default fallback
            return ','
            
        except Exception as e:
            self.logger.error(f"Error detecting delimiter for {filepath}: {str(e)}")
            return ','
    
    def analyze_file(self, filepath: Path) -> FileInfo:
        """
        Analyze file structure and metadata.
        
        Args:
            filepath: Path to file to analyze
            
        Returns:
            FileInfo: Comprehensive file information
        """
        try:
            # Basic file info
            size_bytes = filepath.stat().st_size
            
            # Detect encoding and delimiter
            encoding = self.detect_encoding(filepath)
            delimiter = self.detect_csv_delimiter(filepath, encoding)
            
            # Analyze CSV structure
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                # Peek at first few lines to determine structure
                first_lines = []
                for i, line in enumerate(f):
                    first_lines.append(line.strip())
                    if i >= 5:  # Read first 6 lines
                        break
            
            if not first_lines:
                raise ValueError("File appears to be empty")
            
            # Parse header and sample rows
            reader = csv.reader(first_lines, delimiter=delimiter)
            rows = list(reader)
            
            if not rows:
                raise ValueError("No valid CSV rows found")
            
            # Assume first row is header
            columns = rows[0] if rows else []
            column_count = len(columns)
            has_header = True
            
            # Get sample data rows (skip header)
            sample_rows = []
            for row in rows[1:4]:  # Take up to 3 sample rows
                if len(row) == column_count:
                    row_dict = dict(zip(columns, row))
                    sample_rows.append(row_dict)
            
            # Count total rows (approximate for large files)
            row_count = self._count_file_rows(filepath, encoding)
            
            file_info = FileInfo(
                filepath=filepath,
                encoding=encoding,
                size_bytes=size_bytes,
                row_count=row_count,
                column_count=column_count,
                columns=columns,
                has_header=has_header,
                delimiter=delimiter,
                sample_rows=sample_rows
            )
            
            self.logger.info(f"Analyzed {filepath.name}: {row_count} rows, {column_count} columns")
            return file_info
            
        except Exception as e:
            self.logger.error(f"Error analyzing file {filepath}: {str(e)}")
            raise
    
    def _count_file_rows(self, filepath: Path, encoding: str) -> int:
        """
        Count rows in file efficiently.
        
        Args:
            filepath: Path to file
            encoding: File encoding
            
        Returns:
            int: Number of rows in file
        """
        try:
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                row_count = sum(1 for line in f)
            return max(0, row_count - 1)  # Subtract header row
            
        except Exception as e:
            self.logger.warning(f"Could not count rows in {filepath}: {str(e)}")
            return 0
    
    def read_csv_file(self, filepath: Path, use_pandas: bool = True, 
                     chunk_size: Optional[int] = None) -> ParseResult:
        """
        Read CSV file with comprehensive error handling and validation.
        
        Args:
            filepath: Path to CSV file
            use_pandas: Whether to use pandas for reading (default: True)
            chunk_size: Optional chunk size for batch processing
            
        Returns:
            ParseResult: Parsing results with data and metadata
        """
        result = ParseResult(
            success=False,
            data=None,
            file_info=None,
            errors=[],
            warnings=[]
        )
        
        try:
            if not filepath.exists():
                result.errors.append(f"File not found: {filepath}")
                return result
            
            # Analyze file first
            try:
                file_info = self.analyze_file(filepath)
                result.file_info = file_info
            except Exception as e:
                result.errors.append(f"File analysis failed: {str(e)}")
                return result
            
            # Read file data
            if use_pandas:
                data = self._read_with_pandas(filepath, file_info, chunk_size)
            else:
                data = self._read_with_csv_module(filepath, file_info, chunk_size)
            
            result.data = data
            result.success = True
            
            # Add warnings for potential issues
            if file_info.size_bytes > 100 * 1024 * 1024:  # > 100MB
                result.warnings.append("Large file detected - consider using chunk processing")
            
            if file_info.row_count == 0:
                result.warnings.append("File contains no data rows")
            
            self.logger.info(f"Successfully read {filepath.name}: {file_info.row_count} rows")
            
        except Exception as e:
            result.errors.append(f"Unexpected error reading {filepath}: {str(e)}")
            self.logger.error(result.errors[-1])
        
        return result
    
    def _read_with_pandas(self, filepath: Path, file_info: FileInfo, 
                         chunk_size: Optional[int] = None) -> pd.DataFrame:
        """Read CSV file using pandas with optimized settings"""
        
        pandas_args = {
            'filepath_or_buffer': str(filepath),
            'encoding': file_info.encoding,
            'encoding_errors': 'replace',  # Handle encoding errors gracefully
            'delimiter': file_info.delimiter,
            'quotechar': '"',
            'skipinitialspace': True,
            'na_values': ['', 'NULL', 'null', 'N/A', 'n/a', 'NA', 'na'],
            'keep_default_na': True,
            'low_memory': False,  # Ensure consistent dtypes
            'dtype': str  # Read all columns as strings initially
        }
        
        if chunk_size:
            pandas_args['chunksize'] = chunk_size
            return pd.read_csv(**pandas_args)  # Returns iterator
        else:
            return pd.read_csv(**pandas_args)
    
    def _read_with_csv_module(self, filepath: Path, file_info: FileInfo, 
                            chunk_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read CSV file using standard csv module"""
        
        data = []
        
        with open(filepath, 'r', encoding=file_info.encoding, errors='replace') as f:
            reader = csv.DictReader(
                f,
                delimiter=file_info.delimiter,
                quotechar='"',
                skipinitialspace=True
            )
            
            if chunk_size:
                # Return generator for chunked processing
                return self._chunked_reader(reader, chunk_size)
            else:
                # Read all data
                for row in reader:
                    # Clean row data
                    cleaned_row = {}
                    for key, value in row.items():
                        # Handle None/empty values
                        if value in ['', 'NULL', 'null', 'N/A', 'n/a', 'NA', 'na']:
                            cleaned_row[key] = None
                        else:
                            cleaned_row[key] = str(value).strip() if value else None
                    data.append(cleaned_row)
        
        return data
    
    def _chunked_reader(self, reader: csv.DictReader, chunk_size: int) -> Iterator[List[Dict[str, Any]]]:
        """Generate chunks of data from CSV reader"""
        chunk = []
        for row in reader:
            # Clean row data
            cleaned_row = {}
            for key, value in row.items():
                if value in ['', 'NULL', 'null', 'N/A', 'n/a', 'NA', 'na']:
                    cleaned_row[key] = None
                else:
                    cleaned_row[key] = str(value).strip() if value else None
            
            chunk.append(cleaned_row)
            
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        
        # Yield remaining rows
        if chunk:
            yield chunk
    
    def write_csv_file(self, data: Union[pd.DataFrame, List[Dict[str, Any]]], 
                      filepath: Path, encoding: str = 'utf-8') -> bool:
        """
        Write data to CSV file.
        
        Args:
            data: Data to write (DataFrame or list of dicts)
            filepath: Output file path
            encoding: File encoding (default: utf-8)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(data, pd.DataFrame):
                data.to_csv(filepath, index=False, encoding=encoding)
            else:
                # Write list of dictionaries
                if not data:
                    self.logger.warning("No data to write")
                    return False
                
                fieldnames = data[0].keys()
                with open(filepath, 'w', newline='', encoding=encoding) as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
            
            self.logger.info(f"Successfully wrote data to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing to {filepath}: {str(e)}")
            return False
    
    def validate_required_columns(self, data: Union[pd.DataFrame, List[Dict[str, Any]]], 
                                 required_columns: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that required columns are present in data.
        
        Args:
            data: Data to validate
            required_columns: List of required column names
            
        Returns:
            Tuple of (is_valid, missing_columns)
        """
        try:
            if isinstance(data, pd.DataFrame):
                available_columns = set(data.columns)
            elif isinstance(data, list) and data:
                available_columns = set(data[0].keys())
            else:
                return False, required_columns
            
            missing_columns = [col for col in required_columns if col not in available_columns]
            is_valid = len(missing_columns) == 0
            
            return is_valid, missing_columns
            
        except Exception as e:
            self.logger.error(f"Error validating columns: {str(e)}")
            return False, required_columns


# Example usage and testing
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test file handler
    file_handler = FileHandler()
    
    # Test file analysis
    test_file = Path(r"C:\Users\jamlung\Documents\LOINC\Loinc_2.80\Loinc.csv")
    
    if test_file.exists():
        print(f"Analyzing {test_file.name}...")
        
        try:
            file_info = file_handler.analyze_file(test_file)
            print(f"✓ File analyzed successfully")
            print(f"  Encoding: {file_info.encoding}")
            print(f"  Delimiter: '{file_info.delimiter}'")
            print(f"  Rows: {file_info.row_count:,}")
            print(f"  Columns: {file_info.column_count}")
            print(f"  Size: {file_info.size_bytes:,} bytes")
            print(f"  First few columns: {file_info.columns[:5]}")
            
            # Test reading a small sample
            print(f"\nReading file sample...")
            result = file_handler.read_csv_file(test_file, chunk_size=100)
            if result.success:
                print(f"✓ Successfully read file")
                if isinstance(result.data, pd.DataFrame):
                    print(f"  Data shape: {result.data.shape}")
                else:
                    print(f"  Data rows: {len(result.data) if result.data else 0}")
            else:
                print(f"✗ Failed to read file: {result.errors}")
                
        except Exception as e:
            print(f"✗ Error testing file handler: {str(e)}")
    else:
        print(f"Test file not found: {test_file}")
        print("Please ensure LOINC files are available for testing")