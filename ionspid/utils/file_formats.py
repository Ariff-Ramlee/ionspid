"""
File format standards and utilities for iONspID.

This module defines supported file formats, provides validation, detection, and conversion utilities to ensure interoperability between pipeline modules.
"""

from enum import Enum
from pathlib import Path
from typing import Optional, List

class FileFormat(str, Enum):
    POD5 = "pod5"
    FAST5 = "fast5" 
    FASTQ = "fastq"
    FASTA = "fasta"
    BAM = "bam"
    TSV = "tsv"
    CSV = "csv"
    TAXONOMY = "taxonomy"

# Mapping of formats to extensions (lowercase, with dot)
FORMAT_EXTENSIONS = {
    FileFormat.POD5: [".pod5"],
    FileFormat.FAST5: [".fast5"],
    FileFormat.FASTQ: [".fastq", ".fq", ".fastq.gz", ".fq.gz"],
    FileFormat.FASTA: [".fasta", ".fa", ".fna", ".fas", ".fasta.gz", ".fa.gz", ".fna.gz", ".fas.gz"],
    FileFormat.BAM: [".bam"],
    FileFormat.TSV: [".tsv", ".txt"],
    FileFormat.CSV: [".csv"],
    FileFormat.TAXONOMY: [".tax", ".taxonomy", ".kraken", ".centrifuge", ".txt", ".tsv", ".csv"],
}


def detect_format(file_path: Path) -> FileFormat:
    """
    Detect file format based on file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Detected file format
        
    Raises:
        ValueError: If format cannot be determined
    """
    file_path = Path(file_path)
    
    # Handle multiple extensions (e.g., .fastq.gz)
    full_suffix = "".join(file_path.suffixes).lower()
    single_suffix = file_path.suffix.lower()
    
    # Check both full suffix and single suffix
    for format_type, extensions in FORMAT_EXTENSIONS.items():
        if full_suffix in extensions or single_suffix in extensions:
            return format_type
    
    # Special handling for common compressed formats
    if full_suffix.endswith('.gz'):
        base_suffix = full_suffix[:-3]  # Remove .gz
        for format_type, extensions in FORMAT_EXTENSIONS.items():
            if base_suffix in extensions:
                return format_type
    
    raise ValueError(f"Cannot determine file format for: {file_path}")


def is_supported_format(
    file_path: Path, 
    allowed_formats: Optional[List[FileFormat]] = None
) -> bool:
    """
    Check if a file format is supported.
    
    Args:
        file_path: Path to the file
        allowed_formats: List of allowed formats (None = all supported)
        
    Returns:
        True if format is supported
    """
    try:
        detected_format = detect_format(file_path)
        if allowed_formats is None:
            return True
        return detected_format in allowed_formats
    except ValueError:
        return False


def get_format_extensions(format_type: FileFormat) -> List[str]:
    """
    Get all extensions for a given file format.

    Args:
        fmt (FileFormat): File format enum.

    Returns:
        List[str]: List of extensions (with dot).
    """
    return FORMAT_EXTENSIONS.get(format_type, [])


def is_compressed(file_path: Path) -> bool:
    """Check if file is compressed based on extension."""
    return str(file_path).lower().endswith('.gz')

