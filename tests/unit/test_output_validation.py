"""Unit tests for cross-stack output validation."""

import pytest
from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.resource_registry import ResourceRegistry
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
    StackConfig
)


class TestOutputValidation:
    """Test cross-stack output validation functionality."""
    
    def test_valid_output_references(self):
        """Test that valid output references pass validation."""
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
                    properties={"cidr": "10.0.0.0/16"},
                    stack="network-stack",
                    outputs={"id": "VPC ID"}
                ),
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "vpc_ref": "${stack.network-stack.id}",
                        "instance_type": "t3.medium"
                    },
                    stack="app-stack"
                )
            ],
            stacks={
                "network-stack": StackConfig(
                    stack_id="network-stack",
                    description="Network infrastructure",
                    resources=["vpc-main"]
                ),
                "app-stack": StackConfig(
                    stack_id="app-stack",
                    description="Application infrastructure",
                    resources=["ec2-web"]
                )
            }
        )
        
        resolver = ResourceLinkResolver()
        errors = resolver.validate_cross_stack_outputs(config)
        
        assert len(errors) == 0
    
    def test_invalid_output_reference(self):
        """Test that invalid output references are detected."""
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
                    properties={"cidr": "10.0.0.0/16"},
                    stack="network-stack",
                    outputs={"id": "VPC ID"}
                ),
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "vpc_ref": "${stack.network-stack.invalid_output}",
                        "instance_type": "t3.medium"
                    },
                    stack="app-stack"
                )
            ],
            stacks={
                "network-stack": StackConfig(
                    stack_id="network-stack",
                    description="Network infrastructure",
                    resources=["vpc-main"]
                ),
                "app-stack": StackConfig(
                    stack_id="app-stack",
                    description="Application infrastructure",
                    resources=["ec2-web"]
                )
            }
        )
        
        resolver = ResourceLinkResolver()
        errors = resolver.validate_cross_stack_outputs(config)
        
        assert len(errors) == 1
        assert "invalid_output" in errors[0]
        assert "ec2-web" in errors[0]
        assert "network-stack" in errors[0]
    
    def test_non_existent_stack_reference(self):
        """Test that references to non-existent stacks are detected."""
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
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "vpc_ref": "${stack.non-existent-stack.id}",
                        "instance_type": "t3.medium"
                    },
                    stack="app-stack"
                )
            ],
            stacks={
                "app-stack": StackConfig(
                    stack_id="app-stack",
                    description="Application infrastructure",
                    resources=["ec2-web"]
                )
            }
        )
        
        resolver = ResourceLinkResolver()
        errors = resolver.validate_cross_stack_outputs(config)
        
        assert len(errors) == 1
        assert "non-existent-stack" in errors[0]
        assert "ec2-web" in errors[0]
    
    def test_stack_with_no_outputs(self):
        """Test that references to stacks with no outputs are detected."""
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
                    properties={"cidr": "10.0.0.0/16"},
                    stack="network-stack",
                    outputs={}  # No outputs defined
                ),
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "vpc_ref": "${stack.network-stack.id}",
                        "instance_type": "t3.medium"
                    },
                    stack="app-stack"
                )
            ],
            stacks={
                "network-stack": StackConfig(
                    stack_id="network-stack",
                    description="Network infrastructure",
                    resources=["vpc-main"]
                ),
                "app-stack": StackConfig(
                    stack_id="app-stack",
                    description="Application infrastructure",
                    resources=["ec2-web"]
                )
            }
        )
        
        resolver = ResourceLinkResolver()
        errors = resolver.validate_cross_stack_outputs(config)
        
        assert len(errors) == 1
        assert "no outputs defined" in errors[0]
        assert "network-stack" in errors[0]
    
    def test_multiple_validation_errors(self):
        """Test that multiple validation errors are all reported."""
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
                    properties={"cidr": "10.0.0.0/16"},
                    stack="network-stack",
                    outputs={"id": "VPC ID"}
                ),
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "vpc_ref": "${stack.network-stack.invalid_output}",
                        "subnet_ref": "${stack.non-existent-stack.subnet}",
                        "instance_type": "t3.medium"
                    },
                    stack="app-stack"
                )
            ],
            stacks={
                "network-stack": StackConfig(
                    stack_id="network-stack",
                    description="Network infrastructure",
                    resources=["vpc-main"]
                ),
                "app-stack": StackConfig(
                    stack_id="app-stack",
                    description="Application infrastructure",
                    resources=["ec2-web"]
                )
            }
        )
        
        resolver = ResourceLinkResolver()
        errors = resolver.validate_cross_stack_outputs(config)
        
        assert len(errors) == 2
    
    def test_resource_registry_stack_outputs(self):
        """Test that stack outputs can be registered and retrieved."""
        registry = ResourceRegistry()
        
        # Register stack outputs
        outputs = {
            "vpc_id": "vpc-12345",
            "subnet_id": "subnet-67890"
        }
        registry.register_stack_outputs("network-stack", outputs)
        
        # Retrieve stack outputs
        retrieved = registry.get_stack_outputs("network-stack")
        
        assert retrieved == outputs
    
    def test_resource_registry_non_existent_stack(self):
        """Test that retrieving outputs for non-existent stack returns None."""
        registry = ResourceRegistry()
        
        retrieved = registry.get_stack_outputs("non-existent-stack")
        
        assert retrieved is None
    
    def test_resource_registry_update_stack_outputs(self):
        """Test that stack outputs can be updated."""
        registry = ResourceRegistry()
        
        # Register initial outputs
        outputs1 = {"vpc_id": "vpc-12345"}
        registry.register_stack_outputs("network-stack", outputs1)
        
        # Update outputs
        outputs2 = {"vpc_id": "vpc-12345", "subnet_id": "subnet-67890"}
        registry.register_stack_outputs("network-stack", outputs2)
        
        # Retrieve updated outputs
        retrieved = registry.get_stack_outputs("network-stack")
        
        assert retrieved == outputs2
