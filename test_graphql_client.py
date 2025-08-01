"""
Unit tests for MeetupGraphQLClient.
"""
import json
import pytest
import responses
from unittest.mock import Mock, patch
import requests

from meetup_rsvp_fetcher.api.graphql_client import MeetupGraphQLClient, GraphQLError
from meetup_rsvp_fetcher.auth.meetup_auth import MeetupAuth


class TestMeetupGraphQLClient:
    """Test cases for MeetupGraphQLClient."""
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Create a mock authentication manager."""
        auth_manager = Mock(spec=MeetupAuth)
        auth_manager.get_auth_headers.return_value = {
            "Authorization": "Bearer test_token"
        }
        return auth_manager
    
    @pytest.fixture
    def client(self, mock_auth_manager):
        """Create a GraphQL client instance for testing."""
        return MeetupGraphQLClient(mock_auth_manager)
    
    def test_init(self, mock_auth_manager):
        """Test client initialization."""
        client = MeetupGraphQLClient(mock_auth_manager)
        assert client.auth_manager == mock_auth_manager
        assert client.session is not None
        assert client.GRAPHQL_ENDPOINT == "https://api.meetup.com/gql"
    
    def test_get_headers_success(self, client, mock_auth_manager):
        """Test successful header generation."""
        headers = client._get_headers()
        
        expected_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer test_token"
        }
        assert headers == expected_headers
        mock_auth_manager.get_auth_headers.assert_called_once()
    
    def test_get_headers_auth_failure(self, client, mock_auth_manager):
        """Test header generation when authentication fails."""
        mock_auth_manager.get_auth_headers.side_effect = Exception("Auth failed")
        
        with pytest.raises(GraphQLError, match="Authentication error: Auth failed"):
            client._get_headers()
    
    @responses.activate
    def test_execute_query_success(self, client):
        """Test successful GraphQL query execution."""
        # Mock successful response
        mock_response = {
            "data": {
                "user": {
                    "id": "123",
                    "name": "Test User"
                }
            }
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        query = "query { user { id name } }"
        variables = {"userId": "123"}
        
        result = client.execute_query(query, variables)
        
        assert result == mock_response["data"]
        assert len(responses.calls) == 1
        
        # Verify request payload
        request_body = json.loads(responses.calls[0].request.body)
        assert request_body["query"] == query
        assert request_body["variables"] == variables
    
    @responses.activate
    def test_execute_query_no_variables(self, client):
        """Test GraphQL query execution without variables."""
        mock_response = {"data": {"test": "value"}}
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        query = "query { test }"
        result = client.execute_query(query)
        
        assert result == mock_response["data"]
        
        # Verify empty variables were sent
        request_body = json.loads(responses.calls[0].request.body)
        assert request_body["variables"] == {}
    
    @responses.activate
    def test_execute_query_graphql_errors(self, client):
        """Test handling of GraphQL errors in response."""
        mock_response = {
            "errors": [
                {"message": "Field 'invalid' doesn't exist"},
                {"message": "Another error"}
            ]
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        query = "query { invalid }"
        
        with pytest.raises(GraphQLError, match="GraphQL errors: Field 'invalid' doesn't exist; Another error"):
            client.execute_query(query)
    
    @responses.activate
    def test_execute_query_http_401(self, client):
        """Test handling of 401 authentication error."""
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            status=401
        )
        
        query = "query { test }"
        
        with pytest.raises(GraphQLError, match="Authentication failed - invalid credentials"):
            client.execute_query(query)
    
    @responses.activate
    def test_execute_query_http_429(self, client):
        """Test handling of 429 rate limit error."""
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            status=429
        )
        
        query = "query { test }"
        
        with pytest.raises(GraphQLError, match="Rate limit exceeded - too many requests"):
            client.execute_query(query)
    
    @responses.activate
    def test_execute_query_http_500(self, client):
        """Test handling of 500 server error after retries are exhausted."""
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            body="Internal Server Error",
            status=500
        )
        
        query = "query { test }"
        
        # The client will retry 500 errors, so we expect a request error after retries are exhausted
        with pytest.raises(GraphQLError, match="Request error"):
            client.execute_query(query)
    
    @responses.activate
    def test_execute_query_invalid_json(self, client):
        """Test handling of invalid JSON response."""
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            body="invalid json",
            status=200
        )
        
        query = "query { test }"
        
        with pytest.raises(GraphQLError, match="Invalid JSON response"):
            client.execute_query(query)
    
    @responses.activate
    def test_execute_query_missing_data_field(self, client):
        """Test handling of response missing data field."""
        mock_response = {"something": "else"}
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        query = "query { test }"
        
        with pytest.raises(GraphQLError, match="Response missing 'data' field"):
            client.execute_query(query)
    
    def test_execute_query_timeout(self, client):
        """Test handling of request timeout."""
        with patch.object(client.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()
            
            query = "query { test }"
            
            with pytest.raises(GraphQLError, match="Request timeout"):
                client.execute_query(query)
    
    def test_execute_query_connection_error(self, client):
        """Test handling of connection error."""
        with patch.object(client.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            query = "query { test }"
            
            with pytest.raises(GraphQLError, match="Connection error: Connection failed"):
                client.execute_query(query)
    
    def test_execute_query_request_exception(self, client):
        """Test handling of general request exception."""
        with patch.object(client.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException("Request failed")
            
            query = "query { test }"
            
            with pytest.raises(GraphQLError, match="Request error: Request failed"):
                client.execute_query(query)
    
    def test_close(self, client):
        """Test session cleanup."""
        mock_session = Mock()
        client.session = mock_session
        
        client.close()
        mock_session.close.assert_called_once()
    
    def test_context_manager(self, mock_auth_manager):
        """Test context manager functionality."""
        with MeetupGraphQLClient(mock_auth_manager) as client:
            assert client is not None
            mock_session = Mock()
            client.session = mock_session
        
        # Session should be closed after exiting context
        mock_session.close.assert_called_once()
    
    def test_session_setup_retry_configuration(self, client):
        """Test that session is configured with proper retry strategy."""
        session = client.session
        
        # Check that adapters are mounted
        assert 'http://' in session.adapters
        assert 'https://' in session.adapters
        
        # Verify adapter configuration
        adapter = session.adapters['https://']
        assert isinstance(adapter, requests.adapters.HTTPAdapter)
    
    @responses.activate
    def test_execute_query_with_retry_on_500(self, client):
        """Test that retries work for 500 errors."""
        # First call returns 500, second call succeeds
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            status=500
        )
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json={"data": {"test": "success"}},
            status=200
        )
        
        query = "query { test }"
        result = client.execute_query(query)
        
        assert result == {"test": "success"}
        assert len(responses.calls) == 2


class TestFetchNetworkEvents:
    """Test cases for fetch_network_events method."""
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Create a mock authentication manager."""
        auth_manager = Mock(spec=MeetupAuth)
        auth_manager.get_auth_headers.return_value = {
            "Authorization": "Bearer test_token"
        }
        return auth_manager
    
    @pytest.fixture
    def client(self, mock_auth_manager):
        """Create a GraphQL client instance for testing."""
        return MeetupGraphQLClient(mock_auth_manager)
    
    def create_mock_event(self, event_id: str, title: str = "Test Event") -> dict:
        """Helper to create mock event data."""
        return {
            "id": event_id,
            "title": title,
            "description": "Test event description",
            "dateTime": "2024-01-15T19:00:00-08:00",
            "group": {
                "id": "group123",
                "name": "Test Group",
                "urlname": "test-group"
            },
            "venue": {
                "name": "Test Venue",
                "address": "123 Test St",
                "city": "Test City",
                "state": "CA"
            },
            "maxTickets": 50
        }
    
    def create_mock_response(self, events: list, has_next_page: bool = False, end_cursor: str = None) -> dict:
        """Helper to create mock GraphQL response."""
        return {
            "data": {
                "proNetworkByUrlname": {
                    "eventsSearch": {
                        "pageInfo": {
                            "hasNextPage": has_next_page,
                            "endCursor": end_cursor
                        },
                        "edges": [{"node": event} for event in events]
                    }
                }
            }
        }
    
    @responses.activate
    def test_fetch_network_events_single_page(self, client):
        """Test fetching network events with single page of results."""
        network_id = "test-network"
        events = [
            self.create_mock_event("event1", "Event 1"),
            self.create_mock_event("event2", "Event 2")
        ]
        
        mock_response = self.create_mock_response(events, has_next_page=False)
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_network_events(network_id)
        
        assert len(result) == 2
        assert result[0]["id"] == "event1"
        assert result[0]["title"] == "Event 1"
        assert result[1]["id"] == "event2"
        assert result[1]["title"] == "Event 2"
        
        # Verify the GraphQL query was called correctly
        assert len(responses.calls) == 1
        request_body = json.loads(responses.calls[0].request.body)
        assert "GetNetworkEvents" in request_body["query"]
        assert request_body["variables"]["networkId"] == network_id
        assert "after" not in request_body["variables"]
    
    @responses.activate
    def test_fetch_network_events_multiple_pages(self, client):
        """Test fetching network events with pagination across multiple pages."""
        network_id = "test-network"
        
        # First page
        page1_events = [self.create_mock_event("event1", "Event 1")]
        page1_response = self.create_mock_response(
            page1_events, 
            has_next_page=True, 
            end_cursor="cursor1"
        )
        
        # Second page
        page2_events = [self.create_mock_event("event2", "Event 2")]
        page2_response = self.create_mock_response(
            page2_events, 
            has_next_page=True, 
            end_cursor="cursor2"
        )
        
        # Third page (final)
        page3_events = [self.create_mock_event("event3", "Event 3")]
        page3_response = self.create_mock_response(
            page3_events, 
            has_next_page=False
        )
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=page1_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=page2_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=page3_response,
            status=200
        )
        
        result = client.fetch_network_events(network_id)
        
        assert len(result) == 3
        assert result[0]["id"] == "event1"
        assert result[1]["id"] == "event2"
        assert result[2]["id"] == "event3"
        
        # Verify pagination was handled correctly
        assert len(responses.calls) == 3
        
        # First request should not have cursor
        request1 = json.loads(responses.calls[0].request.body)
        assert "after" not in request1["variables"]
        
        # Second request should have cursor1
        request2 = json.loads(responses.calls[1].request.body)
        assert request2["variables"]["after"] == "cursor1"
        
        # Third request should have cursor2
        request3 = json.loads(responses.calls[2].request.body)
        assert request3["variables"]["after"] == "cursor2"
    
    @responses.activate
    def test_fetch_network_events_empty_results(self, client):
        """Test fetching network events with no events."""
        network_id = "empty-network"
        
        mock_response = self.create_mock_response([], has_next_page=False)
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_network_events(network_id)
        
        assert len(result) == 0
        assert isinstance(result, list)
    
    @responses.activate
    def test_fetch_network_events_network_not_found(self, client):
        """Test handling when network is not found."""
        network_id = "nonexistent-network"
        
        mock_response = {
            "data": {
                "proNetworkByUrlname": None
            }
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        with pytest.raises(GraphQLError, match="Network 'nonexistent-network' not found or not accessible"):
            client.fetch_network_events(network_id)
    
    @responses.activate
    def test_fetch_network_events_graphql_error(self, client):
        """Test handling of GraphQL errors during network events fetch."""
        network_id = "test-network"
        
        mock_response = {
            "errors": [
                {"message": "Network access denied"}
            ]
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        with pytest.raises(GraphQLError, match="GraphQL errors: Network access denied"):
            client.fetch_network_events(network_id)
    
    @responses.activate
    def test_fetch_network_events_http_error(self, client):
        """Test handling of HTTP errors during network events fetch."""
        network_id = "test-network"
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            status=500
        )
        
        with pytest.raises(GraphQLError, match="Request error"):
            client.fetch_network_events(network_id)
    
    @responses.activate
    def test_fetch_network_events_pagination_error_on_second_page(self, client):
        """Test error handling when pagination fails on subsequent pages."""
        network_id = "test-network"
        
        # First page succeeds
        page1_events = [self.create_mock_event("event1", "Event 1")]
        page1_response = self.create_mock_response(
            page1_events, 
            has_next_page=True, 
            end_cursor="cursor1"
        )
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=page1_response,
            status=200
        )
        
        # Second page fails
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            status=500
        )
        
        with pytest.raises(GraphQLError, match="Request error"):
            client.fetch_network_events(network_id)
        
        # Should have made multiple requests due to retries (first successful, then retries on 500)
        assert len(responses.calls) > 1  # At least the first successful call plus retry attempts
    
    @responses.activate
    def test_fetch_network_events_unexpected_error(self, client):
        """Test handling of unexpected errors during network events fetch."""
        network_id = "test-network"
        
        with patch.object(client, 'execute_query') as mock_execute:
            mock_execute.side_effect = ValueError("Unexpected error")
            
            with pytest.raises(GraphQLError, match="Unexpected error during network events fetch: Unexpected error"):
                client.fetch_network_events(network_id)
    
    @responses.activate
    def test_fetch_network_events_large_dataset(self, client):
        """Test fetching a large number of events across many pages."""
        network_id = "large-network"
        
        # Create 5 pages with 10 events each
        for page in range(5):
            events = [
                self.create_mock_event(f"event{page * 10 + i}", f"Event {page * 10 + i}")
                for i in range(10)
            ]
            
            is_last_page = page == 4
            mock_response = self.create_mock_response(
                events,
                has_next_page=not is_last_page,
                end_cursor=f"cursor{page + 1}" if not is_last_page else None
            )
            
            responses.add(
                responses.POST,
                "https://api.meetup.com/gql",
                json=mock_response,
                status=200
            )
        
        result = client.fetch_network_events(network_id)
        
        assert len(result) == 50  # 5 pages * 10 events each
        assert len(responses.calls) == 5
        
        # Verify all events are present and in order
        for i in range(50):
            assert result[i]["id"] == f"event{i}"
            assert result[i]["title"] == f"Event {i}"
    
    @responses.activate
    def test_fetch_network_events_with_null_venue(self, client):
        """Test fetching events where some events have null venue data."""
        network_id = "test-network"
        
        event_with_venue = self.create_mock_event("event1", "Event with Venue")
        event_without_venue = self.create_mock_event("event2", "Event without Venue")
        event_without_venue["venue"] = None
        
        events = [event_with_venue, event_without_venue]
        mock_response = self.create_mock_response(events, has_next_page=False)
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_network_events(network_id)
        
        assert len(result) == 2
        assert result[0]["venue"] is not None
        assert result[1]["venue"] is None
    
    def test_fetch_network_events_query_structure(self, client):
        """Test that the GraphQL query has the correct structure."""
        with patch.object(client, 'execute_query') as mock_execute:
            mock_execute.return_value = {
                "proNetworkByUrlname": {
                    "eventsSearch": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "edges": []
                    }
                }
            }
            
            client.fetch_network_events("test-network")
            
            # Verify the query was called
            assert mock_execute.called
            query, variables = mock_execute.call_args[0]
            
            # Check that query contains expected GraphQL structure
            assert "query GetNetworkEvents" in query
            assert "proNetworkByUrlname(urlname: $networkId)" in query
            assert "eventsSearch(first: 50, after: $after)" in query
            assert "pageInfo" in query
            assert "hasNextPage" in query
            assert "endCursor" in query
            assert "edges" in query
            assert "node" in query
            
            # Check required fields are present
            required_fields = ["id", "title", "description", "dateTime", "group", "venue", "maxTickets"]
            for field in required_fields:
                assert field in query
            
            # Check variables
            assert variables["networkId"] == "test-network"


