"""Template classes for generating CDK code for AWS resources."""

from cdk_templates.templates.base import ResourceTemplate, GenerationContext
from cdk_templates.templates.rds_template import RDSTemplate
from cdk_templates.templates.s3_template import S3Template

__all__ = ['ResourceTemplate', 'GenerationContext', 'RDSTemplate', 'S3Template']
