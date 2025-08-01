"""
Meetup API Authentication Manager

This module handles authentication with the Meetup.com GraphQL API,
including credential validation, token management, authentication state tracking,
and comprehensive error handling with proper logging.
"""

import logging
from typing import Dict, Optional
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from ..utils.logging_config import get_logger
from ..utils.retry_utils import retry_network_call, NetworkRetryableError


class AuthenticationError(Exception):
    """Raised when authentication with Meetup API fails."""
    pass


class MeetupAuth:
    """
    Handles Meetup API authentication and token management.
    
    This class manages API credentials, validates authentication,
    and provides authentication headers for API requests.
    """
    
    def __init__(self, api_key: str, oauth_token: str):
        """
        Initialize the authentication manager.
        
        Args:
            api_key: Meetup API key
            oauth_token: OAuth token for API access
            
        Raises:
            ValueError: If credentials are empty or None
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty or None")
        if not oauth_token or not oauth_token.strip():
            raise ValueError("OAuth token cannot be empty or None")
            
        self._api_key = api_key.strip()
        self._oauth_token = oauth_token.strip()
        self._authenticated = False
        self._auth_headers: Optional[Dict[str, str]] = None
        
        # Use centralized logging
        self.logger = get_logger(__name__)
        self.logger.info("MeetupAuth initialized with credentials")
    
    def authenticate(self) -> bool:
        """
        Authenticate with the Meetup API.
        
        Validates credentials by making a test API call to verify
        the authentication token works.
        
        Returns:
            bool: True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails due to invalid credentials
        """
        try:
            # Prepare authentication headers
            headers = {
                'Authorization': f'Bearer {self._oauth_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'MeetupRSVPFetcher/1.0'
            }
            
            # Test authentication with a simple GraphQL query
            test_query = {
                'query': '''
                    query TestAuth {
                        self {
                            id
                            name
                        }
                    }
                '''
            }
            
            self.logger.info("Attempting to authenticate with Meetup API")
            
            # Make test request to validate credentials
            response = requests.post(
                'https://api.meetup.com/gql',
                json=test_query,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if the response contains errors
                if 'errors' in data:
                    error_messages = [error.get('message', 'Unknown error') for error in data['errors']]
                    self.logger.error(f"Authentication failed with API errors: {error_messages}")
                    raise AuthenticationError(f"Authentication failed: {', '.join(error_messages)}")
                
                # Check if we got valid user data
                if 'data' in data and data['data'] and 'self' in data['data']:
                    self._authenticated = True
                    self._auth_headers = headers
                    user_info = data['data']['self']
                    self.logger.info(f"Authentication successful for user: {user_info.get('name', 'Unknown')}")
                    return True
                else:
                    self.logger.error("Authentication failed: Invalid response format")
                    raise AuthenticationError("Authentication failed: Invalid response format")
                    
            elif response.status_code == 401:
                self.logger.error("Authentication failed: Invalid credentials (401)")
                raise AuthenticationError("Authentication failed: Invalid credentials")
            elif response.status_code == 403:
                self.logger.error("Authentication failed: Access forbidden (403)")
                raise AuthenticationError("Authentication failed: Access forbidden")
            else:
                self.logger.error(f"Authentication failed: HTTP {response.status_code}")
                raise AuthenticationError(f"Authentication failed: HTTP {response.status_code}")
                
        except Timeout:
            self.logger.error("Authentication failed: Request timeout")
            raise AuthenticationError("Authentication failed: Request timeout")
        except ConnectionError:
            self.logger.error("Authentication failed: Connection error")
            raise AuthenticationError("Authentication failed: Connection error")
        except RequestException as e:
            self.logger.error(f"Authentication failed: Network error - {str(e)}")
            raise AuthenticationError(f"Authentication failed: Network error - {str(e)}")
        except Exception as e:
            self.logger.error(f"Authentication failed: Unexpected error - {str(e)}")
            raise AuthenticationError(f"Authentication failed: Unexpected error - {str(e)}")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dict[str, str]: Headers dictionary with authentication information
            
        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._authenticated or not self._auth_headers:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")
        
        return self._auth_headers.copy()
    
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        return self._authenticated
    
    def reset_authentication(self) -> None:
        """
        Reset authentication state.
        
        This method clears the authentication state and headers,
        requiring re-authentication before making API calls.
        """
        self._authenticated = False
        self._auth_headers = None
        self.logger.info("Authentication state reset")