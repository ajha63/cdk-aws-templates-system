"""Naming Convention Service for generating consistent AWS resource names."""

import re
from typing import Optional
from cdk_templates.models import ValidationResult, ValidationError


class NamingConventionService:
    """
    Service for generating and validating AWS resource names.
    
    Implements naming pattern: {env}-{service}-{purpose}-{region}[-{instance}]
    Enforces AWS resource-specific naming constraints.
    """
    
    # AWS resource naming constraints
    # Format: resource_type -> (max_length, allowed_pattern, description)
    RESOURCE_CONSTRAINTS = {
        'vpc': (255, r'^[a-zA-Z0-9\s._\-:/()#,@\[\]+=&;{}!$*]+$', 'VPC name'),
        'ec2': (255, r'^[a-zA-Z0-9\s._\-:/()#,@\[\]+=&;{}!$*]+$', 'EC2 instance name'),
        'rds': (63, r'^[a-zA-Z][a-zA-Z0-9\-]*$', 'RDS instance identifier (must start with letter, alphanumeric and hyphens only)'),
        's3': (63, r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', 'S3 bucket name (lowercase, alphanumeric and hyphens, cannot start/end with hyphen)'),
        'subnet': (255, r'^[a-zA-Z0-9\s._\-:/()#,@\[\]+=&;{}!$*]+$', 'Subnet name'),
        'security_group': (255, r'^[a-zA-Z0-9\s._\-:/()#,@\[\]+=&;{}!$*]+$', 'Security group name'),
        'iam_role': (64, r'^[\w+=,.@\-]+$', 'IAM role name'),
        'lambda': (64, r'^[a-zA-Z0-9\-_]+$', 'Lambda function name'),
        'dynamodb': (255, r'^[a-zA-Z0-9_.\-]+$', 'DynamoDB table name'),
        'sns': (256, r'^[a-zA-Z0-9_\-]+$', 'SNS topic name'),
        'sqs': (80, r'^[a-zA-Z0-9_\-]+$', 'SQS queue name'),
        'cloudwatch_log_group': (512, r'^[a-zA-Z0-9_/.\-]+$', 'CloudWatch log group name'),
    }
    
    def __init__(self):
        """Initialize the naming convention service."""
        self._instance_counters = {}
    
    def generate_name(
        self,
        resource_type: str,
        purpose: str,
        environment: str,
        region: str,
        service: Optional[str] = None,
        instance_number: Optional[int] = None
    ) -> str:
        """
        Generate a resource name following the naming convention.
        
        Pattern: {env}-{service}-{purpose}-{region}[-{instance}]
        
        Args:
            resource_type: Type of AWS resource (vpc, ec2, rds, s3, etc.)
            purpose: Purpose or role of the resource
            environment: Environment name (dev, staging, prod)
            region: AWS region (us-east-1, eu-west-1, etc.)
            service: Service name (optional, defaults to 'app')
            instance_number: Instance number for multiple resources (optional)
            
        Returns:
            Generated resource name following the convention
            
        Raises:
            ValueError: If generated name violates AWS constraints
        """
        # Default service name if not provided
        if service is None:
            service = 'app'
        
        # Normalize components to lowercase for consistency
        env = environment.lower()
        svc = service.lower()
        prp = purpose.lower()
        rgn = region.lower()
        
        # Build base name
        name_parts = [env, svc, prp, rgn]
        
        # Add instance number if provided
        if instance_number is not None:
            name_parts.append(f"{instance_number:02d}")
        
        # Join with hyphens
        generated_name = '-'.join(name_parts)
        
        # Apply resource-specific transformations
        generated_name = self._apply_resource_constraints(generated_name, resource_type)
        
        # Validate the generated name
        validation_result = self.validate_name(generated_name, resource_type)
        if not validation_result.is_valid:
            error_messages = '; '.join([e.message for e in validation_result.errors])
            raise ValueError(
                f"Generated name '{generated_name}' violates AWS constraints for {resource_type}: {error_messages}"
            )
        
        return generated_name
    
    def validate_name(self, name: str, resource_type: str) -> ValidationResult:
        """
        Validate that a name complies with AWS resource-specific constraints.
        
        Args:
            name: Resource name to validate
            resource_type: Type of AWS resource
            
        Returns:
            ValidationResult indicating if name is valid and any errors
        """
        errors = []
        
        # Check if resource type is known
        if resource_type not in self.RESOURCE_CONSTRAINTS:
            # For unknown resource types, apply generic validation
            max_length = 255
            pattern = r'^[a-zA-Z0-9\s._\-:/()#,@\[\]+=&;{}!$*]+$'
            description = 'Generic AWS resource name'
        else:
            max_length, pattern, description = self.RESOURCE_CONSTRAINTS[resource_type]
        
        # Check length constraint
        if len(name) > max_length:
            errors.append(ValidationError(
                field_path='name',
                message=f"Name exceeds maximum length of {max_length} characters for {resource_type} (current: {len(name)})",
                error_code='NAME_TOO_LONG',
                severity='ERROR'
            ))
        
        # Check if name is empty or only whitespace
        if not name or not name.strip():
            errors.append(ValidationError(
                field_path='name',
                message=f"Name cannot be empty or whitespace-only for {resource_type}",
                error_code='NAME_EMPTY',
                severity='ERROR'
            ))
            # Return early if name is empty to avoid regex errors
            return ValidationResult(is_valid=False, errors=errors)
        
        # Check character constraints
        if not re.match(pattern, name):
            errors.append(ValidationError(
                field_path='name',
                message=f"Name contains invalid characters for {resource_type}. {description}",
                error_code='INVALID_CHARACTERS',
                severity='ERROR'
            ))
        
        # Resource-specific validations
        if resource_type == 's3':
            # S3 bucket names have additional constraints
            if name.startswith('-') or name.endswith('-'):
                errors.append(ValidationError(
                    field_path='name',
                    message="S3 bucket name cannot start or end with a hyphen",
                    error_code='S3_INVALID_HYPHEN',
                    severity='ERROR'
                ))
            
            if '..' in name:
                errors.append(ValidationError(
                    field_path='name',
                    message="S3 bucket name cannot contain consecutive periods",
                    error_code='S3_CONSECUTIVE_PERIODS',
                    severity='ERROR'
                ))
            
            if not name.islower():
                errors.append(ValidationError(
                    field_path='name',
                    message="S3 bucket name must be lowercase",
                    error_code='S3_NOT_LOWERCASE',
                    severity='ERROR'
                ))
            
            # Check for IP address format (not allowed)
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', name):
                errors.append(ValidationError(
                    field_path='name',
                    message="S3 bucket name cannot be formatted as an IP address",
                    error_code='S3_IP_FORMAT',
                    severity='ERROR'
                ))
        
        elif resource_type == 'rds':
            # RDS identifiers must start with a letter
            if not name[0].isalpha():
                errors.append(ValidationError(
                    field_path='name',
                    message="RDS instance identifier must start with a letter",
                    error_code='RDS_MUST_START_WITH_LETTER',
                    severity='ERROR'
                ))
            
            # RDS identifiers must be lowercase
            if not name.islower():
                errors.append(ValidationError(
                    field_path='name',
                    message="RDS instance identifier must be lowercase",
                    error_code='RDS_NOT_LOWERCASE',
                    severity='ERROR'
                ))
            
            # RDS identifiers cannot end with a hyphen
            if name.endswith('-'):
                errors.append(ValidationError(
                    field_path='name',
                    message="RDS instance identifier cannot end with a hyphen",
                    error_code='RDS_CANNOT_END_WITH_HYPHEN',
                    severity='ERROR'
                ))
            
            # RDS identifiers cannot contain consecutive hyphens
            if '--' in name:
                errors.append(ValidationError(
                    field_path='name',
                    message="RDS instance identifier cannot contain consecutive hyphens",
                    error_code='RDS_CONSECUTIVE_HYPHENS',
                    severity='ERROR'
                ))
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors)
    
    def _apply_resource_constraints(self, name: str, resource_type: str) -> str:
        """
        Apply resource-specific transformations to ensure compliance.
        
        Args:
            name: Base name to transform
            resource_type: Type of AWS resource
            
        Returns:
            Transformed name
        """
        # S3 buckets must be lowercase
        if resource_type == 's3':
            name = name.lower()
            # Remove any invalid characters for S3
            name = re.sub(r'[^a-z0-9\-]', '-', name)
            # Remove consecutive hyphens
            name = re.sub(r'-+', '-', name)
            # Remove leading/trailing hyphens
            name = name.strip('-')
        
        # RDS identifiers: ensure starts with letter, lowercase
        elif resource_type == 'rds':
            name = name.lower()
            # Remove invalid characters
            name = re.sub(r'[^a-z0-9\-]', '-', name)
            # Remove consecutive hyphens
            name = re.sub(r'-+', '-', name)
            # Remove trailing hyphens
            name = name.rstrip('-')
            # Ensure starts with letter
            if name and not name[0].isalpha():
                name = 'db-' + name
        
        # Apply length constraints
        if resource_type in self.RESOURCE_CONSTRAINTS:
            max_length, _, _ = self.RESOURCE_CONSTRAINTS[resource_type]
            if len(name) > max_length:
                # Truncate to max length
                name = name[:max_length]
                # Ensure doesn't end with hyphen after truncation
                name = name.rstrip('-')
        
        return name
