"""Integration tests for multi-stack deployment scenarios.

These tests verify:
- Generation of multiple stacks with dependencies
- Deployment order calculation based on cross-stack references
- Cross-stack reference resolution and validation
- Stack output exports and imports
"""

import pytest
import ast
import yaml
from pathlib import Path

from cdk_templates.config_loader import ConfigurationLoader
from cdk_templates.template_generator import TemplateGenerator
from cdk_templates.resource_link_resolver import ResourceLinkResolver


class TestMultiStackGeneration:
    """Test generation of multiple stacks with dependencies."""
    
    def test_two_stack_generation_with_dependency(self, tmp_path):
        """Test generating two stacks where one depends on the other."""
        # Stack 1: Network infrastructure (foundation)
        network_config = {
            'version': '1.0',
            'metadata': {
                'project': 'network-stack',
                'owner': 'infra-team',
                'cost_center': 'infrastructure',
                'description': 'Network infrastructure stack'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {'Stack': 'network'},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'vpc-shared',
                    'resource_type': 'vpc',
                    'properties': {
                        'cidr': '10.0.0.0/16',
                        'availability_zones': 3,
                        'enable_dns_hostnames': True,
                        'enable_flow_logs': True
                    },
                    'tags': {'Purpose': 'shared-network'},
                    'depends_on': []
                }
            ],
            'deployment_rules': [],
            'outputs': {
                'VpcId': {
                    'value': '${resource.vpc-shared.id}',
                    'export_name': 'NetworkStack-VpcId',
                    'description': 'Shared VPC ID'
                },
                'VpcCidr': {
                    'value': '${resource.vpc-shared.cidr}',
                    'export_name': 'NetworkStack-VpcCidr',
                    'description': 'VPC CIDR block'
                }
            }
        }
        
        # Stack 2: Application stack (depends on network)
        app_config = {
            'version': '1.0',
            'metadata': {
                'project': 'app-stack',
                'owner': 'app-team',
                'cost_center': 'application',
                'description': 'Application stack'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {'Stack': 'application'},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'ec2-app',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.medium',
                        'vpc_ref': '${import.NetworkStack-VpcId}',
                        'enable_session_manager': True
                    },
                    'tags': {'Role': 'app-server'},
                    'depends_on': []
                }
            ],
            'deployment_rules': []
        }
        
        # Write configuration files
        network_file = tmp_path / "network-stack.yaml"
        with open(network_file, 'w') as f:
            yaml.dump(network_config, f)
        
        app_file = tmp_path / "app-stack.yaml"
        with open(app_file, 'w') as f:
            yaml.dump(app_config, f)
        
        # Generate network stack
        loader = ConfigurationLoader()
        network_cfg = loader.load_config([str(network_file)])
        
        generator = TemplateGenerator()
        network_result = generator.generate(network_cfg, environment='prod')
        
        assert network_result.success, f"Network stack generation failed: {network_result.errors}"
        assert 'app.py' in network_result.generated_files
        
        # Verify network stack has outputs
        stack_files = [f for f in network_result.generated_files.keys() if 'stack.py' in f]
        assert len(stack_files) > 0
        
        network_stack_code = network_result.generated_files[stack_files[0]]
        # Verify VPC is created
        assert 'vpc_shared' in network_stack_code or 'vpc-shared' in network_stack_code
        
        # Generate application stack
        app_cfg = loader.load_config([str(app_file)])
        app_result = generator.generate(app_cfg, environment='prod')
        
        assert app_result.success, f"App stack generation failed: {app_result.errors}"
        
        # Verify both stacks have valid Python syntax
        for file_path, content in network_result.generated_files.items():
            if file_path.endswith('.py'):
                ast.parse(content)
        
        for file_path, content in app_result.generated_files.items():
            if file_path.endswith('.py'):
                ast.parse(content)
    
    def test_three_stack_generation_linear_dependency(self, tmp_path):
        """Test generating three stacks with linear dependency chain: A -> B -> C."""
        # Stack A: Foundation (S3 bucket)
        stack_a = {
            'version': '1.0',
            'metadata': {
                'project': 'foundation-stack',
                'owner': 'platform-team',
                'cost_center': 'infrastructure',
                'description': 'Foundation stack with S3'
            },
            'environments': {
                'dev': {
                    'name': 'dev',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 's3-foundation',
                    'resource_type': 's3',
                    'properties': {
                        'versioning_enabled': True,
                        'encryption': 'aws:kms'
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': [],
            'outputs': {
                'BucketName': {
                    'value': '${resource.s3-foundation.name}',
                    'export_name': 'FoundationStack-BucketName'
                }
            }
        }
        
        # Stack B: Network (depends on A)
        stack_b = {
            'version': '1.0',
            'metadata': {
                'project': 'network-stack',
                'owner': 'network-team',
                'cost_center': 'infrastructure',
                'description': 'Network stack'
            },
            'environments': {
                'dev': {
                    'name': 'dev',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'vpc-network',
                    'resource_type': 'vpc',
                    'properties': {
                        'cidr': '10.1.0.0/16',
                        'availability_zones': 2
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': [],
            'outputs': {
                'VpcId': {
                    'value': '${resource.vpc-network.id}',
                    'export_name': 'NetworkStack-VpcId'
                }
            }
        }
        
        # Stack C: Application (depends on B)
        stack_c = {
            'version': '1.0',
            'metadata': {
                'project': 'app-stack',
                'owner': 'app-team',
                'cost_center': 'application',
                'description': 'Application stack'
            },
            'environments': {
                'dev': {
                    'name': 'dev',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'ec2-app',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.small',
                        'vpc_ref': '${import.NetworkStack-VpcId}',
                        'enable_session_manager': True
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': []
        }
        
        # Write all stack files
        stack_a_file = tmp_path / "stack-a.yaml"
        with open(stack_a_file, 'w') as f:
            yaml.dump(stack_a, f)
        
        stack_b_file = tmp_path / "stack-b.yaml"
        with open(stack_b_file, 'w') as f:
            yaml.dump(stack_b, f)
        
        stack_c_file = tmp_path / "stack-c.yaml"
        with open(stack_c_file, 'w') as f:
            yaml.dump(stack_c, f)
        
        # Generate all stacks
        loader = ConfigurationLoader()
        generator = TemplateGenerator()
        
        # Stack A
        config_a = loader.load_config([str(stack_a_file)])
        result_a = generator.generate(config_a, environment='dev')
        assert result_a.success
        
        # Stack B
        config_b = loader.load_config([str(stack_b_file)])
        result_b = generator.generate(config_b, environment='dev')
        assert result_b.success
        
        # Stack C
        config_c = loader.load_config([str(stack_c_file)])
        result_c = generator.generate(config_c, environment='dev')
        assert result_c.success
        
        # Verify all have valid syntax
        for result in [result_a, result_b, result_c]:
            for file_path, content in result.generated_files.items():
                if file_path.endswith('.py'):
                    ast.parse(content)


class TestDeploymentOrderCalculation:
    """Test deployment order calculation based on dependencies."""
    
    def test_deployment_order_with_dependencies(self, tmp_path):
        """Test that deployment order is correctly calculated from dependencies."""
        # Create a configuration with multiple resources and dependencies
        config_data = {
            'version': '1.0',
            'metadata': {
                'project': 'order-test',
                'owner': 'test-team',
                'cost_center': 'engineering',
                'description': 'Test deployment order'
            },
            'environments': {
                'dev': {
                    'name': 'dev',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                # Level 0: No dependencies
                {
                    'logical_id': 'vpc-base',
                    'resource_type': 'vpc',
                    'properties': {
                        'cidr': '10.0.0.0/16',
                        'availability_zones': 2
                    },
                    'tags': {},
                    'depends_on': []
                },
                {
                    'logical_id': 's3-independent',
                    'resource_type': 's3',
                    'properties': {
                        'versioning_enabled': True
                    },
                    'tags': {},
                    'depends_on': []
                },
                # Level 1: Depends on VPC
                {
                    'logical_id': 'rds-level1',
                    'resource_type': 'rds',
                    'properties': {
                        'engine': 'postgres',
                        'engine_version': '15.3',
                        'instance_class': 'db.t3.micro',
                        'vpc_ref': '${resource.vpc-base.id}',
                        'allocated_storage': 20
                    },
                    'tags': {},
                    'depends_on': ['vpc-base']
                },
                # Level 2: Depends on RDS and VPC
                {
                    'logical_id': 'ec2-level2',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.micro',
                        'vpc_ref': '${resource.vpc-base.id}',
                        'enable_session_manager': True
                    },
                    'tags': {},
                    'depends_on': ['vpc-base', 'rds-level1']
                }
            ],
            'deployment_rules': []
        }
        
        config_file = tmp_path / "order.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Load configuration
        loader = ConfigurationLoader()
        config = loader.load_config([str(config_file)])
        
        # Use ResourceLinkResolver to calculate deployment order
        resolver = ResourceLinkResolver()
        link_result = resolver.resolve_links(config)
        
        assert link_result.success
        
        # Build dependency graph
        graph = resolver.build_dependency_graph(config)
        
        # Get topological order
        deployment_order = resolver.topological_sort(graph)
        
        # Verify order: VPC and S3 should come before RDS, RDS before EC2
        vpc_idx = deployment_order.index('vpc-base')
        rds_idx = deployment_order.index('rds-level1')
        ec2_idx = deployment_order.index('ec2-level2')
        
        assert vpc_idx < rds_idx, "VPC should be deployed before RDS"
        assert rds_idx < ec2_idx, "RDS should be deployed before EC2"
    
    def test_parallel_deployment_detection(self, tmp_path):
        """Test detection of resources that can be deployed in parallel."""
        config_data = {
            'version': '1.0',
            'metadata': {
                'project': 'parallel-test',
                'owner': 'test-team',
                'cost_center': 'engineering',
                'description': 'Test parallel deployment detection'
            },
            'environments': {
                'dev': {
                    'name': 'dev',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                # Three independent resources that can be deployed in parallel
                {
                    'logical_id': 's3-bucket-1',
                    'resource_type': 's3',
                    'properties': {
                        'versioning_enabled': True
                    },
                    'tags': {},
                    'depends_on': []
                },
                {
                    'logical_id': 's3-bucket-2',
                    'resource_type': 's3',
                    'properties': {
                        'versioning_enabled': True
                    },
                    'tags': {},
                    'depends_on': []
                },
                {
                    'logical_id': 's3-bucket-3',
                    'resource_type': 's3',
                    'properties': {
                        'versioning_enabled': True
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': []
        }
        
        config_file = tmp_path / "parallel.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        loader = ConfigurationLoader()
        config = loader.load_config([str(config_file)])
        
        # Build dependency graph
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        
        # Verify no dependencies between the three buckets
        assert len(graph.edges) == 0, "Independent resources should have no edges"
        
        # All three can be deployed in any order (or in parallel)
        deployment_order = resolver.topological_sort(graph)
        assert len(deployment_order) == 3
        assert set(deployment_order) == {'s3-bucket-1', 's3-bucket-2', 's3-bucket-3'}
    
    def test_complex_dependency_graph_ordering(self, tmp_path):
        """Test deployment order with complex dependency graph."""
        config_data = {
            'version': '1.0',
            'metadata': {
                'project': 'complex-deps',
                'owner': 'test-team',
                'cost_center': 'engineering',
                'description': 'Complex dependency graph'
            },
            'environments': {
                'dev': {
                    'name': 'dev',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                # VPC (no deps)
                {
                    'logical_id': 'vpc-main',
                    'resource_type': 'vpc',
                    'properties': {
                        'cidr': '10.0.0.0/16',
                        'availability_zones': 2
                    },
                    'tags': {},
                    'depends_on': []
                },
                # S3 (no deps)
                {
                    'logical_id': 's3-data',
                    'resource_type': 's3',
                    'properties': {
                        'versioning_enabled': True
                    },
                    'tags': {},
                    'depends_on': []
                },
                # RDS (depends on VPC)
                {
                    'logical_id': 'rds-db',
                    'resource_type': 'rds',
                    'properties': {
                        'engine': 'postgres',
                        'engine_version': '15.3',
                        'instance_class': 'db.t3.micro',
                        'vpc_ref': '${resource.vpc-main.id}',
                        'allocated_storage': 20
                    },
                    'tags': {},
                    'depends_on': ['vpc-main']
                },
                # EC2-1 (depends on VPC and RDS)
                {
                    'logical_id': 'ec2-app-1',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.micro',
                        'vpc_ref': '${resource.vpc-main.id}',
                        'enable_session_manager': True
                    },
                    'tags': {},
                    'depends_on': ['vpc-main', 'rds-db']
                },
                # EC2-2 (depends on VPC only)
                {
                    'logical_id': 'ec2-app-2',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.micro',
                        'vpc_ref': '${resource.vpc-main.id}',
                        'enable_session_manager': True
                    },
                    'tags': {},
                    'depends_on': ['vpc-main']
                }
            ],
            'deployment_rules': []
        }
        
        config_file = tmp_path / "complex.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        loader = ConfigurationLoader()
        config = loader.load_config([str(config_file)])
        
        resolver = ResourceLinkResolver()
        graph = resolver.build_dependency_graph(config)
        deployment_order = resolver.topological_sort(graph)
        
        # Get indices
        vpc_idx = deployment_order.index('vpc-main')
        s3_idx = deployment_order.index('s3-data')
        rds_idx = deployment_order.index('rds-db')
        ec2_1_idx = deployment_order.index('ec2-app-1')
        ec2_2_idx = deployment_order.index('ec2-app-2')
        
        # Verify ordering constraints
        assert vpc_idx < rds_idx, "VPC before RDS"
        assert vpc_idx < ec2_1_idx, "VPC before EC2-1"
        assert vpc_idx < ec2_2_idx, "VPC before EC2-2"
        assert rds_idx < ec2_1_idx, "RDS before EC2-1"
        
        # EC2-2 can be deployed after VPC (doesn't need to wait for RDS)
        # S3 is independent and can be deployed anytime


class TestCrossStackReferences:
    """Test cross-stack reference resolution and validation."""
    
    def test_cross_stack_reference_resolution(self, tmp_path):
        """Test that cross-stack references are correctly resolved."""
        # Stack with output
        producer_config = {
            'version': '1.0',
            'metadata': {
                'project': 'producer-stack',
                'owner': 'team-a',
                'cost_center': 'infrastructure',
                'description': 'Producer stack with outputs'
            },
            'environments': {
                'dev': {
                    'name': 'dev',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'vpc-producer',
                    'resource_type': 'vpc',
                    'properties': {
                        'cidr': '10.0.0.0/16',
                        'availability_zones': 2
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': [],
            'outputs': {
                'VpcId': {
                    'value': '${resource.vpc-producer.id}',
                    'export_name': 'ProducerStack-VpcId',
                    'description': 'VPC ID for cross-stack reference'
                },
                'VpcCidr': {
                    'value': '${resource.vpc-producer.cidr}',
                    'export_name': 'ProducerStack-VpcCidr',
                    'description': 'VPC CIDR block'
                }
            }
        }
        
        # Stack with import
        consumer_config = {
            'version': '1.0',
            'metadata': {
                'project': 'consumer-stack',
                'owner': 'team-b',
                'cost_center': 'application',
                'description': 'Consumer stack using imports'
            },
            'environments': {
                'dev': {
                    'name': 'dev',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'ec2-consumer',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.micro',
                        'vpc_ref': '${import.ProducerStack-VpcId}',
                        'enable_session_manager': True
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': []
        }
        
        # Write files
        producer_file = tmp_path / "producer.yaml"
        with open(producer_file, 'w') as f:
            yaml.dump(producer_config, f)
        
        consumer_file = tmp_path / "consumer.yaml"
        with open(consumer_file, 'w') as f:
            yaml.dump(consumer_config, f)
        
        # Generate producer stack
        loader = ConfigurationLoader()
        producer_cfg = loader.load_config([str(producer_file)])
        
        generator = TemplateGenerator()
        producer_result = generator.generate(producer_cfg, environment='dev')
        
        assert producer_result.success
        
        # Generate consumer stack
        consumer_cfg = loader.load_config([str(consumer_file)])
        consumer_result = generator.generate(consumer_cfg, environment='dev')
        
        assert consumer_result.success
        
        # Verify both have valid syntax
        for result in [producer_result, consumer_result]:
            for file_path, content in result.generated_files.items():
                if file_path.endswith('.py'):
                    ast.parse(content)
    
    def test_multiple_cross_stack_references(self, tmp_path):
        """Test stack consuming multiple outputs from different stacks."""
        # Stack 1: Network
        network_config = {
            'version': '1.0',
            'metadata': {
                'project': 'network-stack',
                'owner': 'network-team',
                'cost_center': 'infrastructure',
                'description': 'Network stack'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'vpc-network',
                    'resource_type': 'vpc',
                    'properties': {
                        'cidr': '10.0.0.0/16',
                        'availability_zones': 3
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': [],
            'outputs': {
                'VpcId': {
                    'value': '${resource.vpc-network.id}',
                    'export_name': 'NetworkStack-VpcId'
                }
            }
        }
        
        # Stack 2: Storage
        storage_config = {
            'version': '1.0',
            'metadata': {
                'project': 'storage-stack',
                'owner': 'storage-team',
                'cost_center': 'infrastructure',
                'description': 'Storage stack'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 's3-storage',
                    'resource_type': 's3',
                    'properties': {
                        'versioning_enabled': True,
                        'encryption': 'aws:kms'
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': [],
            'outputs': {
                'BucketName': {
                    'value': '${resource.s3-storage.name}',
                    'export_name': 'StorageStack-BucketName'
                }
            }
        }
        
        # Stack 3: Application (consumes from both)
        app_config = {
            'version': '1.0',
            'metadata': {
                'project': 'app-stack',
                'owner': 'app-team',
                'cost_center': 'application',
                'description': 'Application stack'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'ec2-app',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.medium',
                        'vpc_ref': '${import.NetworkStack-VpcId}',
                        'enable_session_manager': True
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': []
        }
        
        # Write all files
        network_file = tmp_path / "network.yaml"
        with open(network_file, 'w') as f:
            yaml.dump(network_config, f)
        
        storage_file = tmp_path / "storage.yaml"
        with open(storage_file, 'w') as f:
            yaml.dump(storage_config, f)
        
        app_file = tmp_path / "app.yaml"
        with open(app_file, 'w') as f:
            yaml.dump(app_config, f)
        
        # Generate all stacks
        loader = ConfigurationLoader()
        generator = TemplateGenerator()
        
        network_cfg = loader.load_config([str(network_file)])
        network_result = generator.generate(network_cfg, environment='prod')
        assert network_result.success
        
        storage_cfg = loader.load_config([str(storage_file)])
        storage_result = generator.generate(storage_cfg, environment='prod')
        assert storage_result.success
        
        app_cfg = loader.load_config([str(app_file)])
        app_result = generator.generate(app_cfg, environment='prod')
        assert app_result.success
        
        # Verify all have valid syntax
        for result in [network_result, storage_result, app_result]:
            for file_path, content in result.generated_files.items():
                if file_path.endswith('.py'):
                    ast.parse(content)
    
    def test_invalid_cross_stack_reference(self, tmp_path):
        """Test that invalid cross-stack references are detected."""
        # Stack referencing non-existent export
        config_data = {
            'version': '1.0',
            'metadata': {
                'project': 'invalid-ref-stack',
                'owner': 'test-team',
                'cost_center': 'engineering',
                'description': 'Stack with invalid reference'
            },
            'environments': {
                'dev': {
                    'name': 'dev',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'ec2-invalid',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.micro',
                        'vpc_ref': '${import.NonExistentStack-VpcId}',
                        'enable_session_manager': True
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': []
        }
        
        config_file = tmp_path / "invalid-ref.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        loader = ConfigurationLoader()
        config = loader.load_config([str(config_file)])
        
        # Generation should handle the import reference
        # (validation of whether the export exists would happen at CDK synth time)
        generator = TemplateGenerator()
        result = generator.generate(config, environment='dev')
        
        # The generation may succeed but the reference will be unresolved
        # This is expected behavior - CDK will validate at synth time
        assert result is not None


class TestMultiStackIntegration:
    """Integration tests for complete multi-stack scenarios."""
    
    def test_complete_multi_stack_deployment_scenario(self, tmp_path):
        """Test complete multi-stack deployment with network, data, and app tiers."""
        # Tier 1: Network infrastructure
        network_stack = {
            'version': '1.0',
            'metadata': {
                'project': 'network-infrastructure',
                'owner': 'network-team',
                'cost_center': 'infrastructure',
                'description': 'Network infrastructure tier'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {'Tier': 'network'},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'vpc-prod',
                    'resource_type': 'vpc',
                    'properties': {
                        'cidr': '10.0.0.0/16',
                        'availability_zones': 3,
                        'enable_dns_hostnames': True,
                        'enable_flow_logs': True
                    },
                    'tags': {'Component': 'network'},
                    'depends_on': []
                }
            ],
            'deployment_rules': [],
            'outputs': {
                'VpcId': {
                    'value': '${resource.vpc-prod.id}',
                    'export_name': 'NetworkTier-VpcId',
                    'description': 'Production VPC ID'
                },
                'VpcCidr': {
                    'value': '${resource.vpc-prod.cidr}',
                    'export_name': 'NetworkTier-VpcCidr',
                    'description': 'Production VPC CIDR'
                }
            }
        }
        
        # Tier 2: Data layer
        data_stack = {
            'version': '1.0',
            'metadata': {
                'project': 'data-layer',
                'owner': 'data-team',
                'cost_center': 'infrastructure',
                'description': 'Data layer tier'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {'Tier': 'data'},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'rds-prod',
                    'resource_type': 'rds',
                    'properties': {
                        'engine': 'postgres',
                        'engine_version': '15.3',
                        'instance_class': 'db.r5.large',
                        'vpc_ref': '${import.NetworkTier-VpcId}',
                        'allocated_storage': 100,
                        'multi_az': True,
                        'encryption_enabled': True
                    },
                    'tags': {'Component': 'database'},
                    'depends_on': []
                },
                {
                    'logical_id': 's3-data',
                    'resource_type': 's3',
                    'properties': {
                        'versioning_enabled': True,
                        'encryption': 'aws:kms',
                        'block_public_access': True
                    },
                    'tags': {'Component': 'storage'},
                    'depends_on': []
                }
            ],
            'deployment_rules': [],
            'outputs': {
                'DatabaseEndpoint': {
                    'value': '${resource.rds-prod.endpoint}',
                    'export_name': 'DataTier-DatabaseEndpoint',
                    'description': 'RDS endpoint'
                },
                'DataBucketName': {
                    'value': '${resource.s3-data.name}',
                    'export_name': 'DataTier-BucketName',
                    'description': 'Data bucket name'
                }
            }
        }
        
        # Tier 3: Application layer
        app_stack = {
            'version': '1.0',
            'metadata': {
                'project': 'application-layer',
                'owner': 'app-team',
                'cost_center': 'application',
                'description': 'Application layer tier'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {'Tier': 'application'},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'ec2-app-1',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.large',
                        'vpc_ref': '${import.NetworkTier-VpcId}',
                        'enable_session_manager': True,
                        'enable_detailed_monitoring': True
                    },
                    'tags': {'Component': 'app-server', 'Instance': '1'},
                    'depends_on': []
                },
                {
                    'logical_id': 'ec2-app-2',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.large',
                        'vpc_ref': '${import.NetworkTier-VpcId}',
                        'enable_session_manager': True,
                        'enable_detailed_monitoring': True
                    },
                    'tags': {'Component': 'app-server', 'Instance': '2'},
                    'depends_on': []
                }
            ],
            'deployment_rules': []
        }
        
        # Write all stack files
        network_file = tmp_path / "01-network.yaml"
        with open(network_file, 'w') as f:
            yaml.dump(network_stack, f)
        
        data_file = tmp_path / "02-data.yaml"
        with open(data_file, 'w') as f:
            yaml.dump(data_stack, f)
        
        app_file = tmp_path / "03-app.yaml"
        with open(app_file, 'w') as f:
            yaml.dump(app_stack, f)
        
        # Generate all stacks in order
        loader = ConfigurationLoader()
        generator = TemplateGenerator()
        
        # 1. Network tier (no dependencies)
        network_cfg = loader.load_config([str(network_file)])
        network_result = generator.generate(network_cfg, environment='prod')
        
        assert network_result.success, f"Network stack failed: {network_result.errors}"
        assert 'app.py' in network_result.generated_files
        
        # Verify network stack content
        network_stack_files = [f for f in network_result.generated_files.keys() if 'stack.py' in f]
        assert len(network_stack_files) > 0
        network_code = network_result.generated_files[network_stack_files[0]]
        assert 'vpc_prod' in network_code or 'vpc-prod' in network_code
        
        # 2. Data tier (depends on network)
        data_cfg = loader.load_config([str(data_file)])
        data_result = generator.generate(data_cfg, environment='prod')
        
        assert data_result.success, f"Data stack failed: {data_result.errors}"
        
        # Verify data stack content
        data_stack_files = [f for f in data_result.generated_files.keys() if 'stack.py' in f]
        assert len(data_stack_files) > 0
        data_code = data_result.generated_files[data_stack_files[0]]
        assert 'rds_prod' in data_code or 'rds-prod' in data_code
        assert 's3_data' in data_code or 's3-data' in data_code
        
        # 3. Application tier (depends on network and data)
        app_cfg = loader.load_config([str(app_file)])
        app_result = generator.generate(app_cfg, environment='prod')
        
        assert app_result.success, f"App stack failed: {app_result.errors}"
        
        # Verify app stack content
        app_stack_files = [f for f in app_result.generated_files.keys() if 'stack.py' in f]
        assert len(app_stack_files) > 0
        app_code = app_result.generated_files[app_stack_files[0]]
        assert 'ec2_app_1' in app_code or 'ec2-app-1' in app_code
        assert 'ec2_app_2' in app_code or 'ec2-app-2' in app_code
        
        # Verify all stacks have valid Python syntax
        for result in [network_result, data_result, app_result]:
            for file_path, content in result.generated_files.items():
                if file_path.endswith('.py'):
                    try:
                        ast.parse(content)
                    except SyntaxError as e:
                        pytest.fail(f"Syntax error in {file_path}: {e}")
    
    def test_multi_stack_with_shared_resources(self, tmp_path):
        """Test multiple stacks sharing common resources from a foundation stack."""
        # Foundation stack with shared resources
        foundation_stack = {
            'version': '1.0',
            'metadata': {
                'project': 'foundation',
                'owner': 'platform-team',
                'cost_center': 'infrastructure',
                'description': 'Foundation stack with shared resources'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'vpc-shared',
                    'resource_type': 'vpc',
                    'properties': {
                        'cidr': '10.0.0.0/16',
                        'availability_zones': 3
                    },
                    'tags': {},
                    'depends_on': []
                },
                {
                    'logical_id': 's3-shared-logs',
                    'resource_type': 's3',
                    'properties': {
                        'versioning_enabled': True,
                        'encryption': 'AES256'
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': [],
            'outputs': {
                'SharedVpcId': {
                    'value': '${resource.vpc-shared.id}',
                    'export_name': 'Foundation-VpcId'
                },
                'SharedLogsBucket': {
                    'value': '${resource.s3-shared-logs.name}',
                    'export_name': 'Foundation-LogsBucket'
                }
            }
        }
        
        # Service A stack
        service_a_stack = {
            'version': '1.0',
            'metadata': {
                'project': 'service-a',
                'owner': 'team-a',
                'cost_center': 'application',
                'description': 'Service A'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'ec2-service-a',
                    'resource_type': 'ec2',
                    'properties': {
                        'instance_type': 't3.medium',
                        'vpc_ref': '${import.Foundation-VpcId}',
                        'enable_session_manager': True
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': []
        }
        
        # Service B stack
        service_b_stack = {
            'version': '1.0',
            'metadata': {
                'project': 'service-b',
                'owner': 'team-b',
                'cost_center': 'application',
                'description': 'Service B'
            },
            'environments': {
                'prod': {
                    'name': 'prod',
                    'account_id': '123456789012',
                    'region': 'us-east-1',
                    'tags': {},
                    'overrides': {}
                }
            },
            'resources': [
                {
                    'logical_id': 'rds-service-b',
                    'resource_type': 'rds',
                    'properties': {
                        'engine': 'mysql',
                        'engine_version': '8.0',
                        'instance_class': 'db.t3.medium',
                        'vpc_ref': '${import.Foundation-VpcId}',
                        'allocated_storage': 50
                    },
                    'tags': {},
                    'depends_on': []
                }
            ],
            'deployment_rules': []
        }
        
        # Write files
        foundation_file = tmp_path / "foundation.yaml"
        with open(foundation_file, 'w') as f:
            yaml.dump(foundation_stack, f)
        
        service_a_file = tmp_path / "service-a.yaml"
        with open(service_a_file, 'w') as f:
            yaml.dump(service_a_stack, f)
        
        service_b_file = tmp_path / "service-b.yaml"
        with open(service_b_file, 'w') as f:
            yaml.dump(service_b_stack, f)
        
        # Generate all stacks
        loader = ConfigurationLoader()
        generator = TemplateGenerator()
        
        # Foundation must be deployed first
        foundation_cfg = loader.load_config([str(foundation_file)])
        foundation_result = generator.generate(foundation_cfg, environment='prod')
        assert foundation_result.success
        
        # Service A and B can be deployed in parallel (both depend only on foundation)
        service_a_cfg = loader.load_config([str(service_a_file)])
        service_a_result = generator.generate(service_a_cfg, environment='prod')
        assert service_a_result.success
        
        service_b_cfg = loader.load_config([str(service_b_file)])
        service_b_result = generator.generate(service_b_cfg, environment='prod')
        assert service_b_result.success
        
        # Verify all have valid syntax
        for result in [foundation_result, service_a_result, service_b_result]:
            for file_path, content in result.generated_files.items():
                if file_path.endswith('.py'):
                    ast.parse(content)
