"""S3 Template for generating CDK code for S3 buckets."""

from typing import Dict, Any, List
from cdk_templates.templates.base import ResourceTemplate, GenerationContext


class S3Template(ResourceTemplate):
    """Template for generating AWS S3 bucket infrastructure with CDK."""
    
    def generate_code(self, resource_config: Dict[str, Any], context: GenerationContext) -> str:
        """
        Generate CDK Python code for S3 bucket with versioning, encryption, and lifecycle rules.
        
        Args:
            resource_config: S3 configuration with properties like versioning_enabled, encryption, etc.
            context: Generation context with naming and tagging services
            
        Returns:
            CDK Python code as a string
        """
        logical_id = resource_config.get('logical_id', 's3-bucket')
        properties = resource_config.get('properties', {})
        
        # Extract configuration
        versioning_enabled = properties.get('versioning_enabled', True)
        encryption = properties.get('encryption', 'aws:kms')
        kms_key_ref = properties.get('kms_key_ref', '')
        block_public_access = properties.get('block_public_access', True)
        lifecycle_rules = properties.get('lifecycle_rules', [])
        access_logging = properties.get('access_logging', {})
        
        # Generate resource name using naming service
        bucket_name = context.naming_service.generate_name(
            resource_type='s3',
            purpose=logical_id,
            environment=context.environment,
            region=context.region
        )
        
        # Get tags from tagging service
        from cdk_templates.models import ResourceConfig
        resource_obj = ResourceConfig(
            logical_id=logical_id,
            resource_type='s3',
            properties=properties,
            tags=resource_config.get('tags', {})
        )
        tags = context.tagging_service.apply_tags(resource_obj, context.environment)
        
        # Build the CDK code
        code_lines = []
        
        # Add comment header
        code_lines.append(f"# S3 Bucket: {bucket_name}")
        code_lines.append(f"# Versioning: {versioning_enabled}, Encryption: {encryption}, Block Public Access: {block_public_access}")
        code_lines.append("")
        
        # Create S3 bucket
        code_lines.append(f"{logical_id.replace('-', '_')} = s3.Bucket(")
        code_lines.append(f"    self, '{logical_id}',")
        code_lines.append(f"    bucket_name='{bucket_name}',")
        
        # Versioning
        if versioning_enabled:
            code_lines.append(f"    versioned=True,")
        else:
            code_lines.append(f"    versioned=False,")
        
        # Encryption configuration
        code_lines.extend(self._generate_encryption_config(encryption, kms_key_ref, logical_id, context))
        
        # Block public access
        if block_public_access:
            code_lines.append(f"    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,")
        
        # Access logging
        if access_logging.get('enabled', False):
            code_lines.extend(self._generate_access_logging_config(access_logging, logical_id, context))
        
        # Lifecycle rules
        if lifecycle_rules:
            code_lines.extend(self._generate_lifecycle_rules(lifecycle_rules))
        
        # Removal policy
        code_lines.append(f"    removal_policy=cdk.RemovalPolicy.RETAIN,")
        code_lines.append(f"    auto_delete_objects=False")
        code_lines.append(")")
        code_lines.append("")
        
        # Bucket policy with least privilege
        code_lines.extend(self._generate_bucket_policy(logical_id, properties))
        
        # Apply tags
        code_lines.append(f"# Apply tags to S3 bucket")
        for tag_key, tag_value in tags.items():
            code_lines.append(f"cdk.Tags.of({logical_id.replace('-', '_')}).add('{tag_key}', '{tag_value}')")
        code_lines.append("")
        
        return '\n'.join(code_lines)
    
    def _generate_encryption_config(self, encryption: str, kms_key_ref: str, 
                                   logical_id: str, context: GenerationContext) -> List[str]:
        """
        Generate encryption configuration for S3 bucket.
        
        Args:
            encryption: Encryption type ('aws:kms' or 'AES256')
            kms_key_ref: Reference to KMS key if using KMS encryption
            logical_id: Logical ID of the bucket
            context: Generation context
            
        Returns:
            List of code lines for encryption configuration
        """
        lines = []
        
        if encryption == 'aws:kms':
            if kms_key_ref:
                # Use referenced KMS key
                kms_var = self._resolve_reference(kms_key_ref, context)
                lines.append(f"    encryption=s3.BucketEncryption.KMS,")
                lines.append(f"    encryption_key={kms_var},")
            else:
                # Use AWS managed KMS key
                lines.append(f"    encryption=s3.BucketEncryption.KMS_MANAGED,")
        else:
            # Use SSE-S3 encryption
            lines.append(f"    encryption=s3.BucketEncryption.S3_MANAGED,")
        
        return lines
    
    def _generate_lifecycle_rules(self, lifecycle_rules: List[Dict[str, Any]]) -> List[str]:
        """
        Generate lifecycle rules configuration.
        
        Args:
            lifecycle_rules: List of lifecycle rule configurations
            
        Returns:
            List of code lines for lifecycle rules
        """
        lines = []
        lines.append(f"    lifecycle_rules=[")
        
        for rule in lifecycle_rules:
            rule_id = rule.get('id', 'rule')
            enabled = rule.get('enabled', True)
            transitions = rule.get('transitions', [])
            expiration_days = rule.get('expiration_days')
            
            lines.append(f"        s3.LifecycleRule(")
            lines.append(f"            id='{rule_id}',")
            lines.append(f"            enabled={enabled},")
            
            # Transitions
            if transitions:
                lines.append(f"            transitions=[")
                for transition in transitions:
                    storage_class = transition.get('storage_class', 'STANDARD_IA')
                    days = transition.get('days', 30)
                    lines.append(f"                s3.Transition(")
                    lines.append(f"                    storage_class=s3.StorageClass.{storage_class},")
                    lines.append(f"                    transition_after=cdk.Duration.days({days})")
                    lines.append(f"                ),")
                lines.append(f"            ],")
            
            # Expiration
            if expiration_days:
                lines.append(f"            expiration=cdk.Duration.days({expiration_days})")
            
            lines.append(f"        ),")
        
        lines.append(f"    ],")
        return lines
    
    def _generate_access_logging_config(self, access_logging: Dict[str, Any], 
                                       logical_id: str, context: GenerationContext) -> List[str]:
        """
        Generate access logging configuration.
        
        Args:
            access_logging: Access logging configuration
            logical_id: Logical ID of the bucket
            context: Generation context
            
        Returns:
            List of code lines for access logging
        """
        lines = []
        
        target_bucket_ref = access_logging.get('target_bucket_ref', '')
        prefix = access_logging.get('prefix', 'access-logs/')
        
        if target_bucket_ref:
            target_bucket_var = self._resolve_reference(target_bucket_ref, context)
            lines.append(f"    server_access_logs_bucket={target_bucket_var},")
            lines.append(f"    server_access_logs_prefix='{prefix}',")
        
        return lines
    
    def _generate_bucket_policy(self, logical_id: str, properties: Dict[str, Any]) -> List[str]:
        """
        Generate bucket policy with least privilege principle.
        
        Args:
            logical_id: Logical ID of the bucket
            properties: Bucket properties
            
        Returns:
            List of code lines for bucket policy
        """
        lines = []
        
        # Add comment about bucket policy
        lines.append(f"# Bucket policy with least privilege")
        lines.append(f"# Configure specific access policies based on your requirements")
        lines.append(f"# Example: Deny insecure transport")
        lines.append(f"{logical_id.replace('-', '_')}.add_to_resource_policy(")
        lines.append(f"    iam.PolicyStatement(")
        lines.append(f"        sid='DenyInsecureTransport',")
        lines.append(f"        effect=iam.Effect.DENY,")
        lines.append(f"        principals=[iam.AnyPrincipal()],")
        lines.append(f"        actions=['s3:*'],")
        lines.append(f"        resources=[")
        lines.append(f"            {logical_id.replace('-', '_')}.bucket_arn,")
        lines.append(f"            {logical_id.replace('-', '_')}.arn_for_objects('*')")
        lines.append(f"        ],")
        lines.append(f"        conditions={{")
        lines.append(f"            'Bool': {{'aws:SecureTransport': 'false'}}")
        lines.append(f"        }}")
        lines.append(f"    )")
        lines.append(f")")
        lines.append("")
        
        return lines
    
    def _resolve_reference(self, reference: str, context: GenerationContext) -> str:
        """
        Resolve a resource reference to a CDK variable name.
        
        Args:
            reference: Reference string like ${resource.kms-main.id}
            context: Generation context with resolved links
            
        Returns:
            Variable name to use in generated code
        """
        if not reference:
            return ""
        
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
    
    def get_outputs(self, resource_config: Dict[str, Any]) -> Dict[str, str]:
        """
        Define S3 bucket outputs for cross-stack references.
        
        Args:
            resource_config: S3 configuration
            
        Returns:
            Dictionary mapping output names to CDK value expressions
        """
        logical_id = resource_config.get('logical_id', 's3-bucket')
        var_name = logical_id.replace('-', '_')
        
        return {
            'name': f"{var_name}.bucket_name",
            'arn': f"{var_name}.bucket_arn",
            'domain_name': f"{var_name}.bucket_domain_name",
            'regional_domain_name': f"{var_name}.bucket_regional_domain_name"
        }
