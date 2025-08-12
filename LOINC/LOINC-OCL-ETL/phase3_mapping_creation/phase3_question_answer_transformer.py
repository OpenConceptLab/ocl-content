"""
Question-Answer Mapping Transformer for LOINC to OCL Transformation - Phase 3

Transforms LOINC question-answer relationships from LoincAnswerListLink.csv into
OCL "has answer" mappings between LOINC terms and their answer lists.

Data source: LoincAnswerListLink.csv (29,018 associations from Phase 1)
Target: OCL mappings with map_type "has answer"

Features:
- LOINC question/term → Answer list concept relationships
- Answer list linkage type analysis (PREFERRED, EXAMPLE, etc.)
- Clinical context and workflow metadata preservation
- Comprehensive validation and error handling

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import pandas as pd
from typing import Optional, List, Tuple, Dict, Any
from phase3_mapping_creation.phase3_base_transformer import BaseMappingTransformer
from phase3_mapping_creation.phase3_ocl_models import OCLMapping, LOINCMappingTypes


class QuestionAnswerMappingTransformer(BaseMappingTransformer):
    """
    Transformer for question-answer mappings (LoincAnswerListLink.csv).
    
    Creates "has answer" mappings where:
    - from_concept: LOINC question/term concept (LoincNumber)
    - to_concept: Answer list concept (AnswerListId)
    - map_type: "has answer"
    
    Expected columns in LoincAnswerListLink.csv:
    - LoincNumber: LOINC term identifier  
    - AnswerListId: Answer list identifier (typically LLxxxxx-x format)
    - AnswerListLinkType: Type of linkage (PREFERRED, EXAMPLE, etc.)
    - ApplicableContext: Optional context information
    - AnswerListName: Human-readable name of answer list
    """
    
    def __init__(self, config_manager=None):
        super().__init__(config_manager)
        # Track linkage types for analysis
        self.linkage_type_stats: Dict[str, int] = {}
    
    def get_transformer_name(self) -> str:
        return "Question-Answer Mapping Transformer"
    
    def get_source_file(self) -> str:
        return "LoincAnswerListLink.csv"
    
    def get_mapping_type(self) -> str:
        return "Question-Answer Mappings"
    
    def get_ocl_map_type(self) -> str:
        return LOINCMappingTypes.HAS_ANSWER
    
    def validate_record(self, record: pd.Series) -> Tuple[bool, List[str]]:
        """Validate a LoincAnswerListLink record before transformation"""
        errors = []
        
        # Extract key fields
        loinc_number = str(record.get('LoincNumber', '')).strip()
        answer_list_id = str(record.get('AnswerListId', '')).strip()
        
        # Required field validation
        if not loinc_number or loinc_number == 'nan':
            errors.append("Missing LoincNumber")
        if not answer_list_id or answer_list_id == 'nan':
            errors.append("Missing AnswerListId")
        
        # LOINC code format validation
        if loinc_number and loinc_number != 'nan':
            if not self._is_valid_loinc_format(loinc_number):
                errors.append(f"Invalid LoincNumber format: {loinc_number}")
        
        # Answer list ID format validation (typically LLxxxxx-x)
        if answer_list_id and answer_list_id != 'nan':
            if not self._is_valid_answer_list_format(answer_list_id):
                errors.append(f"Invalid AnswerListId format: {answer_list_id}")
        
        return len(errors) == 0, errors
    
    def _is_valid_loinc_format(self, loinc_code: str) -> bool:
        """Basic LOINC code format validation"""
        if not loinc_code or loinc_code == 'nan':
            return False
        
        # LOINC codes are typically NNNNN-N format
        return len(loinc_code) >= 3 and '-' in loinc_code
    
    def _is_valid_answer_list_format(self, answer_list_id: str) -> bool:
        """Basic answer list ID format validation"""
        if not answer_list_id or answer_list_id == 'nan':
            return False
        
        # Answer list IDs are typically LLxxxxx-x format, but can vary
        # This is a basic check - main validation happens in Phase 1
        return len(answer_list_id) >= 3
    
    def _analyze_linkage_type(self, linkage_type: str) -> Dict[str, Any]:
        """Analyze and categorize linkage type"""
        if not linkage_type or linkage_type == 'nan':
            return {}
        
        linkage_type = linkage_type.strip().upper()
        
        # Track statistics
        if linkage_type not in self.linkage_type_stats:
            self.linkage_type_stats[linkage_type] = 0
        self.linkage_type_stats[linkage_type] += 1
        
        # Categorize linkage type
        analysis = {
            'raw_type': linkage_type,
            'category': 'OTHER'
        }
        
        if 'PREFERRED' in linkage_type:
            analysis['category'] = 'PREFERRED'
        elif 'EXAMPLE' in linkage_type:
            analysis['category'] = 'EXAMPLE'
        elif 'RECOMMENDED' in linkage_type:
            analysis['category'] = 'RECOMMENDED'
        elif 'DISCOURAGED' in linkage_type:
            analysis['category'] = 'DISCOURAGED'
        
        return analysis
    
    def transform_record(self, record: pd.Series) -> Optional[OCLMapping]:
        """
        Transform a LoincAnswerListLink record into a "has answer" mapping.
        
        Args:
            record: Pandas Series containing LoincAnswerListLink data
            
        Returns:
            OCLMapping object or None if record should be skipped
        """
        try:
            # Extract key fields
            loinc_number = str(record.get('LoincNumber', '')).strip()
            answer_list_id = str(record.get('AnswerListId', '')).strip()
            
            # Get concept URLs from cache
            from_concept_url = self.get_concept_url(loinc_number)
            to_concept_url = self.get_concept_url(answer_list_id)
            
            if not from_concept_url:
                self.logger.debug(f"LOINC concept URL not found: {loinc_number}")
                self.stats['from_concept_missing'] += 1
                return None
            
            if not to_concept_url:
                self.logger.debug(f"Answer list concept URL not found: {answer_list_id}")
                self.stats['to_concept_missing'] += 1
                return None
            
            # Build extras with answer link metadata
            extras = {}
            
            # Answer list linkage type analysis
            if 'AnswerListLinkType' in record and pd.notna(record['AnswerListLinkType']):
                linkage_type = str(record['AnswerListLinkType']).strip()
                if linkage_type and linkage_type != 'nan':
                    extras['answer_list_link_type'] = linkage_type
                    
                    # Add linkage analysis
                    linkage_analysis = self._analyze_linkage_type(linkage_type)
                    if linkage_analysis:
                        extras['linkage_category'] = linkage_analysis['category']
            
            # Applicable context (parent panel information)
            if 'ApplicableContext' in record and pd.notna(record['ApplicableContext']):
                context = str(record['ApplicableContext']).strip()
                if context and context != 'nan':
                    extras['applicable_context'] = context
            
            # Answer list name for reference
            if 'AnswerListName' in record and pd.notna(record['AnswerListName']):
                name = str(record['AnswerListName']).strip()
                if name and name != 'nan':
                    extras['answer_list_name'] = name
            
            # LOINC long common name for reference
            if 'LongCommonName' in record and pd.notna(record['LongCommonName']):
                long_name = str(record['LongCommonName']).strip()
                if long_name and long_name != 'nan':
                    extras['loinc_long_common_name'] = long_name
            
            # ExtCodeId (external code identifier)
            if 'ExtCodeId' in record and pd.notna(record['ExtCodeId']):
                ext_code = str(record['ExtCodeId']).strip()
                if ext_code and ext_code != 'nan':
                    extras['external_code_id'] = ext_code
            
            # Add source codes for reference
            extras['loinc_number'] = loinc_number
            extras['answer_list_id'] = answer_list_id
            
            # Create mapping
            mapping = OCLMapping(
                map_type=self.get_ocl_map_type(),
                from_concept_url=from_concept_url,
                to_concept_url=to_concept_url,
                external_id=f"answer_{loinc_number}_{answer_list_id}",
                extras=extras
            )
            
            return mapping
            
        except Exception as e:
            self.logger.error(f"Error transforming answer link record: {str(e)}")
            return None
    
    def run_transformation(self, limit=None, progress_callback=None):
        """Override to include linkage type statistics"""
        result = super().run_transformation(limit, progress_callback)
        
        # Add linkage type statistics to result
        if hasattr(result, 'statistics'):
            result.statistics['linkage_types'] = self.linkage_type_stats.copy()
        
        return result


def main():
    """Main function for testing question-answer transformation"""
    import argparse
    import logging
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Question-Answer Mapping Transformer")
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
        transformer = QuestionAnswerMappingTransformer()
        
        # Run transformation
        result = transformer.run_transformation(limit=args.limit)
        
        if result.mappings_created:
            # Write output files
            from phase3_mapping_creation.phase3_ocl_models import MappingCollection
            
            collection = MappingCollection()
            result.add_to_collection(collection)
            
            output_dir = Path(args.output_dir)
            output_files = collection.write_jsonl_files(output_dir, base_filename="question_answer_mappings")
            
            # Print summary
            logger.info(f"\n🎉 Question-Answer Mapping Transformation Completed!")
            logger.info(f"Records processed: {result.source_records_processed:,}")
            logger.info(f"Mappings created: {result.success_count:,}")
            logger.info(f"Processing time: {result.processing_time:.1f} seconds")
            logger.info(f"Success rate: {result.success_rate:.1f}%")
            logger.info(f"Errors: {result.error_count}")
            
            # Show linkage type analysis
            if 'linkage_types' in result.statistics:
                logger.info(f"\nLinkage Types Found:")
                for link_type, count in result.statistics['linkage_types'].items():
                    logger.info(f"  {link_type}: {count:,}")
            
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
