#!/usr/bin/env python3
"""
Enhanced LOINC Data Validator - Fixed Version

This module provides comprehensive validation for LOINC data files with realistic,
production-oriented validation rules. This version has been corrected to:

1. Support LOINC codes with 1-6 digits (not just 5-6)
2. Remove ExternallyDefinedReleaseDate from recommended columns (doesn't exist in real files)

Validation Categories:
- CRITICAL (ERROR): Issues that would block OCL transformation
- QUALITY (WARNING): Data quality insights that don't block processing  
- STATS (INFO): Statistics and metrics for monitoring

Author: LOINC OCL Transform Project
Date: July 2025 (Fixed)
"""

import re
import logging
import pandas as pd
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ValidationIssue:
    """Represents a single validation issue"""
    rule_name: str
    severity: str  # ERROR, WARNING, INFO
    message: str
    file_name: str
    column_name: Optional[str] = None
    row_number: Optional[int] = None
    count: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationRule:
    """Represents a validation rule"""
    name: str
    description: str
    severity: str  # ERROR, WARNING, INFO
    rule_type: str  # CRITICAL, QUALITY, CROSS_REF, STATS
    validator_func: str  # Method name to call


@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    total_files_validated: int
    total_rows_validated: int
    total_issues: int
    error_count: int
    warning_count: int
    info_count: int
    issues: List[ValidationIssue]
    
    def __post_init__(self):
        if not hasattr(self, 'issues'):
            self.issues = []
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue to the report"""
        self.issues.append(issue)
        self.total_issues += 1
        
        if issue.severity == "ERROR":
            self.error_count += 1
        elif issue.severity == "WARNING":
            self.warning_count += 1
        elif issue.severity == "INFO":
            self.info_count += 1
    
    def is_valid(self) -> bool:
        """Returns True if validation passed (no critical errors)"""
        return self.error_count == 0


class DataValidator:
    """
    Enhanced LOINC Data Validator
    
    Provides meaningful validation levels:
    1. CRITICAL (ERROR): Required for OCL transformation
    2. IMPORTANT (WARNING): Data quality issues but not transformation blockers
    3. INFORMATIONAL (INFO): Statistics and recommendations
    """
    
    def __init__(self, config_manager=None):
        """
        Initialize DataValidator
        
        Args:
            config_manager: Optional ConfigManager instance for settings
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Store loaded data for cross-reference validation
        self.loaded_data: Dict[str, pd.DataFrame] = {}
        self.validation_rules: List[ValidationRule] = []
        
        # LOINC Model-specific patterns (more lenient for real-world data)
        self.patterns = {
            'loinc_code': re.compile(r'^\d{1,6}-\d{1,2}$'),  # Allow 1 to 6 digits (FIXED)
            'part_number': re.compile(r'^LP\d+(-\d+)?$'),     # e.g., "LP12345-6"
            'answer_list_id': re.compile(r'^LL\d+-\d+$'),     # e.g., "LL123-4"
            'answer_string_id': re.compile(r'^LA\d+-\d+$'),   # e.g., "LA123-4"
        }
        
        # LOINC Model Critical Requirements (corrected column names)
        self.critical_fields = {
            'Loinc.csv': ['LOINC_NUM', 'LONG_COMMON_NAME', 'STATUS'],
            'Part.csv': ['PartNumber', 'PartDisplayName', 'PartTypeName'],
            'AnswerList.csv': ['AnswerListId', 'AnswerListName'],
            'LoincAnswerListLink.csv': ['LoincNumber', 'AnswerListId'],  # Corrected column name
            'PanelsAndForms.csv': ['Loinc', 'ParentLoinc']  # Corrected column name
        }
        
        # Valid status values (from LOINC Model requirements)
        self.valid_statuses = ['ACTIVE', 'TRIAL', 'DISCOURAGED', 'DEPRECATED']
        
        # Initialize validation rules
        self._initialize_loinc_validation_rules()

    def _initialize_loinc_validation_rules(self) -> None:
        """Initialize LOINC model-specific validation rules"""
        
        # CRITICAL VALIDATION RULES (These cause ERROR-level failures)
        self.validation_rules.extend([
            ValidationRule(
                name="critical_primary_keys",
                description="Check for missing primary key values",
                severity="ERROR",
                rule_type="CRITICAL",
                validator_func="validate_critical_primary_keys"
            ),
            ValidationRule(
                name="critical_required_fields",
                description="Check for missing values in transformation-critical fields",
                severity="ERROR",
                rule_type="CRITICAL",
                validator_func="validate_critical_required_fields"
            ),
            ValidationRule(
                name="duplicate_primary_keys",
                description="Check for duplicate primary key values",
                severity="ERROR",
                rule_type="CRITICAL",
                validator_func="validate_no_duplicates"
            ),
            ValidationRule(
                name="loinc_code_format",
                description="Validate LOINC code format (required for OCL concept creation)",
                severity="ERROR",
                rule_type="CRITICAL",
                validator_func="validate_loinc_code_format"
            ),
            ValidationRule(
                name="valid_status_values",
                description="Validate STATUS field contains valid LOINC values",
                severity="ERROR",
                rule_type="CRITICAL",
                validator_func="validate_status_values"
            )
        ])
        
        # IMPORTANT VALIDATION RULES (These cause WARNING-level issues)
        self.validation_rules.extend([
            ValidationRule(
                name="recommended_columns",
                description="Check for presence of recommended columns",
                severity="WARNING",
                rule_type="QUALITY",
                validator_func="validate_recommended_columns"
            ),
            ValidationRule(
                name="data_format_patterns",
                description="Validate data format patterns for parts and answer lists",
                severity="WARNING",
                rule_type="QUALITY",
                validator_func="validate_format_patterns"
            ),
            ValidationRule(
                name="reasonable_name_lengths",
                description="Check for unusually short or long names",
                severity="WARNING",
                rule_type="QUALITY",
                validator_func="validate_name_lengths"
            ),
            ValidationRule(
                name="cross_reference_integrity",
                description="Check cross-file reference integrity",
                severity="WARNING",
                rule_type="CROSS_REF",
                validator_func="validate_cross_references"
            )
        ])
        
        # INFORMATIONAL RULES (These provide statistics and insights)
        self.validation_rules.extend([
            ValidationRule(
                name="file_statistics",
                description="Generate file statistics and coverage metrics",
                severity="INFO",
                rule_type="STATS",
                validator_func="generate_file_statistics"
            ),
            ValidationRule(
                name="encoding_analysis",
                description="Analyze character encoding and special characters",
                severity="INFO",
                rule_type="STATS",
                validator_func="analyze_encoding"
            )
        ])

    def validate_data(self, data_dict: Dict[str, pd.DataFrame]) -> ValidationReport:
        """
        Perform comprehensive validation on loaded LOINC data
        
        Args:
            data_dict: Dictionary of filename -> DataFrame
            
        Returns:
            ValidationReport: Comprehensive validation results
        """
        self.loaded_data = data_dict
        report = ValidationReport(
            total_files_validated=len(data_dict),
            total_rows_validated=sum(len(df) for df in data_dict.values()),
            total_issues=0,
            error_count=0,
            warning_count=0,
            info_count=0
        )
        
        self.logger.info(f"Starting LOINC model validation on {len(data_dict)} files...")
        
        # Run validation rules by priority (critical first)
        critical_rules = [r for r in self.validation_rules if r.severity == "ERROR"]
        warning_rules = [r for r in self.validation_rules if r.severity == "WARNING"]
        info_rules = [r for r in self.validation_rules if r.severity == "INFO"]
        
        # Run critical validations first
        for rule in critical_rules:
            self._run_validation_rule(rule, report)
            
        # Only continue with warnings/info if no critical errors
        if report.error_count == 0:
            self.logger.info("Critical validation passed. Running quality checks...")
            
            for rule in warning_rules:
                self._run_validation_rule(rule, report)
                
            for rule in info_rules:
                self._run_validation_rule(rule, report)
        else:
            self.logger.warning(f"Critical validation failed with {report.error_count} errors. Skipping quality checks.")
        
        # Generate summary
        self._generate_validation_summary(report)
        
        return report

    def _run_validation_rule(self, rule: ValidationRule, report: ValidationReport) -> None:
        """Run a single validation rule"""
        try:
            # Get the validator function
            validator_func = getattr(self, rule.validator_func)
            
            # Run the validation
            validator_func(report)
            
        except Exception as e:
            self.logger.error(f"Error running validation rule '{rule.name}': {e}")
            report.add_issue(ValidationIssue(
                rule_name=rule.name,
                severity="ERROR",
                message=f"Validation rule failed: {str(e)}",
                file_name="SYSTEM"
            ))

    def validate_critical_primary_keys(self, report: ValidationReport) -> None:
        """Check for missing primary key values in critical files"""
        primary_keys = {
            'Loinc.csv': 'LOINC_NUM',
            'Part.csv': 'PartNumber',
            'AnswerList.csv': 'AnswerListId'
        }
        
        for filename, df in self.loaded_data.items():
            if filename in primary_keys:
                key_field = primary_keys[filename]
                if key_field in df.columns:
                    null_count = df[key_field].isnull().sum()
                    if null_count > 0:
                        report.add_issue(ValidationIssue(
                            rule_name="critical_primary_keys",
                            severity="ERROR",
                            message=f"Found {null_count} missing values in primary key field {key_field}",
                            file_name=filename,
                            column_name=key_field,
                            count=null_count
                        ))

    def validate_critical_required_fields(self, report: ValidationReport) -> None:
        """Check for missing values in transformation-critical fields"""
        for filename, df in self.loaded_data.items():
            if filename in self.critical_fields:
                for field in self.critical_fields[filename]:
                    if field not in df.columns:
                        report.add_issue(ValidationIssue(
                            rule_name="critical_required_fields",
                            severity="ERROR",
                            message=f"Critical field '{field}' missing from {filename}",
                            file_name=filename,
                            column_name=field
                        ))
                    else:
                        # Check for excessive missing values in critical fields
                        null_count = df[field].isnull().sum()
                        total_rows = len(df)
                        null_percentage = (null_count / total_rows) * 100 if total_rows > 0 else 0
                        
                        # Only flag as ERROR if >50% of critical field is missing
                        if null_percentage > 50:
                            report.add_issue(ValidationIssue(
                                rule_name="critical_required_fields",
                                severity="ERROR",
                                message=f"Critical field '{field}' missing in {null_percentage:.1f}% of records",
                                file_name=filename,
                                column_name=field,
                                count=null_count
                            ))

    def validate_no_duplicates(self, report: ValidationReport) -> None:
        """Check for duplicate primary key values"""
        # Only validate files with clear, simple primary keys
        primary_keys = {
            'Loinc.csv': 'LOINC_NUM',
            'Part.csv': 'PartNumber',
            # AnswerList.csv intentionally omitted - AnswerListId repeats for each answer option
            # LoincAnswerListLink.csv and PanelsAndForms.csv omitted - complex relational structure
        }
        
        for filename, df in self.loaded_data.items():
            if filename in primary_keys:
                key_field = primary_keys[filename]
                if key_field in df.columns:
                    duplicates = df[df[key_field].duplicated(keep=False)]
                    if len(duplicates) > 0:
                        report.add_issue(ValidationIssue(
                            rule_name="duplicate_primary_keys",
                            severity="ERROR",
                            message=f"Found {len(duplicates)} duplicate values in primary key {key_field}",
                            file_name=filename,
                            column_name=key_field,
                            count=len(duplicates)
                        ))

    def validate_loinc_code_format(self, report: ValidationReport) -> None:
        """Validate LOINC code format (critical for OCL concept creation)"""
        if 'Loinc.csv' in self.loaded_data:
            df = self.loaded_data['Loinc.csv']
            if 'LOINC_NUM' in df.columns:
                # Only check non-null values
                valid_codes = df[df['LOINC_NUM'].notna()]
                invalid_format = ~valid_codes['LOINC_NUM'].str.match(self.patterns['loinc_code'])
                invalid_count = invalid_format.sum()
                
                if invalid_count > 0:
                    report.add_issue(ValidationIssue(
                        rule_name="loinc_code_format",
                        severity="ERROR",
                        message=f"Found {invalid_count} LOINC codes with invalid format (should be N-N to NNNNNN-N)",
                        file_name='Loinc.csv',
                        column_name='LOINC_NUM',
                        count=invalid_count
                    ))

    def validate_status_values(self, report: ValidationReport) -> None:
        """Validate STATUS field contains valid LOINC values"""
        if 'Loinc.csv' in self.loaded_data:
            df = self.loaded_data['Loinc.csv']
            if 'STATUS' in df.columns:
                invalid_statuses = ~df['STATUS'].isin(self.valid_statuses + [None, ''])
                invalid_count = invalid_statuses.sum()
                
                if invalid_count > 0:
                    unique_invalid = df[invalid_statuses]['STATUS'].unique()
                    report.add_issue(ValidationIssue(
                        rule_name="valid_status_values",
                        severity="ERROR",
                        message=f"Found {invalid_count} records with invalid STATUS values: {list(unique_invalid)}",
                        file_name='Loinc.csv',
                        column_name='STATUS',
                        count=invalid_count
                    ))

    def validate_recommended_columns(self, report: ValidationReport) -> None:
        """Check for presence of recommended columns (WARNING level)"""
        recommended_cols = {
            'Loinc.csv': ['SHORTNAME', 'CLASS', 'COMPONENT', 'PROPERTY', 'TIME_ASPCT', 'SYSTEM', 'SCALE_TYP', 'METHOD_TYP'],
            'Part.csv': ['PartName', 'Status'],
            'AnswerList.csv': ['ExtDefinedYN']  # FIXED: Removed ExternallyDefinedReleaseDate
        }
        
        for filename, df in self.loaded_data.items():
            if filename in recommended_cols:
                missing_cols = [col for col in recommended_cols[filename] if col not in df.columns]
                if missing_cols:
                    report.add_issue(ValidationIssue(
                        rule_name="recommended_columns",
                        severity="WARNING",
                        message=f"Recommended columns missing: {missing_cols}",
                        file_name=filename,
                        count=len(missing_cols)
                    ))

    def validate_format_patterns(self, report: ValidationReport) -> None:
        """Validate data format patterns (WARNING level)"""
        format_checks = [
            ('Part.csv', 'PartNumber', self.patterns['part_number']),
            ('AnswerList.csv', 'AnswerListId', self.patterns['answer_list_id'])
        ]
        
        for filename, column, pattern in format_checks:
            if filename in self.loaded_data:
                df = self.loaded_data[filename]
                if column in df.columns:
                    valid_values = df[df[column].notna()]
                    if len(valid_values) > 0:
                        invalid_format = ~valid_values[column].str.match(pattern)
                        invalid_count = invalid_format.sum()
                        
                        if invalid_count > 0:
                            report.add_issue(ValidationIssue(
                                rule_name="data_format_patterns",
                                severity="WARNING",
                                message=f"Found {invalid_count} records with non-standard {column} format",
                                file_name=filename,
                                column_name=column,
                                count=invalid_count
                            ))

    def validate_name_lengths(self, report: ValidationReport) -> None:
        """Check for unusually short or long names (WARNING level)"""
        name_fields = [
            ('Loinc.csv', 'LONG_COMMON_NAME', 10, 500),
            ('Part.csv', 'PartDisplayName', 3, 300),
            ('AnswerList.csv', 'AnswerListName', 3, 200)
        ]
        
        for filename, column, min_len, max_len in name_fields:
            if filename in self.loaded_data:
                df = self.loaded_data[filename]
                if column in df.columns:
                    valid_names = df[df[column].notna()]
                    if len(valid_names) > 0:
                        name_lengths = valid_names[column].str.len()
                        too_short = (name_lengths < min_len).sum()
                        too_long = (name_lengths > max_len).sum()
                        
                        if too_short > 0:
                            report.add_issue(ValidationIssue(
                                rule_name="reasonable_name_lengths",
                                severity="WARNING",
                                message=f"Found {too_short} records with unusually short {column} (< {min_len} chars)",
                                file_name=filename,
                                column_name=column,
                                count=too_short
                            ))
                            
                        if too_long > 0:
                            report.add_issue(ValidationIssue(
                                rule_name="reasonable_name_lengths",
                                severity="WARNING",
                                message=f"Found {too_long} records with unusually long {column} (> {max_len} chars)",
                                file_name=filename,
                                column_name=column,
                                count=too_long
                            ))

    def validate_cross_references(self, report: ValidationReport) -> None:
        """Check cross-file reference integrity (WARNING level)"""
        # Check AnswerListId references between Loinc.csv and AnswerList.csv
        if 'Loinc.csv' in self.loaded_data and 'AnswerList.csv' in self.loaded_data:
            loinc_df = self.loaded_data['Loinc.csv']
            answer_lists_df = self.loaded_data['AnswerList.csv']
            
            if 'AnswerListId' in loinc_df.columns and 'AnswerListId' in answer_lists_df.columns:
                # Get non-null answer list references in LOINC
                loinc_refs = loinc_df[loinc_df['AnswerListId'].notna()]['AnswerListId'].unique()
                available_lists = answer_lists_df['AnswerListId'].unique()
                
                missing_refs = set(loinc_refs) - set(available_lists)
                if missing_refs:
                    report.add_issue(ValidationIssue(
                        rule_name="cross_reference_integrity",
                        severity="WARNING",
                        message=f"Found {len(missing_refs)} AnswerListId references in Loinc.csv not found in AnswerList.csv",
                        file_name='Loinc.csv',
                        column_name='AnswerListId',
                        count=len(missing_refs)
                    ))

    def generate_file_statistics(self, report: ValidationReport) -> None:
        """Generate file statistics and coverage metrics (INFO level)"""
        for filename, df in self.loaded_data.items():
            row_count = len(df)
            col_count = len(df.columns)
            
            # Calculate completeness for key fields
            completeness_stats = {}
            if filename in self.critical_fields:
                for field in self.critical_fields[filename]:
                    if field in df.columns:
                        non_null_count = df[field].notna().sum()
                        completeness = (non_null_count / row_count) * 100 if row_count > 0 else 0
                        completeness_stats[field] = completeness
            
            stats_message = f"File: {row_count:,} rows, {col_count} columns"
            if completeness_stats:
                stats_details = [f"{field}: {pct:.1f}%" for field, pct in completeness_stats.items()]
                stats_message += f". Key field completeness: {', '.join(stats_details)}"
            
            report.add_issue(ValidationIssue(
                rule_name="file_statistics",
                severity="INFO",
                message=stats_message,
                file_name=filename
            ))

    def analyze_encoding(self, report: ValidationReport) -> None:
        """Analyze character encoding and special characters (INFO level)"""
        for filename, df in self.loaded_data.items():
            text_columns = df.select_dtypes(include=['object']).columns
            special_char_count = 0
            
            for col in text_columns:
                # Count non-ASCII characters
                text_data = df[col].dropna().astype(str)
                for text in text_data:
                    special_char_count += sum(1 for char in text if ord(char) > 127)
            
            if special_char_count > 0:
                report.add_issue(ValidationIssue(
                    rule_name="encoding_analysis",
                    severity="INFO",
                    message=f"Found {special_char_count} non-ASCII characters (international characters)",
                    file_name=filename,
                    count=special_char_count
                ))

    def _generate_validation_summary(self, report: ValidationReport) -> None:
        """Generate validation summary and log results"""
        self.logger.info("=" * 60)
        self.logger.info("LOINC VALIDATION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Files validated: {report.total_files_validated}")
        self.logger.info(f"Total records: {report.total_rows_validated:,}")
        self.logger.info(f"Total issues: {report.total_issues:,}")
        self.logger.info(f"  - Errors (critical): {report.error_count:,}")
        self.logger.info(f"  - Warnings (quality): {report.warning_count:,}")
        self.logger.info(f"  - Info (statistics): {report.info_count:,}")
        
        if report.error_count == 0:
            self.logger.info("✅ VALIDATION PASSED - Ready for OCL transformation")
        else:
            self.logger.error("❌ VALIDATION FAILED - Critical errors must be resolved")
            
        # Log top issues by severity
        errors = [issue for issue in report.issues if issue.severity == "ERROR"]
        if errors:
            self.logger.error("Critical errors that must be resolved:")
            for error in errors[:5]:  # Show top 5
                self.logger.error(f"  - {error.file_name}: {error.message}")
                
        self.logger.info("=" * 60)

    def save_detailed_report(self, report: ValidationReport, output_path: Path) -> None:
        """Save detailed validation report to file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("LOINC to OCL Transformation - Validation Report (FIXED VERSION)\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Files validated: {report.total_files_validated}\n")
            f.write(f"Total records: {report.total_rows_validated:,}\n")
            f.write(f"Validation result: {'✅ PASSED' if report.is_valid() else '❌ FAILED'}\n")
            f.write("\n")
            
            f.write("ISSUE SUMMARY\n")
            f.write("-" * 40 + "\n")
            f.write(f"🔴 Critical Errors: {report.error_count:,}\n")
            f.write(f"🟡 Quality Warnings: {report.warning_count:,}\n")
            f.write(f"🔵 Informational: {report.info_count:,}\n")
            f.write(f"📊 Total Issues: {report.total_issues:,}\n")
            f.write("\n")
            
            # Group issues by severity
            errors = [issue for issue in report.issues if issue.severity == "ERROR"]
            warnings = [issue for issue in report.issues if issue.severity == "WARNING"]
            info = [issue for issue in report.issues if issue.severity == "INFO"]
            
            if errors:
                f.write("🔴 CRITICAL ERRORS (Must fix)\n")
                f.write("-" * 40 + "\n")
                for error in errors:
                    f.write(f"{error.file_name}: {error.message}\n")
                    if error.count:
                        f.write(f"   Count: {error.count}\n")
                f.write("\n")
            
            if warnings:
                f.write("🟡 QUALITY WARNINGS (Informational)\n")
                f.write("-" * 40 + "\n")
                for warning in warnings:
                    f.write(f"{warning.file_name}: {warning.message}\n")
                    if warning.count:
                        f.write(f"   Count: {warning.count}\n")
                f.write("\n")
            
            if info:
                f.write("🔵 INFORMATIONAL (Statistics)\n")
                f.write("-" * 40 + "\n")
                for item in info:
                    f.write(f"{item.file_name}: {item.message}\n")
                f.write("\n")
            
            f.write("VALIDATION FIXES IMPLEMENTED\n")
            f.write("-" * 40 + "\n")
            f.write("1. LOINC code format: Now supports 1-6 digits (was 1-5)\n")
            f.write("2. Removed ExternallyDefinedReleaseDate validation (field doesn't exist)\n")
            f.write("3. Updated documentation to reflect correct LOINC code patterns\n")
            f.write("\n")
            
        self.logger.info(f"Detailed validation report saved to: {output_path}")


if __name__ == "__main__":
    # Example usage
    import sys
    
    print("LOINC Data Validator - Fixed Version")
    print("=" * 50)
    print("This validator has been corrected to:")
    print("1. Support LOINC codes with 1-6 digits (not just 5-6)")
    print("2. Remove ExternallyDefinedReleaseDate validation")
    print()
    print("Use this validator with the DataLoader or import as a module.")
    print("Example:")
    print("  from validator import DataValidator")
    print("  validator = DataValidator()")
    print("  report = validator.validate_data(loaded_data_dict)")