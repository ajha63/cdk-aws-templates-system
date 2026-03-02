"""Unit tests for core data models."""

import pytest
from datetime import datetime
from cdk_templates.models import (
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
    Configuration,
    ValidationError,
    ValidationResult,
    ResourceMetadata,
)


class TestConfigMetadata:
    """Tests for ConfigMetadata dataclass."""

    def test_create_config_metadata(self):
        """Test creating ConfigMetadata with all required fields."""
        metadata = ConfigMetadata(
            project="test-project",
            owner="test-team",
            cost_center="engineering",
            description="Test infrastructure",
        )

        assert metadata.project == "test-project"
        assert metadata.owner == "test-team"
        assert metadata.cost_center == "engineering"
        assert metadata.description == "Test infrastructure"


class TestEnvironmentConfig:
    """Tests for EnvironmentConfig dataclass."""

    def test_create_environment_config(self):
        """Test creating EnvironmentConfig with required fields."""
        env = EnvironmentConfig(
            name="dev",
            account_id="123456789012",
            region="us-east-1",
        )

        assert env.name == "dev"
        assert env.account_id == "123456789012"
        assert env.region == "us-east-1"
        assert env.tags == {}
        assert env.overrides == {}

    def test_environment_config_with_tags(self):
        """Test EnvironmentConfig with custom tags."""
        env = EnvironmentConfig(
            name="prod",
            account_id="123456789012",
            region="us-west-2",
            tags={"Environment": "production", "Critical": "true"},
        )

        assert env.tags["Environment"] == "production"
        assert env.tags["Critical"] == "true"


class TestResourceConfig:
    """Tests for ResourceConfig dataclass."""

    def test_create_resource_config(self):
        """Test creating ResourceConfig with required fields."""
        resource = ResourceConfig(
            logical_id="vpc-main",
            resource_type="vpc",
        )

        assert resource.logical_id == "vpc-main"
        assert resource.resource_type == "vpc"
        assert resource.properties == {}
        assert resource.tags == {}
        assert resource.depends_on == []

    def test_resource_config_with_properties(self):
        """Test ResourceConfig with properties."""
        resource = ResourceConfig(
            logical_id="vpc-main",
            resource_type="vpc",
            properties={"cidr": "10.0.0.0/16", "availability_zones": 3},
        )

        assert resource.properties["cidr"] == "10.0.0.0/16"
        assert resource.properties["availability_zones"] == 3

    def test_resource_config_with_dependencies(self):
        """Test ResourceConfig with dependencies."""
        resource = ResourceConfig(
            logical_id="ec2-web",
            resource_type="ec2",
            depends_on=["vpc-main", "security-group-web"],
        )

        assert len(resource.depends_on) == 2
        assert "vpc-main" in resource.depends_on
        assert "security-group-web" in resource.depends_on


class TestConfiguration:
    """Tests for Configuration dataclass."""

    def test_create_configuration(self):
        """Test creating complete Configuration."""
        metadata = ConfigMetadata(
            project="test-project",
            owner="test-team",
            cost_center="engineering",
            description="Test",
        )

        env = EnvironmentConfig(
            name="dev",
            account_id="123456789012",
            region="us-east-1",
        )

        resource = ResourceConfig(
            logical_id="vpc-main",
            resource_type="vpc",
            properties={"cidr": "10.0.0.0/16"},
        )

        config = Configuration(
            version="1.0",
            metadata=metadata,
            environments={"dev": env},
            resources=[resource],
        )

        assert config.version == "1.0"
        assert config.metadata.project == "test-project"
        assert "dev" in config.environments
        assert len(config.resources) == 1
        assert config.deployment_rules == []


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid ValidationResult."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_with_errors(self):
        """Test ValidationResult with errors."""
        error = ValidationError(
            field_path="resources[0].properties.cidr",
            message="Invalid CIDR format",
            error_code="INVALID_CIDR",
            severity="ERROR",
        )

        result = ValidationResult(is_valid=False, errors=[error])

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field_path == "resources[0].properties.cidr"
        assert result.errors[0].severity == "ERROR"


class TestResourceMetadata:
    """Tests for ResourceMetadata dataclass."""

    def test_create_resource_metadata(self):
        """Test creating ResourceMetadata."""
        now = datetime.now()

        metadata = ResourceMetadata(
            resource_id="vpc-123",
            resource_type="vpc",
            logical_name="vpc-main",
            physical_name="prod-myapp-vpc-us-east-1",
            stack_name="infrastructure-stack",
            environment="prod",
            tags={"Environment": "prod"},
            outputs={"VpcId": "vpc-123"},
            dependencies=[],
            created_at=now,
            updated_at=now,
        )

        assert metadata.resource_id == "vpc-123"
        assert metadata.resource_type == "vpc"
        assert metadata.logical_name == "vpc-main"
        assert metadata.environment == "prod"
        assert metadata.tags["Environment"] == "prod"
