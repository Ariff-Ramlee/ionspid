"""
Standardized CLI utilities for consistent interface across all commands.

This module provides common utilities for error handling, output formatting, 
progress indication, and parameter management to ensure consistency across 
all CLI commands.
"""

import sys
from typing import Any, Dict, List, Optional, Union, Type
from pathlib import Path

import click
from pydantic import BaseModel

from ionspid.utils.exceptions import iONspIDError, CLIError, InputError, ProcessingError, ConfigError
from ionspid.utils.logging import get_logger
from ionspid.cli.utils.param_loader import load_config_file, load_env_vars, merge_params, validate_parameters

logger = get_logger(__name__)

# Try to import Rich for enhanced output formatting
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.traceback import Traceback
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


class StandardCLIHandler:
    """
    Standardized CLI handler providing consistent interface patterns across all commands.
    
    This class provides:
    - Consistent parameter loading and validation
    - Standardized error handling and reporting
    - Unified output formatting (Rich or plain text)
    - Progress indication for long-running operations
    """
    
    def __init__(self, command_name: str, use_rich: bool = True):
        """
        Initialize CLI handler.
        
        Args:
            command_name (str): Name of the command for logging and error reporting.
            use_rich (bool): Whether to use Rich formatting if available.
        """
        self.command_name = command_name
        self.use_rich = use_rich and RICH_AVAILABLE
        self.logger = get_logger(f"cli.{command_name}")
    
    def load_and_validate_params(
        self, 
        cli_args: Dict[str, Any], 
        param_model: Type[BaseModel],
        config_path: Optional[str] = None,
        env_prefix: Optional[str] = None
    ) -> BaseModel:
        """
        Load and validate parameters using the standardized parameter loading system.
        
        Args:
            cli_args (Dict[str, Any]): CLI arguments (excluding None values).
            param_model (Type[BaseModel]): Pydantic model for parameter validation.
            config_path (Optional[str]): Path to configuration file.
            env_prefix (Optional[str]): Environment variable prefix.
            
        Returns:
            BaseModel: Validated parameter instance.
            
        Raises:
            click.ClickException: If parameter loading or validation fails.
        """
        try:
            # Load config file
            config_params = load_config_file(config_path) if config_path else {}
            
            # Load environment variables
            env_params = load_env_vars(env_prefix) if env_prefix else {}
            
            # Merge parameters with correct precedence
            merged_params = merge_params(cli_args, env_params, config_params)
            
            # Validate parameters
            validated_params = validate_parameters(merged_params, param_model)
            
            self.logger.debug(f"Parameters loaded and validated successfully for {self.command_name}")
            
            return validated_params
            
        except (ConfigError, CLIError) as e:
            self.handle_error(e, "Parameter validation failed")
            raise click.ClickException(str(e))
        except Exception as e:
            self.handle_error(e, "Unexpected error during parameter loading")
            raise click.ClickException(f"Unexpected error: {str(e)}")
    
    def handle_error(
        self, 
        error: Exception, 
        context: str = "", 
        show_traceback: bool = False,
        exit_code: int = 1
    ) -> None:
        """
        Handle errors with consistent formatting and logging.
        
        Args:
            error (Exception): The exception to handle.
            context (str): Additional context for the error.
            show_traceback (bool): Whether to show full traceback.
            exit_code (int): Exit code for the process.
        """
        # Log the error
        self.logger.error(f"{context}: {str(error)}", exc_info=show_traceback)
        
        if self.use_rich:
            self._handle_error_rich(error, context, show_traceback)
        else:
            self._handle_error_plain(error, context, show_traceback)
    
    def _handle_error_rich(self, error: Exception, context: str, show_traceback: bool) -> None:
        """Handle error output using Rich formatting."""
        if isinstance(error, iONspIDError):
            console.print(f"[bold red]✗ {error.__class__.__name__}[/bold red]: {str(error)}")
        else:
            console.print(f"[bold red]✗ Unexpected Error[/bold red]: {str(error)}")
        
        if context:
            console.print(f"[dim]Context: {context}[/dim]")
        
        if show_traceback:
            tb = Traceback.from_exception(type(error), error, error.__traceback__)
            console.print(tb)
    
    def _handle_error_plain(self, error: Exception, context: str, show_traceback: bool) -> None:
        """Handle error output using plain text formatting."""
        error_type = error.__class__.__name__ if isinstance(error, iONspIDError) else "Unexpected Error"
        click.echo(f"✗ {error_type}: {str(error)}", err=True)
        
        if context:
            click.echo(f"Context: {context}", err=True)
        
        if show_traceback:
            import traceback
            click.echo(traceback.format_exc(), err=True)
    
    def print_success(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Print success message with consistent formatting.
        
        Args:
            message (str): Success message.
            details (Optional[Dict[str, Any]]): Additional details to display.
        """
        if self.use_rich:
            console.print(f"[bold green]✓[/bold green] {message}")
            if details:
                for key, value in details.items():
                    console.print(f"  [cyan]{key}:[/cyan] {value}")
        else:
            click.echo(f"✓ {message}")
            if details:
                for key, value in details.items():
                    click.echo(f"  {key}: {value}")
    
    def print_info(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Print informational message with consistent formatting.
        
        Args:
            message (str): Info message.
            details (Optional[Dict[str, Any]]): Additional details to display.
        """
        if self.use_rich:
            console.print(f"[bold blue]ℹ[/bold blue] {message}")
            if details:
                for key, value in details.items():
                    console.print(f"  [cyan]{key}:[/cyan] {value}")
        else:
            click.echo(f"ℹ {message}")
            if details:
                for key, value in details.items():
                    click.echo(f"  {key}: {value}")
    
    def print_warning(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Print warning message with consistent formatting.
        
        Args:
            message (str): Warning message.
            details (Optional[Dict[str, Any]]): Additional details to display.
        """
        if self.use_rich:
            console.print(f"[bold yellow]⚠[/bold yellow] {message}")
            if details:
                for key, value in details.items():
                    console.print(f"  [cyan]{key}:[/cyan] {value}")
        else:
            click.echo(f"⚠ {message}")
            if details:
                for key, value in details.items():
                    click.echo(f"  {key}: {value}")
    
    def create_progress_context(self, description: str = "Processing..."):
        """
        Create a progress context manager for long-running operations.
        
        Args:
            description (str): Description of the operation.
            
        Returns:
            Context manager for progress indication.
        """
        if self.use_rich:
            return console.status(f"[bold cyan]{description}")
        else:
            return _PlainProgressContext(description)
    
    def create_table(self, title: str, columns: List[str]) -> Union['Table', '_PlainTable']:
        """
        Create a table for structured output.
        
        Args:
            title (str): Table title.
            columns (List[str]): Column headers.
            
        Returns:
            Table object (Rich Table or plain text equivalent).
        """
        if self.use_rich:
            table = Table(title=title)
            for column in columns:
                table.add_column(column)
            return table
        else:
            return _PlainTable(title, columns)
    
    def print_table(self, table: Union['Table', '_PlainTable']) -> None:
        """
        Print a table with consistent formatting.
        
        Args:
            table: Table object to print.
        """
        if self.use_rich and hasattr(table, 'add_row'):
            console.print(table)
        else:
            table.print()


class _PlainProgressContext:
    """Plain text progress context for when Rich is not available."""
    
    def __init__(self, description: str):
        self.description = description
    
    def __enter__(self):
        click.echo(f"{self.description}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            click.echo("✓ Complete")
        else:
            click.echo("✗ Failed")


class _PlainTable:
    """Plain text table for when Rich is not available."""
    
    def __init__(self, title: str, columns: List[str]):
        self.title = title
        self.columns = columns
        self.rows = []
        self.col_widths = [len(col) for col in columns]
    
    def add_row(self, *values):
        """Add a row to the table."""
        row = list(values)
        self.rows.append(row)
        # Update column widths
        for i, value in enumerate(row):
            if i < len(self.col_widths):
                self.col_widths[i] = max(self.col_widths[i], len(str(value)))
    
    def print(self):
        """Print the table in plain text format."""
        if self.title:
            click.echo(f"\n{self.title}")
            click.echo("=" * len(self.title))
        
        # Print header
        header_parts = []
        for i, col in enumerate(self.columns):
            width = self.col_widths[i] if i < len(self.col_widths) else len(col)
            header_parts.append(col.ljust(width))
        click.echo(" | ".join(header_parts))
        
        # Print separator
        sep_parts = []
        for i, col in enumerate(self.columns):
            width = self.col_widths[i] if i < len(self.col_widths) else len(col)
            sep_parts.append("-" * width)
        click.echo("-|-".join(sep_parts))
        
        # Print rows
        for row in self.rows:
            row_parts = []
            for i, value in enumerate(row):
                width = self.col_widths[i] if i < len(self.col_widths) else len(str(value))
                row_parts.append(str(value).ljust(width))
            click.echo(" | ".join(row_parts))
        
        click.echo()


def get_standard_cli_options():
    """
    Get standard CLI options that should be available on all commands.
    
    Returns:
        List of Click decorators for common options.
    """
    return [
        click.option(
            "--config",
            type=click.Path(exists=True, dir_okay=False, resolve_path=True),
            help="Path to configuration file (YAML or JSON)"
        ),
        click.option(
            "--verbose", "-v",
            is_flag=True,
            help="Enable verbose output"
        ),
        click.option(
            "--quiet", "-q",
            is_flag=True,
            help="Suppress non-essential output"
        ),
        click.option(
            "--no-rich",
            is_flag=True,
            help="Disable Rich formatting and use plain text output"
        )
    ]


def create_cli_handler(command_name: str, kwargs: dict) -> StandardCLIHandler:
    """
    Helper function to extract standard options and create CLI handler.
    
    This function extracts standard CLI options (no_rich, config, verbose, quiet)
    from a kwargs dictionary and creates a properly configured StandardCLIHandler.
    This eliminates the need for duplicate _create_cli_handler functions across
    all CLI command modules.
    
    Args:
        command_name: Name of the command for the handler
        kwargs: Dictionary of keyword arguments to extract standard options from
        
    Returns:
        Configured StandardCLIHandler instance
    """
    # Extract standard options from kwargs
    no_rich = kwargs.pop('no_rich', False)
    config = kwargs.pop('config', None)
    verbose = kwargs.pop('verbose', False)
    quiet = kwargs.pop('quiet', False)
    
    # Initialize CLI handler
    return StandardCLIHandler(command_name, use_rich=not no_rich)


def apply_standard_options(func):
    """Apply all standard CLI options to a Click command.
    
    Args:
        func: Click command function.
        
    Returns:
        Decorated function with standard options applied.
    """
    for option in reversed(get_standard_cli_options()):
        func = option(func)
    return func
