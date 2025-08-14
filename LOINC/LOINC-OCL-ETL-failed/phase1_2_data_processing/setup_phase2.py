#!/usr/bin/env python3
"""
Phase 2 Directory Setup Script

Creates the recommended Phase 2 project structure and initializes the development
environment. Organizes code according to the architecture specified in the
Phase 2 Development Handoff Document.

This script sets up:
- Directory structure for Phase 2 components
- Placeholder files for remaining transformers
- Configuration templates
- Development documentation
- Testing framework structure

Usage:
    python setup_phase2.py [--project-dir PATH] [--create-examples] [--force]

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List
import json


def create_directory_structure(base_dir: Path, force: bool = False) -> bool:
    """
    Create the Phase 2 directory structure.
    
    Args:
        base_dir: Base directory for Phase 2 project
        force: Whether to overwrite existing directories
        
    Returns:
        bool: True if successful
    """
    print("📁 Creating Phase 2 directory structure...")
    
    # Define the structure as specified in handoff document
    directories = [
        "phase2_concept_creation",
        "phase2_concept_creation/transformers",
        "phase2_concept_creation/models", 
        "phase2_concept_creation/core",
        "phase2_concept_creation/utils",
        "phase2_concept_creation/tests",
        "phase2_concept_creation/config",
        "phase2_concept_creation/output",
        "phase2_concept_creation/temp",
        "phase2_concept_creation/logs",
        "phase2_concept_creation/docs"
    ]
    
    created_dirs = []
    
    for dir_path in directories:
        full_path = base_dir / dir_path
        
        try:
            if full_path.exists() and not force:
                print(f"   📂 {dir_path} (exists)")
            else:
                full_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(dir_path)
                print(f"   ✅ {dir_path}")
        except Exception as e:
            print(f"   ❌ {dir_path}: {str(e)}")
            return False
    
    print(f"✅ Created {len(created_dirs)} directories")
    return True


def create_init_files(base_dir: Path) -> bool:
    """Create __init__.py files for Python packages"""
    print("🐍 Creating Python package files...")
    
    init_locations = [
        "phase2_concept_creation/__init__.py",
        "phase2_concept_creation/transformers/__init__.py",
        "phase2_concept_creation/models/__init__.py",
        "phase2_concept_creation/core/__init__.py",
        "phase2_concept_creation/utils/__init__.py",
        "phase2_concept_creation/tests/__init__.py"
    ]
    
    for init_file in init_locations:
        init_path = base_dir / init_file
        
        if not init_path.exists():
            with open(init_path, 'w', encoding='utf-8') as f:
                f.write('"""Phase 2 Concept Creation Package"""\n')
            print(f"   ✅ {init_file}")
        else:
            print(f"   📄 {init_file} (exists)")
    
    return True


def create_placeholder_transformers(base_dir: Path) -> bool:
    """Create placeholder files for remaining transformers"""
    print("⚙️ Creating transformer placeholders...")
    
    transformers = {
        "part_transformer.py": "LOINC Parts Transformer",
        "answer_transformer.py": "Answer Lists Transformer", 
        "container_transformer.py": "Container Concepts Generator"
    }
    
    for filename, description in transformers.items():
        file_path = base_dir / "phase2_concept_creation/transformers" / filename
        
        if not file_path.exists():
            template_content = f'''"""
{description} for LOINC to OCL Transformation - Phase 2

TODO: Implement this transformer following the BaseTransformer pattern.

Key requirements:
- Inherit from BaseTransformer
- Implement all abstract methods
- Support multi-language processing
- Follow Phase 2 validation standards

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

from base_transformer import BaseTransformer, TransformationContext
from .ocl_models import OCLConcept
import pandas as pd


class {filename.replace('.py', '').title().replace('_', '')}(BaseTransformer):
    """
    {description}.
    
    TODO: Complete implementation.
    """
    
    def __init__(self, context: TransformationContext):
        super().__init__(context)
        # TODO: Initialize transformer-specific configuration
    
    def get_transformer_name(self) -> str:
        return "{filename.replace('.py', '').replace('_', ' ').title()}"
    
    def get_source_dataset_name(self) -> str:
        # TODO: Return appropriate dataset name
        return "TODO"
    
    def get_primary_key_field(self) -> str:
        # TODO: Return primary key field name
        return "TODO"
    
    def get_concept_class(self, record: pd.Series) -> str:
        # TODO: Implement concept class determination
        return "TODO"
    
    def transform_record(self, record: pd.Series) -> OCLConcept:
        # TODO: Implement record transformation
        raise NotImplementedError("TODO: Implement transform_record method")


