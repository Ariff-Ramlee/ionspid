"""
Command-line interface for BLAST operations.

This module provides command-line commands for BLAST searches, database management,
result filtering, and reporting using the standardized CLI interface.
"""

import click
from pathlib import Path
import pandas as pd
import logging
from ionspid.cli.utils.standard_cli import StandardCLIHandler, apply_standard_options, create_cli_handler
from ionspid.core.blast import (
    BlastConfig, BlastRunner, BlastDBManager, BlastResultParser, 
    BlastFilter, BlastVisualizer, export_assignments
)
from ionspid.core.blast.params import (
    BlastSearchParams,
    BlastFilterParams,
    BlastDBInfoParams,
    BlastFormatDBParams,
    BlastDBManageParams,
    BlastReportParams
)

logger = logging.getLogger(__name__)


@click.group("blast", help="BLAST operations and database management")
def blast_cli():
    """BLAST command group for sequence similarity searches and database management."""
    pass


@blast_cli.command("search", help="Run BLAST search against a database")
@click.option("--input", "-i", "input_path", required=True, type=click.Path(exists=True), 
              help="Input FASTA file.")
@click.option("--db", required=True, type=str, 
              help="BLAST database name or path.")
@click.option("--output", "-o", "output_path", required=True, type=click.Path(), 
              help="Output file for BLAST results.")
@click.option("--outfmt", type=str, default="6", 
              help="BLAST output format (default: tabular).")
@click.option("--evalue", type=float, default=1e-5, 
              help="E-value threshold.")
@click.option("--max-target-seqs", type=int, default=10, 
              help="Maximum target sequences per query.")
@click.option("--num-threads", type=int, default=1, 
              help="Number of threads to use.")
@click.option("--blast-exe", type=str, default="blastn", 
              help="BLAST executable (blastn, blastp, blastx, etc.).")
@click.option("--remote", is_flag=True, 
              help="Use remote BLAST (NCBI).")
@click.option("--remote-program", type=str, default="blastn",
              help="Remote BLAST program.")
@click.option("--remote-db", type=str, default="nt",
              help="Remote BLAST database.")
@click.option("--timeout", type=int, default=600,
              help="Timeout for remote BLAST searches (seconds).")
@click.option("--retry", type=int, default=2,
              help="Number of retry attempts for failed searches.")
@click.option("--chunk-size", type=int, default=1000,
              help="Chunk size for processing large files.")
@apply_standard_options
@click.pass_context
def search(ctx, input_path: str, output_path: str, **kwargs):
    """
    Run a basic BLAST search against a database.
    
    This command provides basic BLAST functionality for sequence similarity searches.
    Results are output in tabular format by default for easy parsing.
    
    Examples:
        ionspid blast search -i sequences.fasta -o results.tsv --db nt --remote
        ionspid blast search -i queries.fasta -o hits.tsv --db mydb --evalue 1e-10
        ionspid blast search -i input.fasta -o output.tsv --db refseq --num-threads 4
    """
    # Create CLI handler
    cli_handler = create_cli_handler("blast.search", kwargs)
    
    try:
        # Prepare parameters
        cli_args = {
            "input_path": Path(input_path),
            "output_path": Path(output_path),
            **kwargs
        }
        
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=BlastSearchParams
        )
        
        # Display configuration
        config_details = {
            "Input": str(params.input_path),
            "Output": str(params.output_path),
            "Database": params.db,
            "BLAST executable": params.blast_exe,
            "E-value threshold": str(params.evalue),
            "Max target sequences": str(params.max_target_seqs)
        }
        
        if params.remote:
            config_details.update({
                "Remote search": f"{params.remote_program} against {params.remote_db}",
                "Timeout": f"{params.timeout}s"
            })
        else:
            config_details["Local threads"] = str(params.num_threads)
            
        cli_handler.print_info("BLAST Search Configuration:", config_details)
        
        # Create BLAST configuration
        config = params.to_blast_config()
        
        # Run BLAST search with progress indication
        with cli_handler.create_progress_context("Running BLAST search..."):
            runner = BlastRunner(config)
            blast_results = runner.run()
        
        # Report results
        if len(blast_results) > 0:
            results_details = {
                "Hits found": f"{len(blast_results)}",
                "Results saved to": str(params.output_path)
            }
            cli_handler.print_success("BLAST search completed successfully!", results_details)
        else:
            cli_handler.print_warning("No BLAST hits found")
            cli_handler.print_success(f"Empty results file created: {params.output_path}")
        
    except Exception as e:
        cli_handler.handle_error(e, "BLAST search failed")


