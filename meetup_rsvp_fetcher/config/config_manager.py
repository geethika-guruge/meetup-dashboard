"""
Configuration management for the Meetup RSVP Fetcher application.

This module handles loading configuration from environment variables and config files,
with secure credential management and validation.
"""

import os
import json
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MeetupConfig:
    """Configuration data class for Meetup API settings."""
    api_key: str
    oauth_token: str
    network_id: str
    base_url: str = "https://api.meetup.com/gql"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 1.0


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ConfigManager:
    """
    Manages application configuration from environment variables and config files.
    
    Supports loading configuration from:
    1. Environment variables (highest priority)
    2. JSON configuration file
    3. Default values (lowest priority)
    """
    
    # Environment variable names
    ENV_API_KEY = "MEETUP_API_KEY"
    ENV_OAUTH_TOKEN = "MEETUP_OAUTH_TOKEN"
    ENV_NETWORK_ID = "MEETUP_NETWORK_ID"
    ENV_BASE_URL = "MEETUP_BASE_URL"
    ENV_TIMEOUT = "MEETUP_TIMEOUT"
    ENV_MAX_RETRIES = "MEETUP_MAX_RETRIES"
    ENV_RATE_LIMIT_DELAY = "MEETUP_RATE_LIMIT_DELAY"
    
    # Required configuration keys
    REQUIRED_KEYS = ["api_key", "oauth_token", "network_id"]
    
    def __init__(self, config_file_path: Optional[str] = None):
        """
        Initialize ConfigManager.
        
        Args:
            config_file_path: Optional path to JSON configuration file
        """
        self.config_file_path = config_file_path or "config.json"
        self._config: Optional[MeetupConfig] = None
    
    def load_config(self) -> MeetupConfig:
        """
        Load configuration from environment variables and config files.
        
        Returns:
            MeetupConfig: Loaded and validated configuration
            
        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        if self._config is not None:
            return self._config
        
        # Start with default values
        config_data = {
            "base_url": "https://api.meetup.com/gql",
            "timeout": 30,
            "max_retries": 3,
            "rate_limit_delay": 1.0
        }
        
        # Load from config file if it exists
        file_config = self._load_from_file()
        if file_config:
            config_data.update(file_config)
        
        # Override with environment variables (highest priority)
        env_config = self._load_from_environment()
        config_data.update(env_config)
        
        # Validate required configuration
        self._validate_config(config_data)
        
        # Create and cache configuration object
        self._config = MeetupConfig(
            api_key=config_data["api_key"],
            oauth_token=config_data["oauth_token"],
            network_id=config_data["network_id"],
            base_url=config_data["base_url"],
            timeout=int(config_data["timeout"]),
            max_retries=int(config_data["max_retries"]),
            rate_limit_delay=float(config_data["rate_limit_delay"])
        )
        
        return self._config
    
    def get_api_credentials(self) -> Tuple[str, str]:
        """
        Get API credentials (API key and OAuth token).
        
        Returns:
            Tuple[str, str]: API key and OAuth token
            
        Raises:
            ConfigurationError: If credentials are not configured
        """
        config = self.load_config()
        return config.api_key, config.oauth_token
    
    def get_network_id(self) -> str:
        """
        Get the MeetupPro network ID.
        
        Returns:
            str: Network ID
            
        Raises:
            ConfigurationError: If network ID is not configured
        """
        config = self.load_config()
        return config.network_id
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        if os.getenv(self.ENV_API_KEY):
            env_config["api_key"] = os.getenv(self.ENV_API_KEY)
        
        if os.getenv(self.ENV_OAUTH_TOKEN):
            env_config["oauth_token"] = os.getenv(self.ENV_OAUTH_TOKEN)
        
        if os.getenv(self.ENV_NETWORK_ID):
            env_config["network_id"] = os.getenv(self.ENV_NETWORK_ID)
        
        if os.getenv(self.ENV_BASE_URL):
            env_config["base_url"] = os.getenv(self.ENV_BASE_URL)
        
        if os.getenv(self.ENV_TIMEOUT):
            try:
                env_config["timeout"] = int(os.getenv(self.ENV_TIMEOUT))
            except ValueError:
                raise ConfigurationError(f"Invalid timeout value: {os.getenv(self.ENV_TIMEOUT)}")
        
        if os.getenv(self.ENV_MAX_RETRIES):
            try:
                env_config["max_retries"] = int(os.getenv(self.ENV_MAX_RETRIES))
            except ValueError:
                raise ConfigurationError(f"Invalid max_retries value: {os.getenv(self.ENV_MAX_RETRIES)}")
        
        if os.getenv(self.ENV_RATE_LIMIT_DELAY):
            try:
                env_config["rate_limit_delay"] = float(os.getenv(self.ENV_RATE_LIMIT_DELAY))
            except ValueError:
                raise ConfigurationError(f"Invalid rate_limit_delay value: {os.getenv(self.ENV_RATE_LIMIT_DELAY)}")
        
        return env_config
    
    def _load_from_file(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from JSON file.
        
        Returns:
            Optional[Dict[str, Any]]: Configuration data or None if file doesn't exist
            
        Raises:
            ConfigurationError: If file exists but is invalid JSON
        """
        config_path = Path(self.config_file_path)
        
        if not config_path.exists():
            return None
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file {self.config_file_path}: {e}")
        except IOError as e:
            raise ConfigurationError(f"Error reading config file {self.config_file_path}: {e}")
    
    def _validate_config(self, config_data: Dict[str, Any]) -> None:
        """
        Validate that all required configuration is present and valid.
        
        Args:
            config_data: Configuration dictionary to validate
            
        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        # Check required keys
        missing_keys = []
        for key in self.REQUIRED_KEYS:
            if key not in config_data or not config_data[key]:
                missing_keys.append(key)
        
        if missing_keys:
            raise ConfigurationError(
                f"Missing required configuration: {', '.join(missing_keys)}. "
                f"Set environment variables or add to config file."
            )
        
        # Validate data types and ranges
        if "timeout" in config_data:
            try:
                timeout = int(config_data["timeout"])
                if timeout <= 0:
                    raise ConfigurationError("Timeout must be a positive integer")
            except (ValueError, TypeError):
                raise ConfigurationError("Timeout must be a valid integer")
        
        if "max_retries" in config_data:
            try:
                max_retries = int(config_data["max_retries"])
                if max_retries < 0:
                    raise ConfigurationError("Max retries must be a non-negative integer")
            except (ValueError, TypeError):
                raise ConfigurationError("Max retries must be a valid integer")
        
        if "rate_limit_delay" in config_data:
            try:
                rate_limit_delay = float(config_data["rate_limit_delay"])
                if rate_limit_delay < 0:
                    raise ConfigurationError("Rate limit delay must be a non-negative number")
            except (ValueError, TypeError):
                raise ConfigurationError("Rate limit delay must be a valid number")
        
        # Validate URL format
        if "base_url" in config_data:
            base_url = config_data["base_url"]
            if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
                raise ConfigurationError("Base URL must be a valid HTTP/HTTPS URL")
    
    def reload_config(self) -> MeetupConfig:
        """
        Force reload configuration from sources.
        
        Returns:
            MeetupConfig: Reloaded configuration
        """
        self._config = None
        return self.load_config()