#!/usr/bin/env python3
"""
Quick Debug Script - Dataset Name Discovery

Helps identify the actual dataset names that Phase 1 DataLoader produces
so we can map them correctly in Phase 2 transformers.

Usage:
    python debug_datasets.py
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from phase1_2_data_processing.config_manager import ConfigManager
    from phase1_2_data_processing.data_loader import DataLoader
    from phase1_2_data_processing.logger import TransformationLogger
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def debug_dataset_names():
    """Debug what dataset names Phase 1 actually produces"""
    print("🔍 Phase 1 Dataset Name Discovery")
    print("=" * 50)
    
    try:
        # Initialize configuration
        print("Loading configuration...")
        config_manager = ConfigManager()
        
        if not config_manager.load_all_configs():
            print("❌ Failed to load configuration")
            return
        
        print("✅ Configuration loaded")
        
        # Initialize data loader
        print("\nLoading Phase 1 data...")
        data_loader = DataLoader()
        
        # Load data (without validation for speed)
        loading_summary = data_loader.load_all_data(
            validate_data=False,
            create_cross_refs=False  # Skip cross-refs for speed
        )
        
        if not loading_summary.is_successful:
            print("❌ Failed to load Phase 1 data")
            return
        
        print(f"✅ Loaded {loading_summary.total_rows_loaded:,} records from {loading_summary.total_files_processed} files")
        
        # Analyze datasets
        print(f"\n📊 Dataset Analysis ({len(loading_summary.datasets)} datasets):")
        print("-" * 80)
        print(f"{'Dataset Name':<30} {'Records':<10} {'Columns':<8} {'Key Columns (first 5)'}")
        print("-" * 80)
        
        # Sort by record count (largest first)
        datasets_by_size = sorted(
            loading_summary.datasets.items(),
            key=lambda x: getattr(x[1], 'row_count', 0),
            reverse=True
        )
        
        candidates = {
            'loinc_terms': [],
            'loinc_parts': [],
            'answer_lists': []
        }
        
        for dataset_name, dataset in datasets_by_size:
            row_count = getattr(dataset, 'row_count', 0)
            
            # Get column info
            if hasattr(dataset, 'data') and hasattr(dataset.data, 'columns'):
                columns = list(dataset.data.columns)
                column_count = len(columns)
                key_columns = ', '.join(columns[:5])
            else:
                columns = []
                column_count = 0
                key_columns = "N/A"
            
            print(f"{dataset_name:<30} {row_count:<10,} {column_count:<8} {key_columns}")
            
            # Categorize likely candidates
            name_lower = dataset_name.lower()
            
            # LOINC Terms candidates (large datasets with LOINC in name)
            if ('loinc' in name_lower and 
                row_count > 50000 and 
                'part' not in name_lower and 
                'answer' not in name_lower and
                'link' not in name_lower):
                candidates['loinc_terms'].append((dataset_name, row_count))
            
            # LOINC Parts candidates
            elif 'part' in name_lower and row_count > 1000:
                candidates['loinc_parts'].append((dataset_name, row_count))
            
            # Answer Lists candidates  
            elif 'answer' in name_lower and row_count > 100:
                candidates['answer_lists'].append((dataset_name, row_count))
        
        # Show recommendations
        print(f"\n🎯 Recommended Dataset Mappings:")
        print("-" * 50)
        
        for category, dataset_list in candidates.items():
            if dataset_list:
                # Sort by size and recommend the largest
                dataset_list.sort(key=lambda x: x[1], reverse=True)
                recommended = dataset_list[0]
                print(f"{category:<15}: {recommended[0]} ({recommended[1]:,} records)")
                
                if len(dataset_list) > 1:
                    print(f"                 Alternatives: {[name for name, _ in dataset_list[1:]]}")
            else:
                print(f"{category:<15}: ❌ No candidates found")
        
        print(f"\n📋 Column Analysis for Top Candidates:")
        print("-" * 50)
        
        # Show detailed column info for likely LOINC terms dataset
        if candidates['loinc_terms']:
            main_dataset_name = candidates['loinc_terms'][0][0]
            dataset = loading_summary.datasets[main_dataset_name]
            
            if hasattr(dataset, 'data') and hasattr(dataset.data, 'columns'):
                columns = list(dataset.data.columns)
                print(f"\n{main_dataset_name} columns ({len(columns)} total):")
                
                # Look for key LOINC columns
                key_columns = ['LOINC_NUM', 'LONG_COMMON_NAME', 'COMPONENT', 'PROPERTY', 'SYSTEM', 'CLASS']
                found_columns = [col for col in key_columns if col in columns]
                missing_columns = [col for col in key_columns if col not in columns]
                
                print(f"  ✅ Found key columns: {found_columns}")
                if missing_columns:
                    print(f"  ❌ Missing key columns: {missing_columns}")
                
                # Show all columns (first 20)
                print(f"  All columns (first 20): {columns[:20]}")
                if len(columns) > 20:
                    print(f"  ... and {len(columns) - 20} more")
        
        print(f"\n✅ Dataset analysis complete!")
        print(f"Use these dataset names in your transformers:")
        for category, dataset_list in candidates.items():
            if dataset_list:
                print(f"  {category}: '{dataset_list[0][0]}'")
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Set up minimal logging
    logger_system = TransformationLogger(log_level="WARNING")  # Minimize noise
    
    debug_dataset_names()
