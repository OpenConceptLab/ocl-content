#!/usr/bin/env python3
"""
Simple LOINC to UMLS CUI Mapper using Direct API Calls and Multi-Level Caching
==============================================================================

This script maps LOINC codes to their corresponding UMLS CUIs using:
1. Local UMLS cache (from MRCONSO.RRF extraction) - FASTEST
2. Local API results cache - FAST  
3. UMLS REST API calls - SLOWEST

Requirements:
- pip install requests pandas
- UMLS API key (free from https://uts.nlm.nih.gov/uts/)
- Optional: Local UMLS cache from umls_loinc_extractor.py

Usage:
    # Drop-in replacement for existing SimpleLOINCMapper
    mapper = SimpleLOINCMapper(api_key="your_key")
    result = mapper.search_loinc_code("100000-9")
    
    # With local UMLS cache (recommended)
    mapper = SimpleLOINCMapper(
        api_key="your_key",
        umls_cache_file="output/loinc_cui_simple_lookup.json"
    )
    
    # With config file support
    mapper = SimpleLOINCMapper(config_path="UMLS_API_config.json")
"""

import argparse
import csv
import json
import logging
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sys
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("Error: pandas not installed. Please run: pip install pandas")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_loinc_mapping.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "UMLS_API_config.json") -> Dict[str, Any]:
    """Load configuration from JSON file."""
    if not Path(config_path).exists():
        return {}
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.warning(f"Error loading config file {config_path}: {e}")
        return {}


