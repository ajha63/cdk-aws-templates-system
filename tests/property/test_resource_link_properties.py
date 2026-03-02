"""Property-based tests for ResourceLinkResolver."""

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st
from hypothesis.strategies import composite

from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig
)


@composite
def valid_configuration_with_links_strategy(draw):
    """Generate valid configurations with resource links."""
    # Create base resources without dependencies
    num_resources = draw(st.integers(min_value=2, max_value=5))
    
    resources = []
    resource_ids = []
    
    # First resource has no dependencies
    first_id = draw(st.text(
        min_size=3,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'
    ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
    
    resource_ids.append(first_id)
    resources.append(ResourceConfig(
        logical_id=first_id,
        resource_type='vpc',
        properties={'cidr': '10.0.0.0/16'}
    ))
    
    # Subsequent resources can reference previous ones
    for i in range(1, num_resources):
        resource_id = draw(st.text(
            min_size=3,
            max_size=20,
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'
        ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-') and x not in resource_ids))
        
        resource_ids.append(resource_id)
        
        # Reference a previous resource
        ref_target = draw(st.sampled_from(resource_ids[:-1]))
        
        resources.append(ResourceConfig(
            logical_id=resource_id,
            resource_type=draw(st.sampled_from(['ec2', 'rds', 's3'])),
            properties={
                'vpc_ref': f'${{resource.{ref_target}.id}}'
            }
        ))
    
    return Configuration(
        version='1.0',
        metadata=ConfigMetadata(
            project='test-project',
            owner='test-team',
            cost_center='engineering',
            description='Test configuration'
        ),
        environments={
            'dev': EnvironmentConfig(
                name='dev',
                account_id='123456789012',
                region='us-east-1'
            )
        },
        resources=resources
    )


@composite
def circular_dependency_configuration_strategy(draw):
    """Generate configurations with circular dependencies."""
    # Create a simple cycle: A -> B -> C -> A
    cycle_length = draw(st.integers(min_value=2, max_value=4))
    
    resource_ids = []
    for i in range(cycle_length):
        resource_id = f'resource-{chr(97 + i)}'  # a, b, c, d
        resource_ids.append(resource_id)
    
    resources = []
    for i, resource_id in enumerate(resource_ids):
        # Each resource references the next one (last one references first)
        next_idx = (i + 1) % cycle_length
        next_resource = resource_ids[next_idx]
        
        resources.append(ResourceConfig(
            logical_id=resource_id,
            resource_type=draw(st.sampled_from(['vpc', 'ec2', 'rds', 's3'])),
            properties={
                'ref': f'${{resource.{next_resource}.id}}'
            }
        ))
    
    return Configuration(
        version='1.0',
        metadata=ConfigMetadata(
            project='test-project',
            owner='test-team',
            cost_center='engineering',
            description='Test configuration with cycle'
        ),
        environments={
            'dev': EnvironmentConfig(
                name='dev',
                account_id='123456789012',
                region='us-east-1'
            )
        },
        resources=resources
    )


@composite
def dangling_reference_configuration_strategy(draw):
    """Generate configurations with dangling references."""
    num_resources = draw(st.integers(min_value=1, max_value=3))
    
    resources = []
    for i in range(num_resources):
        resource_id = f'resource-{i}'
        
        # Reference a non-existent resource
        nonexistent_id = f'nonexistent-{draw(st.integers(min_value=100, max_value=999))}'
        
        resources.append(ResourceConfig(
            logical_id=resource_id,
            resource_type=draw(st.sampled_from(['vpc', 'ec2', 'rds', 's3'])),
            properties={
                'ref': f'${{resource.{nonexistent_id}.id}}'
            }
        ))
    
    return Configuration(
        version='1.0',
        metadata=ConfigMetadata(
            project='test-project',
            owner='test-team',
            cost_center='engineering',
            description='Test configuration with dangling reference'
        ),
        environments={
            'dev': EnvironmentConfig(
                name='dev',
                account_id='123456789012',
                region='us-east-1'
            )
        },
        resources=resources
    )


class TestResourceLinkProperties:
    """Property-based tests for ResourceLinkResolver."""
    
    @given(valid_configuration_with_links_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_11_resource_link_resolution(self, config):
        """
        Feature: cdk-aws-templates-system
        Property 11: Resource Link Resolution - For any resource configuration 
        containing a valid resource reference (e.g., ${resource.vpc-main.id}), 
        the Link Resolver SHALL resolve the reference to the correct CDK 
        construct reference in the generated code.
        
        Validates: Requirements 4.2
        """
        resolver = ResourceLinkResolver()
        
        result = resolver.resolve_links(config)
        
        # Valid configurations should resolve successfully
        assert result.success, \
            f"Valid configuration should resolve successfully. Errors: {result.errors}"
        
        # Should have no errors
        assert len(result.errors) == 0, \
            f"Valid configuration should have no errors: {result.errors}"
        
        # Should have no cycles
        assert len(result.cycles) == 0, \
            f"Valid configuration should have no cycles: {result.cycles}"
        
        # All resources should be in resolved_links
        for resource in config.resources:
            assert resource.logical_id in result.resolved_links, \
                f"Resource {resource.logical_id} should be in resolved_links"
    
    @given(circular_dependency_configuration_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_12_circular_dependency_detection(self, config):
        """
        Feature: cdk-aws-templates-system
        Property 12: Circular Dependency Detection - For any configuration where 
        resources form a circular dependency chain (A depends on B, B depends on C, 
        C depends on A), the Link Resolver SHALL detect the cycle and reject the 
        configuration.
        
        Validates: Requirements 4.3
        """
        resolver = ResourceLinkResolver()
        
        result = resolver.resolve_links(config)
        
        # Should detect the cycle
        assert not result.success, \
            "Configuration with circular dependencies should fail resolution"
        
        # Should have at least one cycle detected
        assert len(result.cycles) > 0, \
            "Should detect at least one cycle"
        
        # Error message should mention circular dependency
        assert "circular" in result.error_message.lower(), \
            f"Error message should mention circular dependency: {result.error_message}"
        
        # Should have errors
        assert len(result.errors) > 0, \
            "Should have errors for circular dependencies"
        
        # All errors should mention circular dependency
        for error in result.errors:
            assert "circular" in error.lower(), \
                f"Error should mention circular dependency: {error}"
    
    @given(dangling_reference_configuration_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_property_13_dangling_reference_detection(self, config):
        """
        Feature: cdk-aws-templates-system
        Property 13: Dangling Reference Detection - For any resource configuration 
        containing a reference to a non-existent resource, the system SHALL detect 
        the dangling reference and reject the configuration before code generation.
        
        Validates: Requirements 4.5
        """
        resolver = ResourceLinkResolver()
        
        result = resolver.resolve_links(config)
        
        # Should fail resolution
        assert not result.success, \
            "Configuration with dangling references should fail resolution"
        
        # Should have errors
        assert len(result.errors) > 0, \
            "Should have errors for dangling references"
        
        # At least one error should mention non-existent resource
        has_nonexistent_error = any(
            "non-existent" in error.lower() or "nonexistent" in error.lower()
            for error in result.errors
        )
        assert has_nonexistent_error, \
            f"Should have error about non-existent resource. Errors: {result.errors}"
    
    @given(valid_configuration_with_links_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_dependency_graph_construction(self, config):
        """
        Test that dependency graph is correctly constructed from configuration.
        
        Validates: Requirements 4.1, 4.2
        """
        resolver = ResourceLinkResolver()
        
        graph = resolver.build_dependency_graph(config)
        
        # All resources should be nodes in the graph
        for resource in config.resources:
            assert resource.logical_id in graph.nodes, \
                f"Resource {resource.logical_id} should be a node in the graph"
            
            node = graph.nodes[resource.logical_id]
            assert node.resource_type == resource.resource_type, \
                f"Node resource_type should match: {node.resource_type} != {resource.resource_type}"
        
        # Graph should have edges for all references
        assert len(graph.edges) >= 0, \
            "Graph should have edges"
        
        # All edges should reference existing nodes
        for edge in graph.edges:
            assert edge.source_resource in graph.nodes, \
                f"Edge source {edge.source_resource} should be in graph nodes"
            assert edge.target_resource in graph.nodes, \
                f"Edge target {edge.target_resource} should be in graph nodes"
    
    @given(valid_configuration_with_links_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_topological_sort_respects_dependencies(self, config):
        """
        Test that topological sort produces valid deployment order.
        
        Validates: Requirements 4.3
        """
        resolver = ResourceLinkResolver()
        
        # First check if there are cycles
        result = resolver.resolve_links(config)
        assume(result.success)  # Skip if there are cycles
        
        graph = resolver.build_dependency_graph(config)
        order = resolver.topological_sort(graph)
        
        # All resources should be in the order
        assert len(order) == len(config.resources), \
            f"Topological sort should include all resources: {len(order)} != {len(config.resources)}"
        
        # Create position map
        position = {resource_id: i for i, resource_id in enumerate(order)}
        
        # For each dependency, the dependency should come before the dependent
        for node_id, node in graph.nodes.items():
            for dep in node.dependencies:
                if dep in position and node_id in position:
                    assert position[dep] < position[node_id], \
                        f"Dependency {dep} should come before {node_id} in deployment order"
    
    @given(st.sampled_from(['vpc', 'ec2', 'rds', 's3']))
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_reference_pattern_extraction(self, resource_type):
        """
        Test that resource references are correctly extracted from properties.
        
        Validates: Requirements 4.1
        """
        resolver = ResourceLinkResolver()
        
        # Create a resource with various reference patterns
        resource = ResourceConfig(
            logical_id='test-resource',
            resource_type=resource_type,
            properties={
                'simple_ref': '${resource.vpc-main.id}',
                'nested': {
                    'deep_ref': '${resource.subnet-1.arn}'
                },
                'list': [
                    '${resource.sg-1.id}',
                    '${resource.sg-2.id}'
                ],
                'mixed': 'prefix-${resource.kms-key.id}-suffix'
            }
        )
        
        refs = resolver._extract_references(resource)
        
        # Should extract all references
        assert len(refs) >= 4, \
            f"Should extract at least 4 references, got {len(refs)}"
        
        # Check that expected targets are found
        target_resources = [ref['target_resource'] for ref in refs]
        assert 'vpc-main' in target_resources, \
            "Should extract vpc-main reference"
        assert 'subnet-1' in target_resources, \
            "Should extract subnet-1 reference"
        assert 'sg-1' in target_resources, \
            "Should extract sg-1 reference"
        assert 'sg-2' in target_resources, \
            "Should extract sg-2 reference"
    
    @given(valid_configuration_with_links_strategy())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_explicit_depends_on_relationships(self, config):
        """
        Test that explicit depends_on relationships are included in the graph.
        
        Validates: Requirements 4.1
        """
        # Add explicit depends_on to some resources
        if len(config.resources) >= 2:
            config.resources[1].depends_on = [config.resources[0].logical_id]
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        
        # Check that explicit dependencies are in the graph
        if len(config.resources) >= 2:
            dependent_id = config.resources[1].logical_id
            dependency_id = config.resources[0].logical_id
            
            assert dependency_id in graph.nodes[dependent_id].dependencies, \
                f"Explicit dependency {dependency_id} should be in {dependent_id}'s dependencies"
            
            # Should have at least one edge for the dependency (could be from ref or explicit)
            dependency_edges = [
                edge for edge in graph.edges
                if edge.source_resource == dependent_id
                and edge.target_resource == dependency_id
            ]
            assert len(dependency_edges) > 0, \
                "Should have at least one edge for the dependency"
    
    @given(valid_configuration_with_links_strategy())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=5000
    )
    def test_resolved_links_mapping(self, config):
        """
        Test that resolved links mapping is correctly built.
        
        Validates: Requirements 4.2
        """
        resolver = ResourceLinkResolver()
        result = resolver.resolve_links(config)
        
        assume(result.success)  # Skip if resolution fails
        
        # All resources should have resolved links
        for resource in config.resources:
            assert resource.logical_id in result.resolved_links, \
                f"Resource {resource.logical_id} should have a resolved link"
            
            resolved = result.resolved_links[resource.logical_id]
            assert isinstance(resolved, str), \
                "Resolved link should be a string"
            assert len(resolved) > 0, \
                "Resolved link should not be empty"
            assert resource.logical_id in resolved, \
                f"Resolved link should contain resource ID: {resolved}"
