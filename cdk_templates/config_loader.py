"""Configuration loader for YAML and JSON files."""

import json
import yaml
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Union
from copy import deepcopy

from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
)
from cdk_templates.exceptions import ConfigurationError


class ConfigurationLoader:
    """Loads and processes configuration files in YAML or JSON format."""

    def load_config(self, file_paths: List[str]) -> Configuration:
        """
        Load and combine multiple configuration files.
        
        Args:
            file_paths: List of paths to configuration files (YAML or JSON)
            
        Returns:
            Combined Configuration object
            
        Raises:
            ConfigurationError: If files cannot be loaded or parsed
        """
        if not file_paths:
            raise ConfigurationError("No configuration files provided")
        
        configs = []
        for file_path in file_paths:
            config_dict = self._load_file(file_path)
            configs.append(config_dict)
        
        # Merge all configurations
        merged_dict = self.merge_configs(configs)
        
        # Convert to Configuration object
        config = self._dict_to_configuration(merged_dict)
        
        # Resolve environment variables
        config = self.resolve_variables(config, os.environ)
        
        return config
    
    def merge_configs(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine multiple configuration dictionaries with deep merge strategy.
        
        Later configurations override earlier ones for conflicting keys.
        Lists are replaced (not merged), nested dicts are merged recursively.
        
        Args:
            configs: List of configuration dictionaries
            
        Returns:
            Merged configuration dictionary
        """
        if not configs:
            return {}
        
        result = deepcopy(configs[0])
        
        for config in configs[1:]:
            result = self._deep_merge(result, config)
        
        return result
    
    def resolve_variables(self, config: Configuration, env_vars: Dict[str, str]) -> Configuration:
        """
        Resolve environment variable references in configuration.
        
        Supports two formats:
        - ${ENV_VAR}: Simple variable reference
        - ${ENV_VAR:-default}: Variable with default value
        
        Args:
            config: Configuration object
            env_vars: Dictionary of environment variables
            
        Returns:
            Configuration with resolved variables
        """
        # Convert to dict for easier manipulation
        config_dict = self._configuration_to_dict(config)
        
        # Resolve variables recursively
        resolved_dict = self._resolve_variables_in_dict(config_dict, env_vars)
        
        # Convert back to Configuration object
        return self._dict_to_configuration(resolved_dict)
    
    def apply_environment_overrides(self, config: Configuration, environment: str) -> Configuration:
        """
        Apply environment-specific configuration overrides.
        
        This method takes the base resource configurations and applies
        environment-specific overrides from the EnvironmentConfig.overrides dictionary.
        
        The overrides dictionary can contain:
        - Resource-specific overrides: {"resource_id": {"property": "value"}}
        - Global overrides applied to all resources
        
        Args:
            config: Base configuration object
            environment: Target environment name
            
        Returns:
            Configuration with environment overrides applied
            
        Raises:
            ConfigurationError: If environment doesn't exist
        """
        if environment not in config.environments:
            raise ConfigurationError(f"Environment '{environment}' not found in configuration")
        
        env_config = config.environments[environment]
        
        # If no overrides, return original config
        if not env_config.overrides:
            return config
        
        # Deep copy to avoid modifying original
        modified_config = deepcopy(config)
        
        # Apply overrides to resources
        for resource in modified_config.resources:
            # Check for resource-specific overrides
            resource_overrides = env_config.overrides.get(resource.logical_id, {})
            
            if resource_overrides:
                # Apply property overrides
                if 'properties' in resource_overrides:
                    resource.properties = self._deep_merge(
                        resource.properties,
                        resource_overrides['properties']
                    )
                
                # Apply tag overrides
                if 'tags' in resource_overrides:
                    resource.tags = self._deep_merge(
                        resource.tags,
                        resource_overrides['tags']
                    )
        
        return modified_config
    def serialize_to_yaml(self, config: Configuration) -> str:
        """
        Serialize Configuration object to YAML string.

        Args:
            config: Configuration object to serialize

        Returns:
            YAML string representation
        """
        config_dict = self._configuration_to_dict(config)
        return yaml.dump(config_dict, default_flow_style=False, sort_keys=False)

    def serialize_to_json(self, config: Configuration) -> str:
        """
        Serialize Configuration object to JSON string.

        Args:
            config: Configuration object to serialize

        Returns:
            JSON string representation
        """
        config_dict = self._configuration_to_dict(config)
        return json.dumps(config_dict, indent=2)

    def load_from_yaml_string(self, yaml_str: str) -> Configuration:
        """
        Load Configuration from YAML string.

        Args:
            yaml_str: YAML string

        Returns:
            Configuration object

        Raises:
            ConfigurationError: If YAML is invalid
        """
        try:
            config_dict = yaml.safe_load(yaml_str)
            if config_dict is None:
                raise ConfigurationError("YAML string is empty")
            if not isinstance(config_dict, dict):
                raise ConfigurationError("YAML must contain a dictionary at root level")
            return self._dict_to_configuration(config_dict)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax: {str(e)}")

    def load_from_json_string(self, json_str: str) -> Configuration:
        """
        Load Configuration from JSON string.

        Args:
            json_str: JSON string

        Returns:
            Configuration object

        Raises:
            ConfigurationError: If JSON is invalid
        """
        try:
            config_dict = json.loads(json_str)
            if not isinstance(config_dict, dict):
                raise ConfigurationError("JSON must contain an object at root level")
            return self._dict_to_configuration(config_dict)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON syntax: {str(e)}")
    
    def _resolve_variables_in_dict(self, data: Any, env_vars: Dict[str, str]) -> Any:
        """
        Recursively resolve environment variables in a data structure.
        
        Args:
            data: Data structure (dict, list, str, or other)
            env_vars: Dictionary of environment variables
            
        Returns:
            Data structure with resolved variables
        """
        if isinstance(data, dict):
            return {
                key: self._resolve_variables_in_dict(value, env_vars)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                self._resolve_variables_in_dict(item, env_vars)
                for item in data
            ]
        elif isinstance(data, str):
            return self._resolve_string_variables(data, env_vars)
        else:
            return data
    
    def _resolve_string_variables(self, text: str, env_vars: Dict[str, str]) -> str:
        """
        Resolve environment variable references in a string.
        
        Supports:
        - ${ENV_VAR}: Simple reference
        - ${ENV_VAR:-default}: Reference with default value
        
        Args:
            text: String potentially containing variable references
            env_vars: Dictionary of environment variables
            
        Returns:
            String with resolved variables
        """
        # Pattern matches ${VAR_NAME} or ${VAR_NAME:-default_value}
        pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}'
        
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(3) if match.group(3) is not None else None
            
            # Get value from environment variables
            if var_name in env_vars:
                return env_vars[var_name]
            elif default_value is not None:
                return default_value
            else:
                # Variable not found and no default
                raise ConfigurationError(
                    f"Environment variable '{var_name}' not found and no default value provided"
                )
        
        return re.sub(pattern, replace_var, text)
    
    def _configuration_to_dict(self, config: Configuration) -> Dict[str, Any]:
        """
        Convert Configuration object to dictionary.
        
        Args:
            config: Configuration object
            
        Returns:
            Configuration dictionary
        """
        return {
            'version': config.version,
            'metadata': {
                'project': config.metadata.project,
                'owner': config.metadata.owner,
                'cost_center': config.metadata.cost_center,
                'description': config.metadata.description,
            },
            'environments': {
                name: {
                    'name': env.name,
                    'account_id': env.account_id,
                    'region': env.region,
                    'tags': env.tags,
                    'overrides': env.overrides,
                }
                for name, env in config.environments.items()
            },
            'resources': [
                {
                    'logical_id': resource.logical_id,
                    'resource_type': resource.resource_type,
                    'properties': resource.properties,
                    'tags': resource.tags,
                    'depends_on': resource.depends_on,
                }
                for resource in config.resources
            ],
            'deployment_rules': config.deployment_rules,
        }
    
    def _load_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load a single configuration file (YAML or JSON).
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        path = Path(file_path)
        
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")
        
        try:
            content = path.read_text()
            
            if not content.strip():
                raise ConfigurationError(f"Configuration file is empty: {file_path}")
            
            # Determine format by extension
            suffix = path.suffix.lower()
            
            if suffix in ['.yaml', '.yml']:
                return self._parse_yaml(content, file_path)
            elif suffix == '.json':
                return self._parse_json(content, file_path)
            else:
                # Try to auto-detect format
                return self._auto_parse(content, file_path)
                
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration file {file_path}: {str(e)}"
            )
    
    def _parse_yaml(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse YAML content."""
        try:
            data = yaml.safe_load(content)
            if data is None:
                raise ConfigurationError(f"YAML file is empty: {file_path}")
            if not isinstance(data, dict):
                raise ConfigurationError(
                    f"YAML file must contain a dictionary at root level: {file_path}"
                )
            return data
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML syntax in {file_path}: {str(e)}"
            )
    
    def _parse_json(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse JSON content."""
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ConfigurationError(
                    f"JSON file must contain an object at root level: {file_path}"
                )
            return data
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON syntax in {file_path}: {str(e)}"
            )
    
    def _auto_parse(self, content: str, file_path: str) -> Dict[str, Any]:
        """Auto-detect and parse YAML or JSON content."""
        # Try JSON first (stricter format)
        try:
            return self._parse_json(content, file_path)
        except ConfigurationError:
            pass
        
        # Try YAML
        try:
            return self._parse_yaml(content, file_path)
        except ConfigurationError:
            pass
        
        raise ConfigurationError(
            f"Could not parse {file_path} as YAML or JSON"
        )
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            override: Dictionary with values to override
            
        Returns:
            Merged dictionary
        """
        result = deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override value (including lists)
                result[key] = deepcopy(value)
        
        return result
    
    def _dict_to_configuration(self, config_dict: Dict[str, Any]) -> Configuration:
        """
        Convert configuration dictionary to Configuration object.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Configuration object
            
        Raises:
            ConfigurationError: If required fields are missing
        """
        try:
            # Extract metadata
            metadata_dict = config_dict.get('metadata', {})
            metadata = ConfigMetadata(
                project=metadata_dict.get('project', ''),
                owner=metadata_dict.get('owner', ''),
                cost_center=metadata_dict.get('cost_center', ''),
                description=metadata_dict.get('description', '')
            )
            
            # Extract environments
            environments = {}
            for env_name, env_dict in config_dict.get('environments', {}).items():
                environments[env_name] = EnvironmentConfig(
                    name=env_dict.get('name', env_name),
                    account_id=env_dict.get('account_id', ''),
                    region=env_dict.get('region', ''),
                    tags=env_dict.get('tags', {}),
                    overrides=env_dict.get('overrides', {})
                )
            
            # Extract resources
            resources = []
            for resource_dict in config_dict.get('resources', []):
                resources.append(ResourceConfig(
                    logical_id=resource_dict.get('logical_id', ''),
                    resource_type=resource_dict.get('resource_type', ''),
                    properties=resource_dict.get('properties', {}),
                    tags=resource_dict.get('tags', {}),
                    depends_on=resource_dict.get('depends_on', [])
                ))
            
            return Configuration(
                version=config_dict.get('version', '1.0'),
                metadata=metadata,
                environments=environments,
                resources=resources,
                deployment_rules=config_dict.get('deployment_rules', [])
            )
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to convert configuration dictionary to Configuration object: {str(e)}"
            )
