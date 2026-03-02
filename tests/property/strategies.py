"""Hypothesis strategies for generating test data."""

from hypothesis import strategies as st
from hypothesis.strategies import composite

from cdk_templates.models import (
    Configuration,
    ConfigMetadata,
    EnvironmentConfig,
    ResourceConfig,
)


@composite
def config_metadata_strategy(draw):
    """Generate random ConfigMetadata."""
    return ConfigMetadata(
        project=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'
        ))),
        owner=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'
        ))),
        cost_center=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'
        ))),
        description=draw(st.text(min_size=0, max_size=200))
    )


@composite
def environment_config_strategy(draw):
    """Generate random EnvironmentConfig."""
    return EnvironmentConfig(
        name=draw(st.sampled_from(['dev', 'staging', 'prod', 'test'])),
        account_id=draw(st.text(min_size=12, max_size=12, alphabet=st.characters(
            whitelist_categories=('Nd',)
        ))),
        region=draw(st.sampled_from([
            'us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'
        ])),
        tags=draw(st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'
            )),
            st.text(min_size=0, max_size=50),
            min_size=0,
            max_size=5
        )),
        overrides=draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(
                st.text(max_size=50),
                st.integers(),
                st.booleans(),
                st.none()
            ),
            min_size=0,
            max_size=5
        ))
    )


@composite
def resource_config_strategy(draw):
    """Generate random ResourceConfig."""
    resource_type = draw(st.sampled_from(['vpc', 'ec2', 'rds', 's3']))
    
    # Generate logical_id that matches the pattern ^[a-z0-9-]+$
    logical_id = draw(st.text(
        min_size=3,
        max_size=30,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'
    ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
    
    # Generate properties based on resource type
    # Note: logical_id is included in properties for schema validation
    if resource_type == 'vpc':
        properties = {
            'logical_id': logical_id,
            'cidr': draw(st.sampled_from([
                '10.0.0.0/16', '10.1.0.0/16', '172.16.0.0/16', '192.168.0.0/16'
            ])),
            'availability_zones': draw(st.integers(min_value=2, max_value=6)),
            'enable_dns_hostnames': draw(st.booleans()),
            'enable_flow_logs': draw(st.booleans())
        }
    elif resource_type == 'ec2':
        properties = {
            'logical_id': logical_id,
            'instance_type': draw(st.sampled_from(['t3.micro', 't3.small', 't3.medium'])),
            'ami_id': draw(st.text(min_size=12, max_size=21, alphabet='ami-0123456789abcdef')),
            'vpc_ref': '${resource.vpc-main.id}',
            'enable_session_manager': draw(st.booleans()),
            'enable_detailed_monitoring': draw(st.booleans())
        }
    elif resource_type == 'rds':
        properties = {
            'logical_id': logical_id,
            'engine': draw(st.sampled_from(['postgres', 'mysql', 'mariadb'])),
            'engine_version': draw(st.sampled_from(['15.3', '8.0', '10.6'])),
            'instance_class': draw(st.sampled_from(['db.t3.micro', 'db.t3.small'])),
            'vpc_ref': '${resource.vpc-main.id}',
            'allocated_storage': draw(st.integers(min_value=20, max_value=1000)),
            'multi_az': draw(st.booleans()),
            'encryption_enabled': draw(st.booleans())
        }
    else:  # s3
        properties = {
            'logical_id': logical_id,
            'versioning_enabled': draw(st.booleans()),
            'encryption': draw(st.sampled_from(['aws:kms', 'AES256'])),
            'block_public_access': draw(st.booleans())
        }
    
    return ResourceConfig(
        logical_id=logical_id,
        resource_type=resource_type,
        properties=properties,
        tags=draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.text(min_size=0, max_size=50),
            min_size=0,
            max_size=5
        )),
        depends_on=draw(st.lists(
            st.text(min_size=3, max_size=30, alphabet='abcdefghijklmnopqrstuvwxyz0123456789-')
            .filter(lambda x: x and not x.startswith('-') and not x.endswith('-')),
            min_size=0,
            max_size=3
        ))
    )


@composite
def configuration_strategy(draw):
    """Generate random valid Configuration."""
    return Configuration(
        version=draw(st.sampled_from(['1.0', '2.0'])),
        metadata=draw(config_metadata_strategy()),
        environments=draw(st.dictionaries(
            st.sampled_from(['dev', 'staging', 'prod', 'test']),
            environment_config_strategy(),
            min_size=1,
            max_size=3
        )),
        resources=draw(st.lists(
            resource_config_strategy(),
            min_size=0,
            max_size=5
        )),
        deployment_rules=draw(st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'
            )),
            min_size=0,
            max_size=3
        ))
    )


