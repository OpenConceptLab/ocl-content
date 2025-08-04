"""
OCL Concept Validator for LOINC to OCL Transformation - Phase 2

This module provides comprehensive validation for OCL concepts to ensure they
meet the OCL bulk import specification requirements. Validates both individual
concepts and collections of concepts.

Key validation areas:
- Required field presence and format
- OCL specification compliance
- Multi-language name validation
- JSON structure and serialization
- Performance and memory efficiency

Maintains Phase 1's zero-error quality standard.

Author: LOINC OCL Transform Project - Phase 2
Date: August 2025
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from ocl_models import OCLConcept, OCLName, OCLDescription, ConceptCollection


@dataclass
class ValidationIssue:
    """Represents a validation issue found in an OCL concept"""
    concept_id: str
    severity: str  # 'ERROR', 'WARNING', 'INFO'
    category: str  # 'REQUIRED_FIELD', 'FORMAT', 'DUPLICATE', etc.
    message: str
    field_name: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class ValidationReport:
    """Comprehensive validation report for OCL concepts"""
    total_concepts: int = 0
    valid_concepts: int = 0
    invalid_concepts: int = 0
    concepts_with_warnings: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    summary_stats: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        return (self.valid_concepts / self.total_concepts * 100) if self.total_concepts > 0 else 0.0
    
    @property
    def has_errors(self) -> bool:
        """Check if report contains any errors"""
        return any(issue.severity == 'ERROR' for issue in self.issues)
    
    def get_errors(self) -> List[ValidationIssue]:
        """Get all error-level issues"""
        return [issue for issue in self.issues if issue.severity == 'ERROR']
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues"""
        return [issue for issue in self.issues if issue.severity == 'WARNING']
    
    def get_issue_summary(self) -> Dict[str, int]:
        """Get summary of issues by category"""
        summary = defaultdict(int)
        for issue in self.issues:
            summary[f"{issue.severity}_{issue.category}"] += 1
        return dict(summary)