class TestFetchEventRSVPs:
    """Test cases for fetch_event_rsvps method."""
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Create a mock authentication manager."""
        auth_manager = Mock(spec=MeetupAuth)
        auth_manager.get_auth_headers.return_value = {
            "Authorization": "Bearer test_token"
        }
        return auth_manager
    
    @pytest.fixture
    def client(self, mock_auth_manager):
        """Create a GraphQL client instance for testing."""
        return MeetupGraphQLClient(mock_auth_manager)
    
    def create_mock_rsvp(self, rsvp_id: str, response: str = "yes", member_name: str = "Test Member") -> dict:
        """Helper to create mock RSVP data."""
        return {
            "id": rsvp_id,
            "response": response,
            "created": "2024-01-10T10:00:00-08:00",
            "guests": 0,
            "member": {
                "id": f"member_{rsvp_id}",
                "name": member_name
            }
        }
    
    def create_mock_rsvp_response(self, event_id: str, rsvps: list, has_next_page: bool = False, end_cursor: str = None) -> dict:
        """Helper to create mock GraphQL response for RSVPs."""
        return {
            "data": {
                "event": {
                    "id": event_id,
                    "title": "Test Event",
                    "rsvps": {
                        "pageInfo": {
                            "hasNextPage": has_next_page,
                            "endCursor": end_cursor
                        },
                        "edges": [{"node": rsvp} for rsvp in rsvps]
                    }
                }
            }
        }
    
    @responses.activate
    def test_fetch_event_rsvps_single_page(self, client):
        """Test fetching event RSVPs with single page of results."""
        event_id = "event123"
        rsvps = [
            self.create_mock_rsvp("rsvp1", "yes", "Alice"),
            self.create_mock_rsvp("rsvp2", "no", "Bob"),
            self.create_mock_rsvp("rsvp3", "waitlist", "Charlie")
        ]
        
        mock_response = self.create_mock_rsvp_response(event_id, rsvps, has_next_page=False)
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_event_rsvps(event_id)
        
        assert len(result) == 3
        assert result[0]["id"] == "rsvp1"
        assert result[0]["response"] == "yes"
        assert result[0]["member"]["name"] == "Alice"
        assert result[1]["response"] == "no"
        assert result[2]["response"] == "waitlist"
        
        # Verify the GraphQL query was called correctly
        assert len(responses.calls) == 1
        request_body = json.loads(responses.calls[0].request.body)
        assert "GetEventRSVPs" in request_body["query"]
        assert request_body["variables"]["eventId"] == event_id
        assert "after" not in request_body["variables"]
    
    @responses.activate
    def test_fetch_event_rsvps_multiple_pages(self, client):
        """Test fetching event RSVPs with pagination across multiple pages."""
        event_id = "event123"
        
        # First page
        page1_rsvps = [self.create_mock_rsvp("rsvp1", "yes", "Alice")]
        page1_response = self.create_mock_rsvp_response(
            event_id, page1_rsvps, has_next_page=True, end_cursor="cursor1"
        )
        
        # Second page
        page2_rsvps = [self.create_mock_rsvp("rsvp2", "no", "Bob")]
        page2_response = self.create_mock_rsvp_response(
            event_id, page2_rsvps, has_next_page=True, end_cursor="cursor2"
        )
        
        # Third page (final)
        page3_rsvps = [self.create_mock_rsvp("rsvp3", "waitlist", "Charlie")]
        page3_response = self.create_mock_rsvp_response(
            event_id, page3_rsvps, has_next_page=False
        )
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=page1_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=page2_response,
            status=200
        )
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=page3_response,
            status=200
        )
        
        result = client.fetch_event_rsvps(event_id)
        
        assert len(result) == 3
        assert result[0]["id"] == "rsvp1"
        assert result[1]["id"] == "rsvp2"
        assert result[2]["id"] == "rsvp3"
        
        # Verify pagination was handled correctly
        assert len(responses.calls) == 3
        
        # First request should not have cursor
        request1 = json.loads(responses.calls[0].request.body)
        assert "after" not in request1["variables"]
        
        # Second request should have cursor1
        request2 = json.loads(responses.calls[1].request.body)
        assert request2["variables"]["after"] == "cursor1"
        
        # Third request should have cursor2
        request3 = json.loads(responses.calls[2].request.body)
        assert request3["variables"]["after"] == "cursor2"
    
    @responses.activate
    def test_fetch_event_rsvps_empty_results(self, client):
        """Test fetching event RSVPs with no RSVPs."""
        event_id = "event123"
        
        mock_response = self.create_mock_rsvp_response(event_id, [], has_next_page=False)
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_event_rsvps(event_id)
        
        assert len(result) == 0
        assert isinstance(result, list)
    
    @responses.activate
    def test_fetch_event_rsvps_event_not_found(self, client):
        """Test handling when event is not found."""
        event_id = "nonexistent-event"
        
        mock_response = {
            "data": {
                "event": None
            }
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        # Should return empty list instead of raising error to allow processing to continue
        result = client.fetch_event_rsvps(event_id)
        assert result == []
    
    @responses.activate
    def test_fetch_event_rsvps_no_rsvps_field(self, client):
        """Test handling when event exists but has no RSVPs field."""
        event_id = "event123"
        
        mock_response = {
            "data": {
                "event": {
                    "id": event_id,
                    "title": "Test Event"
                    # Missing rsvps field
                }
            }
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_event_rsvps(event_id)
        assert result == []
    
    @responses.activate
    def test_fetch_event_rsvps_null_rsvps(self, client):
        """Test handling when event has null RSVPs."""
        event_id = "event123"
        
        mock_response = {
            "data": {
                "event": {
                    "id": event_id,
                    "title": "Test Event",
                    "rsvps": None
                }
            }
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_event_rsvps(event_id)
        assert result == []
    
    @responses.activate
    def test_fetch_event_rsvps_empty_edges(self, client):
        """Test handling when RSVPs field exists but edges is empty."""
        event_id = "event123"
        
        mock_response = {
            "data": {
                "event": {
                    "id": event_id,
                    "title": "Test Event",
                    "rsvps": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "edges": []
                    }
                }
            }
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_event_rsvps(event_id)
        assert result == []
    
    @responses.activate
    def test_fetch_event_rsvps_graphql_error(self, client):
        """Test handling of GraphQL errors during RSVP fetch."""
        event_id = "event123"
        
        mock_response = {
            "errors": [
                {"message": "Event access denied"}
            ]
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        # Should return empty list instead of raising error to allow processing to continue
        result = client.fetch_event_rsvps(event_id)
        assert result == []
    
    @responses.activate
    def test_fetch_event_rsvps_http_error(self, client):
        """Test handling of HTTP errors during RSVP fetch."""
        event_id = "event123"
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            status=500
        )
        
        # Should return empty list instead of raising error to allow processing to continue
        result = client.fetch_event_rsvps(event_id)
        assert result == []
    
    @responses.activate
    def test_fetch_event_rsvps_pagination_error_on_second_page(self, client):
        """Test error handling when pagination fails on subsequent pages."""
        event_id = "event123"
        
        # First page succeeds
        page1_rsvps = [self.create_mock_rsvp("rsvp1", "yes", "Alice")]
        page1_response = self.create_mock_rsvp_response(
            event_id, page1_rsvps, has_next_page=True, end_cursor="cursor1"
        )
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=page1_response,
            status=200
        )
        
        # Second page fails
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            status=500
        )
        
        # Should return empty list instead of raising error
        result = client.fetch_event_rsvps(event_id)
        assert result == []
    
    @responses.activate
    def test_fetch_event_rsvps_unexpected_error(self, client):
        """Test handling of unexpected errors during RSVP fetch."""
        event_id = "event123"
        
        with patch.object(client, 'execute_query') as mock_execute:
            mock_execute.side_effect = ValueError("Unexpected error")
            
            # Should return empty list instead of raising error
            result = client.fetch_event_rsvps(event_id)
            assert result == []
    
    @responses.activate
    def test_fetch_event_rsvps_with_guests(self, client):
        """Test fetching RSVPs that include guest counts."""
        event_id = "event123"
        
        rsvps = [
            {
                "id": "rsvp1",
                "response": "yes",
                "created": "2024-01-10T10:00:00-08:00",
                "guests": 2,  # RSVP with guests
                "member": {"id": "member1", "name": "Alice"}
            },
            {
                "id": "rsvp2",
                "response": "yes",
                "created": "2024-01-10T11:00:00-08:00",
                "guests": 0,  # RSVP without guests
                "member": {"id": "member2", "name": "Bob"}
            }
        ]
        
        mock_response = self.create_mock_rsvp_response(event_id, rsvps, has_next_page=False)
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_event_rsvps(event_id)
        
        assert len(result) == 2
        assert result[0]["guests"] == 2
        assert result[1]["guests"] == 0
    
    @responses.activate
    def test_fetch_event_rsvps_different_response_types(self, client):
        """Test fetching RSVPs with different response types."""
        event_id = "event123"
        
        rsvps = [
            self.create_mock_rsvp("rsvp1", "yes", "Alice"),
            self.create_mock_rsvp("rsvp2", "no", "Bob"),
            self.create_mock_rsvp("rsvp3", "waitlist", "Charlie")
        ]
        
        mock_response = self.create_mock_rsvp_response(event_id, rsvps, has_next_page=False)
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_event_rsvps(event_id)
        
        assert len(result) == 3
        responses_found = {rsvp["response"] for rsvp in result}
        assert responses_found == {"yes", "no", "waitlist"}
    
    @responses.activate
    def test_fetch_event_rsvps_missing_cursor_on_pagination(self, client):
        """Test handling when cursor is missing during pagination."""
        event_id = "event123"
        
        # First page with hasNextPage=True but no endCursor
        page1_rsvps = [self.create_mock_rsvp("rsvp1", "yes", "Alice")]
        mock_response = {
            "data": {
                "event": {
                    "id": event_id,
                    "title": "Test Event",
                    "rsvps": {
                        "pageInfo": {
                            "hasNextPage": True,
                            "endCursor": None  # Missing cursor
                        },
                        "edges": [{"node": rsvp} for rsvp in page1_rsvps]
                    }
                }
            }
        }
        
        responses.add(
            responses.POST,
            "https://api.meetup.com/gql",
            json=mock_response,
            status=200
        )
        
        result = client.fetch_event_rsvps(event_id)
        
        # Should return the first page results and stop pagination
        assert len(result) == 1
        assert result[0]["id"] == "rsvp1"
        assert len(responses.calls) == 1
    
    @responses.activate
    def test_fetch_event_rsvps_large_dataset(self, client):
        """Test fetching a large number of RSVPs across many pages."""
        event_id = "event123"
        
        # Create 3 pages with different numbers of RSVPs
        page_sizes = [100, 50, 25]  # Simulating decreasing page sizes
        all_expected_ids = []
        
        for page, size in enumerate(page_sizes):
            page_rsvp_ids = []
            rsvps = []
            for i in range(size):
                rsvp_id = f"rsvp{page}_{i}"  # Use page-based numbering
                page_rsvp_ids.append(rsvp_id)
                rsvps.append(self.create_mock_rsvp(rsvp_id, "yes", f"Member {page}_{i}"))
            
            all_expected_ids.extend(page_rsvp_ids)
            
            is_last_page = page == len(page_sizes) - 1
            mock_response = self.create_mock_rsvp_response(
                event_id,
                rsvps,
                has_next_page=not is_last_page,
                end_cursor=f"cursor{page + 1}" if not is_last_page else None
            )
            
            responses.add(
                responses.POST,
                "https://api.meetup.com/gql",
                json=mock_response,
                status=200
            )
        
        result = client.fetch_event_rsvps(event_id)
        
        expected_total = sum(page_sizes)  # 100 + 50 + 25 = 175
        assert len(result) == expected_total
        assert len(responses.calls) == 3
        
        # Verify all RSVPs are present
        result_ids = {rsvp["id"] for rsvp in result}
        expected_ids = set(all_expected_ids)
        assert result_ids == expected_ids, f"Missing RSVPs: {expected_ids - result_ids}"
    
    def test_fetch_event_rsvps_query_structure(self, client):
        """Test that the GraphQL query has the correct structure."""
        with patch.object(client, 'execute_query') as mock_execute:
            mock_execute.return_value = {
                "event": {
                    "id": "event123",
                    "title": "Test Event",
                    "rsvps": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "edges": []
                    }
                }
            }
            
            client.fetch_event_rsvps("event123")
            
            # Verify the query was called
            assert mock_execute.called
            query, variables = mock_execute.call_args[0]
            
            # Check that query contains expected GraphQL structure
            assert "query GetEventRSVPs" in query
            assert "event(id: $eventId)" in query
            assert "rsvps(first: 100, after: $after)" in query
            assert "pageInfo" in query
            assert "hasNextPage" in query
            assert "endCursor" in query
            assert "edges" in query
            assert "node" in query
            
            # Check required RSVP fields are present
            required_fields = ["id", "response", "created", "guests", "member"]
            for field in required_fields:
                assert field in query
            
            # Check member fields
            assert "member" in query
            assert "id" in query  # member.id
            assert "name" in query  # member.name
            
            # Check variables
            assert variables["eventId"] == "event123"