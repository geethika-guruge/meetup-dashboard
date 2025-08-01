"""
Core data models for the Meetup RSVP Fetcher application.

This module defines the data structures used throughout the application
for representing events, RSVPs, venues, and summary statistics.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RSVPStatus(Enum):
    """Enumeration for RSVP response statuses."""
    YES = "yes"
    NO = "no"
    WAITLIST = "waitlist"

    @classmethod
    def from_string(cls, status: str) -> 'RSVPStatus':
        """
        Convert string to RSVPStatus enum.
        
        Args:
            status: String representation of RSVP status
            
        Returns:
            RSVPStatus enum value
            
        Raises:
            ValueError: If status is not a valid RSVP status
        """
        status_lower = status.lower()
        for rsvp_status in cls:
            if rsvp_status.value == status_lower:
                return rsvp_status
        raise ValueError(f"Invalid RSVP status: {status}")


@dataclass
class Venue:
    """Represents an event venue with location information."""
    name: str
    address: str
    city: str
    state: str

    def __post_init__(self) -> None:
        """Validate venue data after initialization."""
        if not self.name.strip():
            raise ValueError("Venue name cannot be empty")
        if not self.city.strip():
            raise ValueError("Venue city cannot be empty")


@dataclass
class RSVP:
    """Represents an individual RSVP response to an event."""
    member_id: str
    member_name: str
    response: RSVPStatus
    response_time: datetime
    guests: int = 0

    def __post_init__(self) -> None:
        """Validate RSVP data after initialization."""
        if not self.member_id.strip():
            raise ValueError("Member ID cannot be empty")
        if not self.member_name.strip():
            raise ValueError("Member name cannot be empty")
        if self.guests < 0:
            raise ValueError("Number of guests cannot be negative")


@dataclass
class Event:
    """Represents a Meetup event with all associated information."""
    id: str
    title: str
    description: str
    date_time: datetime
    group_name: str
    group_id: str
    venue: Optional[Venue] = None
    rsvp_limit: Optional[int] = None
    rsvps: List[RSVP] = None

    def __post_init__(self) -> None:
        """Initialize default values and validate event data."""
        if self.rsvps is None:
            self.rsvps = []
        
        # Validation
        if not self.id.strip():
            raise ValueError("Event ID cannot be empty")
        if not self.title.strip():
            raise ValueError("Event title cannot be empty")
        if not self.group_name.strip():
            raise ValueError("Group name cannot be empty")
        if not self.group_id.strip():
            raise ValueError("Group ID cannot be empty")
        if self.rsvp_limit is not None and self.rsvp_limit < 0:
            raise ValueError("RSVP limit cannot be negative")

    @property
    def total_rsvps(self) -> int:
        """Get total number of RSVPs for this event."""
        return len(self.rsvps)

    @property
    def yes_rsvps(self) -> int:
        """Get number of 'yes' RSVPs for this event."""
        return len([rsvp for rsvp in self.rsvps if rsvp.response == RSVPStatus.YES])

    @property
    def no_rsvps(self) -> int:
        """Get number of 'no' RSVPs for this event."""
        return len([rsvp for rsvp in self.rsvps if rsvp.response == RSVPStatus.NO])

    @property
    def waitlist_rsvps(self) -> int:
        """Get number of waitlist RSVPs for this event."""
        return len([rsvp for rsvp in self.rsvps if rsvp.response == RSVPStatus.WAITLIST])

    @property
    def total_attendees(self) -> int:
        """Get total number of attendees including guests."""
        return sum(1 + rsvp.guests for rsvp in self.rsvps if rsvp.response == RSVPStatus.YES)


@dataclass
class Summary:
    """Represents summary statistics for all events and RSVPs."""
    total_events: int
    total_rsvps: int
    rsvp_breakdown: Dict[RSVPStatus, int]
    events_by_group: Dict[str, int]
    date_range: Tuple[Optional[datetime], Optional[datetime]]

    def __post_init__(self) -> None:
        """Validate summary data after initialization."""
        if self.total_events < 0:
            raise ValueError("Total events cannot be negative")
        if self.total_rsvps < 0:
            raise ValueError("Total RSVPs cannot be negative")
        
        # Initialize empty breakdown if not provided
        if not self.rsvp_breakdown:
            self.rsvp_breakdown = {status: 0 for status in RSVPStatus}
        
        # Initialize empty events_by_group if not provided
        if not self.events_by_group:
            self.events_by_group = {}

    @property
    def yes_percentage(self) -> float:
        """Get percentage of 'yes' RSVPs."""
        if self.total_rsvps == 0:
            return 0.0
        return (self.rsvp_breakdown.get(RSVPStatus.YES, 0) / self.total_rsvps) * 100

    @property
    def no_percentage(self) -> float:
        """Get percentage of 'no' RSVPs."""
        if self.total_rsvps == 0:
            return 0.0
        return (self.rsvp_breakdown.get(RSVPStatus.NO, 0) / self.total_rsvps) * 100

    @property
    def waitlist_percentage(self) -> float:
        """Get percentage of waitlist RSVPs."""
        if self.total_rsvps == 0:
            return 0.0
        return (self.rsvp_breakdown.get(RSVPStatus.WAITLIST, 0) / self.total_rsvps) * 100