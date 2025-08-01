#!/usr/bin/env python3
import aws_cdk as cdk
from infrastructure.meetup_dashboard_stack import MeetupDashboardStack

app = cdk.App()
MeetupDashboardStack(app, "MeetupDashboardStack")

app.synth()