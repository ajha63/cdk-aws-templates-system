"""Unit tests for TemplateGenerator."""

import pytest
import ast
from cdk_templates.template_generator import TemplateGenerator
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig
)
from cdk_templates.naming_service import NamingConventionService
from cdk_templates.tagging_service import TaggingStrategyService
from cdk_templates.resource_registry import ResourceRegistry
from cdk_templates.deployment_rules import DeploymentRulesEngine, EncryptionEnforcementRule
from cdk_templates.resource_link_resolver import ResourceLinkResolver


@pytest.fixture
def basic_config():
    """Create a basic configuration for testing."""
    return Configuration(
        version="1.0",
        metadata=ConfigMetadata(
            project="test-project",
            owner="test-team",
            cost_center="engineering",
            description="Test infrastructure"
        ),
        environments={
            "dev": EnvironmentConfig(
                name="dev",
                account_id="123456789012",
                region="us-east-1",
                tags={},
                overrides={}
            )
        },
        resources=[
            ResourceConfig(
                logical_id="vpc-main",
                resource_type="vpc",
                properties={
                    "cidr": "10.0.0.0/16",
                    "availability_zones": 3,
                    "enable_dns_hostnames": True,
                    "enable_flow_logs": True
                },
                tags={},
                depends_on=[]
            )
        ],
        deployment_rules=[]
    )


@pytest.fixture
def multi_resource_config():
    """Create a configuration with multiple resources."""
    return Configuration(
        version="1.0",
        metadata=ConfigMetadata(
            project="multi-resource",
            owner="test-team",
            cost_center="engineering",
            description="Multi-resource test"
        ),
        environments={
            "dev": EnvironmentConfig(
                name="dev",
                account_id="123456789012",
                region="us-east-1",
                tags={},
                overrides={}
            )
        },
        resources=[
            ResourceConfig(
                logical_id="vpc-main",
                resource_type="vpc",
                properties={
                    "cidr": "10.0.0.0/16",
                    "availability_zones": 2
                },
                tags={},
                depends_on=[]
            ),
            ResourceConfig(
                logical_id="ec2-web",
                resource_type="ec2",
                properties={
                    "instance_type": "t3.micro",
                    "vpc_ref": "${resource.vpc-main.id}",
                    "enable_session_manager": True
                },
                tags={},
                depends_on=["vpc-main"]
            ),
            ResourceConfig(
                logical_id="s3-data",
                resource_type="s3",
                properties={
                    "versioning_enabled": True,
                    "encryption": "aws:kms"
                },
                tags={},
                depends_on=[]
            )
        ],
        deployment_rules=[]
    )


class TestTemplateGeneratorInitialization:
    """Test TemplateGenerator initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default services."""
        generator = TemplateGenerator()
        
        assert generator.naming_service is not None
        assert generator.tagging_service is None  # Created lazily from config
        assert generator.resource_registry is not None
        assert generator.rules_engine is not None
        assert generator.link_resolver is not None
        assert len(generator.templates) == 4  # vpc, ec2, rds, s3
    
    def test_init_with_custom_services(self):
        """Test initialization with custom services."""
        naming_service = NamingConventionService()
        metadata = ConfigMetadata(
            project="test",
            owner="test",
            cost_center="test",
            description="Test"
        )
        tagging_service = TaggingStrategyService(metadata)
        
        generator = TemplateGenerator(
            naming_service=naming_service,
            tagging_service=tagging_service
        )
        
        assert generator.naming_service is naming_service
        assert generator.tagging_service is tagging_service


