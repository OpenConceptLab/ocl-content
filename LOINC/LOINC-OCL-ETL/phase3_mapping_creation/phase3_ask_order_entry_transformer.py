"""
Ask at Order Entry Mapping Transformer for LOINC to OCL Transformation - Phase 3

Transforms LOINC order entry workflow relationships from the AskAtOrderEntry field
in the main LOINC table into OCL "Ask At Order Entry" mappings.

Data source: Loinc.csv AskAtOrderEntry field
Target: OCL mappings with map_type "Ask At Order Entry"

Features:
- Test LOINC concept → Common question panel relationships
- Order entry workflow optimization
- Comprehensive validation and error handling
- Batch processing with progress tracking

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import pandas as pd
from typing import Optional, List, Tuple
from phase3_mapping_creation.phase3_base_transformer import BaseMappingTransformer
from phase3_mapping_creation.phase3_ocl_models import OCLMapping, LOINCMappingTypes


class AskAtOrderEntryMappingTransformer(BaseMappingTransformer):
    """
    Transformer for Ask at Order Entry mappings from main LOINC table.
    
    Creates mappings from test codes to common question panels that should
    be asked at order entry to streamline clinical workflow.
    """
    
    def _is_valid_loinc_format(self, loinc_code: str) -> bool:
        """Basic LOINC code format validation"""
        if not loinc_code or loinc_code == 'nan':
            return False
        return len(loinc_code) >= 3 and '-' in loinc_code

    def get_transformer_name(self) -> str:
        """Return the name of this transformer"""
        return "Ask at Order Entry Mapping Transformer"
    
    def get_source_file(self) -> str:
        """Return the source file containing the mapping data"""
        return "Loinc.csv"
    
    def get_mapping_type(self) -> str:
        """Return the human-readable mapping type"""
        return "Ask at Order Entry Mappings"
    
    def get_ocl_map_type(self) -> str:
        """Return the OCL map_type value for this mapping type"""
        return LOINCMappingTypes.ASK_AT_ORDER_ENTRY.value
    
    def get_source_description(self) -> str:
        """Return description of the source data"""
        return "LOINC terms with AskAtOrderEntry field values indicating workflow questions"
    
    def load_source_data(self) -> bool:
        """
        Load and filter LOINC data for records with AskAtOrderEntry values.
        
        Returns:
            bool: True if data loaded successfully
        """
        try:
            # Load main LOINC table through data loader
            if not self.data_loader:
                self.data_loader = self._create_data_loader()
            
            # Load Phase 1 data if not already loaded
            if not hasattr(self.data_loader, 'datasets') or not self.data_loader.datasets:
                self.logger.info("Loading Phase 1 data...")
                self.data_loader.load_all_data()
            
            # Get the main LOINC table
            if 'Loinc.csv' not in self.data_loader.datasets:
                self.logger.error("Loinc.csv not found in Phase 1 data")
                return False
                
            loinc_data = self.data_loader.datasets['Loinc.csv'].data

            if loinc_data is None or loinc_data.empty:
                self.logger.error("Failed to load main LOINC table")
                return False
            
            # Filter for records with non-empty AskAtOrderEntry values
            filtered_data = loinc_data[
                loinc_data['AskAtOrderEntry'].notna() & 
                (loinc_data['AskAtOrderEntry'].str.strip() != '')
            ].copy()
            
            if filtered_data.empty:
                self.logger.warning("No records found with AskAtOrderEntry values")
                return False
            
            self.source_data = filtered_data
            
            self.logger.info(f"Loaded {len(self.source_data):,} LOINC records with AskAtOrderEntry values")
            self.logger.info(f"Sample AskAtOrderEntry values: {self.source_data['AskAtOrderEntry'].dropna().head(3).tolist()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load source data: {e}")
            return False
            
    def validate_source_record(self, record: pd.Series) -> Tuple[bool, List[str]]:
        """
        Validate a source record for mapping creation.
        
        Args:
            record: Source data record
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        if pd.isna(record.get('LOINC_NUM')):
            issues.append("Missing LOINC_NUM")
        
        if pd.isna(record.get('AskAtOrderEntry')) or str(record.get('AskAtOrderEntry')).strip() == '':
            issues.append("Missing or empty AskAtOrderEntry")
        
        # Validate LOINC_NUM format
        loinc_num = str(record.get('LOINC_NUM', ''))
        if loinc_num and not self._is_valid_loinc_format(loinc_num):
            issues.append(f"Invalid LOINC format: {loinc_num}")
        
        return len(issues) == 0, issues
    
    def transform_record(self, record: pd.Series) -> Optional[OCLMapping]:
        """
        Transform a single LOINC record with AskAtOrderEntry into an OCL mapping.
        
        Args:
            record: Source LOINC record
            
        Returns:
            OCLMapping object or None if transformation failed
        """
        try:
            # Extract key fields
            from_loinc = str(record['LOINC_NUM']).strip()
            ask_at_order_entry = str(record['AskAtOrderEntry']).strip()
            
            # Parse the AskAtOrderEntry field to extract target LOINC(s)
            # This field may contain multiple LOINC codes separated by semicolons
            target_loincs = self._parse_ask_at_order_entry_field(ask_at_order_entry)
            
            if not target_loincs:
                self.logger.warning(f"Could not parse AskAtOrderEntry value: {ask_at_order_entry}")
                return None
            
            # For now, create mapping to the first target (could be enhanced to create multiple mappings)
            to_loinc = target_loincs[0]
            
            # Get concept URLs
            from_url = self.get_concept_url(from_loinc)
            to_url = self.get_concept_url(to_loinc)
            
            if not from_url or not to_url:
                missing_concepts = []
                if not from_url:
                    missing_concepts.append(f"from:{from_loinc}")
                if not to_url:
                    missing_concepts.append(f"to:{to_loinc}")
                self.logger.warning(f"Missing concept URLs for {', '.join(missing_concepts)}")
                return None
            
            # Create mapping
            mapping = OCLMapping(
                map_type=self.get_ocl_map_type(),
                from_concept_url=from_url,
                to_concept_url=to_url,
                external_id=f"ask_order_entry_{from_loinc}_{to_loinc}",
                extras={
                    "original_ask_at_order_entry": ask_at_order_entry,
                    "workflow_type": "order_entry",
                    "all_targets": target_loincs if len(target_loincs) > 1 else None
                }
            )
            
            if mapping and isinstance(mapping, OCLMapping):
                return mapping
            else:
                self.logger.warning(f"Transform returned invalid object type: {type(mapping)}")
                return None            
        except Exception as e:
            self.logger.error(f"Failed to transform record {record.get('LOINC_NUM', 'unknown')}: {e}")
            return None
    
    def _parse_ask_at_order_entry_field(self, ask_at_order_entry: str) -> List[str]:
        """
        Parse the AskAtOrderEntry field to extract target LOINC codes.
        
        Args:
            ask_at_order_entry: Raw field value
            
        Returns:
            List of target LOINC codes
        """
        if not ask_at_order_entry or ask_at_order_entry.strip() == '':
            return []
        
        # Common patterns in AskAtOrderEntry field:
        # - Single LOINC code: "12345-6"
        # - Multiple codes: "12345-6;67890-1"
        # - Text with LOINC codes: "Ask about: 12345-6"
        # - Panel references: "Panel 12345-6"
        
        import re
        
        # Extract LOINC-format codes from the field
        loinc_pattern = r'\b\d{1,5}-\d{1,2}\b'
        found_codes = re.findall(loinc_pattern, ask_at_order_entry)
        
        # Validate and clean the codes
        valid_codes = []
        for code in found_codes:
            if self._is_valid_loinc_format(code):
                valid_codes.append(code)
        
        return valid_codes
    
    def get_statistics_summary(self) -> dict:
        """Return transformer-specific statistics"""
        base_stats = super().get_statistics_summary()
        
        # Add Ask at Order Entry specific statistics
        if self.source_data is not None:
            base_stats.update({
                'unique_ask_at_order_entry_patterns': len(self.source_data['AskAtOrderEntry'].dropna().unique()),
                'records_with_multiple_targets': len(self.source_data[
                    self.source_data['AskAtOrderEntry'].str.contains(';', na=False)
                ]) if not self.source_data.empty else 0
            })
        
        return base_stats


# For standalone testing
if __name__ == "__main__":
    import sys
    import logging
    from pathlib import Path
    
    # Setup logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Create and test transformer
    transformer = AskAtOrderEntryMappingTransformer()
    
    print(f"🔧 Testing {transformer.get_transformer_name()}")
    print(f"Source: {transformer.get_source_file()}")
    print(f"Mapping Type: {transformer.get_mapping_type()}")
    print(f"OCL Map Type: {transformer.get_ocl_map_type()}")
    
    # Test with small limit
    try:
        result = transformer.run_transformation(limit=10)
        
        print(f"\n📊 Test Results:")
        print(f"Records processed: {result.source_records_processed}")
        print(f"Mappings created: {result.success_count}")
        print(f"Success rate: {result.success_rate:.1f}%")
        
        if result.success_count > 0:
            print(f"\n✅ Sample mapping:")
            sample_mapping = result.mappings_created[0]
            print(f"  From: {sample_mapping.from_concept_url}")
            print(f"  To: {sample_mapping.to_concept_url}")
            print(f"  Type: {sample_mapping.map_type}")
            print(f"  ID: {sample_mapping.external_id}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    
    print("✅ Transformer test completed successfully")
