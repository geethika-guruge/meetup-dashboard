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

# Subdirectory for the meetup dashboard
SUBDIRECTORY="meetup-dashboard"

echo "📦 Uploading static content to $BUCKET/$SUBDIRECTORY/ using profile: $PROFILE..."

aws s3 cp src/web/index.html s3://$BUCKET/$SUBDIRECTORY/ --content-type "text/html" $PROFILE_ARG && \
aws s3 cp src/web/styles.css s3://$BUCKET/$SUBDIRECTORY/ --content-type "text/css" $PROFILE_ARG && \
aws s3 cp src/web/script.js s3://$BUCKET/$SUBDIRECTORY/ --content-type "application/javascript" $PROFILE_ARG && \
aws s3 cp src/web/error.html s3://$BUCKET/$SUBDIRECTORY/ --content-type "text/html" $PROFILE_ARG && \
aws s3 cp src/web/favicon.svg s3://$BUCKET/$SUBDIRECTORY/ --content-type "image/svg+xml" $PROFILE_ARG

if [ $? -eq 0 ]; then
  echo "✅ Static content deployed successfully to $SUBDIRECTORY/ subdirectory!"
  echo "🌐 Your site will be available at:"
  echo "   CloudFront: https://[cloudfront-domain]/$SUBDIRECTORY/"
  echo "   Custom Domain: https://projects.geethika.dev/$SUBDIRECTORY/"
else
  echo "❌ Failed to deploy static content"
  exit 1
fi