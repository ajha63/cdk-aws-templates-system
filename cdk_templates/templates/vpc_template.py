"""VPC Template for generating CDK code for VPC resources."""

from typing import Dict, Any
from cdk_templates.templates.base import ResourceTemplate, GenerationContext


class VPCTemplate(ResourceTemplate):
    """Template for generating AWS VPC infrastructure with CDK."""
    
    def generate_code(self, resource_config: Dict[str, Any], context: GenerationContext) -> str:
        """
        Generate CDK Python code for VPC with subnets, NAT gateways, and flow logs.
        
        Args:
            resource_config: VPC configuration with properties like cidr, availability_zones, etc.
            context: Generation context with naming and tagging services
            
        Returns:
            CDK Python code as a string
        """
        logical_id = resource_config.get('logical_id', 'vpc-main')
        properties = resource_config.get('properties', {})
        
        # Extract configuration
        cidr = properties.get('cidr', '10.0.0.0/16')
        availability_zones = properties.get('availability_zones', 3)
        enable_dns_hostnames = properties.get('enable_dns_hostnames', True)
        enable_dns_support = properties.get('enable_dns_support', True)
        enable_flow_logs = properties.get('enable_flow_logs', True)
        nat_gateways = properties.get('nat_gateways', 1)
        
        # Generate resource name using naming service
        vpc_name = context.naming_service.generate_name(
            resource_type='vpc',
            purpose=logical_id,
            environment=context.environment,
            region=context.region
        )
        
        # Get tags from tagging service
        from cdk_templates.models import ResourceConfig
        resource_obj = ResourceConfig(
            logical_id=logical_id,
            resource_type='vpc',
            properties=properties,
            tags=resource_config.get('tags', {})
        )
        tags = context.tagging_service.apply_tags(resource_obj, context.environment)
        
        # Build the CDK code
        code_lines = []
        
        # Add comment header
        code_lines.append(f"# VPC: {vpc_name}")
        code_lines.append(f"# CIDR: {cidr}, AZs: {availability_zones}, NAT Gateways: {nat_gateways}")
        code_lines.append("")
        
        # Create VPC with subnet configuration
        code_lines.append(f"{logical_id.replace('-', '_')} = ec2.Vpc(")
        code_lines.append(f"    self, '{logical_id}',")
        code_lines.append(f"    vpc_name='{vpc_name}',")
        code_lines.append(f"    ip_addresses=ec2.IpAddresses.cidr('{cidr}'),")
        code_lines.append(f"    max_azs={availability_zones},")
        code_lines.append(f"    enable_dns_hostnames={enable_dns_hostnames},")
        code_lines.append(f"    enable_dns_support={enable_dns_support},")
        code_lines.append(f"    nat_gateways={nat_gateways},")
        code_lines.append("    subnet_configuration=[")
        
        # Public subnets
        code_lines.append("        ec2.SubnetConfiguration(")
        code_lines.append("            name='Public',")
        code_lines.append("            subnet_type=ec2.SubnetType.PUBLIC,")
        code_lines.append("            cidr_mask=24")
        code_lines.append("        ),")
        
        # Private subnets with egress (NAT)
        code_lines.append("        ec2.SubnetConfiguration(")
        code_lines.append("            name='Private',")
        code_lines.append("            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,")
        code_lines.append("            cidr_mask=24")
        code_lines.append("        )")
        code_lines.append("    ]")
        code_lines.append(")")
        code_lines.append("")
        
        # Apply tags
        code_lines.append(f"# Apply tags to VPC")
        for tag_key, tag_value in tags.items():
            code_lines.append(f"cdk.Tags.of({logical_id.replace('-', '_')}).add('{tag_key}', '{tag_value}')")
        code_lines.append("")
        
        # Add VPC Flow Logs if enabled
        if enable_flow_logs:
            code_lines.append("# VPC Flow Logs")
            log_group_name = f"{vpc_name}-flow-logs"
            code_lines.append(f"flow_log_group = logs.LogGroup(")
            code_lines.append(f"    self, '{logical_id}-flow-logs',")
            code_lines.append(f"    log_group_name='/aws/vpc/{log_group_name}',")
            code_lines.append(f"    retention=logs.RetentionDays.ONE_MONTH,")
            code_lines.append(f"    removal_policy=cdk.RemovalPolicy.DESTROY")
            code_lines.append(")")
            code_lines.append("")
            code_lines.append(f"flow_log = ec2.FlowLog(")
            code_lines.append(f"    self, '{logical_id}-flow-log',")
            code_lines.append(f"    resource_type=ec2.FlowLogResourceType.from_vpc({logical_id.replace('-', '_')}),")
            code_lines.append(f"    destination=ec2.FlowLogDestination.to_cloud_watch_logs(flow_log_group)")
            code_lines.append(")")
            code_lines.append("")
        
        return '\n'.join(code_lines)
    
    def get_outputs(self, resource_config: Dict[str, Any]) -> Dict[str, str]:
        """
        Define VPC outputs for cross-stack references.
        
        Args:
            resource_config: VPC configuration
            
        Returns:
            Dictionary mapping output names to CDK value expressions
        """
        logical_id = resource_config.get('logical_id', 'vpc-main')
        var_name = logical_id.replace('-', '_')
        
        return {
            'id': f"{var_name}.vpc_id",
            'public_subnets': f"','.join([subnet.subnet_id for subnet in {var_name}.public_subnets])",
            'private_subnets': f"','.join([subnet.subnet_id for subnet in {var_name}.private_subnets])",
            'availability_zones': f"','.join({var_name}.availability_zones)"
        }
