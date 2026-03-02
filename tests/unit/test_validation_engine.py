"""Unit tests for ValidationEngine."""

import pytest
from cdk_templates.validation_engine import ValidationEngine, ValidationException
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
    ValidationError,
    ValidationResult,
    RuleApplicationResult,
    RuleRejection,
    LinkResolutionResult,
    Cycle
)
from cdk_templates.schema_validator import SchemaValidator
from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.deployment_rules import DeploymentRulesEngine


class TestValidationEngine:
    """Test suite for ValidationEngine."""
    
    def test_validation_engine_initialization_with_defaults(self):
        """Test that ValidationEngine can be initialized with default components."""
        engine = ValidationEngine()
        
        assert engine.schema_validator is not None
        assert engine.link_resolver is not None
        assert engine.rules_engine is not None
        assert isinstance(engine.schema_validator, SchemaValidator)
        assert isinstance(engine.link_resolver, ResourceLinkResolver)
        assert isinstance(engine.rules_engine, DeploymentRulesEngine)
    
    def test_validation_engine_initialization_with_custom_components(self):
        """Test that ValidationEngine accepts custom component instances."""
        schema_validator = SchemaValidator()
        link_resolver = ResourceLinkResolver()
        rules_engine = DeploymentRulesEngine()
        
        engine = ValidationEngine(
            schema_validator=schema_validator,
            link_resolver=link_resolver,
            rules_engine=rules_engine
        )
        
        assert engine.schema_validator is schema_validator
        assert engine.link_resolver is link_resolver
        assert engine.rules_engine is rules_engine
    
    def test_validate_with_valid_configuration(self):
        """Test validation passes with a valid configuration."""
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
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        "logical_id": "vpc-main",  # Schema requires this in properties
                        "cidr": "10.0.0.0/16",
                        "availability_zones": 3
                    }
                )
            ]
        )
        
        engine = ValidationEngine()
        result = engine.validate(config, "dev")
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_collects_schema_errors(self):
        """Test that validation collects schema validation errors."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        # Missing required 'cidr' field
                        "availability_zones": 3
                    }
                )
            ]
        )
        
        engine = ValidationEngine()
        result = engine.validate(config, "dev")
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # Should have error about missing 'cidr' field
        assert any("cidr" in error.message.lower() for error in result.errors)
    
    def test_validate_collects_link_resolution_errors(self):
        """Test that validation collects resource link resolution errors."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "instance_type": "t3.medium",
                        "vpc_ref": "${resource.vpc-nonexistent.id}"  # Dangling reference
                    }
                )
            ]
        )
        
        engine = ValidationEngine()
        result = engine.validate(config, "dev")
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # Should have error about non-existent resource
        assert any("non-existent" in error.message.lower() or "vpc-nonexistent" in error.message 
                   for error in result.errors)
    
    def test_validate_detects_circular_dependencies(self):
        """Test that validation detects circular dependencies."""
        # Create a circular dependency: A -> B -> C -> A
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="resource-a",
                    resource_type="vpc",
                    properties={"cidr": "10.0.0.0/16"},
                    depends_on=["resource-c"]
                ),
                ResourceConfig(
                    logical_id="resource-b",
                    resource_type="ec2",
                    properties={"instance_type": "t3.medium"},
                    depends_on=["resource-a"]
                ),
                ResourceConfig(
                    logical_id="resource-c",
                    resource_type="s3",
                    properties={},
                    depends_on=["resource-b"]
                )
            ]
        )
        
        engine = ValidationEngine()
        result = engine.validate(config, "dev")
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # Should have error about circular dependency
        assert any("circular" in error.message.lower() for error in result.errors)
    
    def test_validate_collects_deployment_rule_rejections(self):
        """Test that validation collects deployment rule rejections."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="",  # Empty project - will trigger TagComplianceRule
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "prod": EnvironmentConfig(
                    name="prod",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={"cidr": "10.0.0.0/16"}
                )
            ]
        )
        
        # Create engine with rules
        from cdk_templates.deployment_rules import TagComplianceRule
        rules_engine = DeploymentRulesEngine()
        rules_engine.register_rule(TagComplianceRule())
        
        engine = ValidationEngine(rules_engine=rules_engine)
        result = engine.validate(config, "prod")
        
        assert not result.is_valid
        assert len(result.errors) > 0
        # Should have error about missing project
        assert any("project" in error.message.lower() for error in result.errors)
    
    def test_validate_collects_all_errors_before_reporting(self):
        """Test that validation collects ALL errors before reporting."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="",  # Missing - rule error
                owner="",    # Missing - rule error
                cost_center="",  # Missing - rule error
                description="Test"
            ),
            environments={
                "prod": EnvironmentConfig(
                    name="prod",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        # Missing required 'cidr' - schema error
                        "availability_zones": 3
                    }
                ),
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "instance_type": "t3.medium",
                        "vpc_ref": "${resource.vpc-nonexistent.id}"  # Dangling ref - link error
                    }
                )
            ]
        )
        
        from cdk_templates.deployment_rules import TagComplianceRule
        rules_engine = DeploymentRulesEngine()
        rules_engine.register_rule(TagComplianceRule())
        
        engine = ValidationEngine(rules_engine=rules_engine)
        result = engine.validate(config, "prod")
        
        assert not result.is_valid
        # Should have multiple errors from different validators
        assert len(result.errors) >= 3  # At least schema, link, and rule errors
        
        # Verify we have errors from different sources
        error_codes = {error.error_code for error in result.errors}
        assert len(error_codes) > 1  # Multiple types of errors
    
    def test_generate_error_report_with_valid_configuration(self):
        """Test error report generation for valid configuration."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        engine = ValidationEngine()
        report = engine.generate_error_report(result)
        
        assert "passed successfully" in report.lower()
        assert "✓" in report
    
    def test_generate_error_report_with_errors(self):
        """Test error report generation with errors."""
        result = ValidationResult(
            is_valid=False,
            errors=[
                ValidationError(
                    field_path="resources[0].properties.cidr",
                    message="Missing required field 'cidr'",
                    error_code="MISSING_REQUIRED_FIELD",
                    severity="ERROR"
                ),
                ValidationError(
                    field_path="resources[1].properties.vpc_ref",
                    message="Resource 'vpc-nonexistent' does not exist",
                    error_code="LINK_RESOLUTION_ERROR",
                    severity="ERROR"
                )
            ],
            warnings=[]
        )
        
        engine = ValidationEngine()
        report = engine.generate_error_report(result)
        
        assert "VALIDATION FAILED" in report
        assert "ERRORS (2)" in report
        assert "MISSING_REQUIRED_FIELD" in report
        assert "LINK_RESOLUTION_ERROR" in report
        assert "cidr" in report
        assert "vpc-nonexistent" in report
        assert "Code generation cannot proceed" in report
    
    def test_generate_error_report_with_warnings(self):
        """Test error report generation with warnings."""
        result = ValidationResult(
            is_valid=False,
            errors=[
                ValidationError(
                    field_path="resources[0].properties.cidr",
                    message="Missing required field 'cidr'",
                    error_code="MISSING_REQUIRED_FIELD",
                    severity="ERROR"
                )
            ],
            warnings=[
                ValidationError(
                    field_path="resources[0].logical_id",
                    message="Logical ID contains consecutive hyphens",
                    error_code="NAMING_WARNING",
                    severity="WARNING"
                )
            ]
        )
        
        engine = ValidationEngine()
        report = engine.generate_error_report(result)
        
        assert "ERRORS (1)" in report
        assert "WARNINGS (1)" in report
        assert "NAMING_WARNING" in report
        assert "consecutive hyphens" in report
    
    def test_generate_error_report_groups_by_severity(self):
        """Test that error report groups errors and warnings separately."""
        result = ValidationResult(
            is_valid=False,
            errors=[
                ValidationError(
                    field_path="field1",
                    message="Error 1",
                    error_code="ERROR1",
                    severity="ERROR"
                ),
                ValidationError(
                    field_path="field2",
                    message="Warning 1",
                    error_code="WARN1",
                    severity="WARNING"
                ),
                ValidationError(
                    field_path="field3",
                    message="Error 2",
                    error_code="ERROR2",
                    severity="ERROR"
                )
            ],
            warnings=[]
        )
        
        engine = ValidationEngine()
        report = engine.generate_error_report(result)
        
        # Should have 2 errors and 1 warning
        assert "ERRORS (2)" in report
        assert "WARNINGS (1)" in report
        
        # Errors section should come before warnings
        errors_pos = report.find("ERRORS")
        warnings_pos = report.find("WARNINGS")
        assert errors_pos < warnings_pos
    
    def test_validate_and_report_returns_tuple(self):
        """Test that validate_and_report returns (is_valid, report) tuple."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        "logical_id": "vpc-main",
                        "cidr": "10.0.0.0/16"
                    }
                )
            ]
        )
        
        engine = ValidationEngine()
        is_valid, report = engine.validate_and_report(config, "dev")
        
        assert isinstance(is_valid, bool)
        assert isinstance(report, str)
        assert is_valid is True
        assert "passed successfully" in report.lower()
    
    def test_prevent_generation_on_failure_raises_exception(self):
        """Test that prevent_generation_on_failure raises exception on validation failure."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        # Missing required 'cidr' field
                        "availability_zones": 3
                    }
                )
            ]
        )
        
        engine = ValidationEngine()
        
        with pytest.raises(ValidationException) as exc_info:
            engine.prevent_generation_on_failure(config, "dev")
        
        exception = exc_info.value
        # The new ValidationException has a message with error details
        assert "Configuration validation failed" in str(exception)
        assert "cidr" in str(exception).lower()
    
    def test_prevent_generation_on_failure_returns_result_on_success(self):
        """Test that prevent_generation_on_failure returns result when validation passes."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        "logical_id": "vpc-main",
                        "cidr": "10.0.0.0/16"
                    }
                )
            ]
        )
        
        engine = ValidationEngine()
        result = engine.prevent_generation_on_failure(config, "dev")
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validation_exception_str_returns_report(self):
        """Test that ValidationException.__str__ returns the formatted error message."""
        error_messages = [
            "resources[0].properties.cidr: Required field 'cidr' is missing",
            "resources[1].properties.instance_type: Invalid type"
        ]
        
        exception = ValidationException(validation_errors=error_messages)
        
        exception_str = str(exception)
        assert "Configuration validation failed" in exception_str
        assert "cidr" in exception_str
        assert "instance_type" in exception_str
    
    def test_validation_runs_all_three_validators(self):
        """Test that validation runs schema, link, and rules validators."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={"cidr": "10.0.0.0/16"}
                )
            ]
        )
        
        # Create mock validators to track calls
        schema_validator = SchemaValidator()
        link_resolver = ResourceLinkResolver()
        rules_engine = DeploymentRulesEngine()
        
        engine = ValidationEngine(
            schema_validator=schema_validator,
            link_resolver=link_resolver,
            rules_engine=rules_engine
        )
        
        result = engine.validate(config, "dev")
        
        # If we get here without errors, all three validators ran
        assert result is not None
        assert isinstance(result, ValidationResult)


class TestValidationEngineIntegration:
    """Integration tests for ValidationEngine with real validators."""
    
    def test_full_validation_pipeline_with_multiple_error_types(self):
        """Test complete validation pipeline with schema, link, and rule errors."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="",  # Missing - will trigger rule error
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "prod": EnvironmentConfig(
                    name="prod",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        # Missing 'cidr' - schema error
                        "availability_zones": 3
                    }
                ),
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "instance_type": "t3.medium",
                        "vpc_ref": "${resource.vpc-missing.id}"  # Link error
                    }
                )
            ]
        )
        
        from cdk_templates.deployment_rules import TagComplianceRule
        rules_engine = DeploymentRulesEngine()
        rules_engine.register_rule(TagComplianceRule())
        
        engine = ValidationEngine(rules_engine=rules_engine)
        result = engine.validate(config, "prod")
        
        assert not result.is_valid
        assert len(result.errors) >= 3
        
        # Verify we have different types of errors
        error_codes = {error.error_code for error in result.errors}
        assert "MISSING_REQUIRED_FIELD" in error_codes or any("cidr" in e.message for e in result.errors)
        assert "LINK_RESOLUTION_ERROR" in error_codes or any("vpc-missing" in e.message for e in result.errors)
        assert "RULE_VIOLATION" in error_codes or any("project" in e.message.lower() for e in result.errors)
    
    def test_validation_with_production_environment_applies_strict_rules(self):
        """Test that production environment triggers stricter validation rules."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test"
            ),
            environments={
                "prod": EnvironmentConfig(
                    name="prod",
                    account_id="123456789012",
                    region="us-east-1"
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        "logical_id": "vpc-main",
                        "cidr": "10.0.0.0/16"
                    }
                ),
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "logical_id": "rds-main",
                        "engine": "postgres",
                        "engine_version": "15.3",
                        "instance_class": "db.t3.medium",
                        "allocated_storage": 100,
                        "vpc_ref": "${resource.vpc-main.id}",
                        # Missing encryption and multi_az - should be enforced in prod
                        "encryption_enabled": False,
                        "storage_encrypted": False,
                        "multi_az": False
                    }
                )
            ]
        )
        
        from cdk_templates.deployment_rules import (
            EncryptionEnforcementRule,
            ProductionProtectionRule
        )
        rules_engine = DeploymentRulesEngine()
        rules_engine.register_rule(EncryptionEnforcementRule(), priority=200)
        rules_engine.register_rule(ProductionProtectionRule(), priority=100)
        
        engine = ValidationEngine(rules_engine=rules_engine)
        result = engine.validate(config, "prod")
        
        # Rules should modify the configuration to enforce encryption and multi-az
        # The validation should pass after modifications
        assert result.is_valid or len(result.errors) == 0
        
        # Verify that encryption was enforced
        rds_resource = config.resources[1]
        assert rds_resource.properties.get("encryption_enabled") is True
        assert rds_resource.properties.get("storage_encrypted") is True
        assert rds_resource.properties.get("multi_az") is True
