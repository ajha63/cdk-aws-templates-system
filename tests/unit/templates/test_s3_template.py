"""Unit tests for S3 Template."""

import pytest
from cdk_templates.templates.s3_template import S3Template
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


@pytest.fixture
def production_context(metadata, tmp_path):
    """Create production generation context."""
    registry_file = tmp_path / "registry.json"
    return GenerationContext(
        environment='production',
        region='us-east-1',
        account_id='123456789012',
        naming_service=NamingConventionService(),
        tagging_service=TaggingStrategyService(metadata),
        resource_registry=ResourceRegistry(str(registry_file)),
        resolved_links={}
    )


def test_s3_template_basic_configuration(context):
    """Test S3 template with basic configuration."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-data',
        'resource_type': 's3',
        'properties': {
            'versioning_enabled': True,
            'encryption': 'aws:kms',
            'block_public_access': True
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify S3 bucket creation
    assert 's3_data = s3.Bucket(' in code
    assert 'versioned=True' in code
    assert 'encryption=s3.BucketEncryption.KMS_MANAGED' in code
    assert 'block_public_access=s3.BlockPublicAccess.BLOCK_ALL' in code


def test_s3_template_versioning_enabled_by_default(context):
    """Test S3 template enables versioning by default."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-default',
        'resource_type': 's3',
        'properties': {},
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify versioning is enabled by default
    assert 'versioned=True' in code


def test_s3_template_versioning_disabled(context):
    """Test S3 template with versioning explicitly disabled."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-no-version',
        'resource_type': 's3',
        'properties': {
            'versioning_enabled': False
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify versioning is disabled
    assert 'versioned=False' in code


def test_s3_template_block_public_access_by_default(context):
    """Test S3 template blocks public access by default."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-secure',
        'resource_type': 's3',
        'properties': {},
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify public access is blocked by default
    assert 'block_public_access=s3.BlockPublicAccess.BLOCK_ALL' in code


