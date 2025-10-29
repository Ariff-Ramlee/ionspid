"""
CLI commands for sequence clustering operations.

This module provides command-line interface for clustering sequences using
various algorithms including VSEARCH and isONclust.
"""

import os
from pathlib import Path
from typing import Optional

import click
from Bio import SeqIO

from ionspid.core.clustering import (
    ClustererRegistry, ClusteringParams, ClusterAnalyzer, ClusterVisualizer
)
from ionspid.utils.logging import get_logger
from ionspid.utils.exceptions import ProcessingError, InputError
from ionspid.cli.utils.standard_cli import apply_standard_options, create_cli_handler

logger = get_logger(__name__)


@click.group(name="cluster")
def cluster_cli():
    """
    Sequence clustering operations.
    
    Group similar sequences based on identity thresholds using various
    clustering algorithms optimized for different data types.
    """
    pass


@cluster_cli.command("run")
@click.option(
    "--input", "-i",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Input FASTA file containing sequences to cluster"
)
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(dir_okay=True, resolve_path=True),
    help="Output directory for clustering results"
)
@click.option(
    "--algorithm", "-a",
    type=click.Choice(["vsearch", "isonclust", "swarm", "mmseqs2", "cd-hit-est", "cdhit"], case_sensitive=False),
    default="vsearch",
    help="Clustering algorithm to use"
)
@click.option(
    "--identity", "-id",
    type=click.FloatRange(0.5, 1.0),
    default=0.97,
    help="Sequence identity threshold for clustering"
)
@click.option(
    "--min-cluster-size",
    type=click.IntRange(1, None),
    default=1,
    help="Minimum number of sequences per cluster"
)
@click.option(
    "--extra-params",
    type=str,
    help="Additional algorithm-specific parameters (JSON format)"
)
@click.option(
    "--plot/--no-plot",
    default=True,
    help="Generate clustering visualization plots"
)
@apply_standard_options
@click.pass_context
def run_clustering(
    ctx: click.Context,
    input: str,
    output: str,
    algorithm: str,
    identity: float,
    min_cluster_size: int,
    extra_params: Optional[str],
    plot: bool,
    **kwargs
):
    """
    Run sequence clustering on input FASTA file.
    
    This command clusters sequences based on similarity thresholds using
    the specified algorithm. Results include cluster assignments, 
    representative sequences, and optional visualizations.
    
    Examples:
        # Basic clustering with VSEARCH
        ionspid cluster run -i sequences.fasta -o results/ --identity 0.97
        
        # Clustering with isONclust for Nanopore data
        ionspid cluster run -i nanopore.fasta -o results/ -a isonclust
        
        # With custom parameters
        ionspid cluster run -i sequences.fasta -o results/ --extra-params '{"threads": 4}'
    """
    # Create CLI handler
    cli_handler = create_cli_handler("cluster_run", kwargs)
    
    try:
        # Validate input file
        if not os.path.exists(input):
            raise InputError(f"Input file does not exist: {input}")
        
        # Create output directory
        os.makedirs(output, exist_ok=True)
        logger.info(f"Created output directory: {output}")
        
        # Parse extra parameters
        extra_params_dict = None
        if extra_params:
            import json
            try:
                extra_params_dict = json.loads(extra_params)
            except json.JSONDecodeError as e:
                raise InputError(f"Invalid JSON in extra-params: {e}")
        
        # Load sequences
        logger.info(f"Loading sequences from {input}")
        sequences = list(SeqIO.parse(input, "fasta"))
        
        if not sequences:
            raise InputError(f"No sequences found in input file: {input}")
        
        logger.info(f"Loaded {len(sequences)} sequences")
        
        # Create clustering parameters
        params = ClusteringParams(
            identity_threshold=identity,
            min_cluster_size=min_cluster_size,
            algorithm=algorithm,
            extra_params=extra_params_dict
        )
        
        # Get clusterer from registry
        clusterer_class = ClustererRegistry.get_clusterer(algorithm)
        clusterer = clusterer_class(params)
        
        logger.info(f"Running {algorithm} clustering with identity threshold {identity}")
        
        # Run clustering
        assignments = clusterer.cluster_sequences(sequences, output)
        
        if assignments.empty:
            logger.warning("No clusters were formed")
            return
        
        # Save results
        clusterer.save_results(output)
        logger.info(f"Clustering results saved to {output}")
        
        # Generate analysis and statistics
        analyzer = ClusterAnalyzer(assignments)
        
        # Create summary report
        summary_path = os.path.join(output, "clustering_summary.txt")
        with open(summary_path, "w") as f:
            f.write("=== Clustering Summary ===\n")
            f.write(f"Algorithm: {algorithm}\n")
            f.write(f"Identity threshold: {identity}\n")
            f.write(f"Total sequences: {len(sequences)}\n")
            f.write(f"Total clusters: {analyzer.cluster_count()}\n")
            f.write(f"Singleton percentage: {analyzer.singleton_percentage():.2f}%\n")
            f.write(f"Clustering efficiency: {analyzer.clustering_efficiency():.2f}\n")
            f.write("\nCluster size distribution:\n")
            size_dist = analyzer.size_distribution()
            for cluster_id, size in size_dist.head(10).items():
                f.write(f"  Cluster {cluster_id}: {size} sequences\n")
            if len(size_dist) > 10:
                f.write(f"  ... and {len(size_dist) - 10} more clusters\n")
        
        logger.info(f"Summary report saved to {summary_path}")
        
        # Generate plots if requested
        if plot:
            try:
                import matplotlib
                matplotlib.use('Agg')  # Use non-interactive backend
                import matplotlib.pyplot as plt
                
                visualizer = ClusterVisualizer()
                
                # Create cluster size distribution plot
                fig, ax = plt.subplots(figsize=(10, 6))
                visualizer.plot_size_distribution(assignments, ax=ax)
                
                plot_path = os.path.join(output, "cluster_size_distribution.png")
                plt.tight_layout()
                plt.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close()
                
                logger.info(f"Cluster size distribution plot saved to {plot_path}")
                
            except ImportError:
                logger.warning("Matplotlib not available, skipping plot generation")
            except Exception as e:
                logger.warning(f"Failed to generate plots: {e}")
        
        # Print summary to console
        cli_handler.print_success("Clustering completed successfully")
        click.echo("\n" + "="*50)
        click.echo("CLUSTERING SUMMARY")
        click.echo("="*50)
        click.echo(f"Algorithm: {algorithm}")
        click.echo(f"Identity threshold: {identity}")
        click.echo(f"Total sequences: {len(sequences)}")
        click.echo(f"Total clusters: {analyzer.cluster_count()}")
        click.echo(f"Singleton percentage: {analyzer.singleton_percentage():.2f}%")
        click.echo(f"Clustering efficiency: {analyzer.clustering_efficiency():.2f}")
        click.echo(f"\nResults saved to: {output}")
        
    except Exception as e:
        cli_handler.handle_error(e, "Clustering", show_traceback=kwargs.get('verbose', False))
        raise ProcessingError(f"Clustering failed: {e}")


