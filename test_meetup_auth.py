"""
Unit tests for MeetupAuth authentication manager.

Tests cover authentication scenarios including success cases,
failure cases, and error handling.
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, Timeout, ConnectionError

from meetup_rsvp_fetcher.auth.meetup_auth import MeetupAuth, AuthenticationError


class TestMeetupAuthInitialization:
    """Test MeetupAuth initialization and validation."""
    
    def test_init_with_valid_credentials(self):
        """Test initialization with valid credentials."""
        auth = MeetupAuth("valid_api_key", "valid_oauth_token")
        assert not auth.is_authenticated()
        assert auth._api_key == "valid_api_key"
        assert auth._oauth_token == "valid_oauth_token"
    
    def test_init_with_whitespace_credentials(self):
        """Test initialization trims whitespace from credentials."""
        auth = MeetupAuth("  api_key  ", "  oauth_token  ")
        assert auth._api_key == "api_key"
        assert auth._oauth_token == "oauth_token"
    
    def test_init_with_empty_api_key(self):
        """Test initialization fails with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty or None"):
            MeetupAuth("", "valid_oauth_token")
    
    def test_init_with_none_api_key(self):
        """Test initialization fails with None API key."""
        with pytest.raises(ValueError, match="API key cannot be empty or None"):
            MeetupAuth(None, "valid_oauth_token")
    
    def test_init_with_whitespace_only_api_key(self):
        """Test initialization fails with whitespace-only API key."""
        with pytest.raises(ValueError, match="API key cannot be empty or None"):
            MeetupAuth("   ", "valid_oauth_token")
    
    def test_init_with_empty_oauth_token(self):
        """Test initialization fails with empty OAuth token."""
        with pytest.raises(ValueError, match="OAuth token cannot be empty or None"):
            MeetupAuth("valid_api_key", "")
    
    def test_init_with_none_oauth_token(self):
        """Test initialization fails with None OAuth token."""
        with pytest.raises(ValueError, match="OAuth token cannot be empty or None"):
            MeetupAuth("valid_api_key", None)
    
    def test_init_with_whitespace_only_oauth_token(self):
        """Test initialization fails with whitespace-only OAuth token."""
        with pytest.raises(ValueError, match="OAuth token cannot be empty or None"):
            MeetupAuth("valid_api_key", "   ")


