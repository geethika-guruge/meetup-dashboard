#!/bin/bash

# Deployment script for SPA CloudFront S3 stack
# This script uses the sandpit-1-admin AWS profile for deployment

echo "Deploying SPA CloudFront S3 stack using sandpit-1-admin profile..."

# Check if the profile exists
if ! aws configure list-profiles | grep -q "sandpit-1-admin"; then
    echo "Error: sandpit-1-admin profile not found in AWS configuration"
    echo "Please configure the profile using: aws configure --profile sandpit-1-admin"
    exit 1
fi

# Bootstrap CDK if needed (only needs to be done once per account/region)
echo "Checking CDK bootstrap status..."
cdk bootstrap --profile sandpit-1-admin

# Deploy the stack
echo "Deploying the stack..."
cdk deploy --profile sandpit-1-admin

echo "Deployment complete!"
echo "You can now upload your web assets to the S3 bucket and access them via CloudFront."