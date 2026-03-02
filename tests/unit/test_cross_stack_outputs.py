"""Unit tests for cross-stack output functionality."""

import pytest
from cdk_templates.template_generator import TemplateGenerator
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig
)


class TestCrossStackOutputs:
    """Test cross-stack output export functionality."""
    
    def test_generate_outputs_for_vpc(self):
        """Test that VPC outputs are generated correctly."""
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
                        "cidr": "10.0.0.0/16",
                        "availability_zones": 3
                    },
                    tags={},
                    depends_on=[],
                    outputs={
                        "id": "VPC ID for cross-stack references",
                        "public_subnets": "Public subnet IDs"
                    }
                )
            ],
            deployment_rules=[]
        )
        
        generator = TemplateGenerator()
        result = generator.generate(config, environment="dev")
        
        assert result.success
        assert len(result.errors) == 0
        
        # Check that stack file was generated
        stack_file = 'stacks/test_project_stack.py'
        assert stack_file in result.generated_files
        
        stack_code = result.generated_files[stack_file]
        
        # Verify CfnOutput constructs are present
        assert "cdk.CfnOutput" in stack_code
        assert "vpc-main_id" in stack_code
        assert "vpc-main_public_subnets" in stack_code
        assert "export_name=" in stack_code
        assert "dev-vpc-main-id" in stack_code
        assert "dev-vpc-main-public_subnets" in stack_code
    
    def test_generate_outputs_for_multiple_resources(self):
        """Test that outputs are generated for multiple resources."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test-project",
                owner="test-team",
                cost_center="engineering",
                description="Test configuration"
            ),
            environments={
                "prod": EnvironmentConfig(
                    name="prod",
                    account_id="123456789012",
                    region="us-west-2",
                    tags={},
                    overrides={}
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={"cidr": "10.0.0.0/16"},
                    outputs={"id": "VPC ID"}
                ),
                ResourceConfig(
                    logical_id="s3-data",
                    resource_type="s3",
                    properties={},
                    outputs={"name": "Bucket name", "arn": "Bucket ARN"}
                )
            ]
        )
        
        generator = TemplateGenerator()
        result = generator.generate(config, environment="prod")
        
        assert result.success
        
        stack_code = result.generated_files['stacks/test_project_stack.py']
        
        # Verify outputs for both resources
        assert "vpc-main_id" in stack_code
        assert "s3-data_name" in stack_code
        assert "s3-data_arn" in stack_code
        assert "prod-vpc-main-id" in stack_code
        assert "prod-s3-data-name" in stack_code
        assert "prod-s3-data-arn" in stack_code
    
    def test_export_name_generation(self):
        """Test that export names are unique and follow the correct format."""
        generator = TemplateGenerator()
        
        export_name = generator._generate_export_name("vpc-main", "id", "dev")
        assert export_name == "dev-vpc-main-id"
        
        export_name = generator._generate_export_name("rds-primary", "endpoint", "prod")
        assert export_name == "prod-rds-primary-endpoint"
    
    def test_no_outputs_defined(self):
        """Test that resources without outputs don't generate CfnOutput constructs."""
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
                    properties={"cidr": "10.0.0.0/16"},
                    outputs={}  # No outputs defined
                )
            ]
        )
        
        generator = TemplateGenerator()
        result = generator.generate(config, environment="dev")
        
        assert result.success
        
        stack_code = result.generated_files['stacks/test_project_stack.py']
        
        # Verify no CfnOutput constructs are present
        assert "cdk.CfnOutput" not in stack_code
    
    def test_invalid_output_name_skipped(self):
        """Test that invalid output names (not available from template) are skipped."""
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
                    properties={"cidr": "10.0.0.0/16"},
                    outputs={
                        "id": "VPC ID",
                        "invalid_output": "This output doesn't exist"
                    }
                )
            ]
        )
        
        generator = TemplateGenerator()
        result = generator.generate(config, environment="dev")
        
        assert result.success
        
        stack_code = result.generated_files['stacks/test_project_stack.py']
        
        # Verify valid output is present
        assert "vpc-main_id" in stack_code
        # Verify invalid output is not present
        assert "invalid_output" not in stack_code
