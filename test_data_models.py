#!/usr/bin/env python3
"""
Test script to verify the data models implementation.
"""

from datetime import datetime
from meetup_rsvp_fetcher.models import Event, RSVP, RSVPStatus, Summary, Venue

def test_rsvp_status_enum():
    """Test RSVPStatus enum functionality."""
    print("Testing RSVPStatus enum...")
    
    # Test enum values
    assert RSVPStatus.YES.value == "yes"
    assert RSVPStatus.NO.value == "no"
    assert RSVPStatus.WAITLIST.value == "waitlist"
    
    # Test from_string method
    assert RSVPStatus.from_string("yes") == RSVPStatus.YES
    assert RSVPStatus.from_string("YES") == RSVPStatus.YES
    assert RSVPStatus.from_string("no") == RSVPStatus.NO
    assert RSVPStatus.from_string("waitlist") == RSVPStatus.WAITLIST
    
    # Test invalid status
    try:
        RSVPStatus.from_string("invalid")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    print("✓ RSVPStatus enum tests passed")

def test_venue_model():
    """Test Venue data model."""
    print("Testing Venue model...")
    
    venue = Venue(
        name="Test Venue",
        address="123 Main St",
        city="Test City",
        state="CA"
    )
    
    assert venue.name == "Test Venue"
    assert venue.address == "123 Main St"
    assert venue.city == "Test City"
    assert venue.state == "CA"
    
    # Test validation
    try:
        Venue(name="", address="123 Main St", city="Test City", state="CA")
        assert False, "Should have raised ValueError for empty name"
    except ValueError:
        pass
    
    try:
        Venue(name="Test", address="123 Main St", city="", state="CA")
        assert False, "Should have raised ValueError for empty city"
    except ValueError:
        pass
    
    print("✓ Venue model tests passed")

def test_rsvp_model():
    """Test RSVP data model."""
    print("Testing RSVP model...")
    
    rsvp = RSVP(
        member_id="12345",
        member_name="John Doe",
        response=RSVPStatus.YES,
        response_time=datetime.now(),
        guests=2
    )
    
    assert rsvp.member_id == "12345"
    assert rsvp.member_name == "John Doe"
    assert rsvp.response == RSVPStatus.YES
    assert rsvp.guests == 2
    
    # Test validation
    try:
        RSVP(member_id="", member_name="John", response=RSVPStatus.YES, response_time=datetime.now())
        assert False, "Should have raised ValueError for empty member_id"
    except ValueError:
        pass
    
    try:
        RSVP(member_id="123", member_name="", response=RSVPStatus.YES, response_time=datetime.now())
        assert False, "Should have raised ValueError for empty member_name"
    except ValueError:
        pass
    
    try:
        RSVP(member_id="123", member_name="John", response=RSVPStatus.YES, response_time=datetime.now(), guests=-1)
        assert False, "Should have raised ValueError for negative guests"
    except ValueError:
        pass
    
    print("✓ RSVP model tests passed")

def test_event_model():
    """Test Event data model."""
    print("Testing Event model...")
    
    venue = Venue("Test Venue", "123 Main St", "Test City", "CA")
    rsvp1 = RSVP("1", "John", RSVPStatus.YES, datetime.now(), 1)
    rsvp2 = RSVP("2", "Jane", RSVPStatus.NO, datetime.now(), 0)
    rsvp3 = RSVP("3", "Bob", RSVPStatus.WAITLIST, datetime.now(), 0)
    
    event = Event(
        id="event123",
        title="Test Event",
        description="A test event",
        date_time=datetime.now(),
        group_name="Test Group",
        group_id="group123",
        venue=venue,
        rsvp_limit=50,
        rsvps=[rsvp1, rsvp2, rsvp3]
    )
    
    assert event.id == "event123"
    assert event.title == "Test Event"
    assert event.total_rsvps == 3
    assert event.yes_rsvps == 1
    assert event.no_rsvps == 1
    assert event.waitlist_rsvps == 1
    assert event.total_attendees == 2  # 1 person + 1 guest
    
    # Test validation
    try:
        Event(id="", title="Test", description="Test", date_time=datetime.now(), group_name="Group", group_id="123")
        assert False, "Should have raised ValueError for empty id"
    except ValueError:
        pass
    
    print("✓ Event model tests passed")

def test_summary_model():
    """Test Summary data model."""
    print("Testing Summary model...")
    
    rsvp_breakdown = {
        RSVPStatus.YES: 10,
        RSVPStatus.NO: 5,
        RSVPStatus.WAITLIST: 2
    }
    
    events_by_group = {
        "Group A": 3,
        "Group B": 2
    }
    
    summary = Summary(
        total_events=5,
        total_rsvps=17,
        rsvp_breakdown=rsvp_breakdown,
        events_by_group=events_by_group,
        date_range=(datetime.now(), datetime.now())
    )
    
    assert summary.total_events == 5
    assert summary.total_rsvps == 17
    assert abs(summary.yes_percentage - 58.82) < 0.1  # 10/17 * 100
    assert abs(summary.no_percentage - 29.41) < 0.1   # 5/17 * 100
    assert abs(summary.waitlist_percentage - 11.76) < 0.1  # 2/17 * 100
    
    print("✓ Summary model tests passed")

if __name__ == "__main__":
    print("Running data models tests...\n")
    
    test_rsvp_status_enum()
    test_venue_model()
    test_rsvp_model()
    test_event_model()
    test_summary_model()
    
    print("\n✅ All data model tests passed!")
    print("Task 1 implementation verified successfully.")