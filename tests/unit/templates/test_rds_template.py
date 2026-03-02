"""Unit tests for RDS Template."""

import pytest
from cdk_templates.templates.rds_template import RDSTemplate
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


@pytest.fixture
def production_context(naming_service, tagging_service, resource_registry):
    """Create a production generation context."""
    return GenerationContext(
        environment='production',
        region='us-east-1',
        account_id='123456789012',
        naming_service=naming_service,
        tagging_service=tagging_service,
        resource_registry=resource_registry,
        resolved_links={}
    )


class TestRDSTemplate:
    """Test suite for RDSTemplate."""
    
    def test_generate_code_basic_configuration(self, generation_context):
        """Test RDS template with basic configuration."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-main',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'engine_version': '15.3',
                'instance_class': 'db.t3.medium',
                'allocated_storage': 100,
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify basic structure
        assert 'rds_main = rds.DatabaseInstance(' in code
        assert "instance_type=ec2.InstanceType('db.t3.medium')" in code
        assert 'allocated_storage=100' in code
        
        # Verify engine configuration
        assert 'rds.DatabaseInstanceEngine.postgres' in code
        assert "rds.PostgresEngineVersion.of('15.3')" in code
        
        # Verify VPC association
        assert 'vpc=vpc_main' in code
    
    def test_generate_code_with_encryption(self, generation_context):
        """Test RDS template with encryption enabled."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-encrypted',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.small',
                'vpc_ref': '${resource.vpc-main.id}',
                'encryption_enabled': True,
                'storage_encrypted': True
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify KMS key creation
        assert 'rds_encrypted_kms_key = kms.Key(' in code
        assert 'KMS key for' in code
        assert 'enable_key_rotation=True' in code
        
        # Verify encryption is enabled
        assert 'storage_encrypted=True' in code
        assert 'storage_encryption_key=rds_encrypted_kms_key' in code
    
    def test_generate_code_with_secrets_manager(self, generation_context):
        """Test RDS template with Secrets Manager integration."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-secure',
            'resource_type': 'rds',
            'properties': {
                'engine': 'mysql',
                'instance_class': 'db.t3.micro',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify Secrets Manager secret creation
        assert 'rds_secure_secret = secretsmanager.Secret(' in code
        assert 'Database credentials for' in code
        assert 'generate_secret_string=secretsmanager.SecretStringGenerator(' in code
        assert "'username': 'admin'" in code
        assert 'password_length=32' in code
        
        # Verify credentials reference
        assert 'credentials=rds.Credentials.from_secret(rds_secure_secret)' in code
    
    def test_generate_code_with_private_subnets(self, generation_context):
        """Test RDS template with private subnet configuration."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-private',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'subnet_refs': [
                    '${resource.vpc-main.private_subnet_1}',
                    '${resource.vpc-main.private_subnet_2}'
                ]
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify DB subnet group creation
        assert 'rds_private_subnet_group = rds.SubnetGroup(' in code
        assert 'subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS' in code
        assert 'Subnet group for' in code
        
        # Verify subnet group is used
        assert 'subnet_group=rds_private_subnet_group' in code
    
    def test_generate_code_with_security_group(self, generation_context):
        """Test RDS template with security group configuration."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-sg',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.small',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify security group creation
        assert 'rds_sg_sg = ec2.SecurityGroup(' in code
        assert 'Security group for' in code
        assert 'allow_all_outbound=False' in code
        
        # Verify restrictive ingress rules comment
        assert 'Restrictive ingress rules' in code
        assert 'configure based on your requirements' in code
        
        # Verify security group is used
        assert 'security_groups=[rds_sg_sg]' in code
    
    def test_generate_code_with_backup_configuration(self, generation_context):
        """Test RDS template with backup configuration."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-backup',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'backup_retention_days': 14,
                'preferred_backup_window': '02:00-03:00'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify backup configuration
        assert 'backup_retention=cdk.Duration.days(14)' in code
        assert "preferred_backup_window='02:00-03:00'" in code
    
    def test_generate_code_multi_az_production(self, production_context):
        """Test RDS template with Multi-AZ enabled for production."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-prod',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.r5.large',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, production_context)
        
        # Verify Multi-AZ is enabled for production
        assert 'multi_az=True' in code
        
        # Verify deletion protection for production
        assert 'deletion_protection=True' in code
    
    def test_generate_code_multi_az_dev(self, generation_context):
        """Test RDS template with Multi-AZ disabled for dev."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-dev',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.small',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify Multi-AZ is disabled for dev (defaults to False)
        assert 'multi_az=False' in code
        
        # Verify deletion protection is disabled for dev
        assert 'deletion_protection=False' in code
    
    def test_generate_code_multi_az_explicit(self, generation_context):
        """Test RDS template with explicit Multi-AZ configuration."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-ha',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'multi_az': True
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify Multi-AZ is enabled when explicitly set
        assert 'multi_az=True' in code
    
    def test_generate_code_mysql_engine(self, generation_context):
        """Test RDS template with MySQL engine."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-mysql',
            'resource_type': 'rds',
            'properties': {
                'engine': 'mysql',
                'engine_version': '8.0.33',
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify MySQL engine configuration
        assert 'rds.DatabaseInstanceEngine.mysql' in code
        assert "rds.MysqlEngineVersion.of('8.0.33')" in code
    
    def test_generate_code_mariadb_engine(self, generation_context):
        """Test RDS template with MariaDB engine."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-mariadb',
            'resource_type': 'rds',
            'properties': {
                'engine': 'mariadb',
                'engine_version': '10.11',
                'instance_class': 'db.t3.small',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify MariaDB engine configuration
        assert 'rds.DatabaseInstanceEngine.mariadb' in code
        assert "rds.MariaDbEngineVersion.of('10.11')" in code
    
    def test_generate_code_applies_tags(self, generation_context):
        """Test that RDS template applies tags correctly."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-tagged',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.micro',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {'CustomTag': 'CustomValue'}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify tags are applied
        assert 'cdk.Tags.of(rds_tagged).add' in code
        assert 'Environment' in code
        assert 'ManagedBy' in code
    
    def test_generate_code_storage_configuration(self, generation_context):
        """Test RDS template with storage configuration."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-storage',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.medium',
                'allocated_storage': 500,
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify storage configuration
        assert 'allocated_storage=500' in code
        assert 'storage_type=rds.StorageType.GP3' in code
    
    def test_generate_code_publicly_accessible_false(self, generation_context):
        """Test RDS template ensures publicly_accessible is false."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-secure',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.small',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify publicly accessible is false for security
        assert 'publicly_accessible=False' in code
    
    def test_generate_code_auto_minor_version_upgrade(self, generation_context):
        """Test RDS template enables auto minor version upgrade."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-auto-upgrade',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify auto minor version upgrade is enabled
        assert 'auto_minor_version_upgrade=True' in code
    
    def test_generate_code_removal_policy(self, generation_context):
        """Test RDS template sets removal policy to snapshot."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-snapshot',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'instance_class': 'db.t3.small',
                'vpc_ref': '${resource.vpc-main.id}'
            },
            'tags': {}
        }
        
        code = template.generate_code(resource_config, generation_context)
        
        # Verify removal policy is set to snapshot
        assert 'removal_policy=cdk.RemovalPolicy.SNAPSHOT' in code
    
    def test_get_outputs(self):
        """Test RDS template outputs."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-main',
            'resource_type': 'rds',
            'properties': {}
        }
        
        outputs = template.get_outputs(resource_config)
        
        # Verify outputs
        assert 'endpoint' in outputs
        assert 'port' in outputs
        assert 'secret_arn' in outputs
        assert 'security_group_id' in outputs
        
        # Verify output values reference the correct variable
        assert 'rds_main.db_instance_endpoint_address' in outputs['endpoint']
        assert 'rds_main.db_instance_endpoint_port' in outputs['port']
        assert 'rds_main_secret.secret_arn' in outputs['secret_arn']
    
    def test_resolve_reference(self, generation_context):
        """Test reference resolution."""
        template = RDSTemplate()
        
        # Test resource reference
        ref = '${resource.vpc-main.id}'
        resolved = template._resolve_reference(ref, generation_context)
        assert resolved == 'vpc_main'
        
        # Test empty reference
        ref = ''
        resolved = template._resolve_reference(ref, generation_context)
        assert resolved == 'vpc'
    
    def test_get_db_port(self):
        """Test database port resolution."""
        template = RDSTemplate()
        
        # Test PostgreSQL
        assert template._get_db_port('postgres') == 5432
        
        # Test MySQL
        assert template._get_db_port('mysql') == 3306
        
        # Test MariaDB
        assert template._get_db_port('mariadb') == 3306
        
        # Test Oracle
        assert template._get_db_port('oracle-ee') == 1521
        
        # Test SQL Server
        assert template._get_db_port('sqlserver-ex') == 1433
        
        # Test unknown engine (defaults to PostgreSQL)
        assert template._get_db_port('unknown') == 5432
    
    def test_get_engine_version_class(self):
        """Test engine version class resolution."""
        template = RDSTemplate()
        
        # Test PostgreSQL
        assert template._get_engine_version_class('postgres') == 'PostgresEngineVersion.of'
        
        # Test MySQL
        assert template._get_engine_version_class('mysql') == 'MysqlEngineVersion.of'
        
        # Test MariaDB
        assert template._get_engine_version_class('mariadb') == 'MariaDbEngineVersion.of'
        
        # Test Oracle
        assert template._get_engine_version_class('oracle-ee') == 'OracleEngineVersion.of'
        
        # Test SQL Server
        assert template._get_engine_version_class('sqlserver-ex') == 'SqlServerEngineVersion.of'
        
        # Test unknown engine (defaults to PostgreSQL)
        assert template._get_engine_version_class('unknown') == 'PostgresEngineVersion.of'
    
    def test_generate_code_complete_configuration(self, production_context):
        """Test RDS template with all configuration options."""
        template = RDSTemplate()
        
        resource_config = {
            'logical_id': 'rds-complete',
            'resource_type': 'rds',
            'properties': {
                'engine': 'postgres',
                'engine_version': '15.3',
                'instance_class': 'db.r5.xlarge',
                'allocated_storage': 1000,
                'multi_az': True,
                'vpc_ref': '${resource.vpc-main.id}',
                'subnet_refs': [
                    '${resource.vpc-main.private_subnet_1}',
                    '${resource.vpc-main.private_subnet_2}'
                ],
                'backup_retention_days': 30,
                'preferred_backup_window': '01:00-02:00',
                'encryption_enabled': True,
                'storage_encrypted': True
            },
            'tags': {'Application': 'CriticalDB'}
        }
        
        code = template.generate_code(resource_config, production_context)
        
        # Verify all components are present
        assert 'rds_complete = rds.DatabaseInstance(' in code
        assert 'db.r5.xlarge' in code
        assert 'allocated_storage=1000' in code
        assert 'multi_az=True' in code
        assert 'backup_retention=cdk.Duration.days(30)' in code
        assert "preferred_backup_window='01:00-02:00'" in code
        assert 'storage_encrypted=True' in code
        assert 'rds_complete_kms_key' in code
        assert 'rds_complete_secret' in code
        assert 'rds_complete_subnet_group' in code
        assert 'rds_complete_sg' in code
        assert 'deletion_protection=True' in code
