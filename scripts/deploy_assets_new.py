#!/usr/bin/env python3
"""
Deployment script for the new meetup dashboard stack
Deploys assets to /meetup-dashboard-new path
"""

import boto3
import json
import os
import sys
import argparse
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Import the deployment functions from the main script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from deploy_assets import (
    DeploymentError, DeploymentBackup, get_content_type, get_cache_control,
    calculate_file_hash, verify_file_integrity, upload_file_to_s3,
    enable_public_read_access, disable_public_read_access
)

def load_cdk_outputs_new() -> Optional[Dict]:
    """Load CDK outputs for the new stack"""
    try:
        with open('cdk-outputs-new.json', 'r') as f:
            outputs = json.load(f)
        return outputs['MeetupDashboardNewStack']
    except FileNotFoundError:
        raise DeploymentError("cdk-outputs-new.json not found. Please run 'cdk deploy --app \"python app_new.py\"' first.")
    except KeyError:
        raise DeploymentError("MeetupDashboardNewStack outputs not found in cdk-outputs-new.json")
    except json.JSONDecodeError:
        raise DeploymentError("Invalid JSON in cdk-outputs-new.json")

def verify_s3_access_new(s3_client, bucket_name: str, s3_website_url: str, cloudfront_domain: str, subdirectory: str, custom_domain_url: str):
    """Verify files are accessible through S3 static website endpoint and CloudFront for new stack"""
    import requests
    import time
    
    print(f"\nVerifying files are accessible under '{subdirectory}/' prefix...")
    
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
            s3_key = f"{subdirectory}/{file_name}"
            s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            print(f"✓ {s3_key} exists in S3 bucket")
        except Exception as e:
            print(f"✗ {s3_key} not found in S3 bucket: {str(e)}")
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
                url = f"{s3_website_url}/{subdirectory}/{file_name}"
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
            url = f"https://{cloudfront_domain}/{subdirectory}/{file_name}"
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
    
    # Test custom domain if configured
    custom_domain_accessible = True
    if custom_domain_url != 'Not configured':
        print(f"\n6. Testing custom domain: {custom_domain_url}")
        print("Note: Custom domain may take time to propagate DNS and SSL certificate")
        for file_name in test_files:
            try:
                url = f"{custom_domain_url.rstrip('/')}/{file_name}"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    print(f"✓ {file_name} is accessible via custom domain (Status: {response.status_code})")
                else:
                    print(f"✗ {file_name} returned status {response.status_code} via custom domain")
                    if response.status_code in [403, 502, 503]:
                        print(f"  Note: Custom domain may need time to propagate DNS and SSL certificate")
                    custom_domain_accessible = False
                    
            except requests.RequestException as e:
                print(f"✗ Error accessing {file_name} via custom domain: {str(e)}")
                print(f"  Note: This is expected if DNS hasn't propagated yet")
                custom_domain_accessible = False
    
    # Summary
    print(f"\n=== Verification Summary ===")
    print(f"Files exist in S3 bucket: {'✓' if s3_files_exist else '✗'}")
    print(f"S3 website endpoint accessible: {'✓' if s3_website_accessible else '✗'}")
    print(f"CloudFront distribution accessible: {'✓' if cloudfront_accessible else '✗'}")
    if custom_domain_url != 'Not configured':
        print(f"Custom domain accessible: {'✓' if custom_domain_accessible else '✗ (may need DNS propagation time)'}")
    
    # Return True if files exist in S3 and CloudFront works (S3 website endpoint is optional)
    return s3_files_exist and cloudfront_accessible

