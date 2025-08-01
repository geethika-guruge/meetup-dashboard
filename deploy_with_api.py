#!/usr/bin/env python3
"""
Deploy assets with API Gateway URL integration.
"""

import json
import boto3
import re

def update_script_with_api_url():
    """Update script.js with the actual API Gateway URL from CDK outputs."""
    
    # Read CDK outputs
    try:
        with open('cdk-outputs.json', 'r') as f:
            outputs = json.load(f)
        
        # Use the API Gateway URL from deployment output
        api_url = "https://ctbb1xv1y4.execute-api.ap-southeast-2.amazonaws.com/prod/"
        meetup_endpoint = f"{api_url}meetup"
        
        # Update script.js
        with open('script.js', 'r') as f:
            content = f.read()
        
        # Replace the placeholder URL
        updated_content = re.sub(
            r"const response = await fetch\('/api/meetup',",
            f"const response = await fetch('{meetup_endpoint}',",
            content
        )
        
        with open('script.js', 'w') as f:
            f.write(updated_content)
        
        print(f"✓ Updated script.js with API Gateway URL: {meetup_endpoint}")
        return meetup_endpoint
        
    except Exception as e:
        print(f"Error updating script.js: {e}")
        return None

def deploy_assets():
    """Deploy assets to S3 bucket."""
    try:
        with open('cdk-outputs.json', 'r') as f:
            outputs = json.load(f)
        
        stack_name = list(outputs.keys())[0]
        bucket_name = outputs[stack_name]['S3BucketName']
        
        s3_client = boto3.client('s3')
        
        # Files to upload
        files = [
            ('index.html', 'text/html'),
            ('styles.css', 'text/css'),
            ('script.js', 'application/javascript'),
            ('error.html', 'text/html'),
            ('favicon.svg', 'image/svg+xml')
        ]
        
        for filename, content_type in files:
            try:
                s3_client.upload_file(
                    filename,
                    bucket_name,
                    filename,
                    ExtraArgs={'ContentType': content_type}
                )
                print(f"✓ Uploaded {filename}")
            except Exception as e:
                print(f"✗ Failed to upload {filename}: {e}")
        
        print(f"✓ Assets deployed to bucket: {bucket_name}")
        
    except Exception as e:
        print(f"Error deploying assets: {e}")

if __name__ == "__main__":
    print("Updating script.js with API Gateway URL...")
    api_url = update_script_with_api_url()
    
    if api_url:
        print("Deploying assets to S3...")
        deploy_assets()
        print("✓ Deployment complete!")
    else:
        print("✗ Deployment failed - could not update API URL")