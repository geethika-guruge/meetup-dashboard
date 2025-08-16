from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    Fn,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_secretsmanager as secretsmanager,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_sqs as aws_sqs,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    Tags,
)
import json
from constructs import Construct


class MeetupDashboardStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Add DoNotNuke tag to all resources in this stack
        Tags.of(self).add("DoNotNuke", "True")

        # Create S3 bucket for static hosting with OAC (no public access)
        self.website_bucket = s3.Bucket(
            self, "WebsiteBucket",
            # Remove website hosting configuration for OAC
            public_read_access=False,  # Use OAC instead of public access
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,  # Block all public access
            removal_policy=RemovalPolicy.DESTROY,  # For development/testing
            auto_delete_objects=True  # Clean up objects when stack is deleted
        )
        
        # Add bucket policy to allow uploads from current account
        self.website_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AccountRootPrincipal()],
                actions=["s3:PutObject", "s3:PutObjectAcl", "s3:GetObject", "s3:DeleteObject"],
                resources=[f"{self.website_bucket.bucket_arn}/*"]
            )
        )
        
        self.website_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AccountRootPrincipal()],
                actions=["s3:ListBucket"],
                resources=[self.website_bucket.bucket_arn]
            )
        )

        # Domain configuration
        domain_name = "projects.geethika.dev"
        subdomain_path = "meetup-dashboard"
        
        # Look up the existing hosted zone for geethika.dev
        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name="geethika.dev"
        )
        
        # Import certificate from the certificate stack (us-east-1)
        # Note: Cross-region imports are not supported, so we use the hardcoded ARN
        certificate_arn = "arn:aws:acm:us-east-1:610251782643:certificate/a227ab55-2bc9-4a2a-a508-a3224e52488a"
        certificate = acm.Certificate.from_certificate_arn(
            self, "ImportedCertificate",
            certificate_arn=certificate_arn
        )

        # Create Origin Access Control explicitly using L1 construct
        oac = cloudfront.CfnOriginAccessControl(
            self, "OriginAccessControl",
            origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name="MeetupDashboard-OAC",
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4",
                description="Origin Access Control for Meetup Dashboard S3 bucket"
            )
        )

        # Create S3 origin with Origin Access Control (OAC) for better security
        # No origin_path - files are accessed directly from S3 bucket structure
        s3_origin = origins.S3BucketOrigin(
            self.website_bucket
        )

        # Create CloudFront distribution with S3 origin (custom domain will be added later)
        distribution_props = {
            "default_behavior": cloudfront.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                # Use a cache policy that returns 404 for root path access
                cache_policy=cloudfront.CachePolicy(
                    self, "RootBlockCachePolicy",
                    cache_policy_name="RootBlockCachePolicy",
                    default_ttl=Duration.minutes(5),
                    max_ttl=Duration.hours(1),
                    min_ttl=Duration.seconds(0),
                    query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                    header_behavior=cloudfront.CacheHeaderBehavior.none(),
                    cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                ),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
            ),
            "additional_behaviors": {
                # Exact path behavior for /meetup-dashboard (maps to /meetup-dashboard/index.html in S3)
                "/meetup-dashboard": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                ),
                # Main behavior for /meetup-dashboard/* paths
                "/meetup-dashboard/*": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                ),
                # Cache behavior for HTML files in meetup-dashboard - shorter TTL for content updates
                "/meetup-dashboard/*.html": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy(
                        self, "HtmlCachePolicy",
                        cache_policy_name="HtmlCachePolicy",
                        default_ttl=Duration.minutes(5),
                        max_ttl=Duration.hours(1),
                        min_ttl=Duration.seconds(0),
                        query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                        header_behavior=cloudfront.CacheHeaderBehavior.none(),
                        cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                ),
                # Cache behavior for CSS/JS files in meetup-dashboard - longer TTL for performance
                "/meetup-dashboard/*.css": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy(
                        self, "StaticAssetsCachePolicy",
                        cache_policy_name="StaticAssetsCachePolicy",
                        default_ttl=Duration.days(1),
                        max_ttl=Duration.days(7),
                        min_ttl=Duration.seconds(0),
                        query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                        header_behavior=cloudfront.CacheHeaderBehavior.none(),
                        cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                ),
                "/meetup-dashboard/*.js": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy(
                        self, "JsCachePolicy",
                        cache_policy_name="JsCachePolicy",
                        default_ttl=Duration.days(1),
                        max_ttl=Duration.days(7),
                        min_ttl=Duration.seconds(0),
                        query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                        header_behavior=cloudfront.CacheHeaderBehavior.none(),
                        cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                ),
            },
            "default_root_object": "index.html",  # Serves 404 page for root access
            "comment": "Meetup Dashboard CloudFront Distribution with OAC",
            "error_responses": [
                # Handle 403 errors by serving the index.html file for the dashboard
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/meetup-dashboard/index.html",
                    ttl=Duration.minutes(5)
                ),
                # Handle 404 errors by serving the index.html file for the dashboard
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/meetup-dashboard/index.html",
                    ttl=Duration.minutes(5)
                )
            ]
        }
        
        # Add custom domain if certificate is available
        if certificate:
            distribution_props["domain_names"] = [domain_name]
            distribution_props["certificate"] = certificate
        
        self.distribution = cloudfront.Distribution(
            self, "WebsiteDistribution",
            **distribution_props
        )

        # Use escape hatch to add OAC to the CloudFront distribution
        cfn_distribution = self.distribution.node.default_child
        cfn_distribution.add_property_override(
            "DistributionConfig.Origins.0.OriginAccessControlId",
            oac.attr_id
        )
        
        # Add dependency to ensure OAC is created before distribution
        self.distribution.node.add_dependency(oac)

        # Add bucket policy for CloudFront OAC access
        self.website_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[f"{self.website_bucket.bucket_arn}/*"],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{self.account}:distribution/{self.distribution.distribution_id}"
                    }
                }
            )
        )

        # Create Route 53 A record pointing to CloudFront distribution
        route53.ARecord(
            self, "AliasRecord",
            zone=hosted_zone,
            record_name="projects",
            target=route53.RecordTarget.from_alias(targets.CloudFrontTarget(self.distribution))
        )

        # Grant CloudFront access to S3 bucket using Origin Access Control
        # This is automatically handled by S3BucketOrigin with OAC

        # Output the custom domain URL with /meetup-dashboard path
        CfnOutput(
            self, "CustomDomainUrl",
            value=f"https://{domain_name}/meetup-dashboard",
            description="Custom Domain URL for Meetup Dashboard",
            export_name="MeetupDashboardStack-CustomDomainUrl"
        )

        # Output the CloudFront domain name for testing
        CfnOutput(
            self, "CloudFrontDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront Distribution Domain Name",
            export_name="MeetupDashboardStack-CloudFrontDomainName"
        )

        # Output the S3 bucket name for reference
        CfnOutput(
            self, "S3BucketName",
            value=self.website_bucket.bucket_name,
            description="S3 Bucket Name for Static Website",
            export_name="MeetupDashboardStack-S3BucketName"
        )

        # Output the S3 website URL for reference
        CfnOutput(
            self, "S3WebsiteURL",
            value=self.website_bucket.bucket_website_url,
            description="S3 Static Website URL",
            export_name="MeetupDashboardStack-S3WebsiteURL"
        )

        # Create secret for Meetup credentials with placeholder values
        meetup_secret = secretsmanager.Secret(
            self, "MeetupCredentials",
            secret_name="meetup-dashboard/credentials",
            description="Meetup API credentials for dashboard application",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({
                    "MEETUP_CLIENT_ID": "Meetup-Dashboard",
                    "MEETUP_CLIENT_SECRET": "placeholder",
                    "MEETUP_ACCESS_TOKEN": "placeholder",
                    "MEETUP_PRO_URLNAME": "placeholder"
                }),
                generate_string_key="placeholder"
            )
        )
        # Create SQS queue for group IDs
        self.meetup_group_queue = aws_sqs.Queue(
            self, "MeetupGroupQueue",
            queue_name="meetup-group-ids",
            removal_policy=RemovalPolicy.DESTROY, # For dev/testing
            visibility_timeout=Duration.seconds(300) 
        )

        # Create DynamoDB table for storing Lambda results
        self.meetup_results_table = dynamodb.Table(
            self, "MeetupResultsTable",
            table_name="meetup-dashboard-results",
            partition_key=dynamodb.Attribute(
                name="pk",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk", 
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/testing
            point_in_time_recovery=False  # Disabled for cost optimization
        )

        # Add GSI for querying by data type and timestamp
        self.meetup_results_table.add_global_secondary_index(
            index_name="DataTypeIndex",
            partition_key=dynamodb.Attribute(
                name="data_type",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Create Lambda function for Meetup API
        self.meetup_lambda = _lambda.Function(
            self, "MeetupApiFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda"),
            timeout=Duration.seconds(30),
            environment={
                "MEETUP_SECRET_NAME": meetup_secret.secret_name
            }
        )
        
        # Grant Lambda permission to read the secret
        meetup_secret.grant_read(self.meetup_lambda)

        # Create API Gateway
        self.api = apigateway.RestApi(
            self, "MeetupApi",
            rest_api_name="Meetup Dashboard API",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            )
        )

        # Create Lambda integration
        lambda_integration = apigateway.LambdaIntegration(self.meetup_lambda)

        # Add API Gateway resource and method
        meetup_resource = self.api.root.add_resource("meetup")
        meetup_resource.add_method("POST", lambda_integration)

        # Create Lambda function for group details
        self.group_details_lambda = _lambda.Function(
            self, "GroupDetailsFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="group_details_function.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda"),
            timeout=Duration.seconds(30),
            environment={
                "MEETUP_SECRET_NAME": meetup_secret.secret_name
            }
        )
        
        # Grant Lambda permission to read the secret
        meetup_secret.grant_read(self.group_details_lambda)

        # Add group details resource and method
        group_details_resource = self.api.root.add_resource("group-details")
        group_details_integration = apigateway.LambdaIntegration(self.group_details_lambda)
        group_details_resource.add_method("POST", group_details_integration)

        # Create Lambda function to query pro network
        self.query_pro_network_lambda = _lambda.Function(
            self, "QueryProNetworkFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="query_pro_network.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda"),
            timeout=Duration.seconds(30),
            environment={
                "MEETUP_SECRET_NAME": meetup_secret.secret_name,
                "MEETUP_GROUP_SQS_URL": self.meetup_group_queue.queue_url,
                "DYNAMODB_TABLE_NAME": self.meetup_results_table.table_name
            }
        )
        # Grant Lambda permission to read the secret
        meetup_secret.grant_read(self.query_pro_network_lambda)
        # Grant Lambda permission to send messages to SQS
        self.meetup_group_queue.grant_send_messages(self.query_pro_network_lambda)
        # Grant Lambda permission to write to DynamoDB
        self.meetup_results_table.grant_write_data(self.query_pro_network_lambda)

        # Add pro network resource and method
        query_pro_network_resource = self.api.root.add_resource("pro-network-details")
        query_pro_network_integration = apigateway.LambdaIntegration(self.query_pro_network_lambda)
        query_pro_network_resource.add_method("POST", query_pro_network_integration)

        # Create Lambda function to process group events (triggered by SQS)
        self.process_group_events_lambda = _lambda.Function(
            self, "ProcessGroupEventsFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="process_group_events.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda"),
            timeout=Duration.seconds(300),  # 5 minutes for processing multiple events
            environment={
                "MEETUP_SECRET_NAME": meetup_secret.secret_name,
                "DYNAMODB_TABLE_NAME": self.meetup_results_table.table_name
            }
        )
        
        # Grant Lambda permission to read the secret
        meetup_secret.grant_read(self.process_group_events_lambda)
        
        # Grant Lambda permission to receive messages from SQS
        self.meetup_group_queue.grant_consume_messages(self.process_group_events_lambda)
        
        # Grant Lambda permission to write to DynamoDB
        self.meetup_results_table.grant_write_data(self.process_group_events_lambda)
        
        # Add SQS event source to trigger the Lambda
        from aws_cdk import aws_lambda_event_sources as lambda_event_sources
        self.process_group_events_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(
                self.meetup_group_queue,
                batch_size=10,  # Process up to 10 messages at once
                max_batching_window=Duration.seconds(5)  # Wait up to 5 seconds to batch messages
            )
        )

        # Output API Gateway URL
        CfnOutput(
            self, "ApiGatewayUrl",
            value=self.api.url,
            description="API Gateway URL for Meetup integration",
            export_name="MeetupDashboardStack-ApiGatewayUrl"
        )

        # Output DynamoDB table name
        CfnOutput(
            self, "DynamoDBTableName",
            value=self.meetup_results_table.table_name,
            description="DynamoDB table name for storing Lambda results",
            export_name="MeetupDashboardStack-DynamoDBTableName"
        )
