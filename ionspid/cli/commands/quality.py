"""
Command-line interface for quality assessment.

This module provides a command-line interface for assessing the quality of
Oxford Nanopore sequencing data using standardized parameter handling.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from ionspid.core.quality.run_qc import run_qc as run_qc_func
from ionspid.core.quality.read_qc import read_qc as read_qc_func
from ionspid.core.quality.params import RunQCParams, ReadQCParams
from ionspid.core.quality.base import QCResult
from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.utils.logging import get_logger

logger = get_logger(__name__)


@click.group(name="qc")
def qc_cli():
    """Quality assessment commands."""
    pass


@apply_standard_options
@qc_cli.command(name="run")
@click.option(
    "--summary", 
    required=True, 
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to the sequencing summary file."
)
@click.option(
    "--output-dir", 
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Directory to save output files."
)
@click.option(
    "--tool",
    type=click.Choice(["native", "pycoQC", "NanoPlot", "minion_qc_python"]),
    default="native",
    show_default=True,
    help="Tool to use for run-level QC."
)
@click.option(
    "--report-format", 
    type=click.Choice(["html", "json", "both"]), 
    default="html",
    help="Format of the generated report. (native only)"
)
@click.option(
    "--title", 
    type=str, 
    default="Run Quality Assessment Report",
    help="Title for the report. (native only)"
)
@click.option(
    "--no-plots", 
    is_flag=True, 
    help="Disable plot generation. (native only)"
)
def run_qc(
    summary: Path, 
    output_dir: Optional[Path] = None, 
    tool: str = "native",
    report_format: str = "html", 
    title: str = "Run Quality Assessment Report",
    no_plots: bool = False,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Assess the quality of a sequencing run using a sequencing summary file.
    """
    # Initialize CLI handler
    cli_handler = create_cli_handler("quality.run", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare CLI arguments
        cli_args = {
            "summary": summary,
            "output_dir": output_dir,
            "tool": tool,
            "report_format": report_format,
            "title": title,
            "no_plots": no_plots
        }
        
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=RunQCParams,
            config_path=config,
            env_prefix="IONSPID_QC_"
        )
        
        if verbose:
            cli_handler.print_info("Starting run-level quality assessment", {
                "Input file": str(params.summary),
                "Tool": params.tool.value,
                "Output directory": str(params.output_dir) if params.output_dir else "Current directory"
            })
        
        # Run QC with progress indication
        with cli_handler.create_progress_context("Running quality assessment..."):
            result = run_qc_func(
                summary_file=str(params.summary), 
                tool=params.tool.value, 
                output_dir=params.output_dir,
                generate_plots=not params.no_plots  # Enable plots unless --no-plots is specified
            )
        
        # Handle results based on tool type and result format
        if isinstance(result, QCResult):
            # QCResult object (native or parsed external tools)
            reports_generated = []
            
            if params.tool.value == "native":
                # Generate reports for native tool
                if params.report_format in ["html", "both"]:
                    html_report = result.generate_report(
                        format="html", 
                        output_dir=params.output_dir,
                        config={"title": params.title, "include_plots": not params.no_plots}
                    )
                    reports_generated.append(f"HTML: {html_report}")
                
                if params.report_format in ["json", "both"]:
                    json_report = result.generate_report(
                        format="json",
                        output_dir=params.output_dir
                    )
                    reports_generated.append(f"JSON: {json_report}")
            
            # Display success message with details
            details = {
                "Source file": str(params.summary),
                "Tool": params.tool.value,
                "QC type": "Run-level (sequencing summary)",
                "Summary": result.summary
            }
            
            if reports_generated:
                details["Reports"] = "; ".join(reports_generated)
            
            # Add plot information for native tool
            if params.tool.value == "native" and not params.no_plots:
                plot_count = 0
                plot_dir = ""
                
                # Check plots directly in QCResult
                if hasattr(result, "plots") and result.plots:
                    plot_count = len(result.plots)
                    if "plot_directory" in result.metadata:
                        plot_dir = result.metadata["plot_directory"]
                
                if plot_count > 0:
                    details["Plots"] = f"{plot_count} plots generated"
                    if plot_dir:
                        details["Plot directory"] = str(plot_dir)
            
            cli_handler.print_success("Quality assessment completed", details)
            
            # Display warnings and errors if any
            if result.warnings:
                for warning in result.warnings:
                    cli_handler.print_warning(warning)
            
            if result.errors:
                for error in result.errors:
                    cli_handler.handle_error(Exception(error), "QC Error")
                    
        else:
            # String path result (fallback for external tools when parsing fails)
            cli_handler.print_success(f"External QC tool '{params.tool.value}' completed", {
                "Output": str(result)
            })
        
        return 0
        
    except Exception as e:
        cli_handler.handle_error(e, "Quality assessment failed", show_traceback=verbose)
        return 1


