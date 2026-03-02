"""Unit tests for DocumentationGenerator."""

import pytest
from cdk_templates.documentation_generator import DocumentationGenerator
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig
)


class TestDocumentationGenerator:
    """Test suite for DocumentationGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = DocumentationGenerator()
        
        # Create a sample configuration
        self.config = Configuration(
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
                    tags={"Environment": "dev"},
                    overrides={}
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        "cidr": "10.0.0.0/16",
                        "availability_zones": 3
                    },
                    tags={"Name": "main-vpc"},
                    depends_on=[]
                ),
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "instance_type": "t3.medium",
                        "vpc_ref": "${resource.vpc-main.id}"
                    },
                    tags={"Name": "web-server"},
                    depends_on=["vpc-main"]
                )
            ]
        )
    
    def test_generate_architecture_diagram_basic(self):
        """Test basic Mermaid diagram generation."""
        diagram = self.generator.generate_architecture_diagram(self.config)
        
        # Check diagram starts with graph declaration
        assert diagram.startswith("graph TB")
        
        # Check nodes are present
        assert "vpc_main" in diagram
        assert "ec2_web" in diagram
        
        # Check node labels
        assert "[vpc]" in diagram
        assert "[ec2]" in diagram
    
    def test_generate_architecture_diagram_with_dependencies(self):
        """Test diagram includes dependency edges."""
        diagram = self.generator.generate_architecture_diagram(self.config)
        
        # Check explicit dependency
        assert "ec2_web --> vpc_main" in diagram
    
    def test_generate_architecture_diagram_with_implicit_references(self):
        """Test diagram includes implicit dependencies from resource references."""
        diagram = self.generator.generate_architecture_diagram(self.config)
        
        # Check that dependency is shown (explicit takes precedence over implicit)
        assert "ec2_web --> vpc_main" in diagram
    
    def test_generate_markdown_docs_structure(self):
        """Test Markdown documentation has correct structure."""
        docs = self.generator.generate_markdown_docs(self.config)
        
        # Check main sections
        assert "# Infrastructure Documentation: test-project" in docs
        assert "## Architecture Diagram" in docs
        assert "## Environments" in docs
        assert "## Resources" in docs
    
    def test_generate_markdown_docs_metadata(self):
        """Test Markdown documentation includes metadata."""
        docs = self.generator.generate_markdown_docs(self.config)
        
        assert "**Description:** Test infrastructure" in docs
        assert "**Owner:** test-team" in docs
        assert "**Cost Center:** engineering" in docs
    
    def test_generate_markdown_docs_environments(self):
        """Test Markdown documentation includes environment details."""
        docs = self.generator.generate_markdown_docs(self.config)
        
        assert "### dev" in docs
        assert "**Account ID:** 123456789012" in docs
        assert "**Region:** us-east-1" in docs
    
    def test_generate_markdown_docs_resources(self):
        """Test Markdown documentation includes resource details."""
        docs = self.generator.generate_markdown_docs(self.config)
        
        # Check VPC resource
        assert "### vpc-main" in docs
        assert "**Type:** `vpc`" in docs
        assert "**cidr:** `10.0.0.0/16`" in docs
        
        # Check EC2 resource
        assert "### ec2-web" in docs
        assert "**Type:** `ec2`" in docs
        assert "**instance_type:** `t3.medium`" in docs
    
    def test_generate_markdown_docs_dependencies(self):
        """Test Markdown documentation includes dependencies."""
        docs = self.generator.generate_markdown_docs(self.config)
        
        # EC2 should show dependency on VPC
        assert "**Dependencies:**" in docs
        assert "- vpc-main" in docs
    
    def test_generate_markdown_docs_references(self):
        """Test Markdown documentation includes resource references."""
        docs = self.generator.generate_markdown_docs(self.config)
        
        # EC2 should show reference to VPC
        assert "**References:**" in docs
    
    def test_generate_markdown_docs_with_outputs(self):
        """Test Markdown documentation includes resource outputs."""
        # Add outputs to a resource
        self.config.resources[0].outputs = {
            "VpcId": "The VPC ID",
            "VpcCidr": "The VPC CIDR block"
        }
        
        docs = self.generator.generate_markdown_docs(self.config)
        
        assert "**Outputs:**" in docs
        assert "**VpcId:** The VPC ID" in docs
        assert "**VpcCidr:** The VPC CIDR block" in docs
    
    def test_generate_markdown_docs_with_tags(self):
        """Test Markdown documentation includes resource tags."""
        docs = self.generator.generate_markdown_docs(self.config)
        
        assert "**Tags:**" in docs
        assert "Name: main-vpc" in docs
    
    def test_export_to_html_basic(self):
        """Test HTML export creates valid HTML structure."""
        markdown = "# Test\n\nThis is a test."
        html = self.generator.export_to_html(markdown)
        
        # Check HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html
    
    def test_export_to_html_with_styling(self):
        """Test HTML export includes CSS styling."""
        markdown = "# Test"
        html = self.generator.export_to_html(markdown)
        
        assert "<style>" in html
        assert "font-family" in html
        assert "color" in html
    
    def test_export_to_html_converts_headers(self):
        """Test HTML export converts markdown headers."""
        markdown = "# Header 1\n## Header 2\n### Header 3"
        html = self.generator.export_to_html(markdown)
        
        assert "<h1>Header 1</h1>" in html
        assert "<h2>Header 2</h2>" in html
        assert "<h3>Header 3</h3>" in html
    
    def test_export_to_html_converts_lists(self):
        """Test HTML export converts markdown lists."""
        markdown = "- Item 1\n- Item 2\n- Item 3"
        html = self.generator.export_to_html(markdown)
        
        assert "<ul>" in html
        assert "<li>Item 1</li>" in html
        assert "<li>Item 2</li>" in html
        assert "</ul>" in html
    
    def test_export_to_html_converts_code_blocks(self):
        """Test HTML export converts markdown code blocks."""
        markdown = "```\ncode here\n```"
        html = self.generator.export_to_html(markdown)
        
        assert "<pre><code>" in html
        assert "code here" in html
        assert "</pre>" in html
    
    def test_export_to_html_converts_inline_code(self):
        """Test HTML export converts inline code."""
        markdown = "This is `inline code` here."
        html = self.generator.export_to_html(markdown)
        
        assert "<code>inline code</code>" in html
    
    def test_export_to_html_converts_bold(self):
        """Test HTML export converts bold text."""
        markdown = "This is **bold** text."
        html = self.generator.export_to_html(markdown)
        
        assert "<strong>bold</strong>" in html
    
    def test_export_to_pdf_placeholder(self):
        """Test PDF export returns placeholder message."""
        html = "<html><body>Test</body></html>"
        pdf_bytes = self.generator.export_to_pdf(html)
        
        # Should return bytes
        assert isinstance(pdf_bytes, bytes)
        
        # Should contain placeholder message
        pdf_text = pdf_bytes.decode('utf-8')
        assert "PDF Generation Placeholder" in pdf_text
    
    def test_sanitize_node_id(self):
        """Test node ID sanitization for Mermaid."""
        # Test with hyphens
        assert self.generator._sanitize_node_id("vpc-main") == "vpc_main"
        
        # Test with dots
        assert self.generator._sanitize_node_id("vpc.main") == "vpc_main"
        
        # Test with both
        assert self.generator._sanitize_node_id("vpc-main.test") == "vpc_main_test"
    
    def test_extract_resource_references_simple(self):
        """Test extracting resource references from properties."""
        properties = {
            "vpc_ref": "${resource.vpc-main.id}"
        }
        
        refs = self.generator._extract_resource_references(properties)
        assert "vpc-main" in refs
    
    def test_extract_resource_references_nested(self):
        """Test extracting resource references from nested properties."""
        properties = {
            "network": {
                "vpc_ref": "${resource.vpc-main.id}",
                "subnet_ref": "${resource.subnet-private.id}"
            }
        }
        
        refs = self.generator._extract_resource_references(properties)
        assert "vpc-main" in refs
        assert "subnet-private" in refs
    
    def test_extract_resource_references_in_list(self):
        """Test extracting resource references from lists."""
        properties = {
            "subnets": [
                "${resource.subnet-1.id}",
                "${resource.subnet-2.id}"
            ]
        }
        
        refs = self.generator._extract_resource_references(properties)
        assert "subnet-1" in refs
        assert "subnet-2" in refs
    
    def test_extract_resource_references_no_references(self):
        """Test extracting references when none exist."""
        properties = {
            "cidr": "10.0.0.0/16",
            "name": "my-vpc"
        }
        
        refs = self.generator._extract_resource_references(properties)
        assert len(refs) == 0
    
    def test_generate_resource_section_complete(self):
        """Test generating complete resource section."""
        resource = ResourceConfig(
            logical_id="test-resource",
            resource_type="vpc",
            properties={
                "cidr": "10.0.0.0/16",
                "description": "Main VPC"
            },
            tags={"Environment": "prod"},
            depends_on=["other-resource"],
            outputs={"VpcId": "The VPC ID"},
            stack="main-stack"
        )
        
        lines = self.generator._generate_resource_section(resource, self.config)
        section = "\n".join(lines)
        
        # Check all sections are present
        assert "### test-resource" in section
        assert "**Type:** `vpc`" in section
        assert "**Stack:** main-stack" in section
        assert "**Purpose:** Main VPC" in section
        assert "**Configuration:**" in section
        assert "**cidr:** `10.0.0.0/16`" in section
        assert "**Dependencies:**" in section
        assert "- other-resource" in section
        assert "**Outputs:**" in section
        assert "**VpcId:** The VPC ID" in section
        assert "**Tags:**" in section
        assert "Environment: prod" in section
    
    def test_markdown_to_html_empty(self):
        """Test HTML conversion with empty markdown."""
        html = self.generator._markdown_to_html("")
        assert html == "<br>"
    
    def test_markdown_to_html_paragraph(self):
        """Test HTML conversion of paragraphs."""
        markdown = "This is a paragraph."
        html = self.generator._markdown_to_html(markdown)
        assert "<p>" in html
        assert "This is a paragraph." in html
    
    def test_escape_html_special_characters(self):
        """Test HTML escaping of special characters."""
        text = "Test & <script> alert('xss') </script>"
        escaped = self.generator._escape_html(text)
        
        assert "&amp;" in escaped
        assert "&lt;" in escaped
        assert "&gt;" in escaped
    
    def test_escape_html_preserves_existing_tags(self):
        """Test HTML escaping escapes all special characters including tags."""
        text = "<strong>bold</strong>"
        escaped = self.generator._escape_html(text)
        
        # Should escape tags
        assert "&lt;strong&gt;" in escaped
        assert "&lt;/strong&gt;" in escaped
    
    def test_full_workflow_markdown_to_html(self):
        """Test complete workflow from config to HTML."""
        # Generate markdown
        markdown = self.generator.generate_markdown_docs(self.config)
        
        # Convert to HTML
        html = self.generator.export_to_html(markdown)
        
        # Verify HTML contains key information
        assert "test-project" in html
        assert "vpc-main" in html
        assert "ec2-web" in html
        assert "<!DOCTYPE html>" in html
    
    def test_diagram_with_no_dependencies(self):
        """Test diagram generation with resources that have no dependencies."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="simple",
                owner="team",
                cost_center="eng",
                description="Simple"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="s3-bucket",
                    resource_type="s3",
                    properties={"bucket_name": "my-bucket"},
                    tags={},
                    depends_on=[]
                )
            ]
        )
        
        diagram = self.generator.generate_architecture_diagram(config)
        
        # Should have node but no edges
        assert "s3_bucket" in diagram
        assert "-->" not in diagram
        assert "-.->not in diagram"
    
    def test_diagram_with_multiple_dependencies(self):
        """Test diagram with resources having multiple dependencies."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="complex",
                owner="team",
                cost_center="eng",
                description="Complex"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="vpc",
                    resource_type="vpc",
                    properties={},
                    tags={},
                    depends_on=[]
                ),
                ResourceConfig(
                    logical_id="subnet",
                    resource_type="subnet",
                    properties={},
                    tags={},
                    depends_on=["vpc"]
                ),
                ResourceConfig(
                    logical_id="ec2",
                    resource_type="ec2",
                    properties={},
                    tags={},
                    depends_on=["vpc", "subnet"]
                )
            ]
        )
        
        diagram = self.generator.generate_architecture_diagram(config)
        
        # Check all dependencies are present
        assert "ec2 --> vpc" in diagram
        assert "ec2 --> subnet" in diagram
        assert "subnet --> vpc" in diagram
    
    def test_documentation_with_empty_resources(self):
        """Test documentation generation with no resources."""
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="empty",
                owner="team",
                cost_center="eng",
                description="Empty"
            ),
            environments={},
            resources=[]
        )
        
        docs = self.generator.generate_markdown_docs(config)
        
        # Should still have structure
        assert "# Infrastructure Documentation: empty" in docs
        assert "## Resources" in docs
