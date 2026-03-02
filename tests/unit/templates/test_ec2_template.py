"""Unit tests for EC2 Template."""

import pytest
from cdk_templates.templates.ec2_template import EC2Template
from cdk_templates.templates.base import GenerationContext
from cdk_templates.naming_service import NamingConventionService
from cdk_templates.tagging_service import TaggingStrategyService
from cdk_templates.resource_registry import ResourceRegistry


@pytest.fixture
def naming_service():
    """Create a naming service instance."""
    return NamingConventionService()


@pytest.fixture
def tagging_service():
    """Create a tagging service instance."""
    from cdk_templates.models import ConfigMetadata
    metadata = ConfigMetadata(
        project='test-project',
        owner='test-team',
        cost_center='engineering',
        description='Test project'
    )
    return TaggingStrategyService(metadata)


@pytest.fixture
def resource_registry(tmp_path):
    """Create a resource registry instance."""
    registry_file = tmp_path / "registry.json"
    return ResourceRegistry(str(registry_file))


@pytest.fixture
def generation_context(naming_service, tagging_service, resource_registry):
    """Create a generation context."""
    return GenerationContext(
        environment='dev',
        region='us-east-1',
        account_id='123456789012',
        naming_service=naming_service,
        tagging_service=tagging_service,
        resource_registry=resource_registry,
        resolved_links={}
    )


