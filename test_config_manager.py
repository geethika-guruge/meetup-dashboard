"""
Unit tests for the ConfigManager class.
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from meetup_rsvp_fetcher.config import ConfigManager, MeetupConfig, ConfigurationError


class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Clear any cached config
        self.config_manager = ConfigManager()
        self.config_manager._config = None
        
        # Clear environment variables
        env_vars = [
            "MEETUP_API_KEY", "MEETUP_OAUTH_TOKEN", "MEETUP_NETWORK_ID",
            "MEETUP_BASE_URL", "MEETUP_TIMEOUT", "MEETUP_MAX_RETRIES",
            "MEETUP_RATE_LIMIT_DELAY"
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def test_load_config_from_environment_variables(self):
        """Test loading configuration from environment variables."""
        # Set environment variables
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        os.environ["MEETUP_BASE_URL"] = "https://custom.api.com/gql"
        os.environ["MEETUP_TIMEOUT"] = "60"
        os.environ["MEETUP_MAX_RETRIES"] = "5"
        os.environ["MEETUP_RATE_LIMIT_DELAY"] = "2.5"
        
        config = self.config_manager.load_config()
        
        assert config.api_key == "test_api_key"
        assert config.oauth_token == "test_oauth_token"
        assert config.network_id == "test_network"
        assert config.base_url == "https://custom.api.com/gql"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.rate_limit_delay == 2.5
    
    def test_load_config_from_file(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "api_key": "file_api_key",
            "oauth_token": "file_oauth_token",
            "network_id": "file_network",
            "base_url": "https://file.api.com/gql",
            "timeout": 45,
            "max_retries": 4,
            "rate_limit_delay": 1.5
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            config_manager = ConfigManager(config_file_path=temp_file)
            config = config_manager.load_config()
            
            assert config.api_key == "file_api_key"
            assert config.oauth_token == "file_oauth_token"
            assert config.network_id == "file_network"
            assert config.base_url == "https://file.api.com/gql"
            assert config.timeout == 45
            assert config.max_retries == 4
            assert config.rate_limit_delay == 1.5
        finally:
            os.unlink(temp_file)
    
    def test_environment_variables_override_file(self):
        """Test that environment variables take precedence over file configuration."""
        # Create config file
        config_data = {
            "api_key": "file_api_key",
            "oauth_token": "file_oauth_token",
            "network_id": "file_network"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            # Set environment variables
            os.environ["MEETUP_API_KEY"] = "env_api_key"
            os.environ["MEETUP_OAUTH_TOKEN"] = "env_oauth_token"
            os.environ["MEETUP_NETWORK_ID"] = "env_network"
            
            config_manager = ConfigManager(config_file_path=temp_file)
            config = config_manager.load_config()
            
            # Environment variables should override file values
            assert config.api_key == "env_api_key"
            assert config.oauth_token == "env_oauth_token"
            assert config.network_id == "env_network"
        finally:
            os.unlink(temp_file)
    
    def test_default_values(self):
        """Test that default values are used when not specified."""
        # Set only required values
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        
        config = self.config_manager.load_config()
        
        # Check default values
        assert config.base_url == "https://api.meetup.com/gql"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.rate_limit_delay == 1.0
    
    def test_missing_required_configuration_raises_error(self):
        """Test that missing required configuration raises ConfigurationError."""
        # Don't set any required environment variables
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_manager.load_config()
        
        assert "Missing required configuration" in str(exc_info.value)
        assert "api_key" in str(exc_info.value)
        assert "oauth_token" in str(exc_info.value)
        assert "network_id" in str(exc_info.value)
    
    def test_partial_missing_configuration_raises_error(self):
        """Test that partially missing required configuration raises error."""
        # Set only some required values
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        # Missing oauth_token and network_id
        
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_manager.load_config()
        
        assert "Missing required configuration" in str(exc_info.value)
        assert "oauth_token" in str(exc_info.value)
        assert "network_id" in str(exc_info.value)
    
    def test_invalid_timeout_raises_error(self):
        """Test that invalid timeout value raises ConfigurationError."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        os.environ["MEETUP_TIMEOUT"] = "invalid"
        
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_manager.load_config()
        
        assert "Invalid timeout value" in str(exc_info.value)
    
    def test_negative_timeout_raises_error(self):
        """Test that negative timeout raises ConfigurationError."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        os.environ["MEETUP_TIMEOUT"] = "-5"
        
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_manager.load_config()
        
        assert "Timeout must be a positive integer" in str(exc_info.value)
    
    def test_invalid_max_retries_raises_error(self):
        """Test that invalid max_retries value raises ConfigurationError."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        os.environ["MEETUP_MAX_RETRIES"] = "invalid"
        
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_manager.load_config()
        
        assert "Invalid max_retries value" in str(exc_info.value)
    
    def test_negative_max_retries_raises_error(self):
        """Test that negative max_retries raises ConfigurationError."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        os.environ["MEETUP_MAX_RETRIES"] = "-1"
        
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_manager.load_config()
        
        assert "Max retries must be a non-negative integer" in str(exc_info.value)
    
    def test_invalid_rate_limit_delay_raises_error(self):
        """Test that invalid rate_limit_delay value raises ConfigurationError."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        os.environ["MEETUP_RATE_LIMIT_DELAY"] = "invalid"
        
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_manager.load_config()
        
        assert "Invalid rate_limit_delay value" in str(exc_info.value)
    
    def test_negative_rate_limit_delay_raises_error(self):
        """Test that negative rate_limit_delay raises ConfigurationError."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        os.environ["MEETUP_RATE_LIMIT_DELAY"] = "-1.0"
        
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_manager.load_config()
        
        assert "Rate limit delay must be a non-negative number" in str(exc_info.value)
    
    def test_invalid_base_url_raises_error(self):
        """Test that invalid base URL raises ConfigurationError."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        os.environ["MEETUP_BASE_URL"] = "invalid-url"
        
        with pytest.raises(ConfigurationError) as exc_info:
            self.config_manager.load_config()
        
        assert "Base URL must be a valid HTTP/HTTPS URL" in str(exc_info.value)
    
    def test_invalid_json_file_raises_error(self):
        """Test that invalid JSON file raises ConfigurationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            config_manager = ConfigManager(config_file_path=temp_file)
            with pytest.raises(ConfigurationError) as exc_info:
                config_manager.load_config()
            
            assert "Invalid JSON in config file" in str(exc_info.value)
        finally:
            os.unlink(temp_file)
    
    def test_get_api_credentials(self):
        """Test get_api_credentials method."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        
        api_key, oauth_token = self.config_manager.get_api_credentials()
        
        assert api_key == "test_api_key"
        assert oauth_token == "test_oauth_token"
    
    def test_get_network_id(self):
        """Test get_network_id method."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        
        network_id = self.config_manager.get_network_id()
        
        assert network_id == "test_network"
    
    def test_config_caching(self):
        """Test that configuration is cached after first load."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        
        # Load config first time
        config1 = self.config_manager.load_config()
        
        # Change environment variable
        os.environ["MEETUP_API_KEY"] = "changed_api_key"
        
        # Load config second time - should return cached version
        config2 = self.config_manager.load_config()
        
        assert config1 is config2
        assert config2.api_key == "test_api_key"  # Original value, not changed
    
    def test_reload_config(self):
        """Test reload_config method forces fresh load."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        
        # Load config first time
        config1 = self.config_manager.load_config()
        
        # Change environment variable
        os.environ["MEETUP_API_KEY"] = "changed_api_key"
        
        # Reload config - should pick up new value
        config2 = self.config_manager.reload_config()
        
        assert config1 is not config2
        assert config2.api_key == "changed_api_key"
    
    def test_nonexistent_config_file_ignored(self):
        """Test that nonexistent config file is gracefully ignored."""
        os.environ["MEETUP_API_KEY"] = "test_api_key"
        os.environ["MEETUP_OAUTH_TOKEN"] = "test_oauth_token"
        os.environ["MEETUP_NETWORK_ID"] = "test_network"
        
        config_manager = ConfigManager(config_file_path="nonexistent.json")
        config = config_manager.load_config()
        
        # Should still work with environment variables
        assert config.api_key == "test_api_key"
        assert config.oauth_token == "test_oauth_token"
        assert config.network_id == "test_network"


if __name__ == "__main__":
    pytest.main([__file__])