"""Schema validator for resource configurations."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import jsonschema
from jsonschema import Draft7Validator, validators

from cdk_templates.models import ValidationResult, ValidationError, Configuration


class SchemaValidator:
    """Validates resource configurations against JSON Schema definitions."""

    def __init__(self, schemas_dir: Optional[str] = None):
        """
        Initialize the SchemaValidator.

        Args:
            schemas_dir: Directory containing JSON schema files.
                        Defaults to 'schemas/' in the project root.
        """
        if schemas_dir is None:
            # Default to schemas/ directory relative to project root
            schemas_dir = Path(__file__).parent.parent / "schemas"
        else:
            schemas_dir = Path(schemas_dir)

        self.schemas_dir = schemas_dir
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._load_schemas()

    def _load_schemas(self):
        """Load all JSON schema files from the schemas directory."""
        if not self.schemas_dir.exists():
            raise FileNotFoundError(f"Schemas directory not found: {self.schemas_dir}")

        for schema_file in self.schemas_dir.glob("*.json"):
            resource_type = schema_file.stem  # filename without extension
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    self._schemas[resource_type] = schema
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load schema file {schema_file}: {str(e)}"
                )

    def get_schema(self, resource_type: str) -> Dict[str, Any]:
        """
        Get the JSON schema for a specific resource type.

        Args:
            resource_type: Type of resource (vpc, ec2, rds, s3)

        Returns:
            JSON schema dictionary

        Raises:
            ValueError: If schema for resource type is not found
        """
        if resource_type not in self._schemas:
            raise ValueError(
                f"No schema found for resource type '{resource_type}'. "
                f"Available types: {', '.join(self._schemas.keys())}"
            )
        return self._schemas[resource_type]

    def validate(self, config: Configuration) -> ValidationResult:
        """
        Validate complete configuration against all schemas.

        Args:
            config: Configuration object to validate

        Returns:
            ValidationResult with all validation errors and warnings
        """
        all_errors = []
        all_warnings = []

        # Validate each resource
        for idx, resource in enumerate(config.resources):
            result = self.validate_resource(
                resource.resource_type,
                resource.properties
            )

            # Add resource index to field paths for clarity
            for error in result.errors:
                error.field_path = f"resources[{idx}].properties.{error.field_path}"
                all_errors.append(error)

            for warning in result.warnings:
                warning.field_path = f"resources[{idx}].properties.{warning.field_path}"
                all_warnings.append(warning)

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )

    def validate_resource(
        self,
        resource_type: str,
        resource_config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a single resource configuration against its schema.

        Args:
            resource_type: Type of resource (vpc, ec2, rds, s3)
            resource_config: Resource configuration dictionary

        Returns:
            ValidationResult with validation errors and warnings
        """
        errors = []
        warnings = []

        try:
            schema = self.get_schema(resource_type)
        except ValueError as e:
            errors.append(ValidationError(
                field_path="resource_type",
                message=str(e),
                error_code="UNKNOWN_RESOURCE_TYPE",
                severity="ERROR"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Create validator with default values support
        validator = self._create_validator_with_defaults(schema)

        # Validate against schema
        validation_errors = list(validator.iter_errors(resource_config))

        for error in validation_errors:
            # Build field path from error path
            field_path = ".".join(str(p) for p in error.path) if error.path else "root"

            # Generate descriptive error message
            error_message = self._format_error_message(error, resource_config)

            errors.append(ValidationError(
                field_path=field_path,
                message=error_message,
                error_code=self._get_error_code(error),
                severity="ERROR"
            ))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _create_validator_with_defaults(self, schema: Dict[str, Any]) -> Draft7Validator:
        """
        Create a JSON Schema validator that applies default values.

        Args:
            schema: JSON schema dictionary

        Returns:
            Draft7Validator instance
        """
        # Extend the validator to apply defaults
        def set_defaults(validator, properties, instance, schema):
            """Apply default values from schema to instance."""
            for property, subschema in properties.items():
                if "default" in subschema:
                    instance.setdefault(property, subschema["default"])

            # Continue with normal validation
            for error in Draft7Validator.VALIDATORS["properties"](
                validator, properties, instance, schema
            ):
                yield error

        # Create validator class with default handling
        all_validators = dict(Draft7Validator.VALIDATORS)
        all_validators["properties"] = set_defaults
        DefaultValidatingValidator = validators.create(
            meta_schema=Draft7Validator.META_SCHEMA,
            validators=all_validators
        )

        return DefaultValidatingValidator(schema)

    def _format_error_message(
        self,
        error: jsonschema.exceptions.ValidationError,
        resource_config: Dict[str, Any]
    ) -> str:
        """
        Generate a descriptive error message from a validation error.

        Args:
            error: jsonschema ValidationError
            resource_config: Resource configuration being validated

        Returns:
            Formatted error message
        """
        # Get the field path
        field_path = ".".join(str(p) for p in error.path) if error.path else "root"

        # Get the actual value that failed validation
        actual_value = resource_config
        for key in error.path:
            if isinstance(actual_value, dict) and key in actual_value:
                actual_value = actual_value[key]
            elif isinstance(actual_value, list) and isinstance(key, int):
                actual_value = actual_value[key]
            else:
                actual_value = None
                break

        # Format message based on error type
        if error.validator == "required":
            missing_field = error.message.split("'")[1]
            return f"Missing required field '{missing_field}'"

        elif error.validator == "type":
            expected_type = error.validator_value
            return f"Invalid type for field '{field_path}'. Expected {expected_type}, got {type(actual_value).__name__}"

        elif error.validator == "pattern":
            pattern = error.validator_value
            return f"Value '{actual_value}' does not match required pattern: {pattern}"

        elif error.validator == "enum":
            allowed_values = ", ".join(str(v) for v in error.validator_value)
            return f"Value '{actual_value}' is not one of allowed values: {allowed_values}"

        elif error.validator == "minimum":
            minimum = error.validator_value
            return f"Value {actual_value} is less than minimum allowed value {minimum}"

        elif error.validator == "maximum":
            maximum = error.validator_value
            return f"Value {actual_value} is greater than maximum allowed value {maximum}"

        elif error.validator == "minLength":
            min_length = error.validator_value
            return f"String length {len(actual_value)} is less than minimum length {min_length}"

        elif error.validator == "maxLength":
            max_length = error.validator_value
            return f"String length {len(actual_value)} is greater than maximum length {max_length}"

        elif error.validator == "minItems":
            min_items = error.validator_value
            return f"Array has {len(actual_value)} items, minimum is {min_items}"

        elif error.validator == "maxItems":
            max_items = error.validator_value
            return f"Array has {len(actual_value)} items, maximum is {max_items}"

        else:
            # Default to the jsonschema error message
            return error.message

    def _get_error_code(self, error: jsonschema.exceptions.ValidationError) -> str:
        """
        Get an error code from a validation error.

        Args:
            error: jsonschema ValidationError

        Returns:
            Error code string
        """
        error_code_map = {
            "required": "MISSING_REQUIRED_FIELD",
            "type": "INVALID_TYPE",
            "pattern": "PATTERN_MISMATCH",
            "enum": "INVALID_ENUM_VALUE",
            "minimum": "VALUE_TOO_SMALL",
            "maximum": "VALUE_TOO_LARGE",
            "minLength": "STRING_TOO_SHORT",
            "maxLength": "STRING_TOO_LONG",
            "minItems": "ARRAY_TOO_SHORT",
            "maxItems": "ARRAY_TOO_LONG",
        }

        return error_code_map.get(error.validator, "VALIDATION_ERROR")
