# CLI Usage Guide

The CDK AWS Templates System provides a command-line interface for generating, validating, and managing AWS infrastructure code.

## Installation

```bash
pip install -e .
```

This will install the `cdk-templates` command globally.

## Commands

### generate

Generate CDK Python code from configuration files.

```bash
cdk-templates generate -c config.yaml -e dev
```

**Options:**
- `-c, --config PATH`: Configuration file(s) to load (can specify multiple)
- `-e, --environment TEXT`: Target environment (dev, staging, prod) [required]
- `-o, --output PATH`: Output directory for generated CDK code (default: generated)
- `--validate-only`: Only validate configuration without generating code

**Examples:**

```bash
# Generate code for development environment
cdk-templates generate -c config.yaml -e dev

# Generate with multiple config files
cdk-templates generate -c base.yaml -c dev.yaml -e dev

# Specify custom output directory
cdk-templates generate -c config.yaml -e prod -o ./infrastructure

# Validate only without generating
cdk-templates generate -c config.yaml -e dev --validate-only
```

**Output:**
- Displays validation progress and results
- Shows warnings if any
- Generates CDK Python code in the output directory
- Provides next steps for deployment

### validate

Validate configuration files without generating code.

```bash
cdk-templates validate -c config.yaml -e dev
```

**Options:**
- `-c, --config PATH`: Configuration file(s) to validate [required]
- `-e, --environment TEXT`: Target environment [required]
- `-v, --verbose`: Show detailed validation information

**Examples:**

```bash
# Validate configuration
cdk-templates validate -c config.yaml -e dev

# Validate with verbose output
cdk-templates validate -c config.yaml -e dev -v
```

**Output:**
- Validation status (pass/fail)
- List of errors and warnings
- Configuration summary (with -v flag)
- Resource breakdown by type (with -v flag)

### query

Query the Resource Registry for deployed resources.

```bash
cdk-templates query
```

**Options:**
- `-r, --registry PATH`: Path to resource registry file
- `-t, --type TEXT`: Filter by resource type (vpc, ec2, rds, s3)
- `-e, --environment TEXT`: Filter by environment
- `-s, --stack TEXT`: Filter by stack name
- `--tag TEXT`: Filter by tag (format: key=value, can specify multiple)
- `-f, --format [table|json|yaml]`: Output format (default: table)

**Examples:**

```bash
# List all resources
cdk-templates query

# Query VPC resources in production
cdk-templates query --type vpc --environment prod

# Query resources with specific tag
cdk-templates query --tag Project=myapp

# Query with multiple filters
cdk-templates query --type ec2 --environment dev --tag Owner=team-a

# Export as JSON
cdk-templates query --format json

# Export as YAML
cdk-templates query --format yaml
```

**Output:**
- Table view with resource details (default)
- JSON or YAML format for programmatic use
- Resource count summary

### docs

Generate documentation from configuration files.

```bash
cdk-templates docs -c config.yaml
```

**Options:**
- `-c, --config PATH`: Configuration file(s) to document [required]
- `-o, --output PATH`: Output directory for documentation (default: docs)
- `-f, --format [markdown|html|all]`: Documentation format (default: markdown)
- `--include-diagram`: Include architecture diagram (default: true)

**Examples:**

```bash
# Generate Markdown documentation
cdk-templates docs -c config.yaml

# Generate HTML documentation
cdk-templates docs -c config.yaml --format html

# Generate all formats
cdk-templates docs -c config.yaml --format all

# Specify custom output directory
cdk-templates docs -c config.yaml -o ./documentation
```

**Output:**
- `infrastructure.md`: Markdown documentation
- `infrastructure.html`: HTML documentation (if requested)
- Architecture diagram in Mermaid format
- Resource descriptions and configurations

## Output Formatting

The CLI uses rich formatting for better readability:

- **Progress indicators**: Spinners show progress during long operations
- **Color coding**: 
  - Green (✓) for success
  - Red (✗) for errors
  - Yellow (⚠) for warnings
  - Cyan for informational messages
- **Tables**: Resource queries display results in formatted tables
- **Error reports**: Validation errors are formatted with field paths and suggestions

## Error Handling

The CLI provides detailed error messages with:

- **Field paths**: Exact location of errors in configuration
- **Error codes**: Categorized error types
- **Suggestions**: Actionable steps to fix errors
- **Context**: Additional information about the error

Example error output:

```
Configuration Error in file 'config.yaml'
  Path: resources[0].properties.cidr
  Error: Invalid CIDR block format

Suggestions:
  1. Use valid CIDR notation (e.g., 10.0.0.0/16)
  2. Check the schema documentation for valid CIDR formats
```

## Exit Codes

- `0`: Success
- `1`: Error (configuration, validation, or generation failure)
- `2`: Invalid command or options

## Environment Variables

The CLI respects the following environment variables:

- Configuration files can reference environment variables using `${VAR_NAME}` syntax
- Default values can be specified: `${VAR_NAME:-default_value}`

## Next Steps After Generation

After successfully generating CDK code:

1. Navigate to the output directory:
   ```bash
   cd generated
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Synthesize CloudFormation templates:
   ```bash
   cdk synth
   ```

4. Deploy to AWS:
   ```bash
   cdk deploy
   ```

## Debugging

For detailed error traces, you can use the `--debug` flag (add it anywhere in the command):

```bash
cdk-templates generate -c config.yaml -e dev --debug
```

This will show full Python stack traces for debugging purposes.

## Getting Help

For help with any command:

```bash
cdk-templates --help
cdk-templates generate --help
cdk-templates validate --help
cdk-templates query --help
cdk-templates docs --help
```
