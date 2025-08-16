import json
import os
import logging
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB client
dynamodb = boto3.resource('dynamodb')

def decimal_default(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def lambda_handler(event, context):
    """Lambda function to read data from DynamoDB table."""
    
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
    
    table_name = os.environ.get('DYNAMODB_TABLE_NAME')
    if not table_name:
        logger.error("DYNAMODB_TABLE_NAME environment variable not set")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': 'DynamoDB table not configured'}, default=decimal_default)
        }
    
    try:
        table = dynamodb.Table(table_name)
        
        # Get the latest analytics data
        analytics_response = table.query(
            IndexName='DataTypeIndex',
            KeyConditionExpression=Key('data_type').eq('pro_network_analytics'),
            ScanIndexForward=False,  # Sort by timestamp descending
            Limit=1
        )
        
        # Get the latest groups data
        groups_response = table.query(
            IndexName='DataTypeIndex',
            KeyConditionExpression=Key('data_type').eq('group_details'),
            ScanIndexForward=False,  # Sort by timestamp descending
            Limit=50  # Get up to 50 groups
        )
        
        if not analytics_response['Items']:
            logger.warning("No analytics data found in DynamoDB")
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'No data available. Please refresh data first.'}, default=decimal_default)
            }
        
        # Extract analytics data
        analytics_item = analytics_response['Items'][0]
        
        # Extract groups data and get events metrics
        groups = []
        for item in groups_response['Items']:
            group_id = item['group_id']
            
            # Get events summary for this group
            events_response = table.query(
                KeyConditionExpression=Key('pk').eq(f'GROUP#{group_id}') & Key('sk').begins_with('EVENTS_SUMMARY#'),
                ScanIndexForward=False,  # Sort by timestamp descending
                Limit=1
            )
            
            events_count = 0
            avg_rsvps = 0
            
            if events_response['Items']:
                events_item = events_response['Items'][0]
                total_events_all_time = events_item.get('total_events', 0)
                logger.info(f"Group {group_id}: Found {total_events_all_time} total events")
                
                # Get individual events to calculate metrics for last 12 months
                events_details_response = table.query(
                    KeyConditionExpression=Key('pk').eq(f'GROUP#{group_id}') & Key('sk').begins_with('EVENT#'),
                    ScanIndexForward=False,  # Sort by timestamp descending
                    Limit=100  # Get more events to filter by date
                )
                
                if events_details_response['Items']:
                    # Filter events from last 12 months
                    twelve_months_ago = datetime.now() - timedelta(days=365)
                    recent_events = []
                    
                    for event in events_details_response['Items']:
                        event_datetime_str = event.get('event_datetime')
                        if event_datetime_str:
                            try:
                                # Handle different datetime formats
                                if 'T' in event_datetime_str:
                                    # ISO format: 2024-01-15T10:00:00+12:00 or 2024-01-15T10:00:00Z
                                    event_datetime_str = event_datetime_str.replace('Z', '+00:00')
                                    event_datetime = datetime.fromisoformat(event_datetime_str)
                                else:
                                    # Simple date format: 2024-01-15
                                    event_datetime = datetime.strptime(event_datetime_str, '%Y-%m-%d')
                                
                                # Remove timezone info for comparison
                                if event_datetime.tzinfo:
                                    event_datetime = event_datetime.replace(tzinfo=None)
                                
                                if event_datetime >= twelve_months_ago:
                                    recent_events.append(event)
                            except (ValueError, TypeError) as e:
                                # Log the problematic datetime for debugging
                                logger.warning(f"Failed to parse datetime '{event_datetime_str}': {e}")
                                continue
                    
                    events_count = len(recent_events)
                    logger.info(f"Group {group_id}: Found {events_count} events in last 12 months out of {len(events_details_response['Items'])} total")
                    
                    if recent_events:
                        total_rsvps = sum(event.get('total_rsvps', 0) for event in recent_events)
                        avg_rsvps = round(total_rsvps / len(recent_events), 1)
                        logger.info(f"Group {group_id}: Average RSVPs = {avg_rsvps} (total: {total_rsvps}, events: {len(recent_events)})")
                    else:
                        avg_rsvps = 0
                        logger.info(f"Group {group_id}: No recent events found")
            
            group_data = {
                'id': group_id,
                'name': item['group_name'],
                'country': item['country'],
                'foundedDate': item['founded_date'],
                'stats': {
                    'memberCounts': {
                        'all': item['member_count']
                    }
                },
                'eventsLast12Months': events_count,
                'avgRsvpsLast12Months': avg_rsvps
            }
            groups.append(group_data)
        
        # Build response data
        response_data = {
            'success': True,
            'data': {
                'totalCountries': analytics_item['total_countries'],
                'totalGroups': analytics_item['total_groups'],
                'totalMembers': analytics_item['total_members'],
                'groups': groups
            }
        }
        
        logger.info(f"Successfully retrieved data for {len(groups)} groups")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response_data, default=decimal_default)
        }
        
    except Exception as e:
        logger.error(f"Error reading from DynamoDB: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': f'Database error: {str(e)}'}, default=decimal_default)
        }