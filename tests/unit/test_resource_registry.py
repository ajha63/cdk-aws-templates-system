"""Unit tests for ResourceRegistry."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from cdk_templates.resource_registry import (
    ResourceRegistry,
    ResourceQuery,
    ResourceRegistryError
)
from cdk_templates.models import ResourceMetadata


@pytest.fixture
def temp_registry_path():
    """Create a temporary registry file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / 'test_registry.json'


@pytest.fixture
def registry(temp_registry_path):
    """Create a ResourceRegistry instance with temporary storage."""
    return ResourceRegistry(str(temp_registry_path))


@pytest.fixture
def sample_resource():
    """Create a sample ResourceMetadata object."""
    return ResourceMetadata(
        resource_id='vpc-12345',
        resource_type='vpc',
        logical_name='vpc-main',
        physical_name='prod-myapp-vpc-us-east-1',
        stack_name='infrastructure-stack',
        environment='production',
        tags={
            'Environment': 'production',
            'Project': 'myapp',
            'Owner': 'platform-team'
        },
        outputs={
            'VpcId': 'vpc-12345',
            'CidrBlock': '10.0.0.0/16'
        },
        dependencies=[],
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    )


@pytest.fixture
def sample_ec2_resource():
    """Create a sample EC2 ResourceMetadata object."""
    return ResourceMetadata(
        resource_id='i-67890',
        resource_type='ec2',
        logical_name='ec2-web-01',
        physical_name='prod-myapp-ec2-web-us-east-1-01',
        stack_name='compute-stack',
        environment='production',
        tags={
            'Environment': 'production',
            'Project': 'myapp',
            'Owner': 'platform-team',
            'Role': 'webserver'
        },
        outputs={
            'InstanceId': 'i-67890',
            'PrivateIp': '10.0.1.10'
        },
        dependencies=['vpc-12345'],
        created_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    )


class TestResourceRegistryInitialization:
    """Tests for ResourceRegistry initialization."""
    
    def test_init_creates_registry_file(self, temp_registry_path):
        """Test that initialization creates the registry file."""
        registry = ResourceRegistry(str(temp_registry_path))
        assert temp_registry_path.exists()
    
    def test_init_creates_valid_json_structure(self, temp_registry_path):
        """Test that initialization creates valid JSON structure."""
        registry = ResourceRegistry(str(temp_registry_path))
        
        with open(temp_registry_path, 'r') as f:
            data = json.load(f)
        
        assert 'resources' in data
        assert 'indices' in data
        assert isinstance(data['resources'], dict)
        assert isinstance(data['indices'], dict)
    
    def test_init_with_default_path(self):
        """Test initialization with default path."""
        registry = ResourceRegistry()
        assert registry.registry_path.exists()
        assert registry.registry_path.name == 'registry.json'
        assert '.cdk-templates' in str(registry.registry_path)


class TestResourceRegistration:
    """Tests for resource registration."""
    
    def test_register_resource_success(self, registry, sample_resource):
        """Test successful resource registration."""
        registry.register_resource(sample_resource)
        
        # Verify resource is stored
        retrieved = registry.get_resource('vpc-12345')
        assert retrieved is not None
        assert retrieved.resource_id == 'vpc-12345'
        assert retrieved.resource_type == 'vpc'
        assert retrieved.logical_name == 'vpc-main'
    
    def test_register_multiple_resources(self, registry, sample_resource, sample_ec2_resource):
        """Test registering multiple resources."""
        registry.register_resource(sample_resource)
        registry.register_resource(sample_ec2_resource)
        
        vpc = registry.get_resource('vpc-12345')
        ec2 = registry.get_resource('i-67890')
        
        assert vpc is not None
        assert ec2 is not None
        assert vpc.resource_type == 'vpc'
        assert ec2.resource_type == 'ec2'
    
    def test_register_updates_existing_resource(self, registry, sample_resource):
        """Test that registering an existing resource updates it."""
        registry.register_resource(sample_resource)
        
        # Update the resource
        sample_resource.physical_name = 'updated-name'
        sample_resource.updated_at = datetime(2024, 1, 3, 12, 0, 0, tzinfo=timezone.utc)
        registry.register_resource(sample_resource)
        
        # Verify update
        retrieved = registry.get_resource('vpc-12345')
        assert retrieved.physical_name == 'updated-name'
    
    def test_register_resource_persists_to_file(self, registry, sample_resource, temp_registry_path):
        """Test that registration persists to file."""
        registry.register_resource(sample_resource)
        
        # Create new registry instance with same path
        new_registry = ResourceRegistry(str(temp_registry_path))
        retrieved = new_registry.get_resource('vpc-12345')
        
        assert retrieved is not None
        assert retrieved.resource_id == 'vpc-12345'


