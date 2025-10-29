"""
Command-line interface for sequence filtering.

This module provides command-line commands for filtering DNA sequences based on
various quality criteria using standardized parameter handling.
"""

import sys
import click
from pathlib import Path
from typing import Optional

from ionspid.core.filtering import (
    FilterBase, FilterChain, LengthFilter, QualityFilter, 
    ComplexityFilter, GCContentFilter, NContentFilter
)
from ionspid.core.filtering.chain import FilterChainConfig
from ionspid.core.filtering.params import FilterParams
from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.utils.logging import get_logger
from ionspid.utils.file_formats import detect_format, is_supported_format, FileFormat

logger = get_logger(__name__)


@click.group(name="filter", help="Filter sequences based on quality criteria")
def filter_cli():
    """Filter sequences based on various quality criteria."""
    pass


@apply_standard_options
@filter_cli.command(name="run", help="Filter sequences with multiple criteria")
@click.option(
    "--input", "-i", 
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path),
    required=True,
    help="Input FASTQ/FASTA file"
)
@click.option(
    "--output", "-o", 
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    required=True,
    help="Output FASTQ/FASTA file with passing reads"
)
@click.option(
    "--failed", "-f",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    help="Output file for failed reads"
)
@click.option(
    "--report", "-r",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    help="Output HTML report file"
)
@click.option(
    "--format", "-F",
    type=click.Choice([f.value for f in FileFormat if f in (FileFormat.FASTQ, FileFormat.FASTA)], case_sensitive=False),
    default="fastq",
    show_default=True,
    help="Input file format (fastq or fasta)"
)
@click.option(
    "--min-length",
    type=int,
    default=0,
    help="Minimum sequence length to keep"
)
@click.option(
    "--max-length",
    type=int,
    help="Maximum sequence length to keep"
)
@click.option(
    "--min-quality",
    type=float,
    default=0,
    help="Minimum mean quality score to keep"
)
@click.option(
    "--min-base-quality",
    type=float,
    default=0,
    help="Minimum quality score for any base to keep"
)
@click.option(
    "--window-size",
    type=int,
    default=0,
    help="Size of sliding window for quality calculation"
)
@click.option(
    "--window-quality",
    type=float,
    default=0,
    help="Minimum mean quality within the window"
)
@click.option(
    "--threads",
    type=int,
    default=1,
    help="Number of threads for parallel processing"
)
def run_filter(
    input: Path, 
    output: Path, 
    failed: Optional[Path] = None, 
    report: Optional[Path] = None, 
    format: str = "fastq",
    min_length: int = 0,
    max_length: Optional[int] = None,
    min_quality: float = 0,
    min_base_quality: float = 0,
    window_size: int = 0,
    window_quality: float = 0,
    threads: int = 1,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Filter sequences based on multiple criteria.
    
    This command applies various quality filters to a FASTQ/FASTA file and outputs
    the passing sequences to a new file.
    """
    # Initialize CLI handler
    cli_handler = create_cli_handler("filter.run", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:            # Prepare CLI arguments
        cli_args = {
            "input": input,
            "output": output,
            "failed": failed,
            "report": report,
            "format": format,
            "min_length": min_length,
            "max_length": max_length,
            "min_mean_quality": min_quality,
            "min_base_quality": min_base_quality,
            "window_size": window_size,
            "window_quality": window_quality,
            "threads": threads,
            "parallel": threads > 1
        }
        
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=FilterParams,
            config_path=config,
            env_prefix="IONSPID_FILTER_"
        )
        
        if verbose:
            cli_handler.print_info("Starting sequence filtering", {
                "Input file": str(params.input),
                "Output file": str(params.output),
                "Min length": str(params.min_length),
                "Max length": str(params.max_length) if params.max_length else "None",
                "Min mean quality": str(params.min_mean_quality),
                "Min base quality": str(params.min_base_quality),
                "Window size": str(params.window_size),
                "Window quality": str(params.window_quality),
                "Threads": str(params.threads),
                "Command": f"ionspid filter run -i '{params.input}' -o '{params.output}' --min-length {params.min_length}" + 
                          (f" --max-length {params.max_length}" if params.max_length else "") +
                          f" --min-quality {params.min_mean_quality} --threads {params.threads}"
            })
        
        # Validate input file format
        if not is_supported_format(Path(params.input), [FileFormat.FASTQ, FileFormat.FASTA]):
            raise click.ClickException(f"Unsupported input file format: {params.input}")
        
        # Create filters based on parameters
        filters = []
        
        if params.min_length > 0 or params.max_length is not None:
            length_min = params.min_length if params.min_length > 0 else 0
            length_max = params.max_length if params.max_length is not None else "inf"
            length_filter = LengthFilter(
                min_length=params.min_length,
                max_length=params.max_length,
                name=f"Length({length_min}-{length_max})"
            )
            filters.append(length_filter)
            logger.debug(f"Created length filter: {length_filter.name}")
        
        if params.min_mean_quality > 0 or params.min_base_quality > 0 or (params.window_size > 0 and params.window_quality > 0):
            quality_filter = QualityFilter(
                min_mean_quality=params.min_mean_quality,
                min_base_quality=params.min_base_quality,
                window_size=params.window_size,
                window_quality=params.window_quality,
                name=f"Quality(mean≥{params.min_mean_quality},min≥{params.min_base_quality})"
            )
            filters.append(quality_filter)
            logger.debug(f"Created quality filter: {quality_filter.name}")
        
        if not filters:
            cli_handler.print_warning("No filters specified. At least one filter must be enabled.")
            return 1
        
        # Create filter chain
        filter_chain = FilterChain(filters)
        logger.debug(f"Created filter chain with {len(filters)} filters")
        
        # Create configuration
        config = FilterChainConfig(
            input_path=params.input,
            output_path=params.output,
            failed_path=params.failed,
            report_path=params.report,
            file_format=params.format,
            parallel=params.parallel,
            max_workers=params.threads,
            chunk_size=params.chunk_size
        )
        logger.debug(f"Filter configuration: parallel={config.parallel}, max_workers={config.max_workers}")
        
        # Run filtering with progress indication
        with cli_handler.create_progress_context("Filtering sequences..."):
            logger.debug(f"Starting filtering with command-line arguments: {cli_args}")
            result = filter_chain.filter_file(config)
            logger.debug(f"Filtering complete with result: passed={result.passed_reads}, failed={result.failed_reads}")
        
        # Display results
        details = {
            "Total reads": str(result.total_reads),
            "Passed reads": f"{result.passed_reads} ({result.pass_rate:.2f}%)",
            "Failed reads": f"{result.failed_reads} ({100 - result.pass_rate:.2f}%)",
            "Output file": str(result.output_file)
        }
        
        if result.failed_file:
            details["Failed reads file"] = str(result.failed_file)
        
        if result.summary_file:
            details["Report file"] = str(result.summary_file)
        
        cli_handler.print_success("Filtering completed", details)
        
        return 0
        
    except Exception as e:
        cli_handler.handle_error(e, "Sequence filtering failed", show_traceback=verbose)
        return 1

