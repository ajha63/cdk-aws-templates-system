"""Custom exception classes for the CDK AWS Templates System.

This module provides a comprehensive hierarchy of exceptions for different
error scenarios, with detailed error messages and suggestions for resolution.
"""

from typing import List, Optional, Dict, Any


class CDKTemplateSystemError(Exception):
    """Base exception for all CDK Template System errors."""
    
    def __init__(self, message: str, suggestions: Optional[List[str]] = None):
        """Initialize the exception.
        
        Args:
            message: Error message describing what went wrong
            suggestions: Optional list of suggestions for fixing the error
        """
        self.message = message
        self.suggestions = suggestions or []
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        """Format the error message with suggestions."""
        msg = self.message
        if self.suggestions:
            msg += "\n\nSuggestions:"
            for i, suggestion in enumerate(self.suggestions, 1):
                msg += f"\n  {i}. {suggestion}"
        return msg


class ConfigurationError(CDKTemplateSystemError):
    """Raised when configuration loading or parsing fails."""
    
    def __init__(
        self,
        message: str,
        field_path: Optional[str] = None,
        file_path: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        """Initialize configuration error.
        
        Args:
            message: Error message
            field_path: Path to the problematic field (e.g., "resources[0].properties.cidr")
            file_path: Path to the configuration file with the error
            suggestions: List of suggestions for fixing the error
        """
        self.field_path = field_path
        self.file_path = file_path
        
        # Build detailed message
        detailed_msg = "Configuration Error"
        if file_path:
            detailed_msg += f" in file '{file_path}'"
        if field_path:
            detailed_msg += f"\n  Path: {field_path}"
        detailed_msg += f"\n  Error: {message}"
        
        super().__init__(detailed_msg, suggestions)


class SchemaValidationError(ConfigurationError):
    """Raised when configuration fails schema validation."""
    
    def __init__(
        self,
        field_path: str,
        message: str,
        expected: Optional[str] = None,
        actual: Optional[Any] = None,
        file_path: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        """Initialize schema validation error.
        
        Args:
            field_path: Path to the invalid field
            message: Error message
            expected: Expected value or type
            actual: Actual value provided
            file_path: Path to the configuration file
            suggestions: List of suggestions
        """
        self.expected = expected
        self.actual = actual
        
        detailed_msg = message
        if expected:
            detailed_msg += f"\n  Expected: {expected}"
        if actual is not None:
            detailed_msg += f"\n  Actual: {actual}"
        
        super().__init__(detailed_msg, field_path, file_path, suggestions)


class MissingRequiredFieldError(SchemaValidationError):
    """Raised when a required field is missing from configuration."""
    
    def __init__(
        self,
        field_path: str,
        field_name: str,
        resource_type: Optional[str] = None,
        file_path: Optional[str] = None
    ):
        """Initialize missing required field error.
        
        Args:
            field_path: Path to the parent object
            field_name: Name of the missing field
            resource_type: Type of resource (vpc, ec2, etc.)
            file_path: Path to the configuration file
        """
        message = f"Required field '{field_name}' is missing"
        if resource_type:
            message += f" for resource type '{resource_type}'"
        
        suggestions = [
            f"Add the '{field_name}' field to your configuration",
            f"Check the schema documentation for '{resource_type or 'this resource'}' to see required fields"
        ]
        
        super().__init__(
            field_path=field_path,
            message=message,
            expected=f"Field '{field_name}' must be present",
            actual="Field is missing",
            file_path=file_path,
            suggestions=suggestions
        )


class InvalidFieldTypeError(SchemaValidationError):
    """Raised when a field has an invalid type."""
    
    def __init__(
        self,
        field_path: str,
        expected_type: str,
        actual_type: str,
        actual_value: Any,
        file_path: Optional[str] = None
    ):
        """Initialize invalid field type error.
        
        Args:
            field_path: Path to the invalid field
            expected_type: Expected type (e.g., "string", "integer")
            actual_type: Actual type received
            actual_value: The actual value
            file_path: Path to the configuration file
        """
        message = f"Invalid type for field"
        
        suggestions = [
            f"Change the value to a {expected_type}",
            f"Check the schema documentation for the correct type"
        ]
        
        super().__init__(
            field_path=field_path,
            message=message,
            expected=f"Type: {expected_type}",
            actual=f"Type: {actual_type}, Value: {actual_value}",
            file_path=file_path,
            suggestions=suggestions
        )


class InvalidFieldValueError(SchemaValidationError):
    """Raised when a field has an invalid value."""
    
    def __init__(
        self,
        field_path: str,
        message: str,
        actual_value: Any,
        valid_values: Optional[List[str]] = None,
        constraint: Optional[str] = None,
        file_path: Optional[str] = None
    ):
        """Initialize invalid field value error.
        
        Args:
            field_path: Path to the invalid field
            message: Error message
            actual_value: The actual value provided
            valid_values: List of valid values (for enum fields)
            constraint: Description of the constraint (e.g., "must be between 1 and 10")
            file_path: Path to the configuration file
        """
        suggestions = []
        expected = None
        
        if valid_values:
            expected = f"One of: {', '.join(str(v) for v in valid_values)}"
            suggestions.append(f"Use one of the valid values: {', '.join(str(v) for v in valid_values)}")
        elif constraint:
            expected = constraint
            suggestions.append(f"Ensure the value {constraint}")
        
        suggestions.append("Check the schema documentation for valid values and constraints")
        
        super().__init__(
            field_path=field_path,
            message=message,
            expected=expected,
            actual=actual_value,
            file_path=file_path,
            suggestions=suggestions
        )


class ResourceLinkError(CDKTemplateSystemError):
    """Base class for resource link errors."""
    pass


class CircularDependencyError(ResourceLinkError):
    """Raised when circular dependencies are detected between resources."""
    
    def __init__(self, cycle: List[str], dependency_chain: Optional[str] = None):
        """Initialize circular dependency error.
        
        Args:
            cycle: List of resource IDs forming the cycle
            dependency_chain: Visual representation of the dependency chain
        """
        self.cycle = cycle
        self.dependency_chain = dependency_chain
        
        message = "Circular dependency detected between resources"
        if dependency_chain:
            message += f"\n\n  Dependency chain:\n  {dependency_chain}"
        else:
            message += f"\n\n  Resources in cycle: {' -> '.join(cycle)} -> {cycle[0]}"
        
        suggestions = [
            "Remove one of the dependencies to break the cycle",
            "Restructure your resources to avoid circular references",
            "Consider using explicit outputs and imports instead of direct references"
        ]
        
        super().__init__(message, suggestions)


class DanglingReferenceError(ResourceLinkError):
    """Raised when a resource references a non-existent resource."""
    
    def __init__(
        self,
        source_resource: str,
        target_resource: str,
        field_path: str,
        available_resources: Optional[List[str]] = None
    ):
        """Initialize dangling reference error.
        
        Args:
            source_resource: Resource that contains the reference
            target_resource: Referenced resource that doesn't exist
            field_path: Path to the field containing the reference
            available_resources: List of available resource IDs
        """
        self.source_resource = source_resource
        self.target_resource = target_resource
        self.field_path = field_path
        self.available_resources = available_resources
        
        message = f"Resource '{source_resource}' references non-existent resource '{target_resource}'"
        message += f"\n  Field: {field_path}"
        
        suggestions = [
            f"Check that '{target_resource}' is defined in your configuration",
            "Verify the resource ID is spelled correctly",
            "Ensure the referenced resource is in the same configuration or a deployed stack"
        ]
        
        if available_resources:
            message += f"\n\n  Available resources: {', '.join(available_resources)}"
            suggestions.append(f"Use one of the available resources: {', '.join(available_resources)}")
        
        super().__init__(message, suggestions)


class InvalidResourceReferenceError(ResourceLinkError):
    """Raised when a resource reference has invalid format or type."""
    
    def __init__(
        self,
        source_resource: str,
        reference: str,
        field_path: str,
        reason: str
    ):
        """Initialize invalid resource reference error.
        
        Args:
            source_resource: Resource containing the invalid reference
            reference: The invalid reference string
            field_path: Path to the field with the reference
            reason: Reason why the reference is invalid
        """
        message = f"Invalid resource reference in '{source_resource}'"
        message += f"\n  Field: {field_path}"
        message += f"\n  Reference: {reference}"
        message += f"\n  Reason: {reason}"
        
        suggestions = [
            "Use the format: ${resource.<resource-id>.<property>}",
            "Example: ${resource.vpc-main.id}",
            "Ensure the reference syntax is correct"
        ]
        
        super().__init__(message, suggestions)


class AWSServiceLimitError(CDKTemplateSystemError):
    """Raised when configuration exceeds AWS service limits."""
    
    def __init__(
        self,
        resource_id: str,
        resource_type: str,
        limit_description: str,
        requested_value: Any,
        max_value: Any,
        documentation_url: Optional[str] = None
    ):
        """Initialize AWS service limit error.
        
        Args:
            resource_id: ID of the resource
            resource_type: Type of resource
            limit_description: Description of the limit
            requested_value: Value requested in configuration
            max_value: Maximum allowed value
            documentation_url: URL to AWS documentation
        """
        message = f"AWS Service Limit Exceeded for resource '{resource_id}' ({resource_type})"
        message += f"\n  Limit: {limit_description}"
        message += f"\n  Requested: {requested_value}"
        message += f"\n  Maximum: {max_value}"
        
        if documentation_url:
            message += f"\n  Documentation: {documentation_url}"
        
        suggestions = [
            f"Reduce the value to {max_value} or less",
            "Request a service limit increase from AWS Support if needed",
            "Consider alternative architectures that work within the limits"
        ]
        
        super().__init__(message, suggestions)


class NamingConstraintError(CDKTemplateSystemError):
    """Raised when a resource name violates AWS naming constraints."""
    
    def __init__(
        self,
        resource_id: str,
        resource_type: str,
        name: str,
        constraint: str,
        valid_pattern: Optional[str] = None
    ):
        """Initialize naming constraint error.
        
        Args:
            resource_id: ID of the resource
            resource_type: Type of resource
            name: The invalid name
            constraint: Description of the constraint violated
            valid_pattern: Valid naming pattern (regex or description)
        """
        message = f"Invalid name for resource '{resource_id}' ({resource_type})"
        message += f"\n  Name: {name}"
        message += f"\n  Constraint: {constraint}"
        
        if valid_pattern:
            message += f"\n  Valid pattern: {valid_pattern}"
        
        suggestions = [
            "Ensure the name meets AWS naming requirements",
            "Check for invalid characters, length limits, or format requirements",
            "Let the naming service generate the name automatically"
        ]
        
        super().__init__(message, suggestions)


class DeploymentRuleViolationError(CDKTemplateSystemError):
    """Raised when a deployment rule rejects a configuration."""
    
    def __init__(
        self,
        rule_name: str,
        resource_id: str,
        policy: str,
        violation: str,
        remediation: Optional[str] = None
    ):
        """Initialize deployment rule violation error.
        
        Args:
            rule_name: Name of the rule that was violated
            resource_id: ID of the resource
            policy: Description of the policy
            violation: Description of the violation
            remediation: Steps to fix the violation
        """
        message = f"Deployment Rule Violation: {rule_name}"
        message += f"\n  Resource: {resource_id}"
        message += f"\n  Policy: {policy}"
        message += f"\n  Violation: {violation}"
        
        suggestions = []
        if remediation:
            suggestions.append(remediation)
        suggestions.extend([
            "Review your configuration against the deployment rules",
            "Contact your infrastructure team if you need an exception"
        ])
        
        super().__init__(message, suggestions)


class CodeGenerationError(CDKTemplateSystemError):
    """Raised when CDK code generation fails."""
    
    def __init__(
        self,
        resource_id: str,
        template_name: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Initialize code generation error.
        
        Args:
            resource_id: ID of the resource being generated
            template_name: Name of the template that failed
            reason: Reason for the failure
            context: Additional context about the error
        """
        message = f"Code Generation Error for resource '{resource_id}'"
        message += f"\n  Template: {template_name}"
        message += f"\n  Reason: {reason}"
        
        if context:
            message += "\n  Context:"
            for key, value in context.items():
                message += f"\n    {key}: {value}"
        
        suggestions = [
            "Check the resource configuration for invalid values",
            "Verify all required fields are present",
            "Review the template documentation for this resource type"
        ]
        
        super().__init__(message, suggestions)


class ResourceRegistryError(CDKTemplateSystemError):
    """Raised when resource registry operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        """Initialize resource registry error.
        
        Args:
            message: Error message
            operation: The operation that failed (register, unregister, query, etc.)
        """
        if operation:
            message = f"Resource Registry Error ({operation}): {message}"
        else:
            message = f"Resource Registry Error: {message}"
        
        suggestions = [
            "Check that the registry file is not corrupted",
            "Ensure you have write permissions to the registry file",
            "Try backing up and recreating the registry if it's corrupted"
        ]
        
        super().__init__(message, suggestions)


class ValidationException(CDKTemplateSystemError):
    """Exception raised when configuration validation fails.
    
    This is raised by the validation engine when prevent_generation_on_failure
    is called and validation has failed.
    """
    
    def __init__(self, validation_errors: List[str]):
        """Initialize validation exception.
        
        Args:
            validation_errors: List of validation error messages
        """
        message = "Configuration validation failed with the following errors:"
        for error in validation_errors:
            message += f"\n  - {error}"
        
        suggestions = [
            "Fix all validation errors before attempting code generation",
            "Run validation separately to see detailed error reports",
            "Check the schema documentation for each resource type"
        ]
        
        super().__init__(message, suggestions)
