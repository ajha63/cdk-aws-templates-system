"""CLI Interface for CDK AWS Templates System."""

import sys
import json
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.syntax import Syntax

from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator
from cdk_templates.validation_engine import ValidationEngine
from cdk_templates.resource_registry import ResourceRegistry, ResourceQuery
from cdk_templates.documentation_generator import DocumentationGenerator
from cdk_templates.exceptions import (
    ConfigurationError,
    ValidationException,
    CodeGenerationError
)

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="cdk-templates")
def main():
    """
    CDK AWS Templates System - Declarative infrastructure deployment with AWS CDK.
    
    Generate standardized AWS infrastructure code from YAML/JSON configurations.
    """
    pass


@main.command()
@click.option(
    '--config', '-c',
    multiple=True,
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help='Configuration file(s) to load (can specify multiple)'
)
@click.option(
    '--environment', '-e',
    required=True,
    help='Target environment (dev, staging, prod)'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    default=Path('generated'),
    help='Output directory for generated CDK code'
)
@click.option(
    '--validate-only',
    is_flag=True,
    help='Only validate configuration without generating code'
)
def generate(
    config: tuple[Path, ...],
    environment: str,
    output: Path,
    validate_only: bool
):
    """
    Generate CDK Python code from configuration files.
    
    Examples:
    
        # Generate code for development environment
        cdk-templates generate -c config.yaml -e dev
        
        # Generate with multiple config files
        cdk-templates generate -c base.yaml -c dev.yaml -e dev
        
        # Validate only without generating
        cdk-templates generate -c config.yaml -e dev --validate-only
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Load configuration
            task = progress.add_task("Loading configuration...", total=None)
            loader = ConfigurationLoader()
            configuration = loader.load_config(list(config))
            progress.update(task, description="✓ Configuration loaded")
            progress.stop()
            
            # Validate configuration
            console.print("\n[bold cyan]Validating configuration...[/bold cyan]")
            validator = ValidationEngine()
            validation_result = validator.validate(configuration, environment)
            
            if not validation_result.is_valid:
                report = validator.generate_error_report(validation_result)
                console.print(report)
                console.print("[bold red]✗ Validation failed[/bold red]")
                sys.exit(1)
            
            console.print("[bold green]✓ Validation passed[/bold green]")
            
            # Display warnings if any
            if validation_result.warnings:
                console.print(f"\n[yellow]⚠ {len(validation_result.warnings)} warning(s):[/yellow]")
                for warning in validation_result.warnings:
                    console.print(f"  • {warning.field_path}: {warning.message}")
            
            if validate_only:
                console.print("\n[bold green]✓ Configuration is valid[/bold green]")
                return
            
            # Generate CDK code
            console.print(f"\n[bold cyan]Generating CDK code for environment: {environment}[/bold cyan]")
            generator = TemplateGenerator()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating code...", total=None)
                result = generator.generate(configuration, environment)
                progress.stop()
            
            if not result.success:
                console.print("\n[bold red]✗ Code generation failed:[/bold red]")
                for error in result.errors:
                    console.print(f"  • {error}")
                sys.exit(1)
            
            # Write generated files
            output.mkdir(parents=True, exist_ok=True)
            files_written = 0
            
            for file_path, content in result.generated_files.items():
                full_path = output / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                files_written += 1
            
            console.print(f"\n[bold green]✓ Successfully generated {files_written} file(s)[/bold green]")
            console.print(f"[dim]Output directory: {output.absolute()}[/dim]")
            
            # Show next steps
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print(f"  1. cd {output}")
            console.print("  2. pip install -r requirements.txt")
            console.print("  3. cdk synth")
            console.print("  4. cdk deploy")
            
    except ConfigurationError as e:
        console.print(f"\n[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)
    except ValidationException as e:
        console.print(f"\n[bold red]Validation Error:[/bold red] {e}")
        sys.exit(1)
    except CodeGenerationError as e:
        console.print(f"\n[bold red]Generation Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected Error:[/bold red] {e}")
        if '--debug' in sys.argv:
            raise
        sys.exit(1)


@main.command()
@click.option(
    '--config', '-c',
    multiple=True,
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help='Configuration file(s) to validate'
)
@click.option(
    '--environment', '-e',
    required=True,
    help='Target environment (dev, staging, prod)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Show detailed validation information'
)
def validate(config: tuple[Path, ...], environment: str, verbose: bool):
    """
    Validate configuration files without generating code.
    
    Examples:
    
        # Validate configuration
        cdk-templates validate -c config.yaml -e dev
        
        # Validate with verbose output
        cdk-templates validate -c config.yaml -e dev -v
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Load configuration
            task = progress.add_task("Loading configuration...", total=None)
            loader = ConfigurationLoader()
            configuration = loader.load_config(list(config))
            progress.update(task, description="✓ Configuration loaded")
            progress.stop()
        
        # Validate configuration
        console.print("\n[bold cyan]Validating configuration...[/bold cyan]")
        validator = ValidationEngine()
        validation_result = validator.validate(configuration, environment)
        
        if not validation_result.is_valid:
            report = validator.generate_error_report(validation_result)
            console.print(report)
            console.print("[bold red]✗ Validation failed[/bold red]")
            sys.exit(1)
        
        console.print("[bold green]✓ Validation passed[/bold green]")
        
        # Display warnings if any
        if validation_result.warnings:
            console.print(f"\n[yellow]⚠ {len(validation_result.warnings)} warning(s):[/yellow]")
            for warning in validation_result.warnings:
                console.print(f"  • {warning.field_path}: {warning.message}")
        
        # Show verbose information
        if verbose:
            console.print(f"\n[bold]Configuration Summary:[/bold]")
            console.print(f"  • Project: {configuration.metadata.project}")
            console.print(f"  • Owner: {configuration.metadata.owner}")
            console.print(f"  • Environment: {environment}")
            console.print(f"  • Resources: {len(configuration.resources)}")
            console.print(f"  • Stacks: {len(configuration.stacks)}")
            
            # Show resource breakdown
            resource_types = {}
            for resource in configuration.resources:
                resource_types[resource.resource_type] = resource_types.get(resource.resource_type, 0) + 1
            
            console.print("\n[bold]Resources by Type:[/bold]")
            for rtype, count in sorted(resource_types.items()):
                console.print(f"  • {rtype}: {count}")
        
    except ConfigurationError as e:
        console.print(f"\n[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected Error:[/bold red] {e}")
        if '--debug' in sys.argv:
            raise
        sys.exit(1)


