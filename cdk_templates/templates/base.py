"""Base classes for resource templates."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any
from cdk_templates.naming_service import NamingConventionService
from cdk_templates.tagging_service import TaggingStrategyService
from cdk_templates.resource_registry import ResourceRegistry


@dataclass
class GenerationContext:
    """Context available during code generation."""
    environment: str
    region: str
    account_id: str
    naming_service: NamingConventionService
    tagging_service: TaggingStrategyService
    resource_registry: ResourceRegistry
    resolved_links: Dict[str, str]


class ResourceTemplate(ABC):
    """Abstract base class for resource templates."""
    
    @abstractmethod
    def generate_code(self, resource_config: Dict[str, Any], context: GenerationContext) -> str:
        """
        Generate CDK Python code for this resource type.
        
        Args:
            resource_config: Configuration dictionary for the resource
            context: Generation context with services and resolved links
            
        Returns:
            CDK Python code as a string
        """
        pass
    
    @abstractmethod
    def get_outputs(self, resource_config: Dict[str, Any]) -> Dict[str, str]:
        """
        Define outputs that this resource exports.
        
        Args:
            resource_config: Configuration dictionary for the resource
            
        Returns:
            Dictionary mapping output names to their descriptions
        """
        pass
