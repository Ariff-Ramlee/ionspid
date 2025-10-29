"""
File utilities for iONspID.

This module provides helper functions for file operations and path management.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union, Iterator
from ionspid.utils.file_formats import detect_format, is_supported_format, FileFormat


def ensure_directory(directory: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to ensure exists
        
    Returns:
        Path object to the ensured directory
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def is_valid_file(file_path: Union[str, Path], extensions: Optional[List[str]] = None, allowed_formats: Optional[List[FileFormat]] = None) -> bool:
    """
    Check if a file exists and has a valid extension or format.

    Args:
        file_path: Path to the file to check
        extensions: List of valid extensions (e.g., ['.fastq', '.fq'])
        allowed_formats: List of allowed FileFormat enums

    Returns:
        True if file exists and has a valid extension/format, False otherwise
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        return False
    if allowed_formats is not None:
        return is_supported_format(file_path, allowed_formats)
    if extensions is not None:
        return file_path.suffix.lower() in extensions
    return True


def find_files(directory: Union[str, Path], pattern: str) -> List[Path]:
    """
    Find files in a directory matching a glob pattern.
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern to match (e.g., "*.fastq")
        
    Returns:
        List of matching file paths
    """
    directory = Path(directory)
    return list(directory.glob(pattern))


def copy_with_progress(
    src: Union[str, Path], 
    dst: Union[str, Path], 
    callback=None
) -> None:
    """
    Copy a file with progress reporting.
    
    Args:
        src: Source file path
        dst: Destination file path
        callback: Optional callback function for progress reporting
                 Function signature: callback(bytes_copied, total_bytes)
    """
    src, dst = Path(src), Path(dst)
    
    # Get file size for progress reporting
    file_size = src.stat().st_size
    bytes_copied = 0
    
    # Make sure destination directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy with progress reporting
    with src.open('rb') as fsrc, dst.open('wb') as fdst:
        while True:
            buf = fsrc.read(8192)  # 8KB chunks
            if not buf:
                break
                
            fdst.write(buf)
            bytes_copied += len(buf)
            
            if callback is not None:
                callback(bytes_copied, file_size)


def safe_remove(path: Union[str, Path]) -> None:
    """
    Safely remove a file or directory if it exists.
    
    Args:
        path: Path to file or directory to remove
    """
    path = Path(path)
    
    if not path.exists():
        return
        
    if path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def validate_output_path(
    path: Union[str, Path], 
    overwrite: bool = False
) -> bool:
    """
    Validate an output path for writing.
    
    Args:
        path: Path to validate
        overwrite: Whether to allow overwriting existing files
        
    Returns:
        True if the path is valid for writing, False otherwise
    """
    path = Path(path)
    
    # Check if parent directory exists
    if not path.parent.exists():
        return False
    
    # Check if path exists and whether overwriting is allowed
    if path.exists() and not overwrite:
        return False
        
    return True


def iterate_chunks(file_path: Union[str, Path], chunk_size: int = 4096) -> Iterator[bytes]:
    """
    Iterate over a file in chunks.
    
    Args:
        file_path: Path to the file
        chunk_size: Size of each chunk in bytes
        
    Yields:
        File chunks as bytes
    """
    file_path = Path(file_path)
    
    with file_path.open('rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk
