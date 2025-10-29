"""
Data commands for iONspID CLI.

Commands for working with sequencing data files (POD5, FAST5, FASTQ, FASTA, BAM).
"""

import json
from pathlib import Path
from typing import Optional

import click

from ionspid.core.data_reader import open_sequencing_file, BAM_SUPPORT
from ionspid.utils.logging import get_logger

logger = get_logger(__name__)


@click.group(name="data")
def data_cli():
    """Commands for working with sequencing data files (POD5, FAST5, FASTQ, FASTA, BAM)."""
    pass


@data_cli.command(name="inspect")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--format", 
              type=click.Choice(['pod5', 'fast5', 'fastq', 'fasta', 'bam']),
              help="Explicit file format (auto-detected if not specified)")
@click.option("--output", 
              type=click.Path(), 
              help="Output file path for inspection report")
@click.option("--output-dir", 
              type=click.Path(), 
              help="Output directory for reports")
@click.option("--report-format", 
              type=click.Choice(['html', 'json', 'txt']), 
              default='txt',
              help="Report format")
@click.option("--show-quality", 
              is_flag=True, 
              help="Include quality metrics (if available)")
@click.option("--compressed", 
              is_flag=True, 
              help="Handle compressed files")
def inspect_data(input_file: str, 
                format: Optional[str], 
                output: Optional[str],
                output_dir: Optional[str], 
                report_format: str,
                show_quality: bool,
                compressed: bool):
    """Inspect sequencing data files of any supported format."""
    try:
        click.echo(f"🔍 Inspecting sequencing data file: {input_file}")
        
        # Auto-detect or use explicit format
        if format:
            click.echo(f"📄 Using explicit format: {format}")
        else:
            click.echo("🔍 Auto-detecting file format...")
        
        # Open the file with appropriate reader
        reader = open_sequencing_file(input_file, filetype=format)
        
        # Collect inspection data
        inspection_data = {
            'file_info': {
                'filepath': str(input_file),
                'file_type': type(reader).__name__,
                'format': format or 'auto-detected'
            },
            'inspection_results': {}
        }
        
        # Display basic information
        click.echo(f"✅ Successfully opened {type(reader).__name__}")
        inspection_data['inspection_results']['reader_type'] = type(reader).__name__
        
        # Get read count
        try:
            read_count = reader.get_read_count()
            click.echo(f"📊 Total reads: {read_count:,}")
            inspection_data['inspection_results']['read_count'] = read_count
        except Exception as e:
            click.echo(f"⚠️  Could not determine read count: {e}")
            inspection_data['inspection_results']['read_count_error'] = str(e)
        
        # Get additional information if available
        try:
            read_ids = reader.read_ids()
            if read_ids:
                click.echo(f"🆔 First read ID: {read_ids[0]}")
                inspection_data['inspection_results']['first_read_id'] = read_ids[0]
                if len(read_ids) > 1:
                    click.echo(f"🆔 Last read ID: {read_ids[-1]}")
                    inspection_data['inspection_results']['last_read_id'] = read_ids[-1]
                # Store sample of read IDs (first 10)
                inspection_data['inspection_results']['sample_read_ids'] = read_ids[:10]
        except Exception as e:
            click.echo(f"⚠️  Could not access read IDs: {e}")
            inspection_data['inspection_results']['read_ids_error'] = str(e)
        
        # Get run info if available
        try:
            if hasattr(reader, 'run_info') and reader.run_info:
                inspection_data['inspection_results']['run_info'] = reader.run_info
                # Display some key run info
                if 'sample_id' in reader.run_info and reader.run_info['sample_id'] != 'unknown':
                    click.echo(f"🏷️  Sample ID: {reader.run_info['sample_id']}")
                if 'flow_cell_id' in reader.run_info and reader.run_info['flow_cell_id'] != 'unknown':
                    click.echo(f"🧬 Flow cell ID: {reader.run_info['flow_cell_id']}")
        except Exception as e:
            inspection_data['inspection_results']['run_info_error'] = str(e)
        
        # Show quality metrics if requested and available
        if show_quality:
            try:
                # This would need to be implemented per reader type
                click.echo("📈 Quality metrics: Feature coming soon")
                inspection_data['inspection_results']['quality_metrics'] = "Feature coming soon"
            except Exception as e:
                click.echo(f"⚠️  Quality metrics not available: {e}")
                inspection_data['inspection_results']['quality_metrics_error'] = str(e)
        
        # Save output if requested
        if output:
            click.echo(f"💾 Saving inspection report to: {output}")
            try:
                import json
                from pathlib import Path
                
                output_path = Path(output)
                if output_path.suffix.lower() == '.json':
                    with open(output_path, 'w') as f:
                        json.dump(inspection_data, f, indent=2, default=str)
                else:
                    # Default to text format
                    with open(output_path, 'w') as f:
                        f.write(f"iONspID Data Inspection Report\n")
                        f.write(f"{'=' * 40}\n\n")
                        f.write(f"File: {input_file}\n")
                        f.write(f"Reader Type: {inspection_data['inspection_results'].get('reader_type', 'Unknown')}\n")
                        f.write(f"Format: {format or 'auto-detected'}\n\n")
                        
                        # Read count
                        if 'read_count' in inspection_data['inspection_results']:
                            f.write(f"Total reads: {inspection_data['inspection_results']['read_count']:,}\n")
                        elif 'read_count_error' in inspection_data['inspection_results']:
                            f.write(f"Read count error: {inspection_data['inspection_results']['read_count_error']}\n")
                        
                        # Read IDs
                        if 'first_read_id' in inspection_data['inspection_results']:
                            f.write(f"First read ID: {inspection_data['inspection_results']['first_read_id']}\n")
                        if 'last_read_id' in inspection_data['inspection_results']:
                            f.write(f"Last read ID: {inspection_data['inspection_results']['last_read_id']}\n")
                        
                        # Sample read IDs
                        if 'sample_read_ids' in inspection_data['inspection_results']:
                            f.write(f"\nSample read IDs (first 10):\n")
                            for i, read_id in enumerate(inspection_data['inspection_results']['sample_read_ids'], 1):
                                f.write(f"  {i}: {read_id}\n")
                        
                        # Run info
                        if 'run_info' in inspection_data['inspection_results']:
                            f.write(f"\nRun Information:\n")
                            run_info = inspection_data['inspection_results']['run_info']
                            for key, value in run_info.items():
                                if key != 'context_tags' and value != 'unknown':
                                    f.write(f"  {key}: {value}\n")
                            if 'context_tags' in run_info and run_info['context_tags']:
                                f.write(f"  Context tags:\n")
                                for tag, val in run_info['context_tags'].items():
                                    if val != 'unknown':
                                        f.write(f"    {tag}: {val}\n")
                        
                        # Quality metrics
                        if show_quality:
                            if 'quality_metrics' in inspection_data['inspection_results']:
                                f.write(f"\nQuality metrics: {inspection_data['inspection_results']['quality_metrics']}\n")
                
                click.echo(f"✅ Inspection report saved to: {output}")
                
            except Exception as e:
                click.echo(f"❌ Error saving inspection report: {e}", err=True)
        
        click.echo("✅ Inspection completed successfully")
        
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        click.echo("\n💡 Supported formats: POD5, FAST5, FASTQ, FASTA" + 
                  (", BAM" if BAM_SUPPORT else ""), err=True)
        raise click.Abort()
    except Exception as e:
        logger.exception("Unexpected error during file inspection")
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@data_cli.command(name="stats")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--format", 
              type=click.Choice(['pod5', 'fast5', 'fastq', 'fasta', 'bam']),
              help="Explicit file format (auto-detected if not specified)")
