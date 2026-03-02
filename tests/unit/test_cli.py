"""Unit tests for CLI interface."""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest
from click.testing import CliRunner

from cdk_templates.cli import main, generate, validate, query, docs
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
    ValidationResult,
    ValidationError,
    GenerationResult,
    ResourceMetadata
)


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return Configuration(
        version="1.0",
        metadata=ConfigMetadata(
            project="test-project",
            owner="test-owner",
            cost_center="test-cc",
            description="Test configuration"
        ),
        environments={
            "dev": EnvironmentConfig(
                name="dev",
                account_id="123456789012",
                region="us-east-1",
                tags={"Environment": "dev"}
            )
        },
        resources=[
            ResourceConfig(
                logical_id="vpc-main",
                resource_type="vpc",
                properties={"cidr": "10.0.0.0/16"}
            )
        ]
    )


@pytest.fixture
def sample_resource_metadata():
    """Create sample resource metadata for testing."""
    return ResourceMetadata(
        resource_id="vpc-123",
        resource_type="vpc",
        logical_name="vpc-main",
        physical_name="dev-myapp-vpc-us-east-1",
        stack_name="network-stack",
        environment="dev",
        tags={"Environment": "dev", "Project": "myapp"},
        outputs={"VpcId": "vpc-123"},
        dependencies=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestGenerateCommand:
    """Tests for the generate command."""
    
    def test_generate_success(self, cli_runner, tmp_path, sample_config):
        """Test successful code generation."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        output_dir = tmp_path / "output"
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.ValidationEngine') as mock_validator, \
             patch('cdk_templates.cli.TemplateGenerator') as mock_generator:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock validator
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[]
            )
            mock_validator.return_value = mock_validator_instance
            
            # Mock generator
            mock_generator_instance = Mock()
            mock_generator_instance.generate.return_value = GenerationResult(
                success=True,
                generated_files={
                    "app.py": "# Generated CDK app",
                    "stacks/network_stack.py": "# Network stack"
                },
                errors=[]
            )
            mock_generator.return_value = mock_generator_instance
            
            result = cli_runner.invoke(
                generate,
                ['-c', str(config_file), '-e', 'dev', '-o', str(output_dir)]
            )
            
            assert result.exit_code == 0
            assert "✓ Validation passed" in result.output
            assert "✓ Successfully generated" in result.output
    
    def test_generate_validation_failure(self, cli_runner, tmp_path, sample_config):
        """Test generation with validation failure."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.ValidationEngine') as mock_validator:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock validator with errors
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field_path="resources[0].properties.cidr",
                        message="Invalid CIDR block",
                        error_code="INVALID_CIDR",
                        severity="ERROR"
                    )
                ],
                warnings=[]
            )
            mock_validator_instance.generate_error_report.return_value = "Validation failed"
            mock_validator.return_value = mock_validator_instance
            
            result = cli_runner.invoke(
                generate,
                ['-c', str(config_file), '-e', 'dev']
            )
            
            assert result.exit_code == 1
            assert "✗ Validation failed" in result.output
    
    def test_generate_validate_only(self, cli_runner, tmp_path, sample_config):
        """Test generate with --validate-only flag."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.ValidationEngine') as mock_validator:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock validator
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[]
            )
            mock_validator.return_value = mock_validator_instance
            
            result = cli_runner.invoke(
                generate,
                ['-c', str(config_file), '-e', 'dev', '--validate-only']
            )
            
            assert result.exit_code == 0
            assert "✓ Configuration is valid" in result.output
    
    def test_generate_with_warnings(self, cli_runner, tmp_path, sample_config):
        """Test generation with warnings."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        output_dir = tmp_path / "output"
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.ValidationEngine') as mock_validator, \
             patch('cdk_templates.cli.TemplateGenerator') as mock_generator:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock validator with warnings
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[
                    ValidationError(
                        field_path="resources[0]",
                        message="Consider enabling flow logs",
                        error_code="FLOW_LOGS_RECOMMENDED",
                        severity="WARNING"
                    )
                ]
            )
            mock_validator.return_value = mock_validator_instance
            
            # Mock generator
            mock_generator_instance = Mock()
            mock_generator_instance.generate.return_value = GenerationResult(
                success=True,
                generated_files={"app.py": "# Generated CDK app"},
                errors=[]
            )
            mock_generator.return_value = mock_generator_instance
            
            result = cli_runner.invoke(
                generate,
                ['-c', str(config_file), '-e', 'dev', '-o', str(output_dir)]
            )
            
            assert result.exit_code == 0
            assert "⚠" in result.output
            assert "warning(s)" in result.output


