#!/usr/bin/env python3
import aws_cdk as cdk
from spa_stack import SpaStack

# Initialize CDK app
app = cdk.App()

# Create the SPA stack with tags and metadata for resource identification
spa_stack = SpaStack(
    app, 
    "SpaStack",
    description="Single Page Application with S3 and CloudFront",
    env=cdk.Environment(
        # Use default account and region from AWS profile
        # The sandpit-1-admin profile will be specified during deployment
        account=None,  # Will use profile's account
        region=None    # Will use profile's region
    )
)

# Add stack-level tags for resource identification and management
cdk.Tags.of(spa_stack).add("Project", "SPA-CloudFront-S3")
cdk.Tags.of(spa_stack).add("Environment", "Development")
cdk.Tags.of(spa_stack).add("Owner", "Developer")
cdk.Tags.of(spa_stack).add("ManagedBy", "CDK")
cdk.Tags.of(spa_stack).add("Purpose", "Static Website Hosting")

# Synthesize the CloudFormation template
app.synth()