class TestCodeGeneration:
    """Test code generation functionality."""
    
    def test_generate_basic_vpc(self, basic_config):
        """Test generating code for a basic VPC configuration."""
        generator = TemplateGenerator()
        
        result = generator.generate(basic_config, environment="dev")
        
        assert result.success is True
        assert len(result.errors) == 0
        assert len(result.generated_files) > 0
        assert 'app.py' in result.generated_files
    
    def test_generate_multi_resource(self, multi_resource_config):
        """Test generating code for multiple resources."""
        generator = TemplateGenerator()
        
        result = generator.generate(multi_resource_config, environment="dev")
        
        assert result.success is True
        assert len(result.errors) == 0
        assert 'app.py' in result.generated_files
        
        # Check that stack file was created
        stack_files = [f for f in result.generated_files.keys() if f.startswith('stacks/')]
        assert len(stack_files) > 0
    
    def test_generate_without_environment(self, basic_config):
        """Test generation uses first environment when not specified."""
        generator = TemplateGenerator()
        
        result = generator.generate(basic_config)
        
        assert result.success is True
        assert len(result.errors) == 0
    
    def test_generate_with_invalid_environment(self, basic_config):
        """Test generation fails with invalid environment."""
        generator = TemplateGenerator()
        
        result = generator.generate(basic_config, environment="nonexistent")
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()
    
    def test_generate_with_no_environments(self):
        """Test generation fails when no environments defined."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="Test"
            ),
            environments={},
            resources=[],
            deployment_rules=[]
        )
        
        generator = TemplateGenerator()
        result = generator.generate(config)
        
        assert result.success is False
        assert "No environments" in result.errors[0]


class TestDeploymentRulesIntegration:
    """Test integration with deployment rules."""
    
    def test_apply_encryption_rule(self):
        """Test that encryption rule is applied during generation."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={}
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="s3-bucket",
                    resource_type="s3",
                    properties={
                        "versioning_enabled": True
                        # No encryption specified
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        # Create generator with encryption rule
        rules_engine = DeploymentRulesEngine()
        rules_engine.register_rule(EncryptionEnforcementRule())
        
        generator = TemplateGenerator(rules_engine=rules_engine)
        result = generator.generate(config, environment="dev")
        
        assert result.success is True
        # Check that encryption was added
        assert config.resources[0].properties.get("encryption") == "aws:kms"


class TestResourceLinkResolution:
    """Test resource link resolution during generation."""
    
    def test_resolve_vpc_reference(self, multi_resource_config):
        """Test that VPC references are resolved correctly."""
        generator = TemplateGenerator()
        
        result = generator.generate(multi_resource_config, environment="dev")
        
        assert result.success is True
        
        # Check that EC2 code references the VPC
        stack_file = [f for f in result.generated_files.keys() if 'stack.py' in f][0]
        stack_code = result.generated_files[stack_file]
        
        # Should contain VPC reference
        assert 'vpc_main' in stack_code or 'vpc-main' in stack_code
    
    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="test",
                cost_center="test",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={}
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="resource-a",
                    resource_type="vpc",
                    properties={},
                    tags={},
                    depends_on=["resource-b"]
                ),
                ResourceConfig(
                    logical_id="resource-b",
                    resource_type="ec2",
                    properties={},
                    tags={},
                    depends_on=["resource-a"]
                )
            ],
            deployment_rules=[]
        )
        
        generator = TemplateGenerator()
        result = generator.generate(config, environment="dev")
        
        assert result.success is False
        assert any("circular" in error.lower() for error in result.errors)


