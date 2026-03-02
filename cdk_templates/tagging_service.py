"""Tagging Strategy Service for consistent resource tagging."""

from typing import Dict
from cdk_templates.models import ResourceConfig, ConfigMetadata


class TaggingStrategyService:
    """Service for applying consistent tagging strategies to AWS resources."""
    
    MANDATORY_TAG_KEYS = ['Environment', 'Project', 'Owner', 'CostCenter', 'ManagedBy']
    MANAGED_BY_VALUE = 'cdk-template-system'
    
    def __init__(self, metadata: ConfigMetadata):
        """
        Initialize the tagging service with project metadata.
        
        Args:
            metadata: Configuration metadata containing project, owner, and cost_center
        """
        self.metadata = metadata
    
    def get_mandatory_tags(self, environment: str) -> Dict[str, str]:
        """
        Get mandatory tags that must be applied to all resources.
        
        Args:
            environment: The environment name (dev, staging, prod)
            
        Returns:
            Dictionary of mandatory tags with their values
        """
        return {
            'Environment': environment,
            'Project': self.metadata.project,
            'Owner': self.metadata.owner,
            'CostCenter': self.metadata.cost_center,
            'ManagedBy': self.MANAGED_BY_VALUE
        }
    
    def apply_tags(self, resource: ResourceConfig, environment: str, custom_tags: Dict[str, str] = None) -> Dict[str, str]:
        """
        Merge mandatory tags with custom tags for a resource.
        
        Mandatory tags cannot be overridden by custom tags.
        
        Args:
            resource: The resource configuration
            environment: The environment name
            custom_tags: Optional custom tags to add
            
        Returns:
            Dictionary containing all tags (mandatory + custom)
        """
        # Start with mandatory tags
        tags = self.get_mandatory_tags(environment)
        
        # Add custom tags from the parameter (if provided)
        if custom_tags:
            for key, value in custom_tags.items():
                # Only add custom tag if it's not a mandatory tag key
                if key not in self.MANDATORY_TAG_KEYS:
                    tags[key] = value
        
        # Add custom tags from the resource configuration
        if resource.tags:
            for key, value in resource.tags.items():
                # Only add custom tag if it's not a mandatory tag key
                if key not in self.MANDATORY_TAG_KEYS:
                    tags[key] = value
        
        return tags
    
    def inherit_tags(self, parent_tags: Dict[str, str], child_tags: Dict[str, str]) -> Dict[str, str]:
        """
        Inherit tags from parent resource to child resource.
        
        Child tags take precedence over parent tags for the same key.
        
        Args:
            parent_tags: Tags from the parent resource
            child_tags: Tags from the child resource
            
        Returns:
            Dictionary containing inherited tags (parent + child, with child taking precedence)
        """
        # Start with parent tags
        inherited = parent_tags.copy()
        
        # Override with child tags
        inherited.update(child_tags)
        
        return inherited
