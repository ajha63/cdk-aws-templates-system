"""Property-based tests for Deployment Rules Engine."""

import pytest
from hypothesis import given, settings, strategies as st
from hypothesis.strategies import composite

from cdk_templates.deployment_rules import (
    DeploymentRulesEngine,
    EncryptionEnforcementRule,
    ProductionProtectionRule,
    TagComplianceRule,
    NamingConventionRule,
)
from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
)
from tests.property.strategies import (
    configuration_strategy,
    config_metadata_strategy,
    environment_config_strategy,
    resource_config_strategy,
)


@composite
def rds_without_encryption_strategy(draw):
    """Generate RDS resource without encryption enabled."""
    logical_id = draw(st.text(
        min_size=3,
        max_size=30,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'
    ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
    
    return ResourceConfig(
        logical_id=logical_id,
        resource_type='rds',
        properties={
            'logical_id': logical_id,
            'engine': draw(st.sampled_from(['postgres', 'mysql', 'mariadb'])),
            'instance_class': draw(st.sampled_from(['db.t3.micro', 'db.t3.small'])),
            'vpc_ref': '${resource.vpc-main.id}',
            'allocated_storage': draw(st.integers(min_value=20, max_value=1000)),
            # Explicitly no encryption fields
        },
        tags={},
        depends_on=[]
    )


@composite
def s3_without_encryption_strategy(draw):
    """Generate S3 resource without encryption enabled."""
    logical_id = draw(st.text(
        min_size=3,
        max_size=30,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'
    ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
    
    return ResourceConfig(
        logical_id=logical_id,
        resource_type='s3',
        properties={
            'logical_id': logical_id,
            'versioning_enabled': draw(st.booleans()),
            # Explicitly no encryption field
        },
        tags={},
        depends_on=[]
    )


@composite
def production_rds_without_multi_az_strategy(draw):
    """Generate production RDS resource without Multi-AZ."""
    logical_id = draw(st.text(
        min_size=3,
        max_size=30,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'
    ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
    
    return ResourceConfig(
        logical_id=logical_id,
        resource_type='rds',
        properties={
            'logical_id': logical_id,
            'engine': draw(st.sampled_from(['postgres', 'mysql'])),
            'instance_class': draw(st.sampled_from(['db.t3.small', 'db.t3.medium'])),
            'allocated_storage': draw(st.integers(min_value=100, max_value=1000)),
            'vpc_ref': '${resource.vpc-main.id}',
            # Explicitly no multi_az or set to False
            'multi_az': False,
        },
        tags={},
        depends_on=[]
    )


class TestDeploymentRuleModification:
    """
    Property 56: Deployment Rule Modification
    
    **Validates: Requirements 14.2**
    
    For any deployment rule that modifies configuration, the modifications 
    SHALL be applied to the configuration before code generation.
    """
    
    @given(
        metadata=config_metadata_strategy(),
        environment=environment_config_strategy(),
        rds_resource=rds_without_encryption_strategy()
    )
    @settings(max_examples=100)
    def test_property_56_encryption_rule_modifies_rds(self, metadata, environment, rds_resource):
        """
        Test that EncryptionEnforcementRule modifies RDS resources without encryption.
        
        **Validates: Requirements 14.2**
        """
        # Create configuration with RDS resource lacking encryption
        config = Configuration(
            version='1.0',
            metadata=metadata,
            environments={environment.name: environment},
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        # Apply encryption rule
        rule = EncryptionEnforcementRule()
        result = rule.apply(config, environment.name)
        
        # Verify modifications were made
        assert result.success, "Rule should succeed"
        assert len(result.modifications) > 0, "Rule should create modifications"
        
        # Verify the resource properties were actually modified
        assert rds_resource.properties.get('encryption_enabled') is True, \
            "encryption_enabled should be set to True"
        assert rds_resource.properties.get('storage_encrypted') is True, \
            "storage_encrypted should be set to True"
        
        # Verify modification records contain correct information
        mod_fields = [mod.field_path for mod in result.modifications]
        assert 'properties.encryption_enabled' in mod_fields
        assert 'properties.storage_encrypted' in mod_fields
        
        # Verify each modification has required fields
        for mod in result.modifications:
            assert mod.rule_name == 'EncryptionEnforcementRule'
            assert mod.resource_id == rds_resource.logical_id
            assert mod.field_path is not None
            assert mod.old_value is not None or mod.old_value is False
            assert mod.new_value is True
            assert mod.reason is not None and len(mod.reason) > 0
    
    @given(
        metadata=config_metadata_strategy(),
        environment=environment_config_strategy(),
        s3_resource=s3_without_encryption_strategy()
    )
    @settings(max_examples=100)
    def test_property_56_encryption_rule_modifies_s3(self, metadata, environment, s3_resource):
        """
        Test that EncryptionEnforcementRule modifies S3 resources without encryption.
        
        **Validates: Requirements 14.2**
        """
        # Create configuration with S3 resource lacking encryption
        config = Configuration(
            version='1.0',
            metadata=metadata,
            environments={environment.name: environment},
            resources=[s3_resource],
            deployment_rules=[]
        )
        
        # Apply encryption rule
        rule = EncryptionEnforcementRule()
        result = rule.apply(config, environment.name)
        
        # Verify modifications were made
        assert result.success, "Rule should succeed"
        assert len(result.modifications) > 0, "Rule should create modifications"
        
        # Verify the resource properties were actually modified
        assert s3_resource.properties.get('encryption') == 'aws:kms', \
            "encryption should be set to aws:kms"
        
        # Verify modification record
        assert len(result.modifications) == 1
        mod = result.modifications[0]
        assert mod.rule_name == 'EncryptionEnforcementRule'
        assert mod.resource_id == s3_resource.logical_id
        assert mod.field_path == 'properties.encryption'
        assert mod.new_value == 'aws:kms'
        assert 'encryption' in mod.reason.lower()
    
    @given(
        metadata=config_metadata_strategy(),
        rds_resource=production_rds_without_multi_az_strategy()
    )
    @settings(max_examples=100)
    def test_property_56_production_rule_modifies_multi_az(self, metadata, rds_resource):
        """
        Test that ProductionProtectionRule modifies RDS to enable Multi-AZ in production.
        
        **Validates: Requirements 14.2**
        """
        # Create production environment
        prod_env = EnvironmentConfig(
            name='production',
            account_id='123456789012',
            region='us-east-1',
            tags={},
            overrides={}
        )
        
        config = Configuration(
            version='1.0',
            metadata=metadata,
            environments={'production': prod_env},
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        # Apply production protection rule
        rule = ProductionProtectionRule()
        result = rule.apply(config, 'production')
        
        # Verify the resource was modified to enable Multi-AZ
        assert rds_resource.properties.get('multi_az') is True, \
            "multi_az should be set to True in production"
        
        # Verify modification was recorded
        multi_az_mods = [m for m in result.modifications if 'multi_az' in m.field_path]
        assert len(multi_az_mods) > 0, "Should have modification for multi_az"
        
        mod = multi_az_mods[0]
        assert mod.rule_name == 'ProductionProtectionRule'
        assert mod.resource_id == rds_resource.logical_id
        assert mod.new_value is True
        assert 'production' in mod.reason.lower() or 'multi-az' in mod.reason.lower()



@composite
def invalid_logical_id_strategy(draw):
    """Generate resource with invalid logical ID."""
    # Generate invalid logical IDs (uppercase, special chars, etc.)
    invalid_id = draw(st.sampled_from([
        'VPC-Main',  # uppercase
        'vpc_main',  # underscore
        'vpc main',  # space
        '-vpc-main',  # starts with hyphen
        'vpc-main-',  # ends with hyphen
        'vpc--main',  # consecutive hyphens
        'a' * 65,  # too long
    ]))
    
    return ResourceConfig(
        logical_id=invalid_id,
        resource_type='vpc',
        properties={
            'logical_id': invalid_id,
            'cidr': '10.0.0.0/16',
            'availability_zones': 3,
        },
        tags={},
        depends_on=[]
    )


@composite
def incomplete_metadata_strategy(draw):
    """Generate metadata missing required fields."""
    # Randomly omit one or more required fields
    omit_field = draw(st.sampled_from(['project', 'owner', 'cost_center']))
    
    return ConfigMetadata(
        project='' if omit_field == 'project' else draw(st.text(min_size=1, max_size=50)),
        owner='' if omit_field == 'owner' else draw(st.text(min_size=1, max_size=50)),
        cost_center='' if omit_field == 'cost_center' else draw(st.text(min_size=1, max_size=50)),
        description=draw(st.text(max_size=200))
    )


@composite
def production_rds_missing_protected_props_strategy(draw):
    """Generate production RDS resource missing protected properties."""
    logical_id = draw(st.text(
        min_size=3,
        max_size=30,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'
    ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
    
    # Randomly omit one or more protected properties
    properties = {'logical_id': logical_id, 'vpc_ref': '${resource.vpc-main.id}'}
    
    # Omit at least one protected property
    omit_props = draw(st.lists(
        st.sampled_from(['engine', 'instance_class', 'allocated_storage']),
        min_size=1,
        max_size=3,
        unique=True
    ))
    
    if 'engine' not in omit_props:
        properties['engine'] = draw(st.sampled_from(['postgres', 'mysql']))
    if 'instance_class' not in omit_props:
        properties['instance_class'] = draw(st.sampled_from(['db.t3.small', 'db.t3.medium']))
    if 'allocated_storage' not in omit_props:
        properties['allocated_storage'] = draw(st.integers(min_value=100, max_value=1000))
    
    return ResourceConfig(
        logical_id=logical_id,
        resource_type='rds',
        properties=properties,
        tags={},
        depends_on=[]
    )


class TestDeploymentRuleRejection:
    """
    Property 57: Deployment Rule Rejection
    
    **Validates: Requirements 14.3**
    
    For any deployment rule that detects a policy violation, the rule 
    SHALL reject the configuration and prevent code generation.
    """
    
    @given(
        metadata=config_metadata_strategy(),
        environment=environment_config_strategy(),
        invalid_resource=invalid_logical_id_strategy()
    )
    @settings(max_examples=100)
    def test_property_57_naming_rule_rejects_invalid_names(self, metadata, environment, invalid_resource):
        """
        Test that NamingConventionRule rejects resources with invalid logical IDs.
        
        **Validates: Requirements 14.3**
        """
        config = Configuration(
            version='1.0',
            metadata=metadata,
            environments={environment.name: environment},
            resources=[invalid_resource],
            deployment_rules=[]
        )
        
        # Apply naming convention rule
        rule = NamingConventionRule()
        result = rule.apply(config, environment.name)
        
        # Verify the rule created rejections (either ERROR or WARNING)
        assert len(result.rejections) > 0, "Rule should create rejections for invalid naming"
        
        # Verify rejection contains relevant information
        for rejection in result.rejections:
            assert rejection.rule_name == 'NamingConventionRule'
            assert rejection.resource_id == invalid_resource.logical_id
            assert rejection.reason is not None and len(rejection.reason) > 0
            assert rejection.severity in ['ERROR', 'WARNING']
        
        # If there are ERROR rejections, success should be False
        error_rejections = [r for r in result.rejections if r.severity == 'ERROR']
        if len(error_rejections) > 0:
            assert result.success is False, "Rule should fail when there are ERROR rejections"
    
    @given(
        incomplete_metadata=incomplete_metadata_strategy(),
        environment=environment_config_strategy()
    )
    @settings(max_examples=100)
    def test_property_57_tag_compliance_rejects_incomplete_metadata(self, incomplete_metadata, environment):
        """
        Test that TagComplianceRule rejects configurations with incomplete metadata.
        
        **Validates: Requirements 14.3**
        """
        config = Configuration(
            version='1.0',
            metadata=incomplete_metadata,
            environments={environment.name: environment},
            resources=[],
            deployment_rules=[]
        )
        
        # Apply tag compliance rule
        rule = TagComplianceRule()
        result = rule.apply(config, environment.name)
        
        # Verify the rule rejected the configuration
        assert result.success is False, "Rule should reject incomplete metadata"
        assert len(result.rejections) > 0, "Rule should create rejections"
        
        # Verify rejection mentions the missing field
        rejection_reasons = [r.reason.lower() for r in result.rejections]
        assert any('project' in reason or 'owner' in reason or 'cost_center' in reason 
                   for reason in rejection_reasons), \
            "Rejection should mention missing required field"
        
        # Verify all rejections have ERROR severity
        for rejection in result.rejections:
            assert rejection.rule_name == 'TagComplianceRule'
            assert rejection.severity == 'ERROR'
    
    @given(
        metadata=config_metadata_strategy(),
        rds_resource=production_rds_missing_protected_props_strategy()
    )
    @settings(max_examples=100)
    def test_property_57_production_rule_rejects_missing_protected_props(self, metadata, rds_resource):
        """
        Test that ProductionProtectionRule rejects resources missing protected properties.
        
        **Validates: Requirements 14.3**
        """
        # Create production environment
        prod_env = EnvironmentConfig(
            name='production',
            account_id='123456789012',
            region='us-east-1',
            tags={},
            overrides={}
        )
        
        config = Configuration(
            version='1.0',
            metadata=metadata,
            environments={'production': prod_env},
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        # Apply production protection rule
        rule = ProductionProtectionRule()
        result = rule.apply(config, 'production')
        
        # Verify the rule rejected the configuration
        assert result.success is False, "Rule should reject missing protected properties"
        assert len(result.rejections) > 0, "Rule should create rejections"
        
        # Verify rejections mention protected properties
        rejection_reasons = [r.reason.lower() for r in result.rejections]
        protected_props = ['engine', 'instance_class', 'allocated_storage']
        assert any(prop in reason for reason in rejection_reasons for prop in protected_props), \
            "Rejection should mention missing protected property"
        
        # Verify all rejections are for the correct resource
        for rejection in result.rejections:
            assert rejection.rule_name == 'ProductionProtectionRule'
            assert rejection.resource_id == rds_resource.logical_id
            assert rejection.severity == 'ERROR'



class TestRuleExecutionOrder:
    """
    Property 58: Rule Execution Order
    
    **Validates: Requirements 14.4**
    
    For any set of deployment rules with different priorities, the system 
    SHALL execute rules in order from highest to lowest priority.
    """
    
    @given(
        metadata=config_metadata_strategy(),
        environment=environment_config_strategy(),
        priorities=st.lists(
            st.integers(min_value=1, max_value=1000),
            min_size=2,
            max_size=4,  # Match the number of available rules
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_58_rules_execute_in_priority_order(self, metadata, environment, priorities):
        """
        Test that rules are executed in priority order (highest to lowest).
        
        **Validates: Requirements 14.4**
        """
        engine = DeploymentRulesEngine()
        
        # Register rules with different priorities
        rules = [
            EncryptionEnforcementRule(),
            ProductionProtectionRule(),
            TagComplianceRule(),
            NamingConventionRule(),
        ]
        
        # Assign priorities to rules (only use as many rules as we have priorities)
        num_rules = len(priorities)
        for i in range(num_rules):
            engine.register_rule(rules[i], priority=priorities[i])
        
        # Get registered rules
        registered = engine.get_registered_rules()
        
        # Verify rules are ordered by priority (descending)
        registered_priorities = [priority for priority, _ in registered]
        assert registered_priorities == sorted(priorities, reverse=True), \
            f"Rules should be ordered by priority (highest first): expected {sorted(priorities, reverse=True)}, got {registered_priorities}"
    
    @given(
        metadata=config_metadata_strategy(),
        environment=environment_config_strategy(),
        rds_resource=rds_without_encryption_strategy()
    )
    @settings(max_examples=100)
    def test_property_58_higher_priority_rules_execute_first(self, metadata, environment, rds_resource):
        """
        Test that higher priority rules execute before lower priority rules.
        
        **Validates: Requirements 14.4**
        """
        engine = DeploymentRulesEngine()
        
        # Register rules with explicit priorities
        # EncryptionEnforcementRule should run first (priority 200)
        # NamingConventionRule should run second (priority 100)
        engine.register_rule(NamingConventionRule(), priority=100)
        engine.register_rule(EncryptionEnforcementRule(), priority=200)
        
        config = Configuration(
            version='1.0',
            metadata=metadata,
            environments={environment.name: environment},
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        # Apply all rules
        result = engine.apply_rules(config, environment.name)
        
        # Verify both rules executed
        assert result.success is True
        
        # Verify modifications from EncryptionEnforcementRule are present
        encryption_mods = [m for m in result.modifications if m.rule_name == 'EncryptionEnforcementRule']
        assert len(encryption_mods) > 0, "EncryptionEnforcementRule should have created modifications"
        
        # Verify the order in registered rules
        registered = engine.get_registered_rules()
        assert registered[0][0] == 200, "First rule should have priority 200"
        assert registered[0][1] == 'EncryptionEnforcementRule'
        assert registered[1][0] == 100, "Second rule should have priority 100"
        assert registered[1][1] == 'NamingConventionRule'
    
    @given(
        priorities=st.lists(
            st.integers(min_value=1, max_value=1000),
            min_size=3,
            max_size=10,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_58_priority_ordering_maintained_after_multiple_registrations(self, priorities):
        """
        Test that priority ordering is maintained even when rules are registered in random order.
        
        **Validates: Requirements 14.4**
        """
        engine = DeploymentRulesEngine()
        
        # Create rules with random priorities
        rules_with_priorities = list(zip(
            [EncryptionEnforcementRule(), ProductionProtectionRule(), TagComplianceRule()],
            priorities[:3]
        ))
        
        # Register in random order (already randomized by hypothesis)
        for rule, priority in rules_with_priorities:
            engine.register_rule(rule, priority=priority)
        
        # Get registered rules
        registered = engine.get_registered_rules()
        
        # Verify they are sorted by priority (descending)
        registered_priorities = [p for p, _ in registered]
        expected_priorities = sorted(priorities[:3], reverse=True)
        
        assert registered_priorities == expected_priorities, \
            f"Rules should be sorted by priority: expected {expected_priorities}, got {registered_priorities}"



class TestRuleModificationAudit:
    """
    Property 59: Rule Modification Audit
    
    **Validates: Requirements 14.5**
    
    For any deployment rule that modifies a configuration, the system 
    SHALL log the modification including rule name, field modified, 
    old value, new value, and reason.
    """
    
    @given(
        metadata=config_metadata_strategy(),
        environment=environment_config_strategy(),
        rds_resource=rds_without_encryption_strategy()
    )
    @settings(max_examples=100)
    def test_property_59_modifications_contain_audit_information(self, metadata, environment, rds_resource):
        """
        Test that all modifications contain complete audit information.
        
        **Validates: Requirements 14.5**
        """
        config = Configuration(
            version='1.0',
            metadata=metadata,
            environments={environment.name: environment},
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        # Apply encryption rule
        rule = EncryptionEnforcementRule()
        result = rule.apply(config, environment.name)
        
        # Verify modifications exist
        assert len(result.modifications) > 0, "Rule should create modifications"
        
        # Verify each modification has complete audit information
        for mod in result.modifications:
            # Rule name
            assert mod.rule_name is not None and len(mod.rule_name) > 0, \
                "Modification must include rule name"
            assert mod.rule_name == 'EncryptionEnforcementRule', \
                "Rule name should match the rule that created it"
            
            # Resource ID
            assert mod.resource_id is not None and len(mod.resource_id) > 0, \
                "Modification must include resource ID"
            assert mod.resource_id == rds_resource.logical_id, \
                "Resource ID should match the modified resource"
            
            # Field path
            assert mod.field_path is not None and len(mod.field_path) > 0, \
                "Modification must include field path"
            assert 'properties.' in mod.field_path, \
                "Field path should indicate the modified property"
            
            # Old value (can be None or False for missing fields)
            assert mod.old_value is not None or mod.old_value is False or mod.old_value == '', \
                "Modification must include old value (even if None/False)"
            
            # New value
            assert mod.new_value is not None, \
                "Modification must include new value"
            
            # Reason
            assert mod.reason is not None and len(mod.reason) > 0, \
                "Modification must include reason"
            assert len(mod.reason) > 10, \
                "Reason should be descriptive (more than 10 characters)"
    
    @given(
        metadata=config_metadata_strategy(),
        environment=environment_config_strategy(),
        s3_resource=s3_without_encryption_strategy()
    )
    @settings(max_examples=100)
    def test_property_59_audit_log_captures_field_changes(self, metadata, environment, s3_resource):
        """
        Test that audit information correctly captures field changes.
        
        **Validates: Requirements 14.5**
        """
        config = Configuration(
            version='1.0',
            metadata=metadata,
            environments={environment.name: environment},
            resources=[s3_resource],
            deployment_rules=[]
        )
        
        # Record original state
        original_encryption = s3_resource.properties.get('encryption')
        
        # Apply encryption rule
        rule = EncryptionEnforcementRule()
        result = rule.apply(config, environment.name)
        
        # Verify modification was recorded
        assert len(result.modifications) == 1
        mod = result.modifications[0]
        
        # Verify old value matches original state
        assert mod.old_value == original_encryption, \
            f"Old value should match original state: expected {original_encryption}, got {mod.old_value}"
        
        # Verify new value matches current state
        assert mod.new_value == s3_resource.properties['encryption'], \
            "New value should match current state"
        assert mod.new_value == 'aws:kms', \
            "New value should be aws:kms"
        
        # Verify field path is correct
        assert mod.field_path == 'properties.encryption', \
            "Field path should indicate the encryption property"
    
    @given(
        metadata=config_metadata_strategy(),
        rds_resource=production_rds_without_multi_az_strategy()
    )
    @settings(max_examples=100)
    def test_property_59_multiple_modifications_all_logged(self, metadata, rds_resource):
        """
        Test that when multiple rules modify a configuration, all modifications are logged.
        
        **Validates: Requirements 14.5**
        """
        # Create production environment
        prod_env = EnvironmentConfig(
            name='production',
            account_id='123456789012',
            region='us-east-1',
            tags={},
            overrides={}
        )
        
        config = Configuration(
            version='1.0',
            metadata=metadata,
            environments={'production': prod_env},
            resources=[rds_resource],
            deployment_rules=[]
        )
        
        # Apply multiple rules through the engine
        engine = DeploymentRulesEngine()
        engine.register_rule(EncryptionEnforcementRule(), priority=200)
        engine.register_rule(ProductionProtectionRule(), priority=100)
        
        result = engine.apply_rules(config, 'production')
        
        # Verify multiple modifications were recorded
        assert len(result.modifications) > 0, "Should have modifications from multiple rules"
        
        # Verify we have modifications from both rules
        rule_names = set(mod.rule_name for mod in result.modifications)
        assert 'EncryptionEnforcementRule' in rule_names, \
            "Should have modifications from EncryptionEnforcementRule"
        assert 'ProductionProtectionRule' in rule_names, \
            "Should have modifications from ProductionProtectionRule"
        
        # Verify each modification has complete audit information
        for mod in result.modifications:
            assert mod.rule_name is not None
            assert mod.resource_id == rds_resource.logical_id
            assert mod.field_path is not None
            assert mod.reason is not None and len(mod.reason) > 0
