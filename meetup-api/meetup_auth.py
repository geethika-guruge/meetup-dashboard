#!/usr/bin/env python3
"""
Minimal Meetup API authentication and data fetching script.
"""

import json
import os
import time

import requests


class MeetupAuth:
    """Handles Meetup API OAuth authentication and GraphQL calls."""
    
    def __init__(self, client_id, client_secret, redirect_uri="http://example.com/callback"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
    
    def get_auth_url(self):
        """Generate authorization URL for user to visit."""
        return (
            f"https://secure.meetup.com/oauth2/authorize?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"redirect_uri={self.redirect_uri}"
        )
    
    def get_access_token(self, auth_code):
        """Exchange authorization code for access token."""
        response = requests.post(
            "https://secure.meetup.com/oauth2/access",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
                "code": auth_code
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            return token_data
        else:
            raise Exception(f"Token exchange failed: {response.text}")
    
    def graphql_call(self, query, variables=None):
        """Make authenticated GraphQL API call."""
        if not self.access_token:
            raise Exception("No access token. Authenticate first.")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        response = requests.post(
            "https://api.meetup.com/gql-ext",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"GraphQL call failed: {response.status_code} - {response.text}")

def main():
    """Main function to run the Meetup API authentication and data fetching."""
    # Get credentials from environment variables
    client_id = os.getenv('MEETUP_CLIENT_ID')
    client_secret = os.getenv('MEETUP_CLIENT_SECRET')
    pro_urlname = os.getenv('MEETUP_PRO_URLNAME')
    
    if not client_id or not client_secret:
        print("Error: Set MEETUP_CLIENT_ID and MEETUP_CLIENT_SECRET environment variables")
        return
    
    if not pro_urlname:
        print("Error: Set MEETUP_PRO_URLNAME environment variable")
        return
    
    # Initialize authentication
    auth = MeetupAuth(client_id, client_secret)
    
    # Step 1: Get authorization URL
    print("1. Visit this URL to authorize the app:")
    print(auth.get_auth_url())
    print()
    
    # Step 2: Get authorization code from user
    auth_code = input("2. Enter the authorization code from the callback URL: ").strip()
    
    try:
        # Step 3: Exchange authorization code for access token
        token_data = auth.get_access_token(auth_code)
        print("✓ Authentication successful!")
        
        # Step 4: Fetch user profile
        print("\nFetching your profile...")
        profile_query = "{ self { id name } }"
        profile_result = auth.graphql_call(profile_query)
        
        if 'data' in profile_result and profile_result['data']['self']:
            profile = profile_result['data']['self']
            print(f"Hello, {profile.get('name', 'User')}!")
        else:
            print("Profile fetch failed")
            profile = {}
        
        # Step 5: Fetch pro network analytics
        print(f"\nFetching proNetwork analytics for {pro_urlname}...")
        analytics_query = """
        query ($urlname: ID) {
          proNetwork(urlname: $urlname) {
            networkAnalytics{
              totalCountries
              totalGroups
              totalMembers
            }
          }
        }
        """
        
        variables = {"urlname": pro_urlname}
        analytics_result = auth.graphql_call(analytics_query, variables)
        
        if 'data' in analytics_result and analytics_result['data']['proNetwork']:
            analytics = analytics_result['data']['proNetwork']['networkAnalytics']
            print(f"Network Analytics:")
            print(f"  - Total Countries: {analytics['totalCountries']}")
            print(f"  - Total Groups: {analytics['totalGroups']}")
            print(f"  - Total Members: {analytics['totalMembers']}")
        else:
            print("ProNetwork analytics fetch failed")
        
        # Step 6: Fetch pro network groups
        print(f"\nFetching proNetwork groups for {pro_urlname}...")
        pro_query = """
        query ($urlname: ID) {
          proNetwork(urlname: $urlname) {
            groupsSearch(input: {desc: true}) {
              totalCount
              pageInfo {
                endCursor
              }
              edges {
                node {
                  id
                  name
                }
              }
            }
          }
        }
        """
        
        pro_result = auth.graphql_call(pro_query, variables)
        
        if 'data' in pro_result and pro_result['data']['proNetwork']:
            groups_data = pro_result['data']['proNetwork']['groupsSearch']
            groups = [edge['node'] for edge in groups_data['edges']]
            print(f"Found {groups_data['totalCount']} total groups, showing {len(groups)}:")
            
            for group in groups[:5]:  # Show first 5 groups
                print(f"  - {group['name']} (ID: {group['id']})")
        else:
            print("ProNetwork groups fetch failed")
        
        # Step 7: Fetch past events
        print(f"\nFetching past events for {pro_urlname}...")
        events_query = """
        query($urlname: ID!) {
          proNetwork(urlname: $urlname) {
            eventsSearch(input: { first: 10000 , filter: { status: "PAST" }}) {
              totalCount
              pageInfo {
                endCursor
              }
              edges {
                node {
                  id
                  title
                }
              }
            }
          }
        }
        """
        
        events_result = auth.graphql_call(events_query, variables)
        
        if 'data' in events_result and events_result['data']['proNetwork']:
            events_data = events_result['data']['proNetwork']['eventsSearch']
            events = [edge['node'] for edge in events_data['edges']]
            print(f"Found {events_data['totalCount']} past events, showing {len(events)}:")
            
            for event in events:
                print(f"  - {event['title']} (ID: {event['id']})")
        else:
            print("Past events fetch failed")
        
        # Step 8: Fetch event details for each event
        print(f"\nFetching event details for {len(events)} events...")
        event_query = """
        query($eventId: ID!) {
  event(id: $eventId) {
    title
    eventUrl
    dateTime
    duration
    eventHosts {
      memberId
      name
    }
    group {
      id
      name
      urlname
    }
    rsvps (first: 1000) {
      edges {
        node {
          id
          member {
            name
          }
        }
      }
    }
  }
}
        """
        
        event_details = []
        for i, event in enumerate(events):
            print(f"  Fetching details for event {i+1}/{len(events)}: {event['title']}")
            try:
                event_variables = {"eventId": event['id']}
                event_result = auth.graphql_call(event_query, event_variables)
                
                if 'data' in event_result and event_result['data']['event']:
                    event_data = event_result['data']['event']
                    rsvps = [edge['node'] for edge in event_data['rsvps']['edges']]
                    print(f"    ✓ {event_data['title']} - {len(rsvps)} RSVPs")
                    event_details.append(event_result)
                else:
                    print(f"    ✗ Failed to fetch details for {event['title']}")
                    event_details.append(None)
            except Exception as e:
                print(f"    ✗ Error fetching {event['title']}: {e}")
                event_details.append(None)
            
            # Add delay to avoid rate limits
            time.sleep(0.5)
        
        # Step 9: Save data to JSON file
        with open('meetup_data.json', 'w') as f:
            json.dump({
                'profile': profile,
                'raw_profile': profile_result,
                'raw_pro': pro_result,
                'raw_analytics': analytics_result,
                'raw_events': events_result,
                'raw_event_details': event_details
            }, f, indent=2)
        print("✓ Data saved to meetup_data.json")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()