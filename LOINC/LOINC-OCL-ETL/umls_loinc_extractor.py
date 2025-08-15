#!/usr/bin/env python3
"""
UMLS LOINC-to-CUI Extractor
============================

This script extracts all LOINC-to-CUI mappings from the UMLS MRCONSO.RRF file
and creates a local cache for fast lookups.

Requirements:
- UMLS license and downloaded MetaThesaurus files
- pandas
- Optional: umls-downloader package for automated downloads

Usage:
    python umls_loinc_extractor.py --mrconso_path /path/to/MRCONSO.RRF
    python umls_loinc_extractor.py --auto_download  # Uses umls-downloader
"""

import pandas as pd
import argparse
import os
import zipfile
import logging
from pathlib import Path
from typing import Dict, Optional, Any
import json
from datetime import datetime

# Will be configured after loading config
logger = logging.getLogger(__name__)

def load_config(config_path: str = "UMLS_API_config.json") -> Dict[str, Any]:
    """Load configuration from JSON file."""
    if not os.path.exists(config_path):
        # Return default config if file doesn't exist
        return {
            "api_key": None,
            "rate_limit_delay": 0.1,
            "default_input_format": "csv",
            "default_output_format": "csv",
            "log_level": "INFO",
            "output_directory": "./output",
            "settings": {
                "include_obsolete": False,
                "include_suppressible": False,
                "preferred_language": "ENG",
                "max_retries": 3
            }
        }
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config file {config_path}: {e}")
        raise

