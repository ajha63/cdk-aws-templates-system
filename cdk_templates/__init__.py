"""CDK AWS Templates System - A declarative framework for AWS CDK infrastructure."""

__version__ = "1.0.0"

from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.validation_engine import ValidationEngine, ValidationException
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
    ResourceLink,
    ResourceNode,
    DependencyGraph,
    Cycle,
    LinkResolutionResult,
    ValidationError,
    ValidationResult,
    ResourceMetadata
)

__all__ = [
    'ResourceLinkResolver',
    'ValidationEngine',
    'ValidationException',
    'Configuration',
    'ConfigMetadata',
    'EnvironmentConfig',
    'ResourceConfig',
    'ResourceLink',
    'ResourceNode',
    'DependencyGraph',
    'Cycle',
    'LinkResolutionResult',
    'ValidationError',
    'ValidationResult',
    'ResourceMetadata'
]
