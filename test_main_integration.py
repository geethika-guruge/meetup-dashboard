"""
Integration tests for the MeetupRSVPFetcher main application orchestrator.

These tests verify the complete workflow from configuration through
data fetching, processing, and output formatting.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from io import StringIO
import sys

from meetup_rsvp_fetcher.main import MeetupRSVPFetcher, MeetupRSVPFetcherError
from meetup_rsvp_fetcher.config.config_manager import ConfigManager, ConfigurationError
from meetup_rsvp_fetcher.auth.meetup_auth import MeetupAuth, AuthenticationError
from meetup_rsvp_fetcher.api.graphql_client import MeetupGraphQLClient, GraphQLError
from meetup_rsvp_fetcher.models.data_models import Event, RSVP, Venue, Summary, RSVPStatus


class TestMeetupRSVPFetcherIntegration:
    """Integration tests for the complete MeetupRSVPFetcher workflow."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock ConfigManager for testing."""
        config_manager = Mock(spec=ConfigManager)
        config_manager.load_config.return_value = Mock(
            api_key="test_api_key",
            oauth_token="test_oauth_token",
            network_id="test_network",
            base_url="https://api.meetup.com/gql",
            timeout=30,
            max_retries=3,
            rate_limit_delay=1.0
        )
        config_manager.get_api_credentials.return_value = ("test_api_key", "test_oauth_token")
        config_manager.get_network_id.return_value = "test_network"
        return config_manager
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Create a mock MeetupAuth for testing."""
        auth_manager = Mock(spec=MeetupAuth)
        auth_manager.authenticate.return_value = True
        auth_manager.is_authenticated.return_value = True
        auth_manager.get_auth_headers.return_value = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }
        return auth_manager
    
    @pytest.fixture
    def mock_graphql_client(self):
        """Create a mock MeetupGraphQLClient for testing."""
        client = Mock(spec=MeetupGraphQLClient)
        
        # Mock network events response
        client.fetch_network_events.return_value = [
            {
                'id': 'event1',
                'title': 'Test Event 1',
                'description': 'First test event',
                'dateTime': '2024-01-15T19:00:00Z',
                'group': {
                    'id': 'group1',
                    'name': 'Test Group 1',
                    'urlname': 'test-group-1'
                },
                'venue': {
                    'name': 'Test Venue',
                    'address': '123 Test St',
                    'city': 'Test City',
                    'state': 'TS'
                },
                'maxTickets': 50
            },
            {
                'id': 'event2',
                'title': 'Test Event 2',
                'description': 'Second test event',
                'dateTime': '2024-01-20T18:30:00Z',
                'group': {
                    'id': 'group2',
                    'name': 'Test Group 2',
                    'urlname': 'test-group-2'
                },
                'venue': None,
                'maxTickets': None
            }
        ]
        
        # Mock RSVP responses
        def mock_fetch_rsvps(event_id):
            if event_id == 'event1':
                return [
                    {
                        'id': 'rsvp1',
                        'response': 'yes',
                        'created': '2024-01-10T10:00:00Z',
                        'guests': 1,
                        'member': {
                            'id': 'member1',
                            'name': 'John Doe'
                        }
                    },
                    {
                        'id': 'rsvp2',
                        'response': 'no',
                        'created': '2024-01-11T15:30:00Z',
                        'guests': 0,
                        'member': {
                            'id': 'member2',
                            'name': 'Jane Smith'
                        }
                    }
                ]
            elif event_id == 'event2':
                return [
                    {
                        'id': 'rsvp3',
                        'response': 'yes',
                        'created': '2024-01-12T09:15:00Z',
                        'guests': 0,
                        'member': {
                            'id': 'member3',
                            'name': 'Bob Johnson'
                        }
                    }
                ]
            return []
        
        client.fetch_event_rsvps.side_effect = mock_fetch_rsvps
        return client
    
    @pytest.fixture
    def sample_events(self):
        """Create sample Event objects for testing."""
        venue = Venue(
            name="Test Venue",
            address="123 Test St",
            city="Test City",
            state="TS"
        )
        
        rsvp1 = RSVP(
            member_id="member1",
            member_name="John Doe",
            response=RSVPStatus.YES,
            response_time=datetime(2024, 1, 10, 10, 0),
            guests=1
        )
        
        rsvp2 = RSVP(
            member_id="member2",
            member_name="Jane Smith",
            response=RSVPStatus.NO,
            response_time=datetime(2024, 1, 11, 15, 30),
            guests=0
        )
        
        event1 = Event(
            id="event1",
            title="Test Event 1",
            description="First test event",
            date_time=datetime(2024, 1, 15, 19, 0),
            group_name="Test Group 1",
            group_id="group1",
            venue=venue,
            rsvp_limit=50,
            rsvps=[rsvp1, rsvp2]
        )
        
        rsvp3 = RSVP(
            member_id="member3",
            member_name="Bob Johnson",
            response=RSVPStatus.YES,
            response_time=datetime(2024, 1, 12, 9, 15),
            guests=0
        )
        
        event2 = Event(
            id="event2",
            title="Test Event 2",
            description="Second test event",
            date_time=datetime(2024, 1, 20, 18, 30),
            group_name="Test Group 2",
            group_id="group2",
            venue=None,
            rsvp_limit=None,
            rsvps=[rsvp3]
        )
        
        return [event1, event2]
    
    @pytest.fixture
    def sample_summary(self):
        """Create a sample Summary object for testing."""
        return Summary(
            total_events=2,
            total_rsvps=3,
            rsvp_breakdown={
                RSVPStatus.YES: 2,
                RSVPStatus.NO: 1,
                RSVPStatus.WAITLIST: 0
            },
            events_by_group={
                "Test Group 1": 1,
                "Test Group 2": 1
            },
            date_range=(datetime(2024, 1, 15, 19, 0), datetime(2024, 1, 20, 18, 30))
        )
    
    def test_initialization_with_config_manager(self, mock_config_manager):
        """Test MeetupRSVPFetcher initialization with provided ConfigManager."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        assert fetcher.config_manager is mock_config_manager
        assert fetcher.auth_manager is None
        assert fetcher.graphql_client is None
        assert fetcher.data_processor is not None
    
    def test_initialization_without_config_manager(self):
        """Test MeetupRSVPFetcher initialization without ConfigManager."""
        fetcher = MeetupRSVPFetcher()
        
        assert fetcher.config_manager is not None
        assert isinstance(fetcher.config_manager, ConfigManager)
        assert fetcher.auth_manager is None
        assert fetcher.graphql_client is None
        assert fetcher.data_processor is not None
    
    @patch('meetup_rsvp_fetcher.main.MeetupAuth')
    @patch('meetup_rsvp_fetcher.main.MeetupGraphQLClient')
    def test_initialize_components_success(self, mock_graphql_class, mock_auth_class, mock_config_manager, mock_auth_manager, mock_graphql_client):
        """Test successful component initialization."""
        mock_auth_class.return_value = mock_auth_manager
        mock_graphql_class.return_value = mock_graphql_client
        
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        fetcher._initialize_components()
        
        # Verify configuration was loaded
        mock_config_manager.load_config.assert_called_once()
        mock_config_manager.get_api_credentials.assert_called_once()
        
        # Verify authentication was initialized and called
        mock_auth_class.assert_called_once_with("test_api_key", "test_oauth_token")
        mock_auth_manager.authenticate.assert_called_once()
        
        # Verify GraphQL client was initialized
        mock_graphql_class.assert_called_once_with(mock_auth_manager)
        
        assert fetcher.auth_manager is mock_auth_manager
        assert fetcher.graphql_client is mock_graphql_client
    
    @patch('meetup_rsvp_fetcher.main.MeetupAuth')
    def test_initialize_components_config_error(self, mock_auth_class, mock_config_manager):
        """Test component initialization with configuration error."""
        mock_config_manager.load_config.side_effect = ConfigurationError("Missing API key")
        
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        with pytest.raises(ConfigurationError, match="Missing API key"):
            fetcher._initialize_components()
        
        mock_auth_class.assert_not_called()
    
    @patch('meetup_rsvp_fetcher.main.MeetupAuth')
    def test_initialize_components_auth_error(self, mock_auth_class, mock_config_manager, mock_auth_manager):
        """Test component initialization with authentication error."""
        mock_auth_class.return_value = mock_auth_manager
        mock_auth_manager.authenticate.return_value = False
        
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        with pytest.raises(AuthenticationError, match="Failed to authenticate"):
            fetcher._initialize_components()
    
    def test_fetch_all_data_success(self, mock_config_manager, sample_events, sample_summary):
        """Test successful data fetching workflow."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        # Mock the GraphQL client
        mock_client = Mock()
        mock_client.fetch_network_events.return_value = [
            {
                'id': 'event1',
                'title': 'Test Event 1',
                'description': 'First test event',
                'dateTime': '2024-01-15T19:00:00Z',
                'group': {'id': 'group1', 'name': 'Test Group 1'},
                'venue': {'name': 'Test Venue', 'address': '123 Test St', 'city': 'Test City', 'state': 'TS'},
                'maxTickets': 50
            }
        ]
        mock_client.fetch_event_rsvps.return_value = [
            {
                'id': 'rsvp1',
                'response': 'yes',
                'created': '2024-01-10T10:00:00Z',
                'guests': 1,
                'member': {'id': 'member1', 'name': 'John Doe'}
            }
        ]
        
        fetcher.graphql_client = mock_client
        
        events, summary = fetcher.fetch_all_data()
        
        assert len(events) == 1
        assert events[0].title == "Test Event 1"
        assert len(events[0].rsvps) == 1
        assert summary.total_events == 1
        assert summary.total_rsvps == 1
    
    def test_fetch_all_data_no_events(self, mock_config_manager):
        """Test data fetching when no events are found."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        mock_client = Mock()
        mock_client.fetch_network_events.return_value = []
        fetcher.graphql_client = mock_client
        
        events, summary = fetcher.fetch_all_data()
        
        assert len(events) == 0
        assert summary.total_events == 0
        assert summary.total_rsvps == 0
    
    def test_fetch_all_data_graphql_error(self, mock_config_manager):
        """Test data fetching with GraphQL error."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        mock_client = Mock()
        mock_client.fetch_network_events.side_effect = GraphQLError("API error")
        fetcher.graphql_client = mock_client
        
        with pytest.raises(GraphQLError, match="API error"):
            fetcher.fetch_all_data()
    
    def test_fetch_all_data_no_client(self, mock_config_manager):
        """Test data fetching without initialized GraphQL client."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        with pytest.raises(MeetupRSVPFetcherError, match="GraphQL client not initialized"):
            fetcher.fetch_all_data()
    
    def test_fetch_rsvps_for_events_success(self, mock_config_manager):
        """Test successful RSVP fetching for events."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        # Create test events
        event = Event(
            id="event1",
            title="Test Event",
            description="Test description",
            date_time=datetime(2024, 1, 15, 19, 0),
            group_name="Test Group",
            group_id="group1",
            rsvps=[]
        )
        
        # Mock GraphQL client
        mock_client = Mock()
        mock_client.fetch_event_rsvps.return_value = [
            {
                'id': 'rsvp1',
                'response': 'yes',
                'created': '2024-01-10T10:00:00Z',
                'guests': 0,
                'member': {'id': 'member1', 'name': 'John Doe'}
            }
        ]
        fetcher.graphql_client = mock_client
        
        events_with_rsvps = fetcher._fetch_rsvps_for_events([event])
        
        assert len(events_with_rsvps) == 1
        assert len(events_with_rsvps[0].rsvps) == 1
        assert events_with_rsvps[0].rsvps[0].member_name == "John Doe"
    
    def test_fetch_rsvps_for_events_with_errors(self, mock_config_manager, caplog):
        """Test RSVP fetching with some events failing."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        # Create test events
        event1 = Event(
            id="event1",
            title="Test Event 1",
            description="Test description",
            date_time=datetime(2024, 1, 15, 19, 0),
            group_name="Test Group",
            group_id="group1",
            rsvps=[]
        )
        
        event2 = Event(
            id="event2",
            title="Test Event 2",
            description="Test description",
            date_time=datetime(2024, 1, 20, 19, 0),
            group_name="Test Group",
            group_id="group1",
            rsvps=[]
        )
        
        # Mock GraphQL client with one success and one failure
        mock_client = Mock()
        def mock_fetch_rsvps(event_id):
            if event_id == "event1":
                return [{'id': 'rsvp1', 'response': 'yes', 'created': '2024-01-10T10:00:00Z', 'guests': 0, 'member': {'id': 'member1', 'name': 'John Doe'}}]
            else:
                raise GraphQLError("Failed to fetch RSVPs")
        
        mock_client.fetch_event_rsvps.side_effect = mock_fetch_rsvps
        fetcher.graphql_client = mock_client
        
        with caplog.at_level(logging.WARNING):
            events_with_rsvps = fetcher._fetch_rsvps_for_events([event1, event2])
        
        # Both events should be returned, but event2 should have no RSVPs
        assert len(events_with_rsvps) == 2
        assert len(events_with_rsvps[0].rsvps) == 1
        assert len(events_with_rsvps[1].rsvps) == 0
        
        # Check that warning was logged
        assert "Failed to fetch RSVPs for event 'Test Event 2'" in caplog.text
    
    def test_output_results(self, mock_config_manager, sample_events, sample_summary, capsys):
        """Test output formatting and display."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        fetcher.output_results(sample_events, sample_summary)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that summary information is displayed
        assert "MEETUP RSVP FETCHER - COMPREHENSIVE REPORT" in output
        assert "Total Events: 2" in output
        assert "Total RSVPs: 3" in output
        assert "Yes: 2 (66.7%)" in output
        assert "No: 1 (33.3%)" in output
        
        # Check that event details are displayed
        assert "DETAILED EVENT INFORMATION" in output
        assert "Test Event 1" in output
        assert "Test Event 2" in output
        assert "Test Group 1" in output
        assert "Test Group 2" in output
    
    def test_output_results_no_events(self, mock_config_manager, capsys):
        """Test output with no events."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        empty_summary = Summary(
            total_events=0,
            total_rsvps=0,
            rsvp_breakdown={status: 0 for status in RSVPStatus},
            events_by_group={},
            date_range=(datetime.now(), datetime.now())
        )
        
        fetcher.output_results([], empty_summary)
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Total Events: 0" in output
        assert "No events to display." in output
    
    @patch('meetup_rsvp_fetcher.main.MeetupAuth')
    @patch('meetup_rsvp_fetcher.main.MeetupGraphQLClient')
    def test_complete_workflow_success(self, mock_graphql_class, mock_auth_class, mock_config_manager, mock_auth_manager, mock_graphql_client, capsys):
        """Test the complete successful workflow from start to finish."""
        mock_auth_class.return_value = mock_auth_manager
        mock_graphql_class.return_value = mock_graphql_client
        
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        fetcher.run()
        
        # Verify all components were initialized
        mock_config_manager.load_config.assert_called_once()
        mock_auth_manager.authenticate.assert_called_once()
        
        # Verify data was fetched
        mock_graphql_client.fetch_network_events.assert_called_once_with("test_network")
        
        # Verify output was generated
        captured = capsys.readouterr()
        assert "MEETUP RSVP FETCHER - COMPREHENSIVE REPORT" in captured.out
    
    @patch('meetup_rsvp_fetcher.main.MeetupAuth')
    def test_complete_workflow_config_error(self, mock_auth_class, mock_config_manager):
        """Test complete workflow with configuration error."""
        mock_config_manager.load_config.side_effect = ConfigurationError("Missing config")
        
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        with pytest.raises(MeetupRSVPFetcherError, match="Workflow failed: Missing config"):
            fetcher.run()
    
    @patch('meetup_rsvp_fetcher.main.MeetupAuth')
    def test_complete_workflow_auth_error(self, mock_auth_class, mock_config_manager, mock_auth_manager):
        """Test complete workflow with authentication error."""
        mock_auth_class.return_value = mock_auth_manager
        mock_auth_manager.authenticate.side_effect = AuthenticationError("Auth failed")
        
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        with pytest.raises(MeetupRSVPFetcherError, match="Workflow failed: Auth failed"):
            fetcher.run()
    
    def test_cleanup(self, mock_config_manager):
        """Test resource cleanup."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        mock_client = Mock()
        fetcher.graphql_client = mock_client
        
        fetcher._cleanup()
        
        mock_client.close.assert_called_once()
    
    def test_cleanup_with_error(self, mock_config_manager, caplog):
        """Test cleanup with error handling."""
        fetcher = MeetupRSVPFetcher(mock_config_manager)
        
        mock_client = Mock()
        mock_client.close.side_effect = Exception("Cleanup error")
        fetcher.graphql_client = mock_client
        
        with caplog.at_level(logging.WARNING):
            fetcher._cleanup()
        
        assert "Error during cleanup: Cleanup error" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__])