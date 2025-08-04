"""
Configuration Management Module for LOINC to OCL Transformation

This module handles loading and validation of configuration files including:
- Runtime settings (paths, versions, processing parameters)
- Transformation rules (LOINC to OCL mapping rules)
- File mappings (input file specifications)

Author: LOINC OCL Transform Project
Date: July 2025
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass, field
import time


@dataclass
class ProjectPaths:
    """Data class for project directory paths"""
    input_dir: Path
    output_dir: Path
    temp_dir: Path
    logs_dir: Path
    
    def create_directories(self) -> None:
        """Create all required directories if they don't exist"""
        for path_attr in ['output_dir', 'temp_dir', 'logs_dir']:
            path = getattr(self, path_attr)
            path.mkdir(parents=True, exist_ok=True)


@dataclass
class ProcessingConfig:
    """Data class for processing configuration parameters"""
    batch_sizes: Dict[str, int]
    umls_api: Dict[str, Any]
    parallel_processing: bool = False
    max_workers: int = 4


@dataclass
class TransformationRules:
    """Data class for transformation rules and mappings"""
    version: str
    target_loinc_version: str
    status_mappings: Dict[str, List[str]]
    container_concepts: List[Dict[str, str]]
    loinc_term_mappings: Dict[str, str]
    field_mappings: Dict[str, Any] = None
    
    # Optional fields that may be present in YAML
    created_date: Optional[str] = None
    description: Optional[str] = None
    part_mappings: Optional[Dict[str, Any]] = None
    answer_list_mappings: Optional[Dict[str, Any]] = None
    answer_mappings: Optional[Dict[str, Any]] = None
    mapping_types: Optional[Dict[str, Any]] = None
    hierarchy_rules: Optional[Dict[str, Any]] = None
    quality_rules: Optional[Dict[str, Any]] = None
    output_rules: Optional[Dict[str, Any]] = None
    umls_enhancement: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Handle any additional fields from YAML"""
        if self.field_mappings is None:
            self.field_mappings = {}


class ConfigManager:
    """
    Manages configuration loading, validation, and access for the LOINC transformation project.
    
    Handles three main configuration files:
    1. settings.yaml - Runtime configuration (paths, versions, processing params)
    2. transformation_rules_v1.yaml - LOINC to OCL transformation logic
    3. file_mappings.yaml - Input file specifications and validation rules
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize ConfigManager
        
        Args:
            config_dir: Optional directory containing config files. 
                       If None, uses current directory.
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd()
        self.settings: Optional[Dict[str, Any]] = None
        self.transformation_rules: Optional[TransformationRules] = None
        self.file_mappings: Optional[Dict[str, Any]] = None
        self.paths: Optional[ProjectPaths] = None
        self.processing: Optional[ProcessingConfig] = None
        
        # Set up basic logging for config operations
        self.logger = logging.getLogger(__name__)
    
    def load_all_configs(self) -> bool:
        """
        Load all configuration files and validate them.
        
        Returns:
            bool: True if all configs loaded successfully, False otherwise
        """
        try:
            # Load settings first as other configs may depend on it
            if not self.load_settings():
                return False
                
            # Load transformation rules
            if not self.load_transformation_rules():
                return False
                
            # Load file mappings
            if not self.load_file_mappings():
                return False
                
            # Create required directories
            if self.paths:
                self.paths.create_directories()
                
            self.logger.info("All configuration files loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load configurations: {str(e)}")
            return False
    
    def load_settings(self, filename: str = "settings.yaml") -> bool:
        """
        Load runtime settings configuration.
        
        Args:
            filename: Name of settings file (default: settings.yaml)
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        settings_path = self.config_dir / filename
        
        try:
            if not settings_path.exists():
                # Create default settings if file doesn't exist
                self._create_default_settings(settings_path)
            
            with open(settings_path, 'r', encoding='utf-8') as f:
                self.settings = yaml.safe_load(f)
            
            # Parse and validate settings
            self._parse_settings()
            
            self.logger.info(f"Settings loaded from {settings_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load settings from {settings_path}: {str(e)}")
            return False
    
    def load_transformation_rules(self, filename: Optional[str] = None) -> bool:
        """
        Load transformation rules configuration.
        
        Args:
            filename: Optional filename. If None, uses version from settings.
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        if not filename and self.settings:
            rules_version = self.settings.get('transformation_rules_version', 'v1')
            filename = f"transformation_rules_{rules_version}.yaml"
        elif not filename:
            filename = "transformation_rules_v1.yaml"
            
        rules_path = self.config_dir / filename
        
        try:
            if not rules_path.exists():
                self._create_default_transformation_rules(rules_path)
            
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules_data = yaml.safe_load(f)
            
            # Extract only the fields that TransformationRules expects
            try:
                # Try to create with all fields first
                self.transformation_rules = TransformationRules(**rules_data)
            except TypeError as e:
                # If there are unexpected fields, create with only known fields
                self.logger.debug(f"Some fields in transformation rules not recognized: {str(e)}")
                known_fields = {
                    'version', 'target_loinc_version', 'status_mappings', 
                    'container_concepts', 'loinc_term_mappings', 'field_mappings',
                    'created_date', 'description', 'part_mappings', 'answer_list_mappings',
                    'answer_mappings', 'mapping_types', 'hierarchy_rules', 
                    'quality_rules', 'output_rules', 'umls_enhancement'
                }
                filtered_data = {k: v for k, v in rules_data.items() if k in known_fields}
                
                # Ensure required fields have defaults
                if 'field_mappings' not in filtered_data:
                    filtered_data['field_mappings'] = {}
                
                self.transformation_rules = TransformationRules(**filtered_data)
            
            self.logger.info(f"Transformation rules loaded from {rules_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load transformation rules from {rules_path}: {str(e)}")
            return False
    
    def load_file_mappings(self, filename: str = "file_mappings.yaml") -> bool:
        """
        Load file mappings configuration.
        
        Args:
            filename: Name of file mappings file
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        mappings_path = self.config_dir / filename
        
        try:
            if not mappings_path.exists():
                self._create_default_file_mappings(mappings_path)
            
            with open(mappings_path, 'r', encoding='utf-8') as f:
                self.file_mappings = yaml.safe_load(f)
            
            self.logger.info(f"File mappings loaded from {mappings_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load file mappings from {mappings_path}: {str(e)}")
            return False
    
    def _parse_settings(self) -> None:
        """Parse settings dictionary into structured objects"""
        if not self.settings:
            raise ValueError("Settings not loaded")
        
        # Parse directory paths
        dirs = self.settings.get('directories', {})
        self.paths = ProjectPaths(
            input_dir=Path(dirs.get('input_dir', r'C:\Users\jamlung\Documents\LOINC\Loinc_2.80')),
            output_dir=Path(dirs.get('output_dir', './output')),
            temp_dir=Path(dirs.get('temp_dir', './temp')),
            logs_dir=Path(dirs.get('logs_dir', './logs'))
        )
        
        # Parse processing configuration
        self.processing = ProcessingConfig(
            batch_sizes=self.settings.get('batch_sizes', {
                'concept_batch': 1000,
                'mapping_batch': 500,
                'umls_batch': 100
            }),
            umls_api=self.settings.get('umls_api', {
                'enabled': True,
                'rate_limit': 20,
                'timeout': 30,
                'retry_attempts': 3
            }),
            parallel_processing=self.settings.get('parallel_processing', False),
            max_workers=self.settings.get('max_workers', 4)
        )
    
    def _create_default_settings(self, settings_path: Path) -> None:
        """Create default settings file"""
        default_settings = {
            'project_name': 'LOINC_OCL_Transform',
            'loinc_version': '2.80',
            'transformation_rules_version': 'v1',
            'log_level': 'INFO',
            'directories': {
                'input_dir': r'C:\Users\jamlung\Documents\LOINC\Loinc_2.80',
                'output_dir': r'C:\Users\jamlung\Documents\LOINC\LOINC Content for OCL - put in GitHub\ETL Development - LOINC 2-80\output',
                'temp_dir': r'C:\Users\jamlung\Documents\LOINC\LOINC Content for OCL - put in GitHub\ETL Development - LOINC 2-80\temp',
                'logs_dir': r'C:\Users\jamlung\Documents\LOINC\LOINC Content for OCL - put in GitHub\ETL Development - LOINC 2-80\logs'
            },
            'batch_sizes': {
                'concept_batch': 1000,
                'mapping_batch': 500,
                'umls_batch': 100
            },
            'umls_api': {
                'enabled': True,
                'rate_limit': 20,
                'timeout': 30,
                'retry_attempts': 3
            },
            'parallel_processing': False,
            'max_workers': 4
        }
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_settings, f, default_flow_style=False, indent=2)
    
    def _create_default_transformation_rules(self, rules_path: Path) -> None:
        """Create default transformation rules file"""
        default_rules = {
            'version': 'v1',
            'target_loinc_version': '2.80',
            'status_mappings': {
                'retired_true': ['DEPRECATED'],
                'retired_false': ['ACTIVE', 'TRIAL', 'DISCOURAGED']
            },
            'container_concepts': [
                {'id': 'LOINC_COMPONENT', 'name': 'LOINC Component', 'description': 'Component parts without hierarchy'},
                {'id': 'LOINC_PROPERTY', 'name': 'LOINC Property', 'description': 'Property parts without hierarchy'},
                {'id': 'LOINC_TIME', 'name': 'LOINC Time', 'description': 'Time aspects without hierarchy'},
                {'id': 'LOINC_SYSTEM', 'name': 'LOINC System', 'description': 'System parts without hierarchy'},
                {'id': 'LOINC_SCALE', 'name': 'LOINC Scale', 'description': 'Scale types without hierarchy'},
                {'id': 'LOINC_METHOD', 'name': 'LOINC Method', 'description': 'Method parts without hierarchy'},
                {'id': 'OTHER', 'name': 'Other', 'description': 'Uncategorized parts'}
            ],
            'loinc_term_mappings': {
                'id_field': 'LOINC_NUM',
                'retired_logic': 'status_mappings',
                'primary_name': 'LONG_COMMON_NAME',
                'secondary_name': 'SHORTNAME'
            },
            'field_mappings': {
                'concept_class': 'Test',
                'datatype': 'None',
                'default_locale': 'en'
            }
        }
        
        with open(rules_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_rules, f, default_flow_style=False, indent=2)
    
    def _create_default_file_mappings(self, mappings_path: Path) -> None:
        """Create default file mappings file"""
        default_mappings = {
            'loinc_files': {
                'Loinc.csv': {
                    'description': 'Main LOINC terms table',
                    'required': True,
                    'key_field': 'LOINC_NUM',
                    'expected_columns': ['LOINC_NUM', 'LONG_COMMON_NAME', 'SHORTNAME', 'STATUS']
                },
                'Part.csv': {
                    'description': 'LOINC parts/components',
                    'required': True,
                    'key_field': 'PartNumber',
                    'expected_columns': ['PartNumber', 'PartDisplayName', 'PartName']
                },
                'AnswerList.csv': {
                    'description': 'Answer lists for LOINC terms',
                    'required': True,
                    'key_field': 'AnswerListId',
                    'expected_columns': ['AnswerListId', 'AnswerListName']
                }
            }
        }
        
        with open(mappings_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_mappings, f, default_flow_style=False, indent=2)
    
    def get_input_file_path(self, filename: str) -> Path:
        """Get full path to input file"""
        if not self.paths:
            raise ValueError("Paths not configured. Call load_settings() first.")
        return self.paths.input_dir / filename
    
    def get_output_file_path(self, filename: str) -> Path:
        """Get full path to output file"""
        if not self.paths:
            raise ValueError("Paths not configured. Call load_settings() first.")
        return self.paths.output_dir / filename
    
    def validate_input_files(self) -> Dict[str, bool]:
        """
        Validate that all required input files exist in LOINC folder structure.
        
        Returns:
            Dict mapping filename to existence status
        """
        if not self.file_mappings or not self.paths:
            raise ValueError("Configuration not fully loaded")
        
        # LOINC folder structure mappings
        loinc_file_paths = {
            'Loinc.csv': 'LoincTable/Loinc.csv',
            'Part.csv': 'AccessoryFiles/PartFile/Part.csv',
            'AnswerList.csv': 'AccessoryFiles/AnswerFile/AnswerList.csv',
            'LoincAnswerListLink.csv': 'AccessoryFiles/AnswerFile/LoincAnswerListLink.csv',
            'PanelsAndForms.csv': 'AccessoryFiles/PanelsAndForms/PanelsAndForms.csv',
            'MapTo.csv': 'LoincTable/MapTo.csv'
        }
        
        results = {}
        loinc_files = self.file_mappings.get('loinc_files', {})
        
        for filename, config in loinc_files.items():
            # Use LOINC structure path if available, otherwise try root directory
            if filename in loinc_file_paths:
                file_path = self.paths.input_dir / loinc_file_paths[filename]
            else:
                file_path = self.paths.input_dir / filename
                
            results[filename] = file_path.exists()
            
            if config.get('required', False) and not results[filename]:
                self.logger.warning(f"Required file not found: {file_path}")
        
        return results

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
    
class DiscoveryConfigManager:
    """
    Manages dataset discovery configuration independent of main config manager.
    
    Provides discovery settings and caching functionality for Phase 2 enhancements.
    """
    
    def __init__(self):
        """Initialize discovery config manager with defaults"""
        self.discovery_config = self._get_default_discovery_config()
    
    def _get_default_discovery_config(self) -> Dict[str, Any]:
        """Get default dataset discovery configuration"""
        return {
            'size_thresholds': {
                'loinc_terms': {
                    'min_records': 50000,
                    'max_records': 200000,
                    'expected_records': 104672
                },
                'loinc_parts': {
                    'min_records': 10000,
                    'max_records': 100000,
                    'expected_records': 72740
                },
                'answer_lists': {
                    'min_records': 1000,
                    'max_records': 50000,
                    'expected_records': 30315
                }
            },
            'identification_patterns': {
                'loinc_terms': {
                    'preferred_names': ["Loinc.csv", "loinc_terms", "loinc", "loinc_table"],
                    'required_columns': ["LOINC_NUM", "LONG_COMMON_NAME"],
                    'exclude_patterns': ["part", "answer", "link", "linguistic"]
                },
                'loinc_parts': {
                    'preferred_names': ["Part.csv", "loinc_parts", "parts"],
                    'required_columns': ["PartNumber", "PartDisplayName"],
                    'exclude_patterns': ["link", "supplementary", "primary"]
                },
                'answer_lists': {
                    'preferred_names': ["AnswerList.csv", "answer_lists", "answerlist"],
                    'required_columns': ["AnswerListId", "AnswerListName"],
                    'exclude_patterns': ["link", "string"]
                }
            },
            'behavior': {
                'enable_caching': True,
                'cache_ttl_seconds': 3600,
                'fallback_to_size_matching': True,
                'strict_column_validation': False,
                'log_discovery_details': True
            }
        }
    def get_dataset_discovery_config(self) -> Dict[str, Any]:
        """Get complete dataset discovery configuration"""
        return self.discovery_config
    
    def get_cache_settings(self) -> Dict[str, Any]:
        """Get caching settings for dataset discovery"""
        behavior = self.discovery_config.get('behavior', {})
        
        return {
            'enable_caching': behavior.get('enable_caching', True),
            'cache_ttl_seconds': behavior.get('cache_ttl_seconds', 3600),
            'log_cache_hits': behavior.get('log_discovery_details', True)
        }
    
    def get_discovery_thresholds(self, dataset_type: str) -> Dict[str, int]:
        """Get size thresholds for a specific dataset type"""
        thresholds = self.discovery_config.get('size_thresholds', {})
        return thresholds.get(dataset_type, {})
    
    def get_discovery_patterns(self, dataset_type: str) -> Dict[str, Any]:
        """Get identification patterns for a specific dataset type"""
        patterns = self.discovery_config.get('identification_patterns', {})
        return patterns.get(dataset_type, {})
    
    def create_discovery_cache(self) -> DatasetDiscoveryCache:
        """Create a new discovery cache with configured settings"""
        cache_settings = self.get_cache_settings()
        cache = DatasetDiscoveryCache()
        cache.cache_ttl_seconds = cache_settings['cache_ttl_seconds']
        return cache
    
# Global discovery config instance
_discovery_config_manager = None

def get_discovery_config_manager() -> DiscoveryConfigManager:
    """Get the global discovery config manager instance"""
    global _discovery_config_manager
    if _discovery_config_manager is None:
        _discovery_config_manager = DiscoveryConfigManager()
    return _discovery_config_manager


# Convenience functions for easy access
def get_discovery_config() -> Dict[str, Any]:
    """Get discovery configuration"""
    return get_discovery_config_manager().get_dataset_discovery_config()

def get_cache_settings() -> Dict[str, Any]:
    """Get cache settings"""
    return get_discovery_config_manager().get_cache_settings()

def get_discovery_thresholds(dataset_type: str) -> Dict[str, int]:
    """Get discovery thresholds for dataset type"""
    return get_discovery_config_manager().get_discovery_thresholds(dataset_type)

def get_discovery_patterns(dataset_type: str) -> Dict[str, Any]:
    """Get discovery patterns for dataset type"""
    return get_discovery_config_manager().get_discovery_patterns(dataset_type)

def create_discovery_cache() -> DatasetDiscoveryCache:
    """Create a new discovery cache"""
    return get_discovery_config_manager().create_discovery_cache()


# Example usage and testing
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test configuration loading
    config_mgr = ConfigManager()
    
    print("Loading all configurations...")
    if config_mgr.load_all_configs():
        print("✓ All configurations loaded successfully")
        
        # Test file validation
        print("\nValidating input files...")
        file_status = config_mgr.validate_input_files()
        for filename, exists in file_status.items():
            status = "✓" if exists else "✗"
            print(f"{status} {filename}")
        
        # Display key configuration info
        print(f"\nProject: {config_mgr.settings['project_name']}")
        print(f"LOINC Version: {config_mgr.settings['loinc_version']}")
        print(f"Input Directory: {config_mgr.paths.input_dir}")
        print(f"Output Directory: {config_mgr.paths.output_dir}")
        
    else:
        print("✗ Failed to load configurations")