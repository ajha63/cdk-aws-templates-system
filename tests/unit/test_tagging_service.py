"""Unit tests for TaggingStrategyService."""

import pytest
from cdk_templates.tagging_service import TaggingStrategyService
from cdk_templates.models import ConfigMetadata, ResourceConfig


@pytest.fixture
def metadata():
    """Create sample configuration metadata."""
    return ConfigMetadata(
        project='test-project',
        owner='test-team',
        cost_center='CC-12345',
        description='Test project'
    )


@pytest.fixture
def tagging_service(metadata):
    """Create a TaggingStrategyService instance."""
    return TaggingStrategyService(metadata)


class TestGetMandatoryTags:
    """Tests for get_mandatory_tags method."""
    
    def test_returns_all_mandatory_tags(self, tagging_service):
        """Test that all mandatory tags are returned."""
        tags = tagging_service.get_mandatory_tags('dev')
        
        assert 'Environment' in tags
        assert 'Project' in tags
        assert 'Owner' in tags
        assert 'CostCenter' in tags
        assert 'ManagedBy' in tags
    
    def test_environment_tag_matches_parameter(self, tagging_service):
        """Test that Environment tag matches the provided environment."""
        tags = tagging_service.get_mandatory_tags('production')
        assert tags['Environment'] == 'production'
        
        tags = tagging_service.get_mandatory_tags('dev')
        assert tags['Environment'] == 'dev'
    
    def test_project_tag_from_metadata(self, tagging_service):
        """Test that Project tag comes from metadata."""
        tags = tagging_service.get_mandatory_tags('dev')
        assert tags['Project'] == 'test-project'
    
    def test_owner_tag_from_metadata(self, tagging_service):
        """Test that Owner tag comes from metadata."""
        tags = tagging_service.get_mandatory_tags('dev')
        assert tags['Owner'] == 'test-team'
    
    def test_cost_center_tag_from_metadata(self, tagging_service):
        """Test that CostCenter tag comes from metadata."""
        tags = tagging_service.get_mandatory_tags('dev')
        assert tags['CostCenter'] == 'CC-12345'
    
    def test_managed_by_tag_is_system(self, tagging_service):
        """Test that ManagedBy tag is set to the system name."""
        tags = tagging_service.get_mandatory_tags('dev')
        assert tags['ManagedBy'] == 'cdk-template-system'


class TestApplyTags:
    """Tests for apply_tags method."""
    
    def test_includes_all_mandatory_tags(self, tagging_service):
        """Test that mandatory tags are always included."""
        resource = ResourceConfig(
            logical_id='test-resource',
            resource_type='ec2'
        )
        
        tags = tagging_service.apply_tags(resource, 'dev')
        
        assert tags['Environment'] == 'dev'
        assert tags['Project'] == 'test-project'
        assert tags['Owner'] == 'test-team'
        assert tags['CostCenter'] == 'CC-12345'
        assert tags['ManagedBy'] == 'cdk-template-system'
    
    def test_adds_custom_tags_from_parameter(self, tagging_service):
        """Test that custom tags from parameter are added."""
        resource = ResourceConfig(
            logical_id='test-resource',
            resource_type='ec2'
        )
        custom_tags = {'Application': 'web-app', 'Version': '1.0'}
        
        tags = tagging_service.apply_tags(resource, 'dev', custom_tags)
        
        assert tags['Application'] == 'web-app'
        assert tags['Version'] == '1.0'
    
    def test_adds_custom_tags_from_resource(self, tagging_service):
        """Test that custom tags from resource configuration are added."""
        resource = ResourceConfig(
            logical_id='test-resource',
            resource_type='ec2',
            tags={'Application': 'web-app', 'Version': '1.0'}
        )
        
        tags = tagging_service.apply_tags(resource, 'dev')
        
        assert tags['Application'] == 'web-app'
        assert tags['Version'] == '1.0'
    
    def test_custom_tags_cannot_override_mandatory_tags(self, tagging_service):
        """Test that custom tags cannot override mandatory tags."""
        resource = ResourceConfig(
            logical_id='test-resource',
            resource_type='ec2',
            tags={'Environment': 'hacked', 'Project': 'malicious'}
        )
        custom_tags = {'Owner': 'attacker', 'ManagedBy': 'manual'}
        
        tags = tagging_service.apply_tags(resource, 'dev', custom_tags)
        
        # Mandatory tags should not be overridden
        assert tags['Environment'] == 'dev'
        assert tags['Project'] == 'test-project'
        assert tags['Owner'] == 'test-team'
        assert tags['ManagedBy'] == 'cdk-template-system'
    
    def test_combines_resource_and_parameter_custom_tags(self, tagging_service):
        """Test that custom tags from both sources are combined."""
        resource = ResourceConfig(
            logical_id='test-resource',
            resource_type='ec2',
            tags={'Application': 'web-app'}
        )
        custom_tags = {'Version': '1.0'}
        
        tags = tagging_service.apply_tags(resource, 'dev', custom_tags)
        
        assert tags['Application'] == 'web-app'
        assert tags['Version'] == '1.0'
    
    def test_works_with_no_custom_tags(self, tagging_service):
        """Test that apply_tags works with no custom tags."""
        resource = ResourceConfig(
            logical_id='test-resource',
            resource_type='ec2'
        )
        
        tags = tagging_service.apply_tags(resource, 'dev')
        
        # Should only have mandatory tags
        assert len(tags) == 5
        assert all(key in tags for key in TaggingStrategyService.MANDATORY_TAG_KEYS)


