"""Unit tests for stack deployment ordering."""

import pytest
from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
    StackConfig
)


class TestStackDeploymentOrder:
    """Test stack deployment ordering functionality."""
    
    def test_simple_stack_dependency(self):
        """Test deployment order with simple linear dependency."""
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
                    stack="network-stack"
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
        deployment_order = resolver.get_stack_deployment_order(config)
        
        # network-stack should be deployed before app-stack
        assert deployment_order.index("network-stack") < deployment_order.index("app-stack")
    
    def test_multiple_stack_dependencies(self):
        """Test deployment order with multiple dependencies."""
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
                    stack="network-stack"
                ),
                ResourceConfig(
                    logical_id="s3-data",
                    resource_type="s3",
                    properties={},
                    stack="storage-stack"
                ),
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "vpc_ref": "${stack.network-stack.id}",
                        "instance_type": "t3.medium"
                    },
                    stack="app-stack"
                ),
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "vpc_ref": "${stack.network-stack.id}",
                        "backup_bucket": "${stack.storage-stack.bucket_name}"
                    },
                    stack="database-stack"
                )
            ],
            stacks={
                "network-stack": StackConfig(
                    stack_id="network-stack",
                    description="Network infrastructure",
                    resources=["vpc-main"]
                ),
                "storage-stack": StackConfig(
                    stack_id="storage-stack",
                    description="Storage infrastructure",
                    resources=["s3-data"]
                ),
                "app-stack": StackConfig(
                    stack_id="app-stack",
                    description="Application infrastructure",
                    resources=["ec2-web"]
                ),
                "database-stack": StackConfig(
                    stack_id="database-stack",
                    description="Database infrastructure",
                    resources=["rds-main"]
                )
            }
        )
        
        resolver = ResourceLinkResolver()
        deployment_order = resolver.get_stack_deployment_order(config)
        
        # network-stack and storage-stack should be deployed before database-stack
        assert deployment_order.index("network-stack") < deployment_order.index("database-stack")
        assert deployment_order.index("storage-stack") < deployment_order.index("database-stack")
        
        # network-stack should be deployed before app-stack
        assert deployment_order.index("network-stack") < deployment_order.index("app-stack")
    
    def test_circular_stack_dependency_detection(self):
        """Test that circular dependencies between stacks are detected."""
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
                    logical_id="resource-a",
                    resource_type="vpc",
                    properties={
                        "ref": "${stack.stack-b.output}"
                    },
                    stack="stack-a"
                ),
                ResourceConfig(
                    logical_id="resource-b",
                    resource_type="s3",
                    properties={
                        "ref": "${stack.stack-a.output}"
                    },
                    stack="stack-b"
                )
            ],
            stacks={
                "stack-a": StackConfig(
                    stack_id="stack-a",
                    description="Stack A",
                    resources=["resource-a"]
                ),
                "stack-b": StackConfig(
                    stack_id="stack-b",
                    description="Stack B",
                    resources=["resource-b"]
                )
            }
        )
        
        resolver = ResourceLinkResolver()
        
        with pytest.raises(ValueError) as exc_info:
            resolver.get_stack_deployment_order(config)
        
        assert "Circular dependencies detected" in str(exc_info.value)
    
    def test_independent_stacks(self):
        """Test deployment order with independent stacks (no dependencies)."""
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
                    stack="network-stack"
                ),
                ResourceConfig(
                    logical_id="s3-data",
                    resource_type="s3",
                    properties={},
                    stack="storage-stack"
                )
            ],
            stacks={
                "network-stack": StackConfig(
                    stack_id="network-stack",
                    description="Network infrastructure",
                    resources=["vpc-main"]
                ),
                "storage-stack": StackConfig(
                    stack_id="storage-stack",
                    description="Storage infrastructure",
                    resources=["s3-data"]
                )
            }
        )
        
        resolver = ResourceLinkResolver()
        deployment_order = resolver.get_stack_deployment_order(config)
        
        # Both stacks should be in the order (order doesn't matter for independent stacks)
        assert len(deployment_order) == 2
        assert "network-stack" in deployment_order
        assert "storage-stack" in deployment_order
    
    def test_empty_stacks_configuration(self):
        """Test deployment order with no stacks defined."""
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
            resources=[],
            stacks={}
        )
        
        resolver = ResourceLinkResolver()
        deployment_order = resolver.get_stack_deployment_order(config)
        
        assert deployment_order == []
    
    def test_build_stack_dependency_graph(self):
        """Test that stack dependency graph is built correctly."""
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
                    stack="network-stack"
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
        graph = resolver.build_stack_dependency_graph(config)
        
        # Verify nodes
        assert "network-stack" in graph.nodes
        assert "app-stack" in graph.nodes
        
        # Verify dependencies
        assert "network-stack" in graph.nodes["app-stack"].dependencies
        assert len(graph.nodes["network-stack"].dependencies) == 0
        
        # Verify edges
        assert len(graph.edges) == 1
        assert graph.edges[0].source_resource == "app-stack"
        assert graph.edges[0].target_resource == "network-stack"
