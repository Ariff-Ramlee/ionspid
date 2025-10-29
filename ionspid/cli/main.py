"""
Main CLI entry point for iONspID.

This module provides the command-line interface for the iONspID application.
"""

import sys
from pathlib import Path
from typing import List, Optional

import click

from ionspid import __version__
from ionspid.utils.logging import get_logger, configure_logging
from ionspid.config.settings import SettingsManager
from ionspid.utils.exceptions import iONspIDError, CLIError, InputError, ProcessingError, ConfigError

logger = get_logger(__name__)


@click.command(name="help-all")
@click.option(
    "--rich",
    is_flag=True,
    default=False,
    help="Use rich formatting (requires rich package)"
)
@click.pass_context
def help_all(ctx: click.Context, rich: bool):
    """
    Display comprehensive help for all available commands and subcommands.
    
    This command provides a complete overview of the iONspID CLI interface,
    showing all command groups, their subcommands, and available options.
    """
    # Get the main CLI group
    main_cli = ctx.find_root().command
    
    if rich:
        _display_help_rich(main_cli)
    else:
        _display_help_simple(main_cli)


def _display_help_rich(main_cli):
    """Display help using Rich formatting."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        
        console = Console()
        
        console.print(Panel.fit(
            "[bold cyan]iONspID: MinION NGS Species Identification Pipeline[/bold cyan]\n"
            "[dim]Comprehensive Command Reference[/dim]",
            border_style="cyan"
        ))
        
        # Display main CLI options
        console.print("\n[bold]Global Options:[/bold]")
        if main_cli.params:
            for param in main_cli.params:
                if hasattr(param, 'opts'):
                    opts_str = ', '.join(param.opts)
                    help_text = param.help or "No description available"
                    console.print(f"  [cyan]{opts_str}[/cyan]: {help_text}")
        
        # Display all command groups
        console.print("\n[bold]Available Command Groups:[/bold]")
        
        for cmd_name in sorted(main_cli.commands.keys()):
            cmd = main_cli.commands[cmd_name]
            
            # Skip help-all command in listing
            if cmd_name == "help-all":
                continue
                
            console.print(f"\n[bold green]ionspid {cmd_name}[/bold green]")
            
            if cmd.help:
                console.print(f"  [dim]{cmd.help}[/dim]")
            
            # If it's a group, show subcommands
            if hasattr(cmd, 'commands') and cmd.commands:
                console.print("  [bold]Subcommands:[/bold]")
                
                # Create table for subcommands
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("Command", style="cyan")
                table.add_column("Description", style="dim")
                
                for subcmd_name in sorted(cmd.commands.keys()):
                    subcmd = cmd.commands[subcmd_name]
                    help_text = subcmd.help or "No description available"
                    # Truncate long help text
                    if len(help_text) > 80:
                        help_text = help_text[:77] + "..."
                    table.add_row(f"{cmd_name} {subcmd_name}", help_text)
                
                console.print(table)
            else:
                # Single command
                console.print("  [dim]Single command (no subcommands)[/dim]")
        
        # Display usage examples
        console.print(Panel(
            "[bold]Common Usage Examples:[/bold]\n\n"
            "[cyan]# Inspect any sequencing data file[/cyan]\n"
            "ionspid data inspect data/sequences.fastq\n"
            "ionspid data inspect data/nanopore.pod5\n\n"
            "[cyan]# Get statistics for sequencing data[/cyan]\n"
            "ionspid data stats data/sequences.fasta --plot\n\n"
            "[cyan]# Check basecalling setup[/cyan]\n"
            "ionspid basecall check\n\n"
            "[cyan]# Run quality control on sequencing data[/cyan]\n"
            "ionspid qc run --summary data/summary.txt\n\n"
            "[cyan]# Filter sequences by quality[/cyan]\n"
            "ionspid filter run --input data.fastq --output filtered.fastq\n\n"
            "[cyan]# Run BLAST search[/cyan]\n"
            "ionspid blast search --input sequences.fasta --db nt --output results.txt\n\n"
            "[cyan]# Get detailed help for specific command[/cyan]\n"
            "ionspid <command> --help\n"
            "ionspid <command> <subcommand> --help",
            title="Examples",
            border_style="green"
        ))
        
        console.print("\n[dim]For detailed help on any command, use: ionspid <command> --help[/dim]")
        
    except ImportError:
        click.echo("Rich package not available. Use --no-rich flag for simple formatting.")
        _display_help_simple(main_cli)


def _display_help_simple(main_cli):
    """Display help using simple text formatting."""
    click.echo("=" * 70)
    click.echo("iONspID: MinION NGS Species Identification Pipeline")
    click.echo("Comprehensive Command Reference")
    click.echo("=" * 70)
    
    # Display main CLI options
    click.echo("\nGLOBAL OPTIONS:")
    if main_cli.params:
        for param in main_cli.params:
            if hasattr(param, 'opts'):
                opts_str = ', '.join(param.opts)
                help_text = param.help or "No description available"
                click.echo(f"  {opts_str:<20} {help_text}")
    
    # Display all command groups
    click.echo("\nAVAILABLE COMMAND GROUPS:")
    click.echo("-" * 40)
    
    for cmd_name in sorted(main_cli.commands.keys()):
        cmd = main_cli.commands[cmd_name]
        
        # Skip help-all command in listing
        if cmd_name == "help-all":
            continue
            
        click.echo(f"\nionspid {cmd_name}")
        
        if cmd.help:
            click.echo(f"  Description: {cmd.help}")
        
        # If it's a group, show subcommands
        if hasattr(cmd, 'commands') and cmd.commands:
            click.echo("  Subcommands:")
            
            for subcmd_name in sorted(cmd.commands.keys()):
                subcmd = cmd.commands[subcmd_name]
                help_text = subcmd.help or "No description available"
                # Truncate long help text
                if len(help_text) > 60:
                    help_text = help_text[:57] + "..."
                click.echo(f"    {cmd_name} {subcmd_name:<15} {help_text}")
        else:
            # Single command
            click.echo("  Single command (no subcommands)")
    
    # Display usage examples
    click.echo("\n" + "=" * 70)
    click.echo("COMMON USAGE EXAMPLES:")
    click.echo("=" * 70)
    click.echo()
    click.echo("# Inspect any sequencing data file")
    click.echo("ionspid data inspect data/sequences.fastq")
    click.echo("ionspid data inspect data/nanopore.pod5")
    click.echo()
    click.echo("# Get statistics for sequencing data")
    click.echo("ionspid data stats data/sequences.fasta --plot")
    click.echo()
    click.echo("# Check basecalling setup")
    click.echo("ionspid basecall check")
    click.echo()
    click.echo("# Run quality control on sequencing data")
    click.echo("ionspid qc run --summary data/summary.txt")
    click.echo()
    click.echo("# Filter sequences by quality")
    click.echo("ionspid filter run --input data.fastq --output filtered.fastq")
    click.echo()
    click.echo("# Run BLAST search")
    click.echo("ionspid blast search --input sequences.fasta --db nt --output results.txt")
    click.echo()
    click.echo("# Get detailed help for specific command")
    click.echo("ionspid <command> --help")
    click.echo("ionspid <command> <subcommand> --help")
    click.echo()
    click.echo("For detailed help on any command, use: ionspid <command> --help")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="iONspID")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to configuration file",
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["debug", "info", "warning", "error", "critical"], case_sensitive=False),
    default="info",
    help="Set logging level",
)
@click.option(
    "--log-dir",
    type=click.Path(file_okay=False, resolve_path=True),
    help="Directory for log files",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output (equivalent to --log-level debug)",
)
@click.pass_context
def cli(
    ctx: click.Context,
    config: Optional[str],
    log_level: str,
    log_dir: Optional[str],
    verbose: bool,
) -> None:
    """
    iONspID: MinION NGS Species Identification Bioinformatics Pipeline.
    
    This command-line tool provides a comprehensive solution for environmental DNA (eDNA)
    metabarcoding data analysis using Oxford Nanopore sequencing technologies.
    """
    # Initialize context object to share data between commands
    ctx.ensure_object(dict)
    
    # Set up logging
    if verbose:
        log_level = "debug"
    
    configure_logging(
        log_dir=log_dir,
        console_level=log_level,
        file_level="debug",
    )
    
    # Load settings
    settings_manager = SettingsManager()
    if config:
        settings_manager.load_settings(config)
    
    # Store in context for subcommands
    ctx.obj["settings"] = settings_manager.get_settings()
    
    logger.debug("iONspID CLI initialized")


# Import and add command groups
# This will be expanded as command modules are implemented
from ionspid.cli.commands import (
    data_cli, basecall_cli, qc_cli, demux_cli, filter_cli, trim_cli, 
    polish_consensus_cli, denoise_cli, blast_cli, taxonomy_cli, chimera_cli, cluster_cli
)

cli.add_command(data_cli)
cli.add_command(basecall_cli)
cli.add_command(qc_cli)
cli.add_command(demux_cli)
cli.add_command(filter_cli)
cli.add_command(trim_cli)
cli.add_command(polish_consensus_cli)
cli.add_command(denoise_cli)
cli.add_command(blast_cli)
cli.add_command(taxonomy_cli)
cli.add_command(chimera_cli)
cli.add_command(cluster_cli)

# Add the comprehensive help command
cli.add_command(help_all)


def handle_cli_exception(exc, logger=None, debug=False):
    """
    Handle exceptions for CLI commands with user-friendly output and rich tracebacks.
    
    Args:
        exc: Exception instance
        logger: Logger to use for error logging
        debug: If True, show full traceback
    """
    try:
        from rich.console import Console
        from rich.traceback import Traceback
        console = Console()
        use_rich = True
    except ImportError:
        console = None
        use_rich = False
    
    if logger:
        logger.error(str(exc), exc_info=True)
    
    if use_rich:
        if isinstance(exc, iONspIDError):
            console.print(f"[bold red][ERROR][/bold red] {str(exc)}")
        else:
            console.print(f"[bold red][UNEXPECTED ERROR][/bold red] {str(exc)}")
        if debug:
            tb = Traceback.from_exception(type(exc), exc, exc.__traceback__)
            console.print(tb)
        else:
            console.print("For debugging details, run with --verbose flag.")
    else:
        # Fallback to plain text
        error_type = "ERROR" if isinstance(exc, iONspIDError) else "UNEXPECTED ERROR"
        click.echo(f"✗ {error_type}: {str(exc)}", err=True)
        if debug:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        else:
            click.echo("For debugging details, run with --verbose flag.", err=True)


def summarize_errors(error_list):
    """
    Generate and print a summary of errors for batch operations.
    
    Args:
        error_list: List of exception instances
    """
    if not error_list:
        return
    
    try:
        from rich.console import Console
        console = Console()
        console.print(f"[bold red]Batch completed with {len(error_list)} errors:[/bold red]")
        for i, err in enumerate(error_list, 1):
            console.print(f"  {i}. {type(err).__name__}: {err}")
    except ImportError:
        # Fallback to plain text
        click.echo(f"✗ Batch completed with {len(error_list)} errors:", err=True)
        for i, err in enumerate(error_list, 1):
            click.echo(f"  {i}. {type(err).__name__}: {err}", err=True)


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.
    
    Args:
        args: Command-line arguments (uses sys.argv if None)
        
    Returns:
        Exit code
    """
    try:
        return cli(args)
    except Exception as e:
        handle_cli_exception(e, logger, debug=False)
        return 1


if __name__ == "__main__":
    sys.exit(main())
