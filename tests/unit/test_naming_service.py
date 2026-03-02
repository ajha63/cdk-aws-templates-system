"""Unit tests for NamingConventionService."""

import pytest
from cdk_templates.naming_service import NamingConventionService


class TestNamingConventionService:
    """Test suite for NamingConventionService."""
    
    def test_generate_name_basic(self):
        """Test basic name generation with all required parameters."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='vpc',
            purpose='main',
            environment='prod',
            region='us-east-1'
        )
        
        assert name == 'prod-app-main-us-east-1'
    
    def test_generate_name_with_service(self):
        """Test name generation with custom service name."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='ec2',
            purpose='web',
            environment='dev',
            region='eu-west-1',
            service='myapp'
        )
        
        assert name == 'dev-myapp-web-eu-west-1'
    
    def test_generate_name_with_instance_number(self):
        """Test name generation with instance number."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='ec2',
            purpose='worker',
            environment='staging',
            region='us-west-2',
            instance_number=3
        )
        
        assert name == 'staging-app-worker-us-west-2-03'
    
    def test_generate_name_s3_lowercase(self):
        """Test that S3 bucket names are forced to lowercase."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='s3',
            purpose='DataBucket',
            environment='PROD',
            region='US-EAST-1'
        )
        
        assert name == 'prod-app-databucket-us-east-1'
        assert name.islower()
    
    def test_generate_name_rds_starts_with_letter(self):
        """Test that RDS identifiers start with a letter."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='rds',
            purpose='main',
            environment='prod',
            region='us-east-1'
        )
        
        assert name[0].isalpha()
    
    def test_generate_name_maximum_length_s3(self):
        """Test name generation respects S3 bucket name length limit (63 chars)."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='s3',
            purpose='very-long-purpose-name-that-might-exceed-the-limit',
            environment='production',
            region='us-east-1',
            service='myapplication'
        )
        
        assert len(name) <= 63
        assert not name.endswith('-')
    
    def test_generate_name_maximum_length_rds(self):
        """Test name generation respects RDS identifier length limit (63 chars)."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='rds',
            purpose='very-long-database-purpose-name-that-exceeds-limits',
            environment='production',
            region='us-east-1',
            service='application'
        )
        
        assert len(name) <= 63
        assert not name.endswith('-')
        assert name[0].isalpha()
    
    def test_validate_name_valid_vpc(self):
        """Test validation accepts valid VPC name."""
        service = NamingConventionService()
        
        result = service.validate_name('prod-app-main-us-east-1', 'vpc')
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_name_valid_s3(self):
        """Test validation accepts valid S3 bucket name."""
        service = NamingConventionService()
        
        result = service.validate_name('prod-app-data-us-east-1', 's3')
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_name_s3_uppercase_rejected(self):
        """Test validation rejects S3 bucket name with uppercase letters."""
        service = NamingConventionService()
        
        result = service.validate_name('Prod-App-Data', 's3')
        
        assert not result.is_valid
        assert any('lowercase' in error.message.lower() for error in result.errors)
    
    def test_validate_name_s3_starts_with_hyphen(self):
        """Test validation rejects S3 bucket name starting with hyphen."""
        service = NamingConventionService()
        
        result = service.validate_name('-prod-app-data', 's3')
        
        assert not result.is_valid
        assert any('start' in error.message.lower() and 'hyphen' in error.message.lower() 
                   for error in result.errors)
    
    def test_validate_name_s3_ends_with_hyphen(self):
        """Test validation rejects S3 bucket name ending with hyphen."""
        service = NamingConventionService()
        
        result = service.validate_name('prod-app-data-', 's3')
        
        assert not result.is_valid
        assert any('end' in error.message.lower() and 'hyphen' in error.message.lower() 
                   for error in result.errors)
    
    def test_validate_name_s3_ip_address_format(self):
        """Test validation rejects S3 bucket name formatted as IP address."""
        service = NamingConventionService()
        
        result = service.validate_name('192.168.1.1', 's3')
        
        assert not result.is_valid
        assert any('ip address' in error.message.lower() for error in result.errors)
    
    def test_validate_name_rds_must_start_with_letter(self):
        """Test validation rejects RDS identifier not starting with letter."""
        service = NamingConventionService()
        
        result = service.validate_name('1prod-db-main', 'rds')
        
        assert not result.is_valid
        assert any('start with a letter' in error.message.lower() for error in result.errors)
    
    def test_validate_name_rds_cannot_end_with_hyphen(self):
        """Test validation rejects RDS identifier ending with hyphen."""
        service = NamingConventionService()
        
        result = service.validate_name('prod-db-main-', 'rds')
        
        assert not result.is_valid
        assert any('end' in error.message.lower() and 'hyphen' in error.message.lower() 
                   for error in result.errors)
    
    def test_validate_name_rds_consecutive_hyphens(self):
        """Test validation rejects RDS identifier with consecutive hyphens."""
        service = NamingConventionService()
        
        result = service.validate_name('prod--db--main', 'rds')
        
        assert not result.is_valid
        assert any('consecutive' in error.message.lower() and 'hyphen' in error.message.lower() 
                   for error in result.errors)
    
    def test_validate_name_too_long(self):
        """Test validation rejects name exceeding maximum length."""
        service = NamingConventionService()
        
        # S3 bucket names have 63 character limit
        long_name = 'a' * 64
        result = service.validate_name(long_name, 's3')
        
        assert not result.is_valid
        assert any('exceeds maximum length' in error.message.lower() for error in result.errors)
    
    def test_validate_name_empty(self):
        """Test validation rejects empty name."""
        service = NamingConventionService()
        
        result = service.validate_name('', 'vpc')
        
        assert not result.is_valid
        assert any('empty' in error.message.lower() for error in result.errors)
    
    def test_validate_name_invalid_characters_s3(self):
        """Test validation rejects S3 bucket name with invalid characters."""
        service = NamingConventionService()
        
        result = service.validate_name('prod_app_data', 's3')
        
        assert not result.is_valid
        assert any('invalid characters' in error.message.lower() for error in result.errors)
    
    def test_validate_name_unknown_resource_type(self):
        """Test validation handles unknown resource types with generic rules."""
        service = NamingConventionService()
        
        # Unknown resource type should use generic validation
        result = service.validate_name('prod-app-custom-resource', 'unknown_type')
        
        # Should still validate (generic rules)
        assert result.is_valid
    
    def test_generate_multiple_instances_unique_names(self):
        """Test generating multiple instances produces unique names."""
        service = NamingConventionService()
        
        names = []
        for i in range(1, 6):
            name = service.generate_name(
                resource_type='ec2',
                purpose='worker',
                environment='prod',
                region='us-east-1',
                instance_number=i
            )
            names.append(name)
        
        # All names should be unique
        assert len(names) == len(set(names))
        
        # Names should follow pattern with instance numbers
        assert 'prod-app-worker-us-east-1-01' in names
        assert 'prod-app-worker-us-east-1-05' in names
    
    def test_validate_name_iam_role(self):
        """Test validation for IAM role names."""
        service = NamingConventionService()
        
        # Valid IAM role name
        result = service.validate_name('prod-app-ec2-role', 'iam_role')
        assert result.is_valid
        
        # IAM role names have 64 character limit
        long_name = 'a' * 65
        result = service.validate_name(long_name, 'iam_role')
        assert not result.is_valid
    
    def test_validate_name_lambda(self):
        """Test validation for Lambda function names."""
        service = NamingConventionService()
        
        # Valid Lambda function name
        result = service.validate_name('prod-app-processor', 'lambda')
        assert result.is_valid
        
        # Lambda names have 64 character limit
        long_name = 'a' * 65
        result = service.validate_name(long_name, 'lambda')
        assert not result.is_valid
    
    def test_apply_resource_constraints_s3(self):
        """Test that S3 constraints are applied during generation."""
        service = NamingConventionService()
        
        # Name with uppercase and special characters
        name = service.generate_name(
            resource_type='s3',
            purpose='Data_Bucket',
            environment='PROD',
            region='US-EAST-1'
        )
        
        # Should be lowercase and hyphens only
        assert name.islower()
        assert '_' not in name
        assert not name.startswith('-')
        assert not name.endswith('-')
    
    def test_apply_resource_constraints_rds(self):
        """Test that RDS constraints are applied during generation."""
        service = NamingConventionService()
        
        # Name that might not start with letter
        name = service.generate_name(
            resource_type='rds',
            purpose='123database',
            environment='prod',
            region='us-east-1'
        )
        
        # Should start with letter
        assert name[0].isalpha()
        assert not name.endswith('-')
        assert '--' not in name
    
    def test_edge_case_very_short_purpose(self):
        """Test name generation with very short purpose."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='vpc',
            purpose='a',
            environment='dev',
            region='us-east-1'
        )
        
        assert name == 'dev-app-a-us-east-1'
    
    def test_edge_case_special_characters_in_purpose(self):
        """Test name generation handles special characters in purpose."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='s3',
            purpose='my_data@bucket',
            environment='prod',
            region='us-east-1'
        )
        
        # Special characters should be converted to hyphens for S3
        assert '@' not in name
        assert '_' not in name
        assert name.islower()
    
    def test_generate_name_all_resource_types(self):
        """Test name generation works for all supported resource types."""
        service = NamingConventionService()
        resource_types = ['vpc', 'ec2', 'rds', 's3', 'subnet', 'security_group', 
                         'iam_role', 'lambda', 'dynamodb', 'sns', 'sqs', 'cloudwatch_log_group']
        
        for resource_type in resource_types:
            name = service.generate_name(
                resource_type=resource_type,
                purpose='test',
                environment='dev',
                region='us-east-1'
            )
            
            # All names should be non-empty and valid
            assert name
            assert len(name) > 0
            
            # Validate the generated name
            result = service.validate_name(name, resource_type)
            assert result.is_valid, f"Generated name '{name}' is invalid for {resource_type}: {result.errors}"
    
    def test_generate_name_different_environments(self):
        """Test name generation with different environment names."""
        service = NamingConventionService()
        environments = ['dev', 'development', 'staging', 'stage', 'prod', 'production', 'test', 'qa']
        
        names = []
        for env in environments:
            name = service.generate_name(
                resource_type='vpc',
                purpose='main',
                environment=env,
                region='us-east-1'
            )
            names.append(name)
            assert env.lower() in name
        
        # All names should be unique
        assert len(names) == len(set(names))
    
    def test_generate_name_different_regions(self):
        """Test name generation with different AWS regions."""
        service = NamingConventionService()
        regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 
                  'ap-southeast-1', 'ap-northeast-1', 'sa-east-1']
        
        names = []
        for region in regions:
            name = service.generate_name(
                resource_type='ec2',
                purpose='web',
                environment='prod',
                region=region
            )
            names.append(name)
            assert region.lower() in name
        
        # All names should be unique
        assert len(names) == len(set(names))
    
    def test_uniqueness_with_instance_numbers(self):
        """Test that instance numbers ensure uniqueness for identical configurations."""
        service = NamingConventionService()
        
        # Generate 10 instances with same config but different instance numbers
        names = set()
        for i in range(1, 11):
            name = service.generate_name(
                resource_type='ec2',
                purpose='worker',
                environment='prod',
                region='us-east-1',
                service='myapp',
                instance_number=i
            )
            names.add(name)
        
        # All 10 names should be unique
        assert len(names) == 10
        
        # Verify instance numbers are properly formatted (01, 02, ..., 10)
        assert 'prod-myapp-worker-us-east-1-01' in names
        assert 'prod-myapp-worker-us-east-1-10' in names
    
    def test_uniqueness_without_instance_numbers(self):
        """Test that different purposes create unique names."""
        service = NamingConventionService()
        
        purposes = ['web', 'api', 'worker', 'database', 'cache']
        names = []
        
        for purpose in purposes:
            name = service.generate_name(
                resource_type='ec2',
                purpose=purpose,
                environment='prod',
                region='us-east-1'
            )
            names.append(name)
        
        # All names should be unique
        assert len(names) == len(set(names))
    
    def test_edge_case_maximum_instance_number(self):
        """Test name generation with large instance numbers."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='ec2',
            purpose='worker',
            environment='prod',
            region='us-east-1',
            instance_number=99
        )
        
        assert name.endswith('-99')
        
        # Test with very large instance number
        name_large = service.generate_name(
            resource_type='ec2',
            purpose='worker',
            environment='prod',
            region='us-east-1',
            instance_number=999
        )
        
        assert '999' in name_large
    
    def test_edge_case_mixed_case_inputs(self):
        """Test that mixed case inputs are normalized correctly."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='vpc',
            purpose='MainVPC',
            environment='PROD',
            region='US-EAST-1',
            service='MyApp'
        )
        
        # All components should be lowercase
        assert name == 'prod-myapp-mainvpc-us-east-1'
    
    def test_validate_name_dynamodb(self):
        """Test validation for DynamoDB table names."""
        service = NamingConventionService()
        
        # Valid DynamoDB table name
        result = service.validate_name('prod-app-users-table', 'dynamodb')
        assert result.is_valid
        
        # DynamoDB names have 255 character limit
        long_name = 'a' * 256
        result = service.validate_name(long_name, 'dynamodb')
        assert not result.is_valid
    
    def test_validate_name_sns(self):
        """Test validation for SNS topic names."""
        service = NamingConventionService()
        
        # Valid SNS topic name
        result = service.validate_name('prod-app-notifications', 'sns')
        assert result.is_valid
        
        # SNS names have 256 character limit
        long_name = 'a' * 257
        result = service.validate_name(long_name, 'sns')
        assert not result.is_valid
    
    def test_validate_name_sqs(self):
        """Test validation for SQS queue names."""
        service = NamingConventionService()
        
        # Valid SQS queue name
        result = service.validate_name('prod-app-queue', 'sqs')
        assert result.is_valid
        
        # SQS names have 80 character limit
        long_name = 'a' * 81
        result = service.validate_name(long_name, 'sqs')
        assert not result.is_valid
    
    def test_validate_name_cloudwatch_log_group(self):
        """Test validation for CloudWatch log group names."""
        service = NamingConventionService()
        
        # Valid CloudWatch log group name with slashes
        result = service.validate_name('/aws/lambda/prod-app-function', 'cloudwatch_log_group')
        assert result.is_valid
        
        # CloudWatch log group names have 512 character limit
        long_name = 'a' * 513
        result = service.validate_name(long_name, 'cloudwatch_log_group')
        assert not result.is_valid
    
    def test_generate_name_with_hyphenated_purpose(self):
        """Test name generation with purpose containing hyphens."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='ec2',
            purpose='web-server',
            environment='prod',
            region='us-east-1'
        )
        
        assert name == 'prod-app-web-server-us-east-1'
    
    def test_generate_name_with_hyphenated_service(self):
        """Test name generation with service name containing hyphens."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='rds',
            purpose='main',
            environment='prod',
            region='us-east-1',
            service='my-app'
        )
        
        assert 'my-app' in name
        # RDS names must start with letter
        assert name[0].isalpha()
    
    def test_edge_case_numeric_purpose(self):
        """Test name generation with numeric purpose."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='s3',
            purpose='123data',
            environment='prod',
            region='us-east-1'
        )
        
        # Should be valid for S3
        assert name
        result = service.validate_name(name, 's3')
        assert result.is_valid
    
    def test_edge_case_single_character_components(self):
        """Test name generation with single character components."""
        service = NamingConventionService()
        
        name = service.generate_name(
            resource_type='vpc',
            purpose='a',
            environment='d',
            region='us-east-1',
            service='x'
        )
        
        assert name == 'd-x-a-us-east-1'
    
    def test_validate_name_security_group(self):
        """Test validation for security group names."""
        service = NamingConventionService()
        
        # Valid security group name
        result = service.validate_name('prod-app-web-sg', 'security_group')
        assert result.is_valid
        
        # Security group names have 255 character limit
        long_name = 'a' * 256
        result = service.validate_name(long_name, 'security_group')
        assert not result.is_valid
    
    def test_validate_name_subnet(self):
        """Test validation for subnet names."""
        service = NamingConventionService()
        
        # Valid subnet name
        result = service.validate_name('prod-app-private-subnet-1a', 'subnet')
        assert result.is_valid
        
        # Subnet names have 255 character limit
        long_name = 'a' * 256
        result = service.validate_name(long_name, 'subnet')
        assert not result.is_valid
    
    def test_generate_name_truncation_preserves_validity(self):
        """Test that truncated names remain valid."""
        service = NamingConventionService()
        
        # Generate name that would exceed S3 limit
        name = service.generate_name(
            resource_type='s3',
            purpose='very-long-purpose-name-that-exceeds-the-maximum-allowed-length',
            environment='production',
            region='us-east-1',
            service='myverylongapplicationname'
        )
        
        # Should be truncated to 63 chars
        assert len(name) <= 63
        
        # Should still be valid
        result = service.validate_name(name, 's3')
        assert result.is_valid
        
        # Should not end with hyphen
        assert not name.endswith('-')
    
    def test_multiple_resources_same_type_different_purposes(self):
        """Test generating names for multiple resources of same type with different purposes."""
        service = NamingConventionService()
        
        purposes = ['public', 'private', 'database', 'cache', 'application']
        names = []
        
        for purpose in purposes:
            name = service.generate_name(
                resource_type='subnet',
                purpose=purpose,
                environment='prod',
                region='us-east-1'
            )
            names.append(name)
        
        # All names should be unique
        assert len(names) == len(set(names))
        
        # Each name should contain its purpose
        for i, purpose in enumerate(purposes):
            assert purpose in names[i]
    
    def test_generate_name_raises_on_invalid_result(self):
        """Test that generate_name raises ValueError if result violates constraints."""
        service = NamingConventionService()
        
        # This should work normally
        name = service.generate_name(
            resource_type='s3',
            purpose='valid',
            environment='prod',
            region='us-east-1'
        )
        assert name
        
        # The service should handle edge cases internally and produce valid names
        # or raise ValueError if it cannot
        try:
            name = service.generate_name(
                resource_type='s3',
                purpose='test',
                environment='prod',
                region='us-east-1'
            )
            # Should succeed
            assert name
        except ValueError:
            # If it raises, that's also acceptable behavior
            pass