class TestInheritTags:
    """Tests for inherit_tags method."""
    
    def test_child_inherits_parent_tags(self, tagging_service):
        """Test that child inherits all parent tags."""
        parent_tags = {
            'Environment': 'prod',
            'Project': 'test-project',
            'Owner': 'test-team'
        }
        child_tags = {}
        
        inherited = tagging_service.inherit_tags(parent_tags, child_tags)
        
        assert inherited['Environment'] == 'prod'
        assert inherited['Project'] == 'test-project'
        assert inherited['Owner'] == 'test-team'
    
    def test_child_tags_override_parent_tags(self, tagging_service):
        """Test that child tags take precedence over parent tags."""
        parent_tags = {
            'Environment': 'prod',
            'Application': 'parent-app',
            'Version': '1.0'
        }
        child_tags = {
            'Application': 'child-app',
            'Version': '2.0'
        }
        
        inherited = tagging_service.inherit_tags(parent_tags, child_tags)
        
        assert inherited['Environment'] == 'prod'  # from parent
        assert inherited['Application'] == 'child-app'  # overridden by child
        assert inherited['Version'] == '2.0'  # overridden by child
    
    def test_child_adds_new_tags(self, tagging_service):
        """Test that child can add new tags not present in parent."""
        parent_tags = {
            'Environment': 'prod',
            'Project': 'test-project'
        }
        child_tags = {
            'SubResource': 'subnet',
            'AZ': 'us-east-1a'
        }
        
        inherited = tagging_service.inherit_tags(parent_tags, child_tags)
        
        assert inherited['Environment'] == 'prod'
        assert inherited['Project'] == 'test-project'
        assert inherited['SubResource'] == 'subnet'
        assert inherited['AZ'] == 'us-east-1a'
    
    def test_empty_parent_tags(self, tagging_service):
        """Test inheritance with empty parent tags."""
        parent_tags = {}
        child_tags = {'Application': 'web-app'}
        
        inherited = tagging_service.inherit_tags(parent_tags, child_tags)
        
        assert inherited == child_tags
    
    def test_empty_child_tags(self, tagging_service):
        """Test inheritance with empty child tags."""
        parent_tags = {'Application': 'web-app'}
        child_tags = {}
        
        inherited = tagging_service.inherit_tags(parent_tags, child_tags)
        
        assert inherited == parent_tags
    
    def test_does_not_modify_original_tags(self, tagging_service):
        """Test that original tag dictionaries are not modified."""
        parent_tags = {'Environment': 'prod'}
        child_tags = {'Application': 'web-app'}
        
        original_parent = parent_tags.copy()
        original_child = child_tags.copy()
        
        tagging_service.inherit_tags(parent_tags, child_tags)
        
        assert parent_tags == original_parent
        assert child_tags == original_child