class TestMeetupAuthAuthentication:
    """Test MeetupAuth authentication functionality."""
    
    @pytest.fixture
    def auth(self):
        """Create MeetupAuth instance for testing."""
        return MeetupAuth("test_api_key", "test_oauth_token")
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_successful_authentication(self, mock_post, auth):
        """Test successful authentication."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'self': {
                    'id': '12345',
                    'name': 'Test User'
                }
            }
        }
        mock_post.return_value = mock_response
        
        result = auth.authenticate()
        
        assert result is True
        assert auth.is_authenticated()
        
        # Verify the request was made correctly
        mock_post.assert_called_once_with(
            'https://api.meetup.com/gql',
            json={'query': '''
                    query TestAuth {
                        self {
                            id
                            name
                        }
                    }
                '''},
            headers={
                'Authorization': 'Bearer test_oauth_token',
                'Content-Type': 'application/json',
                'User-Agent': 'MeetupRSVPFetcher/1.0'
            },
            timeout=30
        )
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_authentication_with_api_errors(self, mock_post, auth):
        """Test authentication failure with API errors."""
        # Mock API response with errors
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'errors': [
                {'message': 'Invalid token'},
                {'message': 'Access denied'}
            ]
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(AuthenticationError, match="Authentication failed: Invalid token, Access denied"):
            auth.authenticate()
        
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_authentication_401_unauthorized(self, mock_post, auth):
        """Test authentication failure with 401 status."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        with pytest.raises(AuthenticationError, match="Authentication failed: Invalid credentials"):
            auth.authenticate()
        
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_authentication_403_forbidden(self, mock_post, auth):
        """Test authentication failure with 403 status."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_post.return_value = mock_response
        
        with pytest.raises(AuthenticationError, match="Authentication failed: Access forbidden"):
            auth.authenticate()
        
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_authentication_other_http_error(self, mock_post, auth):
        """Test authentication failure with other HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        with pytest.raises(AuthenticationError, match="Authentication failed: HTTP 500"):
            auth.authenticate()
        
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_authentication_timeout(self, mock_post, auth):
        """Test authentication failure with timeout."""
        mock_post.side_effect = Timeout("Request timeout")
        
        with pytest.raises(AuthenticationError, match="Authentication failed: Request timeout"):
            auth.authenticate()
        
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_authentication_connection_error(self, mock_post, auth):
        """Test authentication failure with connection error."""
        mock_post.side_effect = ConnectionError("Connection failed")
        
        with pytest.raises(AuthenticationError, match="Authentication failed: Connection error"):
            auth.authenticate()
        
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_authentication_request_exception(self, mock_post, auth):
        """Test authentication failure with general request exception."""
        mock_post.side_effect = RequestException("Network error")
        
        with pytest.raises(AuthenticationError, match="Authentication failed: Network error"):
            auth.authenticate()
        
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_authentication_unexpected_exception(self, mock_post, auth):
        """Test authentication failure with unexpected exception."""
        mock_post.side_effect = ValueError("Unexpected error")
        
        with pytest.raises(AuthenticationError, match="Authentication failed: Unexpected error"):
            auth.authenticate()
        
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_authentication_invalid_response_format(self, mock_post, auth):
        """Test authentication failure with invalid response format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {}  # Missing 'self' key
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(AuthenticationError, match="Authentication failed: Invalid response format"):
            auth.authenticate()
        
        assert not auth.is_authenticated()


class TestMeetupAuthHeaders:
    """Test MeetupAuth header management."""
    
    @pytest.fixture
    def auth(self):
        """Create MeetupAuth instance for testing."""
        return MeetupAuth("test_api_key", "test_oauth_token")
    
    def test_get_auth_headers_not_authenticated(self, auth):
        """Test getting headers when not authenticated."""
        with pytest.raises(AuthenticationError, match="Not authenticated. Call authenticate\\(\\) first."):
            auth.get_auth_headers()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_get_auth_headers_authenticated(self, mock_post, auth):
        """Test getting headers when authenticated."""
        # Mock successful authentication
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'self': {
                    'id': '12345',
                    'name': 'Test User'
                }
            }
        }
        mock_post.return_value = mock_response
        
        auth.authenticate()
        headers = auth.get_auth_headers()
        
        expected_headers = {
            'Authorization': 'Bearer test_oauth_token',
            'Content-Type': 'application/json',
            'User-Agent': 'MeetupRSVPFetcher/1.0'
        }
        
        assert headers == expected_headers
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_get_auth_headers_returns_copy(self, mock_post, auth):
        """Test that get_auth_headers returns a copy of headers."""
        # Mock successful authentication
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'self': {
                    'id': '12345',
                    'name': 'Test User'
                }
            }
        }
        mock_post.return_value = mock_response
        
        auth.authenticate()
        headers1 = auth.get_auth_headers()
        headers2 = auth.get_auth_headers()
        
        # Modify one copy
        headers1['Modified'] = 'True'
        
        # Verify the other copy is not affected
        assert 'Modified' not in headers2
        assert headers1 is not headers2


class TestMeetupAuthState:
    """Test MeetupAuth state management."""
    
    @pytest.fixture
    def auth(self):
        """Create MeetupAuth instance for testing."""
        return MeetupAuth("test_api_key", "test_oauth_token")
    
    def test_is_authenticated_initial_state(self, auth):
        """Test initial authentication state."""
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_is_authenticated_after_success(self, mock_post, auth):
        """Test authentication state after successful authentication."""
        # Mock successful authentication
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'self': {
                    'id': '12345',
                    'name': 'Test User'
                }
            }
        }
        mock_post.return_value = mock_response
        
        auth.authenticate()
        assert auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_is_authenticated_after_failure(self, mock_post, auth):
        """Test authentication state after failed authentication."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        with pytest.raises(AuthenticationError):
            auth.authenticate()
        
        assert not auth.is_authenticated()
    
    @patch('meetup_rsvp_fetcher.auth.meetup_auth.requests.post')
    def test_reset_authentication(self, mock_post, auth):
        """Test resetting authentication state."""
        # Mock successful authentication
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'self': {
                    'id': '12345',
                    'name': 'Test User'
                }
            }
        }
        mock_post.return_value = mock_response
        
        # Authenticate first
        auth.authenticate()
        assert auth.is_authenticated()
        
        # Reset authentication
        auth.reset_authentication()
        assert not auth.is_authenticated()
        
        # Should not be able to get headers after reset
        with pytest.raises(AuthenticationError):
            auth.get_auth_headers()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])