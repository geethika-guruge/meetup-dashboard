import json
import os
import urllib.request
import urllib.parse
import logging
import boto3
from datetime import datetime

# AWS clients
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

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
            "Authorization": f"Bearer {access_token}",
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

def clean_dynamodb_table():
    """Clean all existing data from DynamoDB table."""
    table_name = os.environ.get('DYNAMODB_TABLE_NAME')
    if not table_name:
        logger.warning("DYNAMODB_TABLE_NAME environment variable not set, skipping cleanup")
        return
    
    try:
        table = dynamodb.Table(table_name)
        
        # Scan and delete all items
        response = table.scan()
        items = response.get('Items', [])
        
        logger.info(f"Found {len(items)} items to delete")
        
        # Delete items in batches
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(
                    Key={
                        'pk': item['pk'],
                        'sk': item['sk']
                    }
                )
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items = response.get('Items', [])
            
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={
                            'pk': item['pk'],
                            'sk': item['sk']
                        }
                    )
        
        logger.info("Successfully cleaned DynamoDB table")
        
    except Exception as e:
        logger.error(f"Error cleaning DynamoDB table: {str(e)}", exc_info=True)
        raise

def store_results_in_dynamodb(result, pro_urlname):
    """Store query results in DynamoDB using single table design."""
    table_name = os.environ.get('DYNAMODB_TABLE_NAME')
    if not table_name:
        logger.warning("DYNAMODB_TABLE_NAME environment variable not set, skipping DynamoDB storage")
        return
    
    try:
        table = dynamodb.Table(table_name)
        timestamp = datetime.utcnow().isoformat()
        
        # Store network analytics
        if 'data' in result and result['data'] and result['data']['proNetwork']:
            pro_network = result['data']['proNetwork']
            
            # Store network analytics summary
            analytics = pro_network['networkAnalytics']
            table.put_item(
                Item={
                    'pk': f'PRO_NETWORK#{pro_urlname}',
                    'sk': f'ANALYTICS#{timestamp}',
                    'data_type': 'pro_network_analytics',
                    'timestamp': timestamp,
                    'pro_urlname': pro_urlname,
                    'total_countries': analytics['totalCountries'],
                    'total_groups': analytics['totalGroups'],
                    'total_members': analytics['totalMembers'],
                    'raw_data': analytics
                }
            )
            logger.info("Stored network analytics in DynamoDB")
            
            # Store groups search summary
            groups_search = pro_network['groupsSearch']
            table.put_item(
                Item={
                    'pk': f'PRO_NETWORK#{pro_urlname}',
                    'sk': f'GROUPS_SEARCH#{timestamp}',
                    'data_type': 'pro_network_groups_search',
                    'timestamp': timestamp,
                    'pro_urlname': pro_urlname,
                    'total_count': groups_search['totalCount'],
                    'end_cursor': groups_search['pageInfo']['endCursor'],
                    'groups_retrieved': len(groups_search['edges']),
                    'raw_data': groups_search
                }
            )
            logger.info("Stored groups search summary in DynamoDB")
            
            # Store individual group details
            for edge in groups_search['edges']:
                node = edge['node']
                table.put_item(
                    Item={
                        'pk': f'GROUP#{node["id"]}',
                        'sk': f'DETAILS#{timestamp}',
                        'data_type': 'group_details',
                        'timestamp': timestamp,
                        'group_id': node['id'],
                        'group_name': node['name'],
                        'country': node['country'],
                        'founded_date': node['foundedDate'],
                        'member_count': node['stats']['memberCounts']['all'],
                        'pro_urlname': pro_urlname,
                        'raw_data': node
                    }
                )
            logger.info(f"Stored {len(groups_search['edges'])} group details in DynamoDB")
            
    except Exception as e:
        logger.error(f"Error storing results in DynamoDB: {str(e)}", exc_info=True)
        # Don't fail the entire function if DynamoDB storage fails