@main.command()
@click.option(
    '--registry', '-r',
    type=click.Path(path_type=Path),
    help='Path to resource registry file'
)
@click.option(
    '--type', '-t',
    help='Filter by resource type (vpc, ec2, rds, s3)'
)
@click.option(
    '--environment', '-e',
    help='Filter by environment'
)
@click.option(
    '--stack', '-s',
    help='Filter by stack name'
)
@click.option(
    '--tag',
    multiple=True,
    help='Filter by tag (format: key=value)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['table', 'json', 'yaml']),
    default='table',
    help='Output format'
)
def query(
    registry: Optional[Path],
    type: Optional[str],
    environment: Optional[str],
    stack: Optional[str],
    tag: tuple[str, ...],
    format: str
):
    """
    Query the Resource Registry for deployed resources.
    
    Examples:
    
        # List all resources
        cdk-templates query
        
        # Query VPC resources in production
        cdk-templates query --type vpc --environment prod
        
        # Query resources with specific tag
        cdk-templates query --tag Project=myapp
        
        # Export as JSON
        cdk-templates query --format json
    """
    try:
        # Initialize registry
        resource_registry = ResourceRegistry(str(registry) if registry else None)
        
        # Parse tags
        tag_filters = {}
        for tag_str in tag:
            if '=' not in tag_str:
                console.print(f"[yellow]Warning: Invalid tag format '{tag_str}', expected 'key=value'[/yellow]")
                continue
            key, value = tag_str.split('=', 1)
            tag_filters[key] = value
        
        # Build query
        query_obj = ResourceQuery(
            resource_type=type,
            environment=environment,
            stack_name=stack,
            tags=tag_filters if tag_filters else None
        )
        
        # Execute query
        resources = resource_registry.query_resources(query_obj)
        
        if not resources:
            console.print("[yellow]No resources found matching the query.[/yellow]")
            return
        
        # Format output
        if format == 'json':
            output = []
            for resource in resources:
                output.append({
                    'resource_id': resource.resource_id,
                    'resource_type': resource.resource_type,
                    'logical_name': resource.logical_name,
                    'physical_name': resource.physical_name,
                    'stack_name': resource.stack_name,
                    'environment': resource.environment,
                    'tags': resource.tags,
                    'outputs': resource.outputs,
                    'dependencies': resource.dependencies,
                    'created_at': resource.created_at.isoformat(),
                    'updated_at': resource.updated_at.isoformat()
                })
            console.print(json.dumps(output, indent=2))
        
        elif format == 'yaml':
            import yaml
            output = []
            for resource in resources:
                output.append({
                    'resource_id': resource.resource_id,
                    'resource_type': resource.resource_type,
                    'logical_name': resource.logical_name,
                    'physical_name': resource.physical_name,
                    'stack_name': resource.stack_name,
                    'environment': resource.environment,
                    'tags': resource.tags,
                    'outputs': resource.outputs,
                    'dependencies': resource.dependencies,
                    'created_at': resource.created_at.isoformat(),
                    'updated_at': resource.updated_at.isoformat()
                })
            console.print(yaml.dump(output, default_flow_style=False))
        
        else:  # table format
            table = Table(title=f"Resource Registry ({len(resources)} resources)")
            table.add_column("Resource ID", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Stack", style="yellow")
            table.add_column("Environment", style="magenta")
            table.add_column("Physical Name", style="blue")
            
            for resource in resources:
                table.add_row(
                    resource.resource_id,
                    resource.resource_type,
                    resource.stack_name,
                    resource.environment,
                    resource.physical_name
                )
            
            console.print(table)
            
            # Show summary
            console.print(f"\n[dim]Total: {len(resources)} resource(s)[/dim]")
    
    except Exception as e:
        console.print(f"\n[bold red]Query Error:[/bold red] {e}")
        if '--debug' in sys.argv:
            raise
        sys.exit(1)


@main.command()
@click.option(
    '--config', '-c',
    multiple=True,
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help='Configuration file(s) to document'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    default=Path('docs'),
    help='Output directory for documentation'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['markdown', 'html', 'all']),
    default='markdown',
    help='Documentation format'
)
@click.option(
    '--include-diagram',
    is_flag=True,
    default=True,
    help='Include architecture diagram'
)
def docs(
    config: tuple[Path, ...],
    output: Path,
    format: str,
    include_diagram: bool
):
    """
    Generate documentation from configuration files.
    
    Examples:
    
        # Generate Markdown documentation
        cdk-templates docs -c config.yaml
        
        # Generate HTML documentation
        cdk-templates docs -c config.yaml --format html
        
        # Generate all formats
        cdk-templates docs -c config.yaml --format all
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Load configuration
            task = progress.add_task("Loading configuration...", total=None)
            loader = ConfigurationLoader()
            configuration = loader.load_config(list(config))
            progress.update(task, description="✓ Configuration loaded")
            
            # Generate documentation
            progress.update(task, description="Generating documentation...")
            doc_generator = DocumentationGenerator()
            
            # Create output directory
            output.mkdir(parents=True, exist_ok=True)
            
            # Generate Markdown
            if format in ['markdown', 'all']:
                markdown_content = doc_generator.generate_markdown_docs(configuration)
                
                if include_diagram:
                    diagram = doc_generator.generate_architecture_diagram(configuration)
                    markdown_content = f"{diagram}\n\n{markdown_content}"
                
                markdown_path = output / 'infrastructure.md'
                markdown_path.write_text(markdown_content)
                progress.update(task, description=f"✓ Generated {markdown_path}")
            
            # Generate HTML
            if format in ['html', 'all']:
                if format == 'html':
                    markdown_content = doc_generator.generate_markdown_docs(configuration)
                    if include_diagram:
                        diagram = doc_generator.generate_architecture_diagram(configuration)
                        markdown_content = f"{diagram}\n\n{markdown_content}"
                
                html_content = doc_generator.export_to_html(markdown_content)
                html_path = output / 'infrastructure.html'
                html_path.write_text(html_content)
                progress.update(task, description=f"✓ Generated {html_path}")
            
            progress.stop()
        
        console.print(f"\n[bold green]✓ Documentation generated successfully[/bold green]")
        console.print(f"[dim]Output directory: {output.absolute()}[/dim]")
        
        # List generated files
        console.print("\n[bold]Generated files:[/bold]")
        for file in output.iterdir():
            if file.is_file():
                console.print(f"  • {file.name}")
    
    except ConfigurationError as e:
        console.print(f"\n[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Documentation Error:[/bold red] {e}")
        if '--debug' in sys.argv:
            raise
        sys.exit(1)


if __name__ == '__main__':
    main()