@composite
def invalid_resource_config_strategy(draw):
    """
    Generate ResourceConfig with intentionally invalid properties.

    This strategy creates resource configurations that violate schema constraints
    to test that the SchemaValidator correctly rejects them.
    """
    resource_type = draw(st.sampled_from(['vpc', 'ec2', 'rds', 's3']))

    # Choose a type of violation
    violation_type = draw(st.sampled_from([
        'missing_required',
        'wrong_type',
        'pattern_mismatch',
        'out_of_range',
        'invalid_enum'
    ]))

    properties = {}

    if resource_type == 'vpc':
        if violation_type == 'missing_required':
            # Missing required 'cidr' field
            properties = {
                'availability_zones': draw(st.integers(min_value=2, max_value=6))
            }
        elif violation_type == 'wrong_type':
            # Wrong type for availability_zones (should be int)
            properties = {
                'cidr': '10.0.0.0/16',
                'availability_zones': 'three'  # string instead of int
            }
        elif violation_type == 'pattern_mismatch':
            # Invalid CIDR pattern
            properties = {
                'cidr': 'invalid-cidr',
                'availability_zones': 3
            }
        elif violation_type == 'out_of_range':
            # availability_zones out of range (max is 6)
            properties = {
                'cidr': '10.0.0.0/16',
                'availability_zones': 10
            }
        else:  # invalid_enum - not applicable for VPC, use wrong type
            properties = {
                'cidr': '10.0.0.0/16',
                'enable_dns_hostnames': 'yes'  # should be boolean
            }

    elif resource_type == 'ec2':
        if violation_type == 'missing_required':
            # Missing required 'vpc_ref' field
            properties = {
                'instance_type': 't3.medium'
            }
        elif violation_type == 'wrong_type':
            # Wrong type for enable_session_manager
            properties = {
                'instance_type': 't3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'enable_session_manager': 'true'  # string instead of boolean
            }
        elif violation_type == 'pattern_mismatch':
            # Invalid instance_type pattern
            properties = {
                'instance_type': 'invalid-type',
                'vpc_ref': '${resource.vpc-main.id}'
            }
        elif violation_type == 'out_of_range':
            # root_volume size out of range
            properties = {
                'instance_type': 't3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'root_volume': {
                    'size': 20000  # exceeds maximum of 16384
                }
            }
        else:  # invalid_enum
            properties = {
                'instance_type': 't3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'root_volume': {
                    'volume_type': 'invalid-type'  # not in enum
                }
            }

    elif resource_type == 'rds':
        if violation_type == 'missing_required':
            # Missing required 'engine' field
            properties = {
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}'
            }
        elif violation_type == 'wrong_type':
            # Wrong type for multi_az
            properties = {
                'engine': 'postgres',
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'multi_az': 'yes'  # string instead of boolean
            }
        elif violation_type == 'pattern_mismatch':
            # Invalid instance_class pattern
            properties = {
                'engine': 'postgres',
                'instance_class': 'invalid-class',
                'vpc_ref': '${resource.vpc-main.id}'
            }
        elif violation_type == 'out_of_range':
            # allocated_storage below minimum
            properties = {
                'engine': 'postgres',
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}',
                'allocated_storage': 10  # below minimum of 20
            }
        else:  # invalid_enum
            properties = {
                'engine': 'invalid-engine',  # not in enum
                'instance_class': 'db.t3.medium',
                'vpc_ref': '${resource.vpc-main.id}'
            }

    else:  # s3
        if violation_type == 'missing_required':
            # S3 only requires logical_id, which is in ResourceConfig
            # So we'll use wrong_type instead
            properties = {
                'versioning_enabled': 'yes'  # string instead of boolean
            }
        elif violation_type == 'wrong_type':
            properties = {
                'versioning_enabled': 123  # int instead of boolean
            }
        elif violation_type == 'pattern_mismatch':
            # Invalid logical_id pattern (will be caught at ResourceConfig level)
            properties = {
                'versioning_enabled': True
            }
        elif violation_type == 'out_of_range':
            # Not applicable for S3, use invalid_enum
            properties = {
                'encryption': 'invalid-encryption'  # not in enum
            }
        else:  # invalid_enum
            properties = {
                'encryption': 'RSA'  # not in enum (should be aws:kms or AES256)
            }

    # For pattern_mismatch on logical_id, create invalid logical_id
    if violation_type == 'pattern_mismatch' and resource_type == 's3':
        logical_id = 'INVALID_ID_WITH_CAPS'
    else:
        logical_id = draw(st.text(
            min_size=3,
            max_size=30,
            alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')
        ))

    return ResourceConfig(
        logical_id=logical_id,
        resource_type=resource_type,
        properties=properties,
        tags={},
        depends_on=[]
    )

