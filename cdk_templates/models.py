"""Core data models for the CDK AWS Templates System."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class ConfigMetadata:
    """Metadata about the infrastructure project."""
    project: str
    owner: str
    cost_center: str
    description: str


@dataclass
class EnvironmentConfig:
    """Configuration for a specific environment (dev, staging, prod)."""
    name: str
    account_id: str
    region: str
    tags: Dict[str, str] = field(default_factory=dict)
    overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceConfig:
    """Configuration for a single AWS resource."""
    logical_id: str
    resource_type: str  # vpc, ec2, rds, s3
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    outputs: Dict[str, str] = field(default_factory=dict)  # output_name -> description
    stack: Optional[str] = None  # Stack name this resource belongs to


@dataclass
class StackConfig:
    """Configuration for a CDK stack."""
    stack_id: str
    description: str
    resources: List[str] = field(default_factory=list)  # List of resource logical_ids


@dataclass
class Configuration:
    """Complete system configuration."""
    version: str
    metadata: ConfigMetadata
    environments: Dict[str, EnvironmentConfig]
    resources: List[ResourceConfig]
    deployment_rules: List[str] = field(default_factory=list)
    stacks: Dict[str, 'StackConfig'] = field(default_factory=dict)  # stack_id -> StackConfig


@dataclass
class ValidationError:
    """Represents a validation error."""
    field_path: str
    message: str
    error_code: str
    severity: str  # ERROR, WARNING


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)


@dataclass
class ResourceMetadata:
    """Metadata about a deployed resource."""
    resource_id: str
    resource_type: str
    logical_name: str
    physical_name: str
    stack_name: str
    environment: str
    tags: Dict[str, str]
    outputs: Dict[str, str]
    dependencies: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class ResourceLink:
    """Represents a reference between resources."""
    source_resource: str
    target_resource: str
    link_type: str
    property_path: str


@dataclass
class ResourceNode:
    """Represents a node in the dependency graph."""
    resource_id: str
    resource_type: str
    dependencies: List[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    """Grafo de dependencias entre recursos."""
    nodes: Dict[str, ResourceNode] = field(default_factory=dict)
    edges: List[ResourceLink] = field(default_factory=list)


@dataclass
class Cycle:
    """Represents a circular dependency."""
    resources: List[str]


@dataclass
class LinkResolutionResult:
    """Result of link resolution."""
    success: bool
    resolved_links: Dict[str, str] = field(default_factory=dict)
    cycles: List[Cycle] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    error_message: str = ""


@dataclass
class RuleModification:
    """Represents a modification made by a deployment rule."""
    rule_name: str
    resource_id: str
    field_path: str
    old_value: Any
    new_value: Any
    reason: str


@dataclass
class RuleRejection:
    """Represents a rejection by a deployment rule."""
    rule_name: str
    resource_id: str
    reason: str
    severity: str


@dataclass
class RuleApplicationResult:
    """Result of applying deployment rules."""
    success: bool
    modifications: List['RuleModification'] = field(default_factory=list)
    rejections: List['RuleRejection'] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    """Result of CDK code generation."""
    success: bool
    generated_files: Dict[str, str] = field(default_factory=dict)  # path -> content
    errors: List[str] = field(default_factory=list)
