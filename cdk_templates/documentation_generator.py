"""Documentation Generator for CDK AWS Templates System.

This module generates architecture diagrams and documentation from configurations.
"""

from typing import Dict, List, Set
from cdk_templates.models import Configuration, ResourceConfig


class DocumentationGenerator:
    """Generates documentation and architecture diagrams from configurations."""
    
    def generate_architecture_diagram(self, config: Configuration) -> str:
        """Generate Mermaid diagram showing resources and their dependencies.
        
        Args:
            config: The configuration to generate diagram for
            
        Returns:
            Mermaid diagram as a string
        """
        lines = ["graph TB"]
        
        # Create a mapping of resource logical_id to resource
        resource_map = {r.logical_id: r for r in config.resources}
        
        # Add nodes for each resource
        for resource in config.resources:
            node_id = self._sanitize_node_id(resource.logical_id)
            node_label = f"{resource.logical_id}\\n[{resource.resource_type}]"
            lines.append(f"    {node_id}[\"{node_label}\"]")
        
        # Add edges for dependencies
        edges_added: Set[tuple] = set()
        for resource in config.resources:
            source_id = self._sanitize_node_id(resource.logical_id)
            
            # Add explicit dependencies
            for dep in resource.depends_on:
                if dep in resource_map:
                    target_id = self._sanitize_node_id(dep)
                    edge = (source_id, target_id)
                    if edge not in edges_added:
                        lines.append(f"    {source_id} --> {target_id}")
                        edges_added.add(edge)
            
            # Add implicit dependencies from resource references
            implicit_deps = self._extract_resource_references(resource.properties)
            for dep in implicit_deps:
                if dep in resource_map:
                    target_id = self._sanitize_node_id(dep)
                    edge = (source_id, target_id)
                    if edge not in edges_added:
                        lines.append(f"    {source_id} -.-> {target_id}")
                        edges_added.add(edge)
        
        return "\n".join(lines)
    
    def generate_markdown_docs(self, config: Configuration) -> str:
        """Generate comprehensive Markdown documentation.
        
        Args:
            config: The configuration to document
            
        Returns:
            Markdown documentation as a string
        """
        lines = []
        
        # Title and overview
        lines.append(f"# Infrastructure Documentation: {config.metadata.project}")
        lines.append("")
        lines.append(f"**Description:** {config.metadata.description}")
        lines.append(f"**Owner:** {config.metadata.owner}")
        lines.append(f"**Cost Center:** {config.metadata.cost_center}")
        lines.append("")
        
        # Architecture diagram
        lines.append("## Architecture Diagram")
        lines.append("")
        lines.append("```mermaid")
        lines.append(self.generate_architecture_diagram(config))
        lines.append("```")
        lines.append("")
        
        # Environments
        lines.append("## Environments")
        lines.append("")
        for env_name, env_config in config.environments.items():
            lines.append(f"### {env_name}")
            lines.append(f"- **Account ID:** {env_config.account_id}")
            lines.append(f"- **Region:** {env_config.region}")
            if env_config.tags:
                lines.append("- **Tags:**")
                for key, value in env_config.tags.items():
                    lines.append(f"  - {key}: {value}")
            lines.append("")
        
        # Resources
        lines.append("## Resources")
        lines.append("")
        
        for resource in config.resources:
            lines.extend(self._generate_resource_section(resource, config))
            lines.append("")
        
        return "\n".join(lines)
    
    def export_to_html(self, markdown: str) -> str:
        """Convert Markdown documentation to HTML.
        
        Args:
            markdown: Markdown content to convert
            
        Returns:
            HTML content as a string
        """
        # Basic HTML wrapper with styling
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset=\"UTF-8\">",
            "    <title>Infrastructure Documentation</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }",
            "        h1 { color: #232F3E; border-bottom: 2px solid #FF9900; }",
            "        h2 { color: #232F3E; border-bottom: 1px solid #FF9900; margin-top: 30px; }",
            "        h3 { color: #545B64; }",
            "        code { background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; }",
            "        pre { background-color: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }",
            "        table { border-collapse: collapse; width: 100%; margin: 15px 0; }",
            "        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }",
            "        th { background-color: #232F3E; color: white; }",
            "        tr:nth-child(even) { background-color: #f9f9f9; }",
            "        ul { line-height: 1.8; }",
            "    </style>",
            "</head>",
            "<body>",
        ]
        
        # Convert markdown to HTML (basic conversion)
        html_content = self._markdown_to_html(markdown)
        html_parts.append(html_content)
        
        html_parts.extend([
            "</body>",
            "</html>",
        ])
        
        return "\n".join(html_parts)
    
    def export_to_pdf(self, html: str) -> bytes:
        """Convert HTML documentation to PDF.
        
        Note: This is a placeholder implementation. In production, you would use
        a library like weasyprint or pdfkit to convert HTML to PDF.
        
        Args:
            html: HTML content to convert
            
        Returns:
            PDF content as bytes
        """
        # Placeholder: In a real implementation, use weasyprint or similar
        # For now, return a message indicating PDF generation would happen here
        message = (
            "PDF Generation Placeholder\n"
            "=========================\n\n"
            "In a production environment, this would use a library like:\n"
            "- weasyprint: pip install weasyprint\n"
            "- pdfkit: pip install pdfkit (requires wkhtmltopdf)\n\n"
            "The HTML content would be converted to a proper PDF document.\n"
        )
        return message.encode('utf-8')
    
    def _sanitize_node_id(self, logical_id: str) -> str:
        """Sanitize logical ID for use as Mermaid node ID.
        
        Args:
            logical_id: The resource logical ID
            
        Returns:
            Sanitized node ID safe for Mermaid
        """
        # Replace hyphens with underscores for Mermaid compatibility
        return logical_id.replace('-', '_').replace('.', '_')
    
    def _extract_resource_references(self, properties: Dict) -> List[str]:
        """Extract resource references from properties.
        
        Args:
            properties: Resource properties dictionary
            
        Returns:
            List of referenced resource logical IDs
        """
        references = []
        
        def extract_from_value(value):
            if isinstance(value, str):
                # Look for ${resource.logical_id.property} pattern
                if '${resource.' in value:
                    start = value.find('${resource.') + len('${resource.')
                    end = value.find('.', start)
                    if end > start:
                        ref_id = value[start:end]
                        references.append(ref_id)
            elif isinstance(value, dict):
                for v in value.values():
                    extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item)
        
        extract_from_value(properties)
        return references
    
    def _generate_resource_section(self, resource: ResourceConfig, config: Configuration) -> List[str]:
        """Generate documentation section for a single resource.
        
        Args:
            resource: The resource to document
            config: The full configuration for context
            
        Returns:
            List of markdown lines for this resource
        """
        lines = []
        
        # Resource header
        lines.append(f"### {resource.logical_id}")
        lines.append("")
        lines.append(f"**Type:** `{resource.resource_type}`")
        
        # Stack assignment
        if resource.stack:
            lines.append(f"**Stack:** {resource.stack}")
        
        lines.append("")
        
        # Purpose/Description (if available in properties)
        if 'description' in resource.properties:
            lines.append(f"**Purpose:** {resource.properties['description']}")
            lines.append("")
        
        # Configuration
        lines.append("**Configuration:**")
        lines.append("")
        for key, value in resource.properties.items():
            if key != 'description':
                lines.append(f"- **{key}:** `{value}`")
        lines.append("")
        
        # Dependencies
        if resource.depends_on:
            lines.append("**Dependencies:**")
            lines.append("")
            for dep in resource.depends_on:
                lines.append(f"- {dep}")
            lines.append("")
        
        # Implicit dependencies from references
        implicit_deps = self._extract_resource_references(resource.properties)
        if implicit_deps:
            lines.append("**References:**")
            lines.append("")
            for dep in implicit_deps:
                lines.append(f"- {dep}")
            lines.append("")
        
        # Outputs
        if resource.outputs:
            lines.append("**Outputs:**")
            lines.append("")
            for output_name, output_desc in resource.outputs.items():
                lines.append(f"- **{output_name}:** {output_desc}")
            lines.append("")
        
        # Tags
        if resource.tags:
            lines.append("**Tags:**")
            lines.append("")
            for key, value in resource.tags.items():
                lines.append(f"- {key}: {value}")
            lines.append("")
        
        return lines
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML (basic implementation).
        
        Args:
            markdown: Markdown content
            
        Returns:
            HTML content
        """
        lines = markdown.split('\n')
        html_lines = []
        in_code_block = False
        in_list = False
        
        for line in lines:
            # Code blocks
            if line.startswith('```'):
                if in_code_block:
                    html_lines.append('</pre>')
                    in_code_block = False
                else:
                    html_lines.append('<pre><code>')
                    in_code_block = True
                continue
            
            if in_code_block:
                html_lines.append(self._escape_html(line))
                continue
            
            # Headers
            if line.startswith('# '):
                html_lines.append(f'<h1>{self._escape_html(line[2:])}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{self._escape_html(line[3:])}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{self._escape_html(line[4:])}</h3>')
            # Lists
            elif line.startswith('- '):
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                html_lines.append(f'<li>{self._process_inline_markdown(line[2:])}</li>')
            else:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                if line.strip():
                    html_lines.append(f'<p>{self._process_inline_markdown(line)}</p>')
                else:
                    html_lines.append('<br>')
        
        if in_list:
            html_lines.append('</ul>')
        
        return '\n'.join(html_lines)
    
    def _process_inline_markdown(self, text: str) -> str:
        """Process inline markdown (bold, code, etc.).
        
        Args:
            text: Text with inline markdown
            
        Returns:
            HTML with inline formatting
        """
        # Escape HTML first
        text = (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
        
        # Then apply markdown formatting (which creates HTML tags)
        import re
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Code
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