@blast_cli.command("filter", help="Filter BLAST results by quality criteria")
@click.option("--input", "-i", "input_path", required=True, type=click.Path(exists=True), 
              help="Input BLAST results file (tabular format).")
@click.option("--output", "-o", "output_path", required=True, type=click.Path(), 
              help="Output file for filtered results.")
@click.option("--min-identity", type=float, default=90.0, 
              help="Minimum percent identity threshold.")
@click.option("--min-length", type=int, default=50, 
              help="Minimum alignment length.")
@click.option("--max-evalue", type=float, default=1e-5, 
              help="Maximum E-value threshold.")
@click.option("--min-bit-score", type=float, help="Minimum bit score threshold.")
@click.option("--format", type=click.Choice(["csv", "tsv"]), default="csv", 
              help="Output format.")
@click.option("--keep-best-hit/--keep-all-hits", default=False,
              help="Keep only the best hit per query")
@click.option("--remove-self-hits/--keep-self-hits", default=True,
              help="Remove self hits (query == subject)")
@apply_standard_options
@click.pass_context
def filter_results(ctx, input_path: str, output_path: str, **kwargs):
    """
    Filter BLAST results based on quality thresholds.
    
    Applies various quality filters to BLAST tabular output, including identity,
    alignment length, E-value, and bit score thresholds.
    
    Examples:
        ionspid blast filter -i raw_results.tsv -o filtered.csv --min-identity 95
        ionspid blast filter -i hits.tsv -o best_hits.csv --keep-best-hit
        ionspid blast filter -i results.tsv -o high_quality.tsv --format tsv --min-length 100
    """
    # Create CLI handler
    cli_handler = create_cli_handler("blast.filter", kwargs)
    
    try:
        # Prepare parameters
        cli_args = {
            "input_path": Path(input_path),
            "output_path": Path(output_path),
            **kwargs
        }
        
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=BlastFilterParams
        )
        
        # Display configuration
        filter_details = {
            "Input": str(params.input_path),
            "Output": str(params.output_path),
            "Min identity": f"{params.min_identity}%",
            "Min length": str(params.min_length),
            "Max E-value": str(params.max_evalue),
            "Keep best hit only": "Yes" if params.keep_best_hit else "No",
            "Remove self hits": "Yes" if params.remove_self_hits else "No"
        }
        
        if params.min_bit_score:
            filter_details["Min bit score"] = str(params.min_bit_score)
            
        cli_handler.print_info("BLAST Filter Configuration:", filter_details)
        
        # Read BLAST results
        with cli_handler.create_progress_context("Reading BLAST results..."):
            if str(params.input_path).endswith('.csv'):
                df = pd.read_csv(params.input_path)
            else:
                # Parse tabular format
                df = BlastResultParser.parse_tabular(params.input_path.read_text())
        
        initial_count = len(df)
        cli_handler.print_info(f"Loaded {initial_count} BLAST hits")
        
        # Apply filters
        with cli_handler.create_progress_context("Applying filters..."):
            filtered_df = BlastFilter.filter_hits(
                df,
                min_identity=params.min_identity,
                min_length=params.min_length,
                max_evalue=params.max_evalue,
                min_bit_score=params.min_bit_score,
                keep_best_hit=params.keep_best_hit,
                remove_self_hits=params.remove_self_hits
            )
        
        # Export filtered results
        separator = '\t' if params.format == 'tsv' else ','
        filtered_df.to_csv(params.output_path, sep=separator, index=False)
        
        # Report results
        filtered_count = len(filtered_df)
        filter_results = {
            "Input hits": f"{initial_count:,}",
            "Filtered hits": f"{filtered_count:,}",
            "Retention rate": f"{filtered_count/initial_count*100:.1f}%",
            "Results saved to": str(params.output_path)
        }
        cli_handler.print_success("Filtering completed successfully!", filter_results)
        
    except Exception as e:
        cli_handler.handle_error(e, "BLAST filtering failed")


@blast_cli.command("db-info", help="Get information about BLAST databases")
@click.option("--db-path", type=click.Path(exists=True), 
              help="Path to specific BLAST database.")
@click.option("--db-dir", type=click.Path(), 
              help="Database directory (for listing multiple databases).")
@click.option("--show-details/--summary-only", default=False,
              help="Show detailed database statistics")
@click.option("--validate-only/--full-info", default=False,
              help="Only validate database, don't show statistics")
