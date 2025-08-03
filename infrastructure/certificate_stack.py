from aws_cdk import (
    Stack,
    CfnOutput,
    aws_certificatemanager as acm,
    aws_route53 as route53,
)
from constructs import Construct


class CertificateStack(Stack):
    """
    Stack to create SSL certificate in us-east-1 for CloudFront
    This must be in us-east-1 region for CloudFront to use it
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Domain configuration
        domain_name = "projects.geethika.dev"
        
        # Look up the existing hosted zone for geethika.dev
        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name="geethika.dev"
        )
        
        # Create SSL certificate for the subdomain
        self.certificate = acm.Certificate(
            self, "Certificate",
            domain_name=domain_name,
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )
        
        # Output the certificate ARN for use in other stacks
        CfnOutput(
            self, "CertificateArn",
            value=self.certificate.certificate_arn,
            description="SSL Certificate ARN for CloudFront",
            export_name="CertificateStack-CertificateArn"
        )
