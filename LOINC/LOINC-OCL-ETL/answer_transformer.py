"""
Enhanced Answer Lists Transformer for LOINC to OCL Transformation - Phase 2

This module transforms BOTH Answer Lists (LL codes) AND LOINC Answer concepts (LA codes)
from the same AnswerList.csv file into separate OCL Concept objects.

Key updates:
- Processes both LL and LA records from the same file
- Creates Answer List concepts (concept_class: "Answer List") 
- Creates LOINC Answer concepts (concept_class: "LOINC Answer")
- Uses different transformation rules for each type
- Maintains proper parent-child relationships

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from base_transformer import BaseTransformer, TransformationContext, TransformationResult
from ocl_models import OCLConcept, OCLName, ConceptCollection
import logging
import time


class AnswerListsTransformer(BaseTransformer):
    """
    Enhanced transformer for BOTH LOINC answer lists (LL) and individual answers (LA).
    
    Processes AnswerList.csv file which contains two types of records:
    1. Answer List concepts (LL codes) - containers for answer sets
    2. LOINC Answer concepts (LA codes) - individual answer options
    """
    
    def __init__(self, context: TransformationContext):
        """Initialize Answer Lists transformer"""
        super().__init__(context)
        
        # Answer Lists specific configuration
        self.transformer_name = "Answer_Lists"
        self.source_dataset = "answer_lists"
        self.primary_key = "AnswerListId"  # Used for Answer Lists
        
        # Load mappings for both record types
        self._load_answer_mappings()
        self._load_loinc_answer_mappings()
        
        # Track statistics for both types
        self.answer_list_count = 0
        self.loinc_answer_count = 0
        
        self.logger.info(f"Enhanced Answer Lists Transformer initialized")
        self.logger.info(f"Will process both LL (Answer Lists) and LA (LOINC Answers) from AnswerList.csv")
    
    def get_transformer_name(self) -> str:
        """Get transformer name"""
        return self.transformer_name
    
    def get_source_dataset_name(self) -> str:
        """Get source dataset name"""
        return self.source_dataset
    
    def get_primary_key_field(self) -> str:
        """Get primary key field"""
        return self.primary_key
    
    def get_concept_class(self, record: pd.Series) -> str:
        """Determine concept class based on record type"""
        if self._is_loinc_answer_record(record):
            return 'LOINC Answer'
        else:
            return self._determine_answer_list_class(record)
    
    def transform_record(self, record: pd.Series) -> OCLConcept:
        """
        Transform a single record - detects whether it's an Answer List or LOINC Answer.
        
        This method handles both types of records from AnswerList.csv:
        - Records with AnswerStringId → LOINC Answer concepts
        - Records with AnswerListId (but no AnswerStringId) → Answer List concepts
        """
        if self._is_loinc_answer_record(record):
            return self._transform_loinc_answer_record(record)
        elif self._is_answer_list_record(record):
            return self._transform_answer_list_record(record)
        else:
            raise ValueError(f"Record cannot be classified as Answer List or LOINC Answer: {record.get('AnswerListId', 'UNKNOWN')}")
    
    def transform_dataset(self, progress_callback: Optional[callable] = None) -> TransformationResult:
        """
        Enhanced dataset transformation that processes both LL and LA records.
        
        Overrides the base method to handle mixed record types in the same file.
        """
        start_time = time.time()
        
        self.logger.info(f"Starting {self.get_transformer_name()} transformation")
        
        # Get source dataset
        dataset_name = self.get_source_dataset_name()
        if dataset_name not in self.context.source_datasets:
            raise ValueError(f"Source dataset '{dataset_name}' not found")
        
        source_df = self.context.source_datasets[dataset_name]
        
        # Handle LoadedDataset wrapper
        if hasattr(source_df, 'data'):
            source_df = source_df.data
        
        total_records = len(source_df)
        self.logger.info(f"Processing {total_records} records from AnswerList.csv")
        
        # Initialize result collection
        result_collection = ConceptCollection(
            collection_name=f"{self.get_transformer_name()}_Concepts",
            batch_size=self.context.batch_size
        )
        
        # Separate records by type for better processing
        answer_list_records = source_df[self._get_answer_list_mask(source_df)]
        loinc_answer_records = source_df[self._get_loinc_answer_mask(source_df)]
        
        self.logger.info(f"Found {len(answer_list_records)} Answer List records (LL codes)")
        self.logger.info(f"Found {len(loinc_answer_records)} LOINC Answer records (LA codes)")
        
        success_count = 0
        error_count = 0
        processed_count = 0
        
        # Calculate pseudo-batches for progress tracking
        batch_size = self.context.batch_size
        total_ll_batches = (len(answer_list_records) + batch_size - 1) // batch_size if len(answer_list_records) > 0 else 1
        total_la_batches = (len(loinc_answer_records) + batch_size - 1) // batch_size if len(loinc_answer_records) > 0 else 1
        total_batches = total_ll_batches + total_la_batches
        current_batch = 0
        
        # Process Answer Lists first
        for idx, (_, record) in enumerate(answer_list_records.iterrows()):
            try:
                concept = self._transform_answer_list_record(record)
                result_collection.add_concept(concept)
                success_count += 1
                self.answer_list_count += 1
            except Exception as e:
                self.logger.error(f"Failed to transform Answer List {record.get('AnswerListId', 'UNKNOWN')}: {e}")
                error_count += 1
            
            processed_count += 1
            
            # Progress callback with correct signature
            if progress_callback and processed_count % batch_size == 0:
                current_batch += 1
                progress = (current_batch / total_batches) * 100
                progress_callback(progress, current_batch, total_batches)
        
        # Update batch count if we processed Answer Lists
        if len(answer_list_records) > 0 and (len(answer_list_records) % batch_size != 0):
            current_batch += 1
            progress = (current_batch / total_batches) * 100
            if progress_callback:
                progress_callback(progress, current_batch, total_batches)
        
        # Process LOINC Answers second
        for idx, (_, record) in enumerate(loinc_answer_records.iterrows()):
            try:
                concept = self._transform_loinc_answer_record(record)
                result_collection.add_concept(concept)
                success_count += 1
                self.loinc_answer_count += 1
            except Exception as e:
                self.logger.error(f"Failed to transform LOINC Answer {record.get('AnswerStringId', 'UNKNOWN')}: {e}")
                error_count += 1
            
            processed_count += 1
            
            # Progress callback with correct signature
            if progress_callback and ((processed_count - len(answer_list_records)) % batch_size == 0):
                current_batch += 1
                progress = (current_batch / total_batches) * 100
                progress_callback(progress, current_batch, total_batches)
        
        # Final progress update
        if progress_callback and len(loinc_answer_records) > 0:
            progress = 100.0
            progress_callback(progress, total_batches, total_batches)
        
        processing_time = time.time() - start_time
        
        # Create transformation result
        result = TransformationResult(
            concepts=result_collection,
            success_count=success_count,
            error_count=error_count,
            warning_count=0,
            processing_time_seconds=processing_time
        )
        
        self.logger.info(f"Answer transformation completed: {success_count} concepts ({self.answer_list_count} LL + {self.loinc_answer_count} LA), {error_count} errors in {processing_time:.2f}s")
        return result
    
    def _is_loinc_answer_record(self, record: pd.Series) -> bool:
        """Check if record represents a LOINC Answer (LA code)"""
        return (pd.notna(record.get('AnswerStringId')) and 
                pd.notna(record.get('DisplayText')))
    
    def _is_answer_list_record(self, record: pd.Series) -> bool:
        """Check if record represents an Answer List (LL code)"""
        return (pd.notna(record.get('AnswerListId')) and 
                pd.notna(record.get('AnswerListName')) and
                pd.isna(record.get('AnswerStringId')))  # Pure Answer List row
    
    def _get_answer_list_mask(self, df: pd.DataFrame) -> pd.Series:
        """Get boolean mask for Answer List records"""
        return (df['AnswerListId'].notna() & 
                df['AnswerListName'].notna() &
                df['AnswerStringId'].isna())
    
    def _get_loinc_answer_mask(self, df: pd.DataFrame) -> pd.Series:
        """Get boolean mask for LOINC Answer records"""
        return (df['AnswerStringId'].notna() & 
                df['DisplayText'].notna())
    
    def _transform_answer_list_record(self, record: pd.Series) -> OCLConcept:
        """Transform Answer List record (LL code) to OCL concept"""
        # Extract required fields
        answer_list_id = self._get_required_field(record, 'AnswerListId')
        answer_list_name = self._get_required_field(record, 'AnswerListName')
        
        # Create concept using Answer List mappings
        concept = OCLConcept(
            id=answer_list_id,
            concept_class=self._determine_answer_list_class(record),
            datatype='N/A',  # Answer Lists use N/A datatype
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=self._determine_retired_status(record),
            external_id=answer_list_id
        )
        
        # Add name
        concept.add_name(
            name=self._clean_text(answer_list_name),
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add description if available
        self._add_description(concept, record)
        
        # Add Answer List specific metadata
        concept.extras.update({
            'answer_list_id': answer_list_id,
            'answer_list_oid': record.get('AnswerListOID'),
            'externally_defined': record.get('ExtDefinedYN'),
            'external_code_system': record.get('ExtDefinedAnswerListCodeSystem'),
            'external_link': record.get('ExtDefinedAnswerListLink'),
            'anchored_to': record.get('AnchoredTo'),
            'answer_count': self._count_answers_for_list(answer_list_id)
        })
        
        # Clean up None values
        concept.extras = {k: v for k, v in concept.extras.items() if v is not None}
        concept._source_file = "AnswerList.csv"
        
        return concept
    
    def _transform_loinc_answer_record(self, record: pd.Series) -> OCLConcept:
        """Transform LOINC Answer record (LA code) to OCL concept"""
        # Extract required fields
        answer_string_id = self._get_required_field(record, 'AnswerStringId')
        display_text = self._get_required_field(record, 'DisplayText')
        parent_answer_list_id = record.get('AnswerListId', '')
        
        # Create concept using LOINC Answer mappings
        concept = OCLConcept(
            id=answer_string_id,
            concept_class='LOINC Answer',  # Use new Code Type from transformation rules
            datatype='N/A',  # LOINC Answers use N/A datatype
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=False,  # Individual answers typically don't have retirement status
            external_id=answer_string_id
        )
        
        # Add name
        concept.add_name(
            name=self._clean_text(display_text),
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add LOINC Answer specific metadata
        concept.extras.update({
            'answer_string_id': answer_string_id,
            'answer_list_id': parent_answer_list_id,
            'sequence_number': record.get('SequenceNumber'),
            'local_answer_code': record.get('LocalAnswerCode'),
            'local_code_system': record.get('LocalAnswerCodeSystem'),
            'external_code_id': record.get('ExtCodeId'),
            'external_code_display': record.get('ExtCodeDisplayName'),
            'external_code_system': record.get('ExtCodeSystem'),
            'external_code_version': record.get('ExtCodeSystemVersion'),
            'score': record.get('Score'),
            'description': record.get('Description'),
            'subsequent_text_prompt': record.get('SubsequentTextPrompt')
        })
        
        # Clean up None values
        concept.extras = {k: v for k, v in concept.extras.items() if v is not None}
        concept._source_file = "AnswerList.csv"
        
        return concept
    
    def _determine_answer_list_class(self, record: pd.Series) -> str:
        """Determine concept class for Answer List"""
        if 'ExtDefinedYN' in record and record['ExtDefinedYN'] == 'Y':
            return 'Answer List'
        return 'Answer List'
    
    def _count_answers_for_list(self, answer_list_id: str) -> int:
        """Count individual answers for this answer list"""
        source_df = self.context.source_datasets[self.source_dataset]
        if hasattr(source_df, 'data'):
            source_df = source_df.data
        
        # Count LA records that belong to this LL
        matching_answers = source_df[
            (source_df['AnswerListId'] == answer_list_id) & 
            (source_df['AnswerStringId'].notna())
        ]
        return len(matching_answers)
    
    def _load_answer_mappings(self) -> None:
        """Load Answer List mappings from transformation rules"""
        self.answer_mappings = {}
        if hasattr(self.context.transformation_rules, 'answer_list_mappings'):
            self.answer_mappings = self.context.transformation_rules.answer_list_mappings.copy()
    
    def _load_loinc_answer_mappings(self) -> None:
        """Load LOINC Answer mappings from transformation rules"""
        self.loinc_answer_mappings = {}
        if hasattr(self.context.transformation_rules, 'loinc_answer_mappings'):
            self.loinc_answer_mappings = self.context.transformation_rules.loinc_answer_mappings.copy()
    
    def _get_required_field(self, record: pd.Series, field_name: str) -> str:
        """Get required field value with validation"""
        if field_name not in record:
            raise ValueError(f"Required field '{field_name}' not found in record")
        
        value = record[field_name]
        if pd.isna(value) or str(value).strip() == '':
            raise ValueError(f"Required field '{field_name}' is empty")
        
        return str(value).strip()
    
    def _determine_retired_status(self, record: pd.Series) -> bool:
        """Determine if answer list should be marked as retired"""
        # Answer lists don't typically have explicit STATUS fields
        return False
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for OCL"""
        if pd.isna(text):
            return ""
        return str(text).strip()
    
    def _add_description(self, concept: OCLConcept, record: pd.Series) -> None:
        """Add description if available"""
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
                    break
    
    def validate_prerequisites(self) -> bool:
        """Validate prerequisites for transformation"""
        try:
            # Check source dataset exists
            if self.source_dataset not in self.context.source_datasets:
                self.logger.error(f"Source dataset '{self.source_dataset}' not found")
                return False
            
            source_df = self.context.source_datasets[self.source_dataset]
            if hasattr(source_df, 'data'):
                source_df = source_df.data
            
            # Check required columns exist
            required_columns = ['AnswerListId', 'AnswerListName', 'AnswerStringId', 'DisplayText']
            missing_columns = [col for col in required_columns if col not in source_df.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns: {missing_columns}")
                return False
            
            # Check we have both types of records
            answer_list_count = len(source_df[self._get_answer_list_mask(source_df)])
            loinc_answer_count = len(source_df[self._get_loinc_answer_mask(source_df)])
            
            self.logger.info(f"Prerequisites validation: {answer_list_count} Answer Lists, {loinc_answer_count} LOINC Answers")
            
            if answer_list_count == 0:
                self.logger.warning("No Answer List records found")
            if loinc_answer_count == 0:
                self.logger.warning("No LOINC Answer records found")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Prerequisites validation failed: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    print("Enhanced Answer Lists Transformer")
    print("Transforms BOTH LL and LA concepts from AnswerList.csv")
    print("\nProcesses two record types:")
    print("1. Answer Lists (LL codes) - concept_class: 'Answer List'")
    print("2. LOINC Answers (LA codes) - concept_class: 'LOINC Answer'")
    print("\nExpected output: ~11,000+ total concepts")