@apply_standard_options
@click.pass_context
def db_info(ctx, **kwargs):
    """
    Display information about BLAST databases.
    
    Shows database statistics, validation status, and other metadata for
    BLAST databases in a directory or for a specific database.
    
    Examples:
        ionspid blast db-info --db-dir /data/blast_dbs
        ionspid blast db-info --db-path /data/blast_dbs/nt --show-details
        ionspid blast db-info --db-path /data/mydb --validate-only
    """
    # Create CLI handler
    cli_handler = create_cli_handler("blast.db-info", kwargs)
    
    try:
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=kwargs,
            param_model=BlastDBInfoParams
        )
        
        if not params.db_path and not params.db_dir:
            cli_handler.handle_error(Exception("Either --db-path or --db-dir must be specified"), "Missing required parameter")
            return
        
        if params.db_dir:
            # List all databases in directory
            cli_handler.print_info(f"Scanning directory: {params.db_dir}")
            
            with cli_handler.create_progress_context("Scanning for BLAST databases..."):
                manager = BlastDBManager(Path(params.db_dir))
                databases = manager.list_databases()
            
            if not databases:
                cli_handler.print_warning("No BLAST databases found in directory")
                return
            
            cli_handler.print_success(f"Found {len(databases)} BLAST database(s):")
            
            # Create table for database info
            table = cli_handler.create_table("BLAST Databases", ["Database", "Status", "Sequences", "Type"])
            
            for name, info in databases.items():
                status = "✓ Valid" if info['valid'] else "✗ Invalid"
                sequences = info['stats'].get('num_sequences', 'N/A')
                db_type = info['stats'].get('db_type', 'Unknown')
                table.add_row(name, status, str(sequences), db_type)
            
            cli_handler.print_table(table)
            
        else:
            # Single database info
            cli_handler.print_info(f"Analyzing database: {params.db_path}")
            
            with cli_handler.create_progress_context("Validating database..."):
                manager = BlastDBManager(params.db_path.parent)
                is_valid = manager.validate_db(params.db_path)
            
            status = "✓ Valid" if is_valid else "✗ Invalid"
            validation_details = {"Status": status}
            cli_handler.print_info("Database Validation:", validation_details)
            
            if not params.validate_only and is_valid:
                with cli_handler.create_progress_context("Gathering statistics..."):
                    stats = manager.db_stats(params.db_path)
                
                if stats:
                    formatted_stats = {}
                    for key, value in stats.items():
                        display_key = key.replace('_', ' ').title()
                        formatted_stats[display_key] = str(value)
                    cli_handler.print_info("Database Statistics:", formatted_stats)
                else:
                    cli_handler.print_warning("Could not retrieve database statistics")
            
    except Exception as e:
        cli_handler.handle_error(e, "Database info retrieval failed")


@blast_cli.command("format-db", help="Format FASTA file as BLAST database")
@click.option("--input", "-i", "input_path", required=True, type=click.Path(exists=True), 
              help="Input FASTA file.")
@click.option("--output-dir", type=click.Path(), 
              help="Output directory for database files (default: input file directory).")
@click.option("--dbtype", type=click.Choice(["nucl", "prot"]), default="nucl", 
              help="Database type (nucleotide or protein).")
@click.option("--out-name", type=str, 
              help="Output database name (default: input filename).")
@click.option("--parse-seqids/--no-parse-seqids", default=True, 
              help="Parse sequence IDs.")
@click.option("--hash-index/--no-hash-index", default=True, 
              help="Create hash index for faster searches.")
@click.option("--title", type=str, help="Title for the database.")
@click.option("--mask-data", type=click.Path(exists=True), 
              help="Path to masking data file.")
