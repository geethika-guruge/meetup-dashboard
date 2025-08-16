#!/usr/bin/env python3
"""
Standalone Python script to fetch group details using Meetup GraphQL API.
This script mimics the functionality from src/lambda/lambda_function.py
but focuses on fetching and displaying group details directly.
"""

import json
import urllib.request
import urllib.parse
import logging
from datetime import datetime, timedelta
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MeetupGroupFetcher:
    """Class to handle fetching group details from Meetup GraphQL API."""
    
    def __init__(self, access_token, pro_urlname):
        """
        Initialize the fetcher with credentials.
        
        Args:
            access_token (str): Meetup API access token
            pro_urlname (str): Pro network URL name
        """
        self.access_token = access_token
        self.pro_urlname = pro_urlname
        self.api_url = "https://api.meetup.com/gql-ext"
    
    def graphql_call(self, query, variables=None):
        """
        Make authenticated GraphQL API call using urllib.
        
        Args:
            query (str): GraphQL query string
            variables (dict): Optional variables for the query
            
        Returns:
            dict: Parsed JSON response from the API
        """
        logger.info("Starting GraphQL API call")
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            logger.info(f"GraphQL variables provided: {list(variables.keys())}")
        
        data = json.dumps(payload).encode('utf-8')
        logger.info(f"GraphQL payload size: {len(data)} bytes")
        
        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        )
        
        logger.info("Making HTTP request to Meetup GraphQL API")
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                logger.info(f"HTTP response status: {response.status}")
                response_data = response.read().decode('utf-8')
                logger.info(f"Response data size: {len(response_data)} bytes")
                
                parsed_response = json.loads(response_data)
                
                # Check for GraphQL errors
                if 'errors' in parsed_response:
                    logger.error(f"GraphQL errors: {parsed_response['errors']}")
                    raise Exception(f"GraphQL errors: {parsed_response['errors']}")
                
                logger.info("Successfully parsed JSON response")
                return parsed_response
                
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
                logger.error(f"HTTP Error {e.code}: {error_body}")
            except:
                logger.error(f"HTTP Error {e.code}: Unable to read error body")
            raise Exception(f"GraphQL HTTP error: {e.code}")
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise Exception(f"Invalid JSON response from API")
        except Exception as e:
            logger.error(f"Unexpected error in GraphQL call: {str(e)}")
            raise Exception(f"GraphQL call failed: {str(e)}")
    
    def fetch_group_details(self):
        """
        Fetch group details from the Meetup GraphQL API.
        
        Returns:
            dict: Group details including analytics and individual group information
        """
        logger.info(f"Fetching group details for pro network: {self.pro_urlname}")
        
        # Calculate date one year ago for events filtering
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S+12:00')
        logger.info(f"Filtering events after: {one_year_ago}")
        
        # GraphQL query to fetch pro network analytics and groups
        combined_query = """
        query ($urlname: ID!) {
          proNetwork(urlname: $urlname) {
            networkAnalytics{
              totalCountries
              totalGroups
              totalMembers
            }
            groupsSearch(input: {desc: false}) {
              totalCount
              pageInfo {
                endCursor
              }
              edges {
                node {
                  id
                  country
                  name
                  foundedDate
                  stats{ memberCounts {all} }
                }
              }
            }
          }
        }
        """
        
        try:
            logger.info("Making initial GraphQL call for pro network data")
            result = self.graphql_call(combined_query, {"urlname": self.pro_urlname})
            
            if 'data' not in result or not result['data']['proNetwork']:
                raise Exception("Invalid response structure from API")
            
            pro_network = result['data']['proNetwork']
            analytics = pro_network['networkAnalytics']
            groups_data = pro_network['groupsSearch']
            groups = [edge['node'] for edge in groups_data['edges']]
            
            logger.info(f"Successfully extracted analytics: {analytics}")
            logger.info(f"Successfully extracted {len(groups)} groups")
            
            # Fetch events count for each group in the last 12 months
            logger.info("Fetching event details for each group...")
            for i, group in enumerate(groups, 1):
                logger.info(f"Processing group {i}/{len(groups)}: {group['name']}")
                
                try:
                    events_query = """
                    query ($id: ID!, $afterDateTime: DateTime!) {
                      group(id: $id) {
                        events(status: PAST, sort: DESC, filter: {afterDateTime: $afterDateTime}) {
                          totalCount
                          pageInfo {
                            endCursor
                          }
                          edges {
                            node {
                              rsvps {
                                totalCount
                              }
                            }
                          }
                        }
                      }
                    }
                    """
                    
                    events_result = self.graphql_call(events_query, {
                        "id": group['id'],
                        "afterDateTime": one_year_ago
                    })
                    
                    if 'data' in events_result and events_result['data']['group']:
                        events_data = events_result['data']['group']['events']
                        group['eventsLast12Months'] = events_data['totalCount']
                        
                        # Calculate average RSVPs
                        if events_data['edges']:
                            total_rsvps = sum(edge['node']['rsvps']['totalCount'] for edge in events_data['edges'])
                            group['avgRsvpsLast12Months'] = round(total_rsvps / len(events_data['edges']), 1)
                        else:
                            group['avgRsvpsLast12Months'] = 0
                            
                        logger.info(f"  Events: {group['eventsLast12Months']}, Avg RSVPs: {group['avgRsvpsLast12Months']}")
                    else:
                        group['eventsLast12Months'] = 0
                        group['avgRsvpsLast12Months'] = 0
                        logger.warning(f"  No events data found for group {group['id']}")
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch events for group {group['id']}: {str(e)}")
                    group['eventsLast12Months'] = 0
                    group['avgRsvpsLast12Months'] = 0
            
            # Compile final result
            result_data = {
                'networkAnalytics': analytics,
                'groups': groups,
                'totalGroupsProcessed': len(groups),
                'fetchedAt': datetime.now().isoformat()
            }
            
            logger.info("Successfully fetched all group details")
            return result_data
            
        except Exception as e:
            logger.error(f"Error fetching group details: {str(e)}")
            raise
    
    def print_group_details(self, group_details):
        """
        Print group details in a formatted way.
        
        Args:
            group_details (dict): Group details data to print
        """
        print("\n" + "="*80)
        print("MEETUP GROUP DETAILS - GRAPHQL RESPONSE")
        print("="*80)
        
        # Print network analytics
        analytics = group_details['networkAnalytics']
        print(f"\nNETWORK ANALYTICS:")
        print(f"  Total Countries: {analytics['totalCountries']}")
        print(f"  Total Groups: {analytics['totalGroups']}")
        print(f"  Total Members: {analytics['totalMembers']:,}")
        
        # Print group details
        groups = group_details['groups']
        print(f"\nGROUP DETAILS ({len(groups)} groups):")
        print("-" * 80)
        
        for i, group in enumerate(groups, 1):
            print(f"\n{i}. {group['name']}")
            print(f"   ID: {group['id']}")
            print(f"   Country: {group['country']}")
            print(f"   Founded: {group['foundedDate']}")
            print(f"   Members: {group['stats']['memberCounts']['all']:,}")
            print(f"   Events (12 months): {group['eventsLast12Months']}")
            print(f"   Avg RSVPs (12 months): {group['avgRsvpsLast12Months']}")
        
        print(f"\nFetched at: {group_details['fetchedAt']}")
        print("="*80)


