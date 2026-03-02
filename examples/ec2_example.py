"""Example demonstrating EC2 template usage."""

from cdk_templates.templates.ec2_template import EC2Template
from cdk_templates.templates.base import GenerationContext
from cdk_templates.naming_service import NamingConventionService
from cdk_templates.tagging_service import TaggingStrategyService
from cdk_templates.resource_registry import ResourceRegistry
from cdk_templates.models import ConfigMetadata


def main():
    """Generate EC2 instance CDK code example."""
    
    # Setup services
    metadata = ConfigMetadata(
        project='my-web-app',
        owner='platform-team',
        cost_center='engineering',
        description='Web application infrastructure'
    )
    
    naming_service = NamingConventionService()
    tagging_service = TaggingStrategyService(metadata)
    resource_registry = ResourceRegistry()
    
    # Create generation context
    context = GenerationContext(
        environment='production',
        region='us-east-1',
        account_id='123456789012',
        naming_service=naming_service,
        tagging_service=tagging_service,
        resource_registry=resource_registry,
        resolved_links={}
    )
    
    # Define EC2 configuration
    ec2_config = {
        'logical_id': 'ec2-web-server',
        'resource_type': 'ec2',
        'properties': {
            'instance_type': 't3.medium',
            'ami_id': '${ssm:/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2}',
            'vpc_ref': '${resource.vpc-main.id}',
            'subnet_ref': '${resource.vpc-main.private_subnet_1}',
            'enable_session_manager': True,
            'enable_detailed_monitoring': True,
            'user_data_script': '''#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello from EC2!</h1>" > /var/www/html/index.html''',
            'root_volume': {
                'size': 50,
                'encrypted': True,
                'volume_type': 'gp3'
            }
        },
        'tags': {
            'Application': 'WebServer',
            'Tier': 'Frontend'
        }
    }
    
    # Generate CDK code
    template = EC2Template()
    cdk_code = template.generate_code(ec2_config, context)
    
    print("=" * 80)
    print("Generated CDK Python Code for EC2 Instance")
    print("=" * 80)
    print()
    print(cdk_code)
    print()
    print("=" * 80)
    print("Outputs:")
    print("=" * 80)
    outputs = template.get_outputs(ec2_config)
    for output_name, output_desc in outputs.items():
        print(f"  {output_name}: {output_desc}")
    print()


if __name__ == '__main__':
    main()
