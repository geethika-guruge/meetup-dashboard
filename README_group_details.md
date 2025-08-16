# Meetup Group Details Fetcher

A standalone Python script to fetch group details from the Meetup GraphQL API, based on the functionality in `src/lambda/lambda_function.py`.

## Features

- Fetches pro network analytics (total countries, groups, members)
- Retrieves detailed information for all groups in the network
- Calculates events and average RSVPs for the last 12 months
- Displays results in a formatted output
- Optionally saves results to JSON file
- Comprehensive logging and error handling

## Files

- `fetch_group_details.py` - Main script to fetch real data from Meetup API
- `test_group_details.py` - Demo script with mock data to show expected output
- `README_group_details.md` - This documentation file

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library)
- Valid Meetup API credentials

## Setup

### Option 1: Environment Variables (Recommended)

```bash
export MEETUP_ACCESS_TOKEN='your_access_token_here'
export MEETUP_PRO_URLNAME='your_pro_network_urlname'
```

### Option 2: Interactive Input

The script will prompt for credentials if environment variables are not set.

## Usage

### Run with Real Data

```bash
python3 fetch_group_details.py
```

### Run Demo with Mock Data

```bash
python3 test_group_details.py
```

## Output

The script displays:

1. **Network Analytics**: Total countries, groups, and members
2. **Group Details**: For each group:
   - Name and ID
   - Country and founded date
   - Member count
   - Events in last 12 months
   - Average RSVPs per event

### Sample Output

```
================================================================================
MEETUP GROUP DETAILS - GRAPHQL RESPONSE
================================================================================

NETWORK ANALYTICS:
  Total Countries: 25
  Total Groups: 150
  Total Members: 12,500

GROUP DETAILS (4 groups):
--------------------------------------------------------------------------------

1. AWS User Group Auckland
   ID: 1
   Country: New Zealand
   Founded: 2020-01-15
   Members: 1,500
   Events (12 months): 8
   Avg RSVPs (12 months): 45.2

2. AWS User Group Wellington
   ID: 2
   Country: New Zealand
   Founded: 2019-03-20
   Members: 1,237
   Events (12 months): 12
   Avg RSVPs (12 months): 38.7
```

## GraphQL Queries Used

The script uses two main GraphQL queries:

1. **Network Overview Query**: Fetches analytics and basic group information
2. **Group Events Query**: For each group, fetches event count and RSVP data for the last 12 months

## Error Handling

- Network connectivity issues
- API authentication errors
- GraphQL query errors
- Invalid response formats
- Missing or malformed data

## Logging

The script provides detailed logging at INFO level, including:
- API call progress
- Data processing steps
- Error details
- Performance metrics

## Credentials

You need:
- **Access Token**: Your Meetup API access token
- **Pro URL Name**: The URL name of your pro network

These can be obtained from your Meetup API dashboard.

## Comparison with Lambda Function

This standalone script replicates the GraphQL functionality from `src/lambda/lambda_function.py` but:
- Runs locally instead of in AWS Lambda
- Prints results instead of returning HTTP responses
- Doesn't store data in DynamoDB
- Focuses specifically on group details fetching