def get_credentials_from_env():
    """
    Get credentials from environment variables.
    
    Returns:
        tuple: (access_token, pro_urlname) or (None, None) if not found
    """
    access_token = os.environ.get('MEETUP_ACCESS_TOKEN')
    pro_urlname = os.environ.get('MEETUP_PRO_URLNAME')
    
    return access_token, pro_urlname


def get_credentials_from_input():
    """
    Get credentials from user input.
    
    Returns:
        tuple: (access_token, pro_urlname)
    """
    print("Please provide your Meetup API credentials:")
    access_token = input("Access Token: ").strip()
    pro_urlname = input("Pro Network URL Name: ").strip()
    
    return access_token, pro_urlname


def main():
    """Main function to run the group details fetcher."""
    print("Meetup Group Details Fetcher")
    print("=" * 40)
    
    # Try to get credentials from environment variables first
    access_token, pro_urlname = get_credentials_from_env()
    
    if not access_token or not pro_urlname:
        logger.info("Credentials not found in environment variables")
        print("\nCredentials not found in environment variables.")
        print("You can set them using:")
        print("  export MEETUP_ACCESS_TOKEN='your_token'")
        print("  export MEETUP_PRO_URLNAME='your_pro_urlname'")
        print("\nOr provide them now:")
        
        access_token, pro_urlname = get_credentials_from_input()
    
    if not access_token or not pro_urlname:
        logger.error("Missing required credentials")
        print("Error: Both access token and pro URL name are required!")
        sys.exit(1)
    
    logger.info(f"Using pro network: {pro_urlname}")
    
    try:
        # Create fetcher and get group details
        fetcher = MeetupGroupFetcher(access_token, pro_urlname)
        group_details = fetcher.fetch_group_details()
        
        # Print the results
        fetcher.print_group_details(group_details)
        
        # Optionally save to JSON file
        save_to_file = input("\nSave results to JSON file? (y/n): ").strip().lower()
        if save_to_file == 'y':
            filename = f"group_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(group_details, f, indent=2, default=str)
            print(f"Results saved to: {filename}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to fetch group details: {str(e)}")
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
