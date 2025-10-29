"""
Chimera detection CLI command integration.

This module provides CLI entry points for chimera detection and removal using reference-based and de novo methods.
"""

from pathlib import Path
from typing import Optional

import click
from Bio import SeqIO

from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.core.chimera.params import ChimeraDetectionParams, ChimeraQuickParams
from ionspid.core.chimera.detection import detect_chimeras_reference, detect_chimeras_denovo
from ionspid.core.chimera.scoring import filter_sequences, generate_chimera_report
from ionspid.utils.logging import get_logger
from ionspid.utils.file_formats import detect_format, is_supported_format, FileFormat
from ionspid.utils.exceptions import InputError, ProcessingError

logger = get_logger(__name__)


@click.group(name="chimera")
def chimera_cli():
    """Commands for chimera detection and removal."""
    pass


@chimera_cli.command(name="detect")
@click.option(
    "--input", "-i", 
    "input_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path),
    required=True,
    help="Input FASTA/FASTQ file"
)
@click.option(
    "--output", "-o", 
    "output_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    required=True,
    help="Output file for non-chimeric sequences"
)
@click.option(
    "--chimeric-output", 
    "chimeric_output_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    help="Output file for chimeric sequences (optional)"
)
@click.option(
    "--method", 
    type=click.Choice(['reference', 'denovo', 'both']), 
    default='denovo',
    show_default=True,
    help="Chimera detection method"
)
@click.option(
    "--ref-db", 
    "ref_db_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path),
    help="Reference database for reference-based detection"
)
@click.option(
    "--score-threshold", 
    default=0.8, 
    type=float,
    show_default=True,
    help="Score threshold for chimera calling (0.0-1.0)"
)
@click.option(
    "--report", 
    "report_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    help="Path to save chimera report (CSV)"
)
@click.option(
    "--vsearch-path",
    default="vsearch",
    help="Path to vsearch executable"
)
@click.option(
    "--threads",
    default=1,
    type=int,
    show_default=True,
    help="Number of threads for processing"
)
@apply_standard_options
def detect_chimeras(
    input_path: Path,
    output_path: Path,
    chimeric_output_path: Optional[Path],
    method: str,
    ref_db_path: Optional[Path],
    score_threshold: float,
    report_path: Optional[Path],
    vsearch_path: str,
    threads: int,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Detect and remove chimeric sequences from FASTA/FASTQ files.
    
    This command performs chimera detection using VSEARCH with either reference-based
    or de novo methods. Sequences are classified as chimeric or non-chimeric based
    on the specified score threshold.
    
    Examples:
        ionspid chimera detect -i sequences.fasta -o clean.fasta --method denovo
        ionspid chimera detect -i input.fasta -o output.fasta --method reference --ref-db db.fasta
        ionspid chimera detect -i seqs.fasta -o clean.fasta --chimeric-output chimeric.fasta --report report.csv
    """
    # Initialize CLI handler
    handler = create_cli_handler("chimera.detect", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare CLI arguments
        cli_args = {
            "input_file": input_path,
            "output_file": output_path,
            "chimeric_output": chimeric_output_path,
            "method": method,
            "ref_db": ref_db_path,
            "score_threshold": score_threshold,
            "report": report_path,
            "vsearch_path": vsearch_path,
            "threads": threads,
            "verbose": verbose
        }
        
        # Load and validate parameters
        params = handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=ChimeraDetectionParams,
            config_path=config,
            env_prefix="IONSPID_CHIMERA_"
        )
        
        # Display configuration if verbose
        if verbose and not quiet:
            handler.print_info("Chimera Detection Configuration", params.get_output_summary())
        
        # Load sequences
        with handler.create_progress_context("Loading sequences..."):
            try:
                # Detect file format
                file_format = detect_format(params.input_file)
                if not is_supported_format(file_format, [FileFormat.FASTA, FileFormat.FASTQ]):
                    raise InputError(f"Unsupported file format: {file_format}")
                
                # Load sequences
                format_str = "fasta" if file_format == FileFormat.FASTA else "fastq"
                sequences = list(SeqIO.parse(params.input_file, format_str))
                
                if not sequences:
                    raise InputError("No sequences found in input file")
                    
            except Exception as e:
                raise InputError(f"Failed to load sequences: {str(e)}")
        
        if not quiet:
            handler.print_success(f"Loaded {len(sequences)} sequences")
        
        # Run chimera detection
        with handler.create_progress_context(f"Running {params.method} chimera detection..."):
            try:
                if params.method == 'denovo':
                    results = detect_chimeras_denovo(
                        sequences, 
                        threshold=params.score_threshold,
                        vsearch_path=params.vsearch_path
                    )
                elif params.method == 'reference':
                    results = detect_chimeras_reference(
                        sequences,
                        reference_db=str(params.ref_db),
                        threshold=params.score_threshold,
                        vsearch_path=params.vsearch_path
                    )
                elif params.method == 'both':
                    # Run both methods and combine results
                    results_denovo = detect_chimeras_denovo(
                        sequences, 
                        threshold=params.score_threshold,
                        vsearch_path=params.vsearch_path
                    )
                    results_ref = detect_chimeras_reference(
                        sequences,
                        reference_db=str(params.ref_db),
                        threshold=params.score_threshold,
                        vsearch_path=params.vsearch_path
                    )
                    # Combine results (sequence is chimeric if either method detects it)
                    results = {}
                    for seq_id in set(results_denovo.keys()) | set(results_ref.keys()):
                        denovo_result = results_denovo.get(seq_id)
                        ref_result = results_ref.get(seq_id)
                        
                        is_chimera = (denovo_result and denovo_result.is_chimera) or \
                                   (ref_result and ref_result.is_chimera)
                        score = max(
                            denovo_result.score if denovo_result else 0,
                            ref_result.score if ref_result else 0
                        )
                        
                        from ionspid.core.chimera.detection import ChimeraDetectionResult
                        results[seq_id] = ChimeraDetectionResult(is_chimera, score)
                        
            except Exception as e:
                raise ProcessingError(f"Chimera detection failed: {str(e)}")
        
        # Filter sequences
        with handler.create_progress_context("Filtering sequences..."):
            try:
                non_chimeric, chimeric = filter_sequences(
                    sequences, results, params.score_threshold
                )
            except Exception as e:
                raise ProcessingError(f"Sequence filtering failed: {str(e)}")
        
        # Write output files
        with handler.create_progress_context("Writing output files..."):
            try:
                # Write non-chimeric sequences
                SeqIO.write(non_chimeric, params.output_file, format_str)
                
                # Write chimeric sequences if requested
                if params.chimeric_output:
                    SeqIO.write(chimeric, params.chimeric_output, format_str)
                
                # Generate report if requested
                if params.report:
                    generate_chimera_report(results, str(params.report))
                    
            except Exception as e:
                raise ProcessingError(f"Failed to write output files: {str(e)}")
        
        # Display results summary
        total_sequences = len(sequences)
        chimeric_count = len(chimeric)
        non_chimeric_count = len(non_chimeric)
        chimeric_percentage = (chimeric_count / total_sequences * 100) if total_sequences > 0 else 0
        
        result_details = {
            "Total sequences": str(total_sequences),
            "Chimeric sequences": f"{chimeric_count} ({chimeric_percentage:.1f}%)",
            "Non-chimeric sequences": str(non_chimeric_count),
            "Output file": str(params.output_file)
        }
        
        if params.chimeric_output:
            result_details["Chimeric output"] = str(params.chimeric_output)
        
        if params.report:
            result_details["Report"] = str(params.report)
        
        handler.print_success("Chimera detection completed", result_details)
        
        return 0
        
    except Exception as e:
        handler.handle_error(e, "Chimera detection failed", show_traceback=verbose)
        return 1


@chimera_cli.command(name="run")
@click.option(
    "--input", "-i", 
    "input_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path),
    required=True,
    help="Input FASTA/FASTQ file"
)
@click.option(
    "--output", "-o", 
    "output_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    required=True,
    help="Output file for non-chimeric sequences"
)
@click.option(
    "--method", 
    type=click.Choice(['reference', 'denovo', 'both']), 
    default='denovo',
    show_default=True,
    help="Chimera detection method"
)
@click.option(
    "--ref-db", 
    "ref_db_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path),
    help="Reference database for reference-based detection"
)
@click.option(
    "--threshold", 
    default=0.8, 
    type=float,
    show_default=True,
    help="Score threshold for chimera calling (0.0-1.0)"
)
@apply_standard_options
def run_chimera_detection(
    input_path: Path,
    output_path: Path,
    method: str,
    ref_db_path: Optional[Path],
    threshold: float,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Quick chimera detection with default settings.
    
    This is a simplified interface for common chimera detection tasks.
    For advanced options, use 'ionspid chimera detect'.
    """
    # Initialize CLI handler
    handler = create_cli_handler("chimera.run", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare CLI arguments
        cli_args = {
            "input_file": input_path,
            "output_file": output_path,
            "method": method,
            "ref_db": ref_db_path,
            "threshold": threshold,
            "verbose": verbose
        }
        
        # Load and validate parameters
        params = handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=ChimeraQuickParams,
            config_path=config,
            env_prefix="IONSPID_CHIMERA_"
        )
        
        # Convert to full parameters and run detection
        full_params = params.to_full_params()
        
        # Display configuration if verbose
        if verbose and not quiet:
            handler.print_info("Quick Chimera Detection Configuration", {
                "Input file": str(full_params.input_file),
                "Output file": str(full_params.output_file),
                "Method": full_params.method,
                "Threshold": str(full_params.score_threshold)
            })
        
        # Load sequences
        with handler.create_progress_context("Loading sequences..."):
            try:
                # Detect file format
                file_format = detect_format(full_params.input_file)
                if not is_supported_format(file_format, [FileFormat.FASTA, FileFormat.FASTQ]):
                    raise InputError(f"Unsupported file format: {file_format}")
                
                # Load sequences
                format_str = "fasta" if file_format == FileFormat.FASTA else "fastq"
                sequences = list(SeqIO.parse(full_params.input_file, format_str))
                
                if not sequences:
                    raise InputError("No sequences found in input file")
                    
            except Exception as e:
                raise InputError(f"Failed to load sequences: {str(e)}")
        
        if not quiet:
            handler.print_success(f"Loaded {len(sequences)} sequences")
        
        # Run chimera detection with simplified logic
        with handler.create_progress_context(f"Running {full_params.method} chimera detection..."):
            try:
                if full_params.method == 'denovo':
                    results = detect_chimeras_denovo(
                        sequences, 
                        threshold=full_params.score_threshold,
                        vsearch_path=full_params.vsearch_path
                    )
                elif full_params.method == 'reference':
                    results = detect_chimeras_reference(
                        sequences,
                        reference_db=str(full_params.ref_db),
                        threshold=full_params.score_threshold,
                        vsearch_path=full_params.vsearch_path
                    )
                else:  # both
                    # Simplified version for quick run
                    results = detect_chimeras_denovo(
                        sequences, 
                        threshold=full_params.score_threshold,
                        vsearch_path=full_params.vsearch_path
                    )
                        
            except Exception as e:
                raise ProcessingError(f"Chimera detection failed: {str(e)}")
        
        # Filter sequences
        with handler.create_progress_context("Filtering sequences..."):
            try:
                non_chimeric, chimeric = filter_sequences(
                    sequences, results, full_params.score_threshold
                )
            except Exception as e:
                raise ProcessingError(f"Sequence filtering failed: {str(e)}")
        
        # Write output
        with handler.create_progress_context("Writing output..."):
            try:
                SeqIO.write(non_chimeric, full_params.output_file, format_str)
            except Exception as e:
                raise ProcessingError(f"Failed to write output file: {str(e)}")
        
        # Display results summary
        total_sequences = len(sequences)
        chimeric_count = len(chimeric)
        non_chimeric_count = len(non_chimeric)
        chimeric_percentage = (chimeric_count / total_sequences * 100) if total_sequences > 0 else 0
        
        result_details = {
            "Total sequences": str(total_sequences),
            "Chimeric sequences": f"{chimeric_count} ({chimeric_percentage:.1f}%)",
            "Non-chimeric sequences": str(non_chimeric_count),
            "Output file": str(full_params.output_file)
        }
        
        handler.print_success("Quick chimera detection completed", result_details)
        
        return 0
        
    except Exception as e:
        handler.handle_error(e, "Quick chimera detection failed", show_traceback=verbose)
        return 1