@apply_standard_options
@click.pass_context
def format_db(ctx, input_path: str, **kwargs):
    """
    Format a FASTA file as a BLAST database.
    
    Creates BLAST database files from a FASTA input file using makeblastdb.
    The database can then be used for local BLAST searches.
    
    Examples:
        ionspid blast format-db -i sequences.fasta --dbtype nucl
        ionspid blast format-db -i proteins.fasta --dbtype prot --out-name mydb
        ionspid blast format-db -i refs.fasta --output-dir /data/dbs --hash-index
    """
    # Create CLI handler
    cli_handler = create_cli_handler("blast.format-db", kwargs)
    
    try:
        # Prepare parameters
        cli_args = {
            "input_path": Path(input_path),
            **kwargs
        }
        
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=BlastFormatDBParams
        )
        
        # Set defaults
        if not params.output_dir:
            params.output_dir = params.input_path.parent
        if not params.out_name:
            params.out_name = params.input_path.stem
        
        # Display configuration
        format_details = {
            "Input FASTA": str(params.input_path),
            "Output directory": str(params.output_dir),
            "Database name": params.out_name,
            "Database type": params.dbtype,
            "Parse sequence IDs": "Yes" if params.parse_seqids else "No",
            "Create hash index": "Yes" if params.hash_index else "No"
        }
        if params.title:
            format_details["Database title"] = params.title
        cli_handler.print_info("Database Formatting Configuration:", format_details)
        
        # Create database manager
        manager = BlastDBManager(params.output_dir)
        
        # Format database with progress indication
        with cli_handler.create_progress_context("Formatting BLAST database..."):
            success = manager.format_db(
                params.input_path,
                dbtype=params.dbtype,
                out_name=params.out_name,
                parse_seqids=params.parse_seqids,
                hash_index=params.hash_index,
                title=params.title,
                mask_data=params.mask_data
            )
        
        if success:
            format_success_details = {
                "Database name": params.out_name,
                "Database type": params.dbtype,
                "Database files created in": str(params.output_dir)
            }
            cli_handler.print_success("Database formatting completed successfully!", format_success_details)
            
            # Validate the created database
            with cli_handler.create_progress_context("Validating created database..."):
                db_path = params.output_dir / params.out_name
                is_valid = manager.validate_db(db_path)
            
            if is_valid:
                cli_handler.print_success("Database validation passed")
            else:
                cli_handler.print_warning("Database validation failed - database may not be usable")
        else:
            cli_handler.handle_error(Exception("Database formatting failed"), "Database creation error")
            
    except Exception as e:
        cli_handler.handle_error(e, "Database formatting failed")


# Export for CLI integration
if __name__ == "__main__":
    blast_cli()


@blast_cli.command("db", help="Advanced database management operations")
@click.option("--action", type=click.Choice(["download", "format", "validate", "stats"]), required=True,
              help="Action to perform")
@click.option("--db-url", type=str, help="URL to download database from.")
@click.option("--dest", type=click.Path(), help="Destination path for download or format.")
@click.option("--fasta", type=click.Path(exists=True), help="FASTA file for formatting.")
@click.option("--dbtype", type=click.Choice(["nucl", "prot"]), default="nucl",
              help="Database type")
@click.option("--out-name", type=str, help="Output name for formatted DB.")
@click.option("--decompress/--no-decompress", default=True,
              help="Decompress downloaded files automatically")
@click.option("--validate-after-download/--no-validate", default=True,
              help="Validate database after download")
@apply_standard_options
@click.pass_context
def manage_db(ctx, **kwargs):
    """
    Advanced database management operations.
    
    Provides unified interface for downloading, formatting, validating, and
    getting statistics for BLAST databases.
    
    Examples:
        ionspid blast db --action download --db-url http://example.com/db.tar.gz --dest /data
        ionspid blast db --action format --fasta sequences.fa --dest /data --out-name mydb
        ionspid blast db --action validate --dest /data/mydb
        ionspid blast db --action stats --dest /data/mydb
    """
    # Create CLI handler
    cli_handler = create_cli_handler("blast.db", kwargs)
    
    try:
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=kwargs,
            param_model=BlastDBManageParams
        )
        
        if params.action == "download":
            if not params.db_url or not params.dest:
                cli_handler.handle_error(Exception("--db-url and --dest are required for download action"), "Missing required parameters")
                return
            
            download_details = {
                "Database URL": params.db_url,
                "Destination": str(params.dest)
            }
            cli_handler.print_info("Downloading database", download_details)
            
            with cli_handler.create_progress_context("Downloading database..."):
                BlastDBManager.download_db(params.db_url, Path(params.dest))
            
            cli_handler.print_success(f"Database downloaded to: {params.dest}")
            
            if params.validate_after_download:
                with cli_handler.create_progress_context("Validating downloaded database..."):
                    manager = BlastDBManager(Path(params.dest).parent)
                    is_valid = manager.validate_db(Path(params.dest))
                
                if is_valid:
                    cli_handler.print_success("Database validation passed")
                else:
                    cli_handler.print_warning("Database validation failed")
        
        elif params.action == "format":
            if not params.fasta:
                cli_handler.handle_error(Exception("--fasta is required for format action"), "Missing required parameter")
                return
            
            dest_path = Path(params.dest) if params.dest else Path(params.fasta).parent
            
            with cli_handler.create_progress_context("Formatting database..."):
                manager = BlastDBManager(dest_path)
                success = manager.format_db(
                    Path(params.fasta),
                    dbtype=params.dbtype,
                    out_name=params.out_name
                )
            
            if success:
                cli_handler.print_success("Database formatting completed")
            else:
                cli_handler.handle_error(Exception("Database formatting failed"), "Database creation error")
        
        elif params.action == "validate":
            if not params.dest:
                cli_handler.handle_error(Exception("--dest is required for validate action"), "Missing required parameter")
                return
            
            with cli_handler.create_progress_context("Validating database..."):
                manager = BlastDBManager(Path(params.dest).parent)
                is_valid = manager.validate_db(Path(params.dest))
            
            status = "✓ Valid" if is_valid else "✗ Invalid"
            validation_result = {"Database validation": status}
            cli_handler.print_info("Validation Result:", validation_result)
        
        elif params.action == "stats":
            if not params.dest:
                cli_handler.handle_error(Exception("--dest is required for stats action"), "Missing required parameter")
                return
            
            with cli_handler.create_progress_context("Gathering database statistics..."):
                manager = BlastDBManager(Path(params.dest).parent)
                stats = manager.db_stats(Path(params.dest))
            
            if stats:
                formatted_stats = {}
                for key, value in stats.items():
                    display_key = key.replace('_', ' ').title()
                    formatted_stats[display_key] = str(value)
                cli_handler.print_info("Database Statistics:", formatted_stats)
            else:
                cli_handler.print_warning("Could not retrieve database statistics")
        
    except Exception as e:
        cli_handler.handle_error(e, f"Database {params.action} operation failed")


