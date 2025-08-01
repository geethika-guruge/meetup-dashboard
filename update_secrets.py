#!/usr/bin/env python3
import boto3
import json
import sys

def update_meetup_secret():
    """Update AWS Secrets Manager secret with Meetup credentials."""
    
    # Get credentials from user input
    client_id = input("Enter MEETUP_CLIENT_ID: ").strip()
    client_secret = input("Enter MEETUP_CLIENT_SECRET: ").strip()
    access_token = input("Enter MEETUP_ACCESS_TOKEN: ").strip()
    
    if not all([client_id, client_secret, access_token]):
        print("Error: All credentials are required")
        sys.exit(1)
    
    # Create secret value
    secret_value = {
        "MEETUP_CLIENT_ID": client_id,
        "MEETUP_CLIENT_SECRET": client_secret,
        "MEETUP_ACCESS_TOKEN": access_token,
        "MEETUP_PRO_URLNAME": "aws-user-groups-new-zealand"
    }
    
    # Create Secrets Manager client
    session = boto3.Session(profile_name='sandpit-1-admin')
    secrets_client = session.client('secretsmanager', region_name='ap-southeast-2')
    
    secret_name = "meetup-dashboard/credentials"
    
    try:
        # Update the secret
        response = secrets_client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(secret_value)
        )
        print(f"✓ Secret updated: {response['ARN']}")
        print(f"Secret name: {secret_name}")
        
    except Exception as e:
        print(f"Error updating secret: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_meetup_secret()