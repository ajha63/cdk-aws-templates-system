"""Unit tests for ConfigurationLoader."""

import pytest
import tempfile
import os
from pathlib import Path

from cdk_templates.config_loader import ConfigurationLoader, ConfigurationError
from cdk_templates.models import Configuration


class TestConfigurationLoader:
    """Test suite for ConfigurationLoader class."""

    def test_load_yaml_file(self):
        """Test loading a valid YAML configuration file."""
        loader = ConfigurationLoader()
        
        yaml_content = """
version: "1.0"
metadata:
  project: test-project
  owner: test-team
  cost_center: engineering
  description: Test configuration
environments:
  dev:
    name: dev
    account_id: "123456789012"
    region: us-east-1
    tags:
      Environment: dev
resources:
  - logical_id: vpc-main
    resource_type: vpc
    properties:
      cidr: "10.0.0.0/16"
      availability_zones: 3
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            config = loader.load_config([temp_path])
            
            assert config.version == "1.0"
            assert config.metadata.project == "test-project"
            assert config.metadata.owner == "test-team"
            assert "dev" in config.environments
            assert config.environments["dev"].region == "us-east-1"
            assert len(config.resources) == 1
            assert config.resources[0].logical_id == "vpc-main"
            assert config.resources[0].properties["cidr"] == "10.0.0.0/16"
        finally:
            os.unlink(temp_path)

    def test_load_json_file(self):
        """Test loading a valid JSON configuration file."""
        loader = ConfigurationLoader()
        
        json_content = """{
  "version": "1.0",
  "metadata": {
    "project": "test-project",
    "owner": "test-team",
    "cost_center": "engineering",
    "description": "Test configuration"
  },
  "environments": {
    "dev": {
      "name": "dev",
      "account_id": "123456789012",
      "region": "us-east-1",
      "tags": {}
    }
  },
  "resources": [
    {
      "logical_id": "vpc-main",
      "resource_type": "vpc",
      "properties": {
        "cidr": "10.0.0.0/16"
      }
    }
  ]
}"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_content)
            temp_path = f.name
        
        try:
            config = loader.load_config([temp_path])
            
            assert config.version == "1.0"
            assert config.metadata.project == "test-project"
            assert len(config.resources) == 1
            assert config.resources[0].logical_id == "vpc-main"
        finally:
            os.unlink(temp_path)

    def test_merge_multiple_configs(self):
        """Test merging multiple configuration files."""
        loader = ConfigurationLoader()
        
        base_config = """
version: "1.0"
metadata:
  project: test-project
  owner: test-team
  cost_center: engineering
  description: Base configuration
environments:
  dev:
    name: dev
    account_id: "123456789012"
    region: us-east-1
resources:
  - logical_id: vpc-main
    resource_type: vpc
    properties:
      cidr: "10.0.0.0/16"
"""
        
        override_config = """
metadata:
  description: Override configuration
environments:
  dev:
    region: us-west-2
resources:
  - logical_id: vpc-main
    resource_type: vpc
    properties:
      cidr: "10.1.0.0/16"
      availability_zones: 3
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f1:
            f1.write(base_config)
            temp_path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f2:
            f2.write(override_config)
            temp_path2 = f2.name
        
        try:
            config = loader.load_config([temp_path1, temp_path2])
            
            # Check that override worked
            assert config.metadata.description == "Override configuration"
            assert config.metadata.project == "test-project"  # Not overridden
            assert config.environments["dev"].region == "us-west-2"  # Overridden
            assert config.resources[0].properties["cidr"] == "10.1.0.0/16"  # Overridden
            assert config.resources[0].properties["availability_zones"] == 3  # Added
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)

    def test_resolve_environment_variables(self):
        """Test resolving environment variable references."""
        loader = ConfigurationLoader()
        
        # Set test environment variables
        os.environ['TEST_REGION'] = 'us-west-1'
        os.environ['TEST_ACCOUNT'] = '999888777666'
        
        yaml_content = """
version: "1.0"
metadata:
  project: test-project
  owner: test-team
  cost_center: engineering
  description: Test with env vars
environments:
  dev:
    name: dev
    account_id: "${TEST_ACCOUNT}"
    region: "${TEST_REGION}"
resources:
  - logical_id: vpc-main
    resource_type: vpc
    properties:
      cidr: "10.0.0.0/16"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            config = loader.load_config([temp_path])
            
            assert config.environments["dev"].account_id == "999888777666"
            assert config.environments["dev"].region == "us-west-1"
        finally:
            os.unlink(temp_path)
            # Clean up environment variables
            del os.environ['TEST_REGION']
            del os.environ['TEST_ACCOUNT']

    def test_resolve_environment_variables_with_defaults(self):
        """Test resolving environment variables with default values."""
        loader = ConfigurationLoader()
        
        yaml_content = """
version: "1.0"
metadata:
  project: test-project
  owner: test-team
  cost_center: engineering
  description: Test with defaults
environments:
  dev:
    name: dev
    account_id: "${MISSING_VAR:-123456789012}"
    region: "${ALSO_MISSING:-us-east-1}"
resources: []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            config = loader.load_config([temp_path])
            
            # Should use default values
            assert config.environments["dev"].account_id == "123456789012"
            assert config.environments["dev"].region == "us-east-1"
        finally:
            os.unlink(temp_path)

    def test_missing_environment_variable_without_default(self):
        """Test that missing environment variable without default raises error."""
        loader = ConfigurationLoader()
        
        yaml_content = """
version: "1.0"
metadata:
  project: test-project
  owner: test-team
  cost_center: engineering
  description: Test
environments:
  dev:
    name: dev
    account_id: "${NONEXISTENT_VAR}"
    region: us-east-1
resources: []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                loader.load_config([temp_path])
            
            assert "NONEXISTENT_VAR" in str(exc_info.value)
            assert "not found" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_empty_file_raises_error(self):
        """Test that empty configuration file raises error."""
        loader = ConfigurationLoader()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                loader.load_config([temp_path])
            
            assert "empty" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)

    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises error."""
        loader = ConfigurationLoader()
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load_config(["/nonexistent/path/config.yaml"])
        
        assert "not found" in str(exc_info.value).lower()

    def test_invalid_yaml_syntax_raises_error(self):
        """Test that invalid YAML syntax raises error."""
        loader = ConfigurationLoader()
        
        invalid_yaml = """
version: "1.0"
metadata:
  project: test
  owner: [invalid yaml structure
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                loader.load_config([temp_path])
            
            assert "yaml" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)

    def test_invalid_json_syntax_raises_error(self):
        """Test that invalid JSON syntax raises error."""
        loader = ConfigurationLoader()
        
        invalid_json = """
{
  "version": "1.0",
  "metadata": {
    "project": "test"
  }
  missing comma here
}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(invalid_json)
            temp_path = f.name
        
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                loader.load_config([temp_path])
            
            assert "json" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)

    def test_no_files_provided_raises_error(self):
        """Test that providing no files raises error."""
        loader = ConfigurationLoader()
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load_config([])
        
        assert "no configuration files" in str(exc_info.value).lower()
