"""Unit tests for SchemaValidator."""

import pytest
from cdk_templates.schema_validator import SchemaValidator
from cdk_templates.models import Configuration, ConfigMetadata, EnvironmentConfig, ResourceConfig


class TestSchemaValidator:
    """Test suite for SchemaValidator class."""

    def test_load_schemas(self):
        """Test that schemas are loaded correctly."""
        validator = SchemaValidator()
        
        # Check that all expected schemas are loaded
        assert "vpc" in validator._schemas
        assert "ec2" in validator._schemas
        assert "rds" in validator._schemas
        assert "s3" in validator._schemas

    def test_get_schema_valid_type(self):
        """Test getting schema for valid resource type."""
        validator = SchemaValidator()
        
        vpc_schema = validator.get_schema("vpc")
        assert vpc_schema is not None
        assert "$schema" in vpc_schema
        assert "properties" in vpc_schema

    def test_get_schema_invalid_type(self):
        """Test getting schema for invalid resource type."""
        validator = SchemaValidator()
        
        with pytest.raises(ValueError) as exc_info:
            validator.get_schema("invalid_type")
        
        assert "No schema found" in str(exc_info.value)

    def test_validate_resource_valid_vpc(self):
        """Test validation of valid VPC configuration."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            "cidr": "10.0.0.0/16",
            "availability_zones": 3,
            "enable_dns_hostnames": True
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_resource_missing_required_field(self):
        """Test validation rejects configuration missing required field."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            # Missing required 'cidr' field
            "availability_zones": 3
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("cidr" in error.message.lower() for error in result.errors)
        assert any("required" in error.message.lower() for error in result.errors)

    def test_validate_resource_invalid_type(self):
        """Test validation rejects configuration with wrong type."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            "cidr": "10.0.0.0/16",
            "availability_zones": "three"  # Should be integer
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("type" in error.message.lower() for error in result.errors)

    def test_validate_resource_invalid_pattern(self):
        """Test validation rejects configuration with invalid pattern."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            "cidr": "10.0.0/16"  # Invalid CIDR format (missing last octet)
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("pattern" in error.message.lower() for error in result.errors)

    def test_validate_resource_value_out_of_range(self):
        """Test validation rejects configuration with value out of range."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            "cidr": "10.0.0.0/16",
            "availability_zones": 10  # Maximum is 6
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("maximum" in error.message.lower() for error in result.errors)

    def test_validate_resource_valid_ec2(self):
        """Test validation of valid EC2 configuration."""
        validator = SchemaValidator()
        
        ec2_config = {
            "logical_id": "ec2-web-01",
            "instance_type": "t3.medium",
            "vpc_ref": "${resource.vpc-main.id}",
            "subnet_ref": "${resource.vpc-main.private_subnet_1}",
            "enable_session_manager": True
        }
        
        result = validator.validate_resource("ec2", ec2_config)
        
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_resource_valid_rds(self):
        """Test validation of valid RDS configuration."""
        validator = SchemaValidator()
        
        rds_config = {
            "logical_id": "rds-main",
            "engine": "postgres",
            "engine_version": "15.3",
            "instance_class": "db.t3.medium",
            "allocated_storage": 100,
            "multi_az": True,
            "vpc_ref": "${resource.vpc-main.id}",
            "subnet_refs": [
                "${resource.vpc-main.private_subnet_1}",
                "${resource.vpc-main.private_subnet_2}"
            ]
        }
        
        result = validator.validate_resource("rds", rds_config)
        
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_resource_valid_s3(self):
        """Test validation of valid S3 configuration."""
        validator = SchemaValidator()
        
        s3_config = {
            "logical_id": "s3-data",
            "versioning_enabled": True,
            "encryption": "AES256",
            "block_public_access": True
        }
        
        result = validator.validate_resource("s3", s3_config)
        
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_resource_invalid_enum_value(self):
        """Test validation rejects configuration with invalid enum value."""
        validator = SchemaValidator()
        
        rds_config = {
            "logical_id": "rds-main",
            "engine": "invalid_engine",  # Not in enum
            "instance_class": "db.t3.medium",
            "vpc_ref": "${resource.vpc-main.id}",
            "subnet_refs": [
                "${resource.vpc-main.private_subnet_1}",
                "${resource.vpc-main.private_subnet_2}"
            ]
        }
        
        result = validator.validate_resource("rds", rds_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("allowed values" in error.message.lower() for error in result.errors)

    def test_validate_complete_configuration(self):
        """Test validation of complete configuration with multiple resources."""
        validator = SchemaValidator()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test configuration"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={}
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        "logical_id": "vpc-main",
                        "cidr": "10.0.0.0/16",
                        "availability_zones": 3
                    },
                    tags={},
                    depends_on=[]
                ),
                ResourceConfig(
                    logical_id="ec2-web-01",
                    resource_type="ec2",
                    properties={
                        "logical_id": "ec2-web-01",
                        "instance_type": "t3.medium",
                        "vpc_ref": "${resource.vpc-main.id}"
                    },
                    tags={},
                    depends_on=["vpc-main"]
                )
            ],
            deployment_rules=[]
        )
        
        result = validator.validate(config)
        
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_configuration_with_errors(self):
        """Test validation of configuration with multiple errors."""
        validator = SchemaValidator()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test configuration"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={}
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        "logical_id": "vpc-main",
                        # Missing required 'cidr' field
                        "availability_zones": 10  # Out of range
                    },
                    tags={},
                    depends_on=[]
                ),
                ResourceConfig(
                    logical_id="ec2-web-01",
                    resource_type="ec2",
                    properties={
                        "logical_id": "ec2-web-01",
                        "instance_type": "invalid-type",  # Invalid pattern
                        "vpc_ref": "${resource.vpc-main.id}"
                    },
                    tags={},
                    depends_on=["vpc-main"]
                )
            ],
            deployment_rules=[]
        )
        
        result = validator.validate(config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # Should have errors from both resources
        assert any("resources[0]" in error.field_path for error in result.errors)
        assert any("resources[1]" in error.field_path for error in result.errors)

    def test_error_message_includes_field_path(self):
        """Test that error messages include field paths."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            # Missing cidr
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # Error should have a field path
        assert all(error.field_path for error in result.errors)

    def test_error_codes_are_set(self):
        """Test that error codes are properly set."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            # Missing cidr
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # All errors should have error codes
        assert all(error.error_code for error in result.errors)
        assert any(error.error_code == "MISSING_REQUIRED_FIELD" for error in result.errors)

    def test_default_values_applied(self):
        """Test that default values from schema are applied."""
        validator = SchemaValidator()
        
        # VPC config without optional fields
        vpc_config = {
            "logical_id": "vpc-main",
            "cidr": "10.0.0.0/16"
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        # Should be valid even without optional fields (defaults applied)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_resource_multiple_missing_fields(self):
        """Test validation with multiple missing required fields."""
        validator = SchemaValidator()
        
        rds_config = {
            # Missing logical_id, engine, instance_class, vpc_ref
            "allocated_storage": 100
        }
        
        result = validator.validate_resource("rds", rds_config)
        
        assert not result.is_valid
        assert len(result.errors) >= 4  # At least 4 missing required fields
        # Check that all missing fields are reported
        error_messages = " ".join([e.message for e in result.errors])
        assert "logical_id" in error_messages.lower()
        assert "engine" in error_messages.lower()
        assert "instance_class" in error_messages.lower()
        assert "vpc_ref" in error_messages.lower()

    def test_validate_resource_wrong_type_multiple_fields(self):
        """Test validation with multiple fields having wrong types."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            "cidr": "10.0.0.0/16",
            "availability_zones": "three",  # Should be integer
            "enable_dns_hostnames": "yes",  # Should be boolean
            "nat_gateways": 3.5  # Should be integer
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) >= 2  # At least 2 type errors

    def test_validate_resource_nested_object_validation(self):
        """Test validation of nested object properties."""
        validator = SchemaValidator()
        
        ec2_config = {
            "logical_id": "ec2-web-01",
            "instance_type": "t3.medium",
            "vpc_ref": "${resource.vpc-main.id}",
            "root_volume": {
                "size": 5,  # Below minimum of 8
                "encrypted": True,
                "volume_type": "invalid_type"  # Not in enum
            }
        }
        
        result = validator.validate_resource("ec2", ec2_config)
        
        assert not result.is_valid
        assert len(result.errors) >= 2
        # Check that nested field paths are correct
        assert any("root_volume" in error.field_path for error in result.errors)

    def test_validate_resource_array_validation(self):
        """Test validation of array properties."""
        validator = SchemaValidator()
        
        rds_config = {
            "logical_id": "rds-main",
            "engine": "postgres",
            "instance_class": "db.t3.medium",
            "vpc_ref": "${resource.vpc-main.id}",
            "subnet_refs": [
                "${resource.vpc-main.private_subnet_1}"
                # Only 1 subnet, but minItems is 2
            ]
        }
        
        result = validator.validate_resource("rds", rds_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("subnet_refs" in error.field_path for error in result.errors)

    def test_validate_resource_string_length_validation(self):
        """Test validation of string length constraints."""
        validator = SchemaValidator()
        
        # S3 logical_id has minLength: 3, maxLength: 63
        s3_config_too_short = {
            "logical_id": "s3"  # Only 2 characters, minimum is 3
        }
        
        result = validator.validate_resource("s3", s3_config_too_short)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("length" in error.message.lower() for error in result.errors)

    def test_validate_resource_pattern_validation_detailed(self):
        """Test detailed pattern validation for various resource types."""
        validator = SchemaValidator()
        
        # Test invalid logical_id pattern (uppercase not allowed)
        vpc_config = {
            "logical_id": "VPC-Main",  # Contains uppercase
            "cidr": "10.0.0.0/16"
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("pattern" in error.message.lower() for error in result.errors)

    def test_validate_resource_minimum_maximum_validation(self):
        """Test minimum and maximum value validation."""
        validator = SchemaValidator()
        
        # Test value below minimum
        rds_config_min = {
            "logical_id": "rds-main",
            "engine": "postgres",
            "instance_class": "db.t3.medium",
            "vpc_ref": "${resource.vpc-main.id}",
            "subnet_refs": [
                "${resource.vpc-main.private_subnet_1}",
                "${resource.vpc-main.private_subnet_2}"
            ],
            "allocated_storage": 10  # Below minimum of 20
        }
        
        result = validator.validate_resource("rds", rds_config_min)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("minimum" in error.message.lower() for error in result.errors)
        
        # Test value above maximum
        rds_config_max = {
            "logical_id": "rds-main",
            "engine": "postgres",
            "instance_class": "db.t3.medium",
            "vpc_ref": "${resource.vpc-main.id}",
            "subnet_refs": [
                "${resource.vpc-main.private_subnet_1}",
                "${resource.vpc-main.private_subnet_2}"
            ],
            "backup_retention_days": 40  # Above maximum of 35
        }
        
        result = validator.validate_resource("rds", rds_config_max)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("maximum" in error.message.lower() for error in result.errors)

    def test_error_field_path_accuracy(self):
        """Test that error field paths accurately point to the problematic field."""
        validator = SchemaValidator()
        
        ec2_config = {
            "logical_id": "ec2-web-01",
            "instance_type": "t3.medium",
            "vpc_ref": "${resource.vpc-main.id}",
            "root_volume": {
                "size": 30,
                "encrypted": True,
                "volume_type": "invalid"  # This specific field is invalid
            }
        }
        
        result = validator.validate_resource("ec2", ec2_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # Field path should point exactly to root_volume.volume_type
        assert any("root_volume.volume_type" in error.field_path for error in result.errors)

    def test_error_message_format_consistency(self):
        """Test that error messages follow a consistent format."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            # Missing cidr
            "availability_zones": 10  # Out of range
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) >= 2
        
        # All errors should have required fields
        for error in result.errors:
            assert error.field_path is not None
            assert error.message is not None
            assert error.error_code is not None
            assert error.severity is not None
            # Messages should be descriptive
            assert len(error.message) > 10

    def test_error_codes_mapping(self):
        """Test that different validation errors get appropriate error codes."""
        validator = SchemaValidator()
        
        # Test various error types
        test_cases = [
            # Missing required field
            ({
                "logical_id": "vpc-main"
                # Missing cidr
            }, "MISSING_REQUIRED_FIELD"),
            
            # Invalid type
            ({
                "logical_id": "vpc-main",
                "cidr": "10.0.0.0/16",
                "availability_zones": "three"
            }, "INVALID_TYPE"),
            
            # Pattern mismatch
            ({
                "logical_id": "vpc-main",
                "cidr": "invalid-cidr"
            }, "PATTERN_MISMATCH"),
            
            # Value out of range
            ({
                "logical_id": "vpc-main",
                "cidr": "10.0.0.0/16",
                "availability_zones": 10
            }, "VALUE_TOO_LARGE"),
        ]
        
        for config, expected_code in test_cases:
            result = validator.validate_resource("vpc", config)
            assert not result.is_valid
            assert any(error.error_code == expected_code for error in result.errors), \
                f"Expected error code {expected_code} not found in {[e.error_code for e in result.errors]}"

    def test_validate_configuration_field_path_includes_resource_index(self):
        """Test that configuration validation includes resource index in field paths."""
        validator = SchemaValidator()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test configuration"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={}
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        "logical_id": "vpc-main",
                        "cidr": "10.0.0.0/16"
                    },
                    tags={},
                    depends_on=[]
                ),
                ResourceConfig(
                    logical_id="ec2-web-01",
                    resource_type="ec2",
                    properties={
                        "logical_id": "ec2-web-01",
                        # Missing required instance_type and vpc_ref
                    },
                    tags={},
                    depends_on=["vpc-main"]
                )
            ],
            deployment_rules=[]
        )
        
        result = validator.validate(config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # Field paths should include resource index
        assert any("resources[1]" in error.field_path for error in result.errors)

    def test_validate_unknown_resource_type(self):
        """Test validation with unknown resource type."""
        validator = SchemaValidator()
        
        result = validator.validate_resource("unknown_type", {"some": "config"})
        
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].error_code == "UNKNOWN_RESOURCE_TYPE"
        assert "unknown_type" in result.errors[0].message.lower()

    def test_validate_s3_lifecycle_rules_complex(self):
        """Test validation of complex nested structures like S3 lifecycle rules."""
        validator = SchemaValidator()
        
        s3_config = {
            "logical_id": "s3-data",
            "lifecycle_rules": [
                {
                    "id": "rule-1",
                    "enabled": True,
                    "transitions": [
                        {
                            "storage_class": "STANDARD_IA",
                            "days": 30
                        },
                        {
                            "storage_class": "INVALID_CLASS",  # Invalid enum
                            "days": 90
                        }
                    ]
                }
            ]
        }
        
        result = validator.validate_resource("s3", s3_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # Should have error in nested lifecycle rule
        assert any("lifecycle_rules" in error.field_path for error in result.errors)

    def test_validate_all_resource_types(self):
        """Test that validator can validate all supported resource types."""
        validator = SchemaValidator()
        
        resource_types = ["vpc", "ec2", "rds", "s3"]
        
        for resource_type in resource_types:
            schema = validator.get_schema(resource_type)
            assert schema is not None
            assert "properties" in schema

    def test_validation_result_structure(self):
        """Test that ValidationResult has correct structure."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main",
            "cidr": "10.0.0.0/16"
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        # Check ValidationResult structure
        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_validation_error_structure(self):
        """Test that ValidationError has correct structure."""
        validator = SchemaValidator()
        
        vpc_config = {
            "logical_id": "vpc-main"
            # Missing cidr
        }
        
        result = validator.validate_resource("vpc", vpc_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Check ValidationError structure
        error = result.errors[0]
        assert hasattr(error, "field_path")
        assert hasattr(error, "message")
        assert hasattr(error, "error_code")
        assert hasattr(error, "severity")
        assert error.severity == "ERROR"