# TODO: Remove this section when implementation is complete
if __name__ == "__main__":
    print("TODO: Implement {description}")
'''
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            print(f"   ✅ {filename}")
        else:
            print(f"   📄 {filename} (exists)")
    
    return True


def create_utility_modules(base_dir: Path) -> bool:
    """Create utility modules"""
    print("🔧 Creating utility modules...")
    
    # Language handler utility
    language_handler = base_dir / "phase2_concept_creation/utils/language_handler.py"
    if not language_handler.exists():
        content = '''"""
Language Handler Utility for Multi-language Processing - Phase 2

Handles the 19 language variants loaded in Phase 1, providing utilities for:
- Language code normalization
- Multi-language name extraction
- Unicode text processing
- Locale-specific formatting

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging


class LanguageHandler:
    """
    Utility class for handling multi-language LOINC data.
    
    Supports the 19 language variants loaded in Phase 1.
    """
    
    # Standard language codes supported
    SUPPORTED_LOCALES = [
        'en', 'fr', 'es', 'de', 'it', 'pt', 'nl', 'ru', 'zh', 'ja',
        'ko', 'ar', 'hi', 'sv', 'da', 'no', 'fi', 'pl', 'cs'
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def normalize_locale(self, locale: str) -> str:
        """Normalize locale code to standard format"""
        if not locale:
            return 'en'
        
        # Convert to lowercase and take first part
        clean_locale = locale.lower().split('-')[0].split('_')[0]
        
        # Validate against supported locales
        if clean_locale in self.SUPPORTED_LOCALES:
            return clean_locale
        
        # Default fallback
        return 'en'
    
    def extract_multilingual_names(self, record: pd.Series, 
                                  language_datasets: Dict[str, pd.DataFrame],
                                  primary_key: str) -> List[Tuple[str, str]]:
        """
        Extract names in multiple languages for a concept.
        
        Returns:
            List of (name, locale) tuples
        """
        names = []
        
        for locale, lang_df in language_datasets.items():
            normalized_locale = self.normalize_locale(locale)
            
            # Find matching record
            if primary_key in lang_df.index:
                lang_record = lang_df.loc[primary_key]
                translated_name = self._extract_name_from_record(lang_record)
                
                if translated_name:
                    names.append((translated_name, normalized_locale))
        
        return names
    
    def _extract_name_from_record(self, record: pd.Series) -> Optional[str]:
        """Extract name from language record"""
        # Common name fields in different language files
        name_fields = [
            'LONG_COMMON_NAME',
            'DisplayName',
            'COMPONENT',
            'PartDisplayName',
            'TranslatedName',
            'Name'
        ]
        
        for field in name_fields:
            if field in record and pd.notna(record[field]):
                return str(record[field]).strip()
        
        return None


# TODO: Add more language utilities as needed
'''
        with open(language_handler, 'w', encoding='utf-8') as f:
            f.write(content)
        print("   ✅ language_handler.py")
    
    # Batch processor utility
    batch_processor = base_dir / "phase2_concept_creation/utils/batch_processor.py"
    if not batch_processor.exists():
        content = '''"""
Batch Processor Utility for Memory-Efficient Processing - Phase 2

Provides utilities for batch processing large datasets while maintaining
the memory efficiency proven in Phase 1 (<4GB memory usage).

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

from typing import Iterator, List, Any, Callable, Optional
import pandas as pd
import logging
import time


class BatchProcessor:
    """
    Utility for memory-efficient batch processing.
    
    Maintains Phase 1's performance standards while processing large datasets.
    """
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self.logger = logging.getLogger(__name__)
    
    def process_dataframe_batches(self, 
                                df: pd.DataFrame,
                                processor_func: Callable,
                                progress_callback: Optional[Callable] = None) -> List[Any]:
        """
        Process DataFrame in batches with progress tracking.
        
        Args:
            df: DataFrame to process
            processor_func: Function to process each batch
            progress_callback: Optional progress callback
            
        Returns:
            List of results from each batch
        """
        results = []
        total_batches = (len(df) + self.batch_size - 1) // self.batch_size
        
        self.logger.info(f"Processing {len(df)} records in {total_batches} batches")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            
            # Process batch
            batch_result = processor_func(batch_df)
            results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
            
            # Progress callback
            if progress_callback:
                progress = (batch_num + 1) / total_batches * 100
                progress_callback(progress, batch_num + 1, total_batches)
        
        return results
    
    def create_batches(self, items: List[Any]) -> Iterator[List[Any]]:
        """Create batches from a list of items"""
        for i in range(0, len(items), self.batch_size):
            yield items[i:i + self.batch_size]