def deploy_assets_new(profile_name: str = 'gg-admin', 
                     subdirectory: str = 'meetup-dashboard-new',
                     verify_integrity: bool = True,
                     skip_verification: bool = False,
                     dry_run: bool = False) -> bool:
    """
    Main deployment function for the new stack
    """
    print("=== S3 Asset Deployment Script (New Stack) ===\n")
    
    try:
        # Load CDK outputs for new stack
        outputs = load_cdk_outputs_new()
        
        bucket_name = outputs['S3BucketNameNew']
        s3_website_url = outputs['S3WebsiteURLNew']
        cloudfront_domain = outputs['CloudFrontDomainNameNew']
        custom_domain_url = outputs.get('CustomDomainUrlNew', 'Not configured')
        
        print(f"Deployment Configuration:")
        print(f"  S3 Bucket: {bucket_name}")
        print(f"  S3 Website URL: {s3_website_url}")
        print(f"  CloudFront Domain: {cloudfront_domain}")
        print(f"  Custom Domain URL: {custom_domain_url}")
        print(f"  Subdirectory: {subdirectory}")
        print(f"  AWS Profile: {profile_name}")
        print(f"  Verify Integrity: {verify_integrity}")
        print(f"  Skip Verification: {skip_verification}")
        print(f"  Dry Run: {dry_run}")
        print()
        
        # Initialize S3 client with specified profile
        try:
            session = boto3.Session(profile_name=profile_name)
            s3_client = session.client('s3')
            print(f"✓ AWS session initialized with {profile_name} profile")
        except Exception as e:
            raise DeploymentError(f"Error initializing AWS session: {str(e)}")
        
        # Define files to upload
        files_to_upload = [
            ('src/web/index.html', f'{subdirectory}/index.html'),
            ('src/web/styles.css', f'{subdirectory}/styles.css'),
            ('src/web/script.js', f'{subdirectory}/script.js'),
            ('src/web/error.html', f'{subdirectory}/error.html'),
            ('src/web/favicon.svg', f'{subdirectory}/favicon.svg'),
        ]
        
        # Verify all local files exist
        missing_files = []
        for local_file, _ in files_to_upload:
            if not os.path.exists(local_file):
                missing_files.append(local_file)
        
        if missing_files:
            raise DeploymentError(f"Missing local files: {', '.join(missing_files)}")
        
        if dry_run:
            print(f"\n=== DRY RUN - No files will be uploaded ===")
            print(f"Would upload {len(files_to_upload)} files:")
            for local_file, s3_key in files_to_upload:
                file_size = os.path.getsize(local_file)
                content_type = get_content_type(local_file)
                print(f"  {local_file} -> s3://{bucket_name}/{s3_key}")
                print(f"    Size: {file_size:,} bytes, Type: {content_type}")
            return True
        
        # Initialize backup system
        backup = DeploymentBackup(s3_client, bucket_name, subdirectory)
        
        # Create backup of existing files
        local_files = [local_file for local_file, _ in files_to_upload]
        if not backup.backup_existing_files(local_files):
            raise DeploymentError("Failed to create backup of existing files")
        
        print(f"\n=== Uploading {len(files_to_upload)} files ===")
        
        # Upload each file with error tracking
        upload_errors = []
        uploaded_files = []
        
        for local_file, s3_key in files_to_upload:
            try:
                success = upload_file_to_s3(s3_client, bucket_name, local_file, s3_key, verify_integrity)
                if success:
                    uploaded_files.append((local_file, s3_key))
                else:
                    upload_errors.append(f"Failed to upload {local_file}")
            except Exception as e:
                upload_errors.append(f"Error uploading {local_file}: {str(e)}")
        
        # Check for upload errors
        if upload_errors:
            print(f"\n✗ Upload errors occurred:")
            for error in upload_errors:
                print(f"  {error}")
            
            # Attempt rollback
            print(f"\nAttempting rollback...")
            if backup.rollback():
                print(f"✓ Rollback completed successfully")
            else:
                print(f"✗ Rollback failed - manual intervention may be required")
            
            raise DeploymentError("Deployment failed due to upload errors")
        
        print(f"\n✓ All {len(uploaded_files)} files uploaded successfully")
        
        # Verify accessibility unless skipped
        if not skip_verification:
            print(f"\n=== Verifying deployment accessibility ===")
            verification_success = verify_s3_access_new(
                s3_client, bucket_name, s3_website_url, cloudfront_domain, subdirectory, custom_domain_url
            )
            
            if not verification_success:
                print(f"\n⚠ Verification failed - attempting rollback...")
                if backup.rollback():
                    print(f"✓ Rollback completed successfully")
                    raise DeploymentError("Deployment verification failed - rolled back to previous version")
                else:
                    print(f"✗ Rollback failed - manual intervention required")
                    raise DeploymentError("Deployment verification failed and rollback failed")
        
        # Clean up backup files after successful deployment
        backup.cleanup_backup()
        
        # Success summary
        print(f"\n✅ Deployment completed successfully!")
        print(f"\nDeployment Summary:")
        print(f"  Files deployed: {len(uploaded_files)}")
        print(f"  Target bucket: {bucket_name}")
        print(f"  Subdirectory: {subdirectory}")
        print(f"\nYour website is now available at:")
        print(f"  S3 Website URL: {s3_website_url}/{subdirectory}/")
        print(f"  CloudFront URL: https://{cloudfront_domain}/{subdirectory}/")
        if custom_domain_url != 'Not configured':
            print(f"  Custom Domain URL: {custom_domain_url}")
        
        if not skip_verification:
            print(f"\nNote: CloudFront may take a few minutes to serve updated content due to caching.")
        else:
            print(f"\nNote: Verification was skipped. Please manually verify deployment.")
        
        return True
        
    except DeploymentError as e:
        print(f"\n✗ Deployment Error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected Error: {str(e)}")
        return False

def main():
    """Command line interface for the new deployment script"""
    parser = argparse.ArgumentParser(
        description='Deploy web assets to S3 for the new meetup dashboard stack'
    )
    parser.add_argument(
        '--profile', 
        default='gg-admin',
        help='AWS profile to use (default: gg-admin)'
    )
    parser.add_argument(
        '--subdirectory',
        default='meetup-dashboard-new',
        help='S3 subdirectory to deploy to (default: meetup-dashboard-new)'
    )
    parser.add_argument(
        '--no-integrity-check',
        action='store_true',
        help='Skip file integrity verification after upload'
    )
    parser.add_argument(
        '--skip-verification',
        action='store_true',
        help='Skip accessibility verification (faster deployment)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deployed without actually deploying'
    )
    
    args = parser.parse_args()
    
    success = deploy_assets_new(
        profile_name=args.profile,
        subdirectory=args.subdirectory,
        verify_integrity=not args.no_integrity_check,
        skip_verification=args.skip_verification,
        dry_run=args.dry_run
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()