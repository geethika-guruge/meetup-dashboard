#!/usr/bin/env python3
import aws_cdk as cdk
from infrastructure.meetup_dashboard_stack import MeetupDashboardStack
from infrastructure.certificate_stack import CertificateStack

app = cdk.App()

# Environment configuration for main stack (ap-southeast-2)
main_env = cdk.Environment(
    account="610251782643",  # Your AWS account ID
    region="ap-southeast-2"   # Your AWS region
)

# Environment configuration for certificate stack (us-east-1 - required for CloudFront)
cert_env = cdk.Environment(
    account="610251782643",  # Your AWS account ID
    region="us-east-1"       # Required for CloudFront certificates
)

# Deploy certificate stack first (in us-east-1)
certificate_stack = CertificateStack(app, "CertificateStack", env=cert_env)

# Deploy main stack (in ap-southeast-2)
main_stack = MeetupDashboardStack(app, "MeetupDashboardStack", env=main_env)

# Main stack depends on certificate stack
main_stack.add_dependency(certificate_stack)

app.synth()