class TestEC2Template:
    """Test suite for EC2Template."""
    
    def test_generate_code_basic_configuration(self, generation_context):
        """Test EC2 template with basic configuration."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-web-01',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'subnet_ref': '${resource.vpc-main.private_subnet_1}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify basic structure
        assert 'ec2_web_01 = ec2.Instance(' in code
        assert "instance_type=ec2.InstanceType('t3.medium')" in code
        assert 'vpc=vpc_main' in code
        
        # Verify IAM role creation
        assert 'ec2_web_01_role = iam.Role(' in code
        assert "assumed_by=iam.ServicePrincipal('ec2.amazonaws.com')" in code
        
        # Verify security group creation
        assert 'ec2_web_01_sg = ec2.SecurityGroup(' in code
        
        # Verify encrypted EBS volume
        assert 'encrypted=True' in code
        assert 'volume_size=30' in code
        assert 'volume_type=ec2.EbsDeviceVolumeType.GP3' in code
    
    def test_generate_code_with_session_manager(self, generation_context):
        """Test EC2 template with Session Manager enabled."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-app',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.small',
                'vpc_ref': '${resource.vpc-main.id}',
                'enable_session_manager': True
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify Session Manager policy
        assert 'AmazonSSMManagedInstanceCore' in code
        assert 'add_managed_policy' in code
        
        # Verify SSM agent installation in user data
        assert 'amazon-ssm-agent' in code
        assert 'systemctl enable amazon-ssm-agent' in code
        assert 'systemctl start amazon-ssm-agent' in code
        
        # Verify comment about no SSH required
        assert 'Session Manager enabled' in code
    
    def test_generate_code_without_session_manager(self, generation_context):
        """Test EC2 template with Session Manager disabled."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-legacy',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.micro',
                'vpc_ref': '${resource.vpc-main.id}',
                'enable_session_manager': False
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify Session Manager policy is NOT added
        assert 'AmazonSSMManagedInstanceCore' not in code
    
    def test_generate_code_with_user_data(self, generation_context):
        """Test EC2 template with custom user data script."""
        template = EC2Template()
        
        user_data = """#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd"""
        
        resource_config = {
            'logical_id': 'ec2-web',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'user_data_script': user_data
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify user data is included
        assert 'ec2_web_user_data = ec2.UserData.for_linux()' in code
        assert 'yum update -y' in code
        assert 'yum install -y httpd' in code
        assert 'systemctl start httpd' in code
    
    def test_generate_code_with_detailed_monitoring(self, generation_context):
        """Test EC2 template with detailed monitoring enabled."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-monitored',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.large',
                'vpc_ref': '${resource.vpc-main.id}',
                'enable_detailed_monitoring': True
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify detailed monitoring configuration
        assert 'Enable detailed monitoring' in code
        assert 'cfn_instance = ec2_monitored.node.default_child' in code
        assert 'cfn_instance.monitoring = True' in code
    
    def test_generate_code_with_custom_root_volume(self, generation_context):
        """Test EC2 template with custom root volume configuration."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-storage',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'root_volume': {
                    'size': 100,
                    'encrypted': True,
                    'volume_type': 'gp3'
                }
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify root volume configuration
        assert 'volume_size=100' in code
        assert 'encrypted=True' in code
        assert 'volume_type=ec2.EbsDeviceVolumeType.GP3' in code
    
    def test_generate_code_with_ami_id(self, generation_context):
        """Test EC2 template with specific AMI ID."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-custom-ami',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.medium',
                'ami_id': 'ami-12345678',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify AMI configuration
        assert 'ami-12345678' in code
        assert 'ec2.MachineImage.generic_linux' in code
    
    def test_generate_code_with_ssm_parameter_ami(self, generation_context):
        """Test EC2 template with SSM parameter for AMI."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-ssm-ami',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.medium',
                'ami_id': '${ssm:/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2}',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify SSM parameter usage
        assert 'ec2.MachineImage.from_ssm_parameter' in code
        assert '/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2' in code
    
    def test_generate_code_with_public_subnet(self, generation_context):
        """Test EC2 template with public subnet."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-public',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.micro',
                'vpc_ref': '${resource.vpc-main.id}',
                'subnet_ref': '${resource.vpc-main.public_subnet_1}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify public subnet selection
        assert 'subnet_type=ec2.SubnetType.PUBLIC' in code
    
    def test_generate_code_with_private_subnet(self, generation_context):
        """Test EC2 template with private subnet."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-private',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.micro',
                'vpc_ref': '${resource.vpc-main.id}',
                'subnet_ref': '${resource.vpc-main.private_subnet_1}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify private subnet selection
        assert 'subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS' in code
    
    def test_generate_code_applies_tags(self, generation_context):
        """Test that EC2 template applies tags correctly."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-tagged',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.micro',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {'CustomTag': 'CustomValue'}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify tags are applied
        assert 'cdk.Tags.of(ec2_tagged).add' in code
        assert 'Environment' in code
        assert 'ManagedBy' in code
    
    def test_get_outputs(self):
        """Test EC2 template outputs."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-web-01',
            'resource_type': 'ec2',
            'properties': {}
        }
        
        outputs = template.get_outputs(resource_config)
        
        # Verify outputs
        assert 'id' in outputs
        assert 'private_ip' in outputs
        assert 'availability_zone' in outputs
        assert 'security_group_id' in outputs
        
        # Verify output values reference the correct variable
        assert 'ec2_web_01.instance_id' in outputs['id']
        assert 'ec2_web_01.instance_private_ip' in outputs['private_ip']
    
    def test_resolve_reference(self, generation_context):
        """Test reference resolution."""
        template = EC2Template()
        
        # Test resource reference
        ref = '${resource.vpc-main.id}'
        resolved = template._resolve_reference(ref, generation_context)
        assert resolved == 'vpc_main'
        
        # Test empty reference
        ref = ''
        resolved = template._resolve_reference(ref, generation_context)
        assert resolved == 'vpc'
    
    def test_resolve_subnet_reference(self, generation_context):
        """Test subnet reference resolution."""
        template = EC2Template()
        
        # Test private subnet
        ref = '${resource.vpc-main.private_subnet_1}'
        resolved = template._resolve_subnet_reference(ref, 'vpc_main', generation_context)
        assert 'PRIVATE_WITH_EGRESS' in resolved
        
        # Test public subnet
        ref = '${resource.vpc-main.public_subnet_1}'
        resolved = template._resolve_subnet_reference(ref, 'vpc_main', generation_context)
        assert 'PUBLIC' in resolved
        
        # Test empty reference (defaults to private)
        ref = ''
        resolved = template._resolve_subnet_reference(ref, 'vpc_main', generation_context)
        assert 'PRIVATE_WITH_EGRESS' in resolved
    
    def test_generate_code_complete_configuration(self, generation_context):
        """Test EC2 template with all configuration options."""
        template = EC2Template()
        
        resource_config = {
            'logical_id': 'ec2-complete',
            'resource_type': 'ec2',
            'properties': {
                'instance_type': 't3.xlarge',
                'ami_id': 'ami-abcdef12',
                'vpc_ref': '${resource.vpc-main.id}',
                'subnet_ref': '${resource.vpc-main.private_subnet_1}',
                'enable_session_manager': True,
                'enable_detailed_monitoring': True,
                'user_data_script': 'echo "Hello World"',
                'root_volume': {
                    'size': 50,
                    'encrypted': True,
                    'volume_type': 'gp3'
                }
            },
            'tags': {'Application': 'WebServer'}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify all components are present
        assert 'ec2_complete = ec2.Instance(' in code
        assert 't3.xlarge' in code
        assert 'ami-abcdef12' in code
        assert 'AmazonSSMManagedInstanceCore' in code
        assert 'cfn_instance.monitoring = True' in code
        assert 'echo "Hello World"' in code
        assert 'volume_size=50' in code
        assert 'encrypted=True' in code
