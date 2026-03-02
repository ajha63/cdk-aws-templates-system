"""EC2 Template for generating CDK code for EC2 instances."""

from typing import Dict, Any
from cdk_templates.templates.base import ResourceTemplate, GenerationContext


class EC2Template(ResourceTemplate):
    """Template for generating AWS EC2 instance infrastructure with CDK."""
    
    def generate_code(self, resource_config: Dict[str, Any], context: GenerationContext) -> str:
        """
        Generate CDK Python code for EC2 instance with IAM role, security group, and EBS volumes.
        
        Args:
            resource_config: EC2 configuration with properties like instance_type, ami_id, etc.
            context: Generation context with naming and tagging services
            
        Returns:
            CDK Python code as a string
        """
        logical_id = resource_config.get('logical_id', 'ec2-instance')
        properties = resource_config.get('properties', {})
        
        # Extract configuration
        instance_type = properties.get('instance_type', 't3.medium')
        ami_id = properties.get('ami_id', '')
        vpc_ref = properties.get('vpc_ref', '')
        subnet_ref = properties.get('subnet_ref', '')
        enable_session_manager = properties.get('enable_session_manager', True)
        enable_detailed_monitoring = properties.get('enable_detailed_monitoring', False)
        user_data_script = properties.get('user_data_script', '')
        root_volume = properties.get('root_volume', {})
        
        # Root volume configuration
        volume_size = root_volume.get('size', 30)
        volume_encrypted = root_volume.get('encrypted', True)
        volume_type = root_volume.get('volume_type', 'gp3')
        
        # Generate resource name using naming service
        instance_name = context.naming_service.generate_name(
            resource_type='ec2',
            purpose=logical_id,
            environment=context.environment,
            region=context.region
        )
        
        # Get tags from tagging service
        from cdk_templates.models import ResourceConfig
        resource_obj = ResourceConfig(
            logical_id=logical_id,
            resource_type='ec2',
            properties=properties,
            tags=resource_config.get('tags', {})
        )
        tags = context.tagging_service.apply_tags(resource_obj, context.environment)
        
        # Build the CDK code
        code_lines = []
        
        # Add comment header
        code_lines.append(f"# EC2 Instance: {instance_name}")
        code_lines.append(f"# Instance Type: {instance_type}, Session Manager: {enable_session_manager}")
        code_lines.append("")
        
        # Resolve VPC reference
        vpc_var = self._resolve_reference(vpc_ref, context)
        
        # Create IAM role for EC2 instance
        role_name = f"{instance_name}-role"
        code_lines.append(f"# IAM Role for EC2 instance")
        code_lines.append(f"{logical_id.replace('-', '_')}_role = iam.Role(")
        code_lines.append(f"    self, '{logical_id}-role',")
        code_lines.append(f"    role_name='{role_name}',")
        code_lines.append(f"    assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),")
        code_lines.append(f"    description='IAM role for {instance_name}'")
        code_lines.append(")")
        code_lines.append("")
        
        # Add Session Manager policy if enabled
        if enable_session_manager:
            code_lines.append("# Add AmazonSSMManagedInstanceCore policy for Session Manager")
            code_lines.append(f"{logical_id.replace('-', '_')}_role.add_managed_policy(")
            code_lines.append("    iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore')")
            code_lines.append(")")
            code_lines.append("")
        
        # Create security group
        sg_name = f"{instance_name}-sg"
        code_lines.append(f"# Security Group for EC2 instance")
        code_lines.append(f"{logical_id.replace('-', '_')}_sg = ec2.SecurityGroup(")
        code_lines.append(f"    self, '{logical_id}-sg',")
        code_lines.append(f"    vpc={vpc_var},")
        code_lines.append(f"    security_group_name='{sg_name}',")
        code_lines.append(f"    description='Security group for {instance_name}',")
        code_lines.append(f"    allow_all_outbound=True")
        code_lines.append(")")
        code_lines.append("")
        
        # Add comment about Session Manager not requiring SSH
        if enable_session_manager:
            code_lines.append("# Session Manager enabled - no SSH port required")
            code_lines.append("")
        
        # Prepare user data
        user_data_lines = []
        if user_data_script:
            user_data_lines.append("# User data script")
            code_lines.append(f"{logical_id.replace('-', '_')}_user_data = ec2.UserData.for_linux()")
            
            # Add SSM agent installation if Session Manager is enabled
            if enable_session_manager:
                code_lines.append(f"{logical_id.replace('-', '_')}_user_data.add_commands(")
                code_lines.append("    '# Install and configure SSM Agent',")
                code_lines.append("    'yum install -y amazon-ssm-agent',")
                code_lines.append("    'systemctl enable amazon-ssm-agent',")
                code_lines.append("    'systemctl start amazon-ssm-agent'")
                code_lines.append(")")
            
            # Add custom user data
            code_lines.append(f"{logical_id.replace('-', '_')}_user_data.add_commands(")
            for line in user_data_script.strip().split('\n'):
                if line.strip() and not line.strip().startswith('#!'):
                    code_lines.append(f"    {repr(line)},")
            code_lines.append(")")
            code_lines.append("")
        elif enable_session_manager:
            # Only SSM agent installation
            code_lines.append("# User data for SSM Agent installation")
            code_lines.append(f"{logical_id.replace('-', '_')}_user_data = ec2.UserData.for_linux()")
            code_lines.append(f"{logical_id.replace('-', '_')}_user_data.add_commands(")
            code_lines.append("    '# Install and configure SSM Agent',")
            code_lines.append("    'yum install -y amazon-ssm-agent',")
            code_lines.append("    'systemctl enable amazon-ssm-agent',")
            code_lines.append("    'systemctl start amazon-ssm-agent'")
            code_lines.append(")")
            code_lines.append("")
        
        # Resolve subnet reference
        subnet_selection = self._resolve_subnet_reference(subnet_ref, vpc_var, context)
        
        # Create EC2 instance
        code_lines.append(f"# EC2 Instance")
        code_lines.append(f"{logical_id.replace('-', '_')} = ec2.Instance(")
        code_lines.append(f"    self, '{logical_id}',")
        code_lines.append(f"    instance_name='{instance_name}',")
        code_lines.append(f"    instance_type=ec2.InstanceType('{instance_type}'),")
        
        # Machine image
        if ami_id:
            if ami_id.startswith('${ssm:'):
                # SSM parameter reference
                ssm_param = ami_id.replace('${ssm:', '').rstrip('}')
                code_lines.append(f"    machine_image=ec2.MachineImage.from_ssm_parameter('{ssm_param}'),")
            else:
                code_lines.append(f"    machine_image=ec2.MachineImage.generic_linux({{")
                code_lines.append(f"        '{context.region}': '{ami_id}'")
                code_lines.append(f"    }}),")
        else:
            code_lines.append(f"    machine_image=ec2.MachineImage.latest_amazon_linux2(),")
        
        code_lines.append(f"    vpc={vpc_var},")
        code_lines.append(f"    {subnet_selection},")
        code_lines.append(f"    role={logical_id.replace('-', '_')}_role,")
        code_lines.append(f"    security_group={logical_id.replace('-', '_')}_sg,")
        
        # User data
        if user_data_script or enable_session_manager:
            code_lines.append(f"    user_data={logical_id.replace('-', '_')}_user_data,")
        
        # Block device configuration
        code_lines.append(f"    block_devices=[")
        code_lines.append(f"        ec2.BlockDevice(")
        code_lines.append(f"            device_name='/dev/xvda',")
        code_lines.append(f"            volume=ec2.BlockDeviceVolume.ebs(")
        code_lines.append(f"                volume_size={volume_size},")
        code_lines.append(f"                volume_type=ec2.EbsDeviceVolumeType.{volume_type.upper()},")
        code_lines.append(f"                encrypted={volume_encrypted},")
        code_lines.append(f"                delete_on_termination=True")
        code_lines.append(f"            )")
        code_lines.append(f"        )")
        code_lines.append(f"    ]")
        
        # Detailed monitoring
        if enable_detailed_monitoring:
            code_lines.append(f")")
            code_lines.append("")
            code_lines.append(f"# Enable detailed monitoring")
            code_lines.append(f"cfn_instance = {logical_id.replace('-', '_')}.node.default_child")
            code_lines.append(f"cfn_instance.monitoring = True")
        else:
            code_lines.append(f")")
        
        code_lines.append("")
        
        # Apply tags
        code_lines.append(f"# Apply tags to EC2 instance")
        for tag_key, tag_value in tags.items():
            code_lines.append(f"cdk.Tags.of({logical_id.replace('-', '_')}).add('{tag_key}', '{tag_value}')")
        code_lines.append("")
        
        return '\n'.join(code_lines)
    
    def _resolve_reference(self, reference: str, context: GenerationContext) -> str:
        """
        Resolve a resource reference to a CDK variable name.
        
        Args:
            reference: Reference string like ${resource.vpc-main.id} or ${import.StackName-OutputName}
            context: Generation context with resolved links
            
        Returns:
            Variable name to use in generated code
        """
        if not reference:
            return "vpc"
        
        # Check if it's a cross-stack import reference
        if reference.startswith('${import.') and reference.endswith('}'):
            # Extract export name from ${import.StackName-OutputName}
            export_name = reference[9:-1]  # Remove ${import. and }
            return f"cdk.Fn.import_value('{export_name}')"
        
        # Check if it's a resource reference
        if reference.startswith('${resource.') and reference.endswith('}'):
            # Extract logical_id from ${resource.logical_id.property}
            parts = reference[11:-1].split('.')
            if len(parts) >= 1:
                logical_id = parts[0]
                return logical_id.replace('-', '_')
        
        # Check resolved links
        if reference in context.resolved_links:
            return context.resolved_links[reference]
        
        return reference
    
    def _resolve_subnet_reference(self, subnet_ref: str, vpc_var: str, context: GenerationContext) -> str:
        """
        Resolve subnet reference to CDK subnet selection.
        
        Args:
            subnet_ref: Subnet reference string
            vpc_var: VPC variable name
            context: Generation context
            
        Returns:
            Subnet selection code
        """
        if not subnet_ref:
            return "vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)"
        
        # Check if it's a specific subnet reference
        if 'private' in subnet_ref.lower():
            return "vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)"
        elif 'public' in subnet_ref.lower():
            return "vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)"
        else:
            return "vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)"
    
    def get_outputs(self, resource_config: Dict[str, Any]) -> Dict[str, str]:
        """
        Define EC2 instance outputs for cross-stack references.
        
        Args:
            resource_config: EC2 configuration
            
        Returns:
            Dictionary mapping output names to CDK value expressions
        """
        logical_id = resource_config.get('logical_id', 'ec2-instance')
        var_name = logical_id.replace('-', '_')
        
        return {
            'id': f"{var_name}.instance_id",
            'private_ip': f"{var_name}.instance_private_ip",
            'availability_zone': f"{var_name}.instance_availability_zone",
            'security_group_id': f"{var_name}_sg.security_group_id"
        }
