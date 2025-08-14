"""
Panel-Test Mapping Transformer for LOINC to OCL Transformation - Phase 3

Transforms LOINC panel structure relationships from PanelsAndForms.csv into
OCL "has element" mappings between panel concepts and their component tests.

Data source: PanelsAndForms.csv (91,993 relationships from Phase 1)
Target: OCL mappings with map_type "has element"

Features:
- Panel LOINC concept → Component test concept relationships
- Sequence preservation for panel ordering
- Comprehensive validation and error handling
- Batch processing with progress tracking

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import pandas as pd
from typing import Optional, List, Tuple
from phase3_mapping_creation.phase3_base_transformer import BaseMappingTransformer
from phase3_mapping_creation.phase3_ocl_models import OCLMapping, LOINCMappingTypes


class PanelTestMappingTransformer(BaseMappingTransformer):
    """
    Transformer for panel-to-test mappings (PanelsAndForms.csv).
    
    Creates "has element" mappings where:
    - from_concept: Panel LOINC concept (ParentLoinc)
    - to_concept: Test LOINC concept (ChildLoinc)  
    - map_type: "has element"
    
    Expected columns in PanelsAndForms.csv:
    - ParentLoinc: Panel LOINC code
    - ChildLoinc: Component test LOINC code
    - Sequence: Optional ordering within panel
    - Additional metadata available in extras
    """
    
    def get_transformer_name(self) -> str:
        return "Panel-Test Mapping Transformer"
    
    def get_source_file(self) -> str:
        return "PanelsAndForms.csv"
    
    def get_mapping_type(self) -> str:
        return "Panel Structure Mappings"
    
    def get_ocl_map_type(self) -> str:
        return LOINCMappingTypes.HAS_ELEMENT
    
    def validate_record(self, record: pd.Series) -> Tuple[bool, List[str]]:
        """Validate a PanelsAndForms record before transformation"""
        errors = []
        
        # Extract key fields - FIXED: Use 'Loinc' not 'ChildLoinc'
        parent_loinc = str(record.get('ParentLoinc', '')).strip()
        child_loinc = str(record.get('Loinc', '')).strip()  # FIXED: 'Loinc' not 'ChildLoinc'
        
        # Required field validation
        if not parent_loinc or parent_loinc == 'nan':
            errors.append("Missing ParentLoinc")
        if not child_loinc or child_loinc == 'nan':
            errors.append("Missing Loinc")  # FIXED: Error message
        
        # Self-reference validation
        if parent_loinc == child_loinc:
            errors.append("ParentLoinc and Loinc cannot be the same")
        
        # LOINC code format validation (basic)
        if parent_loinc and parent_loinc != 'nan':
            if not self._is_valid_loinc_format(parent_loinc):
                errors.append(f"Invalid ParentLoinc format: {parent_loinc}")
        
        if child_loinc and child_loinc != 'nan':
            if not self._is_valid_loinc_format(child_loinc):
                errors.append(f"Invalid Loinc format: {child_loinc}")  # FIXED: Error message
        
        return len(errors) == 0, errors
    
    def _is_valid_loinc_format(self, loinc_code: str) -> bool:
        """Basic LOINC code format validation"""
        if not loinc_code or loinc_code == 'nan':
            return False
        
        # LOINC codes are typically NNNNN-N format, but can vary
        # This is a basic check - the main validation happens in Phase 1
        return len(loinc_code) >= 3 and '-' in loinc_code
    
    def transform_record(self, record: pd.Series) -> Optional[OCLMapping]:
        """Transform a PanelsAndForms record into a "has element" mapping."""
        try:
            # Extract key fields - FIXED: Use 'Loinc' not 'ChildLoinc'
            parent_loinc = str(record.get('ParentLoinc', '')).strip()
            child_loinc = str(record.get('Loinc', '')).strip()  # FIXED: 'Loinc' not 'ChildLoinc'
            
            # Get concept URLs from cache
            from_concept_url = self.get_concept_url(parent_loinc)
            to_concept_url = self.get_concept_url(child_loinc)
            
            if not from_concept_url:
                self.logger.debug(f"Parent concept URL not found: {parent_loinc}")
                self.stats['from_concept_missing'] += 1
                return None
            
            if not to_concept_url:
                self.logger.debug(f"Child concept URL not found: {child_loinc}")
                self.stats['to_concept_missing'] += 1
                return None
            
            # Build extras with panel metadata
            extras = {}
            
            # Sequence information for panel ordering - FIXED: Use correct column name
            if 'SEQUENCE' in record and pd.notna(record['SEQUENCE']):  # FIXED: 'SEQUENCE' not 'Sequence'
                try:
                    sequence = str(record['SEQUENCE']).strip()
                    if sequence and sequence != 'nan':
                        extras['sequence'] = sequence
                except Exception as e:
                    self.logger.debug(f"Error processing sequence for {parent_loinc}->{child_loinc}: {e}")
            
            # Panel context information
            if 'ParentName' in record and pd.notna(record['ParentName']):
                panel_name = str(record['ParentName']).strip()
                if panel_name and panel_name != 'nan':
                    extras['panel_name'] = panel_name
            
            if 'LoincName' in record and pd.notna(record['LoincName']):
                component_name = str(record['LoincName']).strip()
                if component_name and component_name != 'nan':
                    extras['component_name'] = component_name
            
            # Create the mapping
            mapping = OCLMapping(
                map_type=self.get_ocl_map_type(),
                from_concept_url=from_concept_url,
                to_concept_url=to_concept_url,
                external_id=f"panel_{parent_loinc}_{child_loinc}",
                extras=extras
            )
            
            return mapping
            
        except Exception as e:
            self.logger.error(f"Failed to transform record {record.get('ParentLoinc', 'unknown')}: {e}")
            return None

def main():
    """Main function for testing panel-test transformation"""
    import argparse
    import logging
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Panel-Test Mapping Transformer")
    parser.add_argument('--limit', type=int, help='Limit number of records to process (for testing)')
    parser.add_argument('--output-dir', type=str, default='output/phase3_mappings',
                       help='Output directory for mapping files')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create transformer
        transformer = PanelTestMappingTransformer()
        
        # Run transformation
        result = transformer.run_transformation(limit=args.limit)
        
        if result.mappings_created:
            # Write output files
            from phase3_mapping_creation.phase3_ocl_models import MappingCollection
            
            collection = MappingCollection()
            result.add_to_collection(collection)
            
            output_dir = Path(args.output_dir)
            output_files = collection.write_jsonl_files(output_dir, base_filename="panel_test_mappings")
            
            # Print summary
            logger.info(f"\n🎉 Panel-Test Mapping Transformation Completed!")
            logger.info(f"Records processed: {result.source_records_processed:,}")
            logger.info(f"Mappings created: {result.success_count:,}")
            logger.info(f"Processing time: {result.processing_time:.1f} seconds")
            logger.info(f"Success rate: {result.success_rate:.1f}%")
            logger.info(f"Errors: {result.error_count}")
            logger.info(f"\nOutput files:")
            for file_path in output_files:
                logger.info(f"  {file_path}")
        else:
            logger.error("No mappings were created")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Transformation failed: {str(e)}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)