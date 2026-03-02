"""Unit tests for cross-stack reference resolution."""

import pytest
from cdk_templates.template_generator import TemplateGenerator
from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
    StackConfig
)
from cdk_templates.templates.base import GenerationContext
from cdk_templates.naming_service import NamingConventionService
from cdk_templates.tagging_service import TaggingStrategyService
from cdk_templates.resource_registry import ResourceRegistry


class TestCrossStackReferences:
    """Test cross-stack reference resolution functionality."""
    
    def test_extract_cross_stack_references(self):
        """Test that cross-stack references are correctly extracted from resource properties."""
        resolver = ResourceLinkResolver()
        
        resource = ResourceConfig(
            logical_id="ec2-web",
            resource_type="ec2",
            properties={
                "vpc_ref": "${stack.vpc-stack.id}",
                "subnet_ref": "${stack.vpc-stack.private_subnet}",
                "instance_type": "t3.medium"
            }
        )
        
        references = resolver.extract_cross_stack_references(resource)
        
        assert len(references) == 2
        assert references[0]['stack_id'] == 'vpc-stack'
        assert references[0]['output_name'] == 'id'
        assert references[1]['stack_id'] == 'vpc-stack'
        assert references[1]['output_name'] == 'private_subnet'
    
    def test_resolve_cross_stack_reference(self):
        """Test that cross-stack references are resolved to Fn.importValue calls."""
        generator = TemplateGenerator()
        
        context = GenerationContext(
            environment="dev",
            region="us-east-1",
            account_id="123456789012",
            naming_service=NamingConventionService(),
            tagging_service=TaggingStrategyService(ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="test"
            )),
            resource_registry=ResourceRegistry(),
            resolved_links={}
        )
        
        reference = "${stack.vpc-stack.id}"
        resolved = generator.resolve_cross_stack_reference(reference, context)
        
        assert resolved == "cdk.Fn.import_value('dev-vpc-stack-id')"
    
    def test_cross_stack_reference_pattern(self):
        """Test that the cross-stack reference pattern matches correctly."""
        resolver = ResourceLinkResolver()
        
        # Valid patterns
        assert resolver.CROSS_STACK_PATTERN.match("${stack.vpc-stack.id}")
        assert resolver.CROSS_STACK_PATTERN.match("${stack.network-stack.subnet_id}")
        
        # Invalid patterns
        assert not resolver.CROSS_STACK_PATTERN.match("${resource.vpc-main.id}")
        assert not resolver.CROSS_STACK_PATTERN.match("${stack.VPC-Stack.id}")  # uppercase not allowed
        assert not resolver.CROSS_STACK_PATTERN.match("stack.vpc-stack.id")  # missing ${}
    
    def test_nested_cross_stack_references(self):
        """Test extraction of cross-stack references from nested structures."""
        resolver = ResourceLinkResolver()
        
        resource = ResourceConfig(
            logical_id="rds-main",
            resource_type="rds",
            properties={
                "vpc_ref": "${stack.vpc-stack.id}",
                "subnet_refs": [
                    "${stack.vpc-stack.private_subnet_1}",
                    "${stack.vpc-stack.private_subnet_2}"
                ],
                "security_group": {
                    "ingress": {
                        "source_sg": "${stack.app-stack.security_group_id}"
                    }
                }
            }
        )
        
        references = resolver.extract_cross_stack_references(resource)
        
        assert len(references) == 4
        stack_ids = [ref['stack_id'] for ref in references]
        assert stack_ids.count('vpc-stack') == 3
        assert stack_ids.count('app-stack') == 1
    
    def test_no_cross_stack_references(self):
        """Test that resources without cross-stack references return empty list."""
        resolver = ResourceLinkResolver()
        
        resource = ResourceConfig(
            logical_id="vpc-main",
            resource_type="vpc",
            properties={
                "cidr": "10.0.0.0/16",
                "availability_zones": 3
            }
        )
        
        references = resolver.extract_cross_stack_references(resource)
        
        assert len(references) == 0
    
    def test_mixed_references(self):
        """Test that both resource and cross-stack references can coexist."""
        resolver = ResourceLinkResolver()
        
        resource = ResourceConfig(
            logical_id="ec2-web",
            resource_type="ec2",
            properties={
                "vpc_ref": "${resource.vpc-main.id}",  # Same-stack reference
                "subnet_ref": "${stack.network-stack.subnet_id}",  # Cross-stack reference
                "instance_type": "t3.medium"
            }
        )
        
        # Extract resource references
        resource_refs = resolver._extract_references(resource)
        assert len(resource_refs) == 1
        assert resource_refs[0]['target_resource'] == 'vpc-main'
        
        # Extract cross-stack references
        cross_stack_refs = resolver.extract_cross_stack_references(resource)
        assert len(cross_stack_refs) == 1
        assert cross_stack_refs[0]['stack_id'] == 'network-stack'
