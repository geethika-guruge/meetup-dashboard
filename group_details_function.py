import json
import os
import urllib.request
import urllib.parse
import logging
import boto3

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
    """Lambda function to fetch detailed group information."""
    
    logger.info(f"Group details Lambda invoked with event: {json.dumps(event, default=str)}")
    
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
    
    # Get group ID from request body
    try:
        body = json.loads(event.get('body', '{}'))
        group_id = body.get('groupId')
        
        if not group_id:
            logger.error("Missing groupId in request body")
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'groupId is required'})
            }
        
        logger.info(f"Fetching details for group ID: {group_id}")
        
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
        
        if not client_id or not client_secret or not access_token:
            logger.warning("Missing required credentials in secret, returning mock data")
            logger.info(f"Credentials status - Client ID: {'SET' if client_id else 'NOT SET'}")
            logger.info(f"Credentials status - Client Secret: {'SET' if client_secret else 'NOT SET'}")
            logger.info(f"Credentials status - Access Token: {'SET' if access_token else 'NOT SET'}")
            mock_data = {
                'success': True,
                'data': {
                    'groupId': group_id,
                    'totalPastEvents': 25,
                    'events': [
                        {'id': '1', 'title': 'AWS Workshop - Serverless'},
                        {'id': '2', 'title': 'Cloud Security Best Practices'},
                        {'id': '3', 'title': 'Introduction to Kubernetes'}
                    ]
                }
            }
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps(mock_data)
            }
        
        # Get pro network urlname from credentials
        pro_urlname = credentials.get('MEETUP_PRO_URLNAME', 'aws-user-groups-new-zealand')
        
        logger.info(f"Making GraphQL call for group {group_id} in pro network: {pro_urlname}")
        
        # Fetch group events using direct group query
        events_query = """
        query ($id: ID!) {
          group(id: $id){
            events(status: PAST, sort: DESC){
              totalCount
              pageInfo {
                endCursor
              }
              edges {
                node {
                  dateTime
                  eventHosts{name}
                  title
                  rsvps{totalCount}
                }
              }
            }
          }
        }
        """
        
        variables = {"id": group_id}
        result = graphql_call(client_id, client_secret, access_token, events_query, variables)
        logger.info(f"GraphQL response: {json.dumps(result, default=str)}")
        
        if 'data' in result and result['data']['group']:
            events_data = result['data']['group']['events']
            events = [edge['node'] for edge in events_data['edges']]
            
            logger.info(f"Successfully extracted {events_data['totalCount']} total events, showing {len(events[:10])}")
            
            response_data = {
                'success': True,
                'data': {
                    'groupId': group_id,
                    'totalPastEvents': events_data['totalCount'],
                    'events': events[:10]  # Show first 10 events
                }
            }
            
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps(response_data)
            }
        else:
            logger.error(f"Invalid response structure or no events found: {result}")
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Group events not found'})
            }
            
    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(e)})
        }

def graphql_call(client_id, client_secret, access_token, query, variables=None):
    """Make authenticated GraphQL API call using urllib with both client credentials and access token."""
    logger.info("Starting GraphQL API call for group details")
    
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
            "Authorization": f"Bearer {access_token[:10]}...",
            "Content-Type": "application/json",
            "X-Meetup-Client-Id": client_id,
            "X-Meetup-Client-Secret": client_secret[:10] + "..."
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