class TestValidateCommand:
    """Tests for the validate command."""
    
    def test_validate_success(self, cli_runner, tmp_path, sample_config):
        """Test successful validation."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.ValidationEngine') as mock_validator:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock validator
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[]
            )
            mock_validator.return_value = mock_validator_instance
            
            result = cli_runner.invoke(
                validate,
                ['-c', str(config_file), '-e', 'dev']
            )
            
            assert result.exit_code == 0
            assert "✓ Validation passed" in result.output
    
    def test_validate_verbose(self, cli_runner, tmp_path, sample_config):
        """Test validation with verbose output."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.ValidationEngine') as mock_validator:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock validator
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[]
            )
            mock_validator.return_value = mock_validator_instance
            
            result = cli_runner.invoke(
                validate,
                ['-c', str(config_file), '-e', 'dev', '-v']
            )
            
            assert result.exit_code == 0
            assert "Configuration Summary" in result.output
            assert "test-project" in result.output
            assert "Resources by Type" in result.output


class TestQueryCommand:
    """Tests for the query command."""
    
    def test_query_table_format(self, cli_runner, sample_resource_metadata):
        """Test query with table format."""
        with patch('cdk_templates.cli.ResourceRegistry') as mock_registry:
            # Mock registry
            mock_registry_instance = Mock()
            mock_registry_instance.query_resources.return_value = [sample_resource_metadata]
            mock_registry.return_value = mock_registry_instance
            
            result = cli_runner.invoke(query, ['--format', 'table'])
            
            assert result.exit_code == 0
            assert "Resource Registry" in result.output
            assert "vpc-123" in result.output
    
    def test_query_json_format(self, cli_runner, sample_resource_metadata):
        """Test query with JSON format."""
        with patch('cdk_templates.cli.ResourceRegistry') as mock_registry:
            # Mock registry
            mock_registry_instance = Mock()
            mock_registry_instance.query_resources.return_value = [sample_resource_metadata]
            mock_registry.return_value = mock_registry_instance
            
            result = cli_runner.invoke(query, ['--format', 'json'])
            
            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert len(output_data) == 1
            assert output_data[0]['resource_id'] == 'vpc-123'
    
    def test_query_with_filters(self, cli_runner, sample_resource_metadata):
        """Test query with filters."""
        with patch('cdk_templates.cli.ResourceRegistry') as mock_registry:
            # Mock registry
            mock_registry_instance = Mock()
            mock_registry_instance.query_resources.return_value = [sample_resource_metadata]
            mock_registry.return_value = mock_registry_instance
            
            result = cli_runner.invoke(
                query,
                ['--type', 'vpc', '--environment', 'dev', '--tag', 'Project=myapp']
            )
            
            assert result.exit_code == 0
    
    def test_query_no_results(self, cli_runner):
        """Test query with no results."""
        with patch('cdk_templates.cli.ResourceRegistry') as mock_registry:
            # Mock registry
            mock_registry_instance = Mock()
            mock_registry_instance.query_resources.return_value = []
            mock_registry.return_value = mock_registry_instance
            
            result = cli_runner.invoke(query, [])
            
            assert result.exit_code == 0
            assert "No resources found" in result.output


