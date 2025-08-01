# Meetup API Integration Setup

## Files Created

1. **lambda_function.py** - AWS Lambda function to fetch Meetup data
2. **lambda_requirements.txt** - Python dependencies for Lambda
3. **deploy_lambda.py** - Deployment script for Lambda function
4. **Updated HTML/CSS/JS** - Added Meetup section to the SPA

## Setup Steps

### 1. Configure Environment Variables
Update the environment variables in `spa_stack.py`:
- `MEETUP_CLIENT_ID` - Your Meetup OAuth client ID
- `MEETUP_CLIENT_SECRET` - Your Meetup OAuth client secret  
- `MEETUP_ACCESS_TOKEN` - Your Meetup access token (get from meetup_auth.py)
- `MEETUP_PRO_URLNAME` - Your pro network URL name

### 2. Deploy CDK Stack
```bash
# Deploy the updated stack with Lambda and API Gateway
cdk deploy
```

### 3. Deploy Updated SPA with API Integration
```bash
# This script updates script.js with the API Gateway URL and deploys assets
python deploy_with_api.py
```

## How It Works

1. User clicks "Fetch Meetup Data" button
2. Frontend makes POST request to API Gateway endpoint
3. API Gateway triggers Lambda function
4. Lambda authenticates with Meetup API using stored access token
5. Lambda fetches pro network analytics
6. Data is returned through API Gateway to the frontend
7. Data is displayed in the SPA with country, group, and member counts

## CDK Stack Components

- **Lambda Function**: Handles Meetup API authentication and data fetching
- **API Gateway**: Provides REST endpoint with CORS enabled
- **S3 + CloudFront**: Existing SPA infrastructure
- **Environment Variables**: Secure storage of Meetup credentials

## Security Notes

- Credentials stored as Lambda environment variables
- CORS enabled on API Gateway for browser requests
- API Gateway provides additional security and monitoring features