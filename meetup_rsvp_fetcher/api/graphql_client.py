"""
GraphQL client for Meetup API interactions.

This module provides a robust GraphQL client with comprehensive error handling,
retry logic with exponential backoff, and proper logging for all API interactions.
"""
import json
import logging
import time
from typing import Dict, Any, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..auth.meetup_auth import MeetupAuth
from ..utils.retry_utils import (
    RetrySession, RetryConfig, retry_api_call, 
    RateLimitError, APIRetryableError, NetworkRetryableError
)
from ..utils.logging_config import get_logger


class GraphQLError(Exception):
    """Custom exception for GraphQL-related errors."""
    pass


class MeetupGraphQLClient:
    """
    GraphQL client for interacting with the Meetup API.
    
    Provides robust HTTP communication with comprehensive error handling,
    retry logic with exponential backoff, and detailed logging for all API interactions.
    """
    
    GRAPHQL_ENDPOINT = "https://api.meetup.com/gql"
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, auth_manager: MeetupAuth, retry_config: Optional[RetryConfig] = None):
        """
        Initialize the GraphQL client with retry capabilities.
        
        Args:
            auth_manager: Authentication manager instance for API credentials
            retry_config: Optional retry configuration (uses defaults if None)
        """
        self.auth_manager = auth_manager
        self.logger = get_logger(__name__)
        
        # Set up retry configuration
        self.retry_config = retry_config or RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True
        )
        
        # Initialize retry session
        self.retry_session = RetrySession(
            config=self.retry_config,
            logger=self.logger
        )
        
        self.logger.info(f"GraphQL client initialized with retry config: {self.retry_config}")
        
        # Track API call statistics
        self._api_call_count = 0
        self._failed_call_count = 0
    
    def get_api_stats(self) -> Dict[str, int]:
        """
        Get API call statistics.
        
        Returns:
            Dictionary with API call statistics
        """
        return {
            'total_calls': self._api_call_count,
            'failed_calls': self._failed_call_count,
            'success_rate': (
                (self._api_call_count - self._failed_call_count) / self._api_call_count * 100
                if self._api_call_count > 0 else 0
            )
        }
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for GraphQL requests.
        
        Returns:
            Dictionary of HTTP headers including authentication
            
        Raises:
            GraphQLError: If authentication headers cannot be obtained
        """
        try:
            auth_headers = self.auth_manager.get_auth_headers()
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                **auth_headers
            }
            return headers
        except Exception as e:
            self.logger.error(f"Failed to get authentication headers: {e}")
            raise GraphQLError(f"Authentication error: {e}")
    
    @retry_api_call(max_attempts=3, base_delay=1.0, max_delay=60.0)
    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the Meetup API with retry logic.
        
        This method includes comprehensive error handling and automatic retries
        for transient failures, rate limiting, and network issues.
        
        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Dictionary containing the GraphQL response data
            
        Raises:
            GraphQLError: If the query execution fails after all retries
        """
        if variables is None:
            variables = {}
        
        # Track API call
        self._api_call_count += 1
        
        payload = {
            "query": query,
            "variables": variables
        }
        
        headers = self._get_headers()
        
        self.logger.debug(f"Executing GraphQL query (attempt {self._api_call_count}) with variables: {variables}")
        
        try:
            # Use retry session for robust HTTP communication
            response = self.retry_session.post(
                self.GRAPHQL_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            # Log response details for debugging
            self.logger.debug(f"GraphQL response status: {response.status_code}")
            
            # Handle authentication errors (don't retry)
            if response.status_code == 401:
                self._failed_call_count += 1
                raise GraphQLError("Authentication failed - invalid credentials")
            
            # Handle client errors (don't retry)
            if 400 <= response.status_code < 500 and response.status_code != 429:
                self._failed_call_count += 1
                raise GraphQLError(f"Client error {response.status_code}: {response.text}")
            
            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                self._failed_call_count += 1
                raise GraphQLError(f"Invalid JSON response: {e}")
            
            # Check for GraphQL errors
            if "errors" in data:
                error_messages = [error.get("message", "Unknown error") for error in data["errors"]]
                error_msg = "; ".join(error_messages)
                self.logger.error(f"GraphQL errors: {error_msg}")
                
                # Some GraphQL errors might be retryable (e.g., temporary server issues)
                # Check if any error indicates a server problem
                server_error_keywords = ['server error', 'internal error', 'timeout', 'unavailable']
                is_server_error = any(
                    keyword in error_msg.lower() for keyword in server_error_keywords
                )
                
                if is_server_error:
                    raise APIRetryableError(f"Server-side GraphQL errors: {error_msg}")
                else:
                    self._failed_call_count += 1
                    raise GraphQLError(f"GraphQL errors: {error_msg}")
            
            # Ensure data field exists
            if "data" not in data:
                self._failed_call_count += 1
                raise GraphQLError("Response missing 'data' field")
            
            self.logger.debug("GraphQL query executed successfully")
            return data["data"]
            
        except (RateLimitError, APIRetryableError, NetworkRetryableError):
            # These are retryable errors - let the retry decorator handle them
            raise
        except GraphQLError:
            # GraphQL errors are already handled above
            raise
        except requests.exceptions.Timeout:
            self.logger.error("Request timeout")
            raise NetworkRetryableError("Request timeout")
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error: {e}")
            raise NetworkRetryableError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")
            raise NetworkRetryableError(f"Request error: {e}")
        except Exception as e:
            self._failed_call_count += 1
            self.logger.error(f"Unexpected error in GraphQL query: {e}")
            raise GraphQLError(f"Unexpected error: {e}")
    
    def close(self):
        """Close the HTTP session."""
        if self.retry_session:
            self.retry_session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def fetch_network_events(self, network_id: str) -> list[dict]:
        """
        Fetch all events from a MeetupPro network with pagination handling.
        
        Args:
            network_id: The URL name of the MeetupPro network
            
        Returns:
            List of event dictionaries containing event data
            
        Raises:
            GraphQLError: If the query execution fails or network is not found
        """
        query = """
        query GetNetworkEvents($networkId: ID!, $after: String) {
          proNetworkByUrlname(urlname: $networkId) {
            eventsSearch(first: 50, after: $after) {
              pageInfo {
                hasNextPage
                endCursor
              }
              edges {
                node {
                  id
                  title
                  description
                  dateTime
                  group {
                    id
                    name
                    urlname
                  }
                  venue {
                    name
                    address
                    city
                    state
                  }
                  maxTickets
                }
              }
            }
          }
        }
        """
        
        all_events = []
        cursor = None
        page_count = 0
        
        self.logger.info(f"Starting to fetch events for network: {network_id}")
        
        while True:
            page_count += 1
            variables = {"networkId": network_id}
            if cursor:
                variables["after"] = cursor
            
            self.logger.debug(f"Fetching page {page_count} with cursor: {cursor}")
            
            try:
                data = self.execute_query(query, variables)
                
                # Check if network exists
                if not data.get("proNetworkByUrlname"):
                    raise GraphQLError(f"Network '{network_id}' not found or not accessible")
                
                events_search = data["proNetworkByUrlname"]["eventsSearch"]
                
                # Extract events from current page
                events = [edge["node"] for edge in events_search["edges"]]
                all_events.extend(events)
                
                self.logger.debug(f"Fetched {len(events)} events on page {page_count}")
                
                # Check if there are more pages
                page_info = events_search["pageInfo"]
                if not page_info["hasNextPage"]:
                    break
                
                cursor = page_info["endCursor"]
                
                # Add a small delay between requests to be respectful to the API
                time.sleep(0.1)
                
            except GraphQLError as e:
                self.logger.error(f"Failed to fetch events page {page_count}: {e}")
                # Re-raise GraphQL errors as they indicate API issues
                raise
            except Exception as e:
                self.logger.error(f"Unexpected error fetching events page {page_count}: {e}")
                raise GraphQLError(f"Unexpected error during network events fetch: {e}")
        
        self.logger.info(f"Successfully fetched {len(all_events)} events across {page_count} pages")
        return all_events
    
    def fetch_event_rsvps(self, event_id: str) -> list[dict]:
        """
        Fetch all RSVPs for a specific event with pagination handling.
        
        Args:
            event_id: The ID of the event to fetch RSVPs for
            
        Returns:
            List of RSVP dictionaries containing RSVP data
            
        Raises:
            GraphQLError: If the query execution fails or event is not found
        """
        query = """
        query GetEventRSVPs($eventId: ID!, $after: String) {
          event(id: $eventId) {
            id
            title
            rsvps(first: 100, after: $after) {
              pageInfo {
                hasNextPage
                endCursor
              }
              edges {
                node {
                  id
                  response
                  created
                  guests
                  member {
                    id
                    name
                  }
                }
              }
            }
          }
        }
        """
        
        all_rsvps = []
        cursor = None
        page_count = 0
        
        self.logger.info(f"Starting to fetch RSVPs for event: {event_id}")
        
        while True:
            page_count += 1
            variables = {"eventId": event_id}
            if cursor:
                variables["after"] = cursor
            
            self.logger.debug(f"Fetching RSVP page {page_count} with cursor: {cursor}")
            
            try:
                data = self.execute_query(query, variables)
                
                # Check if event exists
                if not data.get("event"):
                    self.logger.warning(f"Event '{event_id}' not found or not accessible")
                    # Return empty list instead of raising error to allow processing to continue
                    return []
                
                event_data = data["event"]
                rsvps_data = event_data.get("rsvps", {})
                
                # Handle case where RSVPs might be None or missing
                if not rsvps_data or not rsvps_data.get("edges"):
                    self.logger.debug(f"No RSVPs found for event {event_id}")
                    break
                
                # Extract RSVPs from current page
                rsvps = [edge["node"] for edge in rsvps_data["edges"]]
                all_rsvps.extend(rsvps)
                
                self.logger.debug(f"Fetched {len(rsvps)} RSVPs on page {page_count}")
                
                # Check if there are more pages
                page_info = rsvps_data.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    break
                
                cursor = page_info.get("endCursor")
                if not cursor:
                    self.logger.warning("No cursor found for next page, stopping pagination")
                    break
                
                # Add a small delay between requests to be respectful to the API
                time.sleep(0.1)
                
            except GraphQLError as e:
                self.logger.error(f"Failed to fetch RSVPs for event {event_id} on page {page_count}: {e}")
                # For individual event RSVP failures, log error but don't re-raise
                # This allows processing to continue for other events
                self.logger.warning(f"Skipping RSVPs for event {event_id} due to error: {e}")
                return []
            except Exception as e:
                self.logger.error(f"Unexpected error fetching RSVPs for event {event_id} on page {page_count}: {e}")
                # Log unexpected errors but continue processing
                self.logger.warning(f"Skipping RSVPs for event {event_id} due to unexpected error: {e}")
                return []
        
        self.logger.info(f"Successfully fetched {len(all_rsvps)} RSVPs for event {event_id} across {page_count} pages")
        return all_rsvps