class TestDocsCommand:
    """Tests for the docs command."""
    
    def test_docs_markdown(self, cli_runner, tmp_path, sample_config):
        """Test documentation generation in Markdown format."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        output_dir = tmp_path / "docs"
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.DocumentationGenerator') as mock_doc_gen:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock documentation generator
            mock_doc_gen_instance = Mock()
            mock_doc_gen_instance.generate_markdown_docs.return_value = "# Documentation"
            mock_doc_gen_instance.generate_architecture_diagram.return_value = "```mermaid\ngraph TD\n```"
            mock_doc_gen.return_value = mock_doc_gen_instance
            
            result = cli_runner.invoke(
                docs,
                ['-c', str(config_file), '-o', str(output_dir), '--format', 'markdown']
            )
            
            assert result.exit_code == 0
            assert "✓ Documentation generated successfully" in result.output
    
    def test_docs_html(self, cli_runner, tmp_path, sample_config):
        """Test documentation generation in HTML format."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        output_dir = tmp_path / "docs"
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.DocumentationGenerator') as mock_doc_gen:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock documentation generator
            mock_doc_gen_instance = Mock()
            mock_doc_gen_instance.generate_markdown_docs.return_value = "# Documentation"
            mock_doc_gen_instance.generate_architecture_diagram.return_value = "```mermaid\ngraph TD\n```"
            mock_doc_gen_instance.export_to_html.return_value = "<html><body>Documentation</body></html>"
            mock_doc_gen.return_value = mock_doc_gen_instance
            
            result = cli_runner.invoke(
                docs,
                ['-c', str(config_file), '-o', str(output_dir), '--format', 'html']
            )
            
            assert result.exit_code == 0
            assert "✓ Documentation generated successfully" in result.output


class TestCLIErrorHandling:
    """Tests for CLI error handling."""
    
    def test_missing_config_file(self, cli_runner):
        """Test error when config file doesn't exist."""
        result = cli_runner.invoke(
            generate,
            ['-c', 'nonexistent.yaml', '-e', 'dev']
        )
        
        assert result.exit_code != 0
    
    def test_missing_environment(self, cli_runner, tmp_path):
        """Test error when environment is not specified."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        result = cli_runner.invoke(
            generate,
            ['-c', str(config_file)]
        )
        
        assert result.exit_code != 0


class TestCLIOutputFormatting:
    """Tests for CLI output formatting."""
    
    def test_validation_error_formatting(self, cli_runner, tmp_path, sample_config):
        """Test that validation errors are formatted for readability."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.ValidationEngine') as mock_validator:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock validator with multiple errors
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field_path="resources[0].properties.cidr",
                        message="Invalid CIDR block format",
                        error_code="INVALID_CIDR",
                        severity="ERROR"
                    ),
                    ValidationError(
                        field_path="resources[1].properties.instance_type",
                        message="Invalid instance type",
                        error_code="INVALID_INSTANCE_TYPE",
                        severity="ERROR"
                    )
                ],
                warnings=[]
            )
            mock_validator_instance.generate_error_report.return_value = (
                "ERRORS (2):\n"
                "1. [INVALID_CIDR] resources[0].properties.cidr\n"
                "   Invalid CIDR block format\n"
                "2. [INVALID_INSTANCE_TYPE] resources[1].properties.instance_type\n"
                "   Invalid instance type\n"
            )
            mock_validator.return_value = mock_validator_instance
            
            result = cli_runner.invoke(
                validate,
                ['-c', str(config_file), '-e', 'dev']
            )
            
            assert result.exit_code == 1
            assert "ERRORS" in result.output
            assert "INVALID_CIDR" in result.output
    
    def test_progress_display(self, cli_runner, tmp_path, sample_config):
        """Test that progress is displayed during code generation."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        
        output_dir = tmp_path / "output"
        
        with patch('cdk_templates.cli.ConfigurationLoader') as mock_loader, \
             patch('cdk_templates.cli.ValidationEngine') as mock_validator, \
             patch('cdk_templates.cli.TemplateGenerator') as mock_generator:
            
            # Mock configuration loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_config.return_value = sample_config
            mock_loader.return_value = mock_loader_instance
            
            # Mock validator
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[]
            )
            mock_validator.return_value = mock_validator_instance
            
            # Mock generator
            mock_generator_instance = Mock()
            mock_generator_instance.generate.return_value = GenerationResult(
                success=True,
                generated_files={"app.py": "# Generated CDK app"},
                errors=[]
            )
            mock_generator.return_value = mock_generator_instance
            
            result = cli_runner.invoke(
                generate,
                ['-c', str(config_file), '-e', 'dev', '-o', str(output_dir)]
            )
            
            assert result.exit_code == 0
            # Check for progress indicators
            assert "✓" in result.output
