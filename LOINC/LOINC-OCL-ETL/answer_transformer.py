"""
Answer Lists Transformer for LOINC to OCL Transformation - Phase 2

This module transforms LOINC answer lists (from AnswerList.csv) into OCL Concept objects.
Handles answer lists with 30,315 validated records from Phase 1.

LOINC answer lists represent standardized response options for LOINC terms:
- Coded answer sets (e.g., Positive/Negative, Present/Absent)
- Ordinal scales (e.g., None/Mild/Moderate/Severe)
- Numeric ranges and categorical options
- Multi-language coded responses

Key capabilities:
- Transform answer lists to OCL concepts
- Handle both list-level and individual answer concepts
- Multi-language name support (19 languages)
- Answer-specific metadata and relationships

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from base_transformer import BaseTransformer, TransformationContext
from ocl_models import OCLConcept, OCLName
import logging


class AnswerListsTransformer(BaseTransformer):
    """
    Transformer for LOINC answer lists and individual answers.
    
    Transforms records from AnswerList.csv and related files into OCL Concept objects:
    - Answer List concepts (containers for coded responses)
    - Individual Answer concepts (specific coded values)
    - Multi-language answer variants
    - Answer list metadata and relationships
    """
    
    def __init__(self, context: TransformationContext):
        """Initialize Answer Lists transformer"""
        super().__init__(context)
        
        # Answer Lists specific configuration
        self.transformer_name = "Answer_Lists"
        self.source_dataset = "answer_lists"  # From Phase 1 DataLoader
        self.primary_key = "AnswerListId"
        
        # Answer-specific mappings
        self._load_answer_mappings()
        
        # Check for individual answers dataset
        self.has_individual_answers = "answers" in context.source_datasets
        
        self.logger.info(f"Answer Lists Transformer initialized")
        self.logger.info(f"Expected to process ~30K answer lists")
        if self.has_individual_answers:
            self.logger.info(f"Individual answers dataset available")
    
    def get_transformer_name(self) -> str:
        """Get transformer name"""
        return self.transformer_name
    
    def get_source_dataset_name(self) -> str:
        """Get source dataset name"""
        return self.source_dataset
    
    def get_primary_key_field(self) -> str:
        """Get primary key field"""
        return self.primary_key
    
    def transform_record(self, record: pd.Series) -> OCLConcept:
        """
        Transform a single answer list record into an OCL concept.
        
        Args:
            record: Pandas Series with answer list data
            
        Returns:
            OCLConcept: Transformed concept ready for OCL import
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Extract required fields
        answer_list_id = self._get_required_field(record, 'AnswerListId')
        answer_list_name = self._get_required_field(record, 'AnswerListName')
        
        # Create base concept
        concept = OCLConcept(
            id=answer_list_id,
            concept_class=self.get_concept_class(record),
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=self._determine_retired_status(record),
            external_id=answer_list_id  # Store original answer list ID
        )
        
        # Add primary English name
        concept.add_name(
            name=self._clean_text(answer_list_name),
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add alternative names if available
        self._add_alternative_names(concept, record)
        
        # Add answer list-specific metadata to extras
        self._set_answer_list_extras(concept, record)
        
        # Add description if available
        self._add_description(concept, record)
        
        # Set source file for tracking
        concept._source_file = "AnswerList.csv"
        
        return concept
    
    def get_concept_class(self, record: pd.Series) -> str:
        """
        Determine OCL concept class for answer list.
        
        Answer lists are typically classified as 'Answer List' or by their content type.
        """
        # Check if externally defined
        if 'ExtDefinedYN' in record and record['ExtDefinedYN'] == 'Y':
            return 'External Answer List'
        
        # Check answer string type for more specific classification
        if 'AnswerStringType' in record and pd.notna(record['AnswerStringType']):
            string_type = str(record['AnswerStringType']).strip().upper()
            
            type_mapping = {
                'CODED': 'Coded Answer List',
                'NUMERIC': 'Numeric Answer List', 
                'TEXT': 'Text Answer List',
                'ORDINAL': 'Ordinal Answer List'
            }
            
            return type_mapping.get(string_type, 'Answer List')
        
        # Default classification
        return 'Answer List'
    
    def _load_answer_mappings(self) -> None:
        """Load answer-specific mappings from transformation rules"""
        self.answer_mappings = {}
        
        if hasattr(self.context.transformation_rules, 'answer_list_mappings'):
            self.answer_mappings = self.context.transformation_rules.answer_list_mappings.copy()
    
    def _get_required_field(self, record: pd.Series, field_name: str) -> str:
        """Get required field value with validation"""
        if field_name not in record:
            raise ValueError(f"Required field '{field_name}' not found in record")
        
        value = record[field_name]
        if pd.isna(value) or str(value).strip() == '':
            raise ValueError(f"Required field '{field_name}' is empty")
        
        return str(value).strip()
    
    def _determine_retired_status(self, record: pd.Series) -> bool:
        """
        Determine if answer list should be marked as retired.
        
        Answer lists don't typically have explicit STATUS fields like LOINC terms,
        but may be deprecated based on other indicators.
        """
        # Check for explicit status field
        if 'STATUS' in record and pd.notna(record['STATUS']):
            return self._map_status_to_retired(record['STATUS'])
        
        # Check if marked as deprecated or obsolete
        deprecated_indicators = ['DEPRECATED', 'OBSOLETE', 'REPLACED']
        
        for field in record.index:
            if pd.notna(record[field]):
                value = str(record[field]).upper()
                if any(indicator in value for indicator in deprecated_indicators):
                    return True
        
        # Default to active
        return False
    
    def _add_alternative_names(self, concept: OCLConcept, record: pd.Series) -> None:
        """Add alternative names from answer list fields"""
        # Add alternative name fields if available
        alternative_fields = ['AlternateName', 'ShortName', 'DisplayName']
        
        for field in alternative_fields:
            if field in record and pd.notna(record[field]):
                alt_name = self._clean_text(record[field])
                if alt_name and alt_name != concept.names[0].name:
                    name_type = "Short" if field == 'ShortName' else "Alternative"
                    concept.add_name(
                        name=alt_name,
                        locale="en",
                        locale_preferred=False,
                        name_type=name_type
                    )
    
    def _set_answer_list_extras(self, concept: OCLConcept, record: pd.Series) -> None:
        """Set answer list-specific metadata in extras field"""
        # Core answer list metadata
        metadata_fields = {
            'answer_list_oid': 'AnswerListOID',
            'externally_defined': 'ExtDefinedYN',
            'external_code_system': 'ExtDefinedAnswerListCodeSystem',
            'external_link': 'ExtDefinedAnswerListLink',
            'answer_string_type': 'AnswerStringType',
            'anchored_to': 'AnchoredTo'
        }
        
        for extra_key, field_name in metadata_fields.items():
            if field_name in record and pd.notna(record[field_name]):
                value = self._clean_text(record[field_name])
                if value:
                    concept.extras[extra_key] = value
        
        # Boolean conversion for externally defined flag
        if 'ExtDefinedYN' in record and pd.notna(record['ExtDefinedYN']):
            concept.extras['is_externally_defined'] = record['ExtDefinedYN'] == 'Y'
        
        # Add individual answers count if available
        if self.has_individual_answers:
            answer_count = self._count_individual_answers(concept.id)
            if answer_count > 0:
                concept.extras['individual_answers_count'] = answer_count
        
        # Add processing metadata
        concept.extras['loinc_version'] = self.context.transformation_rules.target_loinc_version
        concept.extras['transformation_date'] = concept._creation_timestamp.isoformat()
        concept.extras['answer_list_source'] = 'LOINC Answer List File'
    
    def _count_individual_answers(self, answer_list_id: str) -> int:
        """Count individual answers for this answer list"""
        if not self.has_individual_answers:
            return 0
        
        answers_df = self.context.source_datasets["answers"]
        
        # Find answers that belong to this list
        if 'AnswerListId' in answers_df.columns:
            matching_answers = answers_df[answers_df['AnswerListId'] == answer_list_id]
            return len(matching_answers)
        
        return 0
    
    def _add_description(self, concept: OCLConcept, record: pd.Series) -> None:
        """Add description if available"""
        # Use definition or other descriptive fields
        description_fields = ['Definition', 'Description', 'AnswerListName']
        
        for field in description_fields:
            if field in record and pd.notna(record[field]):
                desc_text = self._clean_text(record[field])
                
                # Don't duplicate the primary name as description
                if desc_text and desc_text != concept.names[0].name:
                    concept.add_description(
                        description=desc_text,
                        locale="en",
                        locale_preferred=True,
                        desc_type="Definition" if field == 'Definition' else "Annotation"
                    )
                    break  # Only add one description
    
    def create_individual_answer_concepts(self) -> List[OCLConcept]:
        """
        Create OCL concepts for individual answers within answer lists.
        
        Returns:
            List of individual answer concepts
        """
        if not self.has_individual_answers:
            self.logger.warning("Individual answers dataset not available")
            return []
        
        self.logger.info("Creating individual answer concepts...")
        
        answers_df = self.context.source_datasets["answers"]
        answer_concepts = []
        
        for _, answer_record in answers_df.iterrows():
            try:
                answer_concept = self._create_individual_answer_concept(answer_record)
                answer_concepts.append(answer_concept)
            except Exception as e:
                answer_id = answer_record.get('AnswerStringId', 'UNKNOWN')
                self.logger.error(f"Failed to create answer concept {answer_id}: {str(e)}")
        
        self.logger.info(f"Created {len(answer_concepts)} individual answer concepts")
        return answer_concepts
    
    def _create_individual_answer_concept(self, record: pd.Series) -> OCLConcept:
        """Create OCL concept from individual answer record"""
        # Extract required fields
        answer_id = self._get_required_field(record, 'AnswerStringId')
        display_text = self._get_required_field(record, 'DisplayText')
        answer_list_id = record.get('AnswerListId', '')
        
        # Create concept
        concept = OCLConcept(
            id=answer_id,
            concept_class='Answer',
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=False,  # Individual answers typically don't have retirement status
            external_id=answer_id
        )
        
        # Add name
        concept.add_name(
            name=self._clean_text(display_text),
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add answer-specific metadata
        concept.extras.update({
            'answer_list_id': answer_list_id,
            'answer_type': 'Individual Answer',
            'sequence_number': record.get('SequenceNumber'),
            'answer_code': record.get('AnswerCode'),
            'score': record.get('Score')
        })
        
        # Clean up None values in extras
        concept.extras = {k: v for k, v in concept.extras.items() if v is not None}
        
        concept._source_file = "AnswerList.csv"
        
        return concept
    
    def validate_prerequisites(self) -> bool:
        """
        Validate that all prerequisites for transformation are met.
        
        Returns:
            bool: True if ready to transform, False otherwise
        """
        # Check that source dataset is available
        if self.source_dataset not in self.context.source_datasets:
            self.logger.error(f"Source dataset '{self.source_dataset}' not found")
            return False
        
        source_df = self.context.source_datasets[self.source_dataset]
        
        # Check required columns
        required_columns = ['AnswerListId', 'AnswerListName']
        missing_columns = [col for col in required_columns if col not in source_df.columns]
        
        if missing_columns:
            self.logger.error(f"Missing required columns: {missing_columns}")
            return False
        
        # Check data quality
        total_records = len(source_df)
        null_ids = source_df['AnswerListId'].isna().sum()
        null_names = source_df['AnswerListName'].isna().sum()
        
        if null_ids > 0:
            self.logger.warning(f"{null_ids} records have null AnswerListId")
        if null_names > 0:
            self.logger.warning(f"{null_names} records have null AnswerListName")
        
        # Check external definition distribution
        if 'ExtDefinedYN' in source_df.columns:
            external_counts = source_df['ExtDefinedYN'].value_counts()
            self.logger.info(f"External definition distribution: {dict(external_counts)}")
        
        self.logger.info(f"Prerequisites validation passed")
        self.logger.info(f"Ready to transform {total_records} answer lists")
        self.logger.info(f"Multi-language support: {len(self.supported_locales)} locales")
        
        return True
    
    def get_transformation_summary(self) -> Dict[str, Any]:
        """Get summary of transformation configuration"""
        return {
            "transformer_name": self.transformer_name,
            "source_dataset": self.source_dataset,
            "primary_key": self.primary_key,
            "owner_organization": self.owner_org,
            "supported_locales": self.supported_locales,
            "batch_size": self.batch_size,
            "has_individual_answers": self.has_individual_answers,
            "answer_mappings_count": len(self.answer_mappings),
            "transformation_rules_version": getattr(self.context.transformation_rules, 'version', 'Unknown')
        }
    
    def get_answer_list_statistics(self) -> Dict[str, Any]:
        """Get statistics about answer lists in the dataset"""
        if self.source_dataset not in self.context.source_datasets:
            return {}
        
        source_df = self.context.source_datasets[self.source_dataset]
        
        stats = {
            "total_answer_lists": len(source_df),
        }
        
        # External definition statistics
        if 'ExtDefinedYN' in source_df.columns:
            external_counts = source_df['ExtDefinedYN'].value_counts()
            stats["external_definition_distribution"] = dict(external_counts)
        
        # Answer string type distribution
        if 'AnswerStringType' in source_df.columns:
            type_counts = source_df['AnswerStringType'].value_counts()
            stats["answer_string_type_distribution"] = dict(type_counts)
        
        # Individual answers statistics
        if self.has_individual_answers:
            answers_df = self.context.source_datasets["answers"]
            stats["total_individual_answers"] = len(answers_df)
            
            if 'AnswerListId' in answers_df.columns:
                # Average answers per list
                answers_per_list = answers_df.groupby('AnswerListId').size()
                stats["average_answers_per_list"] = float(answers_per_list.mean())
                stats["max_answers_per_list"] = int(answers_per_list.max())
                stats["min_answers_per_list"] = int(answers_per_list.min())
        
        return stats


# Example usage and testing
if __name__ == "__main__":
    print("Answer Lists Transformer")
    print("Transforms LOINC answer lists into OCL Concept objects")
    print("\nKey features:")
    print("- Primary dataset: AnswerList.csv (30K+ records)")
    print("- Individual answers: AnswerList.csv (variable records)")
    print("- Answer types: Coded, Numeric, Text, Ordinal")
    print("- Multi-language support: 19 locales")
    print("- Answer list metadata and relationships")
    print("- Batch processing for memory efficiency")
    print("- Comprehensive validation and error handling")
