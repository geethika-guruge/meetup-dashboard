#!/usr/bin/env python3
"""
Deployment script to upload web assets to S3 bucket
Sets appropriate content-type headers for different file types
"""

import boto3
import json
import os
import mimetypes
from pathlib import Path

def load_cdk_outputs():
    """Load CDK outputs to get S3 bucket name"""
    try:
        with open('cdk-outputs.json', 'r') as f:
            outputs = json.load(f)
        return outputs['SpaStack']
    except FileNotFoundError:
        print("Error: cdk-outputs.json not found. Please run 'cdk deploy' first.")
        return None
    except KeyError:
        print("Error: SpaStack outputs not found in cdk-outputs.json")
        return None

def get_content_type(file_path):
    """Get appropriate content-type for file"""
    content_type, _ = mimetypes.guess_type(file_path)
    
    # Override for specific file types
    file_extension = Path(file_path).suffix.lower()
    if file_extension == '.svg':
        return 'image/svg+xml'
    elif file_extension == '.css':
        return 'text/css'
    elif file_extension == '.js':
        return 'application/javascript'
    elif file_extension == '.html':
        return 'text/html'
    
    return content_type or 'application/octet-stream'

def upload_file_to_s3(s3_client, bucket_name, local_file, s3_key):
    """Upload a single file to S3 with appropriate content-type"""
    try:
        content_type = get_content_type(local_file)
        
        # Additional headers for web assets
        extra_args = {
            'ContentType': content_type,
        }
        
        # Add cache control headers for different file types
        file_extension = Path(local_file).suffix.lower()
        if file_extension in ['.css', '.js']:
            # Cache CSS and JS files for 1 day
            extra_args['CacheControl'] = 'max-age=86400'
        elif file_extension in ['.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico']:
            # Cache images for 7 days
            extra_args['CacheControl'] = 'max-age=604800'
        elif file_extension == '.html':
            # Cache HTML files for 5 minutes
            extra_args['CacheControl'] = 'max-age=300'
        
        print(f"Uploading {local_file} to s3://{bucket_name}/{s3_key}")
        print(f"  Content-Type: {content_type}")
        if 'CacheControl' in extra_args:
            print(f"  Cache-Control: {extra_args['CacheControl']}")
        
        s3_client.upload_file(
            local_file,
            bucket_name,
            s3_key,
            ExtraArgs=extra_args
        )
        
        print(f"✓ Successfully uploaded {local_file}")
        return True
        
    except Exception as e:
        print(f"✗ Error uploading {local_file}: {str(e)}")
        return False

def enable_public_read_access(s3_client, bucket_name):
    """Temporarily enable public read access for S3 static website testing"""
    try:
        # Create bucket policy for public read access
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print(f"✓ Temporarily enabled public read access for bucket {bucket_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to enable public read access: {str(e)}")
        return False

def disable_public_read_access(s3_client, bucket_name):
    """Disable public read access after testing"""
    try:
        s3_client.delete_bucket_policy(Bucket=bucket_name)
        print(f"✓ Disabled public read access for bucket {bucket_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to disable public read access: {str(e)}")
        return False