class SimpleLOINCMapper:
    """Enhanced LOINC to CUI mapper with multi-level caching and config support."""

    def __init__(self, 
                 api_key: Optional[str] = None, 
                 base_url: str = "https://uts-ws.nlm.nih.gov/rest", 
                 rate_limit: float = 0.2, 
                 cache_file_name: Optional[str] = None,
                 config_path: Optional[str] = None,
                 umls_cache_file: Optional[str] = None):
        """
        Initialize the mapper with multi-level caching.

        Args:
            api_key: UMLS API key
            base_url: UMLS REST API base URL
            rate_limit: Delay between API calls in seconds
            cache_file_name: The name of the CSV file to use for API results caching
            config_path: Path to config JSON file (overrides other parameters)
            umls_cache_file: Path to local UMLS cache JSON file
        """
        # Load config if provided
        self.config = {}
        if config_path:
            self.config = load_config(config_path)
        
        # Set parameters with config override support
        self.api_key = api_key or self.config.get("api_key")
        self.base_url = base_url
        self.rate_limit = rate_limit if rate_limit != 0.2 else self.config.get("rate_limit_delay", 0.2)
        
        # Get settings from config
        settings = self.config.get("settings", {})
        self.max_retries = settings.get("max_retries", 3)
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SimpleLOINCMapper/2.0',
            'Accept': 'application/json'
        })
        
        # Set up caching
        self.cache_file_name = cache_file_name or f"loinc_cui_cache_{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        # Load local UMLS cache (highest priority)
        self.umls_cache = self._load_umls_cache(umls_cache_file)
        
        # Load API results cache (medium priority)
        self.api_cache = self._load_api_cache()
        
        # Statistics tracking
        self.stats = {
            'umls_cache_hits': 0,
            'api_cache_hits': 0,
            'api_calls': 0,
            'not_found': 0
        }
        
        # Log initialization info
        if self.umls_cache:
            logger.info(f"Initialized with local UMLS cache: {len(self.umls_cache):,} mappings")
        logger.info(f"Initialized with API cache: {len(self.api_cache):,} mappings")
        if not self.api_key:
            logger.warning("No API key provided. Only cached results will be available.")

    def _load_umls_cache(self, cache_file: Optional[str]) -> Dict[str, str]:
        """Load local UMLS cache file."""
        if not cache_file:
            # Try to find cache file in common locations
            possible_locations = [
                "output/loinc_cui_simple_lookup.json",
                "umls_cache/loinc_cui_simple_lookup.json", 
                "./loinc_cui_simple_lookup.json"
            ]
            
            for location in possible_locations:
                if Path(location).exists():
                    cache_file = location
                    break
            
            if not cache_file:
                logger.info("No local UMLS cache file found. Will use API only.")
                return {}
        
        cache_path = Path(cache_file)
        if not cache_path.exists():
            logger.info(f"UMLS cache file not found: {cache_file}")
            return {}
            
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            logger.info(f"Loaded {len(cache):,} LOINC mappings from local UMLS cache: {cache_file}")
            return cache
        except Exception as e:
            logger.error(f"Failed to load UMLS cache file {cache_file}: {e}")
            return {}

    def _load_api_cache(self) -> Dict[str, str]:
        """Load mappings from a local CSV cache file."""
        if Path(self.cache_file_name).exists():
            try:
                df = pd.read_csv(self.cache_file_name)
                logger.info(f"Loaded {len(df)} mappings from API cache: {self.cache_file_name}")
                return df.set_index('loinc_code')['cui'].to_dict()
            except Exception as e:
                logger.error(f"Failed to load API cache file {self.cache_file_name}: {e}")
                return {}
        else:
            logger.info("No existing API cache file found. Starting with an empty cache.")
            return {}

    def _save_api_cache(self, loinc_code: str, cui: str):
        """Append a new mapping to the API cache file."""
        df = pd.DataFrame([{'loinc_code': loinc_code, 'cui': cui}])
        df.to_csv(self.cache_file_name, mode='a', header=not Path(self.cache_file_name).exists(), index=False)

    def search_loinc_code(self, loinc_code: str) -> Optional[Dict]:
        """
        Search for a LOINC code using multi-level caching, maintaining original interface.

        Args:
            loinc_code: The LOINC code to search for

        Returns:
            Dictionary with mapping information or None if failed
        """
        loinc_code = str(loinc_code).strip()
        
        # Level 1: Check local UMLS cache first (fastest)
        if loinc_code in self.umls_cache:
            self.stats['umls_cache_hits'] += 1
            cui = self.umls_cache[loinc_code]
            logger.debug(f"Found {loinc_code} in local UMLS cache: {cui}")
            return {
                'cui': cui,
                'cui_name': '',  # Not available in simple cache
                'source_ui': loinc_code,
                'source_name': 'LNC',
                'mapping_method': 'umls_local_cache'
            }

        # Level 2: Check API results cache
        if loinc_code in self.api_cache:
            self.stats['api_cache_hits'] += 1
            cui = self.api_cache[loinc_code]
            logger.debug(f"Found {loinc_code} in API cache: {cui}")
            return {
                'cui': cui,
                'cui_name': '',  # Not stored in simple cache
                'source_ui': loinc_code,
                'source_name': 'LNC',
                'mapping_method': 'api_cache'
            }

        # Level 3: Try API search strategies (slowest)
        if not self.api_key:
            self.stats['not_found'] += 1
            logger.debug(f"No API key available for {loinc_code}")
            return None

        try:
            strategies = [
                self._search_exact_in_loinc,
                self._search_general_in_loinc,
                self._search_unrestricted
            ]

            for strategy in strategies:
                result = strategy(loinc_code)
                if result:
                    self.stats['api_calls'] += 1
                    logger.debug(f"Successfully mapped {loinc_code} using {strategy.__name__}")
                    
                    # Save to API cache
                    cui = result.get('cui')
                    if cui:
                        self._save_api_cache(loinc_code, cui)
                        self.api_cache[loinc_code] = cui
                    
                    return result

            logger.warning(f"All search strategies failed for: {loinc_code}")
            self.stats['not_found'] += 1
            return None

        except Exception as e:
            logger.error(f"Error searching for {loinc_code}: {str(e)}")
            self.stats['not_found'] += 1
            return None

    def _search_exact_in_loinc(self, loinc_code: str) -> Optional[Dict]:
        """Search for exact match in LOINC source."""
        params = {
            'string': loinc_code,
            'apiKey': self.api_key,
            'sabs': 'LNC',
            'searchType': 'exact',
            'returnIdType': 'code'
        }
        return self._execute_search(loinc_code, params, "exact_loinc")

    def _search_general_in_loinc(self, loinc_code: str) -> Optional[Dict]:
        """Search with general terms in LOINC source."""
        params = {
            'string': loinc_code,
            'apiKey': self.api_key,
            'sabs': 'LNC',
            'searchType': 'words'
        }
        return self._execute_search(loinc_code, params, "general_loinc")

    def _search_unrestricted(self, loinc_code: str) -> Optional[Dict]:
        """Search without source restriction."""
        params = {
            'string': loinc_code,
            'apiKey': self.api_key,
            'searchType': 'exact'
        }
        return self._execute_search(loinc_code, params, "unrestricted")

    def _execute_search(self, loinc_code: str, params: Dict, method: str) -> Optional[Dict]:
        """Execute API search with given parameters and retry logic."""
        url = f"{self.base_url}/search/current"
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code != 200:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"API request failed for {loinc_code} (attempt {attempt + 1}): {response.status_code}. Retrying...")
                        time.sleep(self.rate_limit * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        logger.warning(f"API request failed for {loinc_code} after {self.max_retries} attempts: {response.status_code}")
                        return None

                data = response.json()
                results = data.get('result', {}).get('results', [])

                if not results:
                    return None

                # Extract CUI from first result
                first_result = results[0]
                return self._extract_cui_info(loinc_code, first_result, method)

            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Error executing API search for {loinc_code} (attempt {attempt + 1}): {str(e)}. Retrying...")
                    time.sleep(self.rate_limit * (attempt + 1))
                    continue
                else:
                    logger.error(f"Error executing API search for {loinc_code} after {self.max_retries} attempts: {str(e)}")
                    return None

        # Rate limiting for successful calls
        time.sleep(self.rate_limit)
        return None

    def _extract_cui_info(self, loinc_code: str, result: Dict, method: str) -> Optional[Dict]:
        """Extract CUI information from API result."""
        try:
            uri = result.get('uri', '')

            # Extract CUI from URI
            if '/CUI/' not in uri:
                return None

            cui = uri.split('/CUI/')[-1].split('/')[0].split('?')[0]

            if not cui or cui == '':
                return None

            # Additional validation: skip MTH codes that might come from API
            source_ui = result.get('ui', '')
            if source_ui.startswith('MTH'):
                logger.debug(f"Skipping MTH code from API result: {source_ui}")
                return None

            mapping_info = {
                'loinc_code': loinc_code,
                'cui': cui,
                'cui_name': result.get('name', ''),
                'source_ui': source_ui,
                'source_name': result.get('rootSource', ''),
                'mapping_method': method
            }

            return mapping_info

        except Exception as e:
            logger.error(f"Error extracting CUI for {loinc_code}: {str(e)}")
            return None

    def process_loinc_list(self, loinc_codes: List[str], progress_interval: int = 10, force_refresh: bool = False) -> Tuple[List[Dict], List[str]]:
        """
        Process a list of LOINC codes.

        Args:
            loinc_codes: List of LOINC codes to process
            progress_interval: How often to show progress
            force_refresh: If True, ignore all caches and re-query all codes

        Returns:
            Tuple of (successful_mappings, failed_codes)
        """
        successful_mappings = []
        failed_codes = []
        total_codes = len(loinc_codes)

        if force_refresh:
            # Clear caches for fresh start
            self.umls_cache = {}
            self.api_cache = {}
            if Path(self.cache_file_name).exists():
                Path(self.cache_file_name).unlink()
            logger.info("Forcing cache refresh. All LOINC codes will be re-queried.")
        else:
            logger.info(f"Starting to process {total_codes} LOINC codes using multi-level caching...")

        for i, loinc_code in enumerate(loinc_codes, 1):
            loinc_code = str(loinc_code).strip()

            if not loinc_code:
                continue

            # Progress update
            if i % progress_interval == 0 or i == total_codes:
                logger.info(f"Progress: {i}/{total_codes} ({i/total_codes*100:.1f}%)")
                self._print_cache_stats()

            # Search for mapping
            mapping = self.search_loinc_code(loinc_code)

            if mapping and mapping.get('cui'):
                successful_mappings.append(mapping)
                logger.debug(f"✓ {loinc_code} -> {mapping['cui']} (Method: {mapping.get('mapping_method', 'unknown')})")
            else:
                failed_codes.append(loinc_code)
                logger.debug(f"✗ Failed to map {loinc_code}")

        logger.info(f"Processing complete. Successfully mapped {len(successful_mappings)}/{total_codes} codes ({len(successful_mappings)/total_codes*100:.1f}%)")
        self._print_cache_stats()
        
        return successful_mappings, failed_codes

    def _print_cache_stats(self):
        """Print cache performance statistics."""
        total_requests = sum(self.stats.values())
        if total_requests == 0:
            return

        logger.info("Cache Performance:")
        logger.info(f"  UMLS cache hits: {self.stats['umls_cache_hits']:,} ({self.stats['umls_cache_hits']/total_requests*100:.1f}%)")
        logger.info(f"  API cache hits: {self.stats['api_cache_hits']:,} ({self.stats['api_cache_hits']/total_requests*100:.1f}%)")
        logger.info(f"  API calls made: {self.stats['api_calls']:,} ({self.stats['api_calls']/total_requests*100:.1f}%)")
        logger.info(f"  Not found: {self.stats['not_found']:,} ({self.stats['not_found']/total_requests*100:.1f}%)")

        # Calculate cache efficiency
        cache_hits = self.stats['umls_cache_hits'] + self.stats['api_cache_hits']
        if total_requests > 0:
            cache_efficiency = cache_hits / total_requests * 100
            logger.info(f"  Total cache efficiency: {cache_efficiency:.1f}%")

    def get_cache_info(self) -> Dict[str, int]:
        """Get information about loaded caches."""
        return {
            'umls_cache_size': len(self.umls_cache),
            'api_cache_size': len(self.api_cache),
            'total_cache_size': len(self.umls_cache) + len(self.api_cache)
        }


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(description="Simple LOINC to UMLS CUI Mapper with Enhanced Caching")
    parser.add_argument('--input', type=str, required=True, help='Input file with LOINC codes (one per line)')
    parser.add_argument('--output', type=str, default='loinc_mappings.csv', help='Output CSV file')
    parser.add_argument('--api_key', type=str, help='UMLS API key')
    parser.add_argument('--config', type=str, default='UMLS_API_config.json', help='Config file path')
    parser.add_argument('--umls_cache', type=str, help='Path to local UMLS cache JSON file')
    parser.add_argument('--refresh', action='store_true', help='Force refresh all caches')
    parser.add_argument('--progress', type=int, default=100, help='Progress reporting interval')

    args = parser.parse_args()

    # Initialize mapper
    mapper = SimpleLOINCMapper(
        api_key=args.api_key,
        config_path=args.config,
        umls_cache_file=args.umls_cache
    )

    # Print cache info
    cache_info = mapper.get_cache_info()
    logger.info(f"Initialized with {cache_info['total_cache_size']:,} total cached mappings")

    # Read input codes
    try:
        with open(args.input, 'r') as f:
            loinc_codes = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(loinc_codes)} LOINC codes from {args.input}")
    except FileNotFoundError:
        logger.error(f"Input file not found: {args.input}")
        return 1

    # Process codes
    successful, failed = mapper.process_loinc_list(
        loinc_codes, 
        progress_interval=args.progress,
        force_refresh=args.refresh
    )

    # Save results
    if successful:
        df = pd.DataFrame(successful)
        df.to_csv(args.output, index=False)
        logger.info(f"Saved {len(successful)} successful mappings to {args.output}")

    if failed:
        failed_file = args.output.replace('.csv', '_failed.txt')
        with open(failed_file, 'w') as f:
            f.write('\n'.join(failed))
        logger.info(f"Saved {len(failed)} failed codes to {failed_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())