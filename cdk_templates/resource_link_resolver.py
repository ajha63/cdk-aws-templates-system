"""Resource Link Resolver for managing dependencies between AWS resources."""

import re
from typing import Dict, List, Set, Optional
from cdk_templates.models import (
    Configuration,
    ResourceConfig,
    ResourceLink,
    ResourceNode,
    DependencyGraph,
    Cycle,
    LinkResolutionResult
)
from cdk_templates.exceptions import (
    CircularDependencyError,
    DanglingReferenceError,
    InvalidResourceReferenceError
)


class ResourceLinkResolver:
    """Resolves references between resources and detects circular dependencies."""
    
    # Pattern to match resource references: ${resource.logical_id.property}
    REFERENCE_PATTERN = re.compile(r'\$\{resource\.([a-z0-9-]+)\.([a-z0-9_]+)\}')
    
    # Pattern to match cross-stack references: ${stack.stack_id.output_name}
    CROSS_STACK_PATTERN = re.compile(r'\$\{stack\.([a-z0-9-]+)\.([a-z0-9_]+)\}')
    
    def resolve_links(self, config: Configuration) -> LinkResolutionResult:
        """
        Resuelve todos los enlaces entre recursos.
        
        Args:
            config: Configuration object containing all resources
            
        Returns:
            LinkResolutionResult with success status, resolved links, and any errors
        """
        # Build dependency graph
        graph = self.build_dependency_graph(config)
        
        # Detect cycles
        cycles = self.detect_cycles(graph)
        
        if cycles:
            cycle_descriptions = []
            for cycle in cycles:
                cycle_str = " -> ".join(cycle.resources + [cycle.resources[0]])
                
                # Create detailed error message with visualization
                dependency_chain = self.visualize_dependency_chain(cycle.resources, graph)
                error_msg = f"Circular dependency detected: {cycle_str}\n{dependency_chain}"
                cycle_descriptions.append(error_msg)
            
            return LinkResolutionResult(
                success=False,
                cycles=cycles,
                errors=cycle_descriptions,
                error_message=cycle_descriptions[0] if cycle_descriptions else ""
            )
        
        # Validate all references exist
        validation_errors = self._validate_references(config, graph)
        
        if validation_errors:
            return LinkResolutionResult(
                success=False,
                errors=validation_errors,
                error_message=validation_errors[0] if validation_errors else ""
            )
        
        # Build resolved links mapping
        resolved_links = self._build_resolved_links(config)
        
        return LinkResolutionResult(
            success=True,
            resolved_links=resolved_links
        )
    
    def build_dependency_graph(self, config: Configuration) -> DependencyGraph:
        """
        Construye grafo de dependencias entre recursos.
        
        Args:
            config: Configuration object containing all resources
            
        Returns:
            DependencyGraph with nodes and edges representing dependencies
        """
        graph = DependencyGraph()
        
        # Create nodes for all resources
        for resource in config.resources:
            node = ResourceNode(
                resource_id=resource.logical_id,
                resource_type=resource.resource_type,
                dependencies=[]
            )
            graph.nodes[resource.logical_id] = node
        
        # Find all resource references and create edges
        for resource in config.resources:
            references = self._extract_references(resource)
            
            for ref in references:
                target_id = ref['target_resource']
                property_name = ref['property']
                property_path = ref['property_path']
                
                # Add dependency to node
                if target_id not in graph.nodes[resource.logical_id].dependencies:
                    graph.nodes[resource.logical_id].dependencies.append(target_id)
                
                # Create edge
                link = ResourceLink(
                    source_resource=resource.logical_id,
                    target_resource=target_id,
                    link_type=property_name,
                    property_path=property_path
                )
                graph.edges.append(link)
        
        # Add explicit depends_on relationships
        for resource in config.resources:
            for dep in resource.depends_on:
                if dep not in graph.nodes[resource.logical_id].dependencies:
                    graph.nodes[resource.logical_id].dependencies.append(dep)
                    
                    link = ResourceLink(
                        source_resource=resource.logical_id,
                        target_resource=dep,
                        link_type="explicit_dependency",
                        property_path="depends_on"
                    )
                    graph.edges.append(link)
        
        return graph
    
    def detect_cycles(self, graph: DependencyGraph) -> List[Cycle]:
        """
        Detecta ciclos en el grafo de dependencias usando DFS.
        
        Args:
            graph: DependencyGraph to check for cycles
            
        Returns:
            List of Cycle objects representing circular dependencies
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node_id: str) -> bool:
            """DFS helper to detect cycles."""
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            if node_id in graph.nodes:
                for neighbor in graph.nodes[node_id].dependencies:
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(neighbor)
                        cycle_resources = path[cycle_start:]
                        cycles.append(Cycle(resources=cycle_resources))
                        return True
            
            path.pop()
            rec_stack.remove(node_id)
            return False
        
        # Check all nodes
        for node_id in graph.nodes:
            if node_id not in visited:
                dfs(node_id)
        
        return cycles
    
    def topological_sort(self, graph: DependencyGraph) -> List[str]:
        """
        Retorna orden de despliegue respetando dependencias.
        
        Uses Kahn's algorithm for topological sorting.
        
        Args:
            graph: DependencyGraph to sort
            
        Returns:
            List of resource IDs in deployment order
            
        Raises:
            ValueError: If graph contains cycles
        """
        # Check for cycles first
        cycles = self.detect_cycles(graph)
        if cycles:
            raise ValueError(f"Cannot perform topological sort: graph contains cycles")
        
        # Calculate in-degree for each node
        in_degree = {node_id: 0 for node_id in graph.nodes}
        
        for node_id, node in graph.nodes.items():
            for dep in node.dependencies:
                if dep in in_degree:
                    in_degree[node_id] += 1
        
        # Queue of nodes with no incoming edges
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # Sort queue for deterministic ordering
            queue.sort()
            node_id = queue.pop(0)
            result.append(node_id)
            
            # Reduce in-degree for dependent nodes
            for other_id, other_node in graph.nodes.items():
                if node_id in other_node.dependencies:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)
        
        return result
    
    def visualize_dependency_chain(self, cycle: List[str], graph: DependencyGraph) -> str:
        """
        Create a visual representation of a dependency chain for error messages.
        
        Args:
            cycle: List of resource IDs forming a cycle
            graph: DependencyGraph containing the resources
            
        Returns:
            Formatted string showing the dependency chain with resource types
        """
        lines = []
        for i, resource_id in enumerate(cycle):
            resource_type = graph.nodes[resource_id].resource_type if resource_id in graph.nodes else "unknown"
            arrow = "  └─>" if i == len(cycle) - 1 else "  ├─>"
            lines.append(f"{arrow} {resource_id} ({resource_type})")
        
        # Add the closing of the cycle
        first_resource = cycle[0]
        first_type = graph.nodes[first_resource].resource_type if first_resource in graph.nodes else "unknown"
        lines.append(f"  └─> {first_resource} ({first_type}) [CYCLE CLOSES HERE]")
        
        return "\n".join(lines)
    
    def _extract_references(self, resource: ResourceConfig) -> List[Dict[str, str]]:
        """
        Extract all resource references from a resource configuration.
        
        Args:
            resource: ResourceConfig to extract references from
            
        Returns:
            List of dictionaries with reference information
        """
        references = []
        
        def search_dict(obj: any, path: str = "properties"):
            """Recursively search for references in nested structures."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}"
                    search_dict(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    search_dict(item, current_path)
            elif isinstance(obj, str):
                # Check if string contains a reference
                matches = self.REFERENCE_PATTERN.findall(obj)
                for match in matches:
                    target_resource, property_name = match
                    references.append({
                        'target_resource': target_resource,
                        'property': property_name,
                        'property_path': path
                    })
        
        # Search in properties
        search_dict(resource.properties, "properties")
        
        return references
    
    def _validate_references(self, config: Configuration, graph: DependencyGraph) -> List[str]:
        """
        Validate that all referenced resources exist.
        
        Args:
            config: Configuration object
            graph: DependencyGraph with all dependencies
            
        Returns:
            List of error messages for invalid references
        """
        errors = []
        resource_ids = {r.logical_id for r in config.resources}
        available_resources = sorted(list(resource_ids))
        
        for edge in graph.edges:
            if edge.target_resource not in resource_ids:
                error_msg = (
                    f"Dangling reference: Resource '{edge.source_resource}' references "
                    f"non-existent resource '{edge.target_resource}'\n"
                    f"  Field: {edge.property_path}\n"
                    f"  Available resources: {', '.join(available_resources)}\n"
                    f"  Suggestion: Check that '{edge.target_resource}' is defined in your configuration"
                )
                errors.append(error_msg)
        
        return errors
    
    def _build_resolved_links(self, config: Configuration) -> Dict[str, str]:
        """
        Build a mapping of logical IDs to their resolved references.
        
        Args:
            config: Configuration object
            
        Returns:
            Dictionary mapping logical IDs to resolved reference strings
        """
        resolved = {}
        
        for resource in config.resources:
            resolved[resource.logical_id] = f"resource.{resource.logical_id}"
        
        return resolved
    
    def extract_cross_stack_references(self, resource: ResourceConfig) -> List[Dict[str, str]]:
        """
        Extract all cross-stack references from a resource configuration.
        
        Args:
            resource: ResourceConfig to extract cross-stack references from
            
        Returns:
            List of dictionaries with cross-stack reference information
        """
        references = []
        
        def search_dict(obj: any, path: str = "properties"):
            """Recursively search for cross-stack references in nested structures."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}"
                    search_dict(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    search_dict(item, current_path)
            elif isinstance(obj, str):
                # Check if string contains a cross-stack reference
                matches = self.CROSS_STACK_PATTERN.findall(obj)
                for match in matches:
                    stack_id, output_name = match
                    references.append({
                        'stack_id': stack_id,
                        'output_name': output_name,
                        'property_path': path,
                        'full_reference': obj
                    })
        
        # Search in properties
        search_dict(resource.properties, "properties")
        
        return references
    
    def build_stack_dependency_graph(self, config: Configuration) -> DependencyGraph:
        """
        Build a dependency graph for stacks based on cross-stack references.
        
        Args:
            config: Configuration object with stacks and resources
            
        Returns:
            DependencyGraph with stack dependencies
        """
        graph = DependencyGraph()
        
        # Create nodes for all stacks
        for stack_id in config.stacks.keys():
            node = ResourceNode(
                resource_id=stack_id,
                resource_type='stack',
                dependencies=[]
            )
            graph.nodes[stack_id] = node
        
        # Find cross-stack references and create edges
        for resource in config.resources:
            if not resource.stack:
                continue
            
            source_stack = resource.stack
            
            # Extract cross-stack references from this resource
            cross_stack_refs = self.extract_cross_stack_references(resource)
            
            for ref in cross_stack_refs:
                target_stack = ref['stack_id']
                
                # Add dependency if not already present
                if target_stack in graph.nodes and source_stack in graph.nodes:
                    if target_stack not in graph.nodes[source_stack].dependencies:
                        graph.nodes[source_stack].dependencies.append(target_stack)
                        
                        # Create edge
                        link = ResourceLink(
                            source_resource=source_stack,
                            target_resource=target_stack,
                            link_type='cross_stack_reference',
                            property_path=ref['property_path']
                        )
                        graph.edges.append(link)
        
        return graph
    
    def get_stack_deployment_order(self, config: Configuration) -> List[str]:
        """
        Determine the deployment order for stacks using topological sort.
        
        Args:
            config: Configuration object with stacks
            
        Returns:
            List of stack IDs in deployment order
            
        Raises:
            ValueError: If circular dependencies exist between stacks
        """
        if not config.stacks:
            return []
        
        # Build stack dependency graph
        graph = self.build_stack_dependency_graph(config)
        
        # Check for cycles
        cycles = self.detect_cycles(graph)
        if cycles:
            cycle_descriptions = []
            for cycle in cycles:
                cycle_str = " -> ".join(cycle.resources + [cycle.resources[0]])
                cycle_descriptions.append(cycle_str)
            raise ValueError(
                f"Circular dependencies detected between stacks: {cycle_descriptions[0]}"
            )
        
        # Perform topological sort
        return self.topological_sort(graph)
    
    def validate_cross_stack_outputs(self, config: Configuration) -> List[str]:
        """
        Validate that all cross-stack output references exist in their source stacks.
        
        Args:
            config: Configuration object with stacks and resources
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Build a map of stack_id -> available outputs
        stack_outputs = {}
        for resource in config.resources:
            if resource.stack and resource.outputs:
                stack_id = resource.stack
                if stack_id not in stack_outputs:
                    stack_outputs[stack_id] = set()
                # Add all output names for this resource
                stack_outputs[stack_id].update(resource.outputs.keys())
        
        # Check all cross-stack references
        for resource in config.resources:
            cross_stack_refs = self.extract_cross_stack_references(resource)
            
            for ref in cross_stack_refs:
                target_stack = ref['stack_id']
                output_name = ref['output_name']
                
                # Check if target stack exists
                if target_stack not in config.stacks:
                    errors.append(
                        f"Resource '{resource.logical_id}' references non-existent "
                        f"stack '{target_stack}' in {ref['property_path']}"
                    )
                    continue
                
                # Check if output exists in target stack
                if target_stack not in stack_outputs:
                    errors.append(
                        f"Resource '{resource.logical_id}' references output '{output_name}' "
                        f"from stack '{target_stack}', but stack has no outputs defined"
                    )
                    continue
                
                if output_name not in stack_outputs[target_stack]:
                    available = ", ".join(sorted(stack_outputs[target_stack]))
                    errors.append(
                        f"Resource '{resource.logical_id}' references non-existent output "
                        f"'{output_name}' from stack '{target_stack}'. "
                        f"Available outputs: {available}"
                    )
        
        return errors
