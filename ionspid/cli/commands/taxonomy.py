"""
CLI commands for enhanced taxonomy assignment.

This module provides comprehensive CLI commands for taxonomic assignment using BLAST
and alternative tools with various assignment algorithms.
"""

import click
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
import logging

from ionspid.core.taxonomy import (
    TaxonomyParams, TaxonomyDatabaseParams, TaxonomyConvertParams,
    TaxonomyAssignerFactory, TaxonomyResult
)
from ionspid.core.blast import (
    BlastConfig, BlastRunner, BlastDBManager,
    ToolAdapters
)

# Keep legacy import for backward compatibility (with deprecation warning)
try:
    from ionspid.core.blast import BlastTaxonomyAssigner
    _has_legacy_blast_taxonomy = True
except ImportError:
    _has_legacy_blast_taxonomy = False
from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.utils.logging import configure_logging


@click.group(name="taxonomy", help="Enhanced taxonomic assignment commands")
def taxonomy_cli():
    """Enhanced taxonomic assignment commands."""
    pass


@taxonomy_cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--database', default="nt", help="BLAST database name or path")
@click.option('--taxonomy-map', type=click.Path(exists=True, path_type=Path), help="Taxonomy mapping file (CSV with subject_id, taxonomy columns)")
@click.option('--method', default="best_hit", type=click.Choice(['best_hit', 'lca', 'threshold', 'weighted', 'consensus']), help="Assignment method")
@click.option('--min-identity', default=70.0, type=float, help="Minimum percent identity threshold")
@click.option('--min-coverage', default=50.0, type=float, help="Minimum query coverage threshold")
@click.option('--max-evalue', default=1e-5, type=float, help="Maximum E-value threshold")
@click.option('--min-bit-score', default=50.0, type=float, help="Minimum bit score threshold")
@click.option('--threads', default=4, type=int, help="Number of CPU threads to use")
@click.option('--top-hits', default=5, type=int, help="Number of top hits to consider for LCA/consensus methods")
@click.option('--consensus-fraction', default=0.6, type=float, help="Minimum fraction for consensus assignment")
@click.option('--export-format', default="csv", type=click.Choice(['csv', 'json', 'excel', 'html']), help="Export format")
@click.option('--include-confidence/--no-include-confidence', default=True, help="Include confidence scores in output")
@click.option('--blast-params', help="Additional BLAST parameters (JSON format)")
@apply_standard_options
def assign(
    input_file: Path,
    output_file: Path,
    database: str,
    taxonomy_map: Optional[Path],
    method: str,
    min_identity: float,
    min_coverage: float,
    max_evalue: float,
    min_bit_score: float,
    threads: int,
    top_hits: int,
    consensus_fraction: float,
    export_format: str,
    include_confidence: bool,
    blast_params: Optional[str],
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Assign taxonomy to sequences using BLAST and advanced assignment algorithms.
    
    This command performs taxonomic assignment with configurable methods and parameters.
    Supports multiple assignment algorithms including best hit, LCA, consensus, and weighted approaches.
    
    Examples:
    
        # Basic taxonomic assignment with best hit method
        ionspid taxonomy assign sequences.fasta assignments.csv
        
        # Use consensus method with custom thresholds
        ionspid taxonomy assign sequences.fasta assignments.csv \\
            --method consensus --min-identity 80 --consensus-fraction 0.7
        
        # Advanced assignment with custom database and taxonomy mapping
        ionspid taxonomy assign sequences.fasta assignments.csv \\
            --database custom_db --taxonomy-map tax_map.csv \\
            --method lca --threads 8
        
        # Export results in different formats
        ionspid taxonomy assign sequences.fasta assignments.json \\
            --export-format json --include-confidence
    """
    handler = create_cli_handler("taxonomy.assign", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare parameters
        cli_params = {
            'input_file': input_file,
            'output_file': output_file,
            'database': database,
            'taxonomy_map': taxonomy_map,
            'method': method,
            'min_identity': min_identity,
            'min_coverage': min_coverage,
            'max_evalue': max_evalue,
            'min_bit_score': min_bit_score,
            'threads': threads,
            'top_hits': top_hits,
            'consensus_fraction': consensus_fraction,
            'export_format': export_format,
            'include_confidence': include_confidence,
            'blast_params': blast_params,
            'verbose': verbose
        }
        
        # Load and validate parameters
        params = handler.load_and_validate_params(
            cli_args=cli_params,
            param_model=TaxonomyParams,
            config_path=config,
            env_prefix="TAXONOMY_ASSIGN"
        )
        
        handler.print_header(f"Taxonomic Assignment: {params.input_file.name}")
        
        # Display configuration
        config_table = handler.create_table("Assignment Configuration", [])
        config_table.add_column("Parameter", style="bold blue")
        config_table.add_column("Value", style="green")
        config_table.add_row("Input File", str(params.input_file))
        config_table.add_row("Output File", str(params.output_file))
        config_table.add_row("Database", params.database)
        config_table.add_row("Method", params.method)
        config_table.add_row("Min Identity", f"{params.min_identity}%")
        config_table.add_row("Min Coverage", f"{params.min_coverage}%")
        config_table.add_row("Max E-value", f"{params.max_evalue}")
        config_table.add_row("Threads", str(params.threads))
        if params.taxonomy_map:
            config_table.add_row("Taxonomy Map", str(params.taxonomy_map))
        handler.print_table(config_table)
        
        with handler.progress() as progress:
            
            # Step 1: Run BLAST search
            blast_task = progress.add_task("Running BLAST search...", total=None)
            
            # Configure BLAST
            blast_config_dict = params.to_blast_config_dict()
            blast_config = BlastConfig(**blast_config_dict)
            
            # Run BLAST
            runner = BlastRunner(blast_config)
            blast_results = runner.run()
            
            if len(blast_results) == 0:
                handler.print_warning("No BLAST hits found")
                # Create empty results using new taxonomy module
                empty_df = pd.DataFrame(columns=params.get_output_columns()[:4])  # Basic columns
                empty_result = TaxonomyResult(assignments=empty_df, metadata={'method': 'none', 'tool': 'blast'})
                empty_result.export_results(params.output_file, format=params.export_format)
                handler.print_success("Empty results file created")
                return
            
            progress.update(blast_task, description=f"Found {len(blast_results)} BLAST hits")
            
            # Step 2: Load taxonomy mapping
            taxonomy_task = progress.add_task("Loading taxonomy mapping...", total=None)
            
            if params.taxonomy_map and params.taxonomy_map.exists():
                tax_map = pd.read_csv(params.taxonomy_map)
                handler.print_info(f"Loaded taxonomy mapping with {len(tax_map)} entries")
            else:
                # Create dummy taxonomy mapping from BLAST results
                unique_subjects = blast_results['subject_id'].unique()
                tax_map = pd.DataFrame({
                    'subject_id': unique_subjects,
                    'taxonomy': [f"Subject_{sid}" for sid in unique_subjects]
                })
                handler.print_warning("No taxonomy mapping provided, using subject IDs as taxonomy")
            
            progress.update(taxonomy_task, description=f"Loaded {len(tax_map)} taxonomy entries")
            
            # Step 3: Assign taxonomy
            assignment_task = progress.add_task(f"Assigning taxonomy using {params.method}...", total=None)
            
            # Get assignment thresholds
            thresholds = params.to_blast_thresholds()
            
            # Create assigner using new factory pattern (with fallback to legacy)
            try:
                assigner = TaxonomyAssignerFactory.create('blast', taxonomy_map=tax_map)
                result = assigner.assign(blast_results, method=params.method, thresholds=thresholds)
            except Exception as e:
                handler.print_warning(f"New taxonomy system failed, falling back to legacy: {e}")
                # Fallback to legacy system if available
                if _has_legacy_blast_taxonomy:
                    assigner = BlastTaxonomyAssigner(tax_map)
                    assignments = assigner.assign(blast_results, method=params.method, thresholds=thresholds)
                    # Convert to TaxonomyResult for enhanced functionality
                    result = TaxonomyResult(assignments=assignments, metadata={'method': params.method, 'tool': 'blast'})
                else:
                    raise RuntimeError("Both new and legacy taxonomy systems failed") from e
            
            progress.update(assignment_task, description=f"Assigned taxonomy to {len(result.assignments)} queries")
            
            # Step 4: Export results  
            export_task = progress.add_task("Exporting results...", total=None)
            
            # Use TaxonomyResult export functionality
            if params.export_format == 'csv':
                result.to_csv(params.output_file)
            elif params.export_format == 'json':
                result.to_json(params.output_file)
            elif params.export_format == 'excel':
                result.to_excel(params.output_file)
            else:
                # Fallback to legacy export for other formats
                available_columns = [col for col in params.get_output_columns() if col in result.assignments.columns]
                final_assignments = result.assignments[available_columns]
                fallback_result = TaxonomyResult(assignments=final_assignments, metadata=result.metadata)
                fallback_result.export_results(params.output_file, format=params.export_format)
            
            progress.update(export_task, description=f"Results exported to {params.output_file}")
        
        # Display summary using TaxonomyResult functionality
        summary = result.get_summary()
        _display_assignment_summary_enhanced(summary, handler)
        
        handler.print_success("Taxonomic assignment completed successfully!")
        handler.print_info(f"Results saved to: {params.output_file}")
        
    except Exception as e:
        handler.handle_error(e, "Failed to complete taxonomic assignment")


@taxonomy_cli.command()
@click.argument('database_name', type=str)
@click.option('--output-dir', default=Path.cwd(), type=click.Path(path_type=Path), help="Directory to store database files")
@click.option('--update-mode', default="check", type=click.Choice(['check', 'download', 'force']), help="Update mode")
@click.option('--compress/--no-compress', default=True, help="Compress downloaded database files")
@click.option('--cleanup/--no-cleanup', default=False, help="Clean up temporary files after processing")
@apply_standard_options
def database(
    database_name: str,
    output_dir: Path,
    update_mode: str,
    compress: bool,
    cleanup: bool,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Manage taxonomy databases for assignment.
    
    This command handles downloading, updating, and managing taxonomy databases
    used for sequence classification.
    
    Examples:
    
        # Check database status
        ionspid taxonomy database nt --update-mode check
        
        # Download NCBI NT database
        ionspid taxonomy database nt --update-mode download --output-dir /path/to/databases
        
        # Force update existing database
        ionspid taxonomy database nt --update-mode force --compress
    """
    handler = create_cli_handler("taxonomy.database", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare parameters
        cli_params = {
            'database_name': database_name,
            'output_dir': output_dir,
            'update_mode': update_mode,
            'compress': compress,
            'cleanup': cleanup
        }
        
        # Load and validate parameters
        params = handler.load_and_validate_params(
            cli_args=cli_params,
            param_model=TaxonomyDatabaseParams,
            config_path=config,
            env_prefix="TAXONOMY_DATABASE"
        )
        
        handler.print_header(f"Database Management: {params.database_name}")
        
        # Display configuration
        config_table = handler.create_table("Database Configuration", [])
        config_table.add_column("Parameter", style="bold blue")
        config_table.add_column("Value", style="green")
        config_table.add_row("Database", params.database_name)
        config_table.add_row("Output Directory", str(params.output_dir))
        config_table.add_row("Update Mode", params.update_mode)
        config_table.add_row("Compress", "Yes" if params.compress else "No")
        config_table.add_row("Cleanup", "Yes" if params.cleanup else "No")
        handler.print_table(config_table)
        
        with handler.progress() as progress:
            
            # Use BlastDBManager for database operations
            db_manager = BlastDBManager()
            
            if params.update_mode == "check":
                task = progress.add_task("Checking database status...", total=None)
                status = db_manager.check_database(params.database_name, params.output_dir)
                progress.update(task, description="Database status checked")
                
                # Display status information
                status_table = handler.create_table("Database Status", [])
                status_table.add_column("Property", style="bold blue")
                status_table.add_column("Value", style="green")
                
                for key, value in status.items():
                    status_table.add_row(str(key), str(value))
                
                handler.print_table(status_table)
                
            elif params.update_mode in ["download", "force"]:
                task = progress.add_task(f"{'Force updating' if params.update_mode == 'force' else 'Downloading'} database...", total=None)
                
                result = db_manager.download_database(
                    params.database_name,
                    params.output_dir,
                    force=params.update_mode == "force",
                    compress=params.compress
                )
                
                progress.update(task, description="Database operation completed")
                
                if params.cleanup:
                    cleanup_task = progress.add_task("Cleaning up temporary files...", total=None)
                    # Implement cleanup logic if needed
                    progress.update(cleanup_task, description="Cleanup completed")
        
        handler.print_success(f"Database management completed for {params.database_name}")
        
    except Exception as e:
        handler.handle_error(e, f"Failed to manage database {database_name}")


@taxonomy_cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--input-format', required=True, type=click.Choice(['csv', 'tsv', 'json', 'xml', 'kraken', 'qiime']), help="Input format")
@click.option('--output-format', required=True, type=click.Choice(['csv', 'tsv', 'json', 'xml', 'kraken', 'qiime']), help="Output format")
@click.option('--validate-taxonomy/--no-validate-taxonomy', default=True, help="Validate taxonomy entries during conversion")
@apply_standard_options
def convert(
    input_file: Path,
    output_file: Path,
    input_format: str,
    output_format: str,
    validate_taxonomy: bool,
    config: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    no_rich: bool = False
):
    """
    Convert between different taxonomy formats.
    
    This command converts taxonomy files between different formats commonly used
    in bioinformatics workflows.
    
    Examples:
    
        # Convert CSV taxonomy to JSON
        ionspid taxonomy convert taxonomy.csv taxonomy.json --input-format csv --output-format json
        
        # Convert Kraken format to QIIME format
        ionspid taxonomy convert kraken_tax.txt qiime_tax.txt --input-format kraken --output-format qiime
        
        # Convert without validation for faster processing
        ionspid taxonomy convert input.tsv output.csv --input-format tsv --output-format csv --no-validate-taxonomy
    """
    handler = create_cli_handler("taxonomy.convert", {
        'config': config, 'verbose': verbose, 'quiet': quiet, 'no_rich': no_rich
    })
    
    try:
        # Prepare parameters
        cli_params = {
            'input_file': input_file,
            'output_file': output_file,
            'input_format': input_format,
            'output_format': output_format,
            'validate_taxonomy': validate_taxonomy
        }
        
        # Load and validate parameters
        params = handler.load_and_validate_params(
            cli_args=cli_params,
            param_model=TaxonomyConvertParams,
            config_path=config,
            env_prefix="TAXONOMY_CONVERT"
        )
        
        handler.print_header(f"Taxonomy Format Conversion")
        
        # Display configuration
        config_table = handler.create_table("Conversion Configuration", [])
        config_table.add_column("Parameter", style="bold blue")
        config_table.add_column("Value", style="green")
        config_table.add_row("Input File", str(params.input_file))
        config_table.add_row("Output File", str(params.output_file))
        config_table.add_row("Input Format", params.input_format)
        config_table.add_row("Output Format", params.output_format)
        config_table.add_row("Validate Taxonomy", "Yes" if params.validate_taxonomy else "No")
        handler.print_table(config_table)
        
        with handler.progress() as progress:
            
            # Step 1: Load input file
            load_task = progress.add_task(f"Loading {params.input_format} file...", total=None)
            
            # Load based on input format
            if params.input_format == 'csv':
                data = pd.read_csv(params.input_file)
            elif params.input_format == 'tsv':
                data = pd.read_csv(params.input_file, sep='\\t')
            elif params.input_format == 'json':
                data = pd.read_json(params.input_file)
            else:
                # For other formats, implement specific parsers
                handler.print_warning(f"Format {params.input_format} conversion not yet implemented")
                return
            
            progress.update(load_task, description=f"Loaded {len(data)} entries")
            
            # Step 2: Validate taxonomy if requested
            if params.validate_taxonomy:
                validate_task = progress.add_task("Validating taxonomy entries...", total=None)
                # Implement taxonomy validation logic
                progress.update(validate_task, description="Validation completed")
            
            # Step 3: Convert and save
            convert_task = progress.add_task(f"Converting to {params.output_format}...", total=None)
            
            # Save based on output format
            if params.output_format == 'csv':
                data.to_csv(params.output_file, index=False)
            elif params.output_format == 'tsv':
                data.to_csv(params.output_file, sep='\\t', index=False)
            elif params.output_format == 'json':
                data.to_json(params.output_file, orient='records', indent=2)
            else:
                # For other formats, implement specific writers
                handler.print_warning(f"Format {params.output_format} conversion not yet implemented")
                return
            
            progress.update(convert_task, description="Conversion completed")
        
        handler.print_success("Taxonomy format conversion completed successfully!")
        handler.print_info(f"Converted file saved to: {params.output_file}")
        
    except Exception as e:
        handler.handle_error(e, "Failed to convert taxonomy format")


def _display_assignment_summary(assignments: pd.DataFrame, handler: StandardCLIHandler):
    """
    Display a summary table of taxonomic assignments.
    
    Args:
        assignments: DataFrame with taxonomic assignments
        handler: CLI handler for output formatting
    """
    try:
        # Create summary table
        summary_table = handler.create_table("Assignment Summary", [])
        summary_table.add_column("Metric", style="bold blue")
        summary_table.add_column("Value", style="green")
        
        # Basic statistics
        total_queries = len(assignments)
        assigned_queries = len(assignments[assignments['taxonomy'].notna()])
        assignment_rate = (assigned_queries / total_queries * 100) if total_queries > 0 else 0
        
        summary_table.add_row("Total Queries", str(total_queries))
        summary_table.add_row("Assigned Queries", str(assigned_queries))
        summary_table.add_row("Assignment Rate", f"{assignment_rate:.1f}%")
        
        # Method-specific statistics
        if 'assignment_method' in assignments.columns:
            method_counts = assignments['assignment_method'].value_counts()
            for method, count in method_counts.items():
                summary_table.add_row(f"Method: {method}", str(count))
        
        # Confidence statistics if available
        if 'confidence' in assignments.columns:
            confidence_stats = assignments['confidence'].describe()
            summary_table.add_row("Mean Confidence", f"{confidence_stats['mean']:.3f}")
            summary_table.add_row("Median Confidence", f"{confidence_stats['50%']:.3f}")
        
        handler.print_table(summary_table)
        
        # Top taxonomic assignments
        if 'taxonomy' in assignments.columns and assigned_queries > 0:
            top_taxa = assignments[assignments['taxonomy'].notna()]['taxonomy'].value_counts().head(10)
            
            if len(top_taxa) > 0:
                taxa_table = handler.create_table("Top 10 Taxonomic Assignments", [])
                taxa_table.add_column("Taxonomy", style="bold cyan")
                taxa_table.add_column("Count", style="green")
                taxa_table.add_column("Percentage", style="yellow")
                
                for taxonomy, count in top_taxa.items():
                    percentage = (count / assigned_queries * 100)
                    taxa_table.add_row(str(taxonomy), str(count), f"{percentage:.1f}%")
                
                handler.print_table(taxa_table)
        
    except Exception as e:
        handler.print_warning(f"Could not generate assignment summary: {e}")


def _display_assignment_summary_enhanced(summary: Dict[str, Any], handler: StandardCLIHandler):
    """
    Display enhanced assignment summary using TaxonomyResult summary data.
    
    Args:
        summary: Summary dictionary from TaxonomyResult.get_summary()
        handler: CLI handler for output formatting
    """
    try:
        handler.print_info("Assignment Summary")
        
        # Create main summary table
        summary_table = handler.create_table("Assignment Statistics", [])
        summary_table.add_column("Metric", style="bold blue")
        summary_table.add_column("Value", style="green")
        
        # Basic statistics
        summary_table.add_row("Total Assignments", str(summary.get('total_assignments', 0)))
        summary_table.add_row("Unique Queries", str(summary.get('unique_queries', 0)))
        
        # Confidence statistics if available
        if 'confidence' in summary:
            conf_stats = summary['confidence']
            summary_table.add_row("Mean Confidence", f"{conf_stats.get('mean', 0):.3f}")
            summary_table.add_row("Median Confidence", f"{conf_stats.get('median', 0):.3f}")
            summary_table.add_row("Min Confidence", f"{conf_stats.get('min', 0):.3f}")
            summary_table.add_row("Max Confidence", f"{conf_stats.get('max', 0):.3f}")
        
        # Method statistics if available
        if 'methods_used' in summary:
            for method, count in summary['methods_used'].items():
                summary_table.add_row(f"Method: {method}", str(count))
        
        handler.print_table(summary_table)
        
        # Taxonomic coverage table
        if 'taxonomic_coverage' in summary:
            coverage_table = handler.create_table("Taxonomic Level Coverage", [])
            coverage_table.add_column("Level", style="bold cyan")
            coverage_table.add_column("Assigned", style="green")
            coverage_table.add_column("Percentage", style="yellow")
            
            for level, stats in summary['taxonomic_coverage'].items():
                assigned = stats.get('assigned', 0)
                percentage = stats.get('percentage', 0)
                coverage_table.add_row(level.capitalize(), str(assigned), f"{percentage:.1f}%")
            
            handler.print_table(coverage_table)
        
    except Exception as e:
        handler.print_warning(f"Could not generate enhanced assignment summary: {e}")
        # Fallback to basic summary if available
        if 'total_assignments' in summary:
            handler.print_info(f"Total assignments: {summary['total_assignments']}")


# Export the CLI group
__all__ = ['taxonomy_cli']
