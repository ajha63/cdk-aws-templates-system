"""Property-based tests for configuration loading and serialization."""

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from cdk_templates.config_loader import ConfigurationLoader
from tests.property.strategies import (
    configuration_strategy,
    resource_config_strategy,
    invalid_resource_config_strategy
)


class TestConfigurationProperties:
    """Property-based tests for Configuration operations."""

    @given(configuration_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000  # 5 seconds per test case
    )
    def test_property_42_configuration_round_trip_yaml(self, config):
        """
        Feature: cdk-aws-templates-system
        Property 42: For any valid configuration, loading the configuration and 
        then serializing it back to YAML SHALL produce a semantically 
        equivalent configuration.
        
        Validates: Requirements 10.5
        """
        loader = ConfigurationLoader()
        
        # Serialize to YAML
        yaml_str = loader.serialize_to_yaml(config)
        
        # Verify YAML string is not empty
        assert yaml_str.strip(), "Serialized YAML should not be empty"
        
        # Load back from YAML
        loaded_config = loader.load_from_yaml_string(yaml_str)
        
        # Verify equivalence - all fields should match
        assert loaded_config.version == config.version, \
            f"Version mismatch: {loaded_config.version} != {config.version}"
        
        assert loaded_config.metadata.project == config.metadata.project, \
            "Project metadata mismatch"
        assert loaded_config.metadata.owner == config.metadata.owner, \
            "Owner metadata mismatch"
        assert loaded_config.metadata.cost_center == config.metadata.cost_center, \
            "Cost center metadata mismatch"
        assert loaded_config.metadata.description == config.metadata.description, \
            "Description metadata mismatch"
        
        # Verify environments
        assert set(loaded_config.environments.keys()) == set(config.environments.keys()), \
            "Environment keys mismatch"
        
        for env_name in config.environments:
            orig_env = config.environments[env_name]
            loaded_env = loaded_config.environments[env_name]
            
            assert loaded_env.name == orig_env.name, \
                f"Environment {env_name} name mismatch"
            assert loaded_env.account_id == orig_env.account_id, \
                f"Environment {env_name} account_id mismatch"
            assert loaded_env.region == orig_env.region, \
                f"Environment {env_name} region mismatch"
            assert loaded_env.tags == orig_env.tags, \
                f"Environment {env_name} tags mismatch"
            assert loaded_env.overrides == orig_env.overrides, \
                f"Environment {env_name} overrides mismatch"
        
        # Verify resources
        assert len(loaded_config.resources) == len(config.resources), \
            f"Resource count mismatch: {len(loaded_config.resources)} != {len(config.resources)}"
        
        for i, (orig_resource, loaded_resource) in enumerate(zip(config.resources, loaded_config.resources)):
            assert loaded_resource.logical_id == orig_resource.logical_id, \
                f"Resource {i} logical_id mismatch"
            assert loaded_resource.resource_type == orig_resource.resource_type, \
                f"Resource {i} resource_type mismatch"
            assert loaded_resource.properties == orig_resource.properties, \
                f"Resource {i} properties mismatch"
            assert loaded_resource.tags == orig_resource.tags, \
                f"Resource {i} tags mismatch"
            assert loaded_resource.depends_on == orig_resource.depends_on, \
                f"Resource {i} depends_on mismatch"
        
        # Verify deployment rules
        assert loaded_config.deployment_rules == config.deployment_rules, \
            "Deployment rules mismatch"

    @given(configuration_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_42_configuration_round_trip_json(self, config):
        """
        Feature: cdk-aws-templates-system
        Property 42: For any valid configuration, loading the configuration and 
        then serializing it back to JSON SHALL produce a semantically 
        equivalent configuration.
        
        Validates: Requirements 10.5
        """
        loader = ConfigurationLoader()
        
        # Serialize to JSON
        json_str = loader.serialize_to_json(config)
        
        # Verify JSON string is not empty
        assert json_str.strip(), "Serialized JSON should not be empty"
        
        # Load back from JSON
        loaded_config = loader.load_from_json_string(json_str)
        
        # Verify equivalence - all fields should match
        assert loaded_config.version == config.version, \
            f"Version mismatch: {loaded_config.version} != {config.version}"
        
        assert loaded_config.metadata.project == config.metadata.project, \
            "Project metadata mismatch"
        assert loaded_config.metadata.owner == config.metadata.owner, \
            "Owner metadata mismatch"
        assert loaded_config.metadata.cost_center == config.metadata.cost_center, \
            "Cost center metadata mismatch"
        assert loaded_config.metadata.description == config.metadata.description, \
            "Description metadata mismatch"
        
        # Verify environments
        assert set(loaded_config.environments.keys()) == set(config.environments.keys()), \
            "Environment keys mismatch"
        
        for env_name in config.environments:
            orig_env = config.environments[env_name]
            loaded_env = loaded_config.environments[env_name]
            
            assert loaded_env.name == orig_env.name, \
                f"Environment {env_name} name mismatch"
            assert loaded_env.account_id == orig_env.account_id, \
                f"Environment {env_name} account_id mismatch"
            assert loaded_env.region == orig_env.region, \
                f"Environment {env_name} region mismatch"
            assert loaded_env.tags == orig_env.tags, \
                f"Environment {env_name} tags mismatch"
            assert loaded_env.overrides == orig_env.overrides, \
                f"Environment {env_name} overrides mismatch"
        
        # Verify resources
        assert len(loaded_config.resources) == len(config.resources), \
            f"Resource count mismatch: {len(loaded_config.resources)} != {len(config.resources)}"
        
        for i, (orig_resource, loaded_resource) in enumerate(zip(config.resources, loaded_config.resources)):
            assert loaded_resource.logical_id == orig_resource.logical_id, \
                f"Resource {i} logical_id mismatch"
            assert loaded_resource.resource_type == orig_resource.resource_type, \
                f"Resource {i} resource_type mismatch"
            assert loaded_resource.properties == orig_resource.properties, \
                f"Resource {i} properties mismatch"
            assert loaded_resource.tags == orig_resource.tags, \
                f"Resource {i} tags mismatch"
            assert loaded_resource.depends_on == orig_resource.depends_on, \
                f"Resource {i} depends_on mismatch"
        
        # Verify deployment rules
        assert loaded_config.deployment_rules == config.deployment_rules, \
            "Deployment rules mismatch"

    @given(configuration_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_42_yaml_json_equivalence(self, config):
        """
        Feature: cdk-aws-templates-system
        Property 42 (Extended): For any valid configuration, serializing to YAML 
        and JSON should produce semantically equivalent results when loaded back.
        
        Validates: Requirements 10.5
        """
        loader = ConfigurationLoader()
        
        # Serialize to both formats
        yaml_str = loader.serialize_to_yaml(config)
        json_str = loader.serialize_to_json(config)
        
        # Load back from both formats
        config_from_yaml = loader.load_from_yaml_string(yaml_str)
        config_from_json = loader.load_from_json_string(json_str)
        
        # Both should be equivalent to original
        assert config_from_yaml.version == config_from_json.version, \
            "YAML and JSON versions differ"
        assert config_from_yaml.metadata.project == config_from_json.metadata.project, \
            "YAML and JSON project metadata differ"
        assert len(config_from_yaml.resources) == len(config_from_json.resources), \
            "YAML and JSON resource counts differ"
        
        # Verify they match the original
        assert config_from_yaml.version == config.version
        assert config_from_json.version == config.version



class TestSchemaValidationProperties:
    """Property-based tests for Schema Validation."""

    @given(resource_config_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_9_valid_resource_passes_validation(self, resource_config):
        """
        Feature: cdk-aws-templates-system
        Property 9: Schema Validation - For any resource configuration that
        conforms to its JSON Schema, the Validation Engine SHALL validate
        all fields against the resource type's schema and return is_valid=True.

        Validates: Requirements 3.4
        """
        from cdk_templates.schema_validator import SchemaValidator

        validator = SchemaValidator()

        # Validate the resource
        result = validator.validate_resource(
            resource_config.resource_type,
            resource_config.properties
        )

        # Valid configurations should pass validation
        assert result.is_valid, \
            f"Valid {resource_config.resource_type} configuration should pass validation. " \
            f"Errors: {[e.message for e in result.errors]}"

        # Should have no errors
        assert len(result.errors) == 0, \
            f"Valid configuration should have no errors, got: {result.errors}"

    @given(invalid_resource_config_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_9_invalid_resource_fails_validation(self, resource_config):
        """
        Feature: cdk-aws-templates-system
        Property 9: Schema Validation - For any resource configuration that
        violates its JSON Schema (missing required fields, wrong types, or
        constraint violations), the Validation Engine SHALL reject the
        configuration with is_valid=False and provide error details.

        Validates: Requirements 3.4
        """
        from cdk_templates.schema_validator import SchemaValidator

        validator = SchemaValidator()

        # Validate the resource
        result = validator.validate_resource(
            resource_config.resource_type,
            resource_config.properties
        )

        # Invalid configurations should fail validation
        assert not result.is_valid, \
            f"Invalid {resource_config.resource_type} configuration should fail validation. " \
            f"Properties: {resource_config.properties}"

        # Should have at least one error
        assert len(result.errors) > 0, \
            f"Invalid configuration should have errors"

        # Each error should have required fields
        for error in result.errors:
            assert error.field_path, "Error should have field_path"
            assert error.message, "Error should have message"
            assert error.error_code, "Error should have error_code"
            assert error.severity, "Error should have severity"

    @given(configuration_strategy())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_9_configuration_validation_aggregates_errors(self, config):
        """
        Feature: cdk-aws-templates-system
        Property 9: Schema Validation - When validating a complete Configuration
        with multiple resources, the Validation Engine SHALL validate all
        resources and aggregate all validation errors.

        Validates: Requirements 3.4
        """
        from cdk_templates.schema_validator import SchemaValidator

        validator = SchemaValidator()

        # Validate the complete configuration
        result = validator.validate(config)

        # Result should have is_valid field
        assert isinstance(result.is_valid, bool), \
            "ValidationResult should have is_valid boolean field"

        # If there are errors, is_valid should be False
        if len(result.errors) > 0:
            assert not result.is_valid, \
                "Configuration with errors should have is_valid=False"

        # If is_valid is True, there should be no errors
        if result.is_valid:
            assert len(result.errors) == 0, \
                "Valid configuration should have no errors"

        # All errors should have proper structure
        for error in result.errors:
            assert error.field_path, "Error should have field_path"
            assert error.message, "Error should have message"
            assert error.error_code, "Error should have error_code"
            assert error.severity in ['ERROR', 'WARNING'], \
                f"Error severity should be ERROR or WARNING, got {error.severity}"

            # Field path should include resource index for multi-resource configs
            if len(config.resources) > 0:
                assert 'resources[' in error.field_path, \
                    f"Error field_path should include resource index, got: {error.field_path}"

    @given(st.sampled_from(['vpc', 'ec2', 'rds', 's3']))
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_9_type_constraints_enforced(self, resource_type):
        """
        Feature: cdk-aws-templates-system
        Property 9: Schema Validation - The Validation Engine SHALL enforce
        type constraints (string, integer, boolean, array, object) as defined
        in the JSON Schema for each resource type.

        Validates: Requirements 3.4
        """
        from cdk_templates.schema_validator import SchemaValidator

        validator = SchemaValidator()

        # Create a configuration with wrong types
        if resource_type == 'vpc':
            # availability_zones should be integer, not string
            invalid_config = {
                'logical_id': 'test-vpc',
                'cidr': '10.0.0.0/16',
                'availability_zones': 'three'  # wrong type
            }
        elif resource_type == 'ec2':
            # enable_session_manager should be boolean, not string
            invalid_config = {
                'logical_id': 'test-ec2',
                'instance_type': 't3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'enable_session_manager': 'true'  # wrong type
            }
        elif resource_type == 'rds':
            # multi_az should be boolean, not integer
            invalid_config = {
                'logical_id': 'test-rds',
                'engine': 'postgres',
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'multi_az': 1  # wrong type
            }
        else:  # s3
            # versioning_enabled should be boolean, not string
            invalid_config = {
                'logical_id': 'test-s3',
                'versioning_enabled': 'yes'  # wrong type
            }

        result = validator.validate_resource(resource_type, invalid_config)

        # Should fail validation
        assert not result.is_valid, \
            f"Configuration with wrong types should fail validation for {resource_type}"

        # Should have at least one type error
        assert len(result.errors) > 0, \
            f"Should have type validation errors for {resource_type}"

        # At least one error should be about invalid type
        type_errors = [e for e in result.errors if 'INVALID_TYPE' in e.error_code or 'type' in e.message.lower()]
        assert len(type_errors) > 0, \
            f"Should have at least one type-related error for {resource_type}"

    @given(st.sampled_from(['vpc', 'ec2', 'rds', 's3']))
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_9_required_fields_enforced(self, resource_type):
        """
        Feature: cdk-aws-templates-system
        Property 9: Schema Validation - The Validation Engine SHALL enforce
        required fields as defined in the JSON Schema, rejecting configurations
        that are missing required fields.

        Validates: Requirements 3.4
        """
        from cdk_templates.schema_validator import SchemaValidator

        validator = SchemaValidator()

        # Create a configuration missing required fields
        if resource_type == 'vpc':
            # Missing required 'cidr' field
            invalid_config = {
                'logical_id': 'test-vpc',
                'availability_zones': 3
            }
        elif resource_type == 'ec2':
            # Missing required 'vpc_ref' field
            invalid_config = {
                'logical_id': 'test-ec2',
                'instance_type': 't3.medium'
            }
        elif resource_type == 'rds':
            # Missing required 'engine' field
            invalid_config = {
                'logical_id': 'test-rds',
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}'
            }
        else:  # s3
            # S3 only requires logical_id, so test with empty properties
            invalid_config = {}

        result = validator.validate_resource(resource_type, invalid_config)

        # Should fail validation (except s3 with just logical_id)
        if resource_type != 's3':
            assert not result.is_valid, \
                f"Configuration missing required fields should fail validation for {resource_type}"

            # Should have at least one required field error
            assert len(result.errors) > 0, \
                f"Should have required field errors for {resource_type}"

            # At least one error should be about missing required field
            required_errors = [e for e in result.errors if 'MISSING_REQUIRED' in e.error_code or 'required' in e.message.lower()]
            assert len(required_errors) > 0, \
                f"Should have at least one required field error for {resource_type}"

    @given(invalid_resource_config_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_10_validation_error_descriptiveness(self, resource_config):
        """
        Feature: cdk-aws-templates-system
        Property 10: Validation Error Descriptiveness - For any invalid resource
        configuration, the Validation Engine SHALL return error messages that
        include the field path (e.g., "resources[0].properties.cidr") and a
        description of the specific violation.

        Validates: Requirements 3.5
        """
        from cdk_templates.schema_validator import SchemaValidator

        validator = SchemaValidator()

        # Validate the invalid resource
        result = validator.validate_resource(
            resource_config.resource_type,
            resource_config.properties
        )

        # Invalid configurations should fail validation
        assert not result.is_valid, \
            f"Invalid {resource_config.resource_type} configuration should fail validation"

        # Should have at least one error
        assert len(result.errors) > 0, \
            "Invalid configuration should produce at least one error"

        # Check each error for descriptiveness
        for error in result.errors:
            # Error must have a field_path
            assert error.field_path, \
                "Error must include field_path"
            assert isinstance(error.field_path, str), \
                "field_path must be a string"
            assert len(error.field_path) > 0, \
                "field_path must not be empty"

            # Error must have a descriptive message
            assert error.message, \
                "Error must include a descriptive message"
            assert isinstance(error.message, str), \
                "message must be a string"
            assert len(error.message) > 10, \
                f"Error message should be descriptive (>10 chars), got: '{error.message}'"

            # Error must have an error_code
            assert error.error_code, \
                "Error must include error_code"
            assert isinstance(error.error_code, str), \
                "error_code must be a string"

            # Error must have severity
            assert error.severity, \
                "Error must include severity"
            assert error.severity in ['ERROR', 'WARNING'], \
                f"severity must be ERROR or WARNING, got: {error.severity}"

            # Message should be human-readable (not just raw jsonschema error)
            # Check that message contains useful information
            assert not error.message.startswith("None"), \
                "Error message should not start with 'None'"
            assert not error.message.startswith("{}"), \
                "Error message should not start with '{}'"

            # For specific error types, verify message contains expected information
            if 'MISSING_REQUIRED' in error.error_code:
                assert 'required' in error.message.lower() or 'missing' in error.message.lower(), \
                    f"Missing required field error should mention 'required' or 'missing': {error.message}"

            elif 'INVALID_TYPE' in error.error_code:
                assert 'type' in error.message.lower() or 'expected' in error.message.lower(), \
                    f"Type error should mention 'type' or 'expected': {error.message}"

            elif 'PATTERN_MISMATCH' in error.error_code:
                assert 'pattern' in error.message.lower() or 'match' in error.message.lower(), \
                    f"Pattern error should mention 'pattern' or 'match': {error.message}"

            elif 'VALUE_TOO_SMALL' in error.error_code or 'VALUE_TOO_LARGE' in error.error_code:
                # Should mention the constraint (minimum/maximum)
                assert any(word in error.message.lower() for word in ['minimum', 'maximum', 'less', 'greater']), \
                    f"Range error should mention constraint: {error.message}"

            elif 'INVALID_ENUM' in error.error_code:
                assert 'allowed' in error.message.lower() or 'valid' in error.message.lower(), \
                    f"Enum error should mention 'allowed' or 'valid': {error.message}"