@click.option("--output", 
              type=click.Path(), 
              help="Output file path")
@click.option("--plot", 
              is_flag=True, 
              help="Generate plots")
@click.option("--summary-only", 
              is_flag=True, 
              help="Brief summary only")
def stats_data(input_file: str, 
               format: Optional[str], 
               output: Optional[str], 
               plot: bool,
               summary_only: bool):
    """Calculate statistics for sequencing data files of any supported format."""
    try:
        click.echo(f"📊 Calculating statistics for: {input_file}")
        
        # Auto-detect or use explicit format
        if format:
            click.echo(f"📄 Using explicit format: {format}")
        else:
            click.echo("🔍 Auto-detecting file format...")
        
        # Open the file with appropriate reader
        reader = open_sequencing_file(input_file, filetype=format)
        click.echo(f"✅ Successfully opened {type(reader).__name__}")
        
        # Calculate basic statistics
        try:
            read_count = reader.get_read_count()
            click.echo(f"📊 Total reads: {read_count:,}")
            
            # Get sequence lengths if available
            try:
                sequences = []
                read_ids = reader.read_ids()
                sample_size = min(1000, len(read_ids))  # Sample first 1000 reads
                
                click.echo(f"📏 Analyzing sequence lengths (sample of {sample_size} reads)...")
                
                for i, read_id in enumerate(read_ids[:sample_size]):
                    if i % 100 == 0:
                        click.echo(f"  Processing read {i+1}/{sample_size}...")
                    
                    try:
                        sequence = reader.get_sequence(read_id)
                        if sequence:
                            sequences.append(len(sequence))
                    except Exception:
                        continue
                
                if sequences:
                    import numpy as np
                    sequences = np.array(sequences)
                    
                    # Calculate statistics
                    stats = {
                        'read_count': read_count,
                        'sample_size': len(sequences),
                        'mean_length': float(np.mean(sequences)),
                        'median_length': float(np.median(sequences)),
                        'min_length': int(np.min(sequences)),
                        'max_length': int(np.max(sequences)),
                        'std_length': float(np.std(sequences)),
                        'total_bases': int(np.sum(sequences))
                    }
                    
                    if not summary_only:
                        stats.update({
                            'q25_length': float(np.percentile(sequences, 25)),
                            'q75_length': float(np.percentile(sequences, 75))
                        })
                    
                    # Display statistics
                    click.echo(f"📏 Sequence length statistics:")
                    click.echo(f"  Mean: {stats['mean_length']:.1f} bp")
                    click.echo(f"  Median: {stats['median_length']:.1f} bp")
                    click.echo(f"  Min: {stats['min_length']} bp")
                    click.echo(f"  Max: {stats['max_length']} bp")
                    click.echo(f"  Std: {stats['std_length']:.1f} bp")
                    
                    if not summary_only:
                        click.echo(f"  25th percentile: {stats['q25_length']:.1f} bp")
                        click.echo(f"  75th percentile: {stats['q75_length']:.1f} bp")
                        click.echo(f"  Total bases: {stats['total_bases']:,} bp")
                
            except Exception as e:
                click.echo(f"⚠️  Could not analyze sequence lengths: {e}")
        
        except Exception as e:
            click.echo(f"⚠️  Could not calculate basic statistics: {e}")
        
        # Generate plots if requested
        if plot:
            click.echo("📈 Plot generation: Feature coming soon")
        
        # Save output if requested
        if output:
            click.echo(f"💾 Saving results to: {output}")
            try:
                import json
                from pathlib import Path
                
                # Prepare output data
                output_data = {
                    'file_info': {
                        'filepath': str(input_file),
                        'file_type': type(reader).__name__,
                        'format': format or 'auto-detected'
                    },
                    'statistics': stats if 'stats' in locals() else {'read_count': read_count}
                }
                
                # Determine output format based on file extension
                output_path = Path(output)
                if output_path.suffix.lower() == '.json':
                    with open(output_path, 'w') as f:
                        json.dump(output_data, f, indent=2)
                else:
                    # Default to text format
                    with open(output_path, 'w') as f:
                        f.write(f"iONspID Data Statistics Report\n")
                        f.write(f"{'=' * 40}\n\n")
                        f.write(f"File: {input_file}\n")
                        f.write(f"Type: {type(reader).__name__}\n")
                        f.write(f"Format: {format or 'auto-detected'}\n\n")
                        
                        if 'stats' in locals():
                            f.write(f"Read Statistics:\n")
                            f.write(f"  Total reads: {stats['read_count']:,}\n")
                            f.write(f"  Sample analyzed: {stats['sample_size']:,}\n\n")
                            f.write(f"Sequence Length Statistics:\n")
                            f.write(f"  Mean: {stats['mean_length']:.1f} bp\n")
                            f.write(f"  Median: {stats['median_length']:.1f} bp\n")
                            f.write(f"  Min: {stats['min_length']} bp\n")
                            f.write(f"  Max: {stats['max_length']} bp\n")
                            f.write(f"  Std: {stats['std_length']:.1f} bp\n")
                            if not summary_only:
                                f.write(f"  25th percentile: {stats['q25_length']:.1f} bp\n")
                                f.write(f"  75th percentile: {stats['q75_length']:.1f} bp\n")
                            f.write(f"  Total bases: {stats['total_bases']:,} bp\n")
                        else:
                            f.write(f"Read count: {read_count:,}\n")
                
                click.echo(f"✅ Results saved to: {output}")
                
            except Exception as e:
                click.echo(f"❌ Error saving results: {e}", err=True)
            
        click.echo("✅ Statistics calculation completed successfully")
        
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        click.echo("\n💡 Supported formats: POD5, FAST5, FASTQ, FASTA" + 
                  (", BAM" if BAM_SUPPORT else ""), err=True)
        raise click.Abort()
    except Exception as e:
        logger.exception("Unexpected error during statistics calculation")
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@data_cli.command(name="info")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--format", 
              type=click.Choice(['pod5', 'fast5', 'fastq', 'fasta', 'bam']),
              help="Explicit file format (auto-detected if not specified)")