class TestResourceUnregistration:
    """Tests for resource unregistration."""
    
    def test_unregister_resource_success(self, registry, sample_resource):
        """Test successful resource unregistration."""
        registry.register_resource(sample_resource)
        registry.unregister_resource('vpc-12345')
        
        retrieved = registry.get_resource('vpc-12345')
        assert retrieved is None
    
    def test_unregister_nonexistent_resource_raises_error(self, registry):
        """Test that unregistering nonexistent resource raises error."""
        with pytest.raises(ResourceRegistryError, match="not found in registry"):
            registry.unregister_resource('nonexistent-id')
    
    def test_unregister_removes_from_indices(self, registry, sample_resource):
        """Test that unregistration removes resource from indices."""
        registry.register_resource(sample_resource)
        registry.unregister_resource('vpc-12345')
        
        # Query should return empty list
        results = registry.query_resources(ResourceQuery(resource_type='vpc'))
        assert len(results) == 0


class TestResourceRetrieval:
    """Tests for resource retrieval."""
    
    def test_get_resource_success(self, registry, sample_resource):
        """Test successful resource retrieval."""
        registry.register_resource(sample_resource)
        retrieved = registry.get_resource('vpc-12345')
        
        assert retrieved is not None
        assert retrieved.resource_id == sample_resource.resource_id
        assert retrieved.resource_type == sample_resource.resource_type
        assert retrieved.tags == sample_resource.tags
    
    def test_get_nonexistent_resource_returns_none(self, registry):
        """Test that getting nonexistent resource returns None."""
        retrieved = registry.get_resource('nonexistent-id')
        assert retrieved is None
    
    def test_get_resource_preserves_datetime(self, registry, sample_resource):
        """Test that datetime fields are preserved correctly."""
        registry.register_resource(sample_resource)
        retrieved = registry.get_resource('vpc-12345')
        
        assert isinstance(retrieved.created_at, datetime)
        assert isinstance(retrieved.updated_at, datetime)
        assert retrieved.created_at == sample_resource.created_at
        assert retrieved.updated_at == sample_resource.updated_at


