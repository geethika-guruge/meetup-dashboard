#!/usr/bin/env python3
import aws_cdk as cdk
from infrastructure.meetup_dashboard_stack import MeetupDashboardStack

app = cdk.App()

# Environment configuration for hosted zone lookup
env = cdk.Environment(
    account="610251782643",  # Your AWS account ID
    region="ap-southeast-2"   # Your AWS region
)

MeetupDashboardStack(app, "MeetupDashboardStack", env=env)

app.synth()