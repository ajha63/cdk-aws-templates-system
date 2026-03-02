"""Deployment Orchestrator for managing resource deployment with failure isolation.

This module handles the orchestration of resource deployments, tracking dependencies
and isolating failures to prevent cascading issues.
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

from cdk_templates.models import Configuration, ResourceConfig, DependencyGraph
from cdk_templates.resource_link_resolver import ResourceLinkResolver
from cdk_templates.logging_config import get_logger, get_audit_logger
from cdk_templates.exceptions import CDKTemplateSystemError


logger = get_logger('deployment_orchestrator')
audit_logger = get_audit_logger()


class ResourceStatus(Enum):
    """Status of a resource during deployment."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ResourceDeploymentResult:
    """Result of deploying a single resource."""
    resource_id: str
    status: ResourceStatus
    error_message: Optional[str] = None
    skipped_reason: Optional[str] = None


@dataclass
class DeploymentPlan:
    """Plan for deploying resources in dependency order."""
    resources: List[str]  # Resource IDs in deployment order
    dependency_graph: DependencyGraph
    critical_resources: Set[str] = field(default_factory=set)


@dataclass
class DeploymentResult:
    """Result of a complete deployment operation."""
    success: bool
    deployed_resources: List[str] = field(default_factory=list)
    failed_resources: List[str] = field(default_factory=list)
    skipped_resources: List[str] = field(default_factory=list)
    resource_results: Dict[str, ResourceDeploymentResult] = field(default_factory=dict)
    error_message: Optional[str] = None


