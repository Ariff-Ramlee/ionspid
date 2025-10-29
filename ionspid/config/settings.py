"""
Settings management for iONspID.

This module provides functionality for loading, validating, and accessing application settings.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, ValidationError

from ionspid.utils.logging import get_logger

logger = get_logger(__name__)


class CoreSettings(BaseModel):
    """Core application settings."""
    
    # Logging settings
    log_level: str = Field(
        default="info", 
        description="Global log level (debug, info, warning, error, critical)"
    )
    log_dir: Optional[str] = Field(
        default=None, 
        description="Directory for log files, if None, file logging is disabled"
    )
    
    # File paths
    temp_dir: str = Field(
        default="{user_temp}/ionspid", 
        description="Directory for temporary files"
    )
    data_dir: str = Field(
        default="{user_data}/ionspid", 
        description="Directory for application data"
    )
    
    # Performance settings
    threads: int = Field(
        default=0, 
        description="Number of threads to use (0 = automatic)"
    )
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Forbid extra attributes


class Settings(BaseModel):
    """Complete application settings."""
    
    core: CoreSettings = Field(default_factory=CoreSettings)
    
    # Additional settings sections can be added here as the application grows
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Forbid extra attributes


class SettingsManager:
    """
    Manager for application settings.
    
    This class provides a singleton interface for loading, validating, and accessing
    application settings from configuration files and environment variables.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._settings = Settings()
        self._config_file = None
    
    def load_settings(self, config_file: Optional[Union[str, Path]] = None) -> None:
        """
        Load settings from a configuration file.
        
        Args:
            config_file: Path to the configuration file (YAML format)
        """
        if config_file is not None:
            config_file = Path(config_file)
            
            if not config_file.exists():
                logger.warning(f"Configuration file not found: {config_file}")
                return
                
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    
                self._settings = Settings.parse_obj(config_data)
                self._config_file = config_file
                logger.info(f"Loaded settings from {config_file}")
                
            except (yaml.YAMLError, ValidationError) as e:
                logger.error(f"Error loading configuration: {e}")
    
    def get_settings(self) -> Settings:
        """
        Get the current application settings.
        
        Returns:
            Current settings object
        """
        return self._settings
    
    def update_settings(self, settings_dict: Dict[str, Any]) -> None:
        """
        Update settings with new values.
        
        Args:
            settings_dict: Dictionary of settings to update
        """
        try:
            # Create a dictionary with current settings
            current_dict = self._settings.dict()
            
            # Update with new values
            current_dict.update(settings_dict)
            
            # Parse updated dictionary
            self._settings = Settings.parse_obj(current_dict)
            
        except ValidationError as e:
            logger.error(f"Error updating settings: {e}")
    
    def save_settings(self, config_file: Optional[Union[str, Path]] = None) -> bool:
        """
        Save current settings to a configuration file.
        
        Args:
            config_file: Path to save the configuration to, if None, uses the file
                        the settings were loaded from
                        
        Returns:
            True if settings were saved successfully, False otherwise
        """
        if config_file is None:
            if self._config_file is None:
                logger.error("No configuration file specified")
                return False
            config_file = self._config_file
        
        config_file = Path(config_file)
        
        try:
            # Ensure the directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save settings as YAML
            with open(config_file, 'w') as f:
                yaml.dump(self._settings.dict(), f, default_flow_style=False)
                
            logger.info(f"Saved settings to {config_file}")
            return True
            
        except (OSError, yaml.YAMLError) as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def expand_path(self, path: str) -> str:
        """
        Expand placeholders in path strings.
        
        Args:
            path: Path string with placeholders
            
        Returns:
            Expanded path string
        """
        # Define common placeholders
        placeholders = {
            "{user_home}": str(Path.home()),
            "{user_data}": str(Path.home() / "Library" / "Application Support" 
                              if os.name == "posix" and sys.platform == "darwin"
                              else Path.home() / ".local" / "share" 
                              if os.name == "posix"
                              else Path.home() / "AppData" / "Local"),
            "{user_temp}": str(Path(os.getenv("TMPDIR", "/tmp")) 
                              if os.name == "posix"
                              else Path(os.getenv("TEMP", "C:\\Temp")))
        }
        
        # Replace placeholders
        result = path
        for placeholder, value in placeholders.items():
            result = result.replace(placeholder, value)
            
        return result
    
    def get_temp_dir(self) -> Path:
        """
        Get the expanded temporary directory path.
        
        Returns:
            Path object to the temporary directory
        """
        temp_dir = self.expand_path(self._settings.core.temp_dir)
        return Path(temp_dir)
    
    def get_data_dir(self) -> Path:
        """
        Get the expanded data directory path.
        
        Returns:
            Path object to the data directory
        """
        data_dir = self.expand_path(self._settings.core.data_dir)
        return Path(data_dir)


# Convenience function to get the settings
def get_settings() -> Settings:
    """
    Get the current application settings.
    
    Returns:
        Current settings object
    """
    return SettingsManager().get_settings()


# Import for the side effect of exposing os and sys
import os
import sys