class OCLConceptValidator:

    """
    Enhanced OCL concept validator that combines official OCL schema validation
    with comprehensive quality assurance for LOINC concepts.
    
    Two-tier validation approach:
    1. Official OCL schema validation (required for bulk import)
    2. Enhanced validation (names, multi-language, LOINC-specific, quality)
    """
     # OCL minimum required fields for bulk import compliance
    ocl_required_fields = [
        'type', 'id', 'owner', 'source', 'concept_class', 'datatype'
    ]

    # Enhanced required fields for usable concepts
    enhanced_required_fields = [
        'names'
    ]   
    valid_locales = {
            'en', 'fr', 'es', 'de', 'it', 'pt', 'nl', 'ru', 'zh', 'ja',
            'ko', 'ar', 'hi', 'sv', 'da', 'no', 'fi', 'pl', 'cs', 'el',
            'tr', 'he', 'th', 'vi', 'uk', 'bg', 'hr', 'et', 'lv', 'lt'
        }
    def __init__(self, strict_mode: bool = True, use_official_schema: bool = True):
        """
        Initialize OCL concept validator.
        
        Args:
            strict_mode: If True, applies strict validation rules for enhanced validation
            use_official_schema: If True, validates against official OCL schema
        """
        self.strict_mode = strict_mode
        self.use_official_schema = use_official_schema
        self.logger = logging.getLogger(__name__)
        
        # Initialize official OCL schema validation if requested
        if self.use_official_schema:
            try:
                import jsonschema
                self.jsonschema = jsonschema
                self.has_jsonschema = True
            except ImportError:
                self.logger.warning("jsonschema library not available - official schema validation disabled")
                self.has_jsonschema = False
                self.use_official_schema = False
        
        # Official OCL concept schema (from OCL validator) 
        self.ocl_concept_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "http://openconceptlab.org/json_concept.schema.json",
            "title": "JSON_Concept",
            "description": "A JSON-based OCL concept",
            "type": "object",
            "properties": {
                "type": {
                    "description": "OCL resource type, eg \"Concept\" or \"Mapping\"",
                    "type": "string"
                },
                "owner": {
                    "description": "ID for the owner of this resource",
                    "type": "string"
                },
                "owner_type": {
                    "description": ("Resource type for the owner of this resource, "
                                    "either \"Organization\" or \"User\"."),
                    "type": "string"
                },
                "source": {
                    "description": "OCL source for this concept",
                    "type": "string"
                },
                "concept_class": {
                    "description": "Class for this concept, eg Symptom, Diagnosis",
                    "type": "string"
                },
                "datatype": {
                    "description": "Datatype for this concept, eg Numeric, Text, Coded",
                    "type": "string"
                },
                "id": {
                    "description": "ID of this resource",
                    "type": "string"
                },
                "external_id": {
                    "description": "External identifier of this resource",
                    "type": "string"
                }
            },
            "required": ["type", "id", "owner", "source", "concept_class", "datatype"]
        }
        
        # Validation patterns for LOINC-specific validation
        self.loinc_patterns = {
            'loinc_code': re.compile(r'^\d{1,6}-\d{1,2}$'),  # Allow 1 to 6 digits (FIXED)
            'part_number': re.compile(r'^LP\d+(-\d+)?$'),     # e.g., "LP12345-6"
            'answer_list_id': re.compile(r'^LL\d+-\d+$'),     # e.g., "LL123-4"
            'answer_string_id': re.compile(r'^LA\d+-\d+$'),   # e.g., "LA123-4"
        }
    
    def validate_concept(self, concept: OCLConcept) -> List[ValidationIssue]:
        """
        Two-tier validation of OCL concept:
        1. Official OCL schema validation (required for bulk import)
        2. Enhanced validation (names, multi-language, LOINC-specific, quality)
        
        Args:
            concept: OCL concept to validate
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        # Tier 1: Official OCL Schema Validation
        if self.use_official_schema and self.has_jsonschema:
            issues.extend(self._validate_official_ocl_schema(concept))
        
        # Tier 2: Enhanced Validation (only if basic schema passes or schema validation disabled)
        schema_errors = [issue for issue in issues if issue.severity == 'ERROR' and issue.category in ['OCL_SCHEMA', 'REQUIRED_FIELD']]
        
        if not schema_errors or not self.use_official_schema:
            # Core field validation (OCL + enhanced)
            issues.extend(self._validate_required_fields(concept))
            
            # Field format validation
            issues.extend(self._validate_field_formats(concept))
            
            # Names validation (critical for usable concepts)
            issues.extend(self._validate_names(concept))
            
            # Descriptions validation
            issues.extend(self._validate_descriptions(concept))
            
            # Extras validation
            issues.extend(self._validate_extras(concept))
            
            # JSON serialization validation
            issues.extend(self._validate_json_serialization(concept))
        else:
            # Add warning that enhanced validation was skipped due to schema errors
            issues.append(ValidationIssue(
                concept_id=concept.id or 'UNKNOWN',
                severity='WARNING',
                category='VALIDATION_SKIPPED',
                message="Enhanced validation skipped due to OCL schema errors",
                suggested_fix="Fix OCL schema compliance issues first"
            ))
        
        return issues
    
    def _validate_official_ocl_schema(self, concept: OCLConcept) -> List[ValidationIssue]:
        """Validate concept against official OCL JSON schema"""
        issues = []
        
        try:
            # Convert concept to dict for schema validation
            concept_dict = concept.to_dict()
            
            # Validate against official OCL schema
            self.jsonschema.validate(instance=concept_dict, schema=self.ocl_concept_schema)
            
            # If we get here, schema validation passed
            issues.append(ValidationIssue(
                concept_id=concept.id or 'UNKNOWN',
                severity='INFO',
                category='OCL_SCHEMA',
                message="Concept passes official OCL schema validation"
            ))
            
        except self.jsonschema.ValidationError as e:
            # Schema validation failed
            issues.append(ValidationIssue(
                concept_id=concept.id or 'UNKNOWN',
                severity='ERROR',
                category='OCL_SCHEMA',
                message=f"OCL schema validation failed: {str(e.message)}",
                field_name='.'.join(str(x) for x in e.absolute_path) if e.absolute_path else None,
                suggested_fix="Ensure concept meets official OCL bulk import schema requirements"
            ))
        except Exception as e:
            # Unexpected validation error
            issues.append(ValidationIssue(
                concept_id=concept.id or 'UNKNOWN',
                severity='ERROR',
                category='OCL_SCHEMA',
                message=f"Schema validation error: {str(e)}",
                suggested_fix="Check concept structure and data types"
            ))
        
        return issues
    
    def validate_collection(self, collection: ConceptCollection) -> ValidationReport:
        """
        Validate a collection of OCL concepts.
        
        Args:
            collection: Collection of concepts to validate
            
        Returns:
            Comprehensive validation report
        """
        self.logger.info(f"Validating concept collection: {collection.collection_name}")
        self.logger.info(f"Total concepts to validate: {len(collection.concepts)}")
        
        report = ValidationReport()
        report.total_concepts = len(collection.concepts)
        
        # Track duplicates and statistics
        concept_ids = set()
        duplicate_ids = set()
        locale_stats = defaultdict(int)
        concept_class_stats = defaultdict(int)
        
        # Validate each concept
        for i, concept in enumerate(collection.concepts):
            concept_issues = self.validate_concept(concept)
            
            # Check for duplicate IDs
            if concept.id in concept_ids:
                duplicate_ids.add(concept.id)
                concept_issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='ERROR',
                    category='DUPLICATE',
                    message=f"Duplicate concept ID: {concept.id}"
                ))
            else:
                concept_ids.add(concept.id)
            
            # Collect statistics
            concept_class_stats[concept.concept_class] += 1
            for name in concept.names:
                locale_stats[name.locale] += 1
            
            # Categorize concept
            has_errors = any(issue.severity == 'ERROR' for issue in concept_issues)
            has_warnings = any(issue.severity == 'WARNING' for issue in concept_issues)
            
            if has_errors:
                report.invalid_concepts += 1
            else:
                report.valid_concepts += 1
            
            if has_warnings:
                report.concepts_with_warnings += 1
            
            # Add issues to report
            report.issues.extend(concept_issues)
            
            # Progress logging
            if (i + 1) % 1000 == 0:
                self.logger.debug(f"Validated {i + 1}/{len(collection.concepts)} concepts")
        
        # Generate summary statistics
        report.summary_stats = {
            'unique_concept_ids': len(concept_ids),
            'duplicate_ids_count': len(duplicate_ids),
            'duplicate_ids': list(duplicate_ids),
            'concept_class_distribution': dict(concept_class_stats),
            'locale_distribution': dict(locale_stats),
            'average_names_per_concept': sum(len(c.names) for c in collection.concepts) / len(collection.concepts) if collection.concepts else 0,
            'concepts_with_descriptions': sum(1 for c in collection.concepts if c.descriptions),
            'concepts_with_extras': sum(1 for c in collection.concepts if c.extras)
        }
        
        self.logger.info(f"Validation complete: {report.valid_concepts}/{report.total_concepts} valid concepts")
        self.logger.info(f"Success rate: {report.success_rate:.1f}%")
        
        return report
    
    def _validate_required_fields(self, concept: OCLConcept) -> List[ValidationIssue]:
        """
        Validate required fields with distinction between OCL minimum and enhanced requirements
        """
        issues = []
        
        # Get concept dict representation
        concept_dict = concept.to_dict()
        
        # Validate OCL minimum required fields (for bulk import compliance)
        for field in self.ocl_required_fields:
            if field not in concept_dict:
                issues.append(ValidationIssue(
                    concept_id=concept.id or 'UNKNOWN',
                    severity='ERROR',
                    category='OCL_REQUIRED_FIELD',
                    message=f"Missing OCL required field: {field}",
                    field_name=field,
                    suggested_fix=f"Add {field} field to concept (required for OCL bulk import)"
                ))
            elif not concept_dict[field] and field != 'external_id':  # external_id can be empty
                issues.append(ValidationIssue(
                    concept_id=concept.id or 'UNKNOWN',
                    severity='ERROR',
                    category='OCL_REQUIRED_FIELD',
                    message=f"OCL required field is empty: {field}",
                    field_name=field,
                    suggested_fix=f"Provide a value for {field}"
                ))
        
        # Validate enhanced required fields (for usable concepts)
        for field in self.enhanced_required_fields:
            if field not in concept_dict:
                severity = 'ERROR' if self.strict_mode else 'WARNING'
                issues.append(ValidationIssue(
                    concept_id=concept.id or 'UNKNOWN',
                    severity=severity,
                    category='ENHANCED_REQUIRED_FIELD',
                    message=f"Missing field required for usable concepts: {field}",
                    field_name=field,
                    suggested_fix=f"Add {field} field - concepts without names are not usable"
                ))
            elif field == 'names' and isinstance(concept_dict[field], list) and len(concept_dict[field]) == 0:
                severity = 'ERROR' if self.strict_mode else 'WARNING'
                issues.append(ValidationIssue(
                    concept_id=concept.id or 'UNKNOWN',
                    severity=severity,
                    category='ENHANCED_REQUIRED_FIELD',
                    message=f"Enhanced required field is empty: {field}",
                    field_name=field,
                    suggested_fix=f"Add at least one name to make the concept usable"
                ))
        
        # Check for optional but recommended fields
        recommended_fields = {'owner_type', 'retired'}
        for field in recommended_fields:
            if field not in concept_dict:
                issues.append(ValidationIssue(
                    concept_id=concept.id or 'UNKNOWN',
                    severity='INFO',
                    category='RECOMMENDED_FIELD',
                    message=f"Recommended field missing: {field}",
                    field_name=field,
                    suggested_fix=f"Consider adding {field} field for better concept metadata"
                ))
        
        return issues
    
    def _validate_field_formats(self, concept: OCLConcept) -> List[ValidationIssue]:
        """Validate field formats with OCL compliance focus + LOINC-specific enhancements"""
        issues = []
        
        # OCL Core Field Validation
        
        # Validate concept ID (OCL allows any string, but we can check LOINC format as enhancement)
        if concept.id:
            # OCL doesn't enforce ID format, but LOINC-specific validation is valuable
            if not self._is_valid_loinc_id(concept.id):
                severity = 'WARNING' if not self.strict_mode else 'ERROR'
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity=severity,
                    category='LOINC_FORMAT',
                    message=f"ID doesn't match LOINC format patterns: {concept.id}",
                    field_name='id',
                    suggested_fix="Use valid LOINC format (e.g., 12345-6, LP12345-6, LL123-4) or use custom format consistently"
                ))
        
        # Validate type field (OCL requires "Concept")
        if concept.type and concept.type != 'Concept':
            issues.append(ValidationIssue(
                concept_id=concept.id,
                severity='ERROR',
                category='OCL_FORMAT',
                message=f"Invalid type field: {concept.type}. OCL requires 'Concept'",
                field_name='type',
                suggested_fix="Set type to 'Concept' for OCL compliance"
            ))
        
        # Validate owner_type field (OCL allows "Organization" or "User")
        if concept.owner_type and concept.owner_type not in ['Organization', 'User']:
            issues.append(ValidationIssue(
                concept_id=concept.id,
                severity='ERROR',
                category='OCL_FORMAT',
                message=f"Invalid owner_type: {concept.owner_type}. Must be 'Organization' or 'User'",
                field_name='owner_type',
                suggested_fix="Set owner_type to 'Organization' or 'User'"
            ))
        
        # LOINC-Specific Enhancements (informational/warning level)
        
        # Validate source field (LOINC-specific preference)
        if concept.source and concept.source != 'LOINC':
            issues.append(ValidationIssue(
                concept_id=concept.id,
                severity='INFO',
                category='LOINC_CONVENTION',
                message=f"Source value: {concept.source}. Consider 'LOINC' for LOINC concepts",
                field_name='source',
                suggested_fix="Use 'LOINC' as source for LOINC-derived concepts"
            ))
        
        # Validate datatype field (LOINC-specific - most LOINC concepts use "None")
        if concept.datatype and concept.datatype not in ['None', 'Coded', 'Numeric', 'Text', 'Boolean']:
            issues.append(ValidationIssue(
                concept_id=concept.id,
                severity='INFO',
                category='LOINC_CONVENTION',
                message=f"Uncommon datatype: {concept.datatype}. Most LOINC concepts use 'None'",
                field_name='datatype',
                suggested_fix="Consider using standard OCL datatypes: None, Coded, Numeric, Text, Boolean"
            ))
        
        return issues
    
    def _validate_names(self, concept: OCLConcept) -> List[ValidationIssue]:
        """Validate concept names"""
        issues = []
        
        if not concept.names:
            issues.append(ValidationIssue(
                concept_id=concept.id,
                severity='ERROR',
                category='REQUIRED_FIELD',
                message="Concept must have at least one name",
                field_name='names',
                suggested_fix="Add at least one OCLName to the concept"
            ))
            return issues
        
        # Track locales and preferred names
        locales_seen = set()
        preferred_names_by_locale = defaultdict(int)
        
        for i, name in enumerate(concept.names):
            # Validate name text
            if not name.name or not name.name.strip():
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='ERROR',
                    category='FORMAT',
                    message=f"Name {i+1} has empty text",
                    field_name='names',
                    suggested_fix="Provide non-empty name text"
                ))
            
            # Validate locale
            if not name.locale:
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='ERROR',
                    category='FORMAT',
                    message=f"Name {i+1} missing locale",
                    field_name='names',
                    suggested_fix="Provide valid locale code (e.g., 'en', 'fr')"
                ))
            elif name.locale not in self.valid_locales:
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='WARNING',
                    category='FORMAT',
                    message=f"Name {i+1} has unrecognized locale: {name.locale}",
                    field_name='names',
                    suggested_fix=f"Use standard ISO 639-1 locale code"
                ))
            
            # Track for duplicate/preference validation
            if name.locale:
                locales_seen.add(name.locale)
                if name.locale_preferred:
                    preferred_names_by_locale[name.locale] += 1
        
        # Validate preferred names
        english_preferred = preferred_names_by_locale.get('en', 0)
        if english_preferred == 0:
            issues.append(ValidationIssue(
                concept_id=concept.id,
                severity='ERROR',
                category='FORMAT',
                message="No preferred English name found",
                field_name='names',
                suggested_fix="Mark one English name as locale_preferred=True"
            ))
        elif english_preferred > 1:
            issues.append(ValidationIssue(
                concept_id=concept.id,
                severity='WARNING',
                category='FORMAT',
                message=f"Multiple preferred English names found ({english_preferred})",
                field_name='names',
                suggested_fix="Only one name per locale should be preferred"
            ))
        
        # Check for multiple preferred names in other locales
        for locale, count in preferred_names_by_locale.items():
            if locale != 'en' and count > 1:
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='WARNING',
                    category='FORMAT',
                    message=f"Multiple preferred names in locale '{locale}' ({count})",
                    field_name='names',
                    suggested_fix=f"Only one name per locale should be preferred"
                ))
        
        return issues
    
    def _validate_descriptions(self, concept: OCLConcept) -> List[ValidationIssue]:
        """Validate concept descriptions"""
        issues = []
        
        for i, desc in enumerate(concept.descriptions):
            # Validate description text
            if not desc.description or not desc.description.strip():
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='WARNING',
                    category='FORMAT',
                    message=f"Description {i+1} has empty text",
                    field_name='descriptions',
                    suggested_fix="Provide non-empty description text or remove description"
                ))
            
            # Validate locale
            if not desc.locale:
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='WARNING',
                    category='FORMAT',
                    message=f"Description {i+1} missing locale",
                    field_name='descriptions',
                    suggested_fix="Provide valid locale code"
                ))
            elif desc.locale not in self.valid_locales:
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='INFO',
                    category='FORMAT',
                    message=f"Description {i+1} has unrecognized locale: {desc.locale}",
                    field_name='descriptions'
                ))
        
        return issues
    
    def _validate_extras(self, concept: OCLConcept) -> List[ValidationIssue]:
        """Validate extras field"""
        issues = []
        
        if not concept.extras:
            return issues
        
        # Check for reasonable extras structure
        if not isinstance(concept.extras, dict):
            issues.append(ValidationIssue(
                concept_id=concept.id,
                severity='ERROR',
                category='FORMAT',
                message="Extras field must be a dictionary",
                field_name='extras',
                suggested_fix="Ensure extras is a dict object"
            ))
            return issues
        
        # Validate extras content
        for key, value in concept.extras.items():
            # Check key format
            if not isinstance(key, str) or not key.strip():
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='WARNING',
                    category='FORMAT',
                    message=f"Extras key is empty or invalid: '{key}'",
                    field_name='extras',
                    suggested_fix="Use non-empty string keys in extras"
                ))
            
            # Check for reasonable value types
            if value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                issues.append(ValidationIssue(
                    concept_id=concept.id,
                    severity='WARNING',
                    category='FORMAT',
                    message=f"Extras value for '{key}' has unsupported type: {type(value)}",
                    field_name='extras',
                    suggested_fix="Use JSON-serializable types in extras"
                ))
        
        return issues
    
    def _validate_json_serialization(self, concept: OCLConcept) -> List[ValidationIssue]:
        """Validate that concept can be serialized to JSON"""
        issues = []
        
        try:
            # Test serialization
            json_str = concept.to_json()
            
            # Test deserialization
            json.loads(json_str)
            
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            issues.append(ValidationIssue(
                concept_id=concept.id,
                severity='ERROR',
                category='SERIALIZATION',
                message=f"Concept cannot be serialized to JSON: {str(e)}",
                suggested_fix="Ensure all concept fields are JSON-serializable"
            ))
        
        return issues
    
    def _is_valid_loinc_id(self, loinc_id: str) -> bool:
        """Check if ID matches valid LOINC patterns"""
        if not loinc_id:
            return False
        
        return any(pattern.match(loinc_id) for pattern in self.loinc_patterns.values())
    
    def generate_validation_report_text(self, report: ValidationReport) -> str:
        """Generate human-readable validation report"""
        lines = []
        lines.append("=" * 60)
        lines.append("OCL CONCEPT VALIDATION REPORT")
        lines.append("=" * 60)
        
        # Summary
        lines.append(f"Total Concepts: {report.total_concepts:,}")
        lines.append(f"Valid Concepts: {report.valid_concepts:,}")
        lines.append(f"Invalid Concepts: {report.invalid_concepts:,}")
        lines.append(f"Success Rate: {report.success_rate:.1f}%")
        lines.append("")
        
        # Issue summary
        if report.issues:
            issue_summary = report.get_issue_summary()
            lines.append("Issues by Category:")
            for category, count in sorted(issue_summary.items()):
                lines.append(f"  {category}: {count}")
            lines.append("")
        
        # Statistics
        if report.summary_stats:
            lines.append("Summary Statistics:")
            for key, value in report.summary_stats.items():
                if isinstance(value, dict):
                    lines.append(f"  {key}:")
                    for sub_key, sub_value in value.items():
                        lines.append(f"    {sub_key}: {sub_value}")
                elif isinstance(value, list):
                    lines.append(f"  {key}: {len(value)} items")
                else:
                    lines.append(f"  {key}: {value}")
            lines.append("")
        
        # Top errors (if any)
        errors = report.get_errors()
        if errors:
            lines.append("Top Validation Errors (first 10):")
            for error in errors[:10]:
                lines.append(f"  {error.concept_id}: {error.message}")
            if len(errors) > 10:
                lines.append(f"  ... and {len(errors) - 10} more errors")
            lines.append("")
        
        # Overall status
        if report.has_errors:
            lines.append("❌ VALIDATION FAILED - Errors must be resolved before OCL import")
        else:
            lines.append("✅ VALIDATION PASSED - Concepts are ready for OCL import")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


    def create_dual_validation_report(self, concepts: List[OCLConcept]) -> Dict[str, Any]:
        """
        Create a comprehensive validation report using both official OCL validation
        and enhanced validation suitable for LOINC concepts.
        
        Args:
            concepts: List of concepts to validate
            
        Returns:
            Dictionary with dual validation results
        """
        collection = ConceptCollection("Dual Validation Test")
        for concept in concepts:
            collection.add_concept(concept)
        
        # Run full validation
        report = self.validate_collection(collection)
        
        # Categorize issues by validation tier
        ocl_schema_issues = [issue for issue in report.issues if issue.category in ['OCL_SCHEMA', 'OCL_REQUIRED_FIELD', 'OCL_FORMAT']]
        enhanced_issues = [issue for issue in report.issues if issue.category in ['ENHANCED_REQUIRED_FIELD', 'LOINC_FORMAT', 'LOINC_CONVENTION']]
        quality_issues = [issue for issue in report.issues if issue.category in ['FORMAT', 'DUPLICATE', 'SERIALIZATION']]
        
        return {
            'total_concepts': len(concepts),
            'ocl_compliance': {
                'passing_concepts': len(concepts) - len([issue for issue in ocl_schema_issues if issue.severity == 'ERROR']),
                'issues': len(ocl_schema_issues),
                'ready_for_bulk_import': len([issue for issue in ocl_schema_issues if issue.severity == 'ERROR']) == 0
            },
            'enhanced_validation': {
                'usable_concepts': len(concepts) - len([issue for issue in enhanced_issues if issue.severity == 'ERROR']),
                'issues': len(enhanced_issues),
                'production_ready': len([issue for issue in enhanced_issues if issue.severity == 'ERROR']) == 0
            },
            'quality_validation': {
                'high_quality_concepts': len(concepts) - len([issue for issue in quality_issues if issue.severity in ['ERROR', 'WARNING']]),
                'issues': len(quality_issues)
            },
            'detailed_report': report
        }


def validate_concepts_for_ocl_import(concepts: List[OCLConcept], 
                                   strict_mode: bool = True) -> Dict[str, Any]:
    """
    Utility function to validate concepts for OCL bulk import.
    
    Combines official OCL schema validation with enhanced quality validation
    specifically designed for LOINC-derived concepts.
    
    Args:
        concepts: List of OCL concepts to validate
        strict_mode: If True, enhanced validation uses strict requirements
        
    Returns:
        Comprehensive validation report with recommendations
    """
    # Initialize validator with official schema support
    validator = OCLConceptValidator(strict_mode=strict_mode, use_official_schema=True)
    
    # Run dual validation
    report = validator.create_dual_validation_report(concepts)
    
    # Add recommendations
    recommendations = []
    
    if not report['ocl_compliance']['ready_for_bulk_import']:
        recommendations.append("❌ Fix OCL schema compliance issues before attempting bulk import")
    else:
        recommendations.append("✅ Concepts meet OCL bulk import requirements")
    
    if not report['enhanced_validation']['production_ready']:
        recommendations.append("⚠️ Add names and improve metadata for production-ready concepts")
    else:
        recommendations.append("✅ Concepts are production-ready with complete metadata")
    
    if report['quality_validation']['issues'] > 0:
        recommendations.append("📊 Review quality issues to improve concept usability")
    else:
        recommendations.append("✅ Concepts meet high quality standards")
    
    report['recommendations'] = recommendations
    
    return report


# Example usage and testing
if __name__ == "__main__":
    print("Enhanced OCL Concept Validator with Official Schema Support")
    print("Combines official OCL validation with comprehensive quality assurance")
    print("\nValidation tiers:")
    print("1. Official OCL Schema - Required for bulk import")
    print("2. Enhanced Validation - Names, multi-language, LOINC-specific")
    print("3. Quality Validation - Data integrity, duplicates, serialization")
    print("\nRecommended usage:")
    print("  from ocl_validator import validate_concepts_for_ocl_import")
    print("  report = validate_concepts_for_ocl_import(concepts)")
    print("  if report['ocl_compliance']['ready_for_bulk_import']:")
    print("      print('Ready for OCL import!')")

    