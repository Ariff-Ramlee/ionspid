"""
Command-line interface for sequence trimming.

This module provides command-line commands for trimming DNA sequences based on
quality criteria and primer detection using the standardized CLI interface.
"""

from pathlib import Path
from typing import List, Optional

import click

from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.core.trimming import (
    TrimmingResult, TrimmerBase, TrimmerType,
    QualityTrimmer, QualityAlgorithm, PrimerTrimmer, PrimerConfig,
    AdapterTrimmer, HomopolymerTrimmer,
    SequenceTrimmer, TrimmingConfig
)
from ionspid.core.trimming.params import (
    QualityTrimParams,
    PrimerTrimParams,
    TrimSequencesParams
)


@click.group(name="trim", help="Trim sequences based on quality and primers")
def trim_cli():
    """Trim sequences based on quality and primer detection."""
    pass


@trim_cli.command(name="quality", help="Trim sequences based on quality scores")
@click.option(
    "--input", "-i", 
    "input_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    required=True,
    help="Input FASTQ file"
)
@click.option(
    "--output", "-o", 
    "output_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    required=True,
    help="Output FASTQ file with trimmed reads"
)
@click.option(
    "--discarded", "-d",
    "discarded_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    help="Output file for discarded reads"
)
@click.option(
    "--report", "-r",
    "report_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    help="Output HTML report file"
)
@click.option(
    "--format",
    "file_format",
    type=click.Choice(["fastq"]),
    default="fastq",
    help="Input/output file format (default: fastq)"
)
@click.option(
    "--threshold", "-q",
    type=int,
    default=10,
    help="Quality score threshold"
)
@click.option(
    "--algorithm",
    type=click.Choice([a.value for a in QualityAlgorithm]),
    default=QualityAlgorithm.SLIDING_WINDOW.value,
    help="Quality trimming algorithm"
)
@click.option(
    "--window-size", "-w",
    type=int,
    default=4,
    help="Size of sliding window for quality calculation"
)
@click.option(
    "--min-length", "-l",
    type=int,
    default=0,
    help="Minimum sequence length to keep after trimming"
)
@click.option(
    "--trim-5-end/--no-trim-5-end",
    default=False,
    help="Trim low quality bases from 5' end"
)
@click.option(
    "--trim-3-end/--no-trim-3-end",
    default=True,
    help="Trim low quality bases from 3' end"
)
@click.option(
    "--discard-untrimmed/--keep-untrimmed",
    default=False,
    help="Discard reads that were not trimmed"
)
@click.option(
    "--parallel/--no-parallel",
    default=False,
    help="Use parallel processing"
)
@click.option(
    "--threads", "-t",
    "max_workers",
    type=int,
    default=None,
    help="Number of threads for parallel processing (default: CPU count - 1)"
)
@click.option(
    "--chunk-size", "-c",
    type=int,
    default=1000,
    help="Chunk size for parallel processing (default: 1000)"
)
@apply_standard_options
@click.pass_context
def trim_quality(
    ctx, 
    input_path: str, 
    output_path: str, 
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False,
    **kwargs
):
    """
    Trim sequences based on quality scores.
    
    This command trims low-quality bases from sequence ends based on quality scores
    in FASTQ files.
    
    Examples:
        ionspid trim quality -i input.fastq -o output.fastq --threshold 15
        ionspid trim quality -i input.fastq -o output.fastq --algorithm simple --min-length 100
        ionspid trim quality -i input.fastq -o output.fastq --parallel --threads 4
    """
    # Create CLI handler
    cli_handler = create_cli_handler("trim.quality", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare parameters
        cli_args = {
            "input_path": Path(input_path),
            "output_path": Path(output_path),
            **kwargs
        }
        
        # Load and validate parameters
        params = cli_handler.load_params(QualityTrimParams, ctx, cli_args)
        
        # Display configuration
        cli_handler.info("Quality Trimming Configuration:")
        cli_handler.print(f"Input: {params.input_path}")
        cli_handler.print(f"Output: {params.output_path}")
        cli_handler.print(f"Quality threshold: {params.threshold}")
        cli_handler.print(f"Algorithm: {params.algorithm.value}")
        if params.algorithm == QualityAlgorithm.SLIDING_WINDOW:
            cli_handler.print(f"Window size: {params.window_size}")
        cli_handler.print(f"Trim 5' end: {'Yes' if params.trim_5_end else 'No'}")
        cli_handler.print(f"Trim 3' end: {'Yes' if params.trim_3_end else 'No'}")
        if params.min_length > 0:
            cli_handler.print(f"Minimum length: {params.min_length}")
        if params.parallel:
            cli_handler.print(f"Parallel processing: {params.max_workers or 'auto'} workers")
        
        # Create quality trimmer
        trimmer = QualityTrimmer(
            threshold=params.threshold,
            algorithm=params.algorithm,
            window_size=params.window_size,
            min_length=params.min_length,
            trim_5_end=params.trim_5_end,
            trim_3_end=params.trim_3_end,
            discard_untrimmed=params.discard_untrimmed
        )
        
        # Create sequence trimmer
        sequence_trimmer = SequenceTrimmer([trimmer])
        
        # Create configuration
        config = TrimmingConfig(
            input_path=params.input_path,
            output_path=params.output_path,
            discarded_path=params.discarded_path,
            report_path=params.report_path,
            file_format=params.file_format,
            parallel=params.parallel,
            max_workers=params.max_workers,
            chunk_size=params.chunk_size
        )
        
        # Run trimming with progress indication
        with cli_handler.status("Trimming sequences based on quality..."):
            result = sequence_trimmer.trim_file(config)
        
        # Report results
        cli_handler.success("✓ Quality trimming completed successfully!")
        cli_handler.print(f"Total reads: {result.total_reads:,}")
        cli_handler.print(f"Trimmed reads: {result.trimmed_reads:,} ({result.trimming_rate:.2f}%)")
        cli_handler.print(f"Discarded reads: {result.discarded_reads:,} ({result.discard_rate:.2f}%)")
        cli_handler.print(f"Bases trimmed: {result.bases_trimmed:,} ({result.bases_trimmed_percent:.2f}%)")
        cli_handler.success(f"Output file: {result.output_file}")
        
        if result.discarded_file:
            cli_handler.warning(f"Discarded reads file: {result.discarded_file}")
        
        if result.summary_file:
            cli_handler.info(f"Report file: {result.summary_file}")
        
    except Exception as e:
        cli_handler.handle_error(e, "Quality trimming failed")


@trim_cli.command(name="primer", help="Trim primers from sequences")
@click.option(
    "--input", "-i", 
    "input_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    required=True,
    help="Input FASTQ/FASTA file"
)
@click.option(
    "--output", "-o", 
    "output_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    required=True,
    help="Output FASTQ/FASTA file with trimmed reads"
)
@click.option(
    "--discarded", "-d",
    "discarded_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    help="Output file for discarded reads"
)
@click.option(
    "--report", "-r",
    "report_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    help="Output HTML report file"
)
@click.option(
    "--format",
    "file_format",
    type=click.Choice(["fastq", "fasta"]),
    default="fastq",
    help="Input/output file format (default: fastq)"
)
@click.option(
    "--forward-primer", "-f",
    "forward_primers",
    multiple=True,
    help="Forward primer sequence(s)"
)
@click.option(
    "--reverse-primer", "-v",
    "reverse_primers",
    multiple=True,
    help="Reverse primer sequence(s)"
)
@click.option(
    "--primer-file",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    help="FASTA file with primer sequences"
)
@click.option(
    "--primer-name",
    default="custom",
    help="Name for the primer set"
)
@click.option(
    "--min-score",
    type=int,
    default=15,
    help="Minimum alignment score for primer detection"
)
@click.option(
    "--max-error-rate",
    type=float,
    default=0.1,
    help="Maximum error rate allowed in primer matches (0.0-1.0)"
)
@click.option(
    "--search-window",
    type=int,
    default=100,
    help="Number of bases to search from each end"
)
@click.option(
    "--check-rc/--no-check-rc",
    "check_reverse_complement",
    default=True,
    help="Also search for reverse complement of primers"
)
@click.option(
    "--both-ends-required/--either-end",
    "both_ends_required",
    default=False,
    help="Require primers at both ends (forward and reverse)"
)
@click.option(
    "--min-length", "-l",
    type=int,
    default=0,
    help="Minimum sequence length to keep after trimming"
)
@click.option(
    "--discard-untrimmed/--keep-untrimmed",
    default=False,
    help="Discard reads where no primers were found"
)
@click.option(
    "--parallel/--no-parallel",
    default=False,
    help="Use parallel processing"
)
@click.option(
    "--threads", "-t",
    "max_workers",
    type=int,
    default=None,
    help="Number of threads for parallel processing (default: CPU count - 1)"
)
@click.option(
    "--chunk-size", "-c",
    type=int,
    default=1000,
    help="Chunk size for parallel processing (default: 1000)"
)
@apply_standard_options
@click.pass_context
def trim_primer(
    ctx, 
    input_path: str, 
    output_path: str, 
    forward_primers: List[str], 
    reverse_primers: List[str], 
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False,
    **kwargs
):
    """
    Trim primer sequences from reads.
    
    This command detects and trims primer sequences from the ends of reads.
    Primers can be specified directly or loaded from a FASTA file.
    
    Examples:
        ionspid trim primer -i input.fastq -o output.fastq -f ATGCGATCG -v CGATCGATC
        ionspid trim primer -i input.fastq -o output.fastq --primer-file primers.fasta
        ionspid trim primer -i input.fastq -o output.fastq -f PRIMER1 --both-ends-required
    """
    # Create CLI handler
    cli_handler = create_cli_handler("trim.primer", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare parameters
        cli_args = {
            "input_path": Path(input_path),
            "output_path": Path(output_path),
            "forward_primers": list(forward_primers),
            "reverse_primers": list(reverse_primers),
            **kwargs
        }
        
        # Load and validate parameters
        params = cli_handler.load_params(PrimerTrimParams, ctx, cli_args)
        
        # Handle primer file if provided
        all_forward = list(params.forward_primers)
        all_reverse = list(params.reverse_primers)
        
        if params.primer_file:
            try:
                from Bio import SeqIO
                for record in SeqIO.parse(str(params.primer_file), "fasta"):
                    seq_str = str(record.seq).upper()
                    if "forward" in record.id.lower() or "fwd" in record.id.lower():
                        all_forward.append(seq_str)
                    elif "reverse" in record.id.lower() or "rev" in record.id.lower():
                        all_reverse.append(seq_str)
                    else:
                        # Assume forward if not specified
                        all_forward.append(seq_str)
            except ImportError:
                cli_handler.error("BioPython is required for FASTA file parsing. Please install with: pip install biopython")
                return
            except Exception as e:
                cli_handler.handle_error(e, f"Failed to read primer file: {params.primer_file}")
                return
        
        if not all_forward and not all_reverse:
            cli_handler.error("No primer sequences provided. Use --forward-primer, --reverse-primer, or --primer-file")
            return
        
        # Display configuration
        cli_handler.info("Primer Trimming Configuration:")
        cli_handler.print(f"Input: {params.input_path}")
        cli_handler.print(f"Output: {params.output_path}")
        cli_handler.print(f"Forward primers: {len(all_forward)}")
        cli_handler.print(f"Reverse primers: {len(all_reverse)}")
        cli_handler.print(f"Minimum score: {params.min_score}")
        cli_handler.print(f"Max error rate: {params.max_error_rate}")
        cli_handler.print(f"Search window: {params.search_window}")
        cli_handler.print(f"Check reverse complement: {'Yes' if params.check_reverse_complement else 'No'}")
        cli_handler.print(f"Both ends required: {'Yes' if params.both_ends_required else 'No'}")
        if params.min_length > 0:
            cli_handler.print(f"Minimum length: {params.min_length}")
        
        # Update parameters with loaded primers for conversion
        updated_params = params.model_copy()
        updated_params.forward_primers = all_forward
        updated_params.reverse_primers = all_reverse
        
        # Create primer configuration using parameter model conversion
        primer_config = updated_params.to_primer_config()
        
        # Create primer trimmer
        trimmer = PrimerTrimmer(
            primers=primer_config,
            min_length=params.min_length,
            discard_untrimmed=params.discard_untrimmed
        )
        
        # Create sequence trimmer
        sequence_trimmer = SequenceTrimmer([trimmer])
        
        # Create configuration
        config = TrimmingConfig(
            input_path=params.input_path,
            output_path=params.output_path,
            discarded_path=params.discarded_path,
            report_path=params.report_path,
            file_format=params.file_format,
            parallel=params.parallel,
            max_workers=params.max_workers,
            chunk_size=params.chunk_size
        )
        
        # Run trimming with progress indication
        with cli_handler.status("Trimming sequences based on primers..."):
            result = sequence_trimmer.trim_file(config)
        
        # Report results
        cli_handler.success("✓ Primer trimming completed successfully!")
        cli_handler.print(f"Total reads: {result.total_reads:,}")
        cli_handler.print(f"Trimmed reads: {result.trimmed_reads:,} ({result.trimming_rate:.2f}%)")
        cli_handler.print(f"Discarded reads: {result.discarded_reads:,} ({result.discard_rate:.2f}%)")
        cli_handler.print(f"Bases trimmed: {result.bases_trimmed:,} ({result.bases_trimmed_percent:.2f}%)")
        cli_handler.success(f"Output file: {result.output_file}")
        
        if result.discarded_file:
            cli_handler.warning(f"Discarded reads file: {result.discarded_file}")
        
        if result.summary_file:
            cli_handler.info(f"Report file: {result.summary_file}")
        
    except Exception as e:
        cli_handler.handle_error(e, "Primer trimming failed")


@trim_cli.command(name="sequences", help="Comprehensive sequence trimming with multiple methods")
@click.option(
    "--input", "-i", 
    "input_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    required=True,
    help="Input FASTQ/FASTA file"
)
@click.option(
    "--output", "-o", 
    "output_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    required=True,
    help="Output FASTQ/FASTA file with trimmed reads"
)
@click.option(
    "--discarded", "-d",
    "discarded_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    help="Output file for discarded reads"
)
@click.option(
    "--report", "-r",
    "report_path",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    help="Output HTML report file"
)
@click.option(
    "--format",
    "file_format",
    type=click.Choice(["fastq", "fasta"]),
    default="fastq",
    help="Input/output file format (default: fastq)"
)
@click.option(
    "--enable-quality/--disable-quality",
    "enable_quality_trimming",
    default=True,
    help="Enable quality-based trimming"
)
@click.option(
    "--quality-threshold",
    type=int,
    default=20,
    help="Quality threshold for trimming"
)
@click.option(
    "--min-length",
    type=int,
    default=100,
    help="Minimum sequence length after trimming"
)
@click.option(
    "--enable-primer/--disable-primer",
    "enable_primer_trimming",
    default=False,
    help="Enable primer-based trimming"
)
@click.option(
    "--primer-sequences",
    multiple=True,
    help="Primer sequences to detect and trim"
)
@click.option(
    "--enable-adapter/--disable-adapter",
    "enable_adapter_trimming",
    default=False,
    help="Enable adapter-based trimming"
)
@click.option(
    "--adapter-sequences",
    multiple=True,
    help="Adapter sequences to detect and trim"
)
@click.option(
    "--enable-homopolymer/--disable-homopolymer",
    "enable_homopolymer_trimming",
    default=False,
    help="Enable homopolymer trimming"
)
@click.option(
    "--homopolymer-threshold",
    type=int,
    default=10,
    help="Minimum homopolymer length to trigger trimming"
)
@click.option(
    "--parallel/--no-parallel",
    default=False,
    help="Use parallel processing"
)
@click.option(
    "--threads", "-t",
    "max_workers",
    type=int,
    default=None,
    help="Number of threads for parallel processing"
)
@click.option(
    "--chunk-size",
    type=int,
    default=1000,
    help="Chunk size for parallel processing"
)
@apply_standard_options
@click.pass_context
def trim_sequences(
    ctx, 
    input_path: str, 
    output_path: str, 
    primer_sequences: List[str], 
    adapter_sequences: List[str], 
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False,
    **kwargs
):
    """
    Comprehensive sequence trimming with multiple methods.
    
    This command combines multiple trimming approaches (quality, primer, adapter, homopolymer)
    to provide comprehensive sequence trimming.
    
    Examples:
        ionspid trim sequences -i input.fastq -o output.fastq --enable-quality --quality-threshold 25
        ionspid trim sequences -i input.fastq -o output.fastq --enable-primer --primer-sequences ATGC
        ionspid trim sequences -i input.fastq -o output.fastq --enable-quality --enable-adapter
    """
    # Create CLI handler
    cli_handler = create_cli_handler("trim.sequences", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare parameters
        cli_args = {
            "input_path": Path(input_path),
            "output_path": Path(output_path),
            "primer_sequences": list(primer_sequences),
            "adapter_sequences": list(adapter_sequences),
            **kwargs
        }
        
        # Load and validate parameters
        params = cli_handler.load_params(TrimSequencesParams, ctx, cli_args)
        
        # Display configuration
        cli_handler.info("Comprehensive Trimming Configuration:")
        cli_handler.print(f"Input: {params.input_path}")
        cli_handler.print(f"Output: {params.output_path}")
        cli_handler.print(f"Quality trimming: {'Enabled' if params.enable_quality_trimming else 'Disabled'}")
        if params.enable_quality_trimming:
            cli_handler.print(f"  Quality threshold: {params.quality_threshold}")
        cli_handler.print(f"Primer trimming: {'Enabled' if params.enable_primer_trimming else 'Disabled'}")
        if params.enable_primer_trimming:
            cli_handler.print(f"  Primer sequences: {len(params.primer_sequences)}")
        cli_handler.print(f"Adapter trimming: {'Enabled' if params.enable_adapter_trimming else 'Disabled'}")
        if params.enable_adapter_trimming:
            cli_handler.print(f"  Adapter sequences: {len(params.adapter_sequences)}")
        cli_handler.print(f"Homopolymer trimming: {'Enabled' if params.enable_homopolymer_trimming else 'Disabled'}")
        if params.enable_homopolymer_trimming:
            cli_handler.print(f"  Homopolymer threshold: {params.homopolymer_threshold}")
        cli_handler.print(f"Minimum length: {params.min_length}")
        
        # Build list of trimmers
        trimmers = []
        
        if params.enable_quality_trimming:
            quality_trimmer = QualityTrimmer(
                threshold=params.quality_threshold,
                min_length=params.min_length
            )
            trimmers.append(quality_trimmer)
        
        if params.enable_primer_trimming and params.primer_sequences:
            primer_config = PrimerConfig(
                name="sequences_primers",
                forward=params.primer_sequences,
                reverse=None
            )
            primer_trimmer = PrimerTrimmer(
                primers=primer_config,
                min_length=params.min_length
            )
            trimmers.append(primer_trimmer)
        
        if params.enable_adapter_trimming and params.adapter_sequences:
            # Note: This would require AdapterConfig and AdapterTrimmer implementation
            cli_handler.warning("Adapter trimming not yet implemented in core module")
        
        if params.enable_homopolymer_trimming:
            homopolymer_trimmer = HomopolymerTrimmer(
                min_length=params.homopolymer_threshold
            )
            trimmers.append(homopolymer_trimmer)
        
        if not trimmers:
            cli_handler.error("No trimming methods enabled. Enable at least one trimming method.")
            return
        
        # Create sequence trimmer
        sequence_trimmer = SequenceTrimmer(trimmers)
        
        # Create configuration
        config = params.to_trimming_config()
        
        # Run trimming with progress indication
        with cli_handler.status("Running comprehensive sequence trimming..."):
            result = sequence_trimmer.trim_file(config)
        
        # Report results
        cli_handler.success("✓ Comprehensive trimming completed successfully!")
        cli_handler.print(f"Total reads: {result.total_reads:,}")
        cli_handler.print(f"Trimmed reads: {result.trimmed_reads:,} ({result.trimming_rate:.2f}%)")
        cli_handler.print(f"Discarded reads: {result.discarded_reads:,} ({result.discard_rate:.2f}%)")
        cli_handler.print(f"Bases trimmed: {result.bases_trimmed:,} ({result.bases_trimmed_percent:.2f}%)")
        cli_handler.success(f"Output file: {result.output_file}")
        
        if result.discarded_file:
            cli_handler.warning(f"Discarded reads file: {result.discarded_file}")
        
        if result.summary_file:
            cli_handler.info(f"Report file: {result.summary_file}")
        
    except Exception as e:
        cli_handler.handle_error(e, "Comprehensive trimming failed")