class TestImportGeneration:
    """Test import statement generation."""
    
    def test_generate_imports_for_vpc(self):
        """Test import generation for VPC resources."""
        resources = [
            ResourceConfig(
                logical_id="vpc-main",
                resource_type="vpc",
                properties={},
                tags={},
                depends_on=[]
            )
        ]
        
        generator = TemplateGenerator()
        imports = generator.generate_imports(resources)
        
        assert any("aws_ec2 as ec2" in imp for imp in imports)
        assert any("aws_logs as logs" in imp for imp in imports)
    
    def test_generate_imports_for_ec2(self):
        """Test import generation for EC2 resources."""
        resources = [
            ResourceConfig(
                logical_id="ec2-instance",
                resource_type="ec2",
                properties={},
                tags={},
                depends_on=[]
            )
        ]
        
        generator = TemplateGenerator()
        imports = generator.generate_imports(resources)
        
        assert any("aws_ec2 as ec2" in imp for imp in imports)
        assert any("aws_iam as iam" in imp for imp in imports)
    
    def test_generate_imports_for_rds(self):
        """Test import generation for RDS resources."""
        resources = [
            ResourceConfig(
                logical_id="rds-db",
                resource_type="rds",
                properties={},
                tags={},
                depends_on=[]
            )
        ]
        
        generator = TemplateGenerator()
        imports = generator.generate_imports(resources)
        
        assert any("aws_rds as rds" in imp for imp in imports)
        assert any("aws_kms as kms" in imp for imp in imports)
        assert any("aws_secretsmanager as secretsmanager" in imp for imp in imports)
        assert any("import json" in imp for imp in imports)
    
    def test_generate_imports_for_s3(self):
        """Test import generation for S3 resources."""
        resources = [
            ResourceConfig(
                logical_id="s3-bucket",
                resource_type="s3",
                properties={},
                tags={},
                depends_on=[]
            )
        ]
        
        generator = TemplateGenerator()
        imports = generator.generate_imports(resources)
        
        assert any("aws_s3 as s3" in imp for imp in imports)
        assert any("aws_iam as iam" in imp for imp in imports)
    
    def test_generate_imports_deduplication(self):
        """Test that duplicate imports are not generated."""
        resources = [
            ResourceConfig(
                logical_id="vpc-main",
                resource_type="vpc",
                properties={},
                tags={},
                depends_on=[]
            ),
            ResourceConfig(
                logical_id="ec2-instance",
                resource_type="ec2",
                properties={},
                tags={},
                depends_on=[]
            )
        ]
        
        generator = TemplateGenerator()
        imports = generator.generate_imports(resources)
        
        # Count occurrences of ec2 import
        ec2_imports = [imp for imp in imports if "aws_ec2 as ec2" in imp]
        assert len(ec2_imports) == 1


class TestFileStructure:
    """Test file structure generation."""
    
    def test_creates_app_py(self, basic_config):
        """Test that app.py is created."""
        generator = TemplateGenerator()
        result = generator.generate(basic_config, environment="dev")
        
        assert 'app.py' in result.generated_files
        
        app_content = result.generated_files['app.py']
        assert '#!/usr/bin/env python3' in app_content
        assert 'import aws_cdk as cdk' in app_content
        assert 'app.synth()' in app_content
    
    def test_creates_stack_file(self, basic_config):
        """Test that stack file is created in stacks/ directory."""
        generator = TemplateGenerator()
        result = generator.generate(basic_config, environment="dev")
        
        stack_files = [f for f in result.generated_files.keys() if f.startswith('stacks/') and f.endswith('.py')]
        assert len(stack_files) > 0
        
        # Check stack file name matches project
        assert any('test_project' in f for f in stack_files)
    
    def test_creates_stacks_init(self, basic_config):
        """Test that stacks/__init__.py is created."""
        generator = TemplateGenerator()
        result = generator.generate(basic_config, environment="dev")
        
        assert 'stacks/__init__.py' in result.generated_files
    
    def test_app_py_references_stack(self, basic_config):
        """Test that app.py correctly imports and instantiates the stack."""
        generator = TemplateGenerator()
        result = generator.generate(basic_config, environment="dev")
        
        app_content = result.generated_files['app.py']
        
        # Should import the stack
        assert 'from stacks.' in app_content
        assert 'import' in app_content
        
        # Should instantiate the stack
        assert 'Stack(' in app_content


class TestCodeValidation:
    """Test generated code validation."""
    
    def test_generated_code_is_valid_python(self, basic_config):
        """Test that generated code is syntactically valid Python."""
        generator = TemplateGenerator()
        result = generator.generate(basic_config, environment="dev")
        
        assert result.success is True
        
        # Try to parse each generated Python file
        for file_path, content in result.generated_files.items():
            if file_path.endswith('.py'):
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Generated code in {file_path} has syntax error: {e}")
    
    def test_multi_resource_code_is_valid(self, multi_resource_config):
        """Test that multi-resource generated code is valid."""
        generator = TemplateGenerator()
        result = generator.generate(multi_resource_config, environment="dev")
        
        assert result.success is True
        
        for file_path, content in result.generated_files.items():
            if file_path.endswith('.py'):
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Generated code in {file_path} has syntax error: {e}")


