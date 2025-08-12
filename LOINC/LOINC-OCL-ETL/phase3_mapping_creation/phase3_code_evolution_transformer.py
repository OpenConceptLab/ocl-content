"""
Code Evolution Mapping Transformer for LOINC to OCL Transformation - Phase 3

Transforms LOINC code evolution relationships from MapTo.csv into
OCL "Map To" mappings between deprecated and current LOINC codes.

Data source: MapTo.csv (4,643 mappings from Phase 1)
Target: OCL mappings with map_type "Map To"

Features:
- Deprecated/old LOINC → Current/new LOINC relationships
- Comment analysis for evolution type categorization
- Historical change tracking and metadata preservation
- Comprehensive validation and error handling

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

import pandas as pd
from typing import Optional, List, Tuple, Dict, Any
from phase3_mapping_creation.phase3_base_transformer import BaseMappingTransformer
from phase3_mapping_creation.phase3_ocl_models import OCLMapping, LOINCMappingTypes


class CodeEvolutionMappingTransformer(BaseMappingTransformer):
    """
    Transformer for code evolution mappings (MapTo.csv).
    
    Creates "Map To" mappings where:
    - from_concept: Deprecated/old LOINC concept (LOINC_NUM)
    - to_concept: Current/new LOINC concept (MAP_TO)
    - map_type: "Map To"
    
    Expected columns in MapTo.csv:
    - LOINC_NUM: Original/deprecated LOINC code
    - MAP_TO: Target/current LOINC code
    - COMMENT: Optional comment about the mapping reason
    """
    
    def __init__(self, config_manager=None):
        super().__init__(config_manager)
        # Track evolution types for analysis
        self.evolution_type_stats: Dict[str, int] = {}
        self.comment_analysis_stats = {
            'has_comment': 0,
            'no_comment': 0,
            'comment_types': {}
        }
    
    def get_transformer_name(self) -> str:
        return "Code Evolution Mapping Transformer"
    
    def get_source_file(self) -> str:
        return "MapTo.csv"
    
    def get_mapping_type(self) -> str:
        return "Code Evolution Mappings"
    
    def get_ocl_map_type(self) -> str:
        return LOINCMappingTypes.MAP_TO
    
    def validate_record(self, record: pd.Series) -> Tuple[bool, List[str]]:
        """Validate a MapTo record before transformation"""
        errors = []
        
        # Extract key fields - FIXED: Use 'LOINC' not 'LOINC_NUM'
        from_loinc = str(record.get('LOINC', '')).strip()  # FIXED: 'LOINC' not 'LOINC_NUM'
        to_loinc = str(record.get('MAP_TO', '')).strip()
        
        # Required field validation
        if not from_loinc or from_loinc == 'nan':
            errors.append("Missing LOINC (from concept)")  # FIXED: Error message
        if not to_loinc or to_loinc == 'nan':
            errors.append("Missing MAP_TO (to concept)")
        
        # Self-reference validation
        if from_loinc == to_loinc:
            errors.append("LOINC and MAP_TO cannot be the same (circular reference)")  # FIXED: Error message
        
        # LOINC code format validation (basic)
        if from_loinc and from_loinc != 'nan':
            if not self._is_valid_loinc_format(from_loinc):
                errors.append(f"Invalid LOINC format: {from_loinc}")  # FIXED: Error message
        
        if to_loinc and to_loinc != 'nan':
            if not self._is_valid_loinc_format(to_loinc):
                errors.append(f"Invalid MAP_TO format: {to_loinc}")
        
        return len(errors) == 0, errors
    
    def _is_valid_loinc_format(self, loinc_code: str) -> bool:
        """Basic LOINC code format validation"""
        if not loinc_code or loinc_code == 'nan':
            return False
        
        # LOINC codes are typically NNNNN-N format
        return len(loinc_code) >= 3 and '-' in loinc_code
    
    def _analyze_comment(self, comment: str) -> Dict[str, Any]:
        """Analyze comment content for evolution type categorization"""
        if not comment or comment.strip() == 'nan':
            return {}
        
        comment_lower = comment.lower().strip()
        analysis = {
            'length': len(comment),
            'categories': []
        }
        
        # Categorize common evolution types based on comment content
        evolution_categories = []
        
        # Deprecation patterns
        if any(word in comment_lower for word in ['deprecated', 'retire', 'obsolete', 'discontinue']):
            evolution_categories.append('deprecation')
        
        # Replacement patterns
        if any(word in comment_lower for word in ['replace', 'supersede', 'substitute', 'update']):
            evolution_categories.append('replacement')
        
        # Consolidation patterns
        if any(word in comment_lower for word in ['merge', 'combine', 'consolidate', 'unified']):
            evolution_categories.append('consolidation')
        
        # Division patterns
        if any(word in comment_lower for word in ['split', 'separate', 'divide', 'broken into']):
            evolution_categories.append('division')
        
        # Naming patterns
        if any(word in comment_lower for word in ['rename', 'name change', 'title', 'naming']):
            evolution_categories.append('naming')
        
        # Correction patterns
        if any(word in comment_lower for word in ['error', 'mistake', 'correct', 'fix']):
            evolution_categories.append('correction')
        
        # Clarification patterns
        if any(word in comment_lower for word in ['clarif', 'specify', 'precision', 'disambiguat']):
            evolution_categories.append('clarification')
        
        # Standardization patterns
        if any(word in comment_lower for word in ['standard', 'conform', 'align', 'harmoniz']):
            evolution_categories.append('standardization')
        
        analysis['categories'] = evolution_categories
        
        # Track statistics
        for category in evolution_categories:
            if category not in self.evolution_type_stats:
                self.evolution_type_stats[category] = 0
            self.evolution_type_stats[category] += 1
            
            if category not in self.comment_analysis_stats['comment_types']:
                self.comment_analysis_stats['comment_types'][category] = 0
            self.comment_analysis_stats['comment_types'][category] += 1
        
        return analysis
    
    def transform_record(self, record: pd.Series) -> Optional[OCLMapping]:
        """Transform a MapTo record into a "Map To" mapping."""
        try:
            # Extract key fields - FIXED: Use 'LOINC' not 'LOINC_NUM'
            from_loinc = str(record.get('LOINC', '')).strip()  # FIXED: 'LOINC' not 'LOINC_NUM'
            to_loinc = str(record.get('MAP_TO', '')).strip()
            
            # Get concept URLs from cache
            from_concept_url = self.get_concept_url(from_loinc)
            to_concept_url = self.get_concept_url(to_loinc)
            
            if not from_concept_url:
                self.logger.debug(f"From concept URL not found: {from_loinc}")
                self.stats['from_concept_missing'] += 1
                return None
            
            if not to_concept_url:
                self.logger.debug(f"To concept URL not found: {to_loinc}")
                self.stats['to_concept_missing'] += 1
                return None
            
            # Build extras with evolution metadata
            extras = {}
            
            # Comment analysis and preservation
            if 'COMMENT' in record and pd.notna(record['COMMENT']):
                comment_text = str(record['COMMENT']).strip()
                if comment_text and comment_text != 'nan':
                    extras['comment'] = comment_text
                    self.comment_analysis_stats['has_comment'] += 1
                    
                    # Analyze comment for categorization
                    comment_analysis = self._analyze_comment(comment_text)
                    if comment_analysis.get('categories'):
                        extras['evolution_type'] = comment_analysis['categories']
                        extras['evolution_primary_type'] = comment_analysis['categories'][0]  # Primary type
                else:
                    self.comment_analysis_stats['no_comment'] += 1
            else:
                self.comment_analysis_stats['no_comment'] += 1
            
            # Evolution direction metadata
            extras['evolution_direction'] = 'deprecated_to_current'
            extras['deprecated_loinc'] = from_loinc
            extras['current_loinc'] = to_loinc
            
            # Create the mapping
            mapping = OCLMapping(
                map_type=self.get_ocl_map_type(),
                from_concept_url=from_concept_url,
                to_concept_url=to_concept_url,
                external_id=f"evolution_{from_loinc}_{to_loinc}",
                extras=extras
            )
            
            return mapping
            
        except Exception as e:
            self.logger.error(f"Failed to transform record {record.get('LOINC', 'unknown')}: {e}")
            return None
    
    def run_transformation(self, limit=None, progress_callback=None):
        """Override to include evolution type statistics"""
        result = super().run_transformation(limit, progress_callback)
        
        # Add evolution analysis statistics to result
        if hasattr(result, 'statistics'):
            result.statistics['evolution_types'] = self.evolution_type_stats.copy()
            result.statistics['comment_analysis'] = self.comment_analysis_stats.copy()
        
        return result


def main():
    """Main function for testing code evolution transformation"""
    import argparse
    import logging
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Code Evolution Mapping Transformer")
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
        transformer = CodeEvolutionMappingTransformer()
        
        # Run transformation
        result = transformer.run_transformation(limit=args.limit)
        
        if result.mappings_created:
            # Write output files
            from phase3_mapping_creation.phase3_ocl_models import MappingCollection
            
            collection = MappingCollection()
            result.add_to_collection(collection)
            
            output_dir = Path(args.output_dir)
            output_files = collection.write_jsonl_files(output_dir, base_filename="code_evolution_mappings")
            
            # Print summary
            logger.info(f"\n🎉 Code Evolution Mapping Transformation Completed!")
            logger.info(f"Records processed: {result.source_records_processed:,}")
            logger.info(f"Mappings created: {result.success_count:,}")
            logger.info(f"Processing time: {result.processing_time:.1f} seconds")
            logger.info(f"Success rate: {result.success_rate:.1f}%")
            logger.info(f"Errors: {result.error_count}")
            
            # Show comment analysis
            if 'comment_analysis' in result.statistics:
                stats = result.statistics['comment_analysis']
                logger.info(f"\nComment Analysis:")
                logger.info(f"  Records with comments: {stats['has_comment']:,}")
                logger.info(f"  Records without comments: {stats['no_comment']:,}")
            
            # Show evolution type analysis
            if 'evolution_types' in result.statistics:
                logger.info(f"\nEvolution Types Found:")
                for evo_type, count in result.statistics['evolution_types'].items():
                    logger.info(f"  {evo_type}: {count:,}")
            
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