#!/usr/bin/env python3
"""
Simple LOINC to UMLS CUI Mapper using Direct API Calls and Local Caching
========================================================================

This script maps LOINC codes to their corresponding UMLS CUIs using direct
HTTP requests to the UMLS REST API. It now includes a local caching mechanism
to reduce redundant API calls and save time.

Requirements:
- pip install requests pandas
- UMLS API key (free from https://uts.nlm.nih.gov/uts/)

Usage:
    python simple_loinc_mapper.py --input loinc_codes.txt --output mappings.csv
    python simple_loinc_mapper.py --input loinc_codes.txt --refresh
"""

import argparse
import csv
import json
import logging
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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


class SimpleLOINCMapper:
    """Simple LOINC to CUI mapper using direct UMLS REST API calls with caching."""

    def __init__(self, api_key: str, base_url: str = "https://uts-ws.nlm.nih.gov/rest", rate_limit: float = 0.2, cache_file_name: Optional[str] = None):
        """
        Initialize the mapper.

        Args:
            api_key: UMLS API key
            base_url: UMLS REST API base URL
            rate_limit: Delay between API calls in seconds
            cache_file_name: The name of the CSV file to use for caching.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SimpleLOINCMapper/1.0',
            'Accept': 'application/json'
        })
        self.cache_file_name = cache_file_name or f"loinc_cui_cache_{datetime.now().strftime('%Y-%m-%d')}.csv"
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load mappings from a local CSV cache file."""
        if Path(self.cache_file_name).exists():
            try:
                df = pd.read_csv(self.cache_file_name)
                logger.info(f"Loaded {len(df)} mappings from local cache: {self.cache_file_name}")
                return df.set_index('loinc_code')['cui'].to_dict()
            except Exception as e:
                logger.error(f"Failed to load cache file {self.cache_file_name}: {e}")
                return {}
        else:
            logger.info("No existing cache file found. Starting with an empty cache.")
            return {}

    def _save_cache(self, loinc_code: str, cui: str):
        """Append a new mapping to the cache file."""
        df = pd.DataFrame([{'loinc_code': loinc_code, 'cui': cui}])
        df.to_csv(self.cache_file_name, mode='a', header=not Path(self.cache_file_name).exists(), index=False)

    def search_loinc_code(self, loinc_code: str) -> Optional[Dict]:
        """
        Search for a LOINC code using the UMLS Search API, checking cache first.

        Args:
            loinc_code: The LOINC code to search for

        Returns:
            Dictionary with mapping information or None if failed
        """
        # 1. Check local cache first
        if loinc_code in self.cache:
            logger.debug(f"Found {loinc_code} in cache: {self.cache[loinc_code]}")
            return {'cui': self.cache[loinc_code], 'mapping_method': 'cache'}

        # 2. Try multiple search strategies via UMLS API
        try:
            strategies = [
                self._search_exact_in_loinc,
                self._search_general_in_loinc,
                self._search_unrestricted
            ]

            for strategy in strategies:
                result = strategy(loinc_code)
                if result:
                    logger.debug(f"Successfully mapped {loinc_code} using {strategy.__name__}")
                    # Save to cache before returning
                    self._save_cache(loinc_code, result.get('cui'))
                    self.cache[loinc_code] = result.get('cui')
                    return result

            logger.warning(f"All search strategies failed for: {loinc_code}")
            return None

        except Exception as e:
            logger.error(f"Error searching for {loinc_code}: {str(e)}")
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
        """Execute the actual API search request."""
        try:
            url = f"{self.base_url}/search/current"

            logger.debug(f"Searching {loinc_code} using {method}: {url}")
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code != 200:
                logger.warning(f"API returned status {response.status_code} for {loinc_code}")
                return None

            data = response.json()
            return self._process_search_results(loinc_code, data, method)

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error searching {loinc_code}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {loinc_code}: {str(e)}")
            return None

    def _process_search_results(self, loinc_code: str, data: Dict, method: str) -> Optional[Dict]:
        """Process search results and extract CUI."""
        try:
            results = data.get('result', {}).get('results', [])

            if not results:
                logger.debug(f"No results found for {loinc_code} using {method}")
                return None

            # Look for exact code match first
            for result in results:
                if result.get('ui') == loinc_code:
                    return self._extract_cui_info(loinc_code, result, method, exact_match=True)

            # If no exact match, try first result with valid CUI
            for result in results:
                cui_info = self._extract_cui_info(loinc_code, result, method, exact_match=False)
                if cui_info:
                    return cui_info

            logger.debug(f"No valid CUI found in results for {loinc_code}")
            return None

        except Exception as e:
            logger.error(f"Error processing results for {loinc_code}: {str(e)}")
            return None

    def _extract_cui_info(self, loinc_code: str, result: Dict, method: str, exact_match: bool) -> Optional[Dict]:
        """Extract CUI information from a search result."""
        try:
            uri = result.get('uri', '')

            # Extract CUI from URI
            if '/CUI/' not in uri:
                return None

            cui = uri.split('/CUI/')[-1].split('/')[0].split('?')[0]

            if not cui or cui == '':
                return None

            mapping_info = {
                'loinc_code': loinc_code,
                'cui': cui,
                'cui_name': result.get('name', ''),
                'source_ui': result.get('ui', ''),
                'source_name': result.get('rootSource', ''),
                'mapping_method': method,
                'exact_match': exact_match
            }

            if not exact_match:
                mapping_info['note'] = f"Mapped to similar result: {result.get('ui', '')}"

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
            force_refresh: If True, ignore cache and re-query all codes

        Returns:
            Tuple of (successful_mappings, failed_codes)
        """
        successful_mappings = []
        failed_codes = []
        total_codes = len(loinc_codes)

        if force_refresh:
            self.cache = {}
            if Path(self.cache_file_name).exists():
                Path(self.cache_file_name).unlink()
            logger.info("Forcing cache refresh. All LOINC codes will be re-queried.")
        else:
            logger.info(f"Starting to process {total_codes} LOINC codes using cache...")

        for i, loinc_code in enumerate(loinc_codes, 1):
            loinc_code = str(loinc_code).strip()

            if not loinc_code:
                continue

            # Progress update
            if i % progress_interval == 0 or i == total_codes:
                logger.info(f"Progress: {i}/{total_codes} ({i/total_codes*100:.1f}%)")

            # Search for mapping, now with caching logic
            mapping = self.search_loinc_code(loinc_code)

            if mapping and mapping.get('cui'):
                successful_mappings.append(mapping)
                logger.debug(f"✓ {loinc_code} -> {mapping['cui']} (Method: {mapping.get('mapping_method', 'cached')})")
            else:
                failed_codes.append(loinc_code)
                logger.debug(f"✗ Failed to map {loinc_code}")

            # Rate limiting only applies to API calls
            if mapping and mapping.get('mapping_method') != 'cache':
                time.sleep(self.rate_limit)

        logger.info(f"Processing complete. Success: {len(successful_mappings)}, Failed: {len(failed_codes)}")
        return successful_mappings, failed_codes


def load_config(config_path: str = "config.json") -> Dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        if 'api_key' not in config:
            raise ValueError("Configuration file must contain 'api_key' field")

        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")


def load_loinc_codes(file_path: str) -> List[str]:
    """Load LOINC codes from file."""
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    loinc_codes = []

    if file_path.suffix.lower() == '.csv':
        df = pd.read_csv(file_path)
        loinc_codes = df.iloc[:, 0].astype(str).tolist()
    elif file_path.suffix.lower() == '.json':
        with open(file_path, 'r') as f:
            data = json.load(f)
            loinc_codes = [str(code) for code in data]
    else:
        with open(file_path, 'r') as f:
            loinc_codes = [line.strip() for line in f if line.strip()]

    logger.info(f"Loaded {len(loinc_codes)} LOINC codes from {file_path}")
    return loinc_codes


def save_results(mappings: List[Dict], output_file: str, format_type: str = 'csv'):
    """Save mapping results."""
    if not mappings:
        logger.warning("No mappings to save")
        return

    # Filter out cached results before saving to a separate file
    api_mappings = [m for m in mappings if m.get('mapping_method') != 'cache']
    if not api_mappings:
        logger.warning("No new mappings to save to output file.")
        return

    if format_type == 'json':
        with open(output_file, 'w') as f:
            json.dump(api_mappings, f, indent=2)
    else:
        df = pd.DataFrame(api_mappings)
        df.to_csv(output_file, index=False)

    logger.info(f"Saved {len(api_mappings)} new mappings to {output_file}")


def create_test_codes() -> str:
    """Create a test file with sample LOINC codes."""
    test_codes = [
        "718-7",      # Hemoglobin [Mass/volume] in Blood
        "8462-4",     # Diastolic blood pressure
        "8478-0",     # Systolic blood pressure
        "33747-7",    # Body temperature
        "29463-7",    # Body weight
    ]

    filename = "test_loinc_codes.txt"
    with open(filename, 'w') as f:
        for code in test_codes:
            f.write(f"{code}\n")

    print(f"Created test file: {filename}")
    return filename


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Simple LOINC to UMLS CUI mapper with caching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input loinc_codes.txt --output mappings.csv
  %(prog)s --config my_config.json --input codes.csv --format json
  %(prog)s --test  # Run with test data
  %(prog)s --input loinc_codes.txt --refresh # Force re-querying all codes
        """
    )

    parser.add_argument('--config', '-c', default='config.json',
                        help='Configuration file (default: config.json)')
    parser.add_argument('--input', '-i',
                        help='Input file with LOINC codes')
    parser.add_argument('--output', '-o',
                        help='Output file for new mappings')
    parser.add_argument('--format', '-f', choices=['csv', 'json'], default='csv',
                        help='Output format (default: csv)')
    parser.add_argument('--test', action='store_true',
                        help='Run test with sample LOINC codes')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--refresh', action='store_true',
                        help='Ignore cache and re-query all LOINC codes')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Handle test mode
        if args.test:
            print("Running in test mode...")
            test_file = create_test_codes()
            args.input = test_file
            args.output = "test_mappings.csv"

        # Load configuration
        config = load_config(args.config)
        api_key = config['api_key']

        if api_key == "YOUR_UMLS_API_KEY_HERE":
            print("Error: Please set your UMLS API key in config.json")
            return

        # Validate input
        if not args.input:
            print("Error: Input file is required (use --test for testing)")
            return

        # Set output file
        if not args.output:
            input_path = Path(args.input)
            args.output = f"{input_path.stem}_cui_mappings.{args.format}"

        # Load LOINC codes
        loinc_codes = load_loinc_codes(args.input)

        if not loinc_codes:
            logger.error("No LOINC codes found in input file")
            return

        # Initialize mapper with cache
        rate_limit = config.get('rate_limit_delay', 0.2)
        mapper = SimpleLOINCMapper(api_key, rate_limit=rate_limit)

        # Process codes
        successful_mappings, failed_codes = mapper.process_loinc_list(loinc_codes, force_refresh=args.refresh)

        # Save new results
        if successful_mappings:
            save_results(successful_mappings, args.output, args.format)

        # Save failed codes
        if failed_codes:
            failed_file = f"failed_codes_{int(time.time())}.txt"
            with open(failed_file, 'w') as f:
                for code in failed_codes:
                    f.write(f"{code}\n")
            logger.info(f"Saved {len(failed_codes)} failed codes to {failed_file}")

        # Summary
        total = len(successful_mappings) + len(failed_codes)
        success_rate = (len(successful_mappings) / total * 100) if total > 0 else 0

        print(f"\n{'='*50}")
        print(f"MAPPING COMPLETE")
        print(f"{'='*50}")
        print(f"Total processed: {total}")
        print(f"Successful: {len(successful_mappings)} ({success_rate:.1f}%)")
        print(f"Failed: {len(failed_codes)}")
        print(f"Output: {args.output}")

        if args.test and successful_mappings:
            print(f"\n✅ Test successful! The mapper is working.")
            print(f"Sample mapping: {loinc_codes[0]} -> {successful_mappings[0]['cui']}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise


if __name__ == "__main__":
    main()