class DeploymentOrchestrator:
    """
    Orchestrates resource deployment with dependency tracking and failure isolation.
    
    Key features:
    - Deploys resources in dependency order
    - Tracks critical resources
    - Isolates failures to prevent deployment of dependent resources
    - Provides detailed deployment results
    """
    
    def __init__(self, link_resolver: Optional[ResourceLinkResolver] = None):
        """
        Initialize the deployment orchestrator.
        
        Args:
            link_resolver: ResourceLinkResolver instance (creates default if None)
        """
        self.link_resolver = link_resolver or ResourceLinkResolver()
    
    def create_deployment_plan(
        self,
        config: Configuration,
        critical_resources: Optional[Set[str]] = None
    ) -> DeploymentPlan:
        """
        Create a deployment plan with resources in dependency order.
        
        Args:
            config: Configuration containing resources to deploy
            critical_resources: Set of resource IDs that are critical (optional)
            
        Returns:
            DeploymentPlan with ordered resources and dependency graph
            
        Raises:
            CDKTemplateSystemError: If dependency resolution fails
        """
        logger.info(f"Creating deployment plan for {len(config.resources)} resources")
        
        # Build dependency graph
        graph = self.link_resolver.build_dependency_graph(config)
        
        # Check for cycles
        cycles = self.link_resolver.detect_cycles(graph)
        if cycles:
            cycle_str = " -> ".join(cycles[0].resources + [cycles[0].resources[0]])
            raise CDKTemplateSystemError(
                f"Cannot create deployment plan: circular dependency detected: {cycle_str}"
            )
        
        # Get topological order
        deployment_order = self.link_resolver.topological_sort(graph)
        
        # Identify critical resources if not provided
        if critical_resources is None:
            critical_resources = self._identify_critical_resources(config, graph)
        
        logger.info(
            f"Deployment plan created: {len(deployment_order)} resources, "
            f"{len(critical_resources)} critical"
        )
        
        return DeploymentPlan(
            resources=deployment_order,
            dependency_graph=graph,
            critical_resources=critical_resources
        )
    
    def _identify_critical_resources(
        self,
        config: Configuration,
        graph: DependencyGraph
    ) -> Set[str]:
        """
        Identify critical resources based on type and dependencies.
        
        Critical resources are those that:
        - Are foundational (VPC, networking)
        - Have many dependents
        - Are explicitly marked as critical in configuration
        
        Args:
            config: Configuration object
            graph: Dependency graph
            
        Returns:
            Set of critical resource IDs
        """
        critical = set()
        
        # Resource types that are typically critical
        critical_types = {'vpc', 'subnet', 'security_group', 'iam_role'}
        
        # Count dependents for each resource
        dependent_count = {node_id: 0 for node_id in graph.nodes}
        for node_id, node in graph.nodes.items():
            for dep in node.dependencies:
                if dep in dependent_count:
                    dependent_count[dep] += 1
        
        # Mark resources as critical based on criteria
        for resource in config.resources:
            resource_id = resource.logical_id
            
            # Critical by type
            if resource.resource_type in critical_types:
                critical.add(resource_id)
                logger.debug(f"Resource '{resource_id}' marked critical (type: {resource.resource_type})")
            
            # Critical by number of dependents (threshold: 3+)
            elif dependent_count.get(resource_id, 0) >= 3:
                critical.add(resource_id)
                logger.debug(
                    f"Resource '{resource_id}' marked critical "
                    f"({dependent_count[resource_id]} dependents)"
                )
            
            # Explicitly marked as critical in properties
            elif resource.properties.get('critical', False):
                critical.add(resource_id)
                logger.debug(f"Resource '{resource_id}' marked critical (explicit)")
        
        return critical
    
    def get_dependent_resources(
        self,
        resource_id: str,
        graph: DependencyGraph,
        transitive: bool = True
    ) -> Set[str]:
        """
        Get all resources that depend on the given resource.
        
        Args:
            resource_id: ID of the resource
            graph: Dependency graph
            transitive: If True, include transitive dependencies
            
        Returns:
            Set of resource IDs that depend on the given resource
        """
        dependents = set()
        
        # Find direct dependents
        for node_id, node in graph.nodes.items():
            if resource_id in node.dependencies:
                dependents.add(node_id)
        
        # Find transitive dependents if requested
        if transitive:
            to_process = list(dependents)
            while to_process:
                current = to_process.pop(0)
                for node_id, node in graph.nodes.items():
                    if current in node.dependencies and node_id not in dependents:
                        dependents.add(node_id)
                        to_process.append(node_id)
        
        return dependents
    
    def simulate_deployment(
        self,
        plan: DeploymentPlan,
        failed_resources: Optional[Set[str]] = None
    ) -> DeploymentResult:
        """
        Simulate a deployment to determine which resources would be skipped on failure.
        
        This is useful for understanding the impact of a resource failure without
        actually deploying anything.
        
        Args:
            plan: Deployment plan
            failed_resources: Set of resource IDs to simulate as failed
            
        Returns:
            DeploymentResult showing what would happen
        """
        if failed_resources is None:
            failed_resources = set()
        
        logger.info(f"Simulating deployment with {len(failed_resources)} failed resources")
        
        result = DeploymentResult(success=True)
        deployed = set()
        failed = set(failed_resources)
        skipped = set()
        
        for resource_id in plan.resources:
            # Check if any dependencies failed
            node = plan.dependency_graph.nodes.get(resource_id)
            if node:
                failed_deps = set(node.dependencies) & failed
                if failed_deps:
                    skipped.add(resource_id)
                    result.skipped_resources.append(resource_id)
                    result.resource_results[resource_id] = ResourceDeploymentResult(
                        resource_id=resource_id,
                        status=ResourceStatus.SKIPPED,
                        skipped_reason=f"Dependencies failed: {', '.join(failed_deps)}"
                    )
                    
                    # If this is a critical resource, mark as failed
                    if resource_id in plan.critical_resources:
                        logger.warning(
                            f"Critical resource '{resource_id}' would be skipped due to "
                            f"failed dependencies: {', '.join(failed_deps)}"
                        )
                    
                    continue
            
            # Check if this resource is in the failed set
            if resource_id in failed_resources:
                failed.add(resource_id)
                result.failed_resources.append(resource_id)
                result.resource_results[resource_id] = ResourceDeploymentResult(
                    resource_id=resource_id,
                    status=ResourceStatus.FAILED,
                    error_message="Simulated failure"
                )
                
                # If critical, log the impact
                if resource_id in plan.critical_resources:
                    dependents = self.get_dependent_resources(
                        resource_id,
                        plan.dependency_graph,
                        transitive=True
                    )
                    logger.warning(
                        f"Critical resource '{resource_id}' failed, "
                        f"affecting {len(dependents)} dependent resources"
                    )
            else:
                deployed.add(resource_id)
                result.deployed_resources.append(resource_id)
                result.resource_results[resource_id] = ResourceDeploymentResult(
                    resource_id=resource_id,
                    status=ResourceStatus.SUCCESS
                )
        
        result.success = len(failed) == 0
        
        logger.info(
            f"Simulation complete: {len(deployed)} deployed, "
            f"{len(failed)} failed, {len(skipped)} skipped"
        )
        
        return result
    
    def handle_deployment_failure(
        self,
        plan: DeploymentPlan,
        failed_resource_id: str,
        error_message: str,
        deployed_resources: Set[str]
    ) -> DeploymentResult:
        """
        Handle a deployment failure by determining which resources to skip.
        
        Args:
            plan: Deployment plan
            failed_resource_id: ID of the resource that failed
            error_message: Error message from the failure
            deployed_resources: Set of resources already deployed
            
        Returns:
            DeploymentResult with failure information and skipped resources
        """
        logger.error(f"Deployment failure at resource '{failed_resource_id}': {error_message}")
        
        # Log to audit trail
        audit_logger.log_deployment_failure(
            stack_name="unknown",  # Would be provided by caller
            resource_id=failed_resource_id,
            error_message=error_message,
            environment="unknown"  # Would be provided by caller
        )
        
        result = DeploymentResult(
            success=False,
            error_message=f"Deployment failed at resource '{failed_resource_id}': {error_message}"
        )
        
        # Add deployed resources
        result.deployed_resources = list(deployed_resources)
        
        # Add failed resource
        result.failed_resources.append(failed_resource_id)
        result.resource_results[failed_resource_id] = ResourceDeploymentResult(
            resource_id=failed_resource_id,
            status=ResourceStatus.FAILED,
            error_message=error_message
        )
        
        # Determine which resources to skip
        is_critical = failed_resource_id in plan.critical_resources
        
        if is_critical:
            logger.warning(f"Critical resource '{failed_resource_id}' failed")
        
        # Get all dependent resources
        dependents = self.get_dependent_resources(
            failed_resource_id,
            plan.dependency_graph,
            transitive=True
        )
        
        # Skip all dependents that haven't been deployed yet
        for resource_id in plan.resources:
            if resource_id in deployed_resources or resource_id == failed_resource_id:
                continue
            
            if resource_id in dependents:
                result.skipped_resources.append(resource_id)
                result.resource_results[resource_id] = ResourceDeploymentResult(
                    resource_id=resource_id,
                    status=ResourceStatus.SKIPPED,
                    skipped_reason=f"Dependency '{failed_resource_id}' failed"
                )
                
                logger.info(
                    f"Skipping resource '{resource_id}' due to failed dependency "
                    f"'{failed_resource_id}'"
                )
        
        logger.info(
            f"Deployment stopped: {len(deployed_resources)} deployed, "
            f"1 failed, {len(result.skipped_resources)} skipped"
        )
        
        return result
    
    def get_deployment_summary(self, result: DeploymentResult) -> str:
        """
        Generate a human-readable summary of deployment results.
        
        Args:
            result: DeploymentResult to summarize
            
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("DEPLOYMENT SUMMARY")
        lines.append("=" * 60)
        
        if result.success:
            lines.append(f"Status: SUCCESS")
        else:
            lines.append(f"Status: FAILED")
            if result.error_message:
                lines.append(f"Error: {result.error_message}")
        
        lines.append("")
        lines.append(f"Deployed: {len(result.deployed_resources)} resources")
        for resource_id in result.deployed_resources:
            lines.append(f"  ✓ {resource_id}")
        
        if result.failed_resources:
            lines.append("")
            lines.append(f"Failed: {len(result.failed_resources)} resources")
            for resource_id in result.failed_resources:
                res = result.resource_results.get(resource_id)
                error = res.error_message if res else "Unknown error"
                lines.append(f"  ✗ {resource_id}: {error}")
        
        if result.skipped_resources:
            lines.append("")
            lines.append(f"Skipped: {len(result.skipped_resources)} resources")
            for resource_id in result.skipped_resources:
                res = result.resource_results.get(resource_id)
                reason = res.skipped_reason if res else "Unknown reason"
                lines.append(f"  ⊘ {resource_id}: {reason}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
