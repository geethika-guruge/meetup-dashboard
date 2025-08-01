"""
Main application orchestrator for the Meetup RSVP Fetcher.

This module provides the MeetupRSVPFetcher class that coordinates the entire
workflow of authentication, data fetching, processing, and output formatting.
"""

import logging
import sys
from typing import List, Tuple, Optional
from datetime import datetime

from .config.config_manager import ConfigManager, ConfigurationError
from .auth.meetup_auth import MeetupAuth, AuthenticationError
from .api.graphql_client import MeetupGraphQLClient, GraphQLError
from .processors.data_processor import EventDataProcessor
from .models.data_models import Event, Summary, RSVPStatus


class MeetupRSVPFetcherError(Exception):
    """Base exception for MeetupRSVPFetcher errors."""
    pass


class MeetupRSVPFetcher:
    """
    Main application orchestrator for fetching and processing Meetup RSVP data.
    
    This class coordinates the entire workflow from authentication through
    data fetching, processing, and output formatting.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the MeetupRSVPFetcher.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, creates a new one.
        """
        self.config_manager = config_manager or ConfigManager()
        self.auth_manager: Optional[MeetupAuth] = None
        self.graphql_client: Optional[MeetupGraphQLClient] = None
        self.data_processor = EventDataProcessor()
        
        # Track errors for reporting
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        self.logger.info("MeetupRSVPFetcher initialized")
    
    def _setup_logging(self) -> None:
        """Configure logging for the application."""
        # Only configure if not already configured
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout)
                ]
            )
    
    def run(self) -> None:
        """
        Run the complete RSVP fetching workflow.
        
        This method orchestrates the entire process:
        1. Load configuration and authenticate
        2. Fetch all data from the API
        3. Process and format the results
        4. Output the results
        
        Raises:
            MeetupRSVPFetcherError: If the workflow fails at any stage
        """
        try:
            self.logger.info("Starting Meetup RSVP Fetcher workflow")
            
            # Initialize components
            self._initialize_components()
            
            # Fetch and process all data
            events, summary = self.fetch_all_data()
            
            # Output results
            self.output_results(events, summary)
            
            self.logger.info("Meetup RSVP Fetcher workflow completed successfully")
            
        except (ConfigurationError, AuthenticationError, GraphQLError) as e:
            self.logger.error(f"Workflow failed: {e}")
            raise MeetupRSVPFetcherError(f"Workflow failed: {e}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error in workflow: {e}")
            raise MeetupRSVPFetcherError(f"Unexpected error in workflow: {e}") from e
        finally:
            self._cleanup()
    
    def _initialize_components(self) -> None:
        """
        Initialize and authenticate all required components.
        
        Raises:
            ConfigurationError: If configuration loading fails
            AuthenticationError: If authentication fails
        """
        try:
            # Load configuration
            self.logger.info("Loading configuration")
            config = self.config_manager.load_config()
            
            # Initialize authentication manager
            self.logger.info("Initializing authentication")
            api_key, oauth_token = self.config_manager.get_api_credentials()
            self.auth_manager = MeetupAuth(api_key, oauth_token)
            
            # Authenticate with Meetup API
            self.logger.info("Authenticating with Meetup API")
            if not self.auth_manager.authenticate():
                raise AuthenticationError("Failed to authenticate with Meetup API")
            
            # Initialize GraphQL client
            self.logger.info("Initializing GraphQL client")
            self.graphql_client = MeetupGraphQLClient(self.auth_manager)
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    def fetch_all_data(self) -> Tuple[List[Event], Summary]:
        """
        Fetch and process all event and RSVP data.
        
        This method handles the complete data collection workflow:
        1. Fetch all events from the network
        2. Fetch RSVPs for each event
        3. Process and validate all data
        4. Generate summary statistics
        
        Returns:
            Tuple containing list of processed events and summary statistics
            
        Raises:
            GraphQLError: If critical API calls fail
            MeetupRSVPFetcherError: If data processing fails
        """
        if not self.graphql_client:
            raise MeetupRSVPFetcherError("GraphQL client not initialized")
        
        try:
            # Get network ID from configuration
            network_id = self.config_manager.get_network_id()
            self.logger.info(f"Fetching data for network: {network_id}")
            
            # Fetch all events from the network
            self.logger.info("Fetching network events")
            raw_events = self.graphql_client.fetch_network_events(network_id)
            self.logger.info(f"Retrieved {len(raw_events)} events from network")
            
            if not raw_events:
                self.logger.warning("No events found in network")
                return [], Summary(
                    total_events=0,
                    total_rsvps=0,
                    rsvp_breakdown={status: 0 for status in RSVPStatus},
                    events_by_group={},
                    date_range=(datetime.now(), datetime.now())
                )
            
            # Process events
            self.logger.info("Processing event data")
            events = self.data_processor.process_events(raw_events)
            self.logger.info(f"Successfully processed {len(events)} events")
            
            # Fetch RSVPs for each event
            self.logger.info("Fetching RSVPs for all events")
            events_with_rsvps = self._fetch_rsvps_for_events(events)
            
            # Generate summary statistics
            self.logger.info("Generating summary statistics")
            summary = self.data_processor.generate_summary(events_with_rsvps)
            
            self.logger.info(
                f"Data collection complete: {summary.total_events} events, "
                f"{summary.total_rsvps} RSVPs"
            )
            
            return events_with_rsvps, summary
            
        except GraphQLError as e:
            self.logger.error(f"API error during data fetching: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during data fetching: {e}")
            raise MeetupRSVPFetcherError(f"Data fetching failed: {e}") from e
    
    def _fetch_rsvps_for_events(self, events: List[Event]) -> List[Event]:
        """
        Fetch RSVPs for all events and populate the events with RSVP data.
        
        Args:
            events: List of Event objects to fetch RSVPs for
            
        Returns:
            List of Event objects with populated RSVP data
        """
        events_with_rsvps = []
        successful_fetches = 0
        failed_fetches = 0
        
        for i, event in enumerate(events, 1):
            try:
                self.logger.debug(f"Fetching RSVPs for event {i}/{len(events)}: {event.title}")
                
                # Fetch raw RSVP data
                raw_rsvps = self.graphql_client.fetch_event_rsvps(event.id)
                
                # Process RSVP data
                processed_rsvps = self.data_processor.process_rsvps(raw_rsvps)
                
                # Create new event with RSVPs
                event_with_rsvps = Event(
                    id=event.id,
                    title=event.title,
                    description=event.description,
                    date_time=event.date_time,
                    group_name=event.group_name,
                    group_id=event.group_id,
                    venue=event.venue,
                    rsvp_limit=event.rsvp_limit,
                    rsvps=processed_rsvps
                )
                
                events_with_rsvps.append(event_with_rsvps)
                successful_fetches += 1
                
                self.logger.debug(f"Successfully fetched {len(processed_rsvps)} RSVPs for event: {event.title}")
                
            except Exception as e:
                # Log error but continue processing other events
                error_msg = f"Failed to fetch RSVPs for event '{event.title}': {str(e)}"
                self.logger.warning(error_msg)
                self.errors.append(error_msg)
                
                # Add event without RSVPs to maintain data integrity
                event_without_rsvps = Event(
                    id=event.id,
                    title=event.title,
                    description=event.description,
                    date_time=event.date_time,
                    group_name=event.group_name,
                    group_id=event.group_id,
                    venue=event.venue,
                    rsvp_limit=event.rsvp_limit,
                    rsvps=[]
                )
                events_with_rsvps.append(event_without_rsvps)
                failed_fetches += 1
        
        if failed_fetches > 0:
            warning_msg = f"RSVP fetching completed with {failed_fetches} failures out of {len(events)} events"
            self.warnings.append(warning_msg)
        
        self.logger.info(
            f"RSVP fetching complete: {successful_fetches} successful, "
            f"{failed_fetches} failed out of {len(events)} events"
        )
        
        return events_with_rsvps
    
    def output_results(self, events: List[Event], summary: Summary) -> None:
        """
        Format and display the fetched events and RSVPs with structured output.
        
        This method provides comprehensive output including:
        - Summary statistics with proper formatting
        - Detailed event information with RSVP data
        - Error reporting without stopping the process
        
        Args:
            events: List of processed Event objects
            summary: Summary statistics object
        """
        self.logger.info("Formatting and displaying results")
        
        try:
            # Display header
            self._display_header()
            
            # Display summary statistics
            self._display_summary(summary)
            
            # Display detailed event information
            self._display_events(events)
            
            # Display RSVP details if requested
            self._display_rsvp_details(events)
            
            # Display any errors that occurred during processing
            self._display_error_summary()
            
            # Display footer
            self._display_footer()
            
        except Exception as e:
            error_msg = f"Error during output formatting: {str(e)}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            print(f"\nERROR: {error_msg}")
            print("Partial results may have been displayed above.")
    
    def _display_header(self) -> None:
        """Display application header with branding and timestamp."""
        print("\n" + "="*80)
        print("MEETUP RSVP FETCHER - COMPREHENSIVE REPORT")
        print("="*80)
        print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

    def _display_summary(self, summary: Summary) -> None:
        """
        Display comprehensive summary statistics with proper formatting.
        
        Args:
            summary: Summary statistics object containing aggregated data
        """
        print("\n" + "─"*60)
        print("📊 SUMMARY STATISTICS")
        print("─"*60)
        
        # Basic counts
        print(f"\n📅 Total Events: {summary.total_events:,}")
        print(f"👥 Total RSVPs: {summary.total_rsvps:,}")
        
        # Date range information
        if summary.date_range[0] and summary.date_range[1]:
            start_date = summary.date_range[0].strftime("%Y-%m-%d")
            end_date = summary.date_range[1].strftime("%Y-%m-%d")
            print(f"📆 Date Range: {start_date} to {end_date}")
            
            # Calculate duration
            duration = summary.date_range[1] - summary.date_range[0]
            print(f"⏱️  Duration: {duration.days} days")
        
        # RSVP breakdown with visual indicators
        print(f"\n📈 RSVP Breakdown:")
        if summary.total_rsvps > 0:
            yes_count = summary.rsvp_breakdown.get(RSVPStatus.YES, 0)
            no_count = summary.rsvp_breakdown.get(RSVPStatus.NO, 0)
            waitlist_count = summary.rsvp_breakdown.get(RSVPStatus.WAITLIST, 0)
            
            print(f"  ✅ Yes: {yes_count:,} ({summary.yes_percentage:.1f}%)")
            print(f"  ❌ No: {no_count:,} ({summary.no_percentage:.1f}%)")
            print(f"  ⏳ Waitlist: {waitlist_count:,} ({summary.waitlist_percentage:.1f}%)")
            
            # Calculate attendance rate
            if yes_count + no_count > 0:
                attendance_rate = (yes_count / (yes_count + no_count)) * 100
                print(f"  📊 Attendance Rate: {attendance_rate:.1f}%")
        else:
            print("  No RSVP data available")
        
        # Events by group with better formatting
        if summary.events_by_group:
            print(f"\n🏢 Events by Group:")
            sorted_groups = sorted(summary.events_by_group.items(), key=lambda x: x[1], reverse=True)
            for i, (group_name, count) in enumerate(sorted_groups[:10], 1):  # Show top 10
                print(f"  {i:2d}. {group_name}: {count} events")
            
            if len(sorted_groups) > 10:
                remaining = len(sorted_groups) - 10
                print(f"      ... and {remaining} more groups")
        
        # Additional statistics
        if summary.total_events > 0:
            avg_rsvps_per_event = summary.total_rsvps / summary.total_events
            print(f"\n📊 Average RSVPs per Event: {avg_rsvps_per_event:.1f}")
            
            if summary.events_by_group:
                avg_events_per_group = summary.total_events / len(summary.events_by_group)
                print(f"📊 Average Events per Group: {avg_events_per_group:.1f}")
    
    def _display_events(self, events: List[Event]) -> None:
        """
        Display detailed event information with structured formatting.
        
        Args:
            events: List of Event objects to display
        """
        if not events:
            print("\n📭 No events to display.")
            return
        
        print(f"\n" + "─"*60)
        print("📅 DETAILED EVENT INFORMATION")
        print("─"*60)
        
        # Sort events by date for better readability
        sorted_events = sorted(events, key=lambda e: e.date_time)
        
        for i, event in enumerate(sorted_events, 1):
            print(f"\n{i:2d}. 📌 {event.title}")
            print(f"     🏢 Group: {event.group_name}")
            print(f"     📅 Date: {event.date_time.strftime('%Y-%m-%d %H:%M (%A)')}")
            print(f"     🆔 Event ID: {event.id}")
            
            # Venue information with better formatting
            if event.venue:
                venue_parts = [event.venue.name]
                if event.venue.address:
                    venue_parts.append(event.venue.address)
                venue_parts.append(event.venue.city)
                if event.venue.state:
                    venue_parts.append(event.venue.state)
                venue_info = ", ".join(venue_parts)
                print(f"     📍 Venue: {venue_info}")
            else:
                print(f"     📍 Venue: Not specified")
            
            # RSVP limit information
            if event.rsvp_limit:
                utilization = (event.total_rsvps / event.rsvp_limit) * 100 if event.rsvp_limit > 0 else 0
                print(f"     🎫 RSVP Limit: {event.rsvp_limit} (Utilization: {utilization:.1f}%)")
            
            # RSVP summary with visual indicators
            print(f"     👥 RSVPs: {event.total_rsvps} total")
            if event.total_rsvps > 0:
                yes_pct = (event.yes_rsvps / event.total_rsvps) * 100
                no_pct = (event.no_rsvps / event.total_rsvps) * 100
                waitlist_pct = (event.waitlist_rsvps / event.total_rsvps) * 100
                
                print(f"       ✅ Yes: {event.yes_rsvps} ({yes_pct:.1f}%)")
                print(f"       ❌ No: {event.no_rsvps} ({no_pct:.1f}%)")
                print(f"       ⏳ Waitlist: {event.waitlist_rsvps} ({waitlist_pct:.1f}%)")
                print(f"       🎉 Total Attendees (with guests): {event.total_attendees}")
                
                # Show capacity utilization if limit exists
                if event.rsvp_limit and event.yes_rsvps > 0:
                    capacity_used = (event.yes_rsvps / event.rsvp_limit) * 100
                    print(f"       📊 Capacity Used: {capacity_used:.1f}%")
            else:
                print(f"       ℹ️  No RSVP data available")
            
            # Description with smart truncation
            if event.description and event.description.strip():
                # Clean up description
                description = event.description.strip()
                if len(description) > 150:
                    # Try to truncate at sentence boundary
                    sentences = description.split('. ')
                    truncated = sentences[0]
                    if len(truncated) < 100 and len(sentences) > 1:
                        truncated += '. ' + sentences[1]
                    if len(truncated) > 150:
                        truncated = description[:150]
                    description = truncated + "..."
                print(f"     📝 Description: {description}")
            
            # Add separator between events (except for the last one)
            if i < len(sorted_events):
                print("     " + "─" * 50)
    
    def _display_rsvp_details(self, events: List[Event]) -> None:
        """
        Display detailed RSVP information for events with significant activity.
        
        Args:
            events: List of Event objects to analyze for RSVP details
        """
        # Only show RSVP details for events with substantial activity
        events_with_rsvps = [e for e in events if e.total_rsvps > 0]
        
        if not events_with_rsvps:
            return
        
        # Show top events by RSVP count
        top_events = sorted(events_with_rsvps, key=lambda e: e.total_rsvps, reverse=True)[:5]
        
        if top_events:
            print(f"\n" + "─"*60)
            print("🏆 TOP EVENTS BY RSVP COUNT")
            print("─"*60)
            
            for i, event in enumerate(top_events, 1):
                print(f"\n{i}. {event.title}")
                print(f"   📊 Total RSVPs: {event.total_rsvps}")
                print(f"   ✅ Attending: {event.yes_rsvps} ({event.yes_rsvps/event.total_rsvps*100:.1f}%)")
                print(f"   🎉 Total Attendees (with guests): {event.total_attendees}")
                print(f"   📅 Date: {event.date_time.strftime('%Y-%m-%d %H:%M')}")
                print(f"   🏢 Group: {event.group_name}")

    def _display_error_summary(self) -> None:
        """
        Display comprehensive summary of errors and warnings that occurred during processing.
        
        This method provides error reporting without stopping the process, as required
        by the task specifications.
        """
        if not self.errors and not self.warnings:
            return
        
        print(f"\n" + "─"*60)
        print("⚠️  PROCESSING ISSUES SUMMARY")
        print("─"*60)
        
        if self.warnings:
            print(f"\n🟡 Warnings ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if self.errors:
            print(f"\n🔴 Errors ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
            
            print(f"\nℹ️  Note: {len(self.errors)} errors occurred during processing, but the application")
            print("   continued to process other data where possible. Check the logs for more details.")
        
        # Provide guidance on common issues
        if self.errors:
            print(f"\n💡 Troubleshooting Tips:")
            print("   • Check your API credentials and network connectivity")
            print("   • Verify that the events still exist and are accessible")
            print("   • Some events may have restricted RSVP data access")
            print("   • Rate limiting may cause temporary failures - try again later")

    def _display_footer(self) -> None:
        """Display application footer with completion information."""
        print(f"\n" + "="*80)
        print("REPORT COMPLETED")
        print("="*80)
        
        # Summary of processing results
        total_issues = len(self.errors) + len(self.warnings)
        if total_issues == 0:
            print("✅ Processing completed successfully with no issues.")
        else:
            print(f"⚠️  Processing completed with {total_issues} issues:")
            if self.warnings:
                print(f"   • {len(self.warnings)} warnings")
            if self.errors:
                print(f"   • {len(self.errors)} errors")
        
        print(f"\nFor technical support or questions about this data, please refer to the")
        print(f"application logs or contact your system administrator.")
        print("="*80)
    
    def _cleanup(self) -> None:
        """Clean up resources and close connections."""
        try:
            if self.graphql_client:
                self.graphql_client.close()
                self.logger.debug("GraphQL client closed")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")