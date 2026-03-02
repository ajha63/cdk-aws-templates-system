"""Validation Engine for comprehensive pre-generation validation."""

from typing import List, Optional
from cdk_templates.models import (
    Configuration,
    ValidationResult,
    ValidationError
)
from cdk_templates.schema_validator import SchemaValidator
from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.deployment_rules import DeploymentRulesEngine
from cdk_templates.exceptions import ValidationException


class ValidationEngine:
    """
    Orchestrates comprehensive validation of configurations before code generation.
    
    Integrates:
    - SchemaValidator: Validates syntax and structure against JSON schemas
    - ResourceLinkResolver: Validates resource links and detects circular dependencies
    - DeploymentRulesEngine: Applies business rules and policies
    """
    
    def __init__(
        self,
        schema_validator: Optional[SchemaValidator] = None,
        link_resolver: Optional[ResourceLinkResolver] = None,
        rules_engine: Optional[DeploymentRulesEngine] = None
    ):
        """
        Initialize the ValidationEngine.
        
        Args:
            schema_validator: SchemaValidator instance (creates default if None)
            link_resolver: ResourceLinkResolver instance (creates default if None)
            rules_engine: DeploymentRulesEngine instance (creates default if None)
        """
        self.schema_validator = schema_validator or SchemaValidator()
        self.link_resolver = link_resolver or ResourceLinkResolver()
        self.rules_engine = rules_engine or DeploymentRulesEngine()
    
    def validate(
        self,
        config: Configuration,
        environment: str
    ) -> ValidationResult:
        """
        Perform comprehensive validation of configuration.
        
        Validation steps:
        1. Schema validation (syntax and structure)
        2. Resource link validation (references and circular dependencies)
        3. Deployment rules validation (business policies)
        
        All validations are run before reporting errors to provide
        comprehensive feedback.
        
        Args:
            config: Configuration to validate
            environment: Target environment (dev, staging, prod)
            
        Returns:
            ValidationResult with all errors and warnings found
        """
        all_errors: List[ValidationError] = []
        all_warnings: List[ValidationError] = []
        
        # Step 1: Schema Validation
        schema_result = self.schema_validator.validate(config)
        all_errors.extend(schema_result.errors)
        all_warnings.extend(schema_result.warnings)
        
        # Step 2: Resource Link Validation
        link_result = self.link_resolver.resolve_links(config)
        if not link_result.success:
            # Convert link resolution errors to ValidationError format
            for error_msg in link_result.errors:
                all_errors.append(ValidationError(
                    field_path="resources",
                    message=error_msg,
                    error_code="LINK_RESOLUTION_ERROR",
                    severity="ERROR"
                ))
            
            # Add cycle-specific errors
            for cycle in link_result.cycles:
                cycle_str = " -> ".join(cycle.resources + [cycle.resources[0]])
                all_errors.append(ValidationError(
                    field_path="resources",
                    message=f"Circular dependency detected: {cycle_str}",
                    error_code="CIRCULAR_DEPENDENCY",
                    severity="ERROR"
                ))
        
        # Step 3: Deployment Rules Validation
        rules_result = self.rules_engine.apply_rules(config, environment)
        
        # Convert rule rejections to ValidationError format
        for rejection in rules_result.rejections:
            all_errors.append(ValidationError(
                field_path=f"resources.{rejection.resource_id}",
                message=f"[{rejection.rule_name}] {rejection.reason}",
                error_code="RULE_VIOLATION",
                severity=rejection.severity
            ))
        
        # Convert rule errors to ValidationError format
        for error_msg in rules_result.errors:
            all_errors.append(ValidationError(
                field_path="configuration",
                message=error_msg,
                error_code="RULE_ERROR",
                severity="ERROR"
            ))
        
        # Determine overall validity
        is_valid = len(all_errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def generate_error_report(self, validation_result: ValidationResult) -> str:
        """
        Generate a detailed error report from validation results.
        
        Args:
            validation_result: ValidationResult to generate report from
            
        Returns:
            Formatted error report string
        """
        if validation_result.is_valid:
            return "✓ Configuration validation passed successfully.\n"
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("CONFIGURATION VALIDATION FAILED")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Group errors by severity
        errors = [e for e in validation_result.errors if e.severity == "ERROR"]
        warnings = [e for e in validation_result.errors if e.severity == "WARNING"]
        warnings.extend(validation_result.warnings)
        
        # Report errors
        if errors:
            report_lines.append(f"ERRORS ({len(errors)}):")
            report_lines.append("-" * 80)
            for idx, error in enumerate(errors, 1):
                report_lines.append(f"{idx}. [{error.error_code}] {error.field_path}")
                report_lines.append(f"   {error.message}")
                report_lines.append("")
        
        # Report warnings
        if warnings:
            report_lines.append(f"WARNINGS ({len(warnings)}):")
            report_lines.append("-" * 80)
            for idx, warning in enumerate(warnings, 1):
                report_lines.append(f"{idx}. [{warning.error_code}] {warning.field_path}")
                report_lines.append(f"   {warning.message}")
                report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append(f"Total: {len(errors)} error(s), {len(warnings)} warning(s)")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append("Code generation cannot proceed until all errors are resolved.")
        report_lines.append("")
        
        return "\n".join(report_lines)
    
    def validate_and_report(
        self,
        config: Configuration,
        environment: str
    ) -> tuple[bool, str]:
        """
        Validate configuration and generate a report.
        
        Convenience method that combines validation and report generation.
        
        Args:
            config: Configuration to validate
            environment: Target environment
            
        Returns:
            Tuple of (is_valid, report_string)
        """
        result = self.validate(config, environment)
        report = self.generate_error_report(result)
        return result.is_valid, report
    
    def prevent_generation_on_failure(
        self,
        config: Configuration,
        environment: str
    ) -> ValidationResult:
        """
        Validate configuration and raise exception if validation fails.
        
        This method enforces the requirement that code generation must not
        proceed if validation errors exist.
        
        Args:
            config: Configuration to validate
            environment: Target environment
            
        Returns:
            ValidationResult if validation passes
            
        Raises:
            ValidationException: If validation fails
        """
        result = self.validate(config, environment)
        
        if not result.is_valid:
            report = self.generate_error_report(result)
            # Extract error messages for the exception
            error_messages = []
            for error in result.errors:
                error_messages.append(f"{error.field_path}: {error.message}")
            
            raise ValidationException(validation_errors=error_messages)
        
        return result
    
    def __str__(self) -> str:
        """Return formatted error report."""
        return self.report
