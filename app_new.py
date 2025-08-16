#!/usr/bin/env python3
import aws_cdk as cdk
from infrastructure.meetup_dashboard_new_stack import MeetupDashboardNewStack

app = cdk.App()

# Environment configuration for main stack (ap-southeast-2)
main_env = cdk.Environment(
    account="610251782643",  # Your AWS account ID
    region="ap-southeast-2"   # Your AWS region
)

# Deploy new stack (in ap-southeast-2) - reuse existing certificate
new_stack = MeetupDashboardNewStack(app, "MeetupDashboardNewStack", env=main_env)

app.synth()