@apply_standard_options
@qc_cli.command(name="reads")
@click.option(
    "--fastq", 
    required=True, 
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to the FASTQ file."
)
@click.option(
    "--output-dir", 
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Directory to save output files."
)
@click.option(
    "--tool",
    type=click.Choice(["native", "FastQC", "NanoPlot"]),
    default="native",
    show_default=True,
    help="Tool to use for read-level QC."
)
@click.option(
    "--report-format", 
    type=click.Choice(["html", "json", "both"]), 
    default="html",
    help="Format of the generated report. (native only)"
)
@click.option(
    "--title", 
    type=str, 
    default="Read Quality Assessment Report",
    help="Title for the report. (native only)"
)
@click.option(
    "--no-plots", 
    is_flag=True, 
    help="Disable plot generation. (native only)"
)
@click.option(
    "--sample-size",
    type=int,
    help="Number of reads to sample for analysis (native only)"
)
@click.option(
    "--threads",
    type=int,
    default=1,
    help="Number of threads for processing"
)
def read_qc(
    fastq: Path, 
    output_dir: Optional[Path] = None, 
    tool: str = "native",
    report_format: str = "html", 
    title: str = "Read Quality Assessment Report",
    no_plots: bool = False,
    sample_size: Optional[int] = None,
    threads: int = 1,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Assess the quality of reads using a FASTQ file.
    """
    # Initialize CLI handler
    cli_handler = create_cli_handler("quality.reads", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare CLI arguments
        cli_args = {
            "fastq": fastq,
            "output_dir": output_dir,
            "tool": tool,
            "report_format": report_format,
            "title": title,
            "no_plots": no_plots,
            "sample_size": sample_size,
            "threads": threads
        }
        
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=ReadQCParams,
            config_path=config,
            env_prefix="IONSPID_QC_"
        )
        
        if verbose:
            cli_handler.print_info("Starting read-level quality assessment", {
                "Input file": str(params.fastq),
                "Tool": params.tool.value,
                "Output directory": str(params.output_dir) if params.output_dir else "Current directory",
                "Threads": str(params.threads),
                "Sample size": str(params.sample_size) if params.sample_size else "All reads"
            })
        
        # Run QC with progress indication
        with cli_handler.create_progress_context("Running read quality assessment..."):
            result = read_qc_func(
                fastq_file=str(params.fastq), 
                tool=params.tool.value, 
                output_dir=params.output_dir,
                threads=params.threads,
                sample_size=params.sample_size
            )
        
        # Handle results based on result format
        if isinstance(result, QCResult):
            # QCResult object (native or parsed external tools)
            reports_generated = []
            
            if params.tool.value == "native":
                # Generate reports for native tool
                if params.report_format in ["html", "both"]:
                    html_report = result.generate_report(
                        format="html", 
                        output_dir=params.output_dir,
                        config={"title": params.title, "include_plots": not params.no_plots}
                    )
                    reports_generated.append(f"HTML: {html_report}")
                
                if params.report_format in ["json", "both"]:
                    json_report = result.generate_report(
                        format="json",
                        output_dir=params.output_dir
                    )
                    reports_generated.append(f"JSON: {json_report}")
            
            # Display success message with details
            details = {
                "Source file": str(params.fastq),
                "Tool": params.tool.value,
                "QC type": "Read-level (FASTQ file)",
                "Summary": result.summary
            }
            
            if reports_generated:
                details["Reports"] = "; ".join(reports_generated)
            
            # Add plot information for native tool
            if params.tool.value == "native" and not params.no_plots:
                plot_count = 0
                plot_dir = ""
                
                # Check plots directly in QCResult
                if hasattr(result, "plots") and result.plots:
                    plot_count = len(result.plots)
                    if "plot_directory" in result.metadata:
                        plot_dir = result.metadata["plot_directory"]
                
                if plot_count > 0:
                    details["Plots"] = f"{plot_count} plots generated"
                    if plot_dir:
                        details["Plot directory"] = str(plot_dir)
            
            cli_handler.print_success("Read quality assessment completed", details)
            
            # Display warnings and errors if any
            if result.warnings:
                for warning in result.warnings:
                    cli_handler.print_warning(warning)
            
            if result.errors:
                for error in result.errors:
                    cli_handler.handle_error(Exception(error), "QC Error")
                    
        else:
            # String path result (fallback for external tools when parsing fails)
            cli_handler.print_success(f"External QC tool '{params.tool.value}' completed", {
                "Output": str(result)
            })
        
        return 0
        
    except Exception as e:
        cli_handler.handle_error(e, "Read quality assessment failed", show_traceback=verbose)
        return 1


@apply_standard_options
@qc_cli.command(name="batch")
@click.option(
    "--input-dir", 
    required=True, 
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Directory containing FASTQ files to assess."
)
@click.option(
    "--output-dir", 
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Directory to save output files."
)
@click.option(
    "--pattern", 
    type=str, 
    default="*.fastq*",
    help="Glob pattern to match FASTQ files."
)
@click.option(
    "--report-format", 
    type=click.Choice(["html", "json", "both"]), 
    default="html",
    help="Format of the generated reports."
)
@click.option(
    "--tool",
    type=click.Choice(["native", "FastQC", "NanoPlot"]),
    default="native",
    show_default=True,
    help="Tool to use for read-level QC."
)
@click.option(
    "--no-plots", 
    is_flag=True, 
    help="Disable plot generation."
)
@click.option(
    "--threads",
    type=int,
    default=1,
    help="Number of threads for processing each file"
)
def batch_qc(
    input_dir: Path, 
    output_dir: Optional[Path] = None, 
    pattern: str = "*.fastq*", 
    report_format: str = "html",
    tool: str = "native",
    no_plots: bool = False,
    threads: int = 1,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Assess the quality of multiple FASTQ files in a directory.
    
    Example:
        ionspid qc batch --input-dir ./fastq_files --output-dir ./qc_results
    """
    # Initialize CLI handler
    cli_handler = create_cli_handler("quality.batch", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Create output directory if not specified
        if output_dir is None:
            output_dir = input_dir / "qc_results"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find FASTQ files matching pattern
        fastq_files = list(input_dir.glob(pattern))
        
        if not fastq_files:
            cli_handler.print_warning(f"No files matching pattern '{pattern}' found in {input_dir}")
            return 0
        
        cli_handler.print_info(f"Found {len(fastq_files)} files to process", {
            "Input directory": str(input_dir),
            "Output directory": str(output_dir),
            "Tool": tool,
            "Pattern": pattern
        })
        
        # Process each file
        processed = 0
        failed = 0
        
        for i, fastq_file in enumerate(fastq_files, 1):
            if not quiet:
                cli_handler.print_info(f"Processing [{i}/{len(fastq_files)}]: {fastq_file.name}")
            
            try:
                # Create sample-specific output directory
                sample_output_dir = output_dir / fastq_file.stem
                sample_output_dir.mkdir(parents=True, exist_ok=True)
                
                # Prepare parameters for this file
                cli_args = {
                    "fastq": fastq_file,
                    "output_dir": sample_output_dir,
                    "tool": tool,
                    "report_format": report_format,
                    "title": f"Read Quality Assessment: {fastq_file.name}",
                    "no_plots": no_plots,
                    "threads": threads
                }
                
                # Validate parameters
                params = cli_handler.load_and_validate_params(
                    cli_args=cli_args,
                    param_model=ReadQCParams,
                    config_path=config,
                    env_prefix="IONSPID_QC_"
                )
                
                # Run QC
                result = read_qc_func(
                    fastq=str(params.fastq), 
                    tool=params.tool.value, 
                    output_dir=params.output_dir,
                    threads=params.threads
                )
                
                if tool == "native":
                    # Generate reports
                    if report_format in ["html", "both"]:
                        result.generate_report(
                            format="html", 
                            output_dir=params.output_dir,
                            config={"title": params.title, "include_plots": not params.no_plots}
                        )
                    
                    if report_format in ["json", "both"]:
                        result.generate_report(
                            format="json",
                            output_dir=params.output_dir
                        )
                    
                    if not quiet:
                        cli_handler.print_success(f"Completed: {fastq_file.name}", {
                            "Summary": result.summary
                        })
                        
                        if result.warnings or result.errors:
                            cli_handler.print_warning(f"Issues found: {len(result.warnings)} warnings, {len(result.errors)} errors")
                
                processed += 1
                
            except Exception as e:
                failed += 1
                cli_handler.handle_error(e, f"Failed to process {fastq_file.name}")
                if not verbose:
                    continue  # Continue with next file
        
        # Final summary
        cli_handler.print_success("Batch processing completed", {
            "Total files": str(len(fastq_files)),
            "Processed successfully": str(processed),
            "Failed": str(failed),
            "Output directory": str(output_dir)
        })
        
        return 0 if failed == 0 else 1
        
    except Exception as e:
        cli_handler.handle_error(e, "Batch quality assessment failed", show_traceback=verbose)
        return 1