def setup_logging(log_level: str = "INFO"):
    """Setup logging based on config."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True  # Override any existing logging config
    )

class UMLSLoincExtractor:
    """Extracts LOINC-to-CUI mappings from UMLS MRCONSO.RRF file."""
    
    # MRCONSO.RRF column positions (0-indexed)
    MRCONSO_COLUMNS = {
        'CUI': 0,           # UMLS Concept Unique Identifier
        'LAT': 1,           # Language of term
        'TS': 2,            # Term status
        'LUI': 3,           # Lexical Unique Identifier
        'STT': 4,           # String type
        'SUI': 5,           # String Unique Identifier
        'ISPREF': 6,        # Preferred flag
        'AUI': 7,           # Atom Unique Identifier
        'SAUI': 8,          # Source asserted atom identifier
        'SCUI': 9,          # Source asserted concept identifier
        'SDUI': 10,         # Source asserted descriptor identifier
        'SAB': 11,          # Source abbreviation
        'TTY': 12,          # Term type in source
        'CODE': 13,         # Most useful source asserted identifier
        'STR': 14,          # String
        'SRL': 15,          # Source restriction level
        'SUPPRESS': 16,     # Suppressible flag
        'CVF': 17           # Content view flag
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the extractor with config settings."""
        self.config = config or load_config()
        
        # Setup output directory from config
        self.output_dir = Path(self.config.get("output_directory", "./output"))
        self.output_dir.mkdir(exist_ok=True)
        
        # Extract settings
        self.settings = self.config.get("settings", {})
        self.include_obsolete = self.settings.get("include_obsolete", False)
        self.include_suppressible = self.settings.get("include_suppressible", False)
        self.preferred_language = self.settings.get("preferred_language", "ENG")
        self.default_output_format = self.config.get("default_output_format", "csv")
        
    def extract_from_file(self, mrconso_path: str) -> Dict[str, str]:
        """
        Extract LOINC-to-CUI mappings from MRCONSO.RRF file.
        
        Args:
            mrconso_path: Path to MRCONSO.RRF file
            
        Returns:
            Dictionary mapping LOINC codes to CUIs
        """
        logger.info(f"Processing MRCONSO.RRF file: {mrconso_path}")
        
        loinc_mappings = {}
        processed_count = 0
        loinc_count = 0
        
        try:
            with open(mrconso_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        # Split the pipe-delimited line
                        fields = line.strip().split('|')
                        
                        if len(fields) < 18:
                            continue
                            
                        # Extract relevant fields
                        cui = fields[self.MRCONSO_COLUMNS['CUI']]
                        sab = fields[self.MRCONSO_COLUMNS['SAB']]  # Source abbreviation
                        code = fields[self.MRCONSO_COLUMNS['CODE']]  # Source code
                        tty = fields[self.MRCONSO_COLUMNS['TTY']]   # Term type
                        str_text = fields[self.MRCONSO_COLUMNS['STR']]  # String/name
                        lat = fields[self.MRCONSO_COLUMNS['LAT']]   # Language
                        suppress = fields[self.MRCONSO_COLUMNS['SUPPRESS']]  # Suppressible
                        
                        # Filter for LOINC entries based on config settings
                        if (sab == 'LNC' and 
                            lat == self.preferred_language and 
                            (self.include_suppressible or suppress != 'Y')):
                            
                            # Skip obsolete entries if configured
                            if not self.include_obsolete and 'obsolete' in str_text.lower():
                                continue
                                
                            # Extract LOINC code from CODE field
                            loinc_code = code.strip()
                            
                            # Store mapping (prefer preferred terms, but take any)
                            if loinc_code and cui:
                                if loinc_code not in loinc_mappings:
                                    loinc_mappings[loinc_code] = {
                                        'cui': cui,
                                        'name': str_text,
                                        'term_type': tty,
                                        'source': 'UMLS_LOCAL',
                                        'language': lat,
                                        'suppressible': suppress == 'Y'
                                    }
                                    loinc_count += 1
                        
                        processed_count += 1
                        
                        # Progress reporting
                        if processed_count % 100000 == 0:
                            logger.info(f"Processed {processed_count:,} rows, found {loinc_count:,} LOINC mappings")
                            
                    except Exception as e:
                        logger.warning(f"Error processing line {line_num}: {e}")
                        continue
                        
        except FileNotFoundError:
            logger.error(f"MRCONSO.RRF file not found: {mrconso_path}")
            raise
            
        logger.info(f"Extraction complete: {loinc_count:,} LOINC-to-CUI mappings found")
        return loinc_mappings
    
    def save_mappings(self, mappings: Dict, output_format: Optional[str] = None) -> str:
        """
        Save mappings to file using config settings.
        
        Args:
            mappings: Dictionary of LOINC mappings
            output_format: Override default output format from config
            
        Returns:
            Path to saved file
        """
        output_format = output_format or self.default_output_format
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if output_format == 'csv':
            # Convert to DataFrame for CSV export
            df_data = []
            for loinc_code, mapping_info in mappings.items():
                df_data.append({
                    'loinc_code': loinc_code,
                    'cui': mapping_info['cui'],
                    'name': mapping_info['name'],
                    'term_type': mapping_info['term_type'],
                    'source': mapping_info['source'],
                    'language': mapping_info.get('language', self.preferred_language),
                    'suppressible': mapping_info.get('suppressible', False)
                })
            
            df = pd.DataFrame(df_data)
            output_file = self.output_dir / f"loinc_cui_mappings_{timestamp}.csv"
            df.to_csv(output_file, index=False)
            
        elif output_format == 'json':
            output_file = self.output_dir / f"loinc_cui_mappings_{timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump(mappings, f, indent=2)
                
        else:
            raise ValueError("output_format must be 'csv' or 'json'")
            
        logger.info(f"Mappings saved to: {output_file}")
        return str(output_file)
    
    def create_simple_lookup(self, mappings: Dict) -> Dict[str, str]:
        """
        Create a simple LOINC -> CUI lookup dictionary.
        
        Args:
            mappings: Full mapping dictionary
            
        Returns:
            Simple dictionary mapping LOINC codes to CUIs
        """
        return {loinc: info['cui'] for loinc, info in mappings.items()}

def download_umls_auto(version: str = "2025AA", config: Optional[Dict[str, Any]] = None) -> str:
    """
    Automatically download UMLS using umls-downloader package.
    
    Args:
        version: UMLS version to download
        config: Configuration dictionary (will load if not provided)
        
    Returns:
        Path to downloaded MRCONSO.RRF file
    """
    if config is None:
        config = load_config()
    
    api_key = config.get("api_key")
    max_retries = config.get("settings", {}).get("max_retries", 3)
    
    try:
        from umls_downloader import download_umls
        import zipfile
        
        logger.info(f"Downloading UMLS {version} using umls-downloader...")
        
        # Download UMLS zip file with retries
        for attempt in range(max_retries):
            try:
                zip_path = download_umls(version=version, api_key=api_key)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Download attempt {attempt + 1} failed: {e}. Retrying...")
                    continue
                else:
                    raise
        
        # Extract MRCONSO.RRF from zip
        extraction_dir = Path(zip_path).parent / f"umls_{version}_extracted"
        extraction_dir.mkdir(exist_ok=True)
        
        mrconso_path = extraction_dir / "MRCONSO.RRF"
        
        if not mrconso_path.exists():
            logger.info("Extracting MRCONSO.RRF from downloaded zip...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extract("MRCONSO.RRF", extraction_dir)
        
        return str(mrconso_path)
        
    except ImportError:
        logger.error("umls-downloader package not installed. Install with: pip install umls-downloader")
        raise
    except Exception as e:
        logger.error(f"Error downloading UMLS: {e}")
        raise

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Extract LOINC-to-CUI mappings from UMLS")
    parser.add_argument('--config', type=str, default='UMLS_API_config.json', help='Path to config JSON file')
    parser.add_argument('--mrconso_path', type=str, help='Path to MRCONSO.RRF file')
    parser.add_argument('--auto_download', action='store_true', help='Automatically download UMLS')
    parser.add_argument('--version', type=str, default='2025AA', help='UMLS version to download')
    parser.add_argument('--api_key', type=str, help='UMLS API key (overrides config)')
    parser.add_argument('--output_dir', type=str, help='Output directory (overrides config)')
    parser.add_argument('--output_format', type=str, choices=['csv', 'json'], help='Output format (overrides config)')
    parser.add_argument('--log_level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Log level (overrides config)')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}")
        return 1
    
    # Override config with command line arguments
    if args.api_key:
        config['api_key'] = args.api_key
    if args.output_dir:
        config['output_directory'] = args.output_dir
    if args.output_format:
        config['default_output_format'] = args.output_format
    if args.log_level:
        config['log_level'] = args.log_level
    
    # Setup logging
    setup_logging(config.get('log_level', 'INFO'))
    
    # Initialize extractor
    extractor = UMLSLoincExtractor(config=config)
    
    # Determine MRCONSO.RRF path
    if args.auto_download:
        mrconso_path = download_umls_auto(version=args.version, config=config)
    elif args.mrconso_path:
        mrconso_path = args.mrconso_path
    else:
        parser.error("Either --mrconso_path or --auto_download must be specified")
    
    # Extract mappings
    logger.info(f"Starting extraction with settings:")
    logger.info(f"  Include obsolete: {extractor.include_obsolete}")
    logger.info(f"  Include suppressible: {extractor.include_suppressible}")
    logger.info(f"  Preferred language: {extractor.preferred_language}")
    logger.info(f"  Output format: {extractor.default_output_format}")
    
    mappings = extractor.extract_from_file(mrconso_path)
    
    if not mappings:
        logger.error("No LOINC mappings found!")
        return 1
    
    # Save full mappings
    output_file = extractor.save_mappings(mappings)
    
    # Also save simple lookup dictionary
    simple_lookup = extractor.create_simple_lookup(mappings)
    simple_file = extractor.output_dir / f"loinc_cui_simple_lookup.json"
    with open(simple_file, 'w') as f:
        json.dump(simple_lookup, f, indent=2)
    
    logger.info(f"Simple lookup saved to: {simple_file}")
    logger.info(f"Total LOINC codes mapped: {len(mappings):,}")
    
    # Show sample mappings
    logger.info("Sample mappings:")
    for i, (loinc, info) in enumerate(list(mappings.items())[:5]):
        logger.info(f"  {loinc} -> {info['cui']} ({info['name'][:50]}...)")
    
    return 0

if __name__ == "__main__":
    main()
