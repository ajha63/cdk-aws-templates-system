"""Deployment Rules Engine for applying policies and business rules."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone
from cdk_templates.models import (
    Configuration,
    ResourceConfig,
    RuleModification,
    RuleRejection,
    RuleApplicationResult
)

# Configure audit logger
audit_logger = logging.getLogger('cdk_templates.deployment_rules.audit')
audit_logger.setLevel(logging.INFO)


class DeploymentRule(ABC):
    """Abstract base class for deployment rules."""
    
    def __init__(self, name: str):
        """
        Initialize the deployment rule.
        
        Args:
            name: Name of the rule for identification and logging
        """
        self.name = name
    
    @abstractmethod
    def apply(self, config: Configuration, environment: str) -> RuleApplicationResult:
        """
        Apply the rule to a configuration.
        
        Args:
            config: The configuration to validate/modify
            environment: The target environment (dev, staging, prod)
            
        Returns:
            RuleApplicationResult with modifications or rejections
        """
        pass


class DeploymentRulesEngine:
    """Engine for managing and applying deployment rules."""
    
    def __init__(self):
        """Initialize the deployment rules engine."""
        self._rules: List[tuple[int, DeploymentRule]] = []  # (priority, rule)
    
    def register_rule(self, rule: DeploymentRule, priority: int = 100):
        """
        Register a deployment rule with a specific priority.
        
        Higher priority rules are executed first.
        
        Args:
            rule: The deployment rule to register
            priority: Priority level (higher = executed first, default 100)
        """
        self._rules.append((priority, rule))
        # Sort by priority (descending)
        self._rules.sort(key=lambda x: x[0], reverse=True)
    
    def apply_rules(self, config: Configuration, environment: str) -> RuleApplicationResult:
        """
        Apply all registered rules in priority order.
        
        Args:
            config: The configuration to validate/modify
            environment: The target environment
            
        Returns:
            Combined RuleApplicationResult from all rules
        """
        combined_result = RuleApplicationResult(success=True)
        
        for priority, rule in self._rules:
            result = rule.apply(config, environment)
            
            # Log all modifications for audit trail
            for modification in result.modifications:
                self._log_modification(modification, environment)
            
            # Combine modifications
            combined_result.modifications.extend(result.modifications)
            
            # Combine rejections
            combined_result.rejections.extend(result.rejections)
            
            # Combine errors
            combined_result.errors.extend(result.errors)
            
            # If any rule fails, mark overall as failure
            if not result.success:
                combined_result.success = False
        
        return combined_result
    
    def _log_modification(self, modification: RuleModification, environment: str):
        """
        Log a rule modification to the audit log.
        
        Args:
            modification: The modification to log
            environment: The target environment
        """
        audit_logger.info(
            "Rule modification applied",
            extra={
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'rule_name': modification.rule_name,
                'resource_id': modification.resource_id,
                'field_path': modification.field_path,
                'old_value': str(modification.old_value),
                'new_value': str(modification.new_value),
                'reason': modification.reason,
                'environment': environment
            }
        )
    
    def get_registered_rules(self) -> List[tuple[int, str]]:
        """
        Get list of registered rules with their priorities.
        
        Returns:
            List of (priority, rule_name) tuples
        """
        return [(priority, rule.name) for priority, rule in self._rules]


class EncryptionEnforcementRule(DeploymentRule):
    """Rule to enforce encryption on RDS and S3 resources."""
    
    def __init__(self):
        super().__init__("EncryptionEnforcementRule")
    
    def apply(self, config: Configuration, environment: str) -> RuleApplicationResult:
        """
        Enforce encryption on RDS and S3 resources.
        
        For RDS: Ensures encryption_enabled and storage_encrypted are true
        For S3: Ensures encryption is configured
        """
        result = RuleApplicationResult(success=True)
        
        for resource in config.resources:
            if resource.resource_type == "rds":
                self._enforce_rds_encryption(resource, result)
            elif resource.resource_type == "s3":
                self._enforce_s3_encryption(resource, result)
        
        return result
    
    def _enforce_rds_encryption(self, resource: ResourceConfig, result: RuleApplicationResult):
        """Enforce encryption on RDS resources."""
        modified = False
        
        # Check encryption_enabled
        if not resource.properties.get("encryption_enabled", False):
            old_value = resource.properties.get("encryption_enabled", False)
            resource.properties["encryption_enabled"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.encryption_enabled",
                old_value=old_value,
                new_value=True,
                reason="Encryption at rest is mandatory for all RDS instances"
            ))
            modified = True
        
        # Check storage_encrypted
        if not resource.properties.get("storage_encrypted", False):
            old_value = resource.properties.get("storage_encrypted", False)
            resource.properties["storage_encrypted"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.storage_encrypted",
                old_value=old_value,
                new_value=True,
                reason="Storage encryption is mandatory for all RDS instances"
            ))
            modified = True
    
    def _enforce_s3_encryption(self, resource: ResourceConfig, result: RuleApplicationResult):
        """Enforce encryption on S3 resources."""
        if "encryption" not in resource.properties or not resource.properties["encryption"]:
            old_value = resource.properties.get("encryption")
            resource.properties["encryption"] = "aws:kms"
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.encryption",
                old_value=old_value,
                new_value="aws:kms",
                reason="Encryption is mandatory for all S3 buckets"
            ))


class ProductionProtectionRule(DeploymentRule):
    """Rule to prevent destructive changes in production environment."""
    
    PROTECTED_PROPERTIES = {
        "rds": ["allocated_storage", "instance_class", "engine"],
        "s3": ["versioning_enabled"],
        "vpc": ["cidr"],
        "ec2": ["instance_type"]
    }
    
    # Properties that would cause resource replacement if changed
    REPLACEMENT_PROPERTIES = {
        "rds": ["engine", "allocated_storage"],
        "s3": ["bucket_name"],
        "vpc": ["cidr"],
        "ec2": ["ami_id", "instance_type", "availability_zone"]
    }
    
    def __init__(self):
        super().__init__("ProductionProtectionRule")
    
    def apply(self, config: Configuration, environment: str) -> RuleApplicationResult:
        """
        Prevent destructive changes to production resources.
        
        This rule:
        1. Validates that critical properties are explicitly set
        2. Prevents changes to properties that would cause resource replacement
        3. Enforces Multi-AZ for RDS in production
        4. Validates that critical resources are marked appropriately
        """
        result = RuleApplicationResult(success=True)
        
        # Only apply to production environment
        if environment.lower() != "production" and environment.lower() != "prod":
            return result
        
        for resource in config.resources:
            # Check if resource is marked as critical
            is_critical = resource.tags.get("Critical", "false").lower() == "true"
            
            # Check if resource has critical properties that shouldn't be changed
            if resource.resource_type in self.PROTECTED_PROPERTIES:
                protected_props = self.PROTECTED_PROPERTIES[resource.resource_type]
                
                # Validate that protected properties are explicitly set
                for prop in protected_props:
                    if prop not in resource.properties:
                        result.rejections.append(RuleRejection(
                            rule_name=self.name,
                            resource_id=resource.logical_id,
                            reason=f"Protected property '{prop}' must be explicitly set in production",
                            severity="ERROR"
                        ))
                        result.success = False
            
            # For critical resources, validate replacement properties
            if is_critical and resource.resource_type in self.REPLACEMENT_PROPERTIES:
                replacement_props = self.REPLACEMENT_PROPERTIES[resource.resource_type]
                
                # Check if any replacement properties are being changed
                # In a real implementation, this would compare against deployed state
                # For now, we just ensure they are explicitly set
                for prop in replacement_props:
                    if prop not in resource.properties:
                        result.rejections.append(RuleRejection(
                            rule_name=self.name,
                            resource_id=resource.logical_id,
                            reason=(
                                f"Critical resource property '{prop}' must be explicitly set "
                                f"to prevent accidental replacement in production"
                            ),
                            severity="ERROR"
                        ))
                        result.success = False
            
            # Enforce Multi-AZ for RDS in production
            if resource.resource_type == "rds":
                if not resource.properties.get("multi_az", False):
                    old_value = resource.properties.get("multi_az", False)
                    resource.properties["multi_az"] = True
                    result.modifications.append(RuleModification(
                        rule_name=self.name,
                        resource_id=resource.logical_id,
                        field_path="properties.multi_az",
                        old_value=old_value,
                        new_value=True,
                        reason="Multi-AZ is mandatory for production RDS instances"
                    ))
            
            # Warn if database resources are not marked as critical
            if resource.resource_type == "rds" and not is_critical:
                result.modifications.append(RuleModification(
                    rule_name=self.name,
                    resource_id=resource.logical_id,
                    field_path="tags.Critical",
                    old_value=resource.tags.get("Critical", "false"),
                    new_value="true",
                    reason="RDS instances in production should be marked as critical"
                ))
                resource.tags["Critical"] = "true"
        
        return result


class TagComplianceRule(DeploymentRule):
    """Rule to validate mandatory tags are present."""
    
    MANDATORY_TAGS = ['Environment', 'Project', 'Owner', 'CostCenter', 'ManagedBy']
    
    def __init__(self):
        super().__init__("TagComplianceRule")
    
    def apply(self, config: Configuration, environment: str) -> RuleApplicationResult:
        """
        Validate that all resources have mandatory tags defined at the metadata level.
        
        Note: The actual tag application is done by TaggingStrategyService,
        this rule validates that the metadata contains the required information.
        """
        result = RuleApplicationResult(success=True)
        
        # Check that metadata has required fields for mandatory tags
        metadata = config.metadata
        
        if not metadata.project:
            result.rejections.append(RuleRejection(
                rule_name=self.name,
                resource_id="configuration",
                reason="Metadata must include 'project' for mandatory Project tag",
                severity="ERROR"
            ))
            result.success = False
        
        if not metadata.owner:
            result.rejections.append(RuleRejection(
                rule_name=self.name,
                resource_id="configuration",
                reason="Metadata must include 'owner' for mandatory Owner tag",
                severity="ERROR"
            ))
            result.success = False
        
        if not metadata.cost_center:
            result.rejections.append(RuleRejection(
                rule_name=self.name,
                resource_id="configuration",
                reason="Metadata must include 'cost_center' for mandatory CostCenter tag",
                severity="ERROR"
            ))
            result.success = False
        
        # Check that environment is defined
        if environment not in config.environments:
            result.rejections.append(RuleRejection(
                rule_name=self.name,
                resource_id="configuration",
                reason=f"Environment '{environment}' is not defined in configuration",
                severity="ERROR"
            ))
            result.success = False
        
        return result


class NamingConventionRule(DeploymentRule):
    """Rule to validate resource names follow naming conventions."""
    
    def __init__(self):
        super().__init__("NamingConventionRule")
    
    def apply(self, config: Configuration, environment: str) -> RuleApplicationResult:
        """
        Validate that resource logical IDs follow naming conventions.
        
        Expected pattern: lowercase alphanumeric with hyphens
        """
        result = RuleApplicationResult(success=True)
        
        import re
        valid_pattern = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
        
        for resource in config.resources:
            logical_id = resource.logical_id
            
            # Check pattern
            if not valid_pattern.match(logical_id):
                result.rejections.append(RuleRejection(
                    rule_name=self.name,
                    resource_id=logical_id,
                    reason=f"Logical ID '{logical_id}' does not follow naming convention (lowercase alphanumeric with hyphens)",
                    severity="ERROR"
                ))
                result.success = False
            
            # Check length (reasonable limit)
            if len(logical_id) > 64:
                result.rejections.append(RuleRejection(
                    rule_name=self.name,
                    resource_id=logical_id,
                    reason=f"Logical ID '{logical_id}' exceeds maximum length of 64 characters",
                    severity="ERROR"
                ))
                result.success = False
            
            # Check for consecutive hyphens
            if '--' in logical_id:
                result.rejections.append(RuleRejection(
                    rule_name=self.name,
                    resource_id=logical_id,
                    reason=f"Logical ID '{logical_id}' contains consecutive hyphens",
                    severity="WARNING"
                ))
        
        return result


class ProductionSecurityPolicyRule(DeploymentRule):
    """Rule to apply stricter security policies in production environments."""
    
    def __init__(self):
        super().__init__("ProductionSecurityPolicyRule")
    
    def apply(self, config: Configuration, environment: str) -> RuleApplicationResult:
        """
        Apply stricter security policies for production environments.
        
        Production policies:
        - RDS: Mandatory encryption, Multi-AZ, enhanced monitoring
        - S3: Mandatory encryption, versioning enabled
        - EC2: Mandatory encrypted volumes, detailed monitoring
        - VPC: Flow logs enabled
        """
        result = RuleApplicationResult(success=True)
        
        # Only apply to production environment
        if environment.lower() != "production" and environment.lower() != "prod":
            return result
        
        for resource in config.resources:
            if resource.resource_type == "rds":
                self._apply_rds_production_policies(resource, result)
            elif resource.resource_type == "s3":
                self._apply_s3_production_policies(resource, result)
            elif resource.resource_type == "ec2":
                self._apply_ec2_production_policies(resource, result)
            elif resource.resource_type == "vpc":
                self._apply_vpc_production_policies(resource, result)
        
        return result
    
    def _apply_rds_production_policies(
        self,
        resource: ResourceConfig,
        result: RuleApplicationResult
    ):
        """Apply production security policies to RDS resources."""
        # Enforce encryption
        if not resource.properties.get("encryption_enabled", False):
            old_value = resource.properties.get("encryption_enabled", False)
            resource.properties["encryption_enabled"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.encryption_enabled",
                old_value=old_value,
                new_value=True,
                reason="Encryption is mandatory for production RDS instances"
            ))
        
        if not resource.properties.get("storage_encrypted", False):
            old_value = resource.properties.get("storage_encrypted", False)
            resource.properties["storage_encrypted"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.storage_encrypted",
                old_value=old_value,
                new_value=True,
                reason="Storage encryption is mandatory for production RDS instances"
            ))
        
        # Enforce Multi-AZ
        if not resource.properties.get("multi_az", False):
            old_value = resource.properties.get("multi_az", False)
            resource.properties["multi_az"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.multi_az",
                old_value=old_value,
                new_value=True,
                reason="Multi-AZ is mandatory for production RDS instances"
            ))
        
        # Enforce enhanced monitoring
        if not resource.properties.get("enable_enhanced_monitoring", False):
            old_value = resource.properties.get("enable_enhanced_monitoring", False)
            resource.properties["enable_enhanced_monitoring"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.enable_enhanced_monitoring",
                old_value=old_value,
                new_value=True,
                reason="Enhanced monitoring is mandatory for production RDS instances"
            ))
        
        # Enforce minimum backup retention
        backup_retention = resource.properties.get("backup_retention_days", 7)
        if backup_retention < 7:
            resource.properties["backup_retention_days"] = 7
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.backup_retention_days",
                old_value=backup_retention,
                new_value=7,
                reason="Minimum 7 days backup retention required for production RDS"
            ))
    
    def _apply_s3_production_policies(
        self,
        resource: ResourceConfig,
        result: RuleApplicationResult
    ):
        """Apply production security policies to S3 resources."""
        # Enforce encryption
        if not resource.properties.get("encryption", None):
            old_value = resource.properties.get("encryption", None)
            resource.properties["encryption"] = "aws:kms"
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.encryption",
                old_value=old_value,
                new_value="aws:kms",
                reason="KMS encryption is mandatory for production S3 buckets"
            ))
        
        # Enforce versioning
        if not resource.properties.get("versioning_enabled", False):
            old_value = resource.properties.get("versioning_enabled", False)
            resource.properties["versioning_enabled"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.versioning_enabled",
                old_value=old_value,
                new_value=True,
                reason="Versioning is mandatory for production S3 buckets"
            ))
        
        # Enforce public access block
        if not resource.properties.get("block_public_access", False):
            old_value = resource.properties.get("block_public_access", False)
            resource.properties["block_public_access"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.block_public_access",
                old_value=old_value,
                new_value=True,
                reason="Public access blocking is mandatory for production S3 buckets"
            ))
    
    def _apply_ec2_production_policies(
        self,
        resource: ResourceConfig,
        result: RuleApplicationResult
    ):
        """Apply production security policies to EC2 resources."""
        # Enforce encrypted root volume
        root_volume = resource.properties.get("root_volume", {})
        if not root_volume.get("encrypted", False):
            if "root_volume" not in resource.properties:
                resource.properties["root_volume"] = {}
            
            old_value = resource.properties["root_volume"].get("encrypted", False)
            resource.properties["root_volume"]["encrypted"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.root_volume.encrypted",
                old_value=old_value,
                new_value=True,
                reason="Encrypted volumes are mandatory for production EC2 instances"
            ))
        
        # Enforce detailed monitoring
        if not resource.properties.get("enable_detailed_monitoring", False):
            old_value = resource.properties.get("enable_detailed_monitoring", False)
            resource.properties["enable_detailed_monitoring"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.enable_detailed_monitoring",
                old_value=old_value,
                new_value=True,
                reason="Detailed monitoring is mandatory for production EC2 instances"
            ))
    
    def _apply_vpc_production_policies(
        self,
        resource: ResourceConfig,
        result: RuleApplicationResult
    ):
        """Apply production security policies to VPC resources."""
        # Enforce VPC Flow Logs
        if not resource.properties.get("enable_flow_logs", False):
            old_value = resource.properties.get("enable_flow_logs", False)
            resource.properties["enable_flow_logs"] = True
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.enable_flow_logs",
                old_value=old_value,
                new_value=True,
                reason="VPC Flow Logs are mandatory for production VPCs"
            ))
        
        # Enforce minimum availability zones for high availability
        availability_zones = resource.properties.get("availability_zones", 2)
        if availability_zones < 3:
            resource.properties["availability_zones"] = 3
            result.modifications.append(RuleModification(
                rule_name=self.name,
                resource_id=resource.logical_id,
                field_path="properties.availability_zones",
                old_value=availability_zones,
                new_value=3,
                reason="Minimum 3 availability zones required for production VPCs"
            ))