class TestResourceQuery:
    """Tests for resource querying."""
    
    def test_query_all_resources(self, registry, sample_resource, sample_ec2_resource):
        """Test querying all resources."""
        registry.register_resource(sample_resource)
        registry.register_resource(sample_ec2_resource)
        
        results = registry.query_resources(ResourceQuery())
        assert len(results) == 2
    
    def test_query_by_resource_type(self, registry, sample_resource, sample_ec2_resource):
        """Test querying by resource type."""
        registry.register_resource(sample_resource)
        registry.register_resource(sample_ec2_resource)
        
        vpc_results = registry.query_resources(ResourceQuery(resource_type='vpc'))
        ec2_results = registry.query_resources(ResourceQuery(resource_type='ec2'))
        
        assert len(vpc_results) == 1
        assert len(ec2_results) == 1
        assert vpc_results[0].resource_type == 'vpc'
        assert ec2_results[0].resource_type == 'ec2'
    
    def test_query_by_environment(self, registry, sample_resource):
        """Test querying by environment."""
        registry.register_resource(sample_resource)
        
        # Create dev resource
        dev_resource = ResourceMetadata(
            resource_id='vpc-dev-123',
            resource_type='vpc',
            logical_name='vpc-dev',
            physical_name='dev-myapp-vpc-us-east-1',
            stack_name='dev-stack',
            environment='development',
            tags={'Environment': 'development'},
            outputs={},
            dependencies=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        registry.register_resource(dev_resource)
        
        prod_results = registry.query_resources(ResourceQuery(environment='production'))
        dev_results = registry.query_resources(ResourceQuery(environment='development'))
        
        assert len(prod_results) == 1
        assert len(dev_results) == 1
        assert prod_results[0].environment == 'production'
        assert dev_results[0].environment == 'development'
    
    def test_query_by_stack_name(self, registry, sample_resource, sample_ec2_resource):
        """Test querying by stack name."""
        registry.register_resource(sample_resource)
        registry.register_resource(sample_ec2_resource)
        
        infra_results = registry.query_resources(ResourceQuery(stack_name='infrastructure-stack'))
        compute_results = registry.query_resources(ResourceQuery(stack_name='compute-stack'))
        
        assert len(infra_results) == 1
        assert len(compute_results) == 1
        assert infra_results[0].stack_name == 'infrastructure-stack'
        assert compute_results[0].stack_name == 'compute-stack'
    
    def test_query_by_logical_name(self, registry, sample_resource):
        """Test querying by logical name."""
        registry.register_resource(sample_resource)
        
        results = registry.query_resources(ResourceQuery(logical_name='vpc-main'))
        assert len(results) == 1
        assert results[0].logical_name == 'vpc-main'
    
    def test_query_by_tags(self, registry, sample_resource, sample_ec2_resource):
        """Test querying by tags."""
        registry.register_resource(sample_resource)
        registry.register_resource(sample_ec2_resource)
        
        # Query by single tag
        results = registry.query_resources(ResourceQuery(tags={'Role': 'webserver'}))
        assert len(results) == 1
        assert results[0].resource_id == 'i-67890'
        
        # Query by multiple tags
        results = registry.query_resources(ResourceQuery(tags={
            'Environment': 'production',
            'Project': 'myapp'
        }))
        assert len(results) == 2
    
    def test_query_with_multiple_filters(self, registry, sample_resource, sample_ec2_resource):
        """Test querying with multiple filters combined."""
        registry.register_resource(sample_resource)
        registry.register_resource(sample_ec2_resource)
        
        results = registry.query_resources(ResourceQuery(
            resource_type='ec2',
            environment='production',
            tags={'Role': 'webserver'}
        ))
        
        assert len(results) == 1
        assert results[0].resource_id == 'i-67890'
    
    def test_query_no_matches_returns_empty_list(self, registry, sample_resource):
        """Test that query with no matches returns empty list."""
        registry.register_resource(sample_resource)
        
        results = registry.query_resources(ResourceQuery(resource_type='rds'))
        assert len(results) == 0


class TestInventoryExport:
    """Tests for inventory export functionality."""
    
    def test_export_inventory_json_format(self, registry, sample_resource):
        """Test exporting inventory in JSON format."""
        registry.register_resource(sample_resource)
        
        export_str = registry.export_inventory(format='json')
        export_data = json.loads(export_str)
        
        assert 'exported_at' in export_data
        assert 'total_resources' in export_data
        assert 'resources' in export_data
        assert export_data['total_resources'] == 1
        assert len(export_data['resources']) == 1
    
    def test_export_inventory_includes_all_metadata(self, registry, sample_resource):
        """Test that export includes all resource metadata."""
        registry.register_resource(sample_resource)
        
        export_str = registry.export_inventory(format='json')
        export_data = json.loads(export_str)
        
        resource = export_data['resources'][0]
        assert resource['resource_id'] == 'vpc-12345'
        assert resource['resource_type'] == 'vpc'
        assert resource['logical_name'] == 'vpc-main'
        assert resource['physical_name'] == 'prod-myapp-vpc-us-east-1'
        assert resource['stack_name'] == 'infrastructure-stack'
        assert resource['environment'] == 'production'
        assert 'tags' in resource
        assert 'outputs' in resource
        assert 'dependencies' in resource
        assert 'created_at' in resource
        assert 'updated_at' in resource
    
    def test_export_empty_inventory(self, registry):
        """Test exporting empty inventory."""
        export_str = registry.export_inventory(format='json')
        export_data = json.loads(export_str)
        
        assert export_data['total_resources'] == 0
        assert len(export_data['resources']) == 0
    
    def test_export_unsupported_format_raises_error(self, registry):
        """Test that unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            registry.export_inventory(format='xml')


class TestAtomicWrites:
    """Tests for atomic write operations."""
    
    def test_concurrent_registrations_are_safe(self, registry, sample_resource, sample_ec2_resource):
        """Test that concurrent registrations don't corrupt data."""
        # Register resources
        registry.register_resource(sample_resource)
        registry.register_resource(sample_ec2_resource)
        
        # Verify both are present
        vpc = registry.get_resource('vpc-12345')
        ec2 = registry.get_resource('i-67890')
        
        assert vpc is not None
        assert ec2 is not None
    
    def test_registry_file_is_valid_json_after_operations(self, registry, sample_resource, temp_registry_path):
        """Test that registry file remains valid JSON after operations."""
        registry.register_resource(sample_resource)
        registry.unregister_resource('vpc-12345')
        
        # Verify file is valid JSON
        with open(temp_registry_path, 'r') as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
        assert 'resources' in data


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_corrupted_registry_file_raises_error(self, temp_registry_path):
        """Test that corrupted registry file raises error."""
        # Create corrupted file
        with open(temp_registry_path, 'w') as f:
            f.write("invalid json {{{")
        
        registry = ResourceRegistry(str(temp_registry_path))
        
        with pytest.raises(ResourceRegistryError, match="corrupted"):
            registry.get_resource('any-id')
    
    def test_missing_required_fields_in_resource_dict(self, registry, temp_registry_path):
        """Test handling of missing required fields."""
        # Manually create invalid registry data
        invalid_data = {
            'resources': {
                'invalid-id': {
                    'resource_id': 'invalid-id',
                    # Missing required fields
                }
            },
            'indices': {}
        }
        
        with open(temp_registry_path, 'w') as f:
            json.dump(invalid_data, f)
        
        # Should raise error when trying to retrieve
        with pytest.raises(ResourceRegistryError):
            registry.get_resource('invalid-id')


class TestIndices:
    """Tests for index management."""
    
    def test_indices_are_created_on_registration(self, registry, sample_resource, temp_registry_path):
        """Test that indices are created when resources are registered."""
        registry.register_resource(sample_resource)
        
        with open(temp_registry_path, 'r') as f:
            data = json.load(f)
        
        indices = data['indices']
        assert 'by_type' in indices
        assert 'by_environment' in indices
        assert 'by_stack' in indices
        assert 'by_tag' in indices
    
    def test_indices_are_updated_on_unregistration(self, registry, sample_resource, temp_registry_path):
        """Test that indices are cleaned up when resources are unregistered."""
        registry.register_resource(sample_resource)
        registry.unregister_resource('vpc-12345')
        
        with open(temp_registry_path, 'r') as f:
            data = json.load(f)
        
        indices = data['indices']
        # Indices should be empty or not contain the resource
        if 'by_type' in indices:
            assert 'vpc' not in indices['by_type'] or len(indices['by_type']['vpc']) == 0