@cluster_cli.command("analyze")
@click.option(
    "--assignments", "-a",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="CSV file containing cluster assignments"
)
@click.option(
    "--output", "-o",
    type=click.Path(dir_okay=True, resolve_path=True),
    help="Output directory for analysis results (default: same as assignments file)"
)
@click.option(
    "--plot/--no-plot",
    default=True,
    help="Generate analysis plots"
)
@apply_standard_options
@click.pass_context
def analyze_clusters(
    ctx: click.Context,
    assignments: str,
    output: Optional[str],
    plot: bool,
    **kwargs
):
    """
    Analyze existing clustering results.
    
    Generate statistics and visualizations from previously computed
    cluster assignments.
    
    Examples:
        # Analyze cluster assignments
        ionspid cluster analyze -a cluster_assignments.csv
        
        # Save analysis to specific directory
        ionspid cluster analyze -a assignments.csv -o analysis_results/
    """
    # Create CLI handler
    cli_handler = create_cli_handler("cluster_analyze", kwargs)
    
    try:
        import pandas as pd
        
        # Load assignments
        logger.info(f"Loading cluster assignments from {assignments}")
        df = pd.read_csv(assignments)
        
        # Validate format
        required_cols = ["sequence_id", "cluster_id", "algorithm"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise InputError(f"Missing required columns: {missing_cols}")
        
        # Set output directory
        if output is None:
            output = os.path.dirname(assignments)
        os.makedirs(output, exist_ok=True)
        
        # Analyze clusters
        analyzer = ClusterAnalyzer(df)
        
        # Generate detailed analysis report
        analysis_path = os.path.join(output, "cluster_analysis.txt")
        with open(analysis_path, "w") as f:
            f.write("=== Detailed Cluster Analysis ===\n")
            f.write(f"Total sequences: {len(df)}\n")
            f.write(f"Total clusters: {analyzer.cluster_count()}\n")
            f.write(f"Singleton percentage: {analyzer.singleton_percentage():.2f}%\n")
            f.write(f"Clustering efficiency: {analyzer.clustering_efficiency():.2f}\n")
            
            size_dist = analyzer.size_distribution()
            f.write(f"\nCluster size statistics:\n")
            f.write(f"  Mean: {size_dist.mean():.2f}\n")
            f.write(f"  Median: {size_dist.median():.2f}\n")
            f.write(f"  Min: {size_dist.min()}\n")
            f.write(f"  Max: {size_dist.max()}\n")
            f.write(f"  Std: {size_dist.std():.2f}\n")
            
            f.write(f"\nLargest clusters:\n")
            largest = size_dist.nlargest(10)
            for cluster_id, size in largest.items():
                f.write(f"  Cluster {cluster_id}: {size} sequences\n")
        
        logger.info(f"Analysis report saved to {analysis_path}")
        
        # Generate plots if requested
        if plot:
            try:
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                
                visualizer = ClusterVisualizer()
                
                # Cluster size distribution
                fig, ax = plt.subplots(figsize=(10, 6))
                visualizer.plot_size_distribution(df, ax=ax)
                
                plot_path = os.path.join(output, "cluster_analysis_distribution.png")
                plt.tight_layout()
                plt.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close()
                
                logger.info(f"Analysis plot saved to {plot_path}")
                
            except ImportError:
                logger.warning("Matplotlib not available, skipping plot generation")
            except Exception as e:
                logger.warning(f"Failed to generate plots: {e}")
        
        # Print summary
        click.echo("\n" + "="*50)
        click.echo("CLUSTER ANALYSIS")
        click.echo("="*50)
        click.echo(f"Total sequences: {len(df)}")
        click.echo(f"Total clusters: {analyzer.cluster_count()}")
        click.echo(f"Singleton percentage: {analyzer.singleton_percentage():.2f}%")
        click.echo(f"Clustering efficiency: {analyzer.clustering_efficiency():.2f}")
        click.echo(f"\nAnalysis saved to: {output}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise ProcessingError(f"Analysis failed: {e}")


@cluster_cli.command("list")
def list_algorithms():
    """
    List available clustering algorithms.
    
    Shows all registered clustering algorithms and their descriptions.
    """
    click.echo("Available clustering algorithms:")
    click.echo("-" * 50)
    click.echo("vsearch    - General-purpose clustering using VSEARCH")
    click.echo("isonclust  - Optimized for Oxford Nanopore long reads")
    click.echo("swarm      - Network-based clustering, preserves rare variants")
    click.echo("mmseqs2    - Ultra-fast clustering for large datasets")
    click.echo("cd-hit-est - Fast, memory-efficient nucleotide clustering")
    click.echo("cdhit      - Alias for cd-hit-est")
    click.echo()
    click.echo("Use 'ionspid cluster run --help' for parameter details.")


if __name__ == "__main__":
    cluster_cli()