def test_s3_template_kms_encryption(context):
    """Test S3 template with KMS encryption."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-encrypted',
        'resource_type': 's3',
        'properties': {
            'encryption': 'aws:kms'
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify KMS encryption is configured
    assert 'encryption=s3.BucketEncryption.KMS_MANAGED' in code


def test_s3_template_kms_encryption_with_key_reference(context):
    """Test S3 template with KMS encryption using referenced key."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-kms',
        'resource_type': 's3',
        'properties': {
            'encryption': 'aws:kms',
            'kms_key_ref': '${resource.kms-main.id}'
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify KMS encryption with referenced key
    assert 'encryption=s3.BucketEncryption.KMS' in code
    assert 'encryption_key=kms_main' in code


def test_s3_template_sse_s3_encryption(context):
    """Test S3 template with SSE-S3 encryption."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-sse',
        'resource_type': 's3',
        'properties': {
            'encryption': 'AES256'
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify SSE-S3 encryption is configured
    assert 'encryption=s3.BucketEncryption.S3_MANAGED' in code


def test_s3_template_lifecycle_rules(context):
    """Test S3 template with lifecycle rules."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-lifecycle',
        'resource_type': 's3',
        'properties': {
            'lifecycle_rules': [
                {
                    'id': 'transition-to-ia',
                    'enabled': True,
                    'transitions': [
                        {
                            'storage_class': 'STANDARD_IA',
                            'days': 30
                        },
                        {
                            'storage_class': 'GLACIER',
                            'days': 90
                        }
                    ]
                }
            ]
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify lifecycle rules are configured
    assert 'lifecycle_rules=[' in code
    assert 's3.LifecycleRule(' in code
    assert "id='transition-to-ia'" in code
    assert 'enabled=True' in code
    assert 'storage_class=s3.StorageClass.STANDARD_IA' in code
    assert 'transition_after=cdk.Duration.days(30)' in code
    assert 'storage_class=s3.StorageClass.GLACIER' in code
    assert 'transition_after=cdk.Duration.days(90)' in code


def test_s3_template_lifecycle_rules_with_expiration(context):
    """Test S3 template with lifecycle rules including expiration."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-expire',
        'resource_type': 's3',
        'properties': {
            'lifecycle_rules': [
                {
                    'id': 'expire-old-objects',
                    'enabled': True,
                    'expiration_days': 365
                }
            ]
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify expiration is configured
    assert 'lifecycle_rules=[' in code
    assert "id='expire-old-objects'" in code
    assert 'expiration=cdk.Duration.days(365)' in code


def test_s3_template_access_logging_enabled(context):
    """Test S3 template with access logging enabled."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-logged',
        'resource_type': 's3',
        'properties': {
            'access_logging': {
                'enabled': True,
                'target_bucket_ref': '${resource.s3-logs.id}',
                'prefix': 'access-logs/'
            }
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify access logging is configured
    assert 'server_access_logs_bucket=s3_logs' in code
    assert "server_access_logs_prefix='access-logs/'" in code


def test_s3_template_access_logging_disabled(context):
    """Test S3 template with access logging disabled."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-no-logs',
        'resource_type': 's3',
        'properties': {
            'access_logging': {
                'enabled': False
            }
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify access logging is not configured
    assert 'server_access_logs_bucket' not in code


def test_s3_template_bucket_policy(context):
    """Test S3 template includes bucket policy with least privilege."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-policy',
        'resource_type': 's3',
        'properties': {},
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify bucket policy is included
    assert 's3_policy.add_to_resource_policy(' in code
    assert 'iam.PolicyStatement(' in code
    assert "sid='DenyInsecureTransport'" in code
    assert 'effect=iam.Effect.DENY' in code
    assert "'aws:SecureTransport': 'false'" in code


def test_s3_template_naming_convention(context):
    """Test that S3 template uses naming service correctly."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-data',
        'resource_type': 's3',
        'properties': {},
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify naming convention is applied
    # Pattern: {env}-{service}-{purpose}-{region}
    assert 'dev-app-s3-data-us-east-1' in code


def test_s3_template_tagging(context):
    """Test that S3 template applies tags correctly."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-tagged',
        'resource_type': 's3',
        'properties': {},
        'tags': {
            'DataClassification': 'Confidential'
        }
    }
    
    code = template.generate_code(config, context)
    
    # Verify mandatory tags are applied
    assert "cdk.Tags.of(s3_tagged).add('Environment', 'dev')" in code
    assert "cdk.Tags.of(s3_tagged).add('Project', 'test-project')" in code
    assert "cdk.Tags.of(s3_tagged).add('Owner', 'test-team')" in code
    assert "cdk.Tags.of(s3_tagged).add('CostCenter', 'engineering')" in code
    assert "cdk.Tags.of(s3_tagged).add('ManagedBy', 'cdk-template-system')" in code
    
    # Verify custom tag is applied
    assert "cdk.Tags.of(s3_tagged).add('DataClassification', 'Confidential')" in code


def test_s3_template_removal_policy(context):
    """Test S3 template sets removal policy to retain."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-retain',
        'resource_type': 's3',
        'properties': {},
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify removal policy is set to retain
    assert 'removal_policy=cdk.RemovalPolicy.RETAIN' in code
    assert 'auto_delete_objects=False' in code


def test_s3_template_get_outputs():
    """Test S3 template output definitions."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-data',
        'resource_type': 's3',
        'properties': {}
    }
    
    outputs = template.get_outputs(config)
    
    # Verify expected outputs
    assert 'name' in outputs
    assert 'arn' in outputs
    assert 'domain_name' in outputs
    assert 'regional_domain_name' in outputs
    
    # Verify output values reference the correct variable
    assert 's3_data.bucket_name' in outputs['name']
    assert 's3_data.bucket_arn' in outputs['arn']


def test_s3_template_variable_substitution(context):
    """Test that logical_id with hyphens is converted to valid Python variable names."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-my-data-bucket',
        'resource_type': 's3',
        'properties': {},
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify hyphenated logical_id is converted to underscores for Python variable
    assert 's3_my_data_bucket = s3.Bucket(' in code
    assert "self, 's3-my-data-bucket'," in code  # CDK construct ID keeps hyphens
    assert 'cdk.Tags.of(s3_my_data_bucket)' in code


def test_s3_template_complete_configuration(context):
    """Test S3 template with all configuration options."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-complete',
        'resource_type': 's3',
        'properties': {
            'versioning_enabled': True,
            'encryption': 'aws:kms',
            'kms_key_ref': '${resource.kms-main.id}',
            'block_public_access': True,
            'lifecycle_rules': [
                {
                    'id': 'archive-old-data',
                    'enabled': True,
                    'transitions': [
                        {
                            'storage_class': 'STANDARD_IA',
                            'days': 30
                        },
                        {
                            'storage_class': 'GLACIER',
                            'days': 90
                        }
                    ],
                    'expiration_days': 365
                }
            ],
            'access_logging': {
                'enabled': True,
                'target_bucket_ref': '${resource.s3-logs.id}',
                'prefix': 'data-logs/'
            }
        },
        'tags': {
            'DataClassification': 'Sensitive',
            'Compliance': 'GDPR'
        }
    }
    
    code = template.generate_code(config, context)
    
    # Verify all components are present
    assert 's3_complete = s3.Bucket(' in code
    assert 'versioned=True' in code
    assert 'encryption=s3.BucketEncryption.KMS' in code
    assert 'encryption_key=kms_main' in code
    assert 'block_public_access=s3.BlockPublicAccess.BLOCK_ALL' in code
    assert 'lifecycle_rules=[' in code
    assert "id='archive-old-data'" in code
    assert 'storage_class=s3.StorageClass.STANDARD_IA' in code
    assert 'storage_class=s3.StorageClass.GLACIER' in code
    assert 'expiration=cdk.Duration.days(365)' in code
    assert 'server_access_logs_bucket=s3_logs' in code
    assert "server_access_logs_prefix='data-logs/'" in code
    assert 's3_complete.add_to_resource_policy(' in code
    assert "cdk.Tags.of(s3_complete).add('DataClassification', 'Sensitive')" in code
    assert "cdk.Tags.of(s3_complete).add('Compliance', 'GDPR')" in code