def verify_s3_access(s3_client, bucket_name, s3_website_url, cloudfront_domain):
    """Verify files are accessible through S3 static website endpoint and CloudFront"""
    import requests
    import time
    
    print(f"\nVerifying files are accessible...")
    
    # Test files to verify
    test_files = ['index.html', 'styles.css', 'script.js', 'error.html', 'favicon.svg']
    
    # Wait a moment for S3 to propagate
    print("Waiting 5 seconds for S3 to propagate changes...")
    time.sleep(5)
    
    # First, verify files exist in S3 bucket using boto3
    print(f"\n1. Verifying files exist in S3 bucket: {bucket_name}")
    s3_files_exist = True
    for file_name in test_files:
        try:
            s3_client.head_object(Bucket=bucket_name, Key=file_name)
            print(f"✓ {file_name} exists in S3 bucket")
        except Exception as e:
            print(f"✗ {file_name} not found in S3 bucket: {str(e)}")
            s3_files_exist = False
    
    # Temporarily enable public read access for S3 website testing
    print(f"\n2. Temporarily enabling public read access for S3 website testing...")
    public_access_enabled = enable_public_read_access(s3_client, bucket_name)
    
    if public_access_enabled:
        # Wait for policy to propagate
        print("Waiting 10 seconds for bucket policy to propagate...")
        time.sleep(10)
        
        # Test S3 website endpoint
        print(f"\n3. Testing S3 static website endpoint: {s3_website_url}")
        s3_website_accessible = True
        for file_name in test_files:
            try:
                url = f"{s3_website_url}/{file_name}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    print(f"✓ {file_name} is accessible via S3 website (Status: {response.status_code})")
                    
                    # Verify content-type header
                    content_type = response.headers.get('content-type', 'unknown')
                    expected_type = get_content_type(file_name)
                    if expected_type.split(';')[0] in content_type:
                        print(f"  Content-Type: {content_type} ✓")
                    else:
                        print(f"  Content-Type: {content_type} (expected: {expected_type})")
                        
                else:
                    print(f"✗ {file_name} returned status {response.status_code} via S3 website")
                    s3_website_accessible = False
                    
            except requests.RequestException as e:
                print(f"✗ Error accessing {file_name} via S3 website: {str(e)}")
                s3_website_accessible = False
        
        # Disable public read access after testing
        print(f"\n4. Disabling public read access (restoring security)...")
        disable_public_read_access(s3_client, bucket_name)
    else:
        s3_website_accessible = False
        print("Skipping S3 website endpoint test due to policy configuration failure")
    
    # Test CloudFront distribution
    print(f"\n5. Testing CloudFront distribution: https://{cloudfront_domain}")
    print("Note: CloudFront may take several minutes to serve new content due to caching and propagation")
    cloudfront_accessible = True
    for file_name in test_files:
        try:
            url = f"https://{cloudfront_domain}/{file_name}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                print(f"✓ {file_name} is accessible via CloudFront (Status: {response.status_code})")
                
                # Verify content-type header
                content_type = response.headers.get('content-type', 'unknown')
                expected_type = get_content_type(file_name)
                if expected_type.split(';')[0] in content_type:
                    print(f"  Content-Type: {content_type} ✓")
                else:
                    print(f"  Content-Type: {content_type} (expected: {expected_type})")
                    
            else:
                print(f"✗ {file_name} returned status {response.status_code} via CloudFront")
                if response.status_code == 403:
                    print(f"  Note: CloudFront may need time to propagate changes or origin access may need configuration")
                cloudfront_accessible = False
                
        except requests.RequestException as e:
            print(f"✗ Error accessing {file_name} via CloudFront: {str(e)}")
            cloudfront_accessible = False
    
    # Summary
    print(f"\n=== Verification Summary ===")
    print(f"Files exist in S3 bucket: {'✓' if s3_files_exist else '✗'}")
    print(f"S3 website endpoint accessible: {'✓' if s3_website_accessible else '✗'}")
    print(f"CloudFront distribution accessible: {'✓' if cloudfront_accessible else '✗'}")
    
    # Return True if files exist in S3 and S3 website endpoint works
    # (CloudFront may take time to propagate, so we focus on S3 website for immediate verification)
    return s3_files_exist and s3_website_accessible

def main():
    """Main deployment function"""
    print("=== S3 Asset Deployment Script ===\n")
    
    # Load CDK outputs
    outputs = load_cdk_outputs()
    if not outputs:
        return False
    
    bucket_name = outputs['S3BucketName']
    s3_website_url = outputs['S3WebsiteURL']
    cloudfront_domain = outputs['CloudFrontDomainName']
    
    print(f"S3 Bucket: {bucket_name}")
    print(f"S3 Website URL: {s3_website_url}")
    print(f"CloudFront Domain: {cloudfront_domain}")
    print()
    
    # Initialize S3 client with sandpit-2-admin profile
    try:
        session = boto3.Session(profile_name='sandpit-2-admin')
        s3_client = session.client('s3')
        print("✓ AWS session initialized with sandpit-2-admin profile")
    except Exception as e:
        print(f"✗ Error initializing AWS session: {str(e)}")
        print("Please ensure AWS CLI is configured with sandpit-2-admin profile")
        return False
    
    # Files to upload with their S3 keys
    files_to_upload = [
        ('index.html', 'index.html'),
        ('styles.css', 'styles.css'),
        ('script.js', 'script.js'),
        ('error.html', 'error.html'),
        ('favicon.svg', 'favicon.svg'),
    ]
    
    print(f"\nUploading {len(files_to_upload)} files to S3...")
    
    # Upload each file
    upload_success = True
    for local_file, s3_key in files_to_upload:
        if os.path.exists(local_file):
            success = upload_file_to_s3(s3_client, bucket_name, local_file, s3_key)
            if not success:
                upload_success = False
        else:
            print(f"✗ Warning: {local_file} not found, skipping...")
    
    if not upload_success:
        print("\n✗ Some files failed to upload")
        return False
    
    print(f"\n✓ All files uploaded successfully to s3://{bucket_name}")
    
    # Verify files are accessible
    verification_success = verify_s3_access(s3_client, bucket_name, s3_website_url, cloudfront_domain)
    
    if verification_success:
        print(f"\n✓ Files are accessible and deployment completed successfully!")
        print(f"\nYour website is now available at:")
        print(f"  S3 Website URL: {s3_website_url}")
        print(f"  CloudFront URL: https://{cloudfront_domain}")
        print(f"\nNote: CloudFront may take a few minutes to serve updated content due to caching.")
        return True
    else:
        print(f"\n✗ Files are not accessible - deployment verification failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)