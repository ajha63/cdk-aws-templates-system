"""Resource Registry for tracking deployed AWS resources."""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
import tempfile
import shutil
from threading import Lock

from cdk_templates.models import ResourceMetadata
from cdk_templates.exceptions import ResourceRegistryError


@dataclass
class ResourceQuery:
    """Query filters for resource discovery."""
    resource_type: Optional[str] = None
    environment: Optional[str] = None
    stack_name: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logical_name: Optional[str] = None


class ResourceRegistry:
    """
    Registry for tracking deployed AWS resources.
    
    Maintains an inventory of all resources deployed by the system,
    storing metadata including type, identifiers, stack, environment, and tags.
    Uses JSON file backend with atomic writes to prevent corruption.
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize the resource registry.
        
        Args:
            registry_path: Path to the JSON registry file. If None, uses default location.
        """
        if registry_path is None:
            # Default to .cdk-templates/registry.json in user's home directory
            registry_dir = Path.home() / '.cdk-templates'
            registry_dir.mkdir(parents=True, exist_ok=True)
            self.registry_path = registry_dir / 'registry.json'
        else:
            self.registry_path = Path(registry_path)
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup directory for state preservation
        self.backup_dir = self.registry_path.parent / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for atomic operations
        self._lock = Lock()
        
        # Initialize registry file if it doesn't exist
        if not self.registry_path.exists():
            self._write_registry({'resources': {}, 'indices': {}})
    
    def create_backup(self) -> Optional[Path]:
        """
        Create a backup of the current registry state.
        
        Returns:
            Path to the backup file, or None if registry doesn't exist
        """
        if not self.registry_path.exists():
            return None
        
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f'registry_backup_{timestamp}.json'
        
        try:
            shutil.copy2(self.registry_path, backup_path)
            
            # Keep only the last 10 backups
            self._cleanup_old_backups(keep=10)
            
            return backup_path
        except Exception as e:
            raise ResourceRegistryError(
                f"Failed to create backup: {str(e)}",
                operation="create_backup"
            )
    
    def restore_from_backup(self, backup_path: Optional[Path] = None) -> None:
        """
        Restore registry from a backup file.
        
        Args:
            backup_path: Path to backup file. If None, uses the most recent backup.
            
        Raises:
            ResourceRegistryError: If restore fails
        """
        with self._lock:
            try:
                if backup_path is None:
                    # Find most recent backup
                    backups = sorted(self.backup_dir.glob('registry_backup_*.json'), reverse=True)
                    if not backups:
                        raise ResourceRegistryError(
                            "No backup files found",
                            operation="restore_from_backup"
                        )
                    backup_path = backups[0]
                
                if not backup_path.exists():
                    raise ResourceRegistryError(
                        f"Backup file not found: {backup_path}",
                        operation="restore_from_backup"
                    )
                
                # Validate backup file before restoring
                with open(backup_path, 'r') as f:
                    backup_data = json.load(f)
                
                # Restore the backup
                shutil.copy2(backup_path, self.registry_path)
                
            except json.JSONDecodeError as e:
                raise ResourceRegistryError(
                    f"Backup file is corrupted: {str(e)}",
                    operation="restore_from_backup"
                )
            except Exception as e:
                raise ResourceRegistryError(
                    f"Failed to restore from backup: {str(e)}",
                    operation="restore_from_backup"
                )
    
    def _cleanup_old_backups(self, keep: int = 10) -> None:
        """
        Remove old backup files, keeping only the most recent ones.
        
        Args:
            keep: Number of backups to keep
        """
        backups = sorted(self.backup_dir.glob('registry_backup_*.json'), reverse=True)
        
        # Remove old backups
        for backup in backups[keep:]:
            try:
                backup.unlink()
            except Exception:
                # Ignore errors when cleaning up old backups
                pass
    
    def register_resource(self, resource: ResourceMetadata) -> None:
        """
        Register a deployed resource in the inventory.
        
        Creates a backup before modifying the registry.
        
        Args:
            resource: ResourceMetadata object containing resource information
            
        Raises:
            ResourceRegistryError: If registration fails
        """
        with self._lock:
            try:
                # Create backup before modification
                self.create_backup()
                
                registry = self._read_registry()
                
                # Convert resource to dictionary
                resource_dict = self._resource_to_dict(resource)
                
                # Store resource by ID
                registry['resources'][resource.resource_id] = resource_dict
                
                # Update indices for efficient querying
                self._update_indices(registry, resource)
                
                # Write atomically
                self._write_registry(registry)
                
            except Exception as e:
                raise ResourceRegistryError(
                    f"Failed to register resource {resource.resource_id}: {str(e)}",
                    operation="register_resource"
                )
    
    def unregister_resource(self, resource_id: str) -> None:
        """
        Remove a resource from the inventory.
        
        Creates a backup before modifying the registry.
        
        Args:
            resource_id: Unique identifier of the resource to remove
            
        Raises:
            ResourceRegistryError: If unregistration fails
        """
        with self._lock:
            try:
                # Create backup before modification
                self.create_backup()
                
                registry = self._read_registry()
                
                # Check if resource exists
                if resource_id not in registry['resources']:
                    raise ResourceRegistryError(
                        f"Resource {resource_id} not found in registry",
                        operation="unregister_resource"
                    )
                
                # Get resource before removing
                resource_dict = registry['resources'][resource_id]
                
                # Remove from resources
                del registry['resources'][resource_id]
                
                # Remove from indices
                self._remove_from_indices(registry, resource_dict)
                
                # Write atomically
                self._write_registry(registry)
                
            except ResourceRegistryError:
                raise
            except Exception as e:
                raise ResourceRegistryError(
                    f"Failed to unregister resource {resource_id}: {str(e)}",
                    operation="unregister_resource"
                )
    
    def query_resources(self, filters: ResourceQuery) -> List[ResourceMetadata]:
        """
        Query resources with filtering by type, tag, name, etc.
        
        Args:
            filters: ResourceQuery object with filter criteria
            
        Returns:
            List of ResourceMetadata objects matching the filters
            
        Raises:
            ResourceRegistryError: If query fails
        """
        try:
            registry = self._read_registry()
            resources = registry['resources']
            
            # Start with all resources
            matching_resources = list(resources.values())
            
            # Apply filters
            if filters.resource_type:
                matching_resources = [
                    r for r in matching_resources
                    if r['resource_type'] == filters.resource_type
                ]
            
            if filters.environment:
                matching_resources = [
                    r for r in matching_resources
                    if r['environment'] == filters.environment
                ]
            
            if filters.stack_name:
                matching_resources = [
                    r for r in matching_resources
                    if r['stack_name'] == filters.stack_name
                ]
            
            if filters.logical_name:
                matching_resources = [
                    r for r in matching_resources
                    if r['logical_name'] == filters.logical_name
                ]
            
            # Filter by tags
            if filters.tags:
                matching_resources = [
                    r for r in matching_resources
                    if self._tags_match(r.get('tags', {}), filters.tags)
                ]
            
            # Convert back to ResourceMetadata objects
            return [self._dict_to_resource(r) for r in matching_resources]
            
        except Exception as e:
            raise ResourceRegistryError(f"Failed to query resources: {str(e)}")
    
    def get_resource(self, resource_id: str) -> Optional[ResourceMetadata]:
        """
        Get metadata for a specific resource.
        
        Args:
            resource_id: Unique identifier of the resource
            
        Returns:
            ResourceMetadata object if found, None otherwise
            
        Raises:
            ResourceRegistryError: If retrieval fails
        """
        try:
            registry = self._read_registry()
            resource_dict = registry['resources'].get(resource_id)
            
            if resource_dict is None:
                return None
            
            return self._dict_to_resource(resource_dict)
            
        except Exception as e:
            raise ResourceRegistryError(
                f"Failed to get resource {resource_id}: {str(e)}"
            )
    
    def export_inventory(self, format: str = 'json') -> str:
        """
        Export complete inventory in specified format.
        
        Args:
            format: Export format ('json' supported)
            
        Returns:
            Inventory data as formatted string
            
        Raises:
            ResourceRegistryError: If export fails
            ValueError: If format is not supported
        """
        if format.lower() != 'json':
            raise ValueError(f"Unsupported export format: {format}. Only 'json' is supported.")
        
        try:
            registry = self._read_registry()
            resources = registry['resources']
            
            # Create export structure with all resource metadata
            export_data = {
                'exported_at': datetime.now(timezone.utc).isoformat(),
                'total_resources': len(resources),
                'resources': list(resources.values())
            }
            
            return json.dumps(export_data, indent=2, default=str)
            
        except Exception as e:
            raise ResourceRegistryError(f"Failed to export inventory: {str(e)}")
    
    def register_stack_outputs(self, stack_name: str, outputs: Dict[str, str]) -> None:
        """
        Register stack outputs in the registry.
        
        Creates a backup before modifying the registry.
        
        Args:
            stack_name: Name of the stack
            outputs: Dictionary of output names to values
            
        Raises:
            ResourceRegistryError: If registration fails
        """
        with self._lock:
            try:
                # Create backup before modification
                self.create_backup()
                
                registry = self._read_registry()
                
                # Initialize stack_outputs section if it doesn't exist
                if 'stack_outputs' not in registry:
                    registry['stack_outputs'] = {}
                
                # Store outputs for this stack
                registry['stack_outputs'][stack_name] = {
                    'outputs': outputs,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Write atomically
                self._write_registry(registry)
                
            except Exception as e:
                raise ResourceRegistryError(
                    f"Failed to register stack outputs for {stack_name}: {str(e)}",
                    operation="register_stack_outputs"
                )
    
    def get_stack_outputs(self, stack_name: str) -> Optional[Dict[str, str]]:
        """
        Get outputs for a specific stack.
        
        Args:
            stack_name: Name of the stack
            
        Returns:
            Dictionary of output names to values, or None if stack not found
            
        Raises:
            ResourceRegistryError: If retrieval fails
        """
        try:
            registry = self._read_registry()
            
            if 'stack_outputs' not in registry:
                return None
            
            stack_data = registry['stack_outputs'].get(stack_name)
            if stack_data is None:
                return None
            
            return stack_data.get('outputs', {})
            
        except Exception as e:
            raise ResourceRegistryError(
                f"Failed to get stack outputs for {stack_name}: {str(e)}"
            )
    
    def _read_registry(self) -> Dict[str, Any]:
        """
        Read registry from JSON file.
        
        Returns:
            Registry dictionary
        """
        try:
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ResourceRegistryError(
                f"Registry file is corrupted: {str(e)}"
            )
        except Exception as e:
            raise ResourceRegistryError(
                f"Failed to read registry: {str(e)}"
            )
    
    def _write_registry(self, registry: Dict[str, Any]) -> None:
        """
        Write registry to JSON file atomically.
        
        Uses atomic write pattern: write to temp file, then rename.
        This prevents corruption if write is interrupted.
        
        Args:
            registry: Registry dictionary to write
        """
        try:
            # Write to temporary file first
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.registry_path.parent,
                prefix='.registry_',
                suffix='.tmp'
            )
            
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(registry, f, indent=2, default=str)
                
                # Atomic rename
                shutil.move(temp_path, self.registry_path)
                
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise
                
        except Exception as e:
            raise ResourceRegistryError(
                f"Failed to write registry: {str(e)}"
            )
    
    def _update_indices(self, registry: Dict[str, Any], resource: ResourceMetadata) -> None:
        """
        Update indices for efficient querying.
        
        Args:
            registry: Registry dictionary
            resource: Resource to index
        """
        if 'indices' not in registry:
            registry['indices'] = {}
        
        indices = registry['indices']
        
        # Index by type
        if 'by_type' not in indices:
            indices['by_type'] = {}
        if resource.resource_type not in indices['by_type']:
            indices['by_type'][resource.resource_type] = []
        if resource.resource_id not in indices['by_type'][resource.resource_type]:
            indices['by_type'][resource.resource_type].append(resource.resource_id)
        
        # Index by environment
        if 'by_environment' not in indices:
            indices['by_environment'] = {}
        if resource.environment not in indices['by_environment']:
            indices['by_environment'][resource.environment] = []
        if resource.resource_id not in indices['by_environment'][resource.environment]:
            indices['by_environment'][resource.environment].append(resource.resource_id)
        
        # Index by stack
        if 'by_stack' not in indices:
            indices['by_stack'] = {}
        if resource.stack_name not in indices['by_stack']:
            indices['by_stack'][resource.stack_name] = []
        if resource.resource_id not in indices['by_stack'][resource.stack_name]:
            indices['by_stack'][resource.stack_name].append(resource.resource_id)
        
        # Index by tags
        if 'by_tag' not in indices:
            indices['by_tag'] = {}
        for tag_key, tag_value in resource.tags.items():
            tag_index_key = f"{tag_key}:{tag_value}"
            if tag_index_key not in indices['by_tag']:
                indices['by_tag'][tag_index_key] = []
            if resource.resource_id not in indices['by_tag'][tag_index_key]:
                indices['by_tag'][tag_index_key].append(resource.resource_id)
    
    def _remove_from_indices(self, registry: Dict[str, Any], resource_dict: Dict[str, Any]) -> None:
        """
        Remove resource from all indices.
        
        Args:
            registry: Registry dictionary
            resource_dict: Resource dictionary to remove from indices
        """
        if 'indices' not in registry:
            return
        
        indices = registry['indices']
        resource_id = resource_dict['resource_id']
        
        # Remove from type index
        if 'by_type' in indices:
            resource_type = resource_dict['resource_type']
            if resource_type in indices['by_type']:
                if resource_id in indices['by_type'][resource_type]:
                    indices['by_type'][resource_type].remove(resource_id)
                if not indices['by_type'][resource_type]:
                    del indices['by_type'][resource_type]
        
        # Remove from environment index
        if 'by_environment' in indices:
            environment = resource_dict['environment']
            if environment in indices['by_environment']:
                if resource_id in indices['by_environment'][environment]:
                    indices['by_environment'][environment].remove(resource_id)
                if not indices['by_environment'][environment]:
                    del indices['by_environment'][environment]
        
        # Remove from stack index
        if 'by_stack' in indices:
            stack_name = resource_dict['stack_name']
            if stack_name in indices['by_stack']:
                if resource_id in indices['by_stack'][stack_name]:
                    indices['by_stack'][stack_name].remove(resource_id)
                if not indices['by_stack'][stack_name]:
                    del indices['by_stack'][stack_name]
        
        # Remove from tag indices
        if 'by_tag' in indices:
            for tag_key, tag_value in resource_dict.get('tags', {}).items():
                tag_index_key = f"{tag_key}:{tag_value}"
                if tag_index_key in indices['by_tag']:
                    if resource_id in indices['by_tag'][tag_index_key]:
                        indices['by_tag'][tag_index_key].remove(resource_id)
                    if not indices['by_tag'][tag_index_key]:
                        del indices['by_tag'][tag_index_key]
    
    def _tags_match(self, resource_tags: Dict[str, str], filter_tags: Dict[str, str]) -> bool:
        """
        Check if resource tags match filter tags.
        
        Args:
            resource_tags: Tags on the resource
            filter_tags: Tags to filter by
            
        Returns:
            True if all filter tags are present in resource tags with matching values
        """
        for key, value in filter_tags.items():
            if key not in resource_tags or resource_tags[key] != value:
                return False
        return True
    
    def _resource_to_dict(self, resource: ResourceMetadata) -> Dict[str, Any]:
        """
        Convert ResourceMetadata to dictionary for JSON serialization.
        
        Args:
            resource: ResourceMetadata object
            
        Returns:
            Dictionary representation
        """
        return {
            'resource_id': resource.resource_id,
            'resource_type': resource.resource_type,
            'logical_name': resource.logical_name,
            'physical_name': resource.physical_name,
            'stack_name': resource.stack_name,
            'environment': resource.environment,
            'tags': resource.tags,
            'outputs': resource.outputs,
            'dependencies': resource.dependencies,
            'created_at': resource.created_at.isoformat() if isinstance(resource.created_at, datetime) else resource.created_at,
            'updated_at': resource.updated_at.isoformat() if isinstance(resource.updated_at, datetime) else resource.updated_at,
        }
    
    def _dict_to_resource(self, resource_dict: Dict[str, Any]) -> ResourceMetadata:
        """
        Convert dictionary to ResourceMetadata object.
        
        Args:
            resource_dict: Dictionary representation
            
        Returns:
            ResourceMetadata object
        """
        # Parse datetime strings
        created_at = resource_dict['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = resource_dict['updated_at']
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        return ResourceMetadata(
            resource_id=resource_dict['resource_id'],
            resource_type=resource_dict['resource_type'],
            logical_name=resource_dict['logical_name'],
            physical_name=resource_dict['physical_name'],
            stack_name=resource_dict['stack_name'],
            environment=resource_dict['environment'],
            tags=resource_dict['tags'],
            outputs=resource_dict['outputs'],
            dependencies=resource_dict['dependencies'],
            created_at=created_at,
            updated_at=updated_at,
        )