@blast_cli.command("report", help="Generate BLAST assignment report and visualizations")
@click.option("--assignments", "-a", "assignments_path", required=True, type=click.Path(exists=True), 
              help="Assignments CSV file.")
@click.option("--output", "-o", "output_path", required=True, type=click.Path(), 
              help="Output report file.")
@click.option("--interactive/--static", default=False, 
              help="Generate interactive HTML report.")
@click.option("--include-tree/--no-tree", default=False, 
              help="Include taxonomic tree visualization.")
@click.option("--plot-format", type=click.Choice(["png", "svg", "pdf"]), default="png",
              help="Plot format for static images")
@click.option("--show-statistics/--no-statistics", default=True,
              help="Include summary statistics in report")
@click.option("--group-by", type=click.Choice(["taxonomy", "identity", "evalue"]), default="taxonomy",
              help="Group results by category")
@click.option("--top-n", type=int, default=20,
              help="Show top N results in visualizations")
@apply_standard_options
@click.pass_context
def report(ctx, assignments_path: str, output_path: str, **kwargs):
    """
    Generate BLAST assignment report and visualizations.
    
    Creates comprehensive reports with summary statistics, taxonomic distributions,
    and optional interactive visualizations from BLAST assignment results.
    
    Examples:
        ionspid blast report -a assignments.csv -o report.html --interactive
        ionspid blast report -a results.csv -o summary.png --include-tree
        ionspid blast report -a data.csv -o report.pdf --group-by identity --top-n 50
    """
    # Create CLI handler
    cli_handler = create_cli_handler("blast.report", kwargs)
    
    try:
        # Prepare parameters
        cli_args = {
            "assignments_path": Path(assignments_path),
            "output_path": Path(output_path),
            **kwargs
        }
        
        # Load and validate parameters
        params = cli_handler.load_and_validate_params(
            cli_args=cli_args,
            param_model=BlastReportParams
        )
        
        # Display configuration
        report_details = {
            "Input assignments": str(params.assignments_path),
            "Output report": str(params.output_path),
            "Interactive": "Yes" if params.interactive else "No",
            "Include tree": "Yes" if params.include_tree else "No",
            "Group by": params.group_by,
            "Top N results": str(params.top_n)
        }
        cli_handler.print_info("Report Generation Configuration:", report_details)
        
        # Load assignments data
        with cli_handler.create_progress_context("Loading assignment data..."):
            df = pd.read_csv(params.assignments_path)
        
        cli_handler.print_info(f"Loaded {len(df)} assignments")
        
        # Generate visualizations
        if params.include_tree:
            tree_path = params.output_path.with_suffix(f".tree.{params.plot_format}")
            with cli_handler.create_progress_context("Generating taxonomic tree..."):
                BlastVisualizer.tree_visualization(df, tree_path)
            cli_handler.print_success(f"Tree visualization saved to: {tree_path}")
        
        # Generate main report
        with cli_handler.create_progress_context("Generating assignment report..."):
            BlastVisualizer.plot_taxonomic_distribution(
                df, 
                params.output_path, 
                interactive=params.interactive,
                group_by=params.group_by,
                top_n=params.top_n,
                show_statistics=params.show_statistics
            )
        
        report_completion = {
            "Report saved to": str(params.output_path)
        }
        cli_handler.print_success("Report generation completed successfully!", report_completion)
        
    except Exception as e:
        cli_handler.handle_error(e, "Report generation failed")
