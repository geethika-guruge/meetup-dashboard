import json
import os
import urllib.request
import urllib.parse
import logging
import boto3
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_secret():
    """Get credentials from AWS Secrets Manager."""
    secret_name = os.environ.get('MEETUP_SECRET_NAME')
    if not secret_name:
        logger.error("MEETUP_SECRET_NAME environment variable not set")
        return None
    
    session = boto3.session.Session()
    client = session.client('secretsmanager', region_name='ap-southeast-2')
    
    try:
        logger.info(f"Getting secret: {secret_name}")
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Error getting secret: {e}")
        return None

def lambda_handler(event, context):
    """Lambda function to fetch Meetup data and return analytics."""
    
    logger.info(f"Lambda invoked with event: {json.dumps(event, default=str)}")
    logger.info(f"Context: {context}")
    
    # Handle CORS preflight requests
    if event.get('httpMethod') == 'OPTIONS':
        logger.info("Handling CORS preflight request")
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': ''
        }
    
    logger.info("Starting Meetup data fetch process")
    
    # Get credentials from Secrets Manager
    credentials = get_secret()
    if not credentials:
        logger.error("Failed to get credentials from Secrets Manager")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': 'Failed to get credentials'})
        }
    
    client_id = credentials.get('MEETUP_CLIENT_ID')
    client_secret = credentials.get('MEETUP_CLIENT_SECRET')
    access_token = credentials.get('MEETUP_ACCESS_TOKEN')
    pro_urlname = credentials.get('MEETUP_PRO_URLNAME')
    
    logger.info(f"Environment variables - Client ID: {'SET' if client_id else 'NOT SET'}")
    logger.info(f"Environment variables - Client Secret: {'SET' if client_secret else 'NOT SET'}")
    logger.info(f"Environment variables - Access Token: {'SET' if access_token else 'NOT SET'}")
    logger.info(f"Environment variables - Pro URL Name: {pro_urlname if pro_urlname else 'NOT SET'}")
    
    if not all([client_id, client_secret, access_token, pro_urlname]):
        logger.warning("Missing environment variables, returning mock data")
        mock_data = {
            'success': True,
            'data': {
                'totalCountries': 25,
                'totalGroups': 150,
                'totalMembers': 12500,
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
                    }
                ]
            },
            'note': 'Mock data - configure environment variables for real data'
        }
        logger.info(f"Returning mock data: {mock_data}")
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(mock_data)
        }
    
    try:
        logger.info("All environment variables present, attempting real API call")
        
        # Calculate date one year ago
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S+12:00')
        
        # Fetch pro network analytics and groups
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
        
        logger.info(f"Making GraphQL call for pro network: {pro_urlname}")
        result = graphql_call(access_token, combined_query, {"urlname": pro_urlname})
        logger.info(f"GraphQL response: {json.dumps(result, default=str)}")
        
        if 'data' in result and result['data']['proNetwork']:
            pro_network = result['data']['proNetwork']
            analytics = pro_network['networkAnalytics']
            groups_data = pro_network['groupsSearch']
            groups = [edge['node'] for edge in groups_data['edges']]
            
            logger.info(f"Successfully extracted analytics: {analytics}")
            logger.info(f"Successfully extracted {len(groups)} groups")
            
            # Fetch events count for each group in the last 12 months
            for group in groups:
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
                    
                    events_result = graphql_call(access_token, events_query, {
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
                    else:
                        group['eventsLast12Months'] = 0
                        group['avgRsvpsLast12Months'] = 0
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch events for group {group['id']}: {str(e)}")
                    group['eventsLast12Months'] = 0
            
            response_data = {
                'success': True,
                'data': {
                    'totalCountries': analytics['totalCountries'],
                    'totalGroups': analytics['totalGroups'],
                    'totalMembers': analytics['totalMembers'],
                    'groups': groups
                }
            }
            logger.info(f"Returning successful response with {len(groups)} groups")
            
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps(response_data)
            }
        else:
            logger.error(f"Invalid response structure: {analytics_result}")
            error_response = {'error': 'Failed to fetch analytics data'}
            return {
                'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps(error_response)
            }
            
    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}", exc_info=True)
        error_response = {'error': str(e)}
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(error_response)
        }

def graphql_call(access_token, query, variables=None):
    """Make authenticated GraphQL API call using urllib."""
    logger.info("Starting GraphQL API call")
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
        logger.info(f"GraphQL variables: {variables}")
    
    data = json.dumps(payload).encode('utf-8')
    logger.info(f"GraphQL payload size: {len(data)} bytes")
    
    req = urllib.request.Request(
        "https://api.meetup.com/gql-ext",
        data=data,
        headers={
            "Authorization": f"Bearer {access_token[:10]}...",  # Log partial token for security
            "Content-Type": "application/json"
        }
    )
    
    logger.info("Making HTTP request to Meetup GraphQL API")
    
    try:
        with urllib.request.urlopen(req) as response:
            logger.info(f"HTTP response status: {response.status}")
            response_data = response.read().decode('utf-8')
            logger.info(f"Response data size: {len(response_data)} bytes")
            
            parsed_response = json.loads(response_data)
            logger.info("Successfully parsed JSON response")
            return parsed_response
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"HTTP Error {e.code}: {error_body}")
        raise Exception(f"GraphQL call failed: {e.code} - {error_body}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise Exception(f"Failed to parse JSON response: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in GraphQL call: {str(e)}")
        raise Exception(f"GraphQL call failed: {str(e)}")