"""
Parameter loading and validation utilities for CLI.

This module provides functions to load, merge, and validate parameters from CLI, environment, and config files using pydantic models.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Type, Optional, Union
from pydantic import BaseModel, ValidationError

from ionspid.utils.exceptions import CLIError, ConfigError, InputError
from ionspid.utils.logging import get_logger

logger = get_logger(__name__)


def load_config_file(config_path: Optional[str]) -> Dict[str, Any]:
    """
    Load parameters from a YAML or JSON config file.

    Args:
        config_path (Optional[str]): Path to config file.

    Returns:
        Dict[str, Any]: Parameters loaded from file.
        
    Raises:
        ConfigError: If config file cannot be loaded or parsed.
    """
    if not config_path:
        return {}
        
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise ConfigError(f"Config file does not exist: {config_path}")
    
    if not config_path.is_file():
        raise ConfigError(f"Config path is not a file: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() == '.json':
                return json.load(f) or {}
            elif config_path.suffix.lower() in ('.yml', '.yaml'):
                return yaml.safe_load(f) or {}
            else:
                # Try to detect format by content
                content = f.read()
                f.seek(0)
                
                try:
                    return json.loads(content) or {}
                except json.JSONDecodeError:
                    try:
                        return yaml.safe_load(content) or {}
                    except yaml.YAMLError:
                        raise ConfigError(f"Unable to parse config file as JSON or YAML: {config_path}")
    except Exception as e:
        if isinstance(e, ConfigError):
            raise
        raise ConfigError(f"Error loading config file {config_path}: {str(e)}")


def load_env_vars(prefix: str) -> Dict[str, Any]:
    """
    Load parameters from environment variables with a given prefix.
    Supports type coercion for common types.

    Args:
        prefix (str): Prefix for environment variables (e.g., 'IONSPID_FILTER_').

    Returns:
        Dict[str, Any]: Parameters from environment variables with type coercion.
    """
    params = {}
    for k, v in os.environ.items():
        if k.startswith(prefix):
            param_name = k[len(prefix):].lower()
            # Basic type coercion
            params[param_name] = _coerce_env_value(v)
    return params


def _coerce_env_value(value: str) -> Union[str, int, float, bool]:
    """
    Coerce environment variable string value to appropriate type.
    
    Args:
        value (str): String value from environment variable.
        
    Returns:
        Union[str, int, float, bool]: Coerced value.
    """
    # Handle boolean values
    if value.lower() in ('true', 'yes', '1', 'on'):
        return True
    elif value.lower() in ('false', 'no', '0', 'off'):
        return False
    
    # Handle numeric values
    try:
        # Try integer first
        if '.' not in value and 'e' not in value.lower():
            return int(value)
        # Try float
        return float(value)
    except ValueError:
        pass
    
    # Return as string
    return value


def merge_params(cli_args: Dict[str, Any], env_vars: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge parameters with precedence: CLI > env > config.
    Filters out None values from CLI args to allow lower precedence values to take effect.

    Args:
        cli_args (Dict[str, Any]): Parameters from CLI.
        env_vars (Dict[str, Any]): Parameters from environment variables.
        config (Dict[str, Any]): Parameters from config file.

    Returns:
        Dict[str, Any]: Merged parameters.
    """
    merged = dict(config)
    merged.update(env_vars)
    # Only update with CLI args that are not None
    merged.update({k: v for k, v in cli_args.items() if v is not None})
    
    # Log the parameter sources for debugging
    logger.debug(f"Parameter sources - Config: {len(config)} params, Env: {len(env_vars)} params, CLI: {len([k for k, v in cli_args.items() if v is not None])} params")
    
    return merged


def validate_parameters(params: Dict[str, Any], model: Type[BaseModel], strict: bool = False) -> BaseModel:
    """
    Validate parameters against a pydantic model.

    Args:
        params (Dict[str, Any]): Parameters to validate.
        model (Type[BaseModel]): Pydantic model class.
        strict (bool): Whether to use strict validation mode.

    Returns:
        BaseModel: Validated model instance.
        
    Raises:
        CLIError: If parameter validation fails.
    """
    try:
        if strict:
            # Use strict mode for validation if supported
            return model.model_validate(params, strict=True)
        else:
            return model(**params)
    except ValidationError as e:
        # Format validation errors in a user-friendly way
        error_msgs = []
        for error in e.errors():
            field = '.'.join(str(loc) for loc in error['loc'])
            msg = error['msg']
            error_msgs.append(f"  {field}: {msg}")
        
        formatted_errors = '\n'.join(error_msgs)
        raise CLIError(f"Parameter validation failed:\n{formatted_errors}")
    except Exception as e:
        raise CLIError(f"Unexpected error during parameter validation: {str(e)}")


def create_config_template(model: Type[BaseModel], format: str = 'yaml') -> str:
    """
    Create a configuration file template from a Pydantic model.
    
    Args:
        model (Type[BaseModel]): Pydantic model class.
        format (str): Output format ('yaml' or 'json').
        
    Returns:
        str: Configuration template as string.
        
    Raises:
        CLIError: If format is not supported.
    """
    try:
        # Get the model schema
        if hasattr(model, 'model_json_schema'):
            schema = model.model_json_schema()
        else:
            schema = model.schema()
        
        # Create example data from schema
        example_data = {}
        properties = schema.get('properties', {})
        
        for field_name, field_info in properties.items():
            if 'default' in field_info:
                example_data[field_name] = field_info['default']
            elif 'example' in field_info:
                example_data[field_name] = field_info['example']
            elif field_info.get('type') == 'string':
                example_data[field_name] = f"example_{field_name}"
            elif field_info.get('type') == 'integer':
                example_data[field_name] = 1
            elif field_info.get('type') == 'number':
                example_data[field_name] = 1.0
            elif field_info.get('type') == 'boolean':
                example_data[field_name] = False
            elif field_info.get('type') == 'array':
                example_data[field_name] = []
        
        # Use example from schema if available
        if 'example' in schema:
            example_data = schema['example']
        
        if format.lower() == 'yaml':
            return yaml.dump(example_data, default_flow_style=False, sort_keys=True)
        elif format.lower() == 'json':
            return json.dumps(example_data, indent=2, sort_keys=True)
        else:
            raise CLIError(f"Unsupported config format: {format}. Use 'yaml' or 'json'.")
            
    except Exception as e:
        raise CLIError(f"Error creating config template: {str(e)}")


def save_config_template(model: Type[BaseModel], output_path: Path, format: str = 'yaml') -> None:
    """
    Save a configuration file template to disk.
    
    Args:
        model (Type[BaseModel]): Pydantic model class.
        output_path (Path): Path to save the template.
        format (str): Output format ('yaml' or 'json').
        
    Raises:
        CLIError: If template cannot be saved.
    """
    try:
        template = create_config_template(model, format)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
            
        logger.info(f"Configuration template saved to: {output_path}")
        
    except Exception as e:
        raise CLIError(f"Error saving config template to {output_path}: {str(e)}")
