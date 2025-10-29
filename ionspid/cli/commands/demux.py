"""
Demultiplexing and adapter trimming commands for the iONspID CLI.

This module provides commands for demultiplexing and adapter trimming of Oxford Nanopore sequencing data.
"""

from pathlib import Path
from typing import Optional, List

import click

from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.core.demux import (
    DoradoBarcodeKit,
    demultiplex_with_dorado,
    trim_adapters,
    register_barcode_set,
    list_barcode_sets,
    list_standard_kits,
    get_barcode_set,
    is_standard_kit
)
from ionspid.core.demux.params import (
    DemuxRunParams,
    TrimAdaptersParams,
    RegisterBarcodeParams
)


@click.group(name="demux")
def demux_cli():
    """Commands for demultiplexing and adapter trimming."""
    pass


@demux_cli.command(name="list-kits")
@apply_standard_options
@click.pass_context
def list_kits(
    ctx,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """List available barcode kits."""
    # Create CLI handler
    cli_handler = create_cli_handler("demux.list-kits", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        cli_handler.info("Available Barcode Kits:")
        
        # Create table for standard kits
        standard_table = cli_handler.create_table("Standard ONT Barcode Kits", [])
        standard_table.add_column("Kit ID", style="cyan")
        standard_table.add_column("Description", style="green")
        standard_table.add_column("Required at both ends", style="yellow")
        
        for kit_id in list_standard_kits():
            kit = get_barcode_set(kit_id)
            if kit:
                standard_table.add_row(
                    kit_id,
                    kit.get('description', 'Oxford Nanopore barcode kit'),
                    "Yes" if kit.get('require_both_ends', False) else "No"
                )
        
        cli_handler.print_table(standard_table)
        
        # Create table for custom kits
        custom_sets = list_barcode_sets()
        if custom_sets:
            custom_table = cli_handler.create_table("Custom Barcode Sets", [])
            custom_table.add_column("Name", style="cyan")
            custom_table.add_column("Description", style="green")
            custom_table.add_column("Barcodes", style="yellow", justify="right")
            custom_table.add_column("Required at both ends", style="yellow")
            
            for name, details in custom_sets.items():
                if not is_standard_kit(name):
                    custom_table.add_row(
                        name,
                        details.get('description', 'Custom barcode set'),
                        str(len(details.get('sequences', {}))),
                        "Yes" if details.get('require_both_ends', False) else "No"
                    )
            
            cli_handler.print_table(custom_table)
        else:
            cli_handler.warning("No custom barcode sets registered.")
            
    except Exception as e:
        cli_handler.handle_error(e, "Failed to list barcode kits")


@demux_cli.command(name="run")
@click.argument(
    "input_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True),
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, resolve_path=True),
    required=True,
    help="Output directory for demultiplexed files",
)
@click.option(
    "--kit",
    "-k",
    type=str,
    required=True,
    help="Barcode kit name (e.g., 'SQK-RBK004')",
)
@click.option(
    "--min-score",
    "-s",
    type=int,
    default=60,
    help="Minimum score for barcode detection (0-100)",
)
@click.option(
    "--require-both-ends/--any-end",
    default=False,
    help="Require barcodes at both ends of read",
)
@click.option(
    "--trim/--no-trim",
    default=True,
    help="Trim barcodes from reads",
)
@click.option(
    "--threads",
    "-t",
    type=int,
    help="Number of CPU threads to use",
)
@apply_standard_options
@click.pass_context
def run_demux(
    ctx, 
    input_file: str, 
    output_dir: str, 
    kit: str, 
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False,
    **kwargs
):
    """
    Demultiplex FASTQ files using barcodes.
    
    INPUT_FILE is the path to the FASTQ file to demultiplex.
    
    Examples:
        ionspid demux run input.fastq -o output_dir -k SQK-RBK004
        ionspid demux run input.fastq -o output_dir -k SQK-RBK004 --min-score 80 --require-both-ends
    """
    # Create CLI handler
    cli_handler = create_cli_handler("demux.run", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare parameters
        cli_args = {
            "input_file": Path(input_file),
            "output_dir": Path(output_dir),
            "barcode_kit": kit,
            **kwargs
        }
        
        # Load and validate parameters
        params = cli_handler.load_params(DemuxRunParams, ctx, cli_args)
        
        # Create output directory if it doesn't exist
        params.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Display configuration
        cli_handler.info("Demultiplexing Configuration:")
        cli_handler.print(f"Input: {params.input_file}")
        cli_handler.print(f"Output directory: {params.output_dir}")
        cli_handler.print(f"Barcode kit: {params.barcode_kit}")
        cli_handler.print(f"Minimum score: {params.min_score}")
        cli_handler.print(f"Require barcodes at both ends: {'Yes' if params.require_barcodes_both_ends else 'No'}")
        cli_handler.print(f"Trim barcodes: {'Yes' if params.barcode_trim else 'No'}")
        
        # Convert to core parameters
        dorado_params = params.to_dorado_demux_params()
        
        with cli_handler.status("Demultiplexing reads..."):
            result = demultiplex_with_dorado(
                input_file=dorado_params.input_file,
                output_dir=dorado_params.output_dir,
                barcode_kit=dorado_params.barcode_kit,
                min_score=dorado_params.min_score,
                require_barcodes_both_ends=dorado_params.require_barcodes_both_ends,
                barcode_trim=dorado_params.barcode_trim,
                threads=dorado_params.threads
            )
            
        cli_handler.success("✓ Demultiplexing completed successfully!")
        cli_handler.print(f"Total reads processed: {result.total_reads:,}")
        cli_handler.print(f"Assignment rate: {result.assignment_rate:.1f}%")
        cli_handler.print(f"Unassigned reads: {result.unassigned_reads:,}")
        
        # Create table for barcode statistics
        barcode_table = cli_handler.create_table("Barcode Statistics", [])
        barcode_table.add_column("Barcode", style="cyan")
        barcode_table.add_column("Reads", style="green", justify="right")
        barcode_table.add_column("Percentage", style="yellow", justify="right")
        
        # Add rows for each barcode
        for barcode, count in sorted(result.assigned_reads.items(), key=lambda x: x[0]):
            percentage = count / result.total_reads * 100 if result.total_reads > 0 else 0
            barcode_table.add_row(
                barcode,
                f"{count:,}",
                f"{percentage:.1f}%"
            )
        
        # Add row for unassigned reads
        percentage = result.unassigned_reads / result.total_reads * 100 if result.total_reads > 0 else 0
        barcode_table.add_row(
            "Unassigned",
            f"{result.unassigned_reads:,}",
            f"{percentage:.1f}%"
        )
        
        cli_handler.print_table(barcode_table)
        
        # Print output files
        cli_handler.info("\nOutput files:")
        for barcode, path in result.output_files.items():
            cli_handler.success(f"{barcode}: {path}")
        
        if result.unassigned_file:
            cli_handler.warning(f"Unassigned: {result.unassigned_file}")
        
        if result.summary_file:
            cli_handler.info(f"Summary: {result.summary_file}")
            
    except Exception as e:
        cli_handler.handle_error(e, "Demultiplexing failed")


@demux_cli.command(name="trim")
@click.argument(
    "input_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True),
)
@click.option(
    "--output-file",
    "-o",
    type=click.Path(dir_okay=False, resolve_path=True),
    required=True,
    help="Output FASTQ file with trimmed adapters",
)
@click.option(
    "--adapter",
    "-a",
    type=str,
    required=True,
    multiple=True,
    help="Adapter sequence to trim (can be used multiple times)",
)
@click.option(
    "--min-length",
    "-m",
    type=int,
    default=100,
    help="Minimum read length after trimming",
)
@click.option(
    "--error-rate",
    "-e",
    type=float,
    default=0.1,
    help="Maximum allowed error rate for adapter matching",
)
@click.option(
    "--quality-cutoff",
    "-q",
    type=int,
    help="Quality threshold for trimming low-quality ends",
)
@click.option(
    "--threads",
    "-t",
    type=int,
    default=1,
    help="Number of CPU threads to use",
)
@apply_standard_options
@click.pass_context
def run_trim(
    ctx, 
    input_file: str, 
    output_file: str, 
    adapter: List[str], 
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False,
    **kwargs
):
    """
    Trim adapter sequences from FASTQ files.
    
    INPUT_FILE is the path to the FASTQ file to trim.
    
    Examples:
        ionspid demux trim input.fastq -o output.fastq -a AGATCGGAAGAGC
        ionspid demux trim input.fastq -o output.fastq -a ADAPTER1 -a ADAPTER2 --min-length 50
    """
    # Create CLI handler
    cli_handler = create_cli_handler("demux.trim", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare parameters
        cli_args = {
            "input_file": Path(input_file),
            "output_file": Path(output_file),
            "adapters": list(adapter),
            **kwargs
        }
        
        # Load and validate parameters
        params = cli_handler.load_params(TrimAdaptersParams, ctx, cli_args)
        
        # Create output directory if it doesn't exist
        params.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Display configuration
        cli_handler.info("Adapter Trimming Configuration:")
        cli_handler.print(f"Input: {params.input_file}")
        cli_handler.print(f"Output: {params.output_file}")
        cli_handler.print(f"Adapters: {', '.join(params.adapters)}")
        cli_handler.print(f"Minimum length: {params.minimum_length}")
        cli_handler.print(f"Error rate: {params.error_rate}")
        if params.quality_cutoff:
            cli_handler.print(f"Quality cutoff: {params.quality_cutoff}")
        cli_handler.print(f"Threads: {params.threads}")
        
        # Convert to core parameters
        cutadapt_params = params.to_cutadapt_params()
        
        with cli_handler.status("Trimming adapters..."):
            summary = trim_adapters(
                input_file=cutadapt_params.input_file,
                output_file=cutadapt_params.output_file,
                adapters=cutadapt_params.adapters,
                minimum_length=cutadapt_params.minimum_length,
                error_rate=cutadapt_params.error_rate,
                quality_cutoff=cutadapt_params.quality_cutoff,
                threads=cutadapt_params.threads
            )
            
        cli_handler.success("✓ Adapter trimming completed successfully!")
        cli_handler.print(f"Total reads processed: {summary['total_reads']:,}")
        cli_handler.print(f"Reads with adapters: {summary['reads_with_adapters']:,} " +
                      f"({summary['reads_with_adapters'] / summary['total_reads'] * 100:.1f}% of total)")
        cli_handler.print(f"Reads too short after trimming: {summary['reads_too_short']:,} " +
                      f"({summary['reads_too_short'] / summary['total_reads'] * 100:.1f}% of total)")
        cli_handler.print(f"Reads written: {summary['reads_written']:,} " +
                      f"({summary['reads_written'] / summary['total_reads'] * 100:.1f}% of total)")
        cli_handler.print(f"Base pairs processed: {summary['bp_processed']:,}")
        cli_handler.print(f"Base pairs trimmed: {summary['bp_trimmed']:,} " +
                      f"({summary['bp_trimmed'] / summary['bp_processed'] * 100:.1f}% of total)")
        cli_handler.success(f"Output file: {params.output_file}")
        
    except Exception as e:
        cli_handler.handle_error(e, "Adapter trimming failed")


@demux_cli.command(name="register")
@click.argument(
    "name",
    type=str,
)
@click.option(
    "--fasta",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True),
    help="FASTA file containing barcode sequences",
)
@click.option(
    "--description",
    type=str,
    help="Description of the barcode set",
)
@click.option(
    "--require-both-ends/--any-end",
    default=False,
    help="Require barcodes at both ends of read",
)
@apply_standard_options
@click.pass_context
def register_barcode_set_cmd(
    ctx, 
    name: str, 
    fasta: Optional[str], 
    description: Optional[str], 
    require_both_ends: bool,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Register a custom barcode set.
    
    NAME is the name to give to the barcode set.
    
    Examples:
        ionspid demux register my_barcodes --fasta barcodes.fasta --description "Custom barcode set"
    """
    # Create CLI handler
    cli_handler = create_cli_handler("demux.register", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        if not fasta:
            cli_handler.error("FASTA file is required")
            return
        
        # Prepare parameters
        cli_args = {
            "name": name,
            "barcode_file": Path(fasta),
            "description": description
        }
        
        # Load and validate parameters
        params = cli_handler.load_params(RegisterBarcodeParams, ctx, cli_args)
        
        # Load sequences from FASTA file
        try:
            from Bio import SeqIO
            sequences = {}
            for record in SeqIO.parse(str(params.barcode_file), "fasta"):
                sequences[record.id] = str(record.seq)
        except ImportError:
            cli_handler.error("BioPython is required for FASTA file parsing. Please install with: pip install biopython")
            return
        except Exception as e:
            cli_handler.handle_error(e, f"Failed to read FASTA file: {params.barcode_file}")
            return
        
        if not sequences:
            cli_handler.error("No sequences found in FASTA file")
            return
        
        # Register barcode set
        register_barcode_set(
            name=params.name,
            sequences=sequences,
            require_both_ends=require_both_ends,
            description=params.description or f"Custom barcode set: {params.name}"
        )
        
        cli_handler.success(f"✓ Registered custom barcode set: {params.name}")
        cli_handler.print(f"Description: {params.description or f'Custom barcode set: {params.name}'}")
        cli_handler.print(f"Number of barcodes: {len(sequences)}")
        cli_handler.print(f"Require barcodes at both ends: {'Yes' if require_both_ends else 'No'}")
        
    except Exception as e:
        cli_handler.handle_error(e, f"Failed to register barcode set: {name}")
