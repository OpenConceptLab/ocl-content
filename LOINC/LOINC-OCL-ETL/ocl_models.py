"""
OCL Data Models for LOINC to OCL Transformation - Phase 2

This module defines the core OCL data structures for concepts, names, descriptions,
and related objects that comply with the OCL bulk import specification.

Based on OCL specification and Phase 2 requirements:
- Complete OCL Concept object structure
- Multi-language name support (19 languages)
- LOINC-specific extras and metadata
- Validation-ready data classes

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
import re


@dataclass
class OCLName:
    """
    OCL Name object for multi-language concept names.
    
    Represents a single name/label for a concept in a specific language.
    Supports the 19 language variants loaded in Phase 1.
    """
    name: str                           # REQUIRED: Actual name text
    locale: str                         # REQUIRED: Language code (en, fr, es, etc.)
    locale_preferred: bool = False      # REQUIRED: Primary name for this locale
    name_type: str = "Fully Specified"  # OPTIONAL: Type of name
    external_id: Optional[str] = None   # OPTIONAL: External identifier
    
    def __post_init__(self):
        """Validate name object after creation"""
        if not self.name or not self.name.strip():
            raise ValueError("Name text cannot be empty")
        if not self.locale or len(self.locale) < 2:
            raise ValueError("Locale must be valid language code")
        
        # Clean up name text
        self.name = self.name.strip()
        self.locale = self.locale.lower()


@dataclass  
class OCLDescription:
    """
    OCL Description object for concept descriptions.
    
    Optional component that provides detailed descriptions for concepts.
    """
    description: str                    # REQUIRED: Description text
    locale: str                         # REQUIRED: Language code
    locale_preferred: bool = False      # OPTIONAL: Primary description flag
    type: str = "Definition"            # OPTIONAL: Description type
    external_id: Optional[str] = None   # OPTIONAL: External identifier
    
    def __post_init__(self):
        """Validate description object after creation"""
        if not self.description or not self.description.strip():
            raise ValueError("Description text cannot be empty")
        if not self.locale or len(self.locale) < 2:
            raise ValueError("Locale must be valid language code")
            
        # Clean up description text
        self.description = self.description.strip()
        self.locale = self.locale.lower()


@dataclass
class OCLConcept:
    """
    Complete OCL Concept object for LOINC concepts.
    
    This is the main data structure that represents a LOINC term, part, or answer list
    as an OCL concept ready for bulk import.
    
    Based on OCL bulk import specification and Phase 2 requirements.
    """
    # REQUIRED FIELDS
    type: str = "Concept"               # REQUIRED: Always "Concept"
    id: str = ""                        # REQUIRED: LOINC_NUM, PartNumber, or AnswerListId
    concept_class: str = ""             # REQUIRED: LOINC CLASS field or derived
    datatype: str = "None"              # REQUIRED: Default "None" for LOINC
    owner: str = ""                     # REQUIRED: Organization ID
    owner_type: str = "Organization"    # REQUIRED: Always "Organization"
    source: str = "LOINC"               # REQUIRED: Source identifier
    retired: bool = False               # REQUIRED: Based on STATUS field
    names: List[OCLName] = field(default_factory=list)  # REQUIRED: Name array
    
    # OPTIONAL FIELDS
    external_id: Optional[str] = None   # OPTIONAL: Original LOINC identifier
    descriptions: List[OCLDescription] = field(default_factory=list)  # OPTIONAL
    extras: Dict[str, Any] = field(default_factory=dict)  # OPTIONAL: LOINC metadata
    
    # Internal tracking fields (not exported to JSON)
    _source_file: Optional[str] = field(default=None, repr=False)
    _creation_timestamp: datetime = field(default_factory=datetime.now, repr=False)
    _validation_errors: List[str] = field(default_factory=list, repr=False)
    
    def __post_init__(self):
        """Validate concept object after creation"""
        # Ensure _validation_errors is always a list
        if not hasattr(self, '_validation_errors') or not isinstance(self._validation_errors, list):
            self._validation_errors = []
        
        # Ensure names and descriptions are lists
        if not isinstance(self.names, list):
            self.names = []
        if not isinstance(self.descriptions, list):
            self.descriptions = []
        
        # Now run validation
        self._validate_initial_state()
    
    def _validate_initial_state(self):
        """Initial validation of concept state"""
        # Clear any existing validation errors
        self._validation_errors = []
        
        # Validate required fields
        if not self.id:
            self._validation_errors.append("Concept ID cannot be empty")
        if not self.concept_class:
            self._validation_errors.append("Concept class cannot be empty")
        if not self.owner:
            self._validation_errors.append("Owner cannot be empty")
        if not self.names:
            self._validation_errors.append("At least one name is required")
            
        # Validate LOINC ID format (commented out by Joe to remove ID format restriction, specifically for Container concepts)
        # if self.id and not self._is_valid_loinc_id(self.id):
        #     self._validation_errors.append(f"Invalid LOINC ID format: {self.id}")
    
    def _is_valid_loinc_id(self, loinc_id: str) -> bool:
        """Validate LOINC ID format (supports terms, parts, answer lists)"""
        patterns = [
            r'^\d{1,6}-\d$',           # LOINC terms: 12345-6
            r'^LP\d+(-\d+)?$',         # LOINC parts: LP12345-6 or LP12345
            r'^LL\d+-\d+$',            # Answer lists: LL123-4
            r'^LA\d+-\d+$',            # Answer codes: LA123-4
            r'^LOINC[-_].+$'              # Container concepts: LOINC- followed by any text
        ]
        return any(re.match(pattern, loinc_id) for pattern in patterns)
    
    def add_name(self, name: str, locale: str = "en", 
                 locale_preferred: bool = False, 
                 name_type: str = "Fully Specified") -> None:
        """Add a name to the concept"""
        try:
            ocl_name = OCLName(
                name=name,
                locale=locale,
                locale_preferred=locale_preferred,
                name_type=name_type
            )
            self.names.append(ocl_name)
            # Re-validate concept after adding name
            self._revalidate()
        except ValueError as e:
            self._validation_errors.append(f"Invalid name: {str(e)}")
    
    def add_description(self, description: str, locale: str = "en",
                       locale_preferred: bool = False,
                       desc_type: str = "Definition") -> None:
        """Add a description to the concept"""
        try:
            ocl_desc = OCLDescription(
                description=description,
                locale=locale,
                locale_preferred=locale_preferred,
                type=desc_type
            )
            self.descriptions.append(ocl_desc)
            # Re-validate concept after adding description
            self._revalidate()
        except ValueError as e:
            self._validation_errors.append(f"Invalid description: {str(e)}")
    
    def _revalidate(self) -> None:
        """Re-run validation after changes to the concept"""
        self._validation_errors = []
        
        # Validate required fields
        if not self.id:
            self._validation_errors.append("Concept ID cannot be empty")
        if not self.concept_class:
            self._validation_errors.append("Concept class cannot be empty")
        if not self.owner:
            self._validation_errors.append("Owner cannot be empty")
        if not self.names:
            self._validation_errors.append("At least one name is required")
            
        # Validate LOINC ID format (commented out by Joe to remove ID format restriction, specifically for Container concepts)
        # if self.id and not self._is_valid_loinc_id(self.id):
        #     self._validation_errors.append(f"Invalid LOINC ID format: {self.id}")
    
    def set_loinc_extras(self, component: str = None, property_: str = None,
                        time_aspect: str = None, system: str = None,
                        scale_type: str = None, method_type: str = None) -> None:
        """Set LOINC-specific metadata in extras"""
        if component:
            self.extras['component'] = component
        if property_:
            self.extras['property'] = property_
        if time_aspect:
            self.extras['time_aspect'] = time_aspect
        if system:
            self.extras['system'] = system
        if scale_type:
            self.extras['scale_type'] = scale_type
        if method_type:
            self.extras['method_type'] = method_type
    
    def is_valid(self) -> bool:
        """Check if concept is valid for OCL export"""
        return len(self._validation_errors) == 0
    
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors"""
        # Ensure we always return a list, even if _validation_errors is somehow not a list
        if isinstance(self._validation_errors, list):
            return self._validation_errors.copy()
        elif isinstance(self._validation_errors, str):
            return [self._validation_errors]
        else:
            return []
    
    def debug_validation_state(self) -> Dict[str, Any]:
        """Debug method to check validation state"""
        return {
            "has_validation_errors_attr": hasattr(self, '_validation_errors'),
            "validation_errors_type": type(self._validation_errors).__name__ if hasattr(self, '_validation_errors') else 'None',
            "validation_errors_value": self._validation_errors if hasattr(self, '_validation_errors') else 'None',
            "names_type": type(self.names).__name__,
            "names_count": len(self.names) if isinstance(self.names, list) else 'Not a list',
            "concept_id": self.id,
            "concept_class": self.concept_class,
            "owner": self.owner
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export (excludes internal fields)"""
        result = {
            "type": self.type,
            "id": self.id,
            "concept_class": self.concept_class,
            "datatype": self.datatype,
            "owner": self.owner,
            "owner_type": self.owner_type,
            "source": self.source,
            "retired": self.retired,
            "names": [
                {
                    "name": name.name,
                    "locale": name.locale,
                    "locale_preferred": name.locale_preferred,
                    "name_type": name.name_type,
                    **({"external_id": name.external_id} if name.external_id else {})
                }
                for name in self.names
            ]
        }
        
        # Add optional fields if present
        if self.external_id:
            result["external_id"] = self.external_id
        
        if self.descriptions:
            result["descriptions"] = [
                {
                    "description": desc.description,
                    "locale": desc.locale,
                    "locale_preferred": desc.locale_preferred,
                    "type": desc.type,
                    **({"external_id": desc.external_id} if desc.external_id else {})
                }
                for desc in self.descriptions
            ]
        
        if self.extras:
            result["extras"] = self.extras
            
        return result
    
    def to_json(self, indent: int = None) -> str:
        """Convert to JSON string for export"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class ConceptCollection:
    """
    Collection of OCL Concepts with batch processing capabilities.
    
    Manages groups of concepts for efficient processing and validation.
    Supports the batch processing patterns proven in Phase 1.
    """
    collection_name: str = "LOINC_Concepts"  # Most commonly specified field first
    concepts: List[OCLConcept] = field(default_factory=list)
    batch_size: int = 1000
    
    def __post_init__(self):
        """Ensure proper initialization of collection"""
        # Ensure concepts is always a list (defensive programming)
        if not isinstance(self.concepts, list):
            # If concepts got assigned a string by mistake, reset it
            if isinstance(self.concepts, str):
                print(f"Warning: ConceptCollection.concepts was assigned string '{self.concepts}', resetting to empty list")
            self.concepts = []
    
    def add_concept(self, concept: OCLConcept) -> None:
        """Add a concept to the collection"""
        # Ensure concepts list exists and is a list
        if not hasattr(self, 'concepts') or not isinstance(self.concepts, list):
            self.concepts = []
        
        self.concepts.append(concept)
    
    def get_valid_concepts(self) -> List[OCLConcept]:
        """Get all valid concepts, deduplicated by concept ID"""
        seen_ids = set()
        deduped = []
        for concept in self.concepts:
            if concept.is_valid() and concept.id not in seen_ids:
                deduped.append(concept)
                seen_ids.add(concept.id)
        return deduped
    
    def get_invalid_concepts(self) -> List[OCLConcept]:
        """Get all invalid concepts"""
        return [concept for concept in self.concepts if not concept.is_valid()]
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get comprehensive validation report"""
        valid_concepts = self.get_valid_concepts()
        invalid_concepts = self.get_invalid_concepts()
        
        # Build error details for invalid concepts
        error_details = []
        for concept in invalid_concepts:
            validation_errors = concept.get_validation_errors()
            if validation_errors:  # Only add if there are actual errors
                error_details.append({
                    "concept_id": concept.id or "UNKNOWN",
                    "errors": validation_errors  # This should be a list
                })
        
        return {
            "collection_name": self.collection_name,
            "total_concepts": len(self.concepts),
            "valid_concepts": len(valid_concepts),
            "invalid_concepts": len(invalid_concepts),
            "validation_rate": len(valid_concepts) / len(self.concepts) if self.concepts else 0,
            "errors": error_details
        }
    
    def get_batches(self) -> List[List[OCLConcept]]:
        """Split collection into batches for processing"""
        batches = []
        for i in range(0, len(self.concepts), self.batch_size):
            batch = self.concepts[i:i + self.batch_size]
            batches.append(batch)
        return batches
    
    def to_jsonl(self) -> str:
        """Convert valid concepts to JSON-lines format"""
        valid_concepts = self.get_valid_concepts()
        jsonl_lines = []
        
        for concept in valid_concepts:
            jsonl_lines.append(concept.to_json())
        
        return '\n'.join(jsonl_lines)


# Example usage and testing
if __name__ == "__main__":
    # Create a sample LOINC concept
    concept = OCLConcept(
        id="1234-5",
        concept_class="Laboratory",
        owner="Regenstrief"
    )
    
    # Add primary English name
    concept.add_name("Glucose [Mass/volume] in Serum", locale="en", locale_preferred=True)
    
    # Add French translation
    concept.add_name("Glucose [Masse/volume] dans Sérum", locale="fr")
    
    # Add LOINC-specific metadata
    concept.set_loinc_extras(
        component="Glucose",
        property_="MCnc",
        time_aspect="Pt",
        system="Ser",
        scale_type="Qn"
    )
    
    # Validate and export
    if concept.is_valid():
        print("✅ Concept is valid")
        print("JSON output:")
        print(concept.to_json(indent=2))
    else:
        print("❌ Concept validation errors:")
        for error in concept.get_validation_errors():
            print(f"  - {error}")