def lambda_handler(event, context):
    """Lambda function to run the specific GraphQL query and print results."""
    
    logger.info(f"Lambda invoked with event: {json.dumps(event, default=str)}")
    
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
    
    access_token = credentials.get('MEETUP_ACCESS_TOKEN')
    pro_urlname = credentials.get('MEETUP_PRO_URLNAME')
    
    if not access_token or not pro_urlname:
        logger.error("Missing required credentials: access_token or pro_urlname")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': 'Missing required credentials'})
        }

    # The specific GraphQL query to run
    query = """
    query ($urlname: ID!) {
        proNetwork(urlname: $urlname) {
            networkAnalytics {
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
                        stats {
                            memberCounts {
                                all
                            }
                        }
                    }
                }
            }
        }
    }
    """

    # Get SQS queue URL from environment
    sqs_queue_url = os.environ.get('MEETUP_GROUP_SQS_URL')
    if not sqs_queue_url:
        logger.error("MEETUP_GROUP_SQS_URL environment variable not set")
        # Continue, but skip SQS writing
    
    try:
        logger.info(f"Running GraphQL query for pro network: {pro_urlname}")
        
        # Clean DynamoDB table first
        logger.info("Cleaning DynamoDB table before storing new data")
        clean_dynamodb_table()
        
        # Make the GraphQL call
        result = graphql_call(access_token, query, {"urlname": pro_urlname})
        
        # Store results in DynamoDB
        store_results_in_dynamodb(result, pro_urlname)
        
        # Print the complete results to console
        print("=" * 80)
        print("GRAPHQL QUERY RESULTS")
        print("=" * 80)
        print(json.dumps(result, indent=2, default=str))
        print("=" * 80)
        
        # Also log the results
        logger.info("GraphQL Query Results:")
        logger.info(json.dumps(result, indent=2, default=str))
        
        # Extract and print specific data sections
        if 'data' in result and result['data'] and result['data']['proNetwork']:
            pro_network = result['data']['proNetwork']
            
            print("\nNETWORK ANALYTICS:")
            print("-" * 40)
            analytics = pro_network['networkAnalytics']
            print(f"Total Countries: {analytics['totalCountries']}")
            print(f"Total Groups: {analytics['totalGroups']}")
            print(f"Total Members: {analytics['totalMembers']}")
            
            print("\nGROUPS SEARCH RESULTS:")
            print("-" * 40)
            groups_search = pro_network['groupsSearch']
            print(f"Total Count: {groups_search['totalCount']}")
            print(f"End Cursor: {groups_search['pageInfo']['endCursor']}")
            
            print(f"\nGROUPS DETAILS ({len(groups_search['edges'])} groups):")
            print("-" * 40)
            for i, edge in enumerate(groups_search['edges'], 1):
                node = edge['node']
                print(f"{i}. {node['name']}")
                print(f"   ID: {node['id']}")
                print(f"   Country: {node['country']}")
                print(f"   Founded: {node['foundedDate']}")
                print(f"   Members: {node['stats']['memberCounts']['all']}")
                print()
                # Write group ID to SQS
                if sqs_queue_url:
                    try:
                        sqs_client.send_message(
                            QueueUrl=sqs_queue_url,
                            MessageBody=json.dumps({
                                'group_id': node['id'],
                                'group_name': node['name'],
                                'country': node['country']
                            })
                        )
                        logger.info(f"Sent group ID {node['id']} to SQS queue.")
                    except Exception as sqs_err:
                        logger.error(f"Failed to send group ID {node['id']} to SQS: {sqs_err}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'success': True,
                'message': 'Query executed successfully. Check logs for results.',
                'data': result
            })
        }
        
    except Exception as e:
        error_msg = f"Error executing GraphQL query: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"ERROR: {error_msg}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'success': False,
                'error': error_msg
            })
        }

# For local testing
if __name__ == "__main__":
    # Mock event and context for local testing
    test_event = {}
    
    class MockContext:
        def __init__(self):
            self.function_name = "query_pro_network"
            self.function_version = "$LATEST"
            self.invoked_function_arn = "arn:aws:lambda:ap-southeast-2:123456789012:function:query_pro_network"
            self.memory_limit_in_mb = "128"
            self.remaining_time_in_millis = lambda: 30000
    
    mock_context = MockContext()
    
    print("Running lambda function locally...")
    result = lambda_handler(test_event, mock_context)
    print(f"Lambda result: {json.dumps(result, indent=2)}")
