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
from .base_transformer import BaseTransformer, TransformationContext, TransformationResult
from .ocl_models import OCLConcept, OCLName, ConceptCollection
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
        if pd.notna(record.get('AnswerStringId')):
            return 'LOINC Answer'
        else:
            return self._determine_answer_list_class(record)
    
    def transform_record(self, record: pd.Series) -> OCLConcept:
        """
        Transform a single record - detects whether it's a LOINC Answer.
        
        NOTE: This method is primarily for LOINC Answer records. 
        Answer List concepts are created via the unique extraction method.
        """
        if pd.notna(record.get('AnswerStringId')):
            return self._transform_loinc_answer_record(record)
        else:
            # This shouldn't happen in the new approach, but fallback for safety
            raise ValueError(f"Record type not supported in transform_record: {record.get('AnswerListId', 'UNKNOWN')}")
    
    def transform_dataset(self, progress_callback: Optional[callable] = None) -> TransformationResult:
        """
        Enhanced dataset transformation that processes both LL and LA records.
        
        CORRECTED APPROACH:
        1. Extract unique AnswerListId values → Create Answer List concepts  
        2. Process rows with AnswerStringId → Create LOINC Answer concepts
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
        
        success_count = 0
        error_count = 0
        
        # STEP 1: Create Answer List concepts from unique AnswerListId values
        self.logger.info("Step 1: Creating Answer List concepts from unique LL codes...")
        unique_answer_lists = self._extract_unique_answer_lists(source_df)
        
        self.logger.info(f"Found {len(unique_answer_lists)} unique Answer Lists")
        
        batch_size = self.context.batch_size
        total_batches = len(unique_answer_lists) + ((len(source_df[source_df['AnswerStringId'].notna()]) + batch_size - 1) // batch_size)
        current_batch = 0
        
        # Process Answer Lists
        for idx, answer_list_info in enumerate(unique_answer_lists):
            try:
                concept = self._create_answer_list_concept_from_info(answer_list_info)
                result_collection.add_concept(concept)
                success_count += 1
                self.answer_list_count += 1
            except Exception as e:
                self.logger.error(f"Failed to create Answer List {answer_list_info.get('AnswerListId', 'UNKNOWN')}: {e}")
                error_count += 1
            
            # Progress callback
            if progress_callback and (idx + 1) % 100 == 0:
                current_batch = (idx + 1) // 100
                progress = (current_batch / total_batches) * 100
                progress_callback(progress, current_batch, total_batches)
        
        # STEP 2: Create LOINC Answer concepts from rows with AnswerStringId
        self.logger.info("Step 2: Creating LOINC Answer concepts from LA codes...")
        loinc_answer_records = source_df[source_df['AnswerStringId'].notna()]
        
        self.logger.info(f"Found {len(loinc_answer_records)} LOINC Answer records")
        
        processed_count = 0
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
            
            # Progress callback
            if progress_callback and processed_count % batch_size == 0:
                current_batch = len(unique_answer_lists) // 100 + (processed_count // batch_size)
                progress = (current_batch / total_batches) * 100
                progress_callback(progress, current_batch, total_batches)
        
        # Final progress update
        if progress_callback:
            progress_callback(100.0, total_batches, total_batches)
        
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
    
    def _extract_unique_answer_lists(self, source_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Extract unique Answer List information from the dataframe.
        
        Since every row has AnswerListId/AnswerListName, we need to get unique 
        combinations and use the first occurrence for each AnswerListId.
        """
        # Get unique AnswerListId values and their associated metadata
        unique_lists = []
        seen_list_ids = set()
        
        for _, row in source_df.iterrows():
            answer_list_id = row.get('AnswerListId')
            
            if pd.notna(answer_list_id) and answer_list_id not in seen_list_ids:
                seen_list_ids.add(answer_list_id)
                
                # Extract Answer List information from this row
                unique_lists.append({
                    'AnswerListId': answer_list_id,
                    'AnswerListName': row.get('AnswerListName'),
                    'AnswerListOID': row.get('AnswerListOID'),
                    'ExtDefinedYN': row.get('ExtDefinedYN'),
                    'ExtDefinedAnswerListCodeSystem': row.get('ExtDefinedAnswerListCodeSystem'),
                    'ExtDefinedAnswerListLink': row.get('ExtDefinedAnswerListLink'),
                    'AnchoredTo': row.get('AnchoredTo')
                })
        
        return unique_lists
    
    def _create_answer_list_concept_from_info(self, answer_list_info: Dict[str, Any]) -> OCLConcept:
        """Create Answer List concept from extracted unique information"""
        answer_list_id = answer_list_info['AnswerListId']
        answer_list_name = answer_list_info['AnswerListName']
        
        # Create concept using Answer List mappings
        concept = OCLConcept(
            id=answer_list_id,
            concept_class=self._determine_answer_list_class_from_info(answer_list_info),
            datatype='N/A',
            owner=self.owner_org,
            owner_type="Organization",
            source=self.source_name,
            retired=False,  # Answer lists are typically not retired
            external_id=answer_list_id
        )
        
        # Add name
        concept.add_name(
            name=self._clean_text(answer_list_name),
            locale="en",
            locale_preferred=True,
            name_type="Fully Specified"
        )
        
        # Add Answer List specific metadata
        concept.extras.update({
            'answer_list_id': answer_list_id,
            'answer_list_oid': answer_list_info.get('AnswerListOID') if self.is_valid_value(answer_list_info.get('AnswerListOID')) else None,
            'externally_defined': answer_list_info.get('ExtDefinedYN') if self.is_valid_value(answer_list_info.get('ExtDefinedYN')) else None,
            'external_code_system': answer_list_info.get('ExtDefinedAnswerListCodeSystem') if self.is_valid_value(answer_list_info.get('ExtDefinedAnswerListCodeSystem')) else None,
            'external_link': answer_list_info.get('ExtDefinedAnswerListLink') if self.is_valid_value(answer_list_info.get('ExtDefinedAnswerListLink')) else None,
            'anchored_to': answer_list_info.get('AnchoredTo') if self.is_valid_value(answer_list_info.get('AnchoredTo')) else None,
            'answer_count': self._count_answers_for_list(answer_list_id)
        })
        
        # Enhanced cleanup - removes None, NaN strings, empty strings, etc.
        concept.extras = self.clean_concept_extras(concept.extras)
        concept._source_file = "AnswerList.csv"
        
        return concept
    
    def _determine_answer_list_class_from_info(self, answer_list_info: Dict[str, Any]) -> str:
        """Determine concept class for Answer List from extracted info"""
        if answer_list_info.get('ExtDefinedYN') == 'Y':
            return 'External Answer List'
        return 'Answer List'
    
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
        # Extract required fields with appropriate validation
        answer_string_id = self._get_required_field(record, 'AnswerStringId')
        display_text = self._get_display_text(record)  # Use special handling for DisplayText
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
        extras = {
            'answer_string_id': answer_string_id,
            'answer_list_id': parent_answer_list_id
        }

        # Optional fields - only add if they have valid values
        optional_fields = {
            'sequence_number': 'SequenceNumber',
            'local_answer_code': 'LocalAnswerCode',
            'local_code_system': 'LocalAnswerCodeSystem',
            'external_code_id': 'ExtCodeId',
            'external_code_display': 'ExtCodeDisplayName',
            'external_code_system': 'ExtCodeSystem',
            'external_code_version': 'ExtCodeSystemVersion',
            'score': 'Score',
            'description': 'Description',
            'subsequent_text_prompt': 'SubsequentTextPrompt'
        }

        for ext_key, field_name in optional_fields.items():
            value = record.get(field_name)
            if pd.notna(value) and str(value).strip():  # Only add non-NaN, non-empty values
                extras[ext_key] = value

        concept.extras.update(extras)
        
        # Clean up None values
        concept.extras = {k: v for k, v in concept.extras.items() if v is not None}
        concept._source_file = "AnswerList.csv"
        
        return concept
    
    def _get_display_text(self, record: pd.Series) -> str:
        """
        Get DisplayText with appropriate validation for LOINC Answer concepts.
        
        Unlike other required fields, DisplayText can have values like "None", "N/A", 
        "Unknown", etc. which are valid display text for answer options.
        """
        field_name = 'DisplayText'
        
        if field_name not in record:
            raise ValueError(f"Required field '{field_name}' not found in record")
        
        value = record[field_name]
        
        # Handle actual NaN/None values
        if pd.isna(value):
            # For missing DisplayText, use a default based on the AnswerStringId
            answer_id = record.get('AnswerStringId', 'Unknown')
            return f"Answer {answer_id}"
        
        # Convert to string and clean
        str_value = str(value).strip()
        
        # Accept any non-empty string, including "None", "N/A", etc.
        if str_value == '':
            # For empty strings, use a default
            answer_id = record.get('AnswerStringId', 'Unknown')
            return f"Answer {answer_id}"
        
        return str_value
    
    def _determine_answer_list_class(self, record: pd.Series) -> str:
        """Determine concept class for Answer List"""
        if 'ExtDefinedYN' in record and record['ExtDefinedYN'] == 'Y':
            return 'External Answer List'
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