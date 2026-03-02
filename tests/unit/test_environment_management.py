"""Unit tests for environment management functionality."""

import pytest
from cdk_templates.config_loader import ConfigurationLoader, ConfigurationError
from cdk_templates.deployment_rules import ProductionProtectionRule
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig
)


class TestEnvironmentOverrides:
    """Test environment-specific configuration overrides."""
    
    def test_apply_environment_overrides_basic(self):
        """Test basic environment override application."""
        loader = ConfigurationLoader()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={
                        "vpc-main": {
                            "properties": {
                                "cidr": "10.1.0.0/16"
                            }
                        }
                    }
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
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        # Apply dev environment overrides
        result = loader.apply_environment_overrides(config, "dev")
        
        # Verify override was applied
        vpc_resource = next(r for r in result.resources if r.logical_id == "vpc-main")
        assert vpc_resource.properties["cidr"] == "10.1.0.0/16"
        assert vpc_resource.properties["availability_zones"] == 3  # Unchanged
    
    def test_apply_environment_overrides_multiple_resources(self):
        """Test overrides for multiple resources."""
        loader = ConfigurationLoader()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={
                "prod": EnvironmentConfig(
                    name="prod",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={
                        "rds-main": {
                            "properties": {
                                "multi_az": True,
                                "backup_retention_days": 30
                            }
                        },
                        "s3-data": {
                            "properties": {
                                "versioning_enabled": True
                            }
                        }
                    }
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "engine": "postgres",
                        "multi_az": False,
                        "backup_retention_days": 7
                    },
                    tags={},
                    depends_on=[]
                ),
                ResourceConfig(
                    logical_id="s3-data",
                    resource_type="s3",
                    properties={
                        "versioning_enabled": False
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        # Apply prod environment overrides
        result = loader.apply_environment_overrides(config, "prod")
        
        # Verify RDS overrides
        rds_resource = next(r for r in result.resources if r.logical_id == "rds-main")
        assert rds_resource.properties["multi_az"] is True
        assert rds_resource.properties["backup_retention_days"] == 30
        assert rds_resource.properties["engine"] == "postgres"  # Unchanged
        
        # Verify S3 overrides
        s3_resource = next(r for r in result.resources if r.logical_id == "s3-data")
        assert s3_resource.properties["versioning_enabled"] is True
    
    def test_apply_environment_overrides_nested_properties(self):
        """Test overrides for nested property structures."""
        loader = ConfigurationLoader()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={
                "prod": EnvironmentConfig(
                    name="prod",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={
                        "ec2-web": {
                            "properties": {
                                "root_volume": {
                                    "size": 100,
                                    "encrypted": True
                                }
                            }
                        }
                    }
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "instance_type": "t3.medium",
                        "root_volume": {
                            "size": 30,
                            "encrypted": False,
                            "volume_type": "gp3"
                        }
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        # Apply prod environment overrides
        result = loader.apply_environment_overrides(config, "prod")
        
        # Verify nested overrides
        ec2_resource = next(r for r in result.resources if r.logical_id == "ec2-web")
        assert ec2_resource.properties["root_volume"]["size"] == 100
        assert ec2_resource.properties["root_volume"]["encrypted"] is True
        assert ec2_resource.properties["root_volume"]["volume_type"] == "gp3"  # Unchanged
        assert ec2_resource.properties["instance_type"] == "t3.medium"  # Unchanged
    
    def test_apply_environment_overrides_tags(self):
        """Test tag overrides."""
        loader = ConfigurationLoader()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={
                "prod": EnvironmentConfig(
                    name="prod",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={
                        "vpc-main": {
                            "tags": {
                                "Compliance": "PCI-DSS",
                                "Backup": "Required"
                            }
                        }
                    }
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={"cidr": "10.0.0.0/16"},
                    tags={
                        "Application": "WebApp",
                        "Backup": "Optional"
                    },
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        # Apply prod environment overrides
        result = loader.apply_environment_overrides(config, "prod")
        
        # Verify tag overrides
        vpc_resource = next(r for r in result.resources if r.logical_id == "vpc-main")
        assert vpc_resource.tags["Compliance"] == "PCI-DSS"
        assert vpc_resource.tags["Backup"] == "Required"  # Overridden
        assert vpc_resource.tags["Application"] == "WebApp"  # Unchanged
    
    def test_apply_environment_overrides_no_overrides(self):
        """Test that config is unchanged when no overrides exist."""
        loader = ConfigurationLoader()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={}  # No overrides
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={"cidr": "10.0.0.0/16"},
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        # Apply dev environment overrides
        result = loader.apply_environment_overrides(config, "dev")
        
        # Verify nothing changed
        vpc_resource = next(r for r in result.resources if r.logical_id == "vpc-main")
        assert vpc_resource.properties["cidr"] == "10.0.0.0/16"
    
    def test_apply_environment_overrides_nonexistent_environment(self):
        """Test error when environment doesn't exist."""
        loader = ConfigurationLoader()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={
                "dev": EnvironmentConfig(
                    name="dev",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={}
                )
            },
            resources=[],
            deployment_rules=[]
        )
        
        # Try to apply overrides for non-existent environment
        with pytest.raises(ConfigurationError) as exc_info:
            loader.apply_environment_overrides(config, "prod")
        
        assert "Environment 'prod' not found" in str(exc_info.value)
    
    def test_apply_environment_overrides_resource_not_affected(self):
        """Test that resources without overrides are not affected."""
        loader = ConfigurationLoader()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={
                "prod": EnvironmentConfig(
                    name="prod",
                    account_id="123456789012",
                    region="us-east-1",
                    tags={},
                    overrides={
                        "vpc-main": {
                            "properties": {
                                "cidr": "10.1.0.0/16"
                            }
                        }
                    }
                )
            },
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={"cidr": "10.0.0.0/16"},
                    tags={},
                    depends_on=[]
                ),
                ResourceConfig(
                    logical_id="s3-data",
                    resource_type="s3",
                    properties={"versioning_enabled": False},
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        # Apply prod environment overrides
        result = loader.apply_environment_overrides(config, "prod")
        
        # Verify vpc-main was overridden
        vpc_resource = next(r for r in result.resources if r.logical_id == "vpc-main")
        assert vpc_resource.properties["cidr"] == "10.1.0.0/16"
        
        # Verify s3-data was not affected
        s3_resource = next(r for r in result.resources if r.logical_id == "s3-data")
        assert s3_resource.properties["versioning_enabled"] is False


class TestProductionProtection:
    """Test production resource protection functionality."""
    
    def test_production_protection_enforces_multi_az(self):
        """Test that Multi-AZ is enforced for RDS in production."""
        rule = ProductionProtectionRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "engine": "postgres",
                        "instance_class": "db.t3.medium",
                        "allocated_storage": 100,
                        "multi_az": False
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert result.success
        assert len(result.modifications) >= 1
        
        # Verify Multi-AZ was enabled
        rds_resource = next(r for r in config.resources if r.logical_id == "rds-main")
        assert rds_resource.properties["multi_az"] is True
        
        # Verify modification was logged
        multi_az_mod = next(
            (m for m in result.modifications if m.field_path == "properties.multi_az"),
            None
        )
        assert multi_az_mod is not None
        assert multi_az_mod.new_value is True
    
    def test_production_protection_requires_protected_properties(self):
        """Test that protected properties must be explicitly set in production."""
        rule = ProductionProtectionRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        # Missing protected properties: engine, instance_class, allocated_storage
                        "multi_az": True
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert not result.success
        assert len(result.rejections) == 3  # engine, instance_class, allocated_storage
        
        # Verify rejection messages
        rejection_props = {r.reason for r in result.rejections}
        assert any("engine" in r for r in rejection_props)
        assert any("instance_class" in r for r in rejection_props)
        assert any("allocated_storage" in r for r in rejection_props)
    
    def test_production_protection_critical_resource_validation(self):
        """Test validation of critical resources in production."""
        rule = ProductionProtectionRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "instance_class": "db.t3.medium",
                        # Missing critical properties: engine, allocated_storage
                    },
                    tags={"Critical": "true"},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert not result.success
        # Should reject due to missing protected and replacement properties
        assert len(result.rejections) > 0
    
    def test_production_protection_marks_rds_as_critical(self):
        """Test that RDS resources are automatically marked as critical in production."""
        rule = ProductionProtectionRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "engine": "postgres",
                        "instance_class": "db.t3.medium",
                        "allocated_storage": 100,
                        "multi_az": True
                    },
                    tags={},  # No Critical tag
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert result.success
        
        # Verify Critical tag was added
        rds_resource = next(r for r in config.resources if r.logical_id == "rds-main")
        assert rds_resource.tags.get("Critical") == "true"
        
        # Verify modification was logged
        critical_mod = next(
            (m for m in result.modifications if "Critical" in m.field_path),
            None
        )
        assert critical_mod is not None
    
    def test_production_protection_not_applied_to_dev(self):
        """Test that production protection is not applied to dev environment."""
        rule = ProductionProtectionRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        # Missing protected properties - should be OK in dev
                        "multi_az": False
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        # Should succeed without modifications or rejections
        assert result.success
        assert len(result.rejections) == 0




class TestProductionSecurityPolicies:
    """Test environment-specific security policies."""
    
    def test_production_security_enforces_rds_encryption(self):
        """Test that RDS encryption is enforced in production."""
        from cdk_templates.deployment_rules import ProductionSecurityPolicyRule
        
        rule = ProductionSecurityPolicyRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "engine": "postgres",
                        "instance_class": "db.t3.medium",
                        "allocated_storage": 100,
                        "encryption_enabled": False,
                        "storage_encrypted": False
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert result.success
        
        # Verify encryption was enabled
        rds_resource = next(r for r in config.resources if r.logical_id == "rds-main")
        assert rds_resource.properties["encryption_enabled"] is True
        assert rds_resource.properties["storage_encrypted"] is True
        
        # Verify modifications were logged (should have both encryption properties modified)
        assert len(result.modifications) >= 2
        encryption_enabled_mod = any(
            m.field_path == "properties.encryption_enabled" for m in result.modifications
        )
        storage_encrypted_mod = any(
            m.field_path == "properties.storage_encrypted" for m in result.modifications
        )
        assert encryption_enabled_mod
        assert storage_encrypted_mod
    
    def test_production_security_enforces_rds_multi_az(self):
        """Test that RDS Multi-AZ is enforced in production."""
        from cdk_templates.deployment_rules import ProductionSecurityPolicyRule
        
        rule = ProductionSecurityPolicyRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "engine": "postgres",
                        "multi_az": False
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert result.success
        
        # Verify Multi-AZ was enabled
        rds_resource = next(r for r in config.resources if r.logical_id == "rds-main")
        assert rds_resource.properties["multi_az"] is True
    
    def test_production_security_enforces_s3_encryption(self):
        """Test that S3 encryption is enforced in production."""
        from cdk_templates.deployment_rules import ProductionSecurityPolicyRule
        
        rule = ProductionSecurityPolicyRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="s3-data",
                    resource_type="s3",
                    properties={
                        "versioning_enabled": False
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert result.success
        
        # Verify encryption and versioning were enabled
        s3_resource = next(r for r in config.resources if r.logical_id == "s3-data")
        assert s3_resource.properties["encryption"] == "aws:kms"
        assert s3_resource.properties["versioning_enabled"] is True
        assert s3_resource.properties["block_public_access"] is True
    
    def test_production_security_enforces_ec2_encryption(self):
        """Test that EC2 volume encryption is enforced in production."""
        from cdk_templates.deployment_rules import ProductionSecurityPolicyRule
        
        rule = ProductionSecurityPolicyRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="ec2-web",
                    resource_type="ec2",
                    properties={
                        "instance_type": "t3.medium",
                        "root_volume": {
                            "size": 30,
                            "encrypted": False
                        }
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert result.success
        
        # Verify encryption and monitoring were enabled
        ec2_resource = next(r for r in config.resources if r.logical_id == "ec2-web")
        assert ec2_resource.properties["root_volume"]["encrypted"] is True
        assert ec2_resource.properties["enable_detailed_monitoring"] is True
    
    def test_production_security_enforces_vpc_flow_logs(self):
        """Test that VPC Flow Logs are enforced in production."""
        from cdk_templates.deployment_rules import ProductionSecurityPolicyRule
        
        rule = ProductionSecurityPolicyRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="vpc-main",
                    resource_type="vpc",
                    properties={
                        "cidr": "10.0.0.0/16",
                        "availability_zones": 2,
                        "enable_flow_logs": False
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert result.success
        
        # Verify flow logs and AZs were configured
        vpc_resource = next(r for r in config.resources if r.logical_id == "vpc-main")
        assert vpc_resource.properties["enable_flow_logs"] is True
        assert vpc_resource.properties["availability_zones"] >= 3
    
    def test_production_security_not_applied_to_dev(self):
        """Test that production security policies are not applied to dev."""
        from cdk_templates.deployment_rules import ProductionSecurityPolicyRule
        
        rule = ProductionSecurityPolicyRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "engine": "postgres",
                        "encryption_enabled": False,
                        "multi_az": False
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        # Should succeed without modifications
        assert result.success
        assert len(result.modifications) == 0
        
        # Verify nothing was changed
        rds_resource = next(r for r in config.resources if r.logical_id == "rds-main")
        assert rds_resource.properties["encryption_enabled"] is False
        assert rds_resource.properties["multi_az"] is False
    
    def test_production_security_enforces_minimum_backup_retention(self):
        """Test that minimum backup retention is enforced for RDS in production."""
        from cdk_templates.deployment_rules import ProductionSecurityPolicyRule
        
        rule = ProductionSecurityPolicyRule()
        
        config = Configuration(
            version="1.0",
            metadata=ConfigMetadata(
                project="test",
                owner="team",
                cost_center="eng",
                description="Test"
            ),
            environments={},
            resources=[
                ResourceConfig(
                    logical_id="rds-main",
                    resource_type="rds",
                    properties={
                        "engine": "postgres",
                        "backup_retention_days": 1
                    },
                    tags={},
                    depends_on=[]
                )
            ],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert result.success
        
        # Verify backup retention was increased
        rds_resource = next(r for r in config.resources if r.logical_id == "rds-main")
        assert rds_resource.properties["backup_retention_days"] >= 7
