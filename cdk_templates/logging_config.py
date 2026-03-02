"""Logging configuration for the CDK AWS Templates System.

This module provides structured logging with multiple levels and destinations,
including console output and file logging for audit trails.
"""

import logging
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import os


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: LogRecord to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'component': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'resource_id'):
            log_data['resource_id'] = record.resource_id
        if hasattr(record, 'stack_name'):
            log_data['stack_name'] = record.stack_name
        if hasattr(record, 'environment'):
            log_data['environment'] = record.environment
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        if hasattr(record, 'rule_name'):
            log_data['rule_name'] = record.rule_name
        if hasattr(record, 'field_path'):
            log_data['field_path'] = record.field_path
        if hasattr(record, 'old_value'):
            log_data['old_value'] = record.old_value
        if hasattr(record, 'new_value'):
            log_data['new_value'] = record.new_value
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Custom formatter for human-readable console output."""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        """Initialize console formatter.
        
        Args:
            use_colors: Whether to use ANSI color codes
        """
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output.
        
        Args:
            record: LogRecord to format
            
        Returns:
            Formatted log string
        """
        # Build the message
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        component = record.name.split('.')[-1]  # Use last part of logger name
        message = record.getMessage()
        
        # Add color if enabled
        if self.use_colors:
            color = self.COLORS.get(level, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            formatted = f"{color}[{timestamp}] [{level:8}] [{component:20}]{reset} {message}"
        else:
            formatted = f"[{timestamp}] [{level:8}] [{component:20}] {message}"
        
        # Add resource ID if present
        if hasattr(record, 'resource_id'):
            formatted += f" [resource={record.resource_id}]"
        
        # Add exception info if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        
        return formatted


class AuditLogger:
    """Specialized logger for audit trail events."""
    
    def __init__(self, logger: logging.Logger):
        """Initialize audit logger.
        
        Args:
            logger: Base logger to use
        """
        self.logger = logger
    
    def log_rule_modification(
        self,
        rule_name: str,
        resource_id: str,
        field_path: str,
        old_value: Any,
        new_value: Any,
        reason: str
    ):
        """Log a deployment rule modification.
        
        Args:
            rule_name: Name of the rule that made the modification
            resource_id: ID of the resource modified
            field_path: Path to the field that was modified
            old_value: Original value
            new_value: New value
            reason: Reason for the modification
        """
        self.logger.info(
            f"Rule '{rule_name}' modified resource '{resource_id}': {reason}",
            extra={
                'operation': 'rule_modification',
                'rule_name': rule_name,
                'resource_id': resource_id,
                'field_path': field_path,
                'old_value': str(old_value),
                'new_value': str(new_value)
            }
        )
    
    def log_resource_registration(
        self,
        resource_id: str,
        resource_type: str,
        stack_name: str,
        environment: str
    ):
        """Log resource registration in the registry.
        
        Args:
            resource_id: ID of the resource
            resource_type: Type of resource
            stack_name: Stack containing the resource
            environment: Environment (dev, staging, prod)
        """
        self.logger.info(
            f"Registered resource '{resource_id}' ({resource_type}) in stack '{stack_name}'",
            extra={
                'operation': 'resource_registration',
                'resource_id': resource_id,
                'stack_name': stack_name,
                'environment': environment
            }
        )
    
    def log_resource_unregistration(
        self,
        resource_id: str,
        stack_name: str,
        environment: str
    ):
        """Log resource removal from the registry.
        
        Args:
            resource_id: ID of the resource
            stack_name: Stack containing the resource
            environment: Environment (dev, staging, prod)
        """
        self.logger.info(
            f"Unregistered resource '{resource_id}' from stack '{stack_name}'",
            extra={
                'operation': 'resource_unregistration',
                'resource_id': resource_id,
                'stack_name': stack_name,
                'environment': environment
            }
        )
    
    def log_configuration_override(
        self,
        environment: str,
        field_path: str,
        base_value: Any,
        override_value: Any
    ):
        """Log environment-specific configuration override.
        
        Args:
            environment: Environment name
            field_path: Path to the overridden field
            base_value: Base configuration value
            override_value: Environment-specific override value
        """
        self.logger.info(
            f"Applied environment override for '{field_path}' in '{environment}'",
            extra={
                'operation': 'configuration_override',
                'environment': environment,
                'field_path': field_path,
                'old_value': str(base_value),
                'new_value': str(override_value)
            }
        )
    
    def log_deployment_failure(
        self,
        stack_name: str,
        resource_id: Optional[str],
        error_message: str,
        environment: str
    ):
        """Log deployment failure with complete context.
        
        Args:
            stack_name: Stack that failed to deploy
            resource_id: Resource being deployed when failure occurred (if known)
            error_message: Error message from the deployment
            environment: Environment where deployment failed
        """
        msg = f"Deployment failed for stack '{stack_name}'"
        if resource_id:
            msg += f" at resource '{resource_id}'"
        msg += f": {error_message}"
        
        extra = {
            'operation': 'deployment_failure',
            'stack_name': stack_name,
            'environment': environment
        }
        if resource_id:
            extra['resource_id'] = resource_id
        
        self.logger.error(msg, extra=extra)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True,
    structured_format: bool = False,
    use_colors: bool = True
) -> logging.Logger:
    """Setup logging configuration for the CDK Templates System.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None to disable file logging)
        console_output: Whether to output logs to console
        structured_format: Whether to use structured JSON format for file logs
        use_colors: Whether to use colors in console output
        
    Returns:
        Configured root logger
    """
    # Get root logger
    root_logger = logging.getLogger('cdk_templates')
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(ConsoleFormatter(use_colors=use_colors))
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        
        if structured_format:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific component.
    
    Args:
        name: Name of the component (e.g., 'config_loader', 'template_generator')
        
    Returns:
        Logger instance for the component
    """
    return logging.getLogger(f'cdk_templates.{name}')


def get_audit_logger() -> AuditLogger:
    """Get the audit logger for tracking system changes.
    
    Returns:
        AuditLogger instance
    """
    logger = logging.getLogger('cdk_templates.audit')
    return AuditLogger(logger)


# Default logging configuration
def configure_default_logging():
    """Configure default logging for the system."""
    # Determine log file path
    log_dir = os.environ.get('CDK_TEMPLATES_LOG_DIR', './logs')
    log_file = os.path.join(log_dir, 'cdk_templates.log')
    
    # Determine log level from environment
    log_level = os.environ.get('CDK_TEMPLATES_LOG_LEVEL', 'INFO')
    
    # Setup logging
    setup_logging(
        log_level=log_level,
        log_file=log_file,
        console_output=True,
        structured_format=True,
        use_colors=True
    )


# Configure logging on module import
configure_default_logging()
