"""Unit tests for ResourceLinkResolver."""

import pytest
from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
    DependencyGraph,
    ResourceNode,
    ResourceLink
)


@pytest.fixture
def basic_config():
    """Create a basic configuration with two resources."""
    return Configuration(
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
                    "cidr": "10.0.0.0/16",
                    "availability_zones": 3
                }
            ),
            ResourceConfig(
                logical_id="ec2-web-01",
                resource_type="ec2",
                properties={
                    "instance_type": "t3.medium",
                    "vpc_ref": "${resource.vpc-main.id}",
                    "subnet_ref": "${resource.vpc-main.private_subnet_1}"
                }
            )
        ]
    )


@pytest.fixture
def circular_config():
    """Create a configuration with circular dependencies."""
    return Configuration(
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
                    "ref": "${resource.resource-b.id}"
                }
            ),
            ResourceConfig(
                logical_id="resource-b",
                resource_type="ec2",
                properties={
                    "ref": "${resource.resource-c.id}"
                }
            ),
            ResourceConfig(
                logical_id="resource-c",
                resource_type="rds",
                properties={
                    "ref": "${resource.resource-a.id}"
                }
            )
        ]
    )


@pytest.fixture
def dangling_ref_config():
    """Create a configuration with a dangling reference."""
    return Configuration(
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
                logical_id="ec2-web-01",
                resource_type="ec2",
                properties={
                    "instance_type": "t3.medium",
                    "vpc_ref": "${resource.vpc-nonexistent.id}"
                }
            )
        ]
    )


