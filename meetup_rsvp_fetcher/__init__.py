"""
Meetup RSVP Fetcher - A Python application for fetching and analyzing Meetup event and RSVP data.

This package provides tools to interface with the Meetup.com GraphQL API to retrieve
comprehensive event and RSVP data from MeetupPro networks.
"""

from .models import Event, RSVP, RSVPStatus, Summary, Venue
from .main import MeetupRSVPFetcher

__version__ = "1.0.0"
__all__ = [
    'Event',
    'RSVP',
    'RSVPStatus', 
    'Summary',
    'Venue',
    'MeetupRSVPFetcher'
]