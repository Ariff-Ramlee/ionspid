"""
Basecalling commands for the iONspID CLI.

This module provides commands for basecalling Oxford Nanopore raw data using Dorado.
"""

import time
from pathlib import Path
from typing import Optional

import click

from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.core.basecalling import (
    DeviceType,
    check_dorado_installation,
    detect_hardware,
    run_dorado,
    get_available_models,
    download_model,
    estimate_basecalling_time,
    DoradoNotFoundError,
    DoradoExecutionError,
    DoradoVersionError
)
from ionspid.core.basecalling.params import BasecallRunParams, ModelDownloadParams


@click.group(name="basecall")
def basecall_cli():
    """Commands for basecalling raw data."""
    pass


@basecall_cli.command(name="check")
@apply_standard_options
@click.pass_context
def check_installation(
    ctx,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """Check if Dorado is installed and report available hardware resources."""
    # Create CLI handler
    cli_handler = create_cli_handler("basecall.check", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        with cli_handler.create_progress_context("Checking Dorado installation..."):
            installed, message, version = check_dorado_installation()
        
        if installed:
            cli_handler.print_success(f"{message}")
        else:
            cli_handler.handle_error(Exception(message), "Dorado installation check failed")
            cli_handler.print_warning("Please ensure Dorado is installed and available in your PATH.")
            cli_handler.print_warning("Installation instructions: https://github.com/nanoporetech/dorado")
            return
        
        cli_handler.print_info("Hardware Detection:")
        with cli_handler.create_progress_context("Detecting hardware resources..."):
            hardware = detect_hardware()
        
        # Display hardware information using print_info with details
        cli_handler.print_info("System Resources:", {
            "CPU Cores": hardware['cpu_count'],
            "System Memory": f"{hardware['memory_gb']:.1f} GB"
        })
        
        if hardware['gpus']:
            cli_handler.print_info("GPU Information:")
            for i, gpu in enumerate(hardware['gpus']):
                gpu_details = {
                    "Memory": f"{gpu['memory_total_gb']:.1f} GB total, {gpu['memory_free_gb']:.1f} GB free",
                    "CUDA Device": gpu['cuda_device']
                }
                cli_handler.print_info(f"GPU {i}: {gpu['name']}", gpu_details)
        else:
            cli_handler.print_warning("No compatible GPUs detected")
        
        cli_handler.print_success(f"Recommended Device: {hardware['recommended_device']}")
        
    except Exception as e:
        cli_handler.handle_error(e, "Hardware detection failed")


@basecall_cli.command(name="list-models")
@apply_standard_options
@click.pass_context
def list_models(
    ctx,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """List available Dorado models."""
    # Create CLI handler
    cli_handler = create_cli_handler("basecall.list-models", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        with cli_handler.create_progress_context("Retrieving available models..."):
            models = get_available_models()
        
        if not models:
            cli_handler.print_warning("No models found. Please check your Dorado installation.")
            return
        
        cli_handler.print_info(f"Available Dorado Models: ({len(models)} total)")
        
        # Group models by category
        categories = {}
        for model in models:
            name = model['name']
            category = name.split('-')[0] if '-' in name else 'Other'
            
            if category not in categories:
                categories[category] = []
            
            categories[category].append(model)
        
        # Print models by category
        for category, model_list in sorted(categories.items()):
            cli_handler.print_info(f"\n{category}")
            
            for model in sorted(model_list, key=lambda m: m['name']):
                if model.get('path'):
                    model_details = {
                        "Description": model['description'],
                        "Local Path": model['path']
                    }
                    cli_handler.print_success(f"{model['name']}", model_details)
                else:
                    cli_handler.print_success(f"{model['name']}: {model['description']}")
                    
    except Exception as e:
        cli_handler.handle_error(e, "Failed to list models")


@basecall_cli.command(name="download")
@click.argument("model", type=str, required=True)
@click.option("--output", "-o", type=click.Path(file_okay=False), help="Output directory")
@apply_standard_options
@click.pass_context
def download_model_cmd(
    ctx, 
    model: str, 
    output: Optional[str],
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """Download a Dorado model."""
    # Create CLI handler
    cli_handler = create_cli_handler("basecall.download", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Create parameters using CLI handler
        params = cli_handler.load_and_validate_params(
            cli_args={"model": model, "output": Path(output) if output else None},
            param_model=ModelDownloadParams
        )
        
        with cli_handler.create_progress_context(f"Downloading model: {params.model}..."):
            path = download_model(params.model, params.output)
            
        cli_handler.print_success(f"Model downloaded successfully to: {path}")
        
    except (DoradoNotFoundError, DoradoExecutionError) as e:
        cli_handler.handle_error(e, f"Failed to download model: {model}")
    except Exception as e:
        cli_handler.handle_error(e, "Download failed")


@basecall_cli.command(name="run")
@click.argument(
    "input_path",
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, resolve_path=True),
    required=True,
    help="Output directory for basecalled data",
)
@click.option(
    "--model",
    type=str,
    default="dna_r10.4.1_e8.2_400bps_hac@v4.2.0",
    help="Dorado basecalling model to use",
)
@click.option(
    "--device",
    type=click.Choice(["cpu", "cuda", "cuda:0", "cuda:1", "cuda:2", "cuda:3", "metal", "auto"]),
    default="auto",
    help="Compute device to use",
)
@click.option(
    "--batch-size",
    "-b",
    type=int,
    default=64,
    help="Batch size for basecalling",
)
@click.option(
    "--recursive/--no-recursive",
    "-r/-R",
    default=False,
    help="Recursively search for input files",
)
@click.option(
    "--threads",
    "-t",
    type=int,
    help="Number of CPU threads to use",
)
@click.option(
    "--barcode-kit",
    type=str,
    help="Barcode kit for demultiplexing during basecalling",
)
@click.option(
    "--sample-name",
    type=str,
    help="Sample name for output files",
)
@click.option(
    "--emit-fastq/--no-emit-fastq",
    default=True,
    help="Output FASTQ files",
)
@click.option(
    "--modified-bases/--no-modified-bases",
    default=False,
    help="Detect modified bases using Remora",
)
@click.option(
    "--max-reads",
    type=int,
    help="Maximum number of reads to process",
)
@click.option(
    "--estimate/--no-estimate",
    "-e/-E",
    default=False,
    help="Only estimate basecalling time without running",
)
@apply_standard_options
@click.pass_context
def run(ctx, input_path, **kwargs):
    """
    Run basecalling on raw Oxford Nanopore data.
    
    INPUT_PATH is the path to the directory containing POD5 files or a single POD5 file.
    
    Examples:
        ionspid basecall run /path/to/pod5_files -o /path/to/output
        ionspid basecall run /path/to/pod5_files -o /path/to/output --model dna_r10.4.1_e8.2_400bps_fast@v4.2.0
        ionspid basecall run /path/to/pod5_files -o /path/to/output --device cuda:0 --threads 8
    """
    # Create CLI handler
    cli_handler = create_cli_handler("basecall.run", kwargs)
    
    try:
        # Merge CLI arguments with kwargs
        cli_args = {"input_path": Path(input_path), **kwargs}
        
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=BasecallRunParams
        )
        
        # Check if Dorado is installed
        with cli_handler.create_progress_context("Checking Dorado installation..."):
            installed, message, version = check_dorado_installation()
            
        if not installed:
            cli_handler.handle_error(Exception(message), "Dorado not available")
            cli_handler.print_warning("Please ensure Dorado is installed and available in your PATH.")
            return
        
        # Convert to DoradoParams for core module
        dorado_params = params.to_dorado_params()
        
        # If just estimating time
        if params.estimate:
            with cli_handler.create_progress_context("Estimating basecalling time..."):
                estimation = estimate_basecalling_time(
                    params.input_path, params.model, params.device
                )
            
            estimation_details = {
                "Input": str(params.input_path),
                "Model": params.model,
                "Device": estimation['device'],
                "Estimated reads": f"{estimation['total_reads']:,}",
                "Processing speed": f"~{estimation['reads_per_second']:.1f} reads/second"
            }
            cli_handler.print_info("Basecalling Time Estimate:", estimation_details)
            
            hours = int(estimation['estimated_hours'])
            minutes = int((estimation['estimated_hours'] - hours) * 60)
            
            if hours > 0:
                time_str = f"{hours} hour{'s' if hours != 1 else ''}"
                if minutes > 0:
                    time_str += f" {minutes} minute{'s' if minutes != 1 else ''}"
            else:
                time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
                if minutes < 1:
                    time_str = "less than 1 minute"
            
            cli_handler.print_success(f"Estimated completion time: {time_str}")
            return
        
        # Run basecalling
        basecall_details = {
            "Input": str(params.input_path),
            "Model": params.model,
            "Output": str(params.output_dir),
            "Device": params.device
        }
        cli_handler.print_info("Starting Dorado basecalling...", basecall_details)
        
        start_time = time.time()
        
        # Run basecalling with progress
        with cli_handler.create_progress_context("Running basecalling..."):
            summary = run_dorado(dorado_params, show_progress=True)
        
        duration = time.time() - start_time
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        
        # Display results
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        results_details = {
            "Duration": duration_str,
            "Total reads": f"{summary.total_reads:,}",
            "Passed reads": f"{summary.passed_reads:,} ({summary.pass_rate:.1f}%)",
            "Total bases": f"{summary.total_bases:,}",
            "Mean read quality": f"{summary.mean_qscore:.2f}",
            "Mean read length": f"{summary.mean_read_length:.1f}",
            "N50 read length": f"{summary.n50_read_length:,}"
        }
        cli_handler.print_success("Basecalling completed successfully!", results_details)
        
        if summary.fastq_paths:
            cli_handler.print_info("Output files:")
            for fastq in summary.fastq_paths:
                cli_handler.print_success(str(fastq))
            
            if summary.sequencing_summary_path:
                cli_handler.print_success(str(summary.sequencing_summary_path))
            
            if summary.summary_path:
                cli_handler.print_success(str(summary.summary_path))
    
    except DoradoNotFoundError as e:
        cli_handler.handle_error(e, "Dorado not found")
        cli_handler.print_warning("Please ensure Dorado is installed and available in your PATH.")
    except DoradoExecutionError as e:
        cli_handler.handle_error(e, "Dorado execution failed")
    except Exception as e:
        cli_handler.handle_error(e, "Basecalling failed")
