"""RDS Template for generating CDK code for RDS database instances."""

from typing import Dict, Any
from cdk_templates.templates.base import ResourceTemplate, GenerationContext


class RDSTemplate(ResourceTemplate):
    """Template for generating AWS RDS database infrastructure with CDK."""
    
    def generate_code(self, resource_config: Dict[str, Any], context: GenerationContext) -> str:
        """
        Generate CDK Python code for RDS instance with encryption, backups, and security.
        
        Args:
            resource_config: RDS configuration with properties like engine, instance_class, etc.
            context: Generation context with naming and tagging services
            
        Returns:
            CDK Python code as a string
        """
        logical_id = resource_config.get('logical_id', 'rds-main')
        properties = resource_config.get('properties', {})
        
        # Extract configuration
        engine = properties.get('engine', 'postgres')
        engine_version = properties.get('engine_version', '15.3')
        instance_class = properties.get('instance_class', 'db.t3.medium')
        allocated_storage = properties.get('allocated_storage', 100)
        multi_az = properties.get('multi_az', context.environment == 'production')
        vpc_ref = properties.get('vpc_ref', '')
        subnet_refs = properties.get('subnet_refs', [])
        backup_retention_days = properties.get('backup_retention_days', 7)
        preferred_backup_window = properties.get('preferred_backup_window', '03:00-04:00')
        encryption_enabled = properties.get('encryption_enabled', True)
        storage_encrypted = properties.get('storage_encrypted', True)
        
        # Generate resource name using naming service
        db_name = context.naming_service.generate_name(
            resource_type='rds',
            purpose=logical_id,
            environment=context.environment,
            region=context.region
        )
        
        # Get tags from tagging service
        from cdk_templates.models import ResourceConfig
        resource_obj = ResourceConfig(
            logical_id=logical_id,
            resource_type='rds',
            properties=properties,
            tags=resource_config.get('tags', {})
        )
        tags = context.tagging_service.apply_tags(resource_obj, context.environment)
        
        # Build the CDK code
        code_lines = []
        
        # Add comment header
        code_lines.append(f"# RDS Instance: {db_name}")
        code_lines.append(f"# Engine: {engine} {engine_version}, Instance: {instance_class}, Multi-AZ: {multi_az}")
        code_lines.append("")
        
        # Resolve VPC reference
        vpc_var = self._resolve_reference(vpc_ref, context)
        
        # Create KMS key for encryption
        if encryption_enabled or storage_encrypted:
            kms_key_name = f"{db_name}-key"
            code_lines.append(f"# KMS Key for RDS encryption")
            code_lines.append(f"{logical_id.replace('-', '_')}_kms_key = kms.Key(")
            code_lines.append(f"    self, '{logical_id}-kms-key',")
            code_lines.append(f"    description='KMS key for {db_name} encryption',")
            code_lines.append(f"    enable_key_rotation=True,")
            code_lines.append(f"    removal_policy=cdk.RemovalPolicy.RETAIN")
            code_lines.append(")")
            code_lines.append("")
        
        # Create Secrets Manager secret for credentials
        code_lines.append(f"# Secrets Manager secret for database credentials")
        code_lines.append(f"{logical_id.replace('-', '_')}_secret = secretsmanager.Secret(")
        code_lines.append(f"    self, '{logical_id}-secret',")
        code_lines.append(f"    secret_name='{db_name}-credentials',")
        code_lines.append(f"    description='Database credentials for {db_name}',")
        code_lines.append(f"    generate_secret_string=secretsmanager.SecretStringGenerator(")
        code_lines.append(f"        secret_string_template=json.dumps({{'username': 'admin'}}),")
        code_lines.append(f"        generate_string_key='password',")
        code_lines.append(f"        exclude_punctuation=True,")
        code_lines.append(f"        password_length=32")
        code_lines.append(f"    )")
        code_lines.append(")")
        code_lines.append("")
        
        # Create DB subnet group with private subnets
        code_lines.append(f"# DB Subnet Group (private subnets only)")
        code_lines.append(f"{logical_id.replace('-', '_')}_subnet_group = rds.SubnetGroup(")
        code_lines.append(f"    self, '{logical_id}-subnet-group',")
        code_lines.append(f"    description='Subnet group for {db_name}',")
        code_lines.append(f"    vpc={vpc_var},")
        code_lines.append(f"    vpc_subnets=ec2.SubnetSelection(")
        code_lines.append(f"        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS")
        code_lines.append(f"    ),")
        code_lines.append(f"    removal_policy=cdk.RemovalPolicy.DESTROY")
        code_lines.append(")")
        code_lines.append("")
        
        # Create security group for database
        sg_name = f"{db_name}-sg"
        code_lines.append(f"# Security Group for RDS instance")
        code_lines.append(f"{logical_id.replace('-', '_')}_sg = ec2.SecurityGroup(")
        code_lines.append(f"    self, '{logical_id}-sg',")
        code_lines.append(f"    vpc={vpc_var},")
        code_lines.append(f"    security_group_name='{sg_name}',")
        code_lines.append(f"    description='Security group for {db_name}',")
        code_lines.append(f"    allow_all_outbound=False")
        code_lines.append(")")
        code_lines.append("")
        code_lines.append(f"# Restrictive ingress rules - configure based on your requirements")
        code_lines.append(f"# Example: Allow access from application security group")
        code_lines.append(f"# {logical_id.replace('-', '_')}_sg.add_ingress_rule(")
        code_lines.append(f"#     peer=ec2.Peer.security_group_id(app_sg_id),")
        code_lines.append(f"#     connection=ec2.Port.tcp({self._get_db_port(engine)}),")
        code_lines.append(f"#     description='Allow database access from application'")
        code_lines.append(f"# )")
        code_lines.append("")
        
        # Create RDS instance
        code_lines.append(f"# RDS Database Instance")
        code_lines.append(f"{logical_id.replace('-', '_')} = rds.DatabaseInstance(")
        code_lines.append(f"    self, '{logical_id}',")
        code_lines.append(f"    instance_identifier='{db_name}',")
        
        # Engine configuration
        engine_map = {
            'postgres': 'rds.DatabaseInstanceEngine.postgres',
            'mysql': 'rds.DatabaseInstanceEngine.mysql',
            'mariadb': 'rds.DatabaseInstanceEngine.mariadb',
            'oracle-ee': 'rds.DatabaseInstanceEngine.oracle_ee',
            'oracle-se2': 'rds.DatabaseInstanceEngine.oracle_se2',
            'sqlserver-ex': 'rds.DatabaseInstanceEngine.sql_server_ex',
            'sqlserver-web': 'rds.DatabaseInstanceEngine.sql_server_web',
            'sqlserver-se': 'rds.DatabaseInstanceEngine.sql_server_se',
            'sqlserver-ee': 'rds.DatabaseInstanceEngine.sql_server_ee'
        }
        
        engine_call = engine_map.get(engine, 'rds.DatabaseInstanceEngine.postgres')
        code_lines.append(f"    engine={engine_call}(")
        code_lines.append(f"        version=rds.{self._get_engine_version_class(engine)}('{engine_version}')")
        code_lines.append(f"    ),")
        
        # Instance configuration
        code_lines.append(f"    instance_type=ec2.InstanceType('{instance_class}'),")
        code_lines.append(f"    vpc={vpc_var},")
        code_lines.append(f"    subnet_group={logical_id.replace('-', '_')}_subnet_group,")
        code_lines.append(f"    security_groups=[{logical_id.replace('-', '_')}_sg],")
        
        # Credentials from Secrets Manager
        code_lines.append(f"    credentials=rds.Credentials.from_secret({logical_id.replace('-', '_')}_secret),")
        
        # Storage configuration
        code_lines.append(f"    allocated_storage={allocated_storage},")
        code_lines.append(f"    storage_type=rds.StorageType.GP3,")
        code_lines.append(f"    storage_encrypted={storage_encrypted},")
        
        # Encryption key
        if encryption_enabled or storage_encrypted:
            code_lines.append(f"    storage_encryption_key={logical_id.replace('-', '_')}_kms_key,")
        
        # Multi-AZ configuration
        code_lines.append(f"    multi_az={multi_az},")
        
        # Backup configuration
        code_lines.append(f"    backup_retention=cdk.Duration.days({backup_retention_days}),")
        code_lines.append(f"    preferred_backup_window='{preferred_backup_window}',")
        
        # Deletion protection for production
        if context.environment == 'production':
            code_lines.append(f"    deletion_protection=True,")
        else:
            code_lines.append(f"    deletion_protection=False,")
        
        # Removal policy
        code_lines.append(f"    removal_policy=cdk.RemovalPolicy.SNAPSHOT,")
        
        # Auto minor version upgrade
        code_lines.append(f"    auto_minor_version_upgrade=True,")
        
        # Publicly accessible (always false for security)
        code_lines.append(f"    publicly_accessible=False")
        code_lines.append(")")
        code_lines.append("")
        
        # Apply tags
        code_lines.append(f"# Apply tags to RDS instance")
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
    
    def _get_db_port(self, engine: str) -> int:
        """
        Get the default port for a database engine.
        
        Args:
            engine: Database engine name
            
        Returns:
            Default port number
        """
        port_map = {
            'postgres': 5432,
            'mysql': 3306,
            'mariadb': 3306,
            'oracle-ee': 1521,
            'oracle-se2': 1521,
            'sqlserver-ex': 1433,
            'sqlserver-web': 1433,
            'sqlserver-se': 1433,
            'sqlserver-ee': 1433
        }
        return port_map.get(engine, 5432)
    
    def _get_engine_version_class(self, engine: str) -> str:
        """
        Get the CDK engine version class name for a database engine.
        
        Args:
            engine: Database engine name
            
        Returns:
            CDK engine version class name
        """
        version_class_map = {
            'postgres': 'PostgresEngineVersion.of',
            'mysql': 'MysqlEngineVersion.of',
            'mariadb': 'MariaDbEngineVersion.of',
            'oracle-ee': 'OracleEngineVersion.of',
            'oracle-se2': 'OracleEngineVersion.of',
            'sqlserver-ex': 'SqlServerEngineVersion.of',
            'sqlserver-web': 'SqlServerEngineVersion.of',
            'sqlserver-se': 'SqlServerEngineVersion.of',
            'sqlserver-ee': 'SqlServerEngineVersion.of'
        }
        return version_class_map.get(engine, 'PostgresEngineVersion.of')
    
    def get_outputs(self, resource_config: Dict[str, Any]) -> Dict[str, str]:
        """
        Define RDS instance outputs for cross-stack references.
        
        Args:
            resource_config: RDS configuration
            
        Returns:
            Dictionary mapping output names to CDK value expressions
        """
        logical_id = resource_config.get('logical_id', 'rds-main')
        var_name = logical_id.replace('-', '_')
        
        return {
            'endpoint': f"{var_name}.db_instance_endpoint_address",
            'port': f"str({var_name}.db_instance_endpoint_port)",
            'secret_arn': f"{var_name}_secret.secret_arn",
            'security_group_id': f"{var_name}_sg.security_group_id"
        }
