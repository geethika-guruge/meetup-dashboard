#!/bin/bash

PROFILE=${1:-default}
PROFILE_ARG=""
if [ "$PROFILE" != "default" ]; then
  PROFILE_ARG="--profile $PROFILE"
fi

BUCKET=$(aws cloudformation describe-stacks --stack-name MeetupDashboardStack --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' --output text $PROFILE_ARG)

if [ -z "$BUCKET" ]; then
  echo "❌ Could not find S3 bucket name from CloudFormation stack"
  exit 1
fi

echo "📦 Uploading static content to $BUCKET using profile: $PROFILE..."

aws s3 cp index.html s3://$BUCKET/ --content-type "text/html" $PROFILE_ARG && \
aws s3 cp styles.css s3://$BUCKET/ --content-type "text/css" $PROFILE_ARG && \
aws s3 cp script.js s3://$BUCKET/ --content-type "application/javascript" $PROFILE_ARG && \
aws s3 cp error.html s3://$BUCKET/ --content-type "text/html" $PROFILE_ARG && \
aws s3 cp favicon.svg s3://$BUCKET/ --content-type "image/svg+xml" $PROFILE_ARG

if [ $? -eq 0 ]; then
  echo "✅ Static content deployed successfully!"
else
  echo "❌ Failed to deploy static content"
  exit 1
fi