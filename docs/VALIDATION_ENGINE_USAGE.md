# Validation Engine Usage Guide

## Overview

The `ValidationEngine` provides comprehensive pre-generation validation for CDK AWS Templates System configurations. It integrates three validation components:

1. **SchemaValidator** - Validates syntax and structure against JSON schemas
2. **ResourceLinkResolver** - Validates resource links and detects circular dependencies
3. **DeploymentRulesEngine** - Applies business rules and policies

## Basic Usage

```python
from cdk_templates import ValidationEngine, Configuration

# Create validation engine with default components
engine = ValidationEngine()

# Validate a configuration
result = engine.validate(config, environment="prod")

if result.is_valid:
    print("✓ Configuration is valid")
else:
    print(f"✗ Found {len(result.errors)} errors")
    for error in result.errors:
        print(f"  - {error.field_path}: {error.message}")
```

## Generating Error Reports

```python
# Validate and generate a detailed report
is_valid, report = engine.validate_and_report(config, "prod")

print(report)
# Output:
# ================================================================================
# CONFIGURATION VALIDATION FAILED
# ================================================================================
# 
# ERRORS (2):
# --------------------------------------------------------------------------------
# 1. [MISSING_REQUIRED_FIELD] resources[0].properties.cidr
#    Missing required field 'cidr'
# 
# 2. [LINK_RESOLUTION_ERROR] resources
#    Resource 'ec2-web' references non-existent resource 'vpc-missing'
# ...
```

## Preventing Code Generation on Failure

```python
from cdk_templates import ValidationException

try:
    # This will raise ValidationException if validation fails
    result = engine.prevent_generation_on_failure(config, "prod")
    
    # If we get here, validation passed
    # Proceed with code generation...
    
except ValidationException as e:
    print(e.report)
    # Handle validation failure
```

## Custom Validation Components

You can provide custom instances of validation components:

```python
from cdk_templates import ValidationEngine
from cdk_templates.schema_validator import SchemaValidator
from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.deployment_rules import (
    DeploymentRulesEngine,
    EncryptionEnforcementRule,
    ProductionProtectionRule
)

# Create custom rules engine with specific rules
rules_engine = DeploymentRulesEngine()
rules_engine.register_rule(EncryptionEnforcementRule(), priority=200)
rules_engine.register_rule(ProductionProtectionRule(), priority=100)

# Create validation engine with custom components
engine = ValidationEngine(
    schema_validator=SchemaValidator(),
    link_resolver=ResourceLinkResolver(),
    rules_engine=rules_engine
)
```

## Validation Process

The validation engine runs all three validators in sequence:

1. **Schema Validation**
   - Validates resource properties against JSON schemas
   - Checks required fields, types, and constraints
   - Applies default values where specified

2. **Link Resolution**
   - Validates all resource references exist
   - Detects circular dependencies
   - Builds dependency graph for deployment ordering

3. **Deployment Rules**
   - Applies business policies (encryption, tagging, etc.)
   - Can modify configuration (auto-fix)
   - Can reject configuration (policy violation)

**Important**: All validations run to completion before reporting errors, providing comprehensive feedback.

## Error Types

### Schema Errors
- `MISSING_REQUIRED_FIELD` - Required field is missing
- `INVALID_TYPE` - Field has wrong type
- `PATTERN_MISMATCH` - Value doesn't match required pattern
- `VALUE_TOO_SMALL` / `VALUE_TOO_LARGE` - Value outside allowed range

### Link Resolution Errors
- `LINK_RESOLUTION_ERROR` - Referenced resource doesn't exist
- `CIRCULAR_DEPENDENCY` - Circular dependency detected

### Rule Violations
- `RULE_VIOLATION` - Configuration violates a deployment rule
- `RULE_ERROR` - Error applying deployment rule

## Integration with Template Generator

The ValidationEngine should be used before code generation:

```python
from cdk_templates import ValidationEngine
from cdk_templates.template_generator import TemplateGenerator

# Validate first
engine = ValidationEngine()
result = engine.prevent_generation_on_failure(config, environment)

# Only generate if validation passed
generator = TemplateGenerator()
generation_result = generator.generate(config)
```

## Best Practices

1. **Always validate before generation** - Use `prevent_generation_on_failure()` to enforce this
2. **Provide environment context** - Different rules apply to different environments
3. **Review all errors** - The engine collects all errors before reporting
4. **Use custom rules** - Register deployment rules specific to your organization
5. **Handle ValidationException** - Catch and display the formatted report to users

## Example: Complete Validation Pipeline

```python
from cdk_templates import (
    ValidationEngine,
    ValidationException,
    Configuration
)
from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator

def generate_infrastructure(config_file: str, environment: str):
    """Generate CDK infrastructure with validation."""
    
    # Load configuration
    loader = ConfigurationLoader()
    config = loader.load_config([config_file])
    
    # Validate configuration
    engine = ValidationEngine()
    
    try:
        result = engine.prevent_generation_on_failure(config, environment)
        print(f"✓ Configuration validated successfully")
        print(f"  - {len(config.resources)} resources")
        print(f"  - Environment: {environment}")
        
    except ValidationException as e:
        print("✗ Configuration validation failed:")
        print(e.report)
        return False
    
    # Generate CDK code
    generator = TemplateGenerator()
    gen_result = generator.generate(config)
    
    if gen_result.success:
        print(f"✓ Generated {len(gen_result.generated_files)} files")
        return True
    else:
        print(f"✗ Code generation failed:")
        for error in gen_result.errors:
            print(f"  - {error}")
        return False

# Usage
if __name__ == "__main__":
    success = generate_infrastructure("infrastructure.yaml", "prod")
    exit(0 if success else 1)
```

## Requirements Validated

The ValidationEngine satisfies the following requirements:

- **Requirement 9.1**: Validates syntax and structure before generating CDK code
- **Requirement 9.2**: Verifies all resource links point to existing resources
- **Requirement 9.3**: Validates configurations comply with AWS service limits
- **Requirement 9.4**: Returns detailed report with all errors found
- **Requirement 9.5**: Prevents CDK stack synthesis if validation errors exist
