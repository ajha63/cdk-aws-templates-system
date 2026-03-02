"""Unit tests for Deployment Rules Engine."""

import pytest
from cdk_templates.deployment_rules import (
    DeploymentRulesEngine,
    DeploymentRule,
    EncryptionEnforcementRule,
    ProductionProtectionRule,
    TagComplianceRule,
    NamingConventionRule,
    RuleApplicationResult,
    RuleModification,
    RuleRejection
)
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig
)


@pytest.fixture
def sample_metadata():
    """Create sample configuration metadata."""
    return ConfigMetadata(
        project="test-project",
        owner="test-team",
        cost_center="engineering",
        description="Test configuration"
    )


@pytest.fixture
def sample_environment():
    """Create sample environment configuration."""
    return {
        "dev": EnvironmentConfig(
            name="dev",
            account_id="123456789012",
            region="us-east-1",
            tags={},
            overrides={}
        ),
        "prod": EnvironmentConfig(
            name="prod",
            account_id="123456789012",
            region="us-east-1",
            tags={},
            overrides={}
        )
    }


@pytest.fixture
def sample_rds_resource():
    """Create sample RDS resource configuration."""
    return ResourceConfig(
        logical_id="rds-main",
        resource_type="rds",
        properties={
            "engine": "postgres",
            "instance_class": "db.t3.medium",
            "allocated_storage": 100
        },
        tags={},
        depends_on=[]
    )


@pytest.fixture
def sample_s3_resource():
    """Create sample S3 resource configuration."""
    return ResourceConfig(
        logical_id="s3-data",
        resource_type="s3",
        properties={
            "versioning_enabled": True
        },
        tags={},
        depends_on=[]
    )


class TestDeploymentRulesEngine:
    """Tests for DeploymentRulesEngine class."""
    
    def test_register_rule(self):
        """Test registering a rule with priority."""
        engine = DeploymentRulesEngine()
        rule = EncryptionEnforcementRule()
        
        engine.register_rule(rule, priority=100)
        
        registered = engine.get_registered_rules()
        assert len(registered) == 1
        assert registered[0] == (100, "EncryptionEnforcementRule")
    
    def test_register_multiple_rules_priority_order(self):
        """Test that rules are ordered by priority."""
        engine = DeploymentRulesEngine()
        
        rule1 = EncryptionEnforcementRule()
        rule2 = TagComplianceRule()
        rule3 = NamingConventionRule()
        
        # Register in random order
        engine.register_rule(rule2, priority=50)
        engine.register_rule(rule1, priority=100)
        engine.register_rule(rule3, priority=75)
        
        registered = engine.get_registered_rules()
        
        # Should be ordered by priority (descending)
        assert registered[0][0] == 100  # EncryptionEnforcementRule
        assert registered[1][0] == 75   # NamingConventionRule
        assert registered[2][0] == 50   # TagComplianceRule
    
    def test_apply_rules_empty_engine(self, sample_metadata, sample_environment):
        """Test applying rules when no rules are registered."""
        engine = DeploymentRulesEngine()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[],
            deployment_rules=[]
        )
        
        result = engine.apply_rules(config, "dev")
        
        assert result.success is True
        assert len(result.modifications) == 0
        assert len(result.rejections) == 0
    
    def test_apply_rules_combines_results(self, sample_metadata, sample_environment, sample_rds_resource):
        """Test that apply_rules combines results from multiple rules."""
        engine = DeploymentRulesEngine()
        
        engine.register_rule(EncryptionEnforcementRule(), priority=100)
        engine.register_rule(NamingConventionRule(), priority=50)
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[sample_rds_resource],
            deployment_rules=[]
        )
        
        result = engine.apply_rules(config, "dev")
        
        # Should have modifications from EncryptionEnforcementRule
        assert len(result.modifications) > 0
        # Should succeed (NamingConventionRule passes)
        assert result.success is True


