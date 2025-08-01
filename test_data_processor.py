"""
Unit tests for the EventDataProcessor class.

Tests cover data transformation, validation, error handling, and edge cases
for processing Meetup API data into structured models.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from meetup_rsvp_fetcher.processors.data_processor import EventDataProcessor
from meetup_rsvp_fetcher.models.data_models import Event, RSVP, Venue, Summary, RSVPStatus


class TestEventDataProcessor:
    """Test cases for EventDataProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = EventDataProcessor()
    
    def test_process_events_success(self):
        """Test successful processing of valid event data."""
        raw_events = [
            {
                'id': '123',
                'title': 'Test Event 1',
                'description': 'A test event',
                'dateTime': '2024-01-15T18:00:00Z',
                'group': {
                    'id': 'group1',
                    'name': 'Test Group'
                },
                'venue': {
                    'name': 'Test Venue',
                    'address': '123 Main St',
                    'city': 'Test City',
                    'state': 'TS'
                },
                'maxTickets': 50
            },
            {
                'id': '456',
                'title': 'Test Event 2',
                'description': '',
                'dateTime': '2024-01-20T19:00:00Z',
                'group': {
                    'id': 'group2',
                    'name': 'Another Group'
                }
            }
        ]
        
        events = self.processor.process_events(raw_events)
        
        assert len(events) == 2
        
        # Check first event
        event1 = events[0]
        assert event1.id == '123'
        assert event1.title == 'Test Event 1'
        assert event1.description == 'A test event'
        assert event1.group_name == 'Test Group'
        assert event1.group_id == 'group1'
        assert event1.rsvp_limit == 50
        assert event1.venue is not None
        assert event1.venue.name == 'Test Venue'
        
        # Check second event
        event2 = events[1]
        assert event2.id == '456'
        assert event2.title == 'Test Event 2'
        assert event2.description == ''
        assert event2.venue is None
        assert event2.rsvp_limit is None
    
    def test_process_events_missing_required_fields(self):
        """Test processing events with missing required fields."""
        raw_events = [
            {
                'id': '123',
                'title': 'Valid Event',
                'dateTime': '2024-01-15T18:00:00Z',
                'group': {
                    'id': 'group1',
                    'name': 'Test Group'
                }
            },
            {
                # Missing id
                'title': 'Invalid Event 1',
                'dateTime': '2024-01-15T18:00:00Z',
                'group': {
                    'id': 'group2',
                    'name': 'Test Group'
                }
            },
            {
                'id': '456',
                # Missing title
                'dateTime': '2024-01-15T18:00:00Z',
                'group': {
                    'id': 'group3',
                    'name': 'Test Group'
                }
            },
            {
                'id': '789',
                'title': 'Invalid Event 3',
                # Missing dateTime
                'group': {
                    'id': 'group4',
                    'name': 'Test Group'
                }
            },
            {
                'id': '101',
                'title': 'Invalid Event 4',
                'dateTime': '2024-01-15T18:00:00Z'
                # Missing group (should fail group_id validation)
            }
        ]
        
        with patch.object(self.processor, 'logger') as mock_logger:
            events = self.processor.process_events(raw_events)
        
        # Only the valid event should be processed
        assert len(events) == 1
        assert events[0].id == '123'
        
        # Check that warnings were logged for invalid events
        assert mock_logger.warning.call_count == 4
    
    def test_process_events_invalid_datetime(self):
        """Test processing events with invalid datetime formats."""
        raw_events = [
            {
                'id': '123',
                'title': 'Invalid DateTime Event',
                'dateTime': 'invalid-date-format'
            }
        ]
        
        with patch.object(self.processor, 'logger') as mock_logger:
            events = self.processor.process_events(raw_events)
        
        assert len(events) == 0
        mock_logger.warning.assert_called()
    
    def test_process_venue_success(self):
        """Test successful venue processing."""
        venue_data = {
            'name': 'Test Venue',
            'address': '123 Main St',
            'city': 'Test City',
            'state': 'TS'
        }
        
        venue = self.processor._process_venue(venue_data)
        
        assert venue is not None
        assert venue.name == 'Test Venue'
        assert venue.address == '123 Main St'
        assert venue.city == 'Test City'
        assert venue.state == 'TS'
    
    def test_process_venue_minimal_data(self):
        """Test venue processing with minimal data."""
        venue_data = {
            'name': 'Minimal Venue'
        }
        
        venue = self.processor._process_venue(venue_data)
        
        assert venue is not None
        assert venue.name == 'Minimal Venue'
        assert venue.address == ''
        assert venue.city == 'Unknown City'  # Default value for missing city
        assert venue.state == ''
    
    def test_process_venue_no_name(self):
        """Test venue processing with no name returns None."""
        venue_data = {
            'address': '123 Main St',
            'city': 'Test City'
        }
        
        venue = self.processor._process_venue(venue_data)
        assert venue is None
    
    def test_process_rsvps_success(self):
        """Test successful processing of valid RSVP data."""
        raw_rsvps = [
            {
                'id': 'rsvp1',
                'response': 'yes',
                'created': '2024-01-10T12:00:00Z',
                'guests': 2,
                'member': {
                    'id': 'member1',
                    'name': 'John Doe'
                }
            },
            {
                'id': 'rsvp2',
                'response': 'no',
                'created': '2024-01-11T13:00:00Z',
                'guests': 0,
                'member': {
                    'id': 'member2',
                    'name': 'Jane Smith'
                }
            },
            {
                'id': 'rsvp3',
                'response': 'waitlist',
                'created': '2024-01-12T14:00:00Z',
                'guests': 1,
                'member': {
                    'id': 'member3',
                    'name': 'Bob Johnson'
                }
            }
        ]
        
        rsvps = self.processor.process_rsvps(raw_rsvps)
        
        assert len(rsvps) == 3
        
        # Check first RSVP
        rsvp1 = rsvps[0]
        assert rsvp1.member_id == 'member1'
        assert rsvp1.member_name == 'John Doe'
        assert rsvp1.response == RSVPStatus.YES
        assert rsvp1.guests == 2
        
        # Check second RSVP
        rsvp2 = rsvps[1]
        assert rsvp2.response == RSVPStatus.NO
        assert rsvp2.guests == 0
        
        # Check third RSVP
        rsvp3 = rsvps[2]
        assert rsvp3.response == RSVPStatus.WAITLIST
        assert rsvp3.guests == 1
    
    def test_process_rsvps_missing_required_fields(self):
        """Test processing RSVPs with missing required fields."""
        raw_rsvps = [
            {
                'id': 'rsvp1',
                'response': 'yes',
                'created': '2024-01-10T12:00:00Z',
                'member': {
                    'id': 'member1',
                    'name': 'John Doe'
                }
            },
            {
                'id': 'rsvp2',
                # Missing response
                'created': '2024-01-11T13:00:00Z',
                'member': {
                    'id': 'member2',
                    'name': 'Jane Smith'
                }
            },
            {
                'id': 'rsvp3',
                'response': 'yes',
                'created': '2024-01-12T14:00:00Z',
                'member': {
                    # Missing member id
                    'name': 'Bob Johnson'
                }
            }
        ]
        
        with patch.object(self.processor, 'logger') as mock_logger:
            rsvps = self.processor.process_rsvps(raw_rsvps)
        
        # Only the valid RSVP should be processed
        assert len(rsvps) == 1
        assert rsvps[0].member_id == 'member1'
        
        # Check that warnings were logged for invalid RSVPs
        assert mock_logger.warning.call_count == 2
    
    def test_process_rsvps_unknown_response_type(self):
        """Test processing RSVPs with unknown response types."""
        raw_rsvps = [
            {
                'id': 'rsvp1',
                'response': 'maybe',  # Unknown response type
                'created': '2024-01-10T12:00:00Z',
                'member': {
                    'id': 'member1',
                    'name': 'John Doe'
                }
            }
        ]
        
        with patch.object(self.processor, 'logger') as mock_logger:
            rsvps = self.processor.process_rsvps(raw_rsvps)
        
        assert len(rsvps) == 1
        assert rsvps[0].response == RSVPStatus.NO  # Should default to 'no'
        mock_logger.warning.assert_called()
    
    def test_process_rsvps_invalid_datetime(self):
        """Test processing RSVPs with invalid datetime."""
        raw_rsvps = [
            {
                'id': 'rsvp1',
                'response': 'yes',
                'created': 'invalid-date',
                'member': {
                    'id': 'member1',
                    'name': 'John Doe'
                }
            }
        ]
        
        with patch.object(self.processor, 'logger') as mock_logger:
            rsvps = self.processor.process_rsvps(raw_rsvps)
        
        assert len(rsvps) == 1
        # Should still process the RSVP with current time as fallback
        assert isinstance(rsvps[0].response_time, datetime)
        mock_logger.warning.assert_called()
    
    def test_parse_datetime_various_formats(self):
        """Test datetime parsing with various formats."""
        test_cases = [
            ('2024-01-15T18:00:00Z', datetime(2024, 1, 15, 18, 0, 0)),
            ('2024-01-15T18:00:00', datetime(2024, 1, 15, 18, 0, 0)),
            ('2024-01-15 18:00:00', datetime(2024, 1, 15, 18, 0, 0)),
            ('2024-01-15', datetime(2024, 1, 15, 0, 0, 0)),
        ]
        
        for datetime_str, expected in test_cases:
            result = self.processor._parse_datetime(datetime_str)
            assert result.replace(tzinfo=None) == expected
    
    def test_parse_datetime_timestamp(self):
        """Test datetime parsing from timestamp."""
        timestamp = 1705339200.0  # 2024-01-15 18:00:00 UTC
        result = self.processor._parse_datetime(str(timestamp))
        assert isinstance(result, datetime)
    
    def test_parse_datetime_invalid(self):
        """Test datetime parsing with invalid input."""
        with pytest.raises(ValueError):
            self.processor._parse_datetime('completely-invalid')
        
        with pytest.raises(ValueError):
            self.processor._parse_datetime('')
        
        with pytest.raises(ValueError):
            self.processor._parse_datetime(None)
    
    def test_generate_summary_with_events(self):
        """Test summary generation with events and RSVPs."""
        # Create test events with RSVPs
        events = [
            Event(
                id='1',
                title='Event 1',
                description='',
                date_time=datetime(2024, 1, 15, 18, 0),
                group_name='Group A',
                group_id='group_a',
                venue=None,
                rsvp_limit=None,
                rsvps=[
                    RSVP('m1', 'Member 1', RSVPStatus.YES, datetime.now(), 1),
                    RSVP('m2', 'Member 2', RSVPStatus.NO, datetime.now(), 0),
                ]
            ),
            Event(
                id='2',
                title='Event 2',
                description='',
                date_time=datetime(2024, 1, 20, 19, 0),
                group_name='Group B',
                group_id='group_b',
                venue=None,
                rsvp_limit=None,
                rsvps=[
                    RSVP('m3', 'Member 3', RSVPStatus.YES, datetime.now(), 2),
                    RSVP('m4', 'Member 4', RSVPStatus.WAITLIST, datetime.now(), 0),
                ]
            ),
            Event(
                id='3',
                title='Event 3',
                description='',
                date_time=datetime(2024, 1, 25, 20, 0),
                group_name='Group A',
                group_id='group_a',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            )
        ]
        
        summary = self.processor.generate_summary(events)
        
        assert summary.total_events == 3
        assert summary.total_rsvps == 4
        assert summary.rsvp_breakdown[RSVPStatus.YES] == 2
        assert summary.rsvp_breakdown[RSVPStatus.NO] == 1
        assert summary.rsvp_breakdown[RSVPStatus.WAITLIST] == 1
        assert summary.events_by_group['Group A'] == 2
        assert summary.events_by_group['Group B'] == 1
        assert summary.date_range[0] == datetime(2024, 1, 15, 18, 0)
        assert summary.date_range[1] == datetime(2024, 1, 25, 20, 0)
    
    def test_generate_summary_empty_events(self):
        """Test summary generation with empty events list."""
        summary = self.processor.generate_summary([])
        
        assert summary.total_events == 0
        assert summary.total_rsvps == 0
        assert all(count == 0 for count in summary.rsvp_breakdown.values())
        assert summary.events_by_group == {}
        assert isinstance(summary.date_range[0], datetime)
        assert isinstance(summary.date_range[1], datetime)
    
    def test_generate_summary_events_without_group_names(self):
        """Test summary generation with events that have Unknown Group names."""
        events = [
            Event(
                id='1',
                title='Event 1',
                description='',
                date_time=datetime(2024, 1, 15, 18, 0),
                group_name='Unknown Group',
                group_id='group1',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            ),
            Event(
                id='2',
                title='Event 2',
                description='',
                date_time=datetime(2024, 1, 20, 19, 0),
                group_name='Unknown Group',
                group_id='group2',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            )
        ]
        
        summary = self.processor.generate_summary(events)
        
        assert summary.total_events == 2
        assert summary.events_by_group['Unknown Group'] == 2
    
    def test_data_validation_and_cleaning(self):
        """Test data validation and cleaning functionality."""
        raw_events = [
            {
                'id': '  123  ',  # Test whitespace trimming
                'title': '  Test Event  ',
                'description': '  A test event  ',
                'dateTime': '2024-01-15T18:00:00Z',
                'group': {
                    'id': '  group1  ',
                    'name': '  Test Group  '
                },
                'maxTickets': '50'  # Test string to int conversion
            }
        ]
        
        events = self.processor.process_events(raw_events)
        
        assert len(events) == 1
        event = events[0]
        assert event.id == '123'
        assert event.title == 'Test Event'
        assert event.description == 'A test event'
        assert event.group_id == 'group1'
        assert event.group_name == 'Test Group'
        assert event.rsvp_limit == 50
    
    def test_negative_values_handling(self):
        """Test handling of negative values in data."""
        raw_events = [
            {
                'id': '123',
                'title': 'Test Event',
                'dateTime': '2024-01-15T18:00:00Z',
                'group': {
                    'id': 'group1',
                    'name': 'Test Group'
                },
                'maxTickets': -10  # Negative value should be set to None
            }
        ]
        
        raw_rsvps = [
            {
                'id': 'rsvp1',
                'response': 'yes',
                'created': '2024-01-10T12:00:00Z',
                'guests': -5,  # Negative guests should be set to 0
                'member': {
                    'id': 'member1',
                    'name': 'John Doe'
                }
            }
        ]
        
        events = self.processor.process_events(raw_events)
        rsvps = self.processor.process_rsvps(raw_rsvps)
        
        assert len(events) == 1
        assert events[0].rsvp_limit is None
        assert len(rsvps) == 1
        assert rsvps[0].guests == 0

    def test_generate_summary_large_dataset(self):
        """Test summary generation with a large dataset."""
        events = []
        groups = ['Tech Meetup', 'Design Group', 'Startup Network', 'Data Science Club']
        
        # Create 20 events across 4 groups
        for i in range(20):
            group_name = groups[i % 4]
            event_rsvps = []
            
            # Add varying numbers of RSVPs per event (0-10)
            for j in range(i % 11):
                status = [RSVPStatus.YES, RSVPStatus.NO, RSVPStatus.WAITLIST][j % 3]
                event_rsvps.append(
                    RSVP(f'm{i}_{j}', f'Member {i}_{j}', status, datetime.now(), j % 3)
                )
            
            events.append(Event(
                id=str(i),
                title=f'Event {i}',
                description='',
                date_time=datetime(2024, 1, i + 1, 18, 0),
                group_name=group_name,
                group_id=f'group_{i % 4}',
                venue=None,
                rsvp_limit=None,
                rsvps=event_rsvps
            ))
        
        summary = self.processor.generate_summary(events)
        
        assert summary.total_events == 20
        assert summary.total_rsvps == sum(i % 11 for i in range(20))  # 0+1+2+...+10+0+1+...
        
        # Check that all groups are represented
        assert len(summary.events_by_group) == 4
        for group in groups:
            assert group in summary.events_by_group
            assert summary.events_by_group[group] == 5  # 20 events / 4 groups
        
        # Check RSVP breakdown totals match
        total_breakdown = sum(summary.rsvp_breakdown.values())
        assert total_breakdown == summary.total_rsvps
        
        # Check date range
        assert summary.date_range[0] == datetime(2024, 1, 1, 18, 0)
        assert summary.date_range[1] == datetime(2024, 1, 20, 18, 0)

    def test_generate_summary_single_group_multiple_events(self):
        """Test summary generation with multiple events from a single group."""
        events = [
            Event(
                id=str(i),
                title=f'Event {i}',
                description='',
                date_time=datetime(2024, 1, i + 1, 18, 0),
                group_name='Single Group',
                group_id='single_group',
                venue=None,
                rsvp_limit=None,
                rsvps=[
                    RSVP(f'm{i}_1', f'Member {i}_1', RSVPStatus.YES, datetime.now(), 0),
                    RSVP(f'm{i}_2', f'Member {i}_2', RSVPStatus.NO, datetime.now(), 0),
                ]
            ) for i in range(5)
        ]
        
        summary = self.processor.generate_summary(events)
        
        assert summary.total_events == 5
        assert summary.total_rsvps == 10
        assert summary.events_by_group['Single Group'] == 5
        assert len(summary.events_by_group) == 1
        assert summary.rsvp_breakdown[RSVPStatus.YES] == 5
        assert summary.rsvp_breakdown[RSVPStatus.NO] == 5
        assert summary.rsvp_breakdown[RSVPStatus.WAITLIST] == 0

    def test_generate_summary_all_rsvp_statuses(self):
        """Test summary generation with all possible RSVP statuses."""
        events = [
            Event(
                id='1',
                title='Event 1',
                description='',
                date_time=datetime(2024, 1, 15, 18, 0),
                group_name='Test Group',
                group_id='test_group',
                venue=None,
                rsvp_limit=None,
                rsvps=[
                    RSVP('m1', 'Member 1', RSVPStatus.YES, datetime.now(), 2),
                    RSVP('m2', 'Member 2', RSVPStatus.YES, datetime.now(), 1),
                    RSVP('m3', 'Member 3', RSVPStatus.YES, datetime.now(), 0),
                    RSVP('m4', 'Member 4', RSVPStatus.NO, datetime.now(), 0),
                    RSVP('m5', 'Member 5', RSVPStatus.NO, datetime.now(), 0),
                    RSVP('m6', 'Member 6', RSVPStatus.WAITLIST, datetime.now(), 1),
                ]
            )
        ]
        
        summary = self.processor.generate_summary(events)
        
        assert summary.total_events == 1
        assert summary.total_rsvps == 6
        assert summary.rsvp_breakdown[RSVPStatus.YES] == 3
        assert summary.rsvp_breakdown[RSVPStatus.NO] == 2
        assert summary.rsvp_breakdown[RSVPStatus.WAITLIST] == 1

    def test_generate_summary_events_with_no_rsvps(self):
        """Test summary generation with events that have no RSVPs."""
        events = [
            Event(
                id='1',
                title='Event 1',
                description='',
                date_time=datetime(2024, 1, 15, 18, 0),
                group_name='Group A',
                group_id='group_a',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            ),
            Event(
                id='2',
                title='Event 2',
                description='',
                date_time=datetime(2024, 1, 20, 19, 0),
                group_name='Group B',
                group_id='group_b',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            )
        ]
        
        summary = self.processor.generate_summary(events)
        
        assert summary.total_events == 2
        assert summary.total_rsvps == 0
        assert all(count == 0 for count in summary.rsvp_breakdown.values())
        assert summary.events_by_group['Group A'] == 1
        assert summary.events_by_group['Group B'] == 1

    def test_generate_summary_mixed_group_names(self):
        """Test summary generation with different group names."""
        events = [
            Event(
                id='1',
                title='Event 1',
                description='',
                date_time=datetime(2024, 1, 15, 18, 0),
                group_name='Valid Group',
                group_id='valid_group',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            ),
            Event(
                id='2',
                title='Event 2',
                description='',
                date_time=datetime(2024, 1, 20, 19, 0),
                group_name='Another Group',
                group_id='another_group',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            ),
            Event(
                id='3',
                title='Event 3',
                description='',
                date_time=datetime(2024, 1, 25, 20, 0),
                group_name='Valid Group',  # Same as first event
                group_id='valid_group_2',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            )
        ]
        
        summary = self.processor.generate_summary(events)
        
        assert summary.total_events == 3
        assert summary.events_by_group['Valid Group'] == 2
        assert summary.events_by_group['Another Group'] == 1

    def test_generate_summary_events_with_none_datetime(self):
        """Test summary generation with events that have None datetime."""
        events = [
            Event(
                id='1',
                title='Event 1',
                description='',
                date_time=datetime(2024, 1, 15, 18, 0),
                group_name='Group A',
                group_id='group_a',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            ),
            Event(
                id='2',
                title='Event 2',
                description='',
                date_time=None,
                group_name='Group B',
                group_id='group_b',
                venue=None,
                rsvp_limit=None,
                rsvps=[]
            )
        ]
        
        summary = self.processor.generate_summary(events)
        
        assert summary.total_events == 2
        # Date range should only include events with valid datetime
        assert summary.date_range[0] == datetime(2024, 1, 15, 18, 0)
        assert summary.date_range[1] == datetime(2024, 1, 15, 18, 0)

    def test_generate_summary_performance_with_many_rsvps(self):
        """Test summary generation performance with events containing many RSVPs."""
        # Create a single event with 1000 RSVPs
        rsvps = []
        for i in range(1000):
            status = [RSVPStatus.YES, RSVPStatus.NO, RSVPStatus.WAITLIST][i % 3]
            rsvps.append(
                RSVP(f'member_{i}', f'Member {i}', status, datetime.now(), i % 5)
            )
        
        events = [
            Event(
                id='1',
                title='Large Event',
                description='',
                date_time=datetime(2024, 1, 15, 18, 0),
                group_name='Large Group',
                group_id='large_group',
                venue=None,
                rsvp_limit=None,
                rsvps=rsvps
            )
        ]
        
        summary = self.processor.generate_summary(events)
        
        assert summary.total_events == 1
        assert summary.total_rsvps == 1000
        
        # Check RSVP breakdown (should be roughly equal distribution)
        expected_yes = len([r for r in rsvps if r.response == RSVPStatus.YES])
        expected_no = len([r for r in rsvps if r.response == RSVPStatus.NO])
        expected_waitlist = len([r for r in rsvps if r.response == RSVPStatus.WAITLIST])
        
        assert summary.rsvp_breakdown[RSVPStatus.YES] == expected_yes
        assert summary.rsvp_breakdown[RSVPStatus.NO] == expected_no
        assert summary.rsvp_breakdown[RSVPStatus.WAITLIST] == expected_waitlist


if __name__ == '__main__':
    pytest.main([__file__])