#!/usr/bin/env python3
"""
Deploy Lambda function for Meetup API integration.
"""

import boto3
import json
import zipfile
import os
from pathlib import Path

def create_lambda_package():
    """Create deployment package for Lambda function."""
    # Create a temporary directory for the package
    package_dir = Path("lambda_package")
    package_dir.mkdir(exist_ok=True)
    
    # Copy lambda function
    with open("lambda_function.py", "r") as src:
        with open(package_dir / "lambda_function.py", "w") as dst:
            dst.write(src.read())
    
    # Install dependencies
    os.system(f"pip install -r lambda_requirements.txt -t {package_dir}")
    
    # Create zip file
    with zipfile.ZipFile("lambda_function.zip", "w") as zip_file:
        for file_path in package_dir.rglob("*"):
            if file_path.is_file():
                zip_file.write(file_path, file_path.relative_to(package_dir))
    
    # Clean up
    import shutil
    shutil.rmtree(package_dir)
    
    return "lambda_function.zip"

def deploy_lambda():
    """Deploy Lambda function to AWS."""
    lambda_client = boto3.client('lambda')
    
    # Create deployment package
    zip_file = create_lambda_package()
    
    function_name = "meetup-dashboard-api"
    
    try:
        # Try to update existing function
        with open(zip_file, "rb") as f:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        print(f"✓ Updated existing Lambda function: {function_name}")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        with open(zip_file, "rb") as f:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime="python3.9",
                Role="arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role",
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": f.read()},
                Environment={
                    "Variables": {
                        "MEETUP_CLIENT_ID": "your_client_id",
                        "MEETUP_CLIENT_SECRET": "your_client_secret", 
                        "MEETUP_ACCESS_TOKEN": "your_access_token",
                        "MEETUP_PRO_URLNAME": "your_pro_urlname"
                    }
                },
                Timeout=30
            )
        print(f"✓ Created new Lambda function: {function_name}")
        print(f"Function ARN: {response['FunctionArn']}")
    
    # Clean up zip file
    os.remove(zip_file)

if __name__ == "__main__":
    deploy_lambda()