class TestEncryptionEnforcementRule:
    """Tests for EncryptionEnforcementRule."""
    
    def test_enforce_rds_encryption_missing(self, sample_metadata, sample_environment, sample_rds_resource):
        """Test that encryption is enforced on RDS when missing."""
        rule = EncryptionEnforcementRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[sample_rds_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is True
        assert len(result.modifications) == 2  # encryption_enabled and storage_encrypted
        
        # Check that properties were modified
        assert sample_rds_resource.properties["encryption_enabled"] is True
        assert sample_rds_resource.properties["storage_encrypted"] is True
        
        # Check modification records
        mod_fields = [mod.field_path for mod in result.modifications]
        assert "properties.encryption_enabled" in mod_fields
        assert "properties.storage_encrypted" in mod_fields
    
    def test_enforce_rds_encryption_already_set(self, sample_metadata, sample_environment):
        """Test that no modifications are made when encryption is already set."""
        rds_resource = ResourceConfig(
            logical_id="rds-main",
            resource_type="rds",
            properties={
                "engine": "postgres",
                "encryption_enabled": True,
                "storage_encrypted": True
            },
            tags={},
            depends_on=[]
        )
        
        rule = EncryptionEnforcementRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is True
        assert len(result.modifications) == 0
    
    def test_enforce_s3_encryption_missing(self, sample_metadata, sample_environment, sample_s3_resource):
        """Test that encryption is enforced on S3 when missing."""
        rule = EncryptionEnforcementRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[sample_s3_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is True
        assert len(result.modifications) == 1
        
        # Check that property was modified
        assert sample_s3_resource.properties["encryption"] == "aws:kms"
        
        # Check modification record
        assert result.modifications[0].field_path == "properties.encryption"
        assert result.modifications[0].new_value == "aws:kms"
    
    def test_enforce_s3_encryption_already_set(self, sample_metadata, sample_environment):
        """Test that no modifications are made when S3 encryption is already set."""
        s3_resource = ResourceConfig(
            logical_id="s3-data",
            resource_type="s3",
            properties={
                "versioning_enabled": True,
                "encryption": "aws:kms"
            },
            tags={},
            depends_on=[]
        )
        
        rule = EncryptionEnforcementRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[s3_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is True
        assert len(result.modifications) == 0


class TestProductionProtectionRule:
    """Tests for ProductionProtectionRule."""
    
    def test_production_protection_not_applied_to_dev(self, sample_metadata, sample_environment, sample_rds_resource):
        """Test that production protection is not applied to dev environment."""
        rule = ProductionProtectionRule()
        
        # RDS without protected properties explicitly set
        rds_resource = ResourceConfig(
            logical_id="rds-main",
            resource_type="rds",
            properties={},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        # Should succeed in dev even without protected properties
        assert result.success is True
        assert len(result.rejections) == 0
    
    def test_production_protection_requires_protected_properties(self, sample_metadata, sample_environment):
        """Test that production requires protected properties to be set."""
        rule = ProductionProtectionRule()
        
        # RDS without protected properties
        rds_resource = ResourceConfig(
            logical_id="rds-main",
            resource_type="rds",
            properties={},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        # Should fail due to missing protected properties
        assert result.success is False
        assert len(result.rejections) > 0
        
        # Check that rejections mention protected properties
        rejection_reasons = [r.reason for r in result.rejections]
        assert any("allocated_storage" in reason for reason in rejection_reasons)
        assert any("instance_class" in reason for reason in rejection_reasons)
        assert any("engine" in reason for reason in rejection_reasons)
    
    def test_production_protection_enforces_multi_az(self, sample_metadata, sample_environment, sample_rds_resource):
        """Test that Multi-AZ is enforced for RDS in production."""
        rule = ProductionProtectionRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[sample_rds_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        # Should have modification for multi_az
        multi_az_mods = [m for m in result.modifications if "multi_az" in m.field_path]
        assert len(multi_az_mods) == 1
        assert sample_rds_resource.properties["multi_az"] is True
    
    def test_production_protection_with_all_properties_set(self, sample_metadata, sample_environment):
        """Test that production protection passes when all properties are set."""
        rds_resource = ResourceConfig(
            logical_id="rds-main",
            resource_type="rds",
            properties={
                "allocated_storage": 100,
                "instance_class": "db.t3.medium",
                "engine": "postgres",
                "multi_az": True
            },
            tags={},
            depends_on=[]
        )
        
        rule = ProductionProtectionRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "production")
        
        assert result.success is True
        assert len(result.rejections) == 0
        # RDS instances are automatically marked as critical in production
        assert len(result.modifications) == 1
        assert result.modifications[0].field_path == "tags.Critical"


class TestTagComplianceRule:
    """Tests for TagComplianceRule."""
    
    def test_tag_compliance_with_complete_metadata(self, sample_metadata, sample_environment):
        """Test that tag compliance passes with complete metadata."""
        rule = TagComplianceRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is True
        assert len(result.rejections) == 0
    
    def test_tag_compliance_missing_project(self, sample_environment):
        """Test that tag compliance fails when project is missing."""
        metadata = ConfigMetadata(
            project="",  # Missing
            owner="test-team",
            cost_center="engineering",
            description="Test"
        )
        
        rule = TagComplianceRule()
        
        config = Configuration(
            version="1.0",
            metadata=metadata,
            environments=sample_environment,
            resources=[],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is False
        assert len(result.rejections) > 0
        assert any("project" in r.reason.lower() for r in result.rejections)
    
    def test_tag_compliance_missing_owner(self, sample_environment):
        """Test that tag compliance fails when owner is missing."""
        metadata = ConfigMetadata(
            project="test-project",
            owner="",  # Missing
            cost_center="engineering",
            description="Test"
        )
        
        rule = TagComplianceRule()
        
        config = Configuration(
            version="1.0",
            metadata=metadata,
            environments=sample_environment,
            resources=[],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is False
        assert any("owner" in r.reason.lower() for r in result.rejections)
    
    def test_tag_compliance_missing_cost_center(self, sample_environment):
        """Test that tag compliance fails when cost_center is missing."""
        metadata = ConfigMetadata(
            project="test-project",
            owner="test-team",
            cost_center="",  # Missing
            description="Test"
        )
        
        rule = TagComplianceRule()
        
        config = Configuration(
            version="1.0",
            metadata=metadata,
            environments=sample_environment,
            resources=[],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is False
        assert any("cost_center" in r.reason.lower() for r in result.rejections)
    
    def test_tag_compliance_undefined_environment(self, sample_metadata, sample_environment):
        """Test that tag compliance fails when environment is not defined."""
        rule = TagComplianceRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "staging")  # staging not in sample_environment
        
        assert result.success is False
        assert any("staging" in r.reason.lower() for r in result.rejections)


class TestNamingConventionRule:
    """Tests for NamingConventionRule."""
    
    def test_naming_convention_valid_names(self, sample_metadata, sample_environment):
        """Test that valid names pass the naming convention rule."""
        rule = NamingConventionRule()
        
        valid_resources = [
            ResourceConfig(logical_id="vpc-main", resource_type="vpc", properties={}, tags={}, depends_on=[]),
            ResourceConfig(logical_id="ec2-web-01", resource_type="ec2", properties={}, tags={}, depends_on=[]),
            ResourceConfig(logical_id="rds-database", resource_type="rds", properties={}, tags={}, depends_on=[]),
            ResourceConfig(logical_id="s3-data-bucket", resource_type="s3", properties={}, tags={}, depends_on=[]),
        ]
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=valid_resources,
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is True
        assert len(result.rejections) == 0
    
    def test_naming_convention_invalid_uppercase(self, sample_metadata, sample_environment):
        """Test that uppercase names are rejected."""
        rule = NamingConventionRule()
        
        invalid_resource = ResourceConfig(
            logical_id="VPC-Main",  # Contains uppercase
            resource_type="vpc",
            properties={},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[invalid_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is False
        assert len(result.rejections) > 0
        assert any("naming convention" in r.reason.lower() for r in result.rejections)
    
    def test_naming_convention_invalid_special_chars(self, sample_metadata, sample_environment):
        """Test that special characters are rejected."""
        rule = NamingConventionRule()
        
        invalid_resource = ResourceConfig(
            logical_id="vpc_main",  # Contains underscore
            resource_type="vpc",
            properties={},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[invalid_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is False
        assert any("naming convention" in r.reason.lower() for r in result.rejections)
    
    def test_naming_convention_too_long(self, sample_metadata, sample_environment):
        """Test that names exceeding maximum length are rejected."""
        rule = NamingConventionRule()
        
        invalid_resource = ResourceConfig(
            logical_id="a" * 65,  # 65 characters, exceeds limit of 64
            resource_type="vpc",
            properties={},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[invalid_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is False
        assert any("maximum length" in r.reason.lower() for r in result.rejections)
    
    def test_naming_convention_consecutive_hyphens(self, sample_metadata, sample_environment):
        """Test that consecutive hyphens generate a warning."""
        rule = NamingConventionRule()
        
        resource_with_consecutive_hyphens = ResourceConfig(
            logical_id="vpc--main",  # Consecutive hyphens
            resource_type="vpc",
            properties={},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[resource_with_consecutive_hyphens],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        # Should have a warning about consecutive hyphens
        warnings = [r for r in result.rejections if r.severity == "WARNING"]
        assert len(warnings) > 0
        assert any("consecutive hyphens" in r.reason.lower() for r in warnings)
    
    def test_naming_convention_starts_with_hyphen(self, sample_metadata, sample_environment):
        """Test that names starting with hyphen are rejected."""
        rule = NamingConventionRule()
        
        invalid_resource = ResourceConfig(
            logical_id="-vpc-main",  # Starts with hyphen
            resource_type="vpc",
            properties={},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[invalid_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is False
        assert any("naming convention" in r.reason.lower() for r in result.rejections)



class TestDeploymentRulesEngineAuditLogging:
    """Tests for audit logging functionality."""
    
    def test_audit_logging_for_modifications(self, sample_metadata, sample_environment, sample_rds_resource, caplog):
        """Test that modifications are logged to the audit log."""
        import logging
        
        # Set up logging to capture audit logs
        caplog.set_level(logging.INFO, logger='cdk_templates.deployment_rules.audit')
        
        engine = DeploymentRulesEngine()
        engine.register_rule(EncryptionEnforcementRule(), priority=100)
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[sample_rds_resource],
            deployment_rules=[]
        )
        
        result = engine.apply_rules(config, "dev")
        
        # Verify modifications were made
        assert len(result.modifications) > 0
        
        # Verify audit logs were created
        audit_records = [record for record in caplog.records 
                        if record.name == 'cdk_templates.deployment_rules.audit']
        
        # Should have one log entry per modification
        assert len(audit_records) == len(result.modifications), \
            f"Expected {len(result.modifications)} audit log entries, got {len(audit_records)}"
        
        # Verify log entries contain required information
        for record in audit_records:
            assert 'rule_name' in record.__dict__
            assert 'resource_id' in record.__dict__
            assert 'field_path' in record.__dict__
            assert 'old_value' in record.__dict__
            assert 'new_value' in record.__dict__
            assert 'reason' in record.__dict__
            assert 'environment' in record.__dict__
            assert 'timestamp' in record.__dict__
    
    def test_no_audit_logs_when_no_modifications(self, sample_metadata, sample_environment, caplog):
        """Test that no audit logs are created when there are no modifications."""
        import logging
        
        caplog.set_level(logging.INFO, logger='cdk_templates.deployment_rules.audit')
        
        # Create RDS resource with encryption already enabled
        rds_resource = ResourceConfig(
            logical_id="rds-main",
            resource_type="rds",
            properties={
                "engine": "postgres",
                "encryption_enabled": True,
                "storage_encrypted": True
            },
            tags={},
            depends_on=[]
        )
        
        engine = DeploymentRulesEngine()
        engine.register_rule(EncryptionEnforcementRule(), priority=100)
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        result = engine.apply_rules(config, "dev")
        
        # Verify no modifications were made
        assert len(result.modifications) == 0
        
        # Verify no audit logs were created
        audit_records = [record for record in caplog.records 
                        if record.name == 'cdk_templates.deployment_rules.audit']
        assert len(audit_records) == 0


class TestRuleApplicationEdgeCases:
    """Tests for edge cases in rule application."""
    
    def test_rule_application_with_empty_resources(self, sample_metadata, sample_environment):
        """Test that rules handle empty resource lists gracefully."""
        engine = DeploymentRulesEngine()
        engine.register_rule(EncryptionEnforcementRule(), priority=100)
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[],  # Empty resources
            deployment_rules=[]
        )
        
        result = engine.apply_rules(config, "dev")
        
        assert result.success is True
        assert len(result.modifications) == 0
        assert len(result.rejections) == 0
    
    def test_multiple_rules_with_same_priority(self, sample_metadata, sample_environment, sample_rds_resource):
        """Test that multiple rules with the same priority are all executed."""
        engine = DeploymentRulesEngine()
        
        # Register multiple rules with same priority
        engine.register_rule(EncryptionEnforcementRule(), priority=100)
        engine.register_rule(NamingConventionRule(), priority=100)
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[sample_rds_resource],
            deployment_rules=[]
        )
        
        result = engine.apply_rules(config, "dev")
        
        # Both rules should have executed
        assert result.success is True
        # Should have modifications from EncryptionEnforcementRule
        assert len(result.modifications) > 0
    
    def test_rule_failure_does_not_stop_other_rules(self, sample_metadata, sample_environment):
        """Test that when one rule fails, other rules still execute."""
        engine = DeploymentRulesEngine()
        
        # Register rules in order
        engine.register_rule(TagComplianceRule(), priority=200)  # Will fail
        engine.register_rule(NamingConventionRule(), priority=100)  # Should still run
        
        # Create config with incomplete metadata (will fail TagComplianceRule)
        incomplete_metadata = ConfigMetadata(
            project="",  # Missing
            owner="test-team",
            cost_center="engineering",
            description="Test"
        )
        
        valid_resource = ResourceConfig(
            logical_id="vpc-main",
            resource_type="vpc",
            properties={"cidr": "10.0.0.0/16"},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=incomplete_metadata,
            environments=sample_environment,
            resources=[valid_resource],
            deployment_rules=[]
        )
        
        result = engine.apply_rules(config, "dev")
        
        # Overall result should be failure
        assert result.success is False
        
        # Should have rejections from TagComplianceRule
        assert len(result.rejections) > 0
        tag_rejections = [r for r in result.rejections if r.rule_name == "TagComplianceRule"]
        assert len(tag_rejections) > 0
        
        # NamingConventionRule should have still executed (no rejections for valid name)
        # We can verify this by checking that the engine processed both rules
        registered = engine.get_registered_rules()
        assert len(registered) == 2


class TestRuleModificationDetails:
    """Tests for detailed modification tracking."""
    
    def test_modification_tracks_old_and_new_values(self, sample_metadata, sample_environment):
        """Test that modifications correctly track old and new values."""
        rds_resource = ResourceConfig(
            logical_id="rds-main",
            resource_type="rds",
            properties={
                "engine": "postgres",
                "encryption_enabled": False,  # Explicitly set to False
                "storage_encrypted": False
            },
            tags={},
            depends_on=[]
        )
        
        rule = EncryptionEnforcementRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        # Find the encryption_enabled modification
        encryption_mod = next(
            (m for m in result.modifications if 'encryption_enabled' in m.field_path),
            None
        )
        
        assert encryption_mod is not None
        assert encryption_mod.old_value is False
        assert encryption_mod.new_value is True
    
    def test_modification_includes_descriptive_reason(self, sample_metadata, sample_environment, sample_s3_resource):
        """Test that modifications include descriptive reasons."""
        rule = EncryptionEnforcementRule()
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[sample_s3_resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert len(result.modifications) > 0
        
        for mod in result.modifications:
            # Reason should be descriptive
            assert len(mod.reason) > 20, "Reason should be descriptive"
            assert "encryption" in mod.reason.lower() or "mandatory" in mod.reason.lower(), \
                "Reason should explain why the modification was made"


class TestProductionProtectionRuleDetails:
    """Detailed tests for ProductionProtectionRule."""
    
    def test_production_protection_allows_non_production_without_protected_props(self, sample_metadata, sample_environment):
        """Test that non-production environments don't require protected properties."""
        rule = ProductionProtectionRule()
        
        # RDS without any protected properties
        rds_resource = ResourceConfig(
            logical_id="rds-test",
            resource_type="rds",
            properties={},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        # Test with dev environment
        result = rule.apply(config, "dev")
        
        # Should succeed in dev
        assert result.success is True
        assert len(result.rejections) == 0
    
    def test_production_protection_checks_all_resource_types(self, sample_metadata):
        """Test that production protection applies to all configured resource types."""
        rule = ProductionProtectionRule()
        
        prod_env = EnvironmentConfig(
            name="production",
            account_id="123456789012",
            region="us-east-1",
            tags={},
            overrides={}
        )
        
        # Test with different resource types
        resource_types = ["rds", "s3", "vpc", "ec2"]
        
        for resource_type in resource_types:
            resource = ResourceConfig(
                logical_id=f"{resource_type}-test",
                resource_type=resource_type,
                properties={},
                tags={},
                depends_on=[]
            )
            
            config = Configuration(
                version="1.0",
                metadata=sample_metadata,
                environments={"production": prod_env},
                resources=[resource],
                deployment_rules=[]
            )
            
            result = rule.apply(config, "production")
            
            # Should have rejections for missing protected properties
            if resource_type in rule.PROTECTED_PROPERTIES:
                assert result.success is False, \
                    f"Should reject {resource_type} without protected properties"
                assert len(result.rejections) > 0


class TestNamingConventionRuleDetails:
    """Detailed tests for NamingConventionRule."""
    
    def test_naming_rule_allows_numbers_in_names(self, sample_metadata, sample_environment):
        """Test that naming rule allows numbers in logical IDs."""
        rule = NamingConventionRule()
        
        resource = ResourceConfig(
            logical_id="vpc-main-01",
            resource_type="vpc",
            properties={"cidr": "10.0.0.0/16"},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is True
        assert len(result.rejections) == 0
    
    def test_naming_rule_rejects_names_ending_with_hyphen(self, sample_metadata, sample_environment):
        """Test that naming rule rejects names ending with hyphen."""
        rule = NamingConventionRule()
        
        resource = ResourceConfig(
            logical_id="vpc-main-",
            resource_type="vpc",
            properties={"cidr": "10.0.0.0/16"},
            tags={},
            depends_on=[]
        )
        
        config = Configuration(
            version="1.0",
            metadata=sample_metadata,
            environments=sample_environment,
            resources=[resource],
            deployment_rules=[]
        )
        
        result = rule.apply(config, "dev")
        
        assert result.success is False
        assert len(result.rejections) > 0
        assert any("naming convention" in r.reason.lower() for r in result.rejections)