def test_s3_template_minimal_configuration(context):
    """Test S3 template with minimal configuration using defaults."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-minimal',
        'resource_type': 's3',
        'properties': {},
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify defaults are applied
    assert 's3_minimal = s3.Bucket(' in code
    assert 'versioned=True' in code  # default
    assert 'encryption=s3.BucketEncryption.KMS_MANAGED' in code  # default
    assert 'block_public_access=s3.BlockPublicAccess.BLOCK_ALL' in code  # default
    assert 'removal_policy=cdk.RemovalPolicy.RETAIN' in code


def test_s3_template_multiple_lifecycle_rules(context):
    """Test S3 template with multiple lifecycle rules."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-multi-rules',
        'resource_type': 's3',
        'properties': {
            'lifecycle_rules': [
                {
                    'id': 'rule-1',
                    'enabled': True,
                    'transitions': [
                        {
                            'storage_class': 'STANDARD_IA',
                            'days': 30
                        }
                    ]
                },
                {
                    'id': 'rule-2',
                    'enabled': True,
                    'transitions': [
                        {
                            'storage_class': 'GLACIER',
                            'days': 60
                        }
                    ]
                }
            ]
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify both rules are present
    assert "id='rule-1'" in code
    assert "id='rule-2'" in code
    assert code.count('s3.LifecycleRule(') == 2


def test_s3_template_disabled_lifecycle_rule(context):
    """Test S3 template with disabled lifecycle rule."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-disabled-rule',
        'resource_type': 's3',
        'properties': {
            'lifecycle_rules': [
                {
                    'id': 'disabled-rule',
                    'enabled': False,
                    'transitions': [
                        {
                            'storage_class': 'GLACIER',
                            'days': 90
                        }
                    ]
                }
            ]
        },
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify rule is present but disabled
    assert "id='disabled-rule'" in code
    assert 'enabled=False' in code


def test_s3_template_resolve_reference():
    """Test reference resolution."""
    template = S3Template()
    
    from cdk_templates.templates.base import GenerationContext
    from cdk_templates.naming_service import NamingConventionService
    from cdk_templates.tagging_service import TaggingStrategyService
    from cdk_templates.resource_registry import ResourceRegistry
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        context = GenerationContext(
            environment='dev',
            region='us-east-1',
            account_id='123456789012',
            naming_service=NamingConventionService(),
            tagging_service=TaggingStrategyService(ConfigMetadata(
                project='test', owner='test', cost_center='test', description='test'
            )),
            resource_registry=ResourceRegistry(f"{tmpdir}/registry.json"),
            resolved_links={}
        )
        
        # Test resource reference
        ref = '${resource.kms-main.id}'
        resolved = template._resolve_reference(ref, context)
        assert resolved == 'kms_main'
        
        # Test empty reference
        ref = ''
        resolved = template._resolve_reference(ref, context)
        assert resolved == ''


def test_s3_template_encryption_default(context):
    """Test S3 template uses KMS encryption by default."""
    template = S3Template()
    
    config = {
        'logical_id': 's3-default-encryption',
        'resource_type': 's3',
        'properties': {},
        'tags': {}
    }
    
    code = template.generate_code(config, context)
    
    # Verify KMS encryption is used by default
    assert 'encryption=s3.BucketEncryption.KMS_MANAGED' in code
