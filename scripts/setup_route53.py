#!/usr/bin/env python3
"""
Script to set up Route 53 hosted zone for geethika.dev domain
This script will create the hosted zone if it doesn't exist and display the name servers
"""

import boto3
import json
from botocore.exceptions import ClientError

def check_hosted_zone_exists(route53_client, domain_name):
    """Check if hosted zone already exists for the domain"""
    try:
        response = route53_client.list_hosted_zones()
        for zone in response['HostedZones']:
            if zone['Name'].rstrip('.') == domain_name:
                return zone
        return None
    except ClientError as e:
        print(f"Error checking hosted zones: {e}")
        return None

def create_hosted_zone(route53_client, domain_name):
    """Create a new hosted zone for the domain"""
    try:
        response = route53_client.create_hosted_zone(
            Name=domain_name,
            CallerReference=f"{domain_name}-{int(__import__('time').time())}",
            HostedZoneConfig={
                'Comment': f'Hosted zone for {domain_name} - created for meetup dashboard',
                'PrivateZone': False
            }
        )
        return response['HostedZone']
    except ClientError as e:
        print(f"Error creating hosted zone: {e}")
        return None

def get_name_servers(route53_client, hosted_zone_id):
    """Get name servers for the hosted zone"""
    try:
        response = route53_client.get_hosted_zone(Id=hosted_zone_id)
        return response['DelegationSet']['NameServers']
    except ClientError as e:
        print(f"Error getting name servers: {e}")
        return None

def main():
    """Main function to set up Route 53 hosted zone"""
    domain_name = "geethika.dev"
    
    print(f"=== Route 53 Setup for {domain_name} ===\n")
    
    # Initialize Route 53 client
    try:
        session = boto3.Session(profile_name='sandpit-2-admin')
        route53_client = session.client('route53')
        print("✓ AWS session initialized with sandpit-2-admin profile")
    except Exception as e:
        print(f"✗ Error initializing AWS session: {str(e)}")
        print("Please ensure AWS CLI is configured with sandpit-2-admin profile")
        return False
    
    # Check if hosted zone already exists
    print(f"\nChecking if hosted zone for {domain_name} already exists...")
    existing_zone = check_hosted_zone_exists(route53_client, domain_name)
    
    if existing_zone:
        print(f"✓ Hosted zone already exists for {domain_name}")
        hosted_zone_id = existing_zone['Id']
        print(f"  Zone ID: {hosted_zone_id}")
    else:
        print(f"✗ No hosted zone found for {domain_name}")
        print(f"Creating new hosted zone...")
        
        new_zone = create_hosted_zone(route53_client, domain_name)
        if not new_zone:
            print("✗ Failed to create hosted zone")
            return False
        
        hosted_zone_id = new_zone['Id']
        print(f"✓ Created new hosted zone for {domain_name}")
        print(f"  Zone ID: {hosted_zone_id}")
    
    # Get name servers
    print(f"\nRetrieving name servers for {domain_name}...")
    name_servers = get_name_servers(route53_client, hosted_zone_id)
    
    if not name_servers:
        print("✗ Failed to retrieve name servers")
        return False
    
    print(f"✓ Name servers for {domain_name}:")
    for i, ns in enumerate(name_servers, 1):
        print(f"  {i}. {ns}")
    
    print(f"\n=== Next Steps ===")
    print(f"1. Update your domain registrar's DNS settings to use these name servers:")
    for ns in name_servers:
        print(f"   - {ns}")
    print(f"\n2. Wait for DNS propagation (can take up to 48 hours)")
    print(f"\n3. Verify DNS propagation with: dig NS {domain_name}")
    print(f"\n4. Deploy your CDK stack: cdk deploy --profile sandpit-2-admin")
    print(f"\n5. The custom domain will be: https://projects.{domain_name}/meetup-dashboard")
    
    # Save configuration for reference
    config = {
        "domain_name": domain_name,
        "hosted_zone_id": hosted_zone_id,
        "name_servers": name_servers,
        "custom_domain": f"projects.{domain_name}",
        "full_url": f"https://projects.{domain_name}/meetup-dashboard"
    }
    
    with open('route53-config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ Configuration saved to route53-config.json")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