def info_data(input_file: str, format: Optional[str]):
    """Display basic information about sequencing data files."""
    try:
        click.echo(f"ℹ️  File information for: {input_file}")
        
        # File system information
        file_path = Path(input_file)
        file_size = file_path.stat().st_size
        click.echo(f"📁 File size: {file_size / (1024**2):.2f} MB")
        click.echo(f"📅 Modified: {file_path.stat().st_mtime}")
        
        # Auto-detect or use explicit format
        if format:
            click.echo(f"📄 Using explicit format: {format}")
        else:
            click.echo("🔍 Auto-detecting file format...")
        
        # Open the file with appropriate reader
        reader = open_sequencing_file(input_file, filetype=format)
        click.echo(f"✅ File type: {type(reader).__name__}")
        
        # Display format-specific information
        try:
            read_count = reader.get_read_count()
            click.echo(f"📊 Read count: {read_count:,}")
        except Exception as e:
            click.echo(f"⚠️  Could not determine read count: {e}")
        
        click.echo("✅ Information retrieval completed")
        
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        click.echo("\n💡 Supported formats: POD5, FAST5, FASTQ, FASTA" + 
                  (", BAM" if BAM_SUPPORT else ""), err=True)
        raise click.Abort()
    except Exception as e:
        logger.exception("Unexpected error during info retrieval")
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


# Make the CLI group available for import
__all__ = ['data_cli']
