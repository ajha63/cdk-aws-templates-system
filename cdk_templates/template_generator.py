"""Template Generator for orchestrating CDK code generation."""

import ast
from typing import Dict, List, Set, Optional
from cdk_templates.models import (
    Configuration,
    ResourceConfig,
    GenerationResult
)
from cdk_templates.naming_service import NamingConventionService
from cdk_templates.tagging_service import TaggingStrategyService
from cdk_templates.resource_registry import ResourceRegistry
from cdk_templates.deployment_rules import DeploymentRulesEngine
from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.templates.base import GenerationContext
from cdk_templates.templates.vpc_template import VPCTemplate
from cdk_templates.templates.ec2_template import EC2Template
from cdk_templates.templates.rds_template import RDSTemplate
from cdk_templates.templates.s3_template import S3Template
from cdk_templates.documentation_generator import DocumentationGenerator


class TemplateGenerator:
    """Orchestrates the full CDK code generation process."""
    
    def __init__(
        self,
        naming_service: NamingConventionService = None,
        tagging_service: TaggingStrategyService = None,
        resource_registry: ResourceRegistry = None,
        rules_engine: DeploymentRulesEngine = None,
        link_resolver: ResourceLinkResolver = None,
        config_loader: ConfigurationLoader = None,
        documentation_generator: DocumentationGenerator = None
    ):
        """
        Initialize the template generator.
        
        Args:
            naming_service: Service for generating resource names
            tagging_service: Service for applying tags (will be created from config if not provided)
            resource_registry: Registry for tracking resources
            rules_engine: Engine for applying deployment rules
            link_resolver: Resolver for resource links
            config_loader: Loader for applying environment overrides
            documentation_generator: Generator for creating documentation
        """
        self.naming_service = naming_service or NamingConventionService()
        self.tagging_service = tagging_service  # Will be created from config metadata if None
        self.resource_registry = resource_registry or ResourceRegistry()
        self.rules_engine = rules_engine or DeploymentRulesEngine()
        self.link_resolver = link_resolver or ResourceLinkResolver()
        self.config_loader = config_loader or ConfigurationLoader()
        self.documentation_generator = documentation_generator or DocumentationGenerator()
        
        # Template registry
        self.templates = {
            'vpc': VPCTemplate(),
            'ec2': EC2Template(),
            'rds': RDSTemplate(),
            's3': S3Template()
        }
    
    def generate(self, config: Configuration, environment: str = None) -> GenerationResult:
        """
        Generate complete CDK code from configuration.
        
        This method orchestrates the full code generation process:
        1. Apply environment-specific overrides
        2. Apply deployment rules
        3. Resolve resource links
        4. Generate code for each resource
        5. Create file structure (app.py, stacks/, resources/)
        6. Format code and add comments
        
        Args:
            config: Configuration object with all resources
            environment: Target environment (uses first environment if not specified)
            
        Returns:
            GenerationResult with success status, generated files, and errors
        """
        result = GenerationResult(success=True)
        
        # Determine environment
        if environment is None:
            if not config.environments:
                result.success = False
                result.errors.append("No environments defined in configuration")
                return result
            environment = list(config.environments.keys())[0]
        
        if environment not in config.environments:
            result.success = False
            result.errors.append(f"Environment '{environment}' not found in configuration")
            return result
        
        env_config = config.environments[environment]
        
        # Create tagging service if not provided
        if self.tagging_service is None:
            self.tagging_service = TaggingStrategyService(config.metadata)
        
        # Step 1: Apply environment-specific overrides
        try:
            config = self.config_loader.apply_environment_overrides(config, environment)
        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to apply environment overrides: {str(e)}")
            return result
        
        # Step 2: Apply deployment rules
        rules_result = self.rules_engine.apply_rules(config, environment)
        if not rules_result.success:
            result.success = False
            result.errors.extend(rules_result.errors)
            for rejection in rules_result.rejections:
                result.errors.append(
                    f"Rule '{rejection.rule_name}' rejected resource '{rejection.resource_id}': "
                    f"{rejection.reason}"
                )
            return result
        
        # Step 3: Resolve resource links
        link_result = self.link_resolver.resolve_links(config)
        if not link_result.success:
            result.success = False
            result.errors.extend(link_result.errors)
            return result
        
        # Step 4: Generate code for each resource
        try:
            # Create generation context
            context = GenerationContext(
                environment=environment,
                region=env_config.region,
                account_id=env_config.account_id,
                naming_service=self.naming_service,
                tagging_service=self.tagging_service,
                resource_registry=self.resource_registry,
                resolved_links=link_result.resolved_links
            )
            
            # Generate stack code
            stack_code = self.generate_stack(config, context)
            
            # Step 5: Create file structure
            files = self._create_file_structure(config, stack_code, context)
            result.generated_files = files
            
            # Step 6: Validate generated Python code
            validation_errors = self._validate_generated_code(files)
            if validation_errors:
                result.success = False
                result.errors.extend(validation_errors)
                return result
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Code generation failed: {str(e)}")
            return result
        
        return result
    
    def generate_stack(self, config: Configuration, context: GenerationContext) -> str:
        """
        Generate code for a single stack.
        
        Args:
            config: Configuration object
            context: Generation context
            
        Returns:
            Generated CDK Python code as a string
        """
        code_lines = []
        
        # Add imports
        imports = self.generate_imports(config.resources)
        code_lines.extend(imports)
        code_lines.append("")
        
        # Add stack class definition
        stack_name = f"{config.metadata.project.replace('-', '_').title()}Stack"
        code_lines.append(f"class {stack_name}(cdk.Stack):")
        code_lines.append('    """CDK Stack generated by CDK AWS Templates System."""')
        code_lines.append("")
        code_lines.append("    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:")
        code_lines.append("        super().__init__(scope, construct_id, **kwargs)")
        code_lines.append("")
        
        # Sort resources by dependency order
        try:
            graph = self.link_resolver.build_dependency_graph(config)
            resource_order = self.link_resolver.topological_sort(graph)
        except ValueError:
            # If topological sort fails, use original order
            resource_order = [r.logical_id for r in config.resources]
        
        # Generate code for each resource in dependency order
        for resource_id in resource_order:
            # Find the resource config
            resource_config = next(
                (r for r in config.resources if r.logical_id == resource_id),
                None
            )
            
            if resource_config is None:
                continue
            
            # Get the appropriate template
            template = self.templates.get(resource_config.resource_type)
            if template is None:
                continue
            
            # Generate resource code
            resource_dict = {
                'logical_id': resource_config.logical_id,
                'properties': resource_config.properties,
                'tags': resource_config.tags
            }
            
            resource_code = template.generate_code(resource_dict, context)
            
            # Indent the resource code
            for line in resource_code.split('\n'):
                if line.strip():
                    code_lines.append(f"        {line}")
                else:
                    code_lines.append("")
            
            # Generate outputs for this resource if defined
            if resource_config.outputs:
                output_code = self._generate_outputs(resource_config, context)
                for line in output_code.split('\n'):
                    if line.strip():
                        code_lines.append(f"        {line}")
                    else:
                        code_lines.append("")
        
        return '\n'.join(code_lines)
    
    def generate_imports(self, resources: List[ResourceConfig]) -> List[str]:
        """
        Generate necessary import statements for CDK constructs.
        
        Args:
            resources: List of resource configurations
            
        Returns:
            List of import statement strings
        """
        imports = []
        
        # Standard imports
        imports.append("import aws_cdk as cdk")
        imports.append("from aws_cdk import (")
        
        # Determine which CDK modules are needed
        needed_modules = set()
        
        for resource in resources:
            if resource.resource_type == 'vpc':
                needed_modules.add('aws_ec2 as ec2')
                needed_modules.add('aws_logs as logs')
            elif resource.resource_type == 'ec2':
                needed_modules.add('aws_ec2 as ec2')
                needed_modules.add('aws_iam as iam')
            elif resource.resource_type == 'rds':
                needed_modules.add('aws_rds as rds')
                needed_modules.add('aws_ec2 as ec2')
                needed_modules.add('aws_kms as kms')
                needed_modules.add('aws_secretsmanager as secretsmanager')
            elif resource.resource_type == 's3':
                needed_modules.add('aws_s3 as s3')
                needed_modules.add('aws_iam as iam')
        
        # Add modules in sorted order
        for module in sorted(needed_modules):
            imports.append(f"    {module},")
        
        imports.append(")")
        imports.append("from constructs import Construct")
        
        # Add json import if RDS is present (for secrets)
        if any(r.resource_type == 'rds' for r in resources):
            imports.append("import json")
        
        return imports
    
    def _create_file_structure(
        self,
        config: Configuration,
        stack_code: str,
        context: GenerationContext
    ) -> Dict[str, str]:
        """
        Create the CDK project file structure.
        
        Creates:
        - app.py at root
        - stacks/main_stack.py for stack code
        - docs/architecture.md for documentation
        - docs/architecture.html for HTML documentation
        
        Args:
            config: Configuration object
            stack_code: Generated stack code
            context: Generation context
            
        Returns:
            Dictionary mapping file paths to their contents
        """
        files = {}
        
        # Create app.py
        app_code = self._generate_app_py(config, context)
        # Add header comment and format
        app_code_with_header = self._add_file_header_comment('app.py', config) + app_code
        files['app.py'] = self._format_code(app_code_with_header)
        
        # Create stack file
        stack_filename = f"{config.metadata.project.replace('-', '_')}_stack.py"
        # Add header comment and format
        stack_code_with_header = self._add_file_header_comment(f'stacks/{stack_filename}', config) + stack_code
        files[f'stacks/{stack_filename}'] = self._format_code(stack_code_with_header)
        
        # Create __init__.py for stacks package
        files['stacks/__init__.py'] = ''
        
        # Generate documentation
        markdown_docs = self.documentation_generator.generate_markdown_docs(config)
        files['docs/architecture.md'] = markdown_docs
        
        # Generate HTML documentation
        html_docs = self.documentation_generator.export_to_html(markdown_docs)
        files['docs/architecture.html'] = html_docs
        
        return files
    
    def _generate_app_py(self, config: Configuration, context: GenerationContext) -> str:
        """
        Generate the app.py file that instantiates the CDK app and stack.
        
        Args:
            config: Configuration object
            context: Generation context
            
        Returns:
            Content of app.py as a string
        """
        lines = []
        
        lines.append("#!/usr/bin/env python3")
        lines.append("")
        lines.append("import aws_cdk as cdk")
        
        # Import the stack
        stack_module = f"{config.metadata.project.replace('-', '_')}_stack"
        stack_class = f"{config.metadata.project.replace('-', '_').title()}Stack"
        lines.append(f"from stacks.{stack_module} import {stack_class}")
        lines.append("")
        
        # Create app
        lines.append("app = cdk.App()")
        lines.append("")
        
        # Create stack instance
        stack_id = f"{config.metadata.project}-{context.environment}"
        lines.append(f"# Create stack for {context.environment} environment")
        lines.append(f"{stack_class}(")
        lines.append("    app,")
        lines.append(f"    '{stack_id}',")
        lines.append(f"    env=cdk.Environment(")
        lines.append(f"        account='{context.account_id}',")
        lines.append(f"        region='{context.region}'")
        lines.append("    ),")
        lines.append(f"    description='CDK stack for {config.metadata.project} in {context.environment}'")
        lines.append(")")
        lines.append("")
        
        # Synthesize
        lines.append("app.synth()")
        
        return '\n'.join(lines)
    
    def _validate_generated_code(self, files: Dict[str, str]) -> List[str]:
        """
        Validate that generated Python code is syntactically correct.
        
        Args:
            files: Dictionary of file paths to contents
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        for file_path, content in files.items():
            if not file_path.endswith('.py'):
                continue
            
            try:
                ast.parse(content)
            except SyntaxError as e:
                errors.append(
                    f"Syntax error in generated file '{file_path}' at line {e.lineno}: {e.msg}"
                )
        
        return errors
    
    def _format_code(self, code: str) -> str:
        """
        Format Python code using black formatter.
        
        Falls back to original code if black is not available or formatting fails.
        
        Args:
            code: Python code to format
            
        Returns:
            Formatted Python code
        """
        try:
            import black
            
            # Format using black with default settings
            mode = black.Mode(
                line_length=88,
                string_normalization=True,
                is_pyi=False
            )
            
            formatted = black.format_str(code, mode=mode)
            return formatted
        except ImportError:
            # Black not installed, return original code
            return code
        except Exception:
            # Formatting failed, return original code
            return code
    
    def _add_file_header_comment(self, file_path: str, config: Configuration) -> str:
        """
        Generate a header comment for a generated file.
        
        Args:
            file_path: Path of the file
            config: Configuration object
            
        Returns:
            Header comment as a string
        """
        lines = []
        lines.append('"""')
        lines.append(f"Generated by CDK AWS Templates System")
        lines.append(f"Project: {config.metadata.project}")
        lines.append(f"Description: {config.metadata.description}")
        lines.append(f"Owner: {config.metadata.owner}")
        lines.append("")
        lines.append("DO NOT EDIT THIS FILE MANUALLY")
        lines.append("This file is auto-generated from configuration files.")
        lines.append('"""')
        lines.append("")
        return '\n'.join(lines)
    
    def _generate_outputs(self, resource_config: ResourceConfig, context: GenerationContext) -> str:
        """
        Generate CfnOutput constructs for a resource's outputs.
        
        Args:
            resource_config: Resource configuration with outputs defined
            context: Generation context
            
        Returns:
            Generated CfnOutput code as a string
        """
        lines = []
        
        # Get the template to determine what outputs are available
        template = self.templates.get(resource_config.resource_type)
        if template is None:
            return ""
        
        # Get available outputs from the template
        resource_dict = {
            'logical_id': resource_config.logical_id,
            'properties': resource_config.properties,
            'tags': resource_config.tags
        }
        available_outputs = template.get_outputs(resource_dict)
        
        # Generate CfnOutput for each configured output
        for output_name, description in resource_config.outputs.items():
            if output_name not in available_outputs:
                # Skip outputs that aren't available for this resource
                continue
            
            # Generate export name for cross-stack references
            export_name = self._generate_export_name(
                resource_config.logical_id,
                output_name,
                context.environment
            )
            
            # Get the value expression from the template
            value_expr = available_outputs[output_name]
            
            lines.append("")
            lines.append(f"# Export {output_name} for cross-stack references")
            lines.append(f"cdk.CfnOutput(")
            lines.append(f"    self,")
            lines.append(f"    '{resource_config.logical_id}_{output_name}',")
            lines.append(f"    value={value_expr},")
            lines.append(f"    description='{description}',")
            lines.append(f"    export_name='{export_name}'")
            lines.append(f")")
        
        return '\n'.join(lines)
    
    def _generate_export_name(self, logical_id: str, output_name: str, environment: str) -> str:
        """
        Generate a unique export name for cross-stack references.
        
        Export names must be unique within a region and account.
        Format: {environment}-{logical_id}-{output_name}
        
        Args:
            logical_id: Logical ID of the resource
            output_name: Name of the output
            environment: Target environment
            
        Returns:
            Export name string
        """
        return f"{environment}-{logical_id}-{output_name}"
    
    def resolve_cross_stack_reference(self, reference: str, context: GenerationContext) -> str:
        """
        Resolve a cross-stack reference to a Fn.importValue call.
        
        Args:
            reference: Cross-stack reference string (e.g., "${stack.vpc-stack.id}")
            context: Generation context
            
        Returns:
            CDK code for importing the value
        """
        # Extract stack_id and output_name from reference
        match = self.link_resolver.CROSS_STACK_PATTERN.match(reference)
        if not match:
            return reference
        
        stack_id, output_name = match.groups()
        
        # Generate the export name that was used when exporting
        export_name = self._generate_export_name(stack_id, output_name, context.environment)
        
        # Return Fn.importValue call
        return f"cdk.Fn.import_value('{export_name}')"