class TestResourceLinkResolver:
    """Test suite for ResourceLinkResolver."""
    
    def test_build_dependency_graph_basic(self, basic_config):
        """Test building a basic dependency graph."""
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(basic_config)
        
        # Check nodes exist
        assert "vpc-main" in graph.nodes
        assert "ec2-web-01" in graph.nodes
        
        # Check node types
        assert graph.nodes["vpc-main"].resource_type == "vpc"
        assert graph.nodes["ec2-web-01"].resource_type == "ec2"
        
        # Check dependencies
        assert "vpc-main" in graph.nodes["ec2-web-01"].dependencies
        assert len(graph.nodes["vpc-main"].dependencies) == 0
        
        # Check edges
        assert len(graph.edges) == 2  # Two references in ec2-web-01
        
    def test_build_dependency_graph_with_explicit_depends_on(self):
        """Test building graph with explicit depends_on."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="resource-a",
                    resource_type="vpc",
                    properties={}
                ),
                ResourceConfig(
                    logical_id="resource-b",
                    resource_type="ec2",
                    properties={},
                    depends_on=["resource-a"]
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        
        assert "resource-a" in graph.nodes["resource-b"].dependencies
        
    def test_detect_cycles_no_cycle(self, basic_config):
        """Test cycle detection with no cycles."""
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(basic_config)
        cycles = resolver.detect_cycles(graph)
        
        assert len(cycles) == 0
        
    def test_detect_cycles_with_cycle(self, circular_config):
        """Test cycle detection with circular dependencies."""
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(circular_config)
        cycles = resolver.detect_cycles(graph)
        
        assert len(cycles) > 0
        # Check that the cycle contains the expected resources
        cycle_resources = cycles[0].resources
        assert "resource-a" in cycle_resources
        assert "resource-b" in cycle_resources
        assert "resource-c" in cycle_resources
        
    def test_topological_sort_valid(self, basic_config):
        """Test topological sort with valid graph."""
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(basic_config)
        order = resolver.topological_sort(graph)
        
        # vpc-main should come before ec2-web-01
        vpc_index = order.index("vpc-main")
        ec2_index = order.index("ec2-web-01")
        assert vpc_index < ec2_index
        
    def test_topological_sort_with_cycle(self, circular_config):
        """Test topological sort raises error with cycles."""
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(circular_config)
        
        with pytest.raises(ValueError, match="cycles"):
            resolver.topological_sort(graph)
            
    def test_resolve_links_success(self, basic_config):
        """Test successful link resolution."""
        resolver = ResourceLinkResolver()
        result = resolver.resolve_links(basic_config)
        
        assert result.success
        assert len(result.errors) == 0
        assert len(result.cycles) == 0
        assert "vpc-main" in result.resolved_links
        assert "ec2-web-01" in result.resolved_links
        
    def test_resolve_links_with_cycle(self, circular_config):
        """Test link resolution fails with circular dependencies."""
        resolver = ResourceLinkResolver()
        result = resolver.resolve_links(circular_config)
        
        assert not result.success
        assert len(result.cycles) > 0
        assert "circular" in result.error_message.lower()
        
    def test_resolve_links_with_dangling_reference(self, dangling_ref_config):
        """Test link resolution fails with dangling references."""
        resolver = ResourceLinkResolver()
        result = resolver.resolve_links(dangling_ref_config)
        
        assert not result.success
        assert len(result.errors) > 0
        assert "non-existent" in result.errors[0].lower()
        assert "vpc-nonexistent" in result.errors[0]
        
    def test_extract_references_nested(self):
        """Test extracting references from nested structures."""
        resolver = ResourceLinkResolver()
        resource = ResourceConfig(
            logical_id="test-resource",
            resource_type="ec2",
            properties={
                "vpc_ref": "${resource.vpc-main.id}",
                "nested": {
                    "subnet_ref": "${resource.vpc-main.subnet_1}"
                },
                "list_refs": [
                    "${resource.sg-1.id}",
                    "${resource.sg-2.id}"
                ]
            }
        )
        
        refs = resolver._extract_references(resource)
        
        assert len(refs) == 4
        target_resources = [ref['target_resource'] for ref in refs]
        assert "vpc-main" in target_resources
        assert "sg-1" in target_resources
        assert "sg-2" in target_resources
        
    def test_reference_pattern_matching(self):
        """Test the reference pattern regex."""
        resolver = ResourceLinkResolver()
        
        # Valid patterns
        valid_refs = [
            "${resource.vpc-main.id}",
            "${resource.my-resource-123.property_name}",
            "${resource.a.b}"
        ]
        
        for ref in valid_refs:
            matches = resolver.REFERENCE_PATTERN.findall(ref)
            assert len(matches) == 1
            
        # Invalid patterns (should not match)
        invalid_refs = [
            "${resource.VPC-Main.id}",  # uppercase
            "${resource.vpc_main.id}",  # underscore in logical_id
            "$resource.vpc-main.id}",   # missing opening brace
            "${resource.vpc-main}",     # missing property
        ]
        
        for ref in invalid_refs:
            matches = resolver.REFERENCE_PATTERN.findall(ref)
            assert len(matches) == 0
            
    def test_complex_dependency_chain(self):
        """Test resolving a complex dependency chain."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="vpc",
                    resource_type="vpc",
                    properties={"cidr": "10.0.0.0/16"}
                ),
                ResourceConfig(
                    logical_id="subnet",
                    resource_type="subnet",
                    properties={"vpc_ref": "${resource.vpc.id}"}
                ),
                ResourceConfig(
                    logical_id="sg",
                    resource_type="security-group",
                    properties={"vpc_ref": "${resource.vpc.id}"}
                ),
                ResourceConfig(
                    logical_id="ec2",
                    resource_type="ec2",
                    properties={
                        "subnet_ref": "${resource.subnet.id}",
                        "sg_ref": "${resource.sg.id}"
                    }
                ),
                ResourceConfig(
                    logical_id="rds",
                    resource_type="rds",
                    properties={
                        "subnet_ref": "${resource.subnet.id}",
                        "sg_ref": "${resource.sg.id}"
                    }
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        result = resolver.resolve_links(config)
        
        assert result.success
        
        # Test topological sort
        graph = resolver.build_dependency_graph(config)
        order = resolver.topological_sort(graph)
        
        # VPC should be first
        assert order[0] == "vpc"
        
        # Subnet and SG should come before EC2 and RDS
        subnet_idx = order.index("subnet")
        sg_idx = order.index("sg")
        ec2_idx = order.index("ec2")
        rds_idx = order.index("rds")
        
        assert subnet_idx < ec2_idx
        assert subnet_idx < rds_idx
        assert sg_idx < ec2_idx
        assert sg_idx < rds_idx
        
    def test_dependency_graph_empty_config(self):
        """Test building dependency graph with no resources."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[]
        )
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        
    def test_dependency_graph_no_dependencies(self):
        """Test building graph with resources that have no dependencies."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="vpc-1",
                    resource_type="vpc",
                    properties={"cidr": "10.0.0.0/16"}
                ),
                ResourceConfig(
                    logical_id="vpc-2",
                    resource_type="vpc",
                    properties={"cidr": "10.1.0.0/16"}
                ),
                ResourceConfig(
                    logical_id="vpc-3",
                    resource_type="vpc",
                    properties={"cidr": "10.2.0.0/16"}
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 0
        
        # All nodes should have no dependencies
        for node in graph.nodes.values():
            assert len(node.dependencies) == 0
            
    def test_topological_sort_independent_resources(self):
        """Test topological sort with independent resources."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="resource-a",
                    resource_type="vpc",
                    properties={}
                ),
                ResourceConfig(
                    logical_id="resource-b",
                    resource_type="vpc",
                    properties={}
                ),
                ResourceConfig(
                    logical_id="resource-c",
                    resource_type="vpc",
                    properties={}
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        order = resolver.topological_sort(graph)
        
        # All resources should be in the result
        assert len(order) == 3
        assert set(order) == {"resource-a", "resource-b", "resource-c"}
        
    def test_cycle_detection_self_reference(self):
        """Test cycle detection with self-referencing resource."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="resource-a",
                    resource_type="vpc",
                    properties={
                        "self_ref": "${resource.resource-a.id}"
                    }
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        cycles = resolver.detect_cycles(graph)
        
        # Self-reference creates a cycle
        assert len(cycles) > 0
        
    def test_cycle_detection_two_node_cycle(self):
        """Test cycle detection with two-node circular dependency."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="resource-a",
                    resource_type="vpc",
                    properties={
                        "ref": "${resource.resource-b.id}"
                    }
                ),
                ResourceConfig(
                    logical_id="resource-b",
                    resource_type="ec2",
                    properties={
                        "ref": "${resource.resource-a.id}"
                    }
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        cycles = resolver.detect_cycles(graph)
        
        assert len(cycles) > 0
        cycle_resources = cycles[0].resources
        assert len(cycle_resources) == 2
        assert "resource-a" in cycle_resources
        assert "resource-b" in cycle_resources
        
    def test_dangling_reference_multiple_errors(self):
        """Test detection of multiple dangling references."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "vpc_ref": "${resource.vpc-missing.id}",
                        "subnet_ref": "${resource.subnet-missing.id}",
                        "sg_ref": "${resource.sg-missing.id}"
                    }
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        result = resolver.resolve_links(config)
        
        assert not result.success
        assert len(result.errors) == 3
        assert any("vpc-missing" in err for err in result.errors)
        assert any("subnet-missing" in err for err in result.errors)
        assert any("sg-missing" in err for err in result.errors)
        
    def test_topological_sort_linear_chain(self):
        """Test topological sort with linear dependency chain."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="resource-a",
                    resource_type="vpc",
                    properties={}
                ),
                ResourceConfig(
                    logical_id="resource-b",
                    resource_type="subnet",
                    properties={"ref": "${resource.resource-a.id}"}
                ),
                ResourceConfig(
                    logical_id="resource-c",
                    resource_type="sg",
                    properties={"ref": "${resource.resource-b.id}"}
                ),
                ResourceConfig(
                    logical_id="resource-d",
                    resource_type="ec2",
                    properties={"ref": "${resource.resource-c.id}"}
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        order = resolver.topological_sort(graph)
        
        # Should be in exact order: a -> b -> c -> d
        assert order == ["resource-a", "resource-b", "resource-c", "resource-d"]
        
    def test_dependency_graph_multiple_references_same_target(self):
        """Test graph construction when multiple properties reference same resource."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="vpc",
                    resource_type="vpc",
                    properties={}
                ),
                ResourceConfig(
                    logical_id="ec2",
                    resource_type="ec2",
                    properties={
                        "vpc_id": "${resource.vpc.id}",
                        "vpc_cidr": "${resource.vpc.cidr}",
                        "vpc_name": "${resource.vpc.name}"
                    }
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        
        # Should have multiple edges but dependency should be listed once
        assert len(graph.edges) == 3
        assert graph.nodes["ec2"].dependencies == ["vpc"]
        
    def test_resolved_links_mapping(self):
        """Test that resolved links mapping is correctly built."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={}
                ),
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={"vpc_ref": "${resource.vpc-main.id}"}
                )
            ]
        )
        
        resolver = ResourceLinkResolver()
        result = resolver.resolve_links(config)
        
        assert result.success
        assert "vpc-main" in result.resolved_links
        assert "ec2-web" in result.resolved_links
        assert result.resolved_links["vpc-main"] == "resource.vpc-main"
        assert result.resolved_links["ec2-web"] == "resource.ec2-web"
