"""
Associated Observations Mapping Transformer for LOINC to OCL Transformation - Phase 3

Transforms LOINC clinical workflow relationships from the AssociatedObservations field
in the main LOINC table into OCL "Associated Observation" mappings.

Data source: Loinc.csv AssociatedObservations field
Target: OCL mappings with map_type "Associated Observation"

Features:
- Test LOINC concept → Related clinical measure relationships
- Clinical workflow optimization
- Comprehensive validation and error handling
- Batch processing with progress tracking

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import pandas as pd
from typing import Optional, List, Tuple
from phase3_mapping_creation.phase3_base_transformer import BaseMappingTransformer
from phase3_mapping_creation.phase3_ocl_models import OCLMapping, LOINCMappingTypes


class AssociatedObservationsMappingTransformer(BaseMappingTransformer):
    """
    Transformer for Associated Observations mappings from main LOINC table.
    
    Creates mappings from test codes to related clinical measures that are
    commonly observed together for comprehensive patient care.
    """
    def _is_valid_loinc_format(self, loinc_code: str) -> bool:
        """Basic LOINC code format validation"""
        if not loinc_code or loinc_code == 'nan':
            return False
        
        # LOINC codes are typically NNNNN-N format
        return len(loinc_code) >= 3 and '-' in loinc_code

    def get_transformer_name(self) -> str:
        """Return the name of this transformer"""
        return "Associated Observations Mapping Transformer"
    
    def get_source_file(self) -> str:
        """Return the source file containing the mapping data"""
        return "Loinc.csv"
    
    def get_mapping_type(self) -> str:
        """Return the human-readable mapping type"""
        return "Associated Observations Mappings"
    
    def get_ocl_map_type(self) -> str:
        """Return the OCL map_type value for this mapping type"""
        return LOINCMappingTypes.ASSOCIATED_OBSERVATION.value
    
    def get_source_description(self) -> str:
        """Return description of the source data"""
        return "LOINC terms with AssociatedObservations field values indicating related clinical measures"
    
    def load_source_data(self) -> bool:
        """
        Load and filter LOINC data for records with AssociatedObservations values.
        
        Returns:
            bool: True if data loaded successfully
        """
        try:
            # Load main LOINC table through data loader
            if not self.data_loader:
                from phase1_2_data_processing.data_loader import DataLoader
                self.data_loader = DataLoader()
            
            if not hasattr(self.data_loader, 'datasets') or not self.data_loader.datasets:
                self.logger.info("Loading Phase 1 data...")
                self.data_loader.load_all_data()
            
            # Get the main LOINC table
            if 'Loinc.csv' not in self.data_loader.datasets:
                self.logger.error("Loinc.csv not found in Phase 1 data")
                return False
                
            dataset = self.data_loader.datasets['Loinc.csv']
            if 'Loinc.csv' not in self.data_loader.datasets:
                self.logger.error("Loinc.csv not found in loaded datasets")
                return False

            loinc_data = self.data_loader.datasets['Loinc.csv'].data
            
            if loinc_data is None or loinc_data.empty:
                self.logger.error("Failed to load main LOINC table")
                return False
            
            # Filter for records with non-empty AssociatedObservations values
            filtered_data = loinc_data[
                loinc_data['AssociatedObservations'].notna() & 
                (loinc_data['AssociatedObservations'].str.strip() != '')
            ].copy()
            
            if filtered_data.empty:
                self.logger.warning("No records found with AssociatedObservations values")
                return False
            
            self.source_data = filtered_data
            
            self.logger.info(f"Loaded {len(self.source_data):,} LOINC records with AssociatedObservations values")
            self.logger.info(f"Sample AssociatedObservations values: {self.source_data['AssociatedObservations'].dropna().head(3).tolist()}")
            
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
        
        if pd.isna(record.get('AssociatedObservations')) or str(record.get('AssociatedObservations')).strip() == '':
            issues.append("Missing or empty AssociatedObservations")
        
        # Validate LOINC_NUM format
        loinc_num = str(record.get('LOINC_NUM', ''))
        if loinc_num and not self._is_valid_loinc_format(loinc_num):
            issues.append(f"Invalid LOINC format: {loinc_num}")
        
        return len(issues) == 0, issues
    
    def transform_record(self, record: pd.Series) -> Optional[OCLMapping]:
        """
        Transform a single LOINC record with AssociatedObservations into an OCL mapping.
        
        Args:
            record: Source LOINC record
            
        Returns:
            OCLMapping object or None if transformation failed
        """
        try:
            # Extract key fields
            from_loinc = str(record['LOINC_NUM']).strip()
            associated_observations = str(record['AssociatedObservations']).strip()
            
            # Parse the AssociatedObservations field to extract target LOINC(s)
            # This field may contain multiple LOINC codes or text descriptions
            target_loincs = self._parse_associated_observations_field(associated_observations)
            
            if not target_loincs:
                self.logger.warning(f"Could not parse AssociatedObservations value: {associated_observations}")
                return None
            
            # For now, create mapping to the first target (could be enhanced to create multiple mappings)
            to_loinc = target_loincs[0]
            
            # Get concept URLs
            from_url = self._get_concept_url(from_loinc)
            to_url = self._get_concept_url(to_loinc)
            
            if not from_url or not to_url:
                missing_concepts = []
                if not from_url:
                    missing_concepts.append(f"from:{from_loinc}")
                if not to_url:
                    missing_concepts.append(f"to:{to_loinc}")
                self.logger.warning(f"Missing concept URLs for {', '.join(missing_concepts)}")
                return None
            
            # Determine relationship type from the field content
            relationship_type = self._analyze_relationship_type(associated_observations)
            
            # Create mapping
            mapping = OCLMapping(
                map_type=self.get_ocl_map_type(),
                from_concept_url=from_url,
                to_concept_url=to_url,
                external_id=f"associated_obs_{from_loinc}_{to_loinc}",
                extras={
                    "original_associated_observations": associated_observations,
                    "relationship_type": relationship_type,
                    "clinical_context": "associated_observation",
                    "all_targets": target_loincs if len(target_loincs) > 1 else None
                }
            )
            
            return mapping
            
        except Exception as e:
            self.logger.error(f"Failed to transform record {record.get('LOINC_NUM', 'unknown')}: {e}")
            return None
    
    def _parse_associated_observations_field(self, associated_observations: str) -> List[str]:
        """
        Parse the AssociatedObservations field to extract target LOINC codes.
        
        Args:
            associated_observations: Raw field value
            
        Returns:
            List of target LOINC codes
        """
        if not associated_observations or associated_observations.strip() == '':
            return []
        
        # Common patterns in AssociatedObservations field:
        # - Single LOINC code: "12345-6"
        # - Multiple codes: "12345-6;67890-1" or "12345-6, 67890-1"
        # - Text with LOINC codes: "Related to: 12345-6"
        # - Descriptive text: "Total protein, Albumin"
        
        import re
        
        # Extract LOINC-format codes from the field
        loinc_pattern = r'\b\d{1,5}-\d{1,2}\b'
        found_codes = re.findall(loinc_pattern, associated_observations)
        
        # Validate and clean the codes
        valid_codes = []
        for code in found_codes:
            if self._is_valid_loinc_format(code):
                valid_codes.append(code)
        
        return valid_codes
    
    def _analyze_relationship_type(self, associated_observations: str) -> str:
        """
        Analyze the AssociatedObservations text to determine relationship type.
        
        Args:
            associated_observations: Raw field value
            
        Returns:
            String describing the relationship type
        """
        text_lower = associated_observations.lower()
        
        # Common relationship patterns
        if any(keyword in text_lower for keyword in ['ratio', 'calculation', 'derived']):
            return "calculated_relationship"
        elif any(keyword in text_lower for keyword in ['panel', 'battery', 'profile']):
            return "panel_relationship"
        elif any(keyword in text_lower for keyword in ['follow-up', 'followup', 'monitoring']):
            return "monitoring_relationship"
        elif any(keyword in text_lower for keyword in ['differential', 'component']):
            return "component_relationship"
        else:
            return "clinical_association"
    
    def get_statistics_summary(self) -> dict:
        """Return transformer-specific statistics"""
        base_stats = super().get_statistics_summary()
        
        # Add Associated Observations specific statistics
        if self.source_data is not None:
            base_stats.update({
                'unique_associated_observations_patterns': len(self.source_data['AssociatedObservations'].dropna().unique()),
                'records_with_multiple_associations': len(self.source_data[
                    self.source_data['AssociatedObservations'].str.contains('[;,]', regex=True, na=False)
                ]) if not self.source_data.empty else 0,
                'records_with_loinc_codes': len(self.source_data[
                    self.source_data['AssociatedObservations'].str.contains(r'\d{1,5}-\d{1,2}', regex=True, na=False)
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
    transformer = AssociatedObservationsMappingTransformer()
    
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