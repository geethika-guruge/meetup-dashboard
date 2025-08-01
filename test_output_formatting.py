"""
Unit tests for output formatting functionality in the Meetup RSVP Fetcher.

This module tests the output_results method and related display methods
to ensure proper formatting and error handling.
"""

import pytest
import io
import sys
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from contextlib import redirect_stdout

from meetup_rsvp_fetcher.main import MeetupRSVPFetcher
from meetup_rsvp_fetcher.models.data_models import Event, RSVP, Venue, Summary, RSVPStatus
from meetup_rsvp_fetcher.config.config_manager import ConfigManager


class TestOutputFormatting:
    """Test cases for output formatting functionality."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager."""
        config_manager = Mock(spec=ConfigManager)
        config_manager.load_config.return_value = {"test": "config"}
        config_manager.get_api_credentials.return_value = ("test_key", "test_token")
        config_manager.get_network_id.return_value = "test_network"
        return config_manager
    
    @pytest.fixture
    def fetcher(self, mock_config_manager):
        """Create a MeetupRSVPFetcher instance for testing."""
        return MeetupRSVPFetcher(config_manager=mock_config_manager)
    
    @pytest.fixture
    def sample_venue(self):
        """Create a sample venue for testing."""
        return Venue(
            name="Test Venue",
            address="123 Test St",
            city="Test City",
            state="TS"
        )
    
    @pytest.fixture
    def sample_rsvps(self):
        """Create sample RSVPs for testing."""
        return [
            RSVP(
                member_id="1",
                member_name="John Doe",
                response=RSVPStatus.YES,
                response_time=datetime(2024, 1, 15, 10, 0),
                guests=1
            ),
            RSVP(
                member_id="2",
                member_name="Jane Smith",
                response=RSVPStatus.YES,
                response_time=datetime(2024, 1, 15, 11, 0),
                guests=0
            ),
            RSVP(
                member_id="3",
                member_name="Bob Wilson",
                response=RSVPStatus.NO,
                response_time=datetime(2024, 1, 15, 12, 0),
                guests=0
            ),
            RSVP(
                member_id="4",
                member_name="Alice Brown",
                response=RSVPStatus.WAITLIST,
                response_time=datetime(2024, 1, 15, 13, 0),
                guests=0
            )
        ]
    
    @pytest.fixture
    def sample_events(self, sample_venue, sample_rsvps):
        """Create sample events for testing."""
        return [
            Event(
                id="event1",
                title="Test Event 1",
                description="This is a test event with a longer description that should be truncated properly when displayed in the output.",
                date_time=datetime(2024, 2, 15, 18, 30),
                group_name="Test Group 1",
                group_id="group1",
                venue=sample_venue,
                rsvp_limit=50,
                rsvps=sample_rsvps
            ),
            Event(
                id="event2",
                title="Test Event 2",
                description="Short description",
                date_time=datetime(2024, 2, 20, 19, 0),
                group_name="Test Group 2",
                group_id="group2",
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            ),
            Event(
                id="event3",
                title="Test Event 3",
                description="",
                date_time=datetime(2024, 2, 25, 20, 0),
                group_name="Test Group 1",
                group_id="group1",
                venue=sample_venue,
                rsvp_limit=25,
                rsvps=sample_rsvps[:2]  # Only yes RSVPs
            )
        ]
    
    @pytest.fixture
    def sample_summary(self):
        """Create a sample summary for testing."""
        return Summary(
            total_events=3,
            total_rsvps=6,
            rsvp_breakdown={
                RSVPStatus.YES: 4,
                RSVPStatus.NO: 1,
                RSVPStatus.WAITLIST: 1
            },
            events_by_group={
                "Test Group 1": 2,
                "Test Group 2": 1
            },
            date_range=(datetime(2024, 2, 15), datetime(2024, 2, 25))
        )
    
    def test_output_results_complete_flow(self, fetcher, sample_events, sample_summary):
        """Test the complete output_results method flow."""
        # Capture stdout
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher.output_results(sample_events, sample_summary)
        
        output = captured_output.getvalue()
        
        # Verify header is displayed
        assert "MEETUP RSVP FETCHER - COMPREHENSIVE REPORT" in output
        assert "Generated on:" in output
        
        # Verify summary statistics are displayed
        assert "SUMMARY STATISTICS" in output
        assert "Total Events: 3" in output
        assert "Total RSVPs: 6" in output
        
        # Verify event details are displayed
        assert "DETAILED EVENT INFORMATION" in output
        assert "Test Event 1" in output
        assert "Test Event 2" in output
        assert "Test Event 3" in output
        
        # Verify top events section
        assert "TOP EVENTS BY RSVP COUNT" in output
        
        # Verify footer is displayed
        assert "REPORT COMPLETED" in output
    
    def test_display_header(self, fetcher):
        """Test the header display functionality."""
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_header()
        
        output = captured_output.getvalue()
        
        assert "MEETUP RSVP FETCHER - COMPREHENSIVE REPORT" in output
        assert "Generated on:" in output
        assert "=" * 80 in output
    
    def test_display_summary_with_data(self, fetcher, sample_summary):
        """Test summary display with complete data."""
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_summary(sample_summary)
        
        output = captured_output.getvalue()
        
        # Check basic statistics
        assert "Total Events: 3" in output
        assert "Total RSVPs: 6" in output
        assert "Date Range: 2024-02-15 to 2024-02-25" in output
        assert "Duration: 10 days" in output
        
        # Check RSVP breakdown
        assert "Yes: 4 (66.7%)" in output
        assert "No: 1 (16.7%)" in output
        assert "Waitlist: 1 (16.7%)" in output
        assert "Attendance Rate: 80.0%" in output
        
        # Check events by group
        assert "Test Group 1: 2 events" in output
        assert "Test Group 2: 1 events" in output
        
        # Check additional statistics
        assert "Average RSVPs per Event: 2.0" in output
        assert "Average Events per Group: 1.5" in output
    
    def test_display_summary_empty_data(self, fetcher):
        """Test summary display with empty data."""
        empty_summary = Summary(
            total_events=0,
            total_rsvps=0,
            rsvp_breakdown={status: 0 for status in RSVPStatus},
            events_by_group={},
            date_range=(None, None)
        )
        
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_summary(empty_summary)
        
        output = captured_output.getvalue()
        
        assert "Total Events: 0" in output
        assert "Total RSVPs: 0" in output
        assert "No RSVP data available" in output
    
    def test_display_events_with_data(self, fetcher, sample_events):
        """Test event display with complete data."""
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_events(sample_events)
        
        output = captured_output.getvalue()
        
        # Check that events are displayed in chronological order
        assert "DETAILED EVENT INFORMATION" in output
        assert "Test Event 1" in output
        assert "Test Event 2" in output
        assert "Test Event 3" in output
        
        # Check event details
        assert "Test Group 1" in output
        assert "Test Group 2" in output
        assert "2024-02-15 18:30 (Thursday)" in output
        assert "Test Venue, 123 Test St, Test City, TS" in output
        assert "Venue: Not specified" in output  # For event without venue
        
        # Check RSVP information
        assert "RSVPs: 4 total" in output
        assert "RSVPs: 0 total" in output  # For event with no RSVPs
        assert "Yes: 2 (50.0%)" in output
        assert "No: 1 (25.0%)" in output
        assert "Waitlist: 1 (25.0%)" in output
        assert "Total Attendees (with guests): 3" in output
        
        # Check RSVP limits and utilization
        assert "RSVP Limit: 50 (Utilization: 8.0%)" in output
        assert "Capacity Used: 4.0%" in output
        
        # Check description truncation
        assert "This is a test event with a longer description that should be truncated" in output
        assert "Short description" in output
    
    def test_display_events_empty_list(self, fetcher):
        """Test event display with empty event list."""
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_events([])
        
        output = captured_output.getvalue()
        
        assert "No events to display" in output
    
    def test_display_rsvp_details(self, fetcher, sample_events):
        """Test RSVP details display for top events."""
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_rsvp_details(sample_events)
        
        output = captured_output.getvalue()
        
        # Should show top events by RSVP count
        assert "TOP EVENTS BY RSVP COUNT" in output
        assert "Test Event 1" in output  # Has 4 RSVPs
        assert "Test Event 3" in output  # Has 2 RSVPs
        # Event 2 has 0 RSVPs so might not be shown
        
        # Check RSVP statistics
        assert "Total RSVPs: 4" in output
        assert "Attending: 2" in output
        assert "Total Attendees (with guests): 3" in output
    
    def test_display_rsvp_details_no_rsvps(self, fetcher):
        """Test RSVP details display when no events have RSVPs."""
        events_no_rsvps = [
            Event(
                id="event1",
                title="Empty Event",
                description="No RSVPs",
                date_time=datetime(2024, 2, 15, 18, 30),
                group_name="Test Group",
                group_id="group1",
                rsvps=[]
            )
        ]
        
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_rsvp_details(events_no_rsvps)
        
        output = captured_output.getvalue()
        
        # Should not display the top events section
        assert "TOP EVENTS BY RSVP COUNT" not in output
    
    def test_display_error_summary_with_errors(self, fetcher):
        """Test error summary display with errors and warnings."""
        # Add some test errors and warnings
        fetcher.errors = [
            "Failed to fetch RSVPs for event 'Test Event': API timeout",
            "Invalid data format in event response"
        ]
        fetcher.warnings = [
            "RSVP fetching completed with 2 failures out of 10 events"
        ]
        
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_error_summary()
        
        output = captured_output.getvalue()
        
        assert "PROCESSING ISSUES SUMMARY" in output
        assert "Warnings (1):" in output
        assert "Errors (2):" in output
        assert "Failed to fetch RSVPs for event 'Test Event': API timeout" in output
        assert "RSVP fetching completed with 2 failures out of 10 events" in output
        assert "Troubleshooting Tips:" in output
        assert "Check your API credentials" in output
    
    def test_display_error_summary_no_errors(self, fetcher):
        """Test error summary display with no errors."""
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_error_summary()
        
        output = captured_output.getvalue()
        
        # Should not display anything when there are no errors
        assert "PROCESSING ISSUES SUMMARY" not in output
    
    def test_display_footer_success(self, fetcher):
        """Test footer display with successful processing."""
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_footer()
        
        output = captured_output.getvalue()
        
        assert "REPORT COMPLETED" in output
        assert "Processing completed successfully with no issues" in output
        assert "For technical support" in output
    
    def test_display_footer_with_issues(self, fetcher):
        """Test footer display with processing issues."""
        fetcher.errors = ["Test error"]
        fetcher.warnings = ["Test warning"]
        
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_footer()
        
        output = captured_output.getvalue()
        
        assert "REPORT COMPLETED" in output
        assert "Processing completed with 2 issues:" in output
        assert "1 warnings" in output
        assert "1 errors" in output
    
    def test_output_results_handles_formatting_errors(self, fetcher, sample_events, sample_summary):
        """Test that output_results handles formatting errors gracefully."""
        # Mock one of the display methods to raise an exception
        with patch.object(fetcher, '_display_summary', side_effect=Exception("Test formatting error")):
            captured_output = io.StringIO()
            
            with redirect_stdout(captured_output):
                fetcher.output_results(sample_events, sample_summary)
            
            output = captured_output.getvalue()
            
            # Should display error message but not crash
            assert "ERROR: Error during output formatting: Test formatting error" in output
            assert "Partial results may have been displayed above" in output
            
            # Error should be tracked
            assert len(fetcher.errors) > 0
            assert "Error during output formatting: Test formatting error" in fetcher.errors
    
    def test_description_truncation_logic(self, fetcher):
        """Test the description truncation logic in event display."""
        # Test event with very long description
        long_event = Event(
            id="long_event",
            title="Long Description Event",
            description="This is a very long description that should be truncated. " * 10,
            date_time=datetime(2024, 2, 15, 18, 30),
            group_name="Test Group",
            group_id="group1",
            rsvps=[]
        )
        
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_events([long_event])
        
        output = captured_output.getvalue()
        
        # Should truncate long descriptions
        assert "..." in output
        # Should not contain the full repeated text
        description_count = output.count("This is a very long description")
        assert description_count < 10  # Much less than the 10 repetitions
    
    def test_events_sorted_by_date(self, fetcher, sample_events):
        """Test that events are displayed in chronological order."""
        # Create events with different dates
        unsorted_events = [
            Event(
                id="event_future",
                title="Future Event",
                description="",
                date_time=datetime(2024, 3, 1, 18, 30),
                group_name="Test Group",
                group_id="group1",
                rsvps=[]
            ),
            Event(
                id="event_past",
                title="Past Event",
                description="",
                date_time=datetime(2024, 1, 1, 18, 30),
                group_name="Test Group",
                group_id="group1",
                rsvps=[]
            ),
            Event(
                id="event_middle",
                title="Middle Event",
                description="",
                date_time=datetime(2024, 2, 1, 18, 30),
                group_name="Test Group",
                group_id="group1",
                rsvps=[]
            )
        ]
        
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_events(unsorted_events)
        
        output = captured_output.getvalue()
        
        # Find positions of event titles in output
        past_pos = output.find("Past Event")
        middle_pos = output.find("Middle Event")
        future_pos = output.find("Future Event")
        
        # Should be in chronological order
        assert past_pos < middle_pos < future_pos
    
    def test_venue_formatting_variations(self, fetcher):
        """Test venue formatting with different venue data combinations."""
        # Test venue with all fields
        full_venue = Venue(name="Full Venue", address="123 Main St", city="Full City", state="FC")
        
        # Test venue without state
        no_state_venue = Venue(name="No State Venue", address="456 Oak Ave", city="No State City", state="")
        
        events = [
            Event(
                id="event1",
                title="Full Venue Event",
                description="",
                date_time=datetime(2024, 2, 15, 18, 30),
                group_name="Test Group",
                group_id="group1",
                venue=full_venue,
                rsvps=[]
            ),
            Event(
                id="event2",
                title="No State Event",
                description="",
                date_time=datetime(2024, 2, 16, 18, 30),
                group_name="Test Group",
                group_id="group1",
                venue=no_state_venue,
                rsvps=[]
            )
        ]
        
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            fetcher._display_events(events)
        
        output = captured_output.getvalue()
        
        # Check venue formatting
        assert "Full Venue, 123 Main St, Full City, FC" in output
        assert "No State Venue, 456 Oak Ave, No State City" in output
        # Should not have trailing comma for missing state
        assert "No State City," not in output


if __name__ == "__main__":
    pytest.main([__file__])