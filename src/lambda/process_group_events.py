import json
import os
import urllib.request
import urllib.parse
import logging
import boto3
from datetime import datetime

# AWS clients
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

def store_group_events_in_dynamodb(result, group_id):
    """Store group events results in DynamoDB using single table design."""
    table_name = os.environ.get('DYNAMODB_TABLE_NAME')
    if not table_name:
        logger.warning("DYNAMODB_TABLE_NAME environment variable not set, skipping DynamoDB storage")
        return
    
    try:
        table = dynamodb.Table(table_name)
        timestamp = datetime.utcnow().isoformat()
        
        if 'data' in result and result['data'] and result['data']['group']:
            group_data = result['data']['group']
            events_data = group_data['events']
            
            # Store events summary
            table.put_item(
                Item={
                    'pk': f'GROUP#{group_id}',
                    'sk': f'EVENTS_SUMMARY#{timestamp}',
                    'data_type': 'group_events_summary',
                    'timestamp': timestamp,
                    'group_id': group_id,
                    'total_events': events_data['totalCount'],
                    'end_cursor': events_data['pageInfo']['endCursor'],
                    'events_retrieved': len(events_data['edges']),
                    'raw_data': events_data
                }
            )
            logger.info(f"Stored events summary for group {group_id} in DynamoDB")
            
            # Store individual events with RSVP details
            for i, edge in enumerate(events_data['edges']):
                event = edge['node']
                event_title_safe = event['title'][:50] if event['title'] else f"Event_{i+1}"
                
                # Store event details
                table.put_item(
                    Item={
                        'pk': f'GROUP#{group_id}',
                        'sk': f'EVENT#{event["dateTime"]}#{event_title_safe}',
                        'data_type': 'group_event_details',
                        'timestamp': timestamp,
                        'group_id': group_id,
                        'event_title': event['title'],
                        'event_datetime': event['dateTime'],
                        'event_hosts': event['eventHosts'],
                        'total_rsvps': event['rsvps']['totalCount'],
                        'rsvps_retrieved': len(event['rsvps']['edges']),
                        'raw_data': event
                    }
                )
                
                # Store RSVP details for each event
                for rsvp_edge in event['rsvps']['edges']:
                    rsvp = rsvp_edge['node']
                    member = rsvp['member']
                    table.put_item(
                        Item={
                            'pk': f'MEMBER#{member["id"]}',
                            'sk': f'RSVP#{event["dateTime"]}#{group_id}',
                            'data_type': 'member_rsvp',
                            'timestamp': timestamp,
                            'member_id': member['id'],
                            'member_name': member['name'],
                            'group_id': group_id,
                            'event_title': event['title'],
                            'event_datetime': event['dateTime'],
                            'is_first_event': rsvp['isFirstEvent'],
                            'raw_data': rsvp
                        }
                    )
            
            logger.info(f"Stored {len(events_data['edges'])} events and their RSVPs for group {group_id} in DynamoDB")
            
    except Exception as e:
        logger.error(f"Error storing group events in DynamoDB: {str(e)}", exc_info=True)
        # Don't fail the entire function if DynamoDB storage fails

