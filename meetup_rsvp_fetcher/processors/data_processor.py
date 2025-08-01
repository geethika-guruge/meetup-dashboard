"""
Data processing and transformation module for Meetup RSVP data.

This module handles the conversion of raw API responses into structured data models
and provides data validation and cleaning functionality.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from ..models.data_models import Event, RSVP, Venue, Summary, RSVPStatus

logger = logging.getLogger(__name__)


class EventDataProcessor:
    """Processes and transforms raw Meetup API data into structured models."""
    
    def __init__(self):
        """Initialize the data processor."""
        self.logger = logging.getLogger(__name__)
    
    def process_events(self, raw_events: List[Dict[str, Any]]) -> List[Event]:
        """
        Convert raw API event data to Event objects.
        
        Args:
            raw_events: List of raw event dictionaries from GraphQL API
            
        Returns:
            List of Event objects with validated and cleaned data
            
        Raises:
            ValueError: If required event data is missing or invalid
        """
        processed_events = []
        
        for raw_event in raw_events:
            try:
                event = self._process_single_event(raw_event)
                if event:
                    processed_events.append(event)
            except Exception as e:
                self.logger.warning(f"Failed to process event {raw_event.get('id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Successfully processed {len(processed_events)} out of {len(raw_events)} events")
        return processed_events
    
    def _process_single_event(self, raw_event: Dict[str, Any]) -> Optional[Event]:
        """
        Process a single raw event into an Event object.
        
        Args:
            raw_event: Raw event dictionary from API
            
        Returns:
            Event object or None if processing fails
        """
        # Validate required fields
        required_fields = ['id', 'title', 'dateTime']
        for field in required_fields:
            if not raw_event.get(field):
                raise ValueError(f"Missing required field: {field}")
        
        # Extract and validate event ID
        event_id = str(raw_event['id']).strip()
        if not event_id:
            raise ValueError("Event ID cannot be empty")
        
        # Extract and clean title
        title = str(raw_event['title']).strip()
        if not title:
            raise ValueError("Event title cannot be empty")
        
        # Parse datetime
        try:
            date_time = self._parse_datetime(raw_event['dateTime'])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid dateTime format: {e}")
        
        # Extract description (optional)
        description = str(raw_event.get('description', '')).strip()
        
        # Process group information
        group_data = raw_event.get('group', {})
        group_id = str(group_data.get('id', '')).strip()
        group_name = str(group_data.get('name', '')).strip()
        
        # Ensure group information is valid
        if not group_id:
            raise ValueError("Group ID cannot be empty")
        if not group_name:
            group_name = 'Unknown Group'
        
        # Process venue information (optional)
        venue = None
        venue_data = raw_event.get('venue')
        if venue_data and isinstance(venue_data, dict):
            venue = self._process_venue(venue_data)
        
        # Extract RSVP limit (optional)
        rsvp_limit = raw_event.get('maxTickets')
        if rsvp_limit is not None:
            try:
                rsvp_limit = int(rsvp_limit)
                if rsvp_limit < 0:
                    rsvp_limit = None
            except (ValueError, TypeError):
                rsvp_limit = None
        
        return Event(
            id=event_id,
            title=title,
            description=description,
            date_time=date_time,
            group_name=group_name,
            group_id=group_id,
            venue=venue,
            rsvp_limit=rsvp_limit,
            rsvps=[]  # RSVPs will be populated separately
        )
    
    def _process_venue(self, venue_data: Dict[str, Any]) -> Optional[Venue]:
        """
        Process venue data into a Venue object.
        
        Args:
            venue_data: Raw venue dictionary from API
            
        Returns:
            Venue object or None if processing fails
        """
        try:
            name = str(venue_data.get('name', '')).strip()
            address = str(venue_data.get('address', '')).strip()
            city = str(venue_data.get('city', '')).strip()
            state = str(venue_data.get('state', '')).strip()
            
            # At least name and city should be present for a valid venue
            if not name:
                return None
            if not city:
                city = 'Unknown City'  # Provide default to satisfy validation
            
            return Venue(
                name=name,
                address=address,
                city=city,
                state=state
            )
        except Exception as e:
            self.logger.warning(f"Failed to process venue data: {e}")
            return None
    
    def process_rsvps(self, raw_rsvps: List[Dict[str, Any]]) -> List[RSVP]:
        """
        Convert raw API RSVP data to RSVP objects.
        
        Args:
            raw_rsvps: List of raw RSVP dictionaries from GraphQL API
            
        Returns:
            List of RSVP objects with validated and cleaned data
        """
        processed_rsvps = []
        
        for raw_rsvp in raw_rsvps:
            try:
                rsvp = self._process_single_rsvp(raw_rsvp)
                if rsvp:
                    processed_rsvps.append(rsvp)
            except Exception as e:
                self.logger.warning(f"Failed to process RSVP {raw_rsvp.get('id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Successfully processed {len(processed_rsvps)} out of {len(raw_rsvps)} RSVPs")
        return processed_rsvps
    
    def _process_single_rsvp(self, raw_rsvp: Dict[str, Any]) -> Optional[RSVP]:
        """
        Process a single raw RSVP into an RSVP object.
        
        Args:
            raw_rsvp: Raw RSVP dictionary from API
            
        Returns:
            RSVP object or None if processing fails
        """
        # Validate required fields
        if not raw_rsvp.get('response'):
            raise ValueError("Missing required field: response")
        
        # Extract member information
        member_data = raw_rsvp.get('member', {})
        if not isinstance(member_data, dict):
            raise ValueError("Invalid member data")
        
        member_id = str(member_data.get('id', '')).strip()
        member_name = str(member_data.get('name', 'Unknown Member')).strip()
        
        if not member_id:
            raise ValueError("Member ID cannot be empty")
        
        # Parse RSVP response status
        response_str = str(raw_rsvp['response']).lower().strip()
        try:
            response = RSVPStatus(response_str)
        except ValueError:
            # Handle unknown response types by defaulting to 'no'
            self.logger.warning(f"Unknown RSVP response type: {response_str}, defaulting to 'no'")
            response = RSVPStatus.NO
        
        # Parse response time
        try:
            response_time = self._parse_datetime(raw_rsvp.get('created'))
        except (ValueError, TypeError):
            # Default to current time if parsing fails
            response_time = datetime.now()
            self.logger.warning(f"Invalid response time for RSVP {raw_rsvp.get('id')}, using current time")
        
        # Extract guest count
        guests = raw_rsvp.get('guests', 0)
        try:
            guests = int(guests)
            if guests < 0:
                guests = 0
        except (ValueError, TypeError):
            guests = 0
        
        return RSVP(
            member_id=member_id,
            member_name=member_name,
            response=response,
            response_time=response_time,
            guests=guests
        )
    
    def _parse_datetime(self, datetime_str: Any) -> datetime:
        """
        Parse datetime string into datetime object.
        
        Args:
            datetime_str: Datetime string in various formats
            
        Returns:
            Parsed datetime object
            
        Raises:
            ValueError: If datetime string cannot be parsed
        """
        if not datetime_str:
            raise ValueError("Datetime string cannot be empty")
        
        datetime_str = str(datetime_str).strip()
        
        # Common datetime formats from Meetup API
        formats = [
            '%Y-%m-%dT%H:%M:%S%z',  # ISO format with timezone
            '%Y-%m-%dT%H:%M:%SZ',   # ISO format with Z timezone
            '%Y-%m-%dT%H:%M:%S',    # ISO format without timezone
            '%Y-%m-%d %H:%M:%S',    # Standard format
            '%Y-%m-%d',             # Date only
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        # Try parsing as timestamp
        try:
            timestamp = float(datetime_str)
            return datetime.fromtimestamp(timestamp)
        except (ValueError, TypeError):
            pass
        
        raise ValueError(f"Unable to parse datetime: {datetime_str}")
    
    def generate_summary(self, events: List[Event]) -> Summary:
        """
        Generate summary statistics from processed events.
        
        Args:
            events: List of processed Event objects
            
        Returns:
            Summary object with aggregated statistics
        """
        if not events:
            return Summary(
                total_events=0,
                total_rsvps=0,
                rsvp_breakdown={status: 0 for status in RSVPStatus},
                events_by_group={},
                date_range=(datetime.now(), datetime.now())
            )
        
        # Calculate totals
        total_events = len(events)
        total_rsvps = sum(len(event.rsvps) for event in events)
        
        # Calculate RSVP breakdown by status
        rsvp_breakdown = {status: 0 for status in RSVPStatus}
        for event in events:
            for rsvp in event.rsvps:
                rsvp_breakdown[rsvp.response] += 1
        
        # Calculate events by group
        events_by_group = {}
        for event in events:
            group_name = event.group_name or 'Unknown Group'
            events_by_group[group_name] = events_by_group.get(group_name, 0) + 1
        
        # Calculate date range
        event_dates = [event.date_time for event in events if event.date_time]
        if event_dates:
            date_range = (min(event_dates), max(event_dates))
        else:
            date_range = (datetime.now(), datetime.now())
        
        return Summary(
            total_events=total_events,
            total_rsvps=total_rsvps,
            rsvp_breakdown=rsvp_breakdown,
            events_by_group=events_by_group,
            date_range=date_range
        )