class TestStackGeneration:
    """Test stack code generation."""
    
    def test_generate_stack_creates_class(self, basic_config):
        """Test that generate_stack creates a stack class."""
        # Create generator with tagging service
        metadata = basic_config.metadata
        tagging_service = TaggingStrategyService(metadata)
        generator = TemplateGenerator(tagging_service=tagging_service)
        
        # Create context
        from cdk_templates.templates.base import GenerationContext
        context = GenerationContext(
            environment="dev",
            region="us-east-1",
            account_id="123456789012",
            naming_service=generator.naming_service,
            tagging_service=tagging_service,
            resource_registry=generator.resource_registry,
            resolved_links={}
        )
        
        stack_code = generator.generate_stack(basic_config, context)
        
        assert 'class' in stack_code
        assert 'Stack' in stack_code
        assert 'def __init__' in stack_code
    
    def test_generate_stack_includes_resources(self, multi_resource_config):
        """Test that generate_stack includes all resources."""
        # Create generator with tagging service
        metadata = multi_resource_config.metadata
        tagging_service = TaggingStrategyService(metadata)
        generator = TemplateGenerator(tagging_service=tagging_service)
        
        from cdk_templates.templates.base import GenerationContext
        context = GenerationContext(
            environment="dev",
            region="us-east-1",
            account_id="123456789012",
            naming_service=generator.naming_service,
            tagging_service=tagging_service,
            resource_registry=generator.resource_registry,
            resolved_links={}
        )
        
        stack_code = generator.generate_stack(multi_resource_config, context)
        
        # Should contain VPC
        assert 'ec2.Vpc' in stack_code or 'Vpc(' in stack_code
        
        # Should contain EC2
        assert 'ec2.Instance' in stack_code or 'Instance(' in stack_code
        
        # Should contain S3
        assert 's3.Bucket' in stack_code or 'Bucket(' in stack_code


class TestCodeFormatting:
    """Test code formatting functionality."""
    
    def test_format_code_with_black_available(self, basic_config):
        """Test code formatting when black is available."""
        generator = TemplateGenerator()
        
        # Simple code to format
        code = "x=1\ny=2\nz=x+y"
        
        formatted = generator._format_code(code)
        
        # Should have proper spacing (if black is available)
        # If black is not available, should return original
        assert formatted is not None
    
    def test_format_code_handles_errors(self):
        """Test that format_code handles errors gracefully."""
        generator = TemplateGenerator()
        
        # Invalid Python code
        code = "this is not valid python ]["
        
        # Should not raise exception
        formatted = generator._format_code(code)
        assert formatted == code  # Returns original on error


class TestHeaderComments:
    """Test header comment generation."""
    
    def test_add_file_header_comment(self, basic_config):
        """Test that header comments are added to files."""
        generator = TemplateGenerator()
        
        header = generator._add_file_header_comment('app.py', basic_config)
        
        assert 'Generated by CDK AWS Templates System' in header
        assert basic_config.metadata.project in header
        assert basic_config.metadata.owner in header
        assert 'DO NOT EDIT' in header
    
    def test_generated_files_have_headers(self, basic_config):
        """Test that generated files include header comments."""
        generator = TemplateGenerator()
        result = generator.generate(basic_config, environment="dev")
        
        app_content = result.generated_files['app.py']
        
        assert 'Generated by CDK AWS Templates System' in app_content
        assert 'DO NOT EDIT' in app_content


class TestDependencyOrdering:
    """Test that resources are generated in dependency order."""
    
    def test_resources_ordered_by_dependencies(self, multi_resource_config):
        """Test that resources are generated in topological order."""
        # Create generator with tagging service
        metadata = multi_resource_config.metadata
        tagging_service = TaggingStrategyService(metadata)
        generator = TemplateGenerator(tagging_service=tagging_service)
        
        from cdk_templates.templates.base import GenerationContext
        context = GenerationContext(
            environment="dev",
            region="us-east-1",
            account_id="123456789012",
            naming_service=generator.naming_service,
            tagging_service=tagging_service,
            resource_registry=generator.resource_registry,
            resolved_links={}
        )
        
        stack_code = generator.generate_stack(multi_resource_config, context)
        
        # VPC should appear before EC2 (since EC2 depends on VPC)
        vpc_pos = stack_code.find('vpc_main')
        ec2_pos = stack_code.find('ec2_web')
        
        if vpc_pos != -1 and ec2_pos != -1:
            assert vpc_pos < ec2_pos, "VPC should be generated before EC2"
