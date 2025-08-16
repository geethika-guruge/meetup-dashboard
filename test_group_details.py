#!/usr/bin/env python3
"""
Test script to demonstrate the group details fetcher with mock data.
This shows what the output would look like without requiring real API credentials.
"""

import json
from datetime import datetime
from fetch_group_details import MeetupGroupFetcher

def create_mock_group_details():
    """Create mock group details data for demonstration."""
    return {
        'networkAnalytics': {
            'totalCountries': 25,
            'totalGroups': 150,
            'totalMembers': 12500
        },
        'groups': [
            {
                'id': '1',
                'country': 'New Zealand',
                'name': 'AWS User Group Auckland',
                'foundedDate': '2020-01-15',
                'stats': {'memberCounts': {'all': 1500}},
                'eventsLast12Months': 8,
                'avgRsvpsLast12Months': 45.2
            },
            {
                'id': '2',
                'country': 'New Zealand',
                'name': 'AWS User Group Wellington',
                'foundedDate': '2019-03-20',
                'stats': {'memberCounts': {'all': 1237}},
                'eventsLast12Months': 12,
                'avgRsvpsLast12Months': 38.7
            },
            {
                'id': '3',
                'country': 'Australia',
                'name': 'AWS User Group Sydney',
                'foundedDate': '2018-06-10',
                'stats': {'memberCounts': {'all': 2100}},
                'eventsLast12Months': 15,
                'avgRsvpsLast12Months': 62.3
            },
            {
                'id': '4',
                'country': 'Australia',
                'name': 'AWS User Group Melbourne',
                'foundedDate': '2017-11-05',
                'stats': {'memberCounts': {'all': 1890}},
                'eventsLast12Months': 18,
                'avgRsvpsLast12Months': 55.8
            }
        ],
        'totalGroupsProcessed': 4,
        'fetchedAt': datetime.now().isoformat()
    }

def main():
    """Main function to demonstrate the group details output."""
    print("DEMO: Meetup Group Details Fetcher")
    print("=" * 50)
    print("This demonstrates what the output looks like with mock data.")
    print("To use with real data, run: python3 fetch_group_details.py")
    print()
    
    # Create a mock fetcher instance (we won't actually call the API)
    fetcher = MeetupGroupFetcher("mock_token", "mock_urlname")
    
    # Create mock data
    mock_data = create_mock_group_details()
    
    # Print the formatted output
    fetcher.print_group_details(mock_data)
    
    print("\nRAW JSON DATA:")
    print("-" * 40)
    print(json.dumps(mock_data, indent=2, default=str))

if __name__ == "__main__":
    main()