# TODO: Add memory monitoring utilities
'''
        with open(batch_processor, 'w', encoding='utf-8') as f:
            f.write(content)
        print("   ✅ batch_processor.py")
    
    return True


def create_test_templates(base_dir: Path) -> bool:
    """Create test templates"""
    print("🧪 Creating test templates...")
    
    tests = {
        "test_ocl_models.py": "OCL Models",
        "test_base_transformer.py": "Base Transformer",
        "test_loinc_transformer.py": "LOINC Terms Transformer",
        "test_concept_factory.py": "Concept Factory"
    }
    
    for filename, component in tests.items():
        test_path = base_dir / "phase2_concept_creation/tests" / filename
        
        if not test_path.exists():
            content = f'''"""
Unit Tests for {component} - Phase 2

TODO: Implement comprehensive unit tests following Phase 1 patterns.

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import unittest
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# TODO: Add appropriate imports


class Test{component.replace(' ', '')}(unittest.TestCase):
    """Test cases for {component}"""
    
    def setUp(self):
        """Set up test fixtures"""
        # TODO: Initialize test data and objects
        pass
    
    def test_placeholder(self):
        """TODO: Replace with actual tests"""
        self.assertTrue(True, "Placeholder test")
    
    # TODO: Add comprehensive test methods


if __name__ == '__main__':
    unittest.main()
'''
            
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   ✅ {filename}")
    
    return True


def create_documentation(base_dir: Path) -> bool:
    """Create documentation files"""
    print("📚 Creating documentation...")
    
    # README for Phase 2
    readme_path = base_dir / "phase2_concept_creation/README.md"
    if not readme_path.exists():
        content = '''# Phase 2: Concept Creation

Transform validated LOINC data from Phase 1 into OCL-compliant concept objects ready for bulk import.

## Overview

**Objective**: Create ~180K OCL Concept objects from LOINC terms, parts, and answer lists.

**Performance Targets** (from Phase 1 benchmarks):
- Processing time: <30 seconds
- Memory usage: <4GB
- Multi-language support: 19 locales
- Zero critical errors

## Architecture

```
phase2_concept_creation/
├── transformers/          # Concept transformers
│   ├── base_transformer.py      # Abstract base class
│   ├── loinc_transformer.py     # LOINC terms (104K records)
│   ├── part_transformer.py      # LOINC parts (72K records)  
│   ├── answer_transformer.py    # Answer lists (30K records)
│   └── container_transformer.py # Container concepts
├── models/               # OCL data models
│   ├── ocl_models.py            # OCL concept structures
│   └── loinc_models.py          # LOINC data structures
├── core/                # Main processing logic
│   ├── concept_factory.py       # Main orchestrator
│   └── validator.py             # OCL validation
├── utils/               # Utility modules
│   ├── language_handler.py      # Multi-language processing
│   └── batch_processor.py       # Batch processing
└── tests/               # Unit tests
```

## Quick Start

1. **Setup Environment**:
   ```bash
   python setup_phase2.py
   ```

2. **Run Concept Creation**:
   ```bash
   python phase2_main.py
   ```

3. **Validate Output**:
   ```bash
   python phase2_main.py --dry-run
   ```

## Expected Output

- **OCL concept files**: JSON-lines format, chunked for optimal import
- **Validation reports**: Comprehensive quality assurance
- **Performance metrics**: Processing statistics and benchmarks
- **Phase 3 handoff**: Ready for mapping creation

## Development Status

### ✅ Completed
- [x] OCL data models
- [x] Base transformer abstract class  
- [x] LOINC terms transformer
- [x] Concept factory orchestrator
- [x] Main entry point script

### 🔄 In Progress
- [ ] LOINC parts transformer
- [ ] Answer lists transformer
- [ ] Container concepts generator
- [ ] Multi-language integration
- [ ] Comprehensive testing

### ⏳ Planned
- [ ] Performance optimization
- [ ] Output file generation
- [ ] Final validation and handoff

## Quality Standards

Maintains Phase 1's exceptional quality standards:
- **Data integrity**: 100% of input records transformed
- **OCL compliance**: Valid JSON-lines format
- **Performance**: <30 seconds processing time
- **Error rate**: Zero critical errors

## Next Steps

1. Complete remaining transformer implementations
2. Integrate multi-language processing  
3. Comprehensive testing and validation
4. Performance optimization and benchmarking
5. Generate production-ready output files
6. Phase 3 handoff preparation

Built on Phase 1's world-class foundation: 30 files, 3.2M+ records, zero errors, <30 seconds.
'''
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("   ✅ README.md")
    
    return True


def create_development_status(base_dir: Path) -> bool:
    """Create development status tracking file"""
    print("📊 Creating development status file...")
    
    status_path = base_dir / "phase2_concept_creation/DEVELOPMENT_STATUS.json"
    
    status = {
        "phase": "Phase 2: Concept Creation",
        "started": "2025-08-01",
        "target_completion": "2025-09-01",
        "overall_progress": "25%",
        "components": {
            "foundation": {
                "status": "complete",
                "progress": "100%",
                "items": [
                    "OCL data models",
                    "Base transformer class",
                    "Directory structure",
                    "Configuration integration"
                ]
            },
            "transformers": {
                "status": "in_progress", 
                "progress": "25%",
                "items": [
                    {"name": "LOINC Terms", "status": "complete", "records": "104K"},
                    {"name": "LOINC Parts", "status": "planned", "records": "72K"},
                    {"name": "Answer Lists", "status": "planned", "records": "30K"},
                    {"name": "Container Concepts", "status": "planned", "records": "TBD"}
                ]
            },
            "integration": {
                "status": "planned",
                "progress": "0%", 
                "items": [
                    "Multi-language processing",
                    "End-to-end pipeline",
                    "OCL format validation",
                    "Performance optimization"
                ]
            },
            "testing": {
                "status": "planned",
                "progress": "10%",
                "items": [
                    "Unit tests",
                    "Integration tests", 
                    "Performance tests",
                    "Output validation"
                ]
            }
        },
        "metrics": {
            "target_concepts": "180000+",
            "target_processing_time": "<30 seconds",
            "target_memory": "<4GB",
            "supported_languages": 19,
            "expected_output_files": "18-20"
        },
        "next_milestones": [
            "Complete LOINC Parts transformer",
            "Complete Answer Lists transformer", 
            "Integrate multi-language processing",
            "End-to-end testing",
            "Performance benchmarking"
        ]
    }
    
    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=2)
    
    print("   ✅ DEVELOPMENT_STATUS.json")
    return True


def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Set up Phase 2 development structure")
    parser.add_argument('--project-dir', type=str, default='.', 
                       help='Base directory for Phase 2 project (default: current)')
    parser.add_argument('--force', action='store_true',
                       help='Overwrite existing directories and files')
    parser.add_argument('--create-examples', action='store_true',
                       help='Create example configuration files')
    
    args = parser.parse_args()
    
    base_dir = Path(args.project_dir).resolve()
    
    print("🏗️ Setting up Phase 2: Concept Creation Development Environment")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print()
    
    try:
        # Create directory structure
        if not create_directory_structure(base_dir, args.force):
            return 1
        
        # Create Python package files
        if not create_init_files(base_dir):
            return 1
        
        # Create transformer placeholders
        if not create_placeholder_transformers(base_dir):
            return 1
        
        # Create utility modules
        if not create_utility_modules(base_dir):
            return 1
        
        # Create test templates
        if not create_test_templates(base_dir):
            return 1
        
        # Create documentation
        if not create_documentation(base_dir):
            return 1
        
        # Create development status tracking
        if not create_development_status(base_dir):
            return 1
        
        print()
        print("🎉 Phase 2 development environment setup complete!")
        print()
        print("📋 Next steps:")
        print("   1. Review the created directory structure")
        print("   2. Complete the transformer implementations")
        print("   3. Run the test suite")
        print("   4. Execute concept creation process")
        print()
        print("🚀 Ready to continue Phase 2 development!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
