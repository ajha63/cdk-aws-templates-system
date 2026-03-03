# CDK AWS Templates System

> Declarative infrastructure as code for AWS using CDK - Define your AWS infrastructure in YAML/JSON and generate production-ready CDK Python code automatically.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-483%2F491%20passing-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-81%25-green.svg)](tests/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[English](README.md) | [Español](README.es.md)

## 🌟 Overview

CDK AWS Templates System is a Python framework that enables you to deploy AWS infrastructure in a standardized and homogeneous way. Instead of writing CDK code directly, you define your infrastructure in declarative YAML/JSON configuration files, and the system automatically generates production-ready CDK Python code following AWS best practices.

## ✨ Key Features

- **📝 Declarative Configuration**: Define infrastructure in YAML/JSON instead of code
- **🏷️ Automatic Conventions**: Consistent naming and tagging applied automatically
- **✅ Pre-deployment Validation**: Catch errors before deployment
- **🔗 Dependency Management**: Automatically resolves resource relationships
- **🌍 Multi-Environment**: Manage dev, staging, and production with a single configuration
- **📊 Auto Documentation**: Generates diagrams and documentation of your infrastructure
- **🛡️ Deployment Rules**: Apply corporate policies automatically
- **🔄 Cross-Stack References**: Link resources across different CDK stacks

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 14+ (for AWS CDK CLI)
- AWS CDK CLI 2.x: `npm install -g aws-cdk`
- AWS credentials configured

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ajha63/cdk-aws-templates-system.git
cd cdk-aws-templates-system

# 2. Run the automated installer (checks all prerequisites)
./install.sh

# Or install manually:
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

# 3. Install AWS CDK CLI (if not already installed)
npm install -g aws-cdk
cdk --version

# 4. Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT-ID/REGION

# 5. Run the interactive quickstart
python quickstart.py
```

## 📋 Supported Resources

| Resource | Description | Features |
|----------|-------------|----------|
| **VPC** | Virtual Private Cloud | Multi-AZ subnets, NAT Gateways, Flow Logs |
| **EC2** | Compute instances | Session Manager, IAM roles, encrypted volumes |
| **RDS** | Relational databases | Multi-AZ, automated backups, encryption, Secrets Manager |
| **S3** | Object storage | Versioning, encryption, lifecycle rules, access logging |

## 💡 Simple Example

Create a file `my-infrastructure.yaml`:

```yaml
version: '1.0'

metadata:
  project: my-project
  owner: my-team
  cost_center: engineering
  description: My first infrastructure

environments:
  dev:
    name: dev
    account_id: '123456789012'
    region: us-east-1

resources:
  - logical_id: vpc-main
    resource_type: vpc
    properties:
      cidr: '10.0.0.0/16'
      availability_zones: 2
      enable_dns_hostnames: true
      enable_flow_logs: true
```

Generate CDK code:

```python
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator
import os

loader = ConfigurationLoader()
config = loader.load_config(['my-infrastructure.yaml'])

generator = TemplateGenerator()
result = generator.generate(config, environment='dev')

# Save generated files
output_dir = 'cdk-output'
os.makedirs(output_dir, exist_ok=True)

for file_path, content in result.generated_files.items():
    full_path = os.path.join(output_dir, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w') as f:
        f.write(content)
    print(f'Created: {full_path}')
```

Deploy to AWS:

```bash
cd cdk-output
pip install -r requirements.txt
cdk synth    # Verify the generated CloudFormation
cdk diff     # See what will be created/changed
cdk deploy   # Deploy to AWS
```

Deploy with CDK:

```bash
cdk synth
cdk deploy
```

## 📖 Documentation

- [Getting Started Guide (English)](docs/GETTING_STARTED.md) *(coming soon)*
- [Guía de Inicio (Español)](docs/GUIA_DE_INICIO.md) - Complete tutorial in Spanish
- [Examples](examples/) - Ready-to-use configuration examples
- [CLI Usage](docs/CLI_USAGE.md) - Command reference
- [Validation Engine](docs/VALIDATION_ENGINE_USAGE.md) - Configuration validation

## 🎯 Complete Example

See [examples/aplicacion-web-completa.yaml](examples/aplicacion-web-completa.yaml) for a full-stack application with:
- VPC with 3 availability zones
- EC2 instance with Session Manager
- RDS PostgreSQL database with Multi-AZ
- S3 buckets for assets and backups
- Multi-environment configuration (dev/prod)

## 🏗️ Architecture

```
User Config (YAML/JSON)
         ↓
Configuration Loader → Schema Validator → Link Resolver
         ↓
Deployment Rules Engine
         ↓
Template Generator
         ↓
CDK Python Code + Documentation
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=cdk_templates --cov-report=html

# Current status: 483/491 tests passing (98.4%)
```

## 📊 Naming Conventions

Pattern: `{environment}-{project}-{type}-{purpose}-{region}[-{instance}]`

Examples:
- VPC: `dev-myapp-vpc-main-us-east-1`
- EC2: `prod-myapp-ec2-web-us-east-1-01`
- RDS: `staging-myapp-rds-main-eu-west-1`

## 🏷️ Mandatory Tags

All resources automatically receive:
- `Environment`: dev, staging, prod
- `Project`: project name
- `Owner`: responsible team
- `CostCenter`: cost center for billing
- `ManagedBy`: cdk-template-system

## 🔧 Advanced Features

### Multi-Environment Configuration

```yaml
environments:
  dev:
    overrides:
      ec2-web:
        properties:
          instance_type: t3.micro
  
  prod:
    overrides:
      ec2-web:
        properties:
          instance_type: t3.large
          enable_detailed_monitoring: true
```

### Resource References

```yaml
resources:
  - logical_id: vpc-app
    resource_type: vpc
    properties:
      cidr: '10.0.0.0/16'

  - logical_id: ec2-web
    resource_type: ec2
    properties:
      vpc_ref: '${resource.vpc-app.id}'
    depends_on:
      - vpc-app
```

### Cross-Stack References

```yaml
resources:
  - logical_id: ec2-app
    resource_type: ec2
    properties:
      vpc_ref: '${import.NetworkStack-VpcId}'
```

## 🛠️ Development

### Project Structure

```
cdk_templates/
├── cdk_templates/          # Main source code
│   ├── templates/          # Resource templates
│   ├── config_loader.py    # Configuration loading
│   ├── schema_validator.py # Schema validation
│   └── template_generator.py # CDK code generation
├── schemas/                # JSON Schema definitions
├── tests/                  # Test suite
├── examples/               # Configuration examples
└── docs/                   # Documentation
```

### Adding a New Resource Type

1. Create JSON schema in `schemas/{type}.json`
2. Create template in `cdk_templates/templates/{type}_template.py`
3. Implement `ResourceTemplate` interface
4. Add tests in `tests/unit/templates/test_{type}_template.py`
5. Update documentation

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -am 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- AWS CDK Team for the excellent framework
- Python community for testing tools
- All project contributors

## 📞 Support

- 📖 [Full Documentation](docs/)
- 💬 [Issues](https://github.com/yourusername/cdk-aws-templates-system/issues)
- 📧 Email: your-email@example.com

## 🗺️ Roadmap

- [ ] Support for Lambda functions
- [ ] Support for API Gateway
- [ ] Support for DynamoDB
- [ ] Support for ECS/Fargate
- [ ] CloudFormation drift detection
- [ ] Cost estimation before deployment
- [ ] Terraform backend support

---

**Made with ❤️ by the infrastructure team**

*Happy deploying!* 🚀
