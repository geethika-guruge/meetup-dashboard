#!/usr/bin/env python3
"""
Script to manually fix CloudFront access to S3 bucket
"""

import boto3
import json

def main():
    # Initialize AWS session
    session = boto3.Session(profile_name='sandpit-1-admin')
    s3_client = session.client('s3')
    cloudfront_client = session.client('cloudfront')
    
    bucket_name = "spastack-websitebucket75c24d94-vsxg9i6tkiky"
    
    # Get CloudFront distributions
    try:
        distributions = cloudfront_client.list_distributions()
        
        # Find our distribution
        distribution_id = None
        for dist in distributions['DistributionList']['Items']:
            if 'd3cm8349so6jga.cloudfront.net' in dist['DomainName']:
                distribution_id = dist['Id']
                break
        
        if not distribution_id:
            print("Could not find CloudFront distribution")
            return False
            
        print(f"Found CloudFront distribution: {distribution_id}")
        
        # Get distribution details
        dist_config = cloudfront_client.get_distribution(Id=distribution_id)
        
        # Check if Origin Access Control is configured
        origins = dist_config['Distribution']['DistributionConfig']['Origins']['Items']
        origin = origins[0]  # Assuming first origin is our S3 bucket
        
        print(f"Origin details: {json.dumps(origin, indent=2, default=str)}")
        
        # Create bucket policy for CloudFront access
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowCloudFrontServicePrincipal",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "cloudfront.amazonaws.com"
                    },
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    "Condition": {
                        "StringEquals": {
                            "AWS:SourceArn": f"arn:aws:cloudfront::722141136946:distribution/{distribution_id}"
                        }
                    }
                }
            ]
        }
        
        # Apply the bucket policy
        try:
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            print(f"✓ Successfully applied bucket policy for CloudFront access")
            return True
        except Exception as e:
            print(f"✗ Failed to apply bucket policy: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)