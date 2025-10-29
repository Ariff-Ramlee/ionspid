"""
CLI command for denoising/error correction module.

This module provides CLI entry points for denoising/error correction using supported tools
with standardized parameter validation, error handling, and progress indication.
"""

from pathlib import Path
from typing import Dict, Any

import click

from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.core.denoising.params import DenoiseRunParams, DenoiseValidateParams
from ionspid.core.denoising import Denoiser, validate_denoising_dependencies, get_method_requirements
from ionspid.utils.logging import get_logger
from ionspid.utils.exceptions import InputError, ProcessingError

logger = get_logger(__name__)


@click.group(name="denoise")
def denoise_cli():
    """Commands for denoising/error correction."""
    pass


@denoise_cli.command(name="run")
@click.option(
    '--method', 
    required=True, 
    type=click.Choice(['medaka', 'racon', 'spoa', 'ngspeciesid', 'dada2', 'unoise3', 'deblur'], case_sensitive=False),
    help='Denoising method/tool'
)
@click.option(
    '--input', 
    'input_file',
    required=True, 
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help='Input FASTA/FASTQ file'
)
@click.option(
    '--output', 
    'output_file',
    required=True, 
    type=click.Path(resolve_path=True),
    help='Output corrected FASTA/FASTQ file'
)
@click.option(
    '--threads', 
    default=1, 
    show_default=True, 
    type=click.IntRange(1, 64),
    help='Number of threads'
)
@click.option(
    '--reference',
    'reference_file',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help='Reference sequences file (required for Medaka/Racon)'
)
@click.option(
    '--alignments',
    'alignments_file',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help='Alignments file for Racon (SAM/BAM format)'
)
@click.option(
    '--model-path',
    'model_path',
    type=click.Path(exists=True, resolve_path=True),
    help='Model path for Medaka'
)
@click.option(
    '--min-abundance',
    default=2,
    show_default=True,
    type=click.IntRange(1),
    help='Minimum abundance threshold'
)
@click.option(
    '--error-rate',
    default=0.01,
    show_default=True,
    type=click.FloatRange(0.0, 1.0),
    help='Expected error rate'
)
@click.option(
    '--extra-args',
    multiple=True,
    help='Extra arguments for the tool (can be specified multiple times)'
)
@click.option(
    '--detect-reverse-complements/--no-detect-reverse-complements',
    default=True,
    show_default=True,
    help='Detect and handle reverse complement sequences'
)
@click.option(
    '--rc-action',
    type=click.Choice(['merge', 'standardize_only'], case_sensitive=False),
    default='merge',
    show_default=True,
    help='Action for reverse complements: merge abundances or standardize orientation only'
)
@click.option(
    '--rc-method',
    'rc_standardization_method',
    type=click.Choice(['lexmin', 'forward'], case_sensitive=False),
    default='lexmin',
    show_default=True,
    help='Reverse complement standardization method'
)
@click.option(
    '--rc-min-abundance',
    default=1,
    show_default=True,
    type=click.IntRange(1),
    help='Minimum abundance threshold for RC detection'
)
@click.option(
    '--force',
    'force_overwrite',
    is_flag=True,
    help='Overwrite output files if they exist'
)
@apply_standard_options
@click.pass_context
def run_denoise(
    ctx, 
    method, 
    input_file, 
    output_file, 
    threads, 
    reference_file, 
    alignments_file, 
    model_path, 
    min_abundance, 
    error_rate, 
    extra_args,
    detect_reverse_complements,
    rc_action,
    rc_standardization_method,
    rc_min_abundance,
    force_overwrite,
    config=None,
    verbose=False,
    quiet=False,
    no_rich=False
):
    """
    Run denoising/error correction on amplicon sequence data.
    
    This command performs error correction using various methods including Medaka, 
    Racon, Spoa, NGSpeciesID, DADA2, UNOISE3, and Deblur.
    """
    handler = create_cli_handler("denoise.run", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Create parameter model with validation
        params = DenoiseRunParams(
            input_file=Path(input_file),
            output_file=Path(output_file),
            method=method,
            threads=threads,
            reference_file=Path(reference_file) if reference_file else None,
            alignments_file=Path(alignments_file) if alignments_file else None,
            model_path=Path(model_path) if model_path else None,
            min_abundance=min_abundance,
            error_rate=error_rate,
            detect_reverse_complements=detect_reverse_complements,
            rc_action=rc_action,
            rc_standardization_method=rc_standardization_method,
            rc_min_abundance=rc_min_abundance,
            extra_args=list(extra_args) if extra_args else None,
            force_overwrite=force_overwrite
        )
        
        # Validate method-specific requirements
        method_errors = params.validate_method_requirements()
        if method_errors:
            raise InputError(f"Method validation failed: {'; '.join(method_errors)}")
        
        # Check if output file exists and handle force overwrite
        if params.output_file.exists() and not params.force_overwrite:
            raise InputError(f"Output file already exists: {params.output_file}. Use --force to overwrite.")
        
        handler.show_progress("Starting", f"Denoising with {params.method}")
        
        # Execute the denoising
        result = _execute_denoising(params, handler)
        
        # Display results
        handler.output_data(result, f"Denoising completed using {params.method}")
        
    except Exception as e:
        handler.handle_error(e, "Denoising failed")


def _execute_denoising(params: DenoiseRunParams, handler: StandardCLIHandler) -> Dict[str, Any]:
    """Execute denoising with progress tracking."""
    
    # Convert to core configuration
    config = params.to_denoising_config()
    
    # Check dependencies
    handler.show_progress("Validating", "Checking method dependencies")
    dep_results = validate_denoising_dependencies([params.method])
    if not dep_results.get(params.method, {}).get('available', False):
        missing_deps = dep_results.get(params.method, {}).get('missing_dependencies', [])
        raise ProcessingError(f"Method {params.method} is not available. Missing dependencies: {missing_deps}")
    
    # Create and run denoiser
    handler.show_progress("Processing", "Initializing denoiser")
    denoiser = Denoiser(config)
    
    handler.show_progress("Processing", f"Running {params.method} denoising")
    denoiser.run()
    
    # Prepare result summary
    result = {
        "method": params.method,
        "input_file": str(params.input_file),
        "output_file": str(params.output_file),
        "threads": params.threads,
        "parameters": params.get_output_summary()
    }
    
    # Add file statistics if output exists
    if params.output_file.exists():
        result["output_exists"] = True
        result["output_size"] = params.output_file.stat().st_size
    else:
        result["output_exists"] = False
        handler.show_warning("Output file was not created")
    
    return result


@denoise_cli.command(name="validate")
@click.option(
    '--method',
    type=click.Choice(['medaka', 'racon', 'spoa', 'ngspeciesid', 'dada2', 'unoise3', 'deblur'], case_sensitive=False),
    help='Specific method to validate (default: validate all methods)'
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
    method, 
    skip_dependencies, 
    test_run,
    config=None,
    verbose=False,
    quiet=False,
    no_rich=False
):
    """
    Validate denoising setup and dependencies.
    
    This command checks if denoising methods are properly configured
    and their dependencies are available.
    """
    handler = create_cli_handler("denoise.validate", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Create parameter model
        params = DenoiseValidateParams(
            method=method,
            check_dependencies=not skip_dependencies,
            test_run=test_run
        )
        
        handler.show_progress("Validating", "Checking denoising setup")
        
        # Execute validation
        result = _execute_validation(params, handler)
        
        # Display results
        handler.output_data(result, "Denoising validation completed")
        
    except Exception as e:
        handler.handle_error(e, "Validation failed")


def _execute_validation(params: DenoiseValidateParams, handler: StandardCLIHandler) -> Dict[str, Any]:
    """Execute denoising validation with progress tracking."""
    
    methods_to_check = params.get_methods_to_validate()
    result = {
        "validation_summary": {},
        "overall_status": "success"
    }
    
    # Check dependencies for each method
    if params.check_dependencies:
        handler.show_progress("Checking", "Validating method dependencies")
        
        dep_results = validate_denoising_dependencies(methods_to_check)
        
        for method in methods_to_check:
            method_result = dep_results.get(method, {})
            
            validation_info = {
                "method": method,
                "available": method_result.get('available', False),
                "dependencies": method_result.get('dependencies', []),
                "missing_dependencies": method_result.get('missing_dependencies', []),
                "requirements": get_method_requirements(method)
            }
            
            if not validation_info["available"]:
                result["overall_status"] = "warning"
                handler.show_warning(f"{method}: Missing dependencies - {validation_info['missing_dependencies']}")
            else:
                handler.show_info(f"{method}: All dependencies available")
            
            result["validation_summary"][method] = validation_info
    
    # Perform test run if requested
    if params.test_run:
        handler.show_progress("Testing", "Performing test runs")
        # This would require sample data and is optional for now
        handler.show_info("Test run functionality not yet implemented")
        result["test_run_performed"] = False
    
    return result


@denoise_cli.command(name="methods")
@apply_standard_options
@click.pass_context
def list_methods(
    ctx,
    config=None,
    verbose=False,
    quiet=False,
    no_rich=False
):
    """
    List available denoising methods and their requirements.
    """
    handler = create_cli_handler("denoise.methods", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        from ionspid.core.denoising.config import get_supported_methods
        
        methods = get_supported_methods()
        
        result = {
            "available_methods": [],
            "method_count": len(methods)
        }
        
        for method in methods:
            requirements = get_method_requirements(method)
            
            method_info = {
                "name": method,
                "description": requirements.get("description", f"{method} denoising method"),
                "dependencies": requirements.get("dependencies", []),
                "input_formats": requirements.get("input_formats", ["fasta", "fastq"]),
                "output_formats": requirements.get("output_formats", ["fasta", "fastq"]),
                "parameters": requirements.get("parameters", {})
            }
            
            result["available_methods"].append(method_info)
        
        handler.output_data(result, f"Found {len(methods)} available denoising methods")
        
    except Exception as e:
        handler.handle_error(e, "Failed to list methods")