def process_group_events(group_id, access_token):
    """Process events for a specific group ID."""
    
    # The GraphQL query for group events with RSVP details
    query = """
    query ($id: ID!) {
      group(id: $id) {
        events(status: PAST, sort: DESC) {
          totalCount
          pageInfo {
            endCursor
          }
          edges {
            node {
              title
              dateTime
              eventHosts {
                memberId
                name
              }
              rsvps (first: 1000) {
                totalCount
                edges{
                  node{
                    isFirstEvent
                    member{
                      id
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    try:
        logger.info(f"Processing events for group ID: {group_id}")
        
        # Make the GraphQL call
        result = graphql_call(access_token, query, {"id": group_id})
        
        # Store results in DynamoDB
        store_group_events_in_dynamodb(result, group_id)
        
        # Print the complete results to console
        print("=" * 100)
        print(f"GROUP EVENTS QUERY RESULTS FOR GROUP ID: {group_id}")
        print("=" * 100)
        print(json.dumps(result, indent=2, default=str))
        print("=" * 100)
        
        # Also log the results
        logger.info(f"GraphQL Query Results for group {group_id}:")
        logger.info(json.dumps(result, indent=2, default=str))
        
        # Extract and print specific data sections
        if 'data' in result and result['data'] and result['data']['group']:
            group_data = result['data']['group']
            events_data = group_data['events']
            
            print(f"\nEVENTS SUMMARY FOR GROUP {group_id}:")
            print("-" * 60)
            print(f"Total Events: {events_data['totalCount']}")
            print(f"End Cursor: {events_data['pageInfo']['endCursor']}")
            print(f"Events Retrieved: {len(events_data['edges'])}")
            
            print(f"\nEVENT DETAILS ({len(events_data['edges'])} events):")
            print("-" * 60)
            
            for i, edge in enumerate(events_data['edges'], 1):
                event = edge['node']
                print(f"\n{i}. {event['title']}")
                print(f"   Date/Time: {event['dateTime']}")
                
                # Event hosts
                if event['eventHosts']:
                    hosts_str = ', '.join([f"{host['name']} (ID: {host['memberId']})" for host in event['eventHosts']])
                    print(f"   Hosts: {hosts_str}")
                else:
                    print("   Hosts: None")
                
                # RSVP information
                rsvps = event['rsvps']
                print(f"   Total RSVPs: {rsvps['totalCount']}")
                
                if rsvps['edges']:
                    print(f"   RSVP Details ({len(rsvps['edges'])} members):")
                    for j, rsvp_edge in enumerate(rsvps['edges'], 1):
                        rsvp = rsvp_edge['node']
                        member = rsvp['member']
                        first_event_indicator = " (FIRST EVENT)" if rsvp['isFirstEvent'] else ""
                        print(f"     {j}. {member['name']} (ID: {member['id']}){first_event_indicator}")
                else:
                    print("   RSVP Details: No RSVP data available")
                
                print()  # Empty line between events
        
        else:
            print(f"No group data found for group ID: {group_id}")
            logger.warning(f"No group data found for group ID: {group_id}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error processing group {group_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"ERROR processing group {group_id}: {error_msg}")
        raise

def lambda_handler(event, context):
    """Lambda function triggered by SQS messages containing group IDs."""
    
    logger.info(f"Lambda invoked with event: {json.dumps(event, default=str)}")
    
    # Get credentials from Secrets Manager
    credentials = get_secret()
    if not credentials:
        logger.error("Failed to get credentials from Secrets Manager")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to get credentials'})
        }
    
    access_token = credentials.get('MEETUP_ACCESS_TOKEN')
    
    if not access_token:
        logger.error("Missing required credential: access_token")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Missing required credentials'})
        }
    
    # Process each SQS record
    successful_records = []
    failed_records = []
    
    for record in event.get('Records', []):
        try:
            # Extract group ID from SQS message
            message_body = record['body']
            logger.info(f"Processing SQS message: {message_body}")
            
            # Handle both plain text group ID and JSON message formats
            try:
                # Try to parse as JSON first
                message_data = json.loads(message_body)
                if isinstance(message_data, dict):
                    group_id = message_data.get('group_id') or message_data.get('groupId') or message_data.get('id')
                else:
                    group_id = str(message_data)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text group ID
                group_id = message_body.strip()
            
            if not group_id:
                logger.error(f"No group ID found in message: {message_body}")
                failed_records.append({
                    'messageId': record.get('messageId'),
                    'error': 'No group ID found in message'
                })
                continue
            
            logger.info(f"Processing group ID: {group_id}")
            
            # Process the group events
            result = process_group_events(group_id, access_token)
            
            successful_records.append({
                'messageId': record.get('messageId'),
                'groupId': group_id,
                'status': 'success'
            })
            
            logger.info(f"Successfully processed group ID: {group_id}")
            
        except Exception as e:
            error_msg = f"Failed to process record {record.get('messageId', 'unknown')}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            failed_records.append({
                'messageId': record.get('messageId'),
                'error': error_msg
            })
    
    # Summary
    print("\n" + "=" * 100)
    print("PROCESSING SUMMARY")
    print("=" * 100)
    print(f"Total Records: {len(event.get('Records', []))}")
    print(f"Successful: {len(successful_records)}")
    print(f"Failed: {len(failed_records)}")
    
    if failed_records:
        print("\nFailed Records:")
        for failed in failed_records:
            print(f"  - Message ID: {failed['messageId']}, Error: {failed['error']}")
    
    logger.info(f"Processing complete. Success: {len(successful_records)}, Failed: {len(failed_records)}")
    
    return {
        'statusCode': 200 if not failed_records else 207,  # 207 = Multi-Status (partial success)
        'body': json.dumps({
            'message': 'Processing complete',
            'successful': len(successful_records),
            'failed': len(failed_records),
            'successfulRecords': successful_records,
            'failedRecords': failed_records
        })
    }

# For local testing
if __name__ == "__main__":
    # Mock SQS event for local testing
    test_event = {
        'Records': [
            {
                'messageId': 'test-message-1',
                'body': '12345',  # Simple group ID
                'receiptHandle': 'test-receipt-handle-1'
            },
            {
                'messageId': 'test-message-2', 
                'body': '{"group_id": "67890"}',  # JSON format
                'receiptHandle': 'test-receipt-handle-2'
            }
        ]
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = "process_group_events"
            self.function_version = "$LATEST"
            self.invoked_function_arn = "arn:aws:lambda:ap-southeast-2:123456789012:function:process_group_events"
            self.memory_limit_in_mb = "256"
            self.remaining_time_in_millis = lambda: 60000
    
    mock_context = MockContext()
    
    print("Running lambda function locally...")
    result = lambda_handler(test_event, mock_context)
    print(f"Lambda result: {json.dumps(result, indent=2)}")
