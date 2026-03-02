"""Unit tests for VPC Template."""

import pytest
from cdk_templates.templates.vpc_template import VPCTemplate
from cdk_templates.templates.base import GenerationContext
from cdk_templates.naming_service import NamingConventionService
from cdk_templates.tagging_service import TaggingStrategyService
from cdk_templates.resource_registry import ResourceRegistry
from cdk_templates.models import ConfigMetadata


@pytest.fixture
def metadata():
    """Create test metadata."""
    return ConfigMetadata(
        project='test-project',
        owner='test-team',
        cost_center='engineering',
        description='Test infrastructure'
    )


@pytest.fixture
def context(metadata, tmp_path):
    """Create test generation context."""
    registry_file = tmp_path / "registry.json"
    return GenerationContext(
        environment='dev',
        region='us-east-1',
        account_id='123456789012',
        naming_service=NamingConventionService(),
        tagging_service=TaggingStrategyService(metadata),
        resource_registry=ResourceRegistry(str(registry_file)),
        resolved_links={}
    )


def test_vpc_template_basic_configuration(context):
    """Test VPC template with basic configuration."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-main',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '10.0.0.0/16',
            'availability_zones': 3,
            'enable_dns_hostnames': True,
            'enable_dns_support': True,
            'enable_flow_logs': True,
            'nat_gateways': 3
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify VPC creation
    assert 'ec2.Vpc(' in code
    assert '10.0.0.0/16' in code
    assert 'max_azs=3' in code
    assert 'nat_gateways=3' in code
    
    # Verify DNS settings
    assert 'enable_dns_hostnames=True' in code
    assert 'enable_dns_support=True' in code
    
    # Verify subnet configuration
    assert 'subnet_configuration=' in code
    assert "name='Public'" in code
    assert 'subnet_type=ec2.SubnetType.PUBLIC' in code
    assert "name='Private'" in code
    assert 'subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS' in code
    
    # Verify Flow Logs
    assert 'flow_log_group = logs.LogGroup(' in code
    assert 'flow_log = ec2.FlowLog(' in code


def test_vpc_template_without_flow_logs(context):
    """Test VPC template with flow logs disabled."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-test',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '172.16.0.0/16',
            'availability_zones': 2,
            'enable_flow_logs': False,
            'nat_gateways': 1
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify VPC creation
    assert 'ec2.Vpc(' in code
    assert '172.16.0.0/16' in code
    assert 'max_azs=2' in code
    assert 'nat_gateways=1' in code
    
    # Verify Flow Logs are NOT present
    assert 'flow_log_group' not in code
    assert 'FlowLog(' not in code


def test_vpc_template_naming_convention(context):
    """Test that VPC template uses naming service correctly."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-main',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '10.0.0.0/16'
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify naming convention is applied
    # Pattern: {env}-{service}-{purpose}-{region}
    assert 'dev-app-vpc-main-us-east-1' in code


def test_vpc_template_tagging(context):
    """Test that VPC template applies tags correctly."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-main',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '10.0.0.0/16'
        },
        'tags': {
            'CustomTag': 'CustomValue'
        }
    }
    
    code = template.generate_code(config, context)
    
    # Verify mandatory tags are applied
    assert "cdk.Tags.of(vpc_main).add('Environment', 'dev')" in code
    assert "cdk.Tags.of(vpc_main).add('Project', 'test-project')" in code
    assert "cdk.Tags.of(vpc_main).add('Owner', 'test-team')" in code
    assert "cdk.Tags.of(vpc_main).add('CostCenter', 'engineering')" in code
    assert "cdk.Tags.of(vpc_main).add('ManagedBy', 'cdk-template-system')" in code
    
    # Verify custom tag is applied
    assert "cdk.Tags.of(vpc_main).add('CustomTag', 'CustomValue')" in code


def test_vpc_template_high_availability(context):
    """Test VPC template with high availability configuration (3+ AZs)."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-ha',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '10.0.0.0/16',
            'availability_zones': 4,
            'nat_gateways': 4
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify high availability settings
    assert 'max_azs=4' in code
    assert 'nat_gateways=4' in code


def test_vpc_template_get_outputs():
    """Test VPC template output definitions."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-main',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '10.0.0.0/16'
        }
    }
    
    outputs = template.get_outputs(config)
    
    # Verify expected outputs
    assert 'id' in outputs
    assert 'public_subnets' in outputs
    assert 'private_subnets' in outputs
    assert 'availability_zones' in outputs
    
    # Verify output values reference the correct variable
    assert 'vpc_main.vpc_id' in outputs['id']
    assert 'vpc_main.public_subnets' in outputs['public_subnets']


def test_vpc_template_default_values(context):
    """Test VPC template with minimal configuration using defaults."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-minimal',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '192.168.0.0/16'
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify defaults are applied
    assert '192.168.0.0/16' in code
    assert 'max_azs=3' in code  # default
    assert 'nat_gateways=1' in code  # default
    assert 'enable_dns_hostnames=True' in code  # default
    assert 'enable_dns_support=True' in code  # default
    assert 'flow_log_group' in code  # flow logs enabled by default


def test_vpc_template_variable_substitution(context):
    """Test that logical_id with hyphens is converted to valid Python variable names."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-my-app',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '10.0.0.0/16'
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify hyphenated logical_id is converted to underscores for Python variable
    assert 'vpc_my_app = ec2.Vpc(' in code
    assert "self, 'vpc-my-app'," in code  # CDK construct ID keeps hyphens
    assert 'cdk.Tags.of(vpc_my_app)' in code


def test_vpc_template_minimum_azs(context):
    """Test VPC template with minimum 2 availability zones."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-min',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '10.0.0.0/16',
            'availability_zones': 2,
            'nat_gateways': 2
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify minimum AZ configuration
    assert 'max_azs=2' in code
    assert 'nat_gateways=2' in code
    
    # Verify subnets are configured
    assert 'subnet_configuration=' in code
    assert "name='Public'" in code
    assert "name='Private'" in code


def test_vpc_template_three_plus_azs_for_ha(context):
    """Test VPC template with 3+ AZs for high availability."""
    template = VPCTemplate()
    
    config = {
        'logical_id': 'vpc-ha-prod',
        'resource_type': 'vpc',
        'properties': {
            'cidr': '10.0.0.0/16',
            'availability_zones': 3,
            'nat_gateways': 3
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify HA configuration with 3+ AZs
    assert 'max_azs=3' in code
    assert 'nat_gateways=3' in code
