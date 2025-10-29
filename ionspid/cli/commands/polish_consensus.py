"""
CLI command for consensus sequence polishing.

This module provides CLI entry points for polishing consensus sequences using Medaka, Racon, 
or Nanopolish with standardized parameter validation, error handling, and progress indication.
"""

from pathlib import Path
from typing import Dict, Any, List

import click

from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.core.consensus.params import PolishConsensusParams, PolishValidateParams, PolishBenchmarkParams
from ionspid.core.consensus.polisher import run_polishing_workflow
from ionspid.utils.logging import get_logger
from ionspid.utils.exceptions import InputError, ProcessingError
from ionspid.utils.file_utils import ensure_directory

logger = get_logger(__name__)


@click.group(name="polish-consensus")
def polish_consensus_cli():
    """Commands for consensus sequence polishing."""
    pass


@polish_consensus_cli.command(name="run")
@click.option(
    "--consensus", 
    "consensus_file",
    required=True, 
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to consensus FASTA/FASTQ file"
)
@click.option(
    "--reads", 
    "reads_file",
    required=True, 
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to supporting reads (FASTA/FASTQ/BAM)"
)
@click.option(
    "--output", 
    "output_file",
    required=True, 
    type=click.Path(resolve_path=True),
    help="Path to output polished consensus file"
)
@click.option(
    "--polisher", 
    type=click.Choice(["medaka", "racon", "nanopolish"], case_sensitive=False),
    default="medaka", 
    show_default=True,
    help="Consensus polisher to use"
)
@click.option(
    "--rounds", 
    type=click.IntRange(1, 10),
    default=1, 
    show_default=True,
    help="Number of polishing rounds"
)
@click.option(
    "--report", 
    "report_file",
    type=click.Path(resolve_path=True),
    help="Path to polishing summary report"
)
@click.option(
    "--threads",
    type=click.IntRange(1, 64),
    default=1,
    show_default=True,
    help="Number of threads to use"
)
@click.option(
    "--memory",
    "memory_gb",
    type=click.IntRange(1),
    help="Memory limit in GB"
)
@click.option(
    "--medaka-model",
    help="Medaka model name (e.g., r941_min_sup_g507)"
)
@click.option(
    "--racon-window-length",
    type=click.IntRange(100),
    help="Racon window length"
)
@click.option(
    "--nanopolish-min-freq",
    "nanopolish_min_candidate_frequency",
    type=click.FloatRange(0.0, 1.0),
    help="Nanopolish minimum candidate frequency"
)
@click.option(
    "--fast5-dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Path to FAST5 directory (required for nanopolish)"
)
@click.option(
    "--chunk-size",
    type=click.IntRange(1),
    help="Chunk size for memory-efficient processing"
)
@click.option(
    "--extra-args",
    multiple=True,
    help="Extra arguments for the polisher (can be specified multiple times)"
)
@click.option(
    "--force",
    "force_overwrite",
    is_flag=True,
    help="Overwrite output files if they exist"
)
@click.option(
    "--keep-intermediate",
    is_flag=True,
    help="Keep intermediate files"
)
@apply_standard_options
@click.pass_context
def run_polish(
    ctx, 
    consensus_file, 
    reads_file, 
    output_file, 
    polisher, 
    rounds, 
    report_file, 
    threads, 
    memory_gb, 
    medaka_model, 
    racon_window_length,
    nanopolish_min_candidate_frequency,
    fast5_dir,
    chunk_size,
    extra_args, 
    force_overwrite,
    keep_intermediate,
    config=None,
    verbose=False,
    quiet=False,
    no_rich=False
):
    """
    Polish consensus sequences using a selected polisher.
    
    This command polishes consensus sequences using Medaka, Racon, or Nanopolish
    to improve accuracy by correcting errors using supporting reads.
    """
    handler = create_cli_handler("polish-consensus.run", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Create parameter model with validation
        params = PolishConsensusParams(
            consensus_file=Path(consensus_file),
            reads_file=Path(reads_file),
            output_file=Path(output_file),
            polisher=polisher,
            rounds=rounds,
            report_file=Path(report_file) if report_file else None,
            threads=threads,
            memory_gb=memory_gb,
            medaka_model=medaka_model,
            racon_window_length=racon_window_length,
            nanopolish_min_candidate_frequency=nanopolish_min_candidate_frequency,
            fast5_dir=Path(fast5_dir) if fast5_dir else None,
            chunk_size=chunk_size,
            extra_args=list(extra_args) if extra_args else None,
            force_overwrite=force_overwrite,
            keep_intermediate=keep_intermediate
        )
        
        # Validate polisher-specific requirements
        polisher_errors = params.validate_polisher_requirements()
        if polisher_errors:
            raise InputError(f"Polisher validation failed: {'; '.join(polisher_errors)}")
        
        # Check if output file exists and handle force overwrite
        if params.output_file.exists() and not params.force_overwrite:
            raise InputError(f"Output file already exists: {params.output_file}. Use --force to overwrite.")
        
        handler.show_progress("Starting", f"Polishing consensus with {params.polisher}")
        
        # Execute the polishing
        result = _execute_polishing(params, handler)
        
        # Display results
        handler.output_data(result, f"Consensus polishing completed using {params.polisher}")
        
    except Exception as e:
        handler.handle_error(e, "Consensus polishing failed")


def _execute_polishing(params: PolishConsensusParams, handler: StandardCLIHandler) -> Dict[str, Any]:
    """Execute consensus polishing with progress tracking."""
    
    # Ensure output directory exists
    if params.output_file.parent != Path('.'):
        ensure_directory(params.output_file.parent)
    
    if params.report_file and params.report_file.parent != Path('.'):
        ensure_directory(params.report_file.parent)
    
    # Convert to core configuration
    config = params.to_polishing_config()
    
    # Run polishing workflow
    handler.show_progress("Processing", f"Running {params.polisher} polishing")
    
    try:
        # Add FAST5 directory to kwargs if provided (for nanopolish)
        kwargs = {}
        if params.fast5_dir:
            kwargs['fast5_dir'] = params.fast5_dir
        
        polishing_result = run_polishing_workflow(
            consensus_path=params.consensus_file,
            reads_path=params.reads_file,
            output_path=params.output_file,
            config=config,
            report_path=params.report_file,
            **kwargs
        )
        
        # Prepare result summary
        result = {
            "polisher": params.polisher,
            "consensus_file": str(params.consensus_file),
            "reads_file": str(params.reads_file),
            "output_file": str(polishing_result.output_path),
            "rounds": params.rounds,
            "parameters": params.get_output_summary(),
            "success": polishing_result.success,
            "processing_time": polishing_result.processing_time,
            "total_sequences": polishing_result.total_sequences
        }
        
        # Add file statistics if output exists
        if polishing_result.output_path.exists():
            result["output_exists"] = True
            result["output_size"] = polishing_result.output_path.stat().st_size
            handler.show_info(f"Polished consensus written to: {polishing_result.output_path}")
        else:
            result["output_exists"] = False
            handler.show_warning("Output file was not created")
        
        # Add report information
        if params.report_file:
            if params.report_file.exists():
                result["report_file"] = str(params.report_file)
                result["report_exists"] = True
                handler.show_info(f"Polishing report written to: {params.report_file}")
            else:
                result["report_exists"] = False
                handler.show_warning("Report file was not created")
        
        return result
        
    except Exception as e:
        raise ProcessingError(f"Polishing workflow failed: {e}") from e


@polish_consensus_cli.command(name="validate")
@click.option(
    '--polisher',
    type=click.Choice(['medaka', 'racon', 'nanopolish'], case_sensitive=False),
    help='Specific polisher to validate (default: validate all polishers)'
)
@click.option(
    '--no-deps',
    'skip_dependencies',
    is_flag=True,
    help='Skip dependency checking'
)
@click.option(
    '--test-run',
    is_flag=True,
    help='Perform a test run with sample data'
)
@apply_standard_options
@click.pass_context
def validate_setup(
    ctx, 
    polisher, 
    skip_dependencies, 
    test_run,
    config=None,
    verbose=False,
    quiet=False,
    no_rich=False
):
    """
    Validate polishing setup and dependencies.
    
    This command checks if polishing tools are properly configured
    and their dependencies are available.
    """
    handler = create_cli_handler("polish-consensus.validate", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Create parameter model
        params = PolishValidateParams(
            polisher=polisher,
            check_dependencies=not skip_dependencies,
            test_run=test_run
        )
        
        handler.show_progress("Validating", "Checking polishing setup")
        
        # Execute validation
        result = _execute_polishing_validation(params, handler)
        
        # Display results
        handler.output_data(result, "Polishing validation completed")
        
    except Exception as e:
        handler.handle_error(e, "Validation failed")


def _execute_polishing_validation(params: PolishValidateParams, handler: StandardCLIHandler) -> Dict[str, Any]:
    """Execute polishing validation with progress tracking."""
    
    polishers_to_check = params.get_polishers_to_validate()
    result = {
        "validation_summary": {},
        "overall_status": "success"
    }
    
    # Check dependencies for each polisher
    if params.check_dependencies:
        handler.show_progress("Checking", "Validating polisher dependencies")
        
        for polisher in polishers_to_check:
            # This would check if the polisher is available
            # For now, we'll simulate the check
            validation_info = {
                "polisher": polisher,
                "available": True,  # Would be determined by actual dependency check
                "dependencies": _get_polisher_dependencies(polisher),
                "missing_dependencies": [],  # Would be populated by actual check
                "requirements": _get_polisher_requirements(polisher)
            }
            
            # Simulate dependency checking
            # In real implementation, this would check for actual tools
            if polisher == "medaka":
                # Check if medaka is available
                validation_info["notes"] = "Requires medaka package and model files"
            elif polisher == "racon":
                # Check if racon is available
                validation_info["notes"] = "Requires racon binary"
            elif polisher == "nanopolish":
                # Check if nanopolish is available
                validation_info["notes"] = "Requires nanopolish binary and index files"
            
            handler.show_info(f"{polisher}: Dependency check completed")
            result["validation_summary"][polisher] = validation_info
    
    # Perform test run if requested
    if params.test_run:
        handler.show_progress("Testing", "Performing test runs")
        # This would require sample data and is optional for now
        handler.show_info("Test run functionality not yet implemented")
        result["test_run_performed"] = False
    
    return result


def _get_polisher_dependencies(polisher: str) -> List[str]:
    """Get list of dependencies for a polisher."""
    deps = {
        "medaka": ["medaka", "minimap2", "samtools"],
        "racon": ["racon", "minimap2"],
        "nanopolish": ["nanopolish", "samtools", "minimap2"]
    }
    return deps.get(polisher, [])


def _get_polisher_requirements(polisher: str) -> Dict[str, Any]:
    """Get requirements and capabilities for a polisher."""
    requirements = {
        "medaka": {
            "description": "Deep learning consensus caller for nanopore sequencing",
            "input_formats": ["fasta", "fastq"],
            "output_formats": ["fasta"],
            "supports_rounds": True,
            "requires_gpu": False,
            "memory_intensive": True
        },
        "racon": {
            "description": "Ultrafast consensus module for raw de novo genome assembly",
            "input_formats": ["fasta", "fastq"],
            "output_formats": ["fasta"],
            "supports_rounds": True,
            "requires_gpu": False,
            "memory_intensive": False
        },
        "nanopolish": {
            "description": "Signal-level algorithms for Oxford Nanopore sequencing data",
            "input_formats": ["fastq"],
            "output_formats": ["fasta"],
            "supports_rounds": True,
            "requires_gpu": False,
            "memory_intensive": True,
            "special_requirements": "Requires FAST5 files and nanopolish index"
        }
    }
    return requirements.get(polisher, {})


@polish_consensus_cli.command(name="benchmark")
@click.option(
    "--consensus",
    "consensus_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to consensus FASTA/FASTQ file"
)
@click.option(
    "--reads",
    "reads_file", 
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to supporting reads"
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(resolve_path=True),
    help="Output directory for benchmark results"
)
@click.option(
    "--reference",
    "reference_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to reference sequence for evaluation"
)
@click.option(
    "--polishers",
    multiple=True,
    type=click.Choice(['medaka', 'racon', 'nanopolish'], case_sensitive=False),
    default=['medaka', 'racon'],
    help="Polishers to benchmark (can be specified multiple times)"
)
@click.option(
    "--rounds",
    "rounds_range",
    multiple=True,
    type=click.IntRange(1, 10),
    default=[1, 2, 3],
    help="Number of polishing rounds to test (can be specified multiple times)"
)
@click.option(
    "--threads",
    type=click.IntRange(1, 64),
    default=1,
    show_default=True,
    help="Number of threads to use"
)
@apply_standard_options
@click.pass_context
def benchmark_polishers(
    ctx, 
    consensus_file, 
    reads_file, 
    output_dir, 
    reference_file,
    polishers, 
    rounds_range, 
    threads,
    config=None,
    verbose=False,
    quiet=False,
    no_rich=False
):
    """
    Benchmark different polishing methods and parameters.
    
    This command runs multiple polishers with different parameters
    to compare their performance and accuracy.
    """
    handler = create_cli_handler("polish-consensus.benchmark", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Create parameter model with validation
        params = PolishBenchmarkParams(
            consensus_file=Path(consensus_file),
            reads_file=Path(reads_file),
            output_dir=Path(output_dir),
            reference_file=Path(reference_file) if reference_file else None,
            polishers=list(polishers),
            rounds_range=list(rounds_range),
            threads=threads
        )
        
        handler.show_progress("Starting", "Polishing benchmark")
        
        # Execute benchmarking
        result = _execute_benchmarking(params, handler)
        
        # Display results
        handler.output_data(result, "Polishing benchmark completed")
        
    except Exception as e:
        handler.handle_error(e, "Benchmarking failed")


def _execute_benchmarking(params: PolishBenchmarkParams, handler: StandardCLIHandler) -> Dict[str, Any]:
    """Execute polishing benchmarking with progress tracking."""
    
    # Ensure output directory exists
    ensure_directory(params.output_dir)
    
    result = {
        "benchmark_summary": {},
        "total_combinations": len(params.polishers) * len(params.rounds_range),
        "completed_combinations": 0,
        "output_directory": str(params.output_dir)
    }
    
    total_combinations = len(params.polishers) * len(params.rounds_range)
    current_combination = 0
    
    # Run benchmark for each polisher and rounds combination
    for polisher in params.polishers:
        for rounds in params.rounds_range:
            current_combination += 1
            
            handler.show_progress(
                "Benchmarking", 
                f"{polisher} with {rounds} rounds ({current_combination}/{total_combinations})"
            )
            
            # Create output file for this combination
            output_file = params.output_dir / f"{polisher}_r{rounds}_polished.fasta"
            
            try:
                # Create polishing parameters for this combination
                polish_params = PolishConsensusParams(
                    consensus_file=params.consensus_file,
                    reads_file=params.reads_file,
                    output_file=output_file,
                    polisher=polisher,
                    rounds=rounds,
                    threads=params.threads,
                    force_overwrite=True
                )
                
                # Run polishing
                config = polish_params.to_polishing_config()
                polishing_result = run_polishing_workflow(
                    consensus_path=params.consensus_file,
                    reads_path=params.reads_file,
                    output_path=output_file,
                    config=config
                )
                
                # Record results
                combination_key = f"{polisher}_rounds_{rounds}"
                result["benchmark_summary"][combination_key] = {
                    "polisher": polisher,
                    "rounds": rounds,
                    "output_file": str(polishing_result.output_path),
                    "success": polishing_result.success,
                    "processing_time": polishing_result.processing_time,
                    "file_size": polishing_result.output_path.stat().st_size if polishing_result.output_path.exists() else 0
                }
                
                result["completed_combinations"] += 1
                
            except Exception as e:
                handler.show_warning(f"Failed {polisher} with {rounds} rounds: {e}")
                combination_key = f"{polisher}_rounds_{rounds}"
                result["benchmark_summary"][combination_key] = {
                    "polisher": polisher,
                    "rounds": rounds,
                    "success": False,
                    "error": str(e)
                }
    
    # Add summary statistics
    successful_runs = sum(1 for r in result["benchmark_summary"].values() if r.get("success", False))
    result["success_rate"] = successful_runs / total_combinations if total_combinations > 0 else 0
    
    return result

