"""
OCL Mapping Models for LOINC to OCL Transformation - Phase 3

This module defines the core OCL mapping data structures that comply with the
OCL bulk import specification for creating relationships between concepts.

Features:
- Complete OCL Mapping object with validation
- Batch processing support with MappingCollection
- LOINC-specific mapping type constants
- JSON Lines output format
- Integration with Phase 2 concept URLs

Author: LOINC OCL Transform Project - Phase 3
Date: August 2025
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import json
import logging


@dataclass
class OCLMapping:
    """
    OCL Mapping object for creating relationships between concepts.
    
    Represents a single mapping/relationship between two concepts, supporting
    the OCL bulk import JSON Lines format.
    """
    # REQUIRED fields for OCL
    type: str = "Mapping"                           # Always "Mapping"
    map_type: str = ""                              # Relationship type
    from_concept_url: str = ""                      # Source concept URL
    
    # Target concept (one required)
    to_concept_url: Optional[str] = None            # Target concept URL (internal)
    to_concept_code: Optional[str] = None           # Target concept code (external)
    to_concept_name: Optional[str] = None           # Target concept name
    
    # Ownership and source
    owner: str = "Regenstrief"                      # Owner organization
    owner_type: str = "Organization"                # Owner type
    source: str = "LOINC"                           # Source repository
    
    # Optional metadata
    id: Optional[str] = None                        # OCL mapping ID
    external_id: Optional[str] = None               # External identifier
    retired: bool = False                           # Retired status
    sort_weight: Optional[float] = None             # Sort weight
    extras: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def __post_init__(self):
        """Validate mapping after creation"""
        if not self.map_type:
            raise ValueError("map_type is required")
        if not self.from_concept_url:
            raise ValueError("from_concept_url is required")
        
        # Ensure target reference exists
        if not any([self.to_concept_url, self.to_concept_code]):
            raise ValueError("Either to_concept_url or to_concept_code must be provided")
        
        # Clean URLs
        if self.from_concept_url:
            self.from_concept_url = self.from_concept_url.strip()
        if self.to_concept_url:
            self.to_concept_url = self.to_concept_url.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert mapping to OCL JSON format"""
        result = {
            "type": self.type,
            "map_type": self.map_type,
            "from_concept_url": self.from_concept_url,
            "owner": self.owner,
            "owner_type": self.owner_type,
            "source": self.source,
            "retired": self.retired
        }
        
        # Add target reference
        if self.to_concept_url:
            result["to_concept_url"] = self.to_concept_url
        elif self.to_concept_code:
            result["to_concept_code"] = self.to_concept_code
        
        # Add optional fields
        if self.id:
            result["id"] = self.id
        if self.external_id:
            result["external_id"] = self.external_id
        if self.to_concept_name:
            result["to_concept_name"] = self.to_concept_name
        if self.sort_weight is not None:
            result["sort_weight"] = self.sort_weight
        if self.extras:
            result["extras"] = self.extras
            
        return result

    def to_json_line(self) -> str:
        """Convert mapping to JSON Lines format for bulk import"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def validate(self) -> tuple[bool, List[str]]:
        """Validate mapping completeness and format"""
        errors = []
        
        # Required field validation
        if not self.map_type:
            errors.append("map_type is required")
        if not self.from_concept_url:
            errors.append("from_concept_url is required")
        if not self.from_concept_url.startswith('/orgs/'):
            errors.append("from_concept_url must be a valid OCL URL")
        
        # Target validation
        if not self.to_concept_url and not self.to_concept_code:
            errors.append("Either to_concept_url or to_concept_code is required")
        
        if self.to_concept_url and not self.to_concept_url.startswith('/orgs/'):
            errors.append("to_concept_url must be a valid OCL URL")
            
        return len(errors) == 0, errors


@dataclass  
class MappingCollection:
    """
    Collection of OCL mappings with batch processing capabilities.
    """
    mappings: List[OCLMapping] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_mapping(self, mapping: OCLMapping) -> None:
        """Add a mapping to the collection"""
        self.mappings.append(mapping)
    
    def extend_mappings(self, mappings: List[OCLMapping]) -> None:
        """Add multiple mappings to the collection"""
        self.mappings.extend(mappings)
    
    def get_by_map_type(self, map_type: str) -> List[OCLMapping]:
        """Get all mappings of a specific type"""
        return [m for m in self.mappings if m.map_type == map_type]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get collection statistics"""
        stats = {
            "total_mappings": len(self.mappings),
            "map_types": {},
            "unique_from_concepts": len(set(m.from_concept_url for m in self.mappings)),
            "unique_to_concepts": len(set(m.to_concept_url for m in self.mappings if m.to_concept_url))
        }
        
        # Count by map type
        for mapping in self.mappings:
            if mapping.map_type not in stats["map_types"]:
                stats["map_types"][mapping.map_type] = 0
            stats["map_types"][mapping.map_type] += 1
        
        return stats
    
    def validate_all(self) -> tuple[int, List[str]]:
        """Validate all mappings in collection"""
        all_errors = []
        valid_count = 0
        
        for i, mapping in enumerate(self.mappings):
            is_valid, errors = mapping.validate()
            if is_valid:
                valid_count += 1
            else:
                for error in errors:
                    all_errors.append(f"Mapping {i}: {error}")
        
        return valid_count, all_errors
    
    def write_jsonl_files(self, output_dir: Path, chunk_size: int = 10000, 
                         base_filename: str = "loinc_mappings") -> List[Path]:
        """Write mappings to chunked JSON Lines files"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_files = []
        total_mappings = len(self.mappings)
        
        if total_mappings == 0:
            return output_files
        
        # Calculate number of files needed
        num_files = (total_mappings + chunk_size - 1) // chunk_size
        
        for file_num in range(num_files):
            start_idx = file_num * chunk_size
            end_idx = min(start_idx + chunk_size, total_mappings)
            
            file_mappings = self.mappings[start_idx:end_idx]
            
            # Generate filename
            if num_files == 1:
                filename = f"{base_filename}.jsonl"
            else:
                filename = f"{base_filename}_{file_num + 1:03d}.jsonl"
            
            file_path = output_dir / filename
            
            # Write JSON Lines file
            with open(file_path, 'w', encoding='utf-8') as f:
                for mapping in file_mappings:
                    f.write(mapping.to_json_line() + '\n')
            
            output_files.append(file_path)
        
        return output_files


class LOINCMappingTypes:
    """Constants for LOINC mapping types"""
    
    # Panel structure mappings
    HAS_ELEMENT = "has element"              # Panel → Test relationships
    
    # Question-answer mappings  
    HAS_ANSWER = "has answer"                # LOINC term → Answer list associations
    
    # Code evolution mappings
    MAP_TO = "Map To"                        # Deprecated → Current code relationships
    
    # Order entry mappings (planned)
    ASK_AT_ORDER_ENTRY = "Ask At Order Entry"  # Order entry workflow
    
    # Associated observations (planned)
    ASSOCIATED_OBSERVATION = "Associated Observation"  # Clinical workflow mappings


@dataclass
class TransformationResult:
    """Result of a mapping transformation operation"""
    mappings_created: List[OCLMapping] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    source_records_processed: int = 0
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_count(self) -> int:
        """Number of successfully created mappings"""
        return len(self.mappings_created)
    
    @property
    def error_count(self) -> int:
        """Number of errors encountered"""
        return len(self.errors)
    
    @property
    def success_rate(self) -> float:
        """Success rate as percentage"""
        if self.source_records_processed == 0:
            return 0.0
        return (self.success_count / self.source_records_processed) * 100
    
    def add_to_collection(self, collection: MappingCollection) -> None:
        """Add all created mappings to a collection"""
        collection.extend_mappings(self.mappings_created)


@dataclass
class MappingTransformationMetadata:
    """Metadata for mapping transformation operations"""
    transformer_name: str
    source_file: str
    mapping_type: str
    ocl_map_type: str
    description: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def mark_completed(self) -> None:
        """Mark transformation as completed"""
        self.completed_at = datetime.now().isoformat()
