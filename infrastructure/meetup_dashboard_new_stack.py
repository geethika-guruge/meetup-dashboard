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
    aws_dynamodb as dynamodb,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    RemovalPolicy,
    Tags,
)
import json
from constructs import Construct


class MeetupDashboardNewStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Add DoNotNuke tag to all resources in this stack
        Tags.of(self).add("DoNotNuke", "True")

        # Create DynamoDB table with single-table design
        self.dynamodb_table = dynamodb.Table(
            self, "AwsUserGroupsTableNew",
            table_name="aws-user-groups-new",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", 
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # On-demand pricing
            encryption=dynamodb.TableEncryption.AWS_MANAGED,  # Encryption at rest
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),  # Enable point-in-time recovery
            removal_policy=RemovalPolicy.DESTROY,  # For development environment cleanup
            deletion_protection=False  # Allow deletion for development
        )

        # Create SNS topic for DynamoDB alarms (optional - for production monitoring)
        alarm_topic = sns.Topic(
            self, "DynamoDBAlarmTopicNew",
            topic_name="meetup-dashboard-new-dynamodb-alarms",
            display_name="Meetup Dashboard New DynamoDB Alarms"
        )

        # CloudWatch alarms for DynamoDB monitoring
        # Alarm for throttled requests
        throttled_requests_alarm = cloudwatch.Alarm(
            self, "DynamoDBThrottledRequestsAlarmNew",
            alarm_name="MeetupDashboardNew-DynamoDB-ThrottledRequests",
            alarm_description="Alarm when DynamoDB requests are throttled",
            metric=cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="ThrottledRequests",
                dimensions_map={
                    "TableName": self.dynamodb_table.table_name
                },
                statistic="Sum"
            ),
            threshold=1,
            evaluation_periods=2,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Add SNS action to throttled requests alarm
        throttled_requests_alarm.add_alarm_action(
            cw_actions.SnsAction(alarm_topic)
        )

        # Create S3 bucket for static website hosting with OAC (secure access via CloudFront)
        self.website_bucket = s3.Bucket(
            self, "WebsiteBucketNew",
            # Enable static website hosting
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=False,  # Use OAC instead of public access for security
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,  # Block all public access - CloudFront uses OAC
            removal_policy=RemovalPolicy.DESTROY,  # For development environment cleanup
            auto_delete_objects=True  # Clean up objects when stack is deleted for development
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

        # For the new stack, we'll use CloudFront domain only to avoid conflicts
        # Domain configuration will be handled separately if needed
        subdomain_path = "meetup-dashboard-new"

        # Create Origin Access Control explicitly using L1 construct
        oac = cloudfront.CfnOriginAccessControl(
            self, "OriginAccessControlNew",
            origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name="MeetupDashboardNew-OAC",
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4",
                description="Origin Access Control for Meetup Dashboard New S3 bucket"
            )
        )

        # Create S3 origin with Origin Access Control (OAC) for better security
        s3_origin = origins.S3BucketOrigin(
            self.website_bucket
        )

        # Create CloudFront distribution with S3 origin and optimized caching strategies
        distribution_props = {
            "default_behavior": cloudfront.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                # Use a cache policy that returns 404 for root path access
                cache_policy=cloudfront.CachePolicy(
                    self, "RootBlockCachePolicyNew",
                    cache_policy_name="RootBlockCachePolicyNew",
                    default_ttl=Duration.minutes(5),
                    max_ttl=Duration.hours(1),
                    min_ttl=Duration.seconds(0),
                    query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                    header_behavior=cloudfront.CacheHeaderBehavior.none(),
                    cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                ),
                # Add security headers for better security posture
                response_headers_policy=cloudfront.ResponseHeadersPolicy(
                    self, "SecurityHeadersPolicyNew",
                    response_headers_policy_name="MeetupDashboardNewSecurityHeaders",
                    security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                        content_type_options=cloudfront.ResponseHeadersContentTypeOptions(override=True),
                        frame_options=cloudfront.ResponseHeadersFrameOptions(frame_option=cloudfront.HeadersFrameOption.DENY, override=True),
                        referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN, override=True),
                        strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                            access_control_max_age=Duration.seconds(31536000),
                            include_subdomains=True,
                            override=True
                        )
                    )
                ),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                compress=True,  # Enable compression for better performance
            ),
            "additional_behaviors": {
                # Exact path behavior for /meetup-dashboard-new (redirect to /meetup-dashboard-new/)
                "/meetup-dashboard-new": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                    compress=True,
                ),
                # Exact path behavior for /meetup-dashboard-new/ (serves index.html)
                "/meetup-dashboard-new/": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                    compress=True,
                ),
                # Main behavior for /meetup-dashboard-new/* paths
                "/meetup-dashboard-new/*": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                    compress=True,
                ),
                # Cache behavior for HTML files in meetup-dashboard-new - shorter TTL for content updates
                "/meetup-dashboard-new/*.html": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy(
                        self, "HtmlCachePolicyNew",
                        cache_policy_name="HtmlCachePolicyNew",
                        default_ttl=Duration.minutes(5),
                        max_ttl=Duration.hours(1),
                        min_ttl=Duration.seconds(0),
                        query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                        header_behavior=cloudfront.CacheHeaderBehavior.none(),
                        cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                    compress=True,  # Enable compression for HTML files
                ),
                # Cache behavior for CSS/JS files in meetup-dashboard-new - longer TTL for performance
                "/meetup-dashboard-new/*.css": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy(
                        self, "StaticAssetsCachePolicyNew",
                        cache_policy_name="StaticAssetsCachePolicyNew",
                        default_ttl=Duration.days(1),
                        max_ttl=Duration.days(7),
                        min_ttl=Duration.seconds(0),
                        query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                        header_behavior=cloudfront.CacheHeaderBehavior.none(),
                        cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                    compress=True,  # Enable compression for CSS files
                ),
                "/meetup-dashboard-new/*.js": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy(
                        self, "JsCachePolicyNew",
                        cache_policy_name="JsCachePolicyNew",
                        default_ttl=Duration.days(1),
                        max_ttl=Duration.days(7),
                        min_ttl=Duration.seconds(0),
                        query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                        header_behavior=cloudfront.CacheHeaderBehavior.none(),
                        cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                    compress=True,  # Enable compression for JS files
                ),
                # Cache behavior for image files in meetup-dashboard-new - long TTL for static assets
                "/meetup-dashboard-new/*.svg": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy(
                        self, "ImageCachePolicyNew",
                        cache_policy_name="ImageCachePolicyNew",
                        default_ttl=Duration.days(7),
                        max_ttl=Duration.days(30),
                        min_ttl=Duration.seconds(0),
                        query_string_behavior=cloudfront.CacheQueryStringBehavior.none(),
                        header_behavior=cloudfront.CacheHeaderBehavior.none(),
                        cookie_behavior=cloudfront.CacheCookieBehavior.none(),
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                ),
                "/meetup-dashboard-new/*.png": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                ),
                "/meetup-dashboard-new/*.jpg": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                ),
                "/meetup-dashboard-new/*.jpeg": cloudfront.BehaviorOptions(
                    origin=s3_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                ),
            },
            "default_root_object": "index.html",  # Serves 404 page for root access
            "comment": "Meetup Dashboard New CloudFront Distribution with OAC",
            "error_responses": [
                # Handle 403 errors by serving the index.html file for the dashboard
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/meetup-dashboard-new/index.html",
                    ttl=Duration.minutes(5)
                ),
                # Handle 404 errors by serving the index.html file for the dashboard
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/meetup-dashboard-new/index.html",
                    ttl=Duration.minutes(5)
                )
            ]
        }
        
        # No custom domain for new stack to avoid conflicts
        
        self.distribution = cloudfront.Distribution(
            self, "WebsiteDistributionNew",
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

        # Output the CloudFront URL with /meetup-dashboard-new path
        CfnOutput(
            self, "CustomDomainUrlNew",
            value=f"https://{self.distribution.distribution_domain_name}/meetup-dashboard-new",
            description="CloudFront URL for Meetup Dashboard New",
            export_name="MeetupDashboardNewStack-CustomDomainUrl"
        )

        # Output the CloudFront domain name for testing
        CfnOutput(
            self, "CloudFrontDomainNameNew",
            value=self.distribution.distribution_domain_name,
            description="CloudFront Distribution Domain Name",
            export_name="MeetupDashboardNewStack-CloudFrontDomainName"
        )

        # Output the S3 bucket name for reference
        CfnOutput(
            self, "S3BucketNameNew",
            value=self.website_bucket.bucket_name,
            description="S3 Bucket Name for Static Website",
            export_name="MeetupDashboardNewStack-S3BucketName"
        )

        # Output the S3 website URL for reference (note: direct access blocked by OAC)
        CfnOutput(
            self, "S3WebsiteURLNew",
            value=self.website_bucket.bucket_website_url,
            description="S3 Static Website URL (access via CloudFront only)",
            export_name="MeetupDashboardNewStack-S3WebsiteURL"
        )

        # Create secret for Meetup credentials with placeholder values
        meetup_secret = secretsmanager.Secret(
            self, "MeetupCredentialsNew",
            secret_name="meetup-dashboard-new/credentials",
            description="Meetup API credentials for dashboard new application"
        )

        # Create Lambda function for Meetup API
        self.meetup_lambda = _lambda.Function(
            self, "MeetupApiFunctionNew",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda"),
            timeout=Duration.seconds(30),
            environment={
                "MEETUP_SECRET_NAME": meetup_secret.secret_name,
                "DYNAMODB_TABLE_NAME": self.dynamodb_table.table_name
            }
        )
        
        # Grant Lambda permission to read the secret
        meetup_secret.grant_read(self.meetup_lambda)
        
        # Grant Lambda permission to read and write to DynamoDB table
        self.dynamodb_table.grant_read_write_data(self.meetup_lambda)

        # Create API Gateway REST API with proper CORS configuration
        self.api = apigateway.RestApi(
            self, "MeetupApiNew",
            rest_api_name="Meetup Dashboard New API",
            description="REST API for AWS User Group Dashboard New with analytics and group details endpoints",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,  # Allow all origins for development
                allow_methods=["GET", "POST", "OPTIONS"],  # Specific HTTP methods for API endpoints
                allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],  # Proper headers for API endpoints
                max_age=Duration.hours(1)  # Cache preflight requests for 1 hour
            ),
            # Enable request validation and throttling (without logging to avoid CloudWatch role issues)
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,  # Requests per second
                throttling_burst_limit=200,  # Burst capacity
                metrics_enabled=True
            )
        )

        # Create Lambda integration for /meetup endpoint with proper proxy integration
        lambda_integration = apigateway.LambdaIntegration(
            self.meetup_lambda,
            proxy=True,  # Enable Lambda proxy integration for proper request/response mapping
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                        "method.response.header.Access-Control-Allow-Methods": "'GET,POST,OPTIONS'"
                    }
                )
            ]
        )

        # Add /meetup POST endpoint for analytics and data loading
        meetup_resource = self.api.root.add_resource("meetup")
        meetup_method = meetup_resource.add_method(
            "POST", 
            lambda_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True
                    }
                )
            ]
        )

        # Create Lambda function for group details
        self.group_details_lambda = _lambda.Function(
            self, "GroupDetailsFunctionNew",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="group_details_function.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda"),
            timeout=Duration.seconds(30),
            environment={
                "MEETUP_SECRET_NAME": meetup_secret.secret_name,
                "DYNAMODB_TABLE_NAME": self.dynamodb_table.table_name
            }
        )
        
        # Grant Lambda permission to read the secret
        meetup_secret.grant_read(self.group_details_lambda)
        
        # Grant Lambda permission to read from DynamoDB table
        self.dynamodb_table.grant_read_data(self.group_details_lambda)

        # Create Lambda integration for /group-details endpoint
        group_details_integration = apigateway.LambdaIntegration(
            self.group_details_lambda,
            proxy=True,  # Enable Lambda proxy integration for proper request/response mapping
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                        "method.response.header.Access-Control-Allow-Methods": "'GET,POST,OPTIONS'"
                    }
                )
            ]
        )

        # Add /group-details POST endpoint for individual group information from database
        group_details_resource = self.api.root.add_resource("group-details")
        group_details_method = group_details_resource.add_method(
            "POST", 
            group_details_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True
                    }
                )
            ]
        )

        # Output API Gateway URL
        CfnOutput(
            self, "ApiGatewayUrlNew",
            value=self.api.url,
            description="API Gateway URL for Meetup integration",
            export_name="MeetupDashboardNewStack-ApiGatewayUrl"
        )

        # Output DynamoDB table name
        CfnOutput(
            self, "DynamoDBTableNameNew",
            value=self.dynamodb_table.table_name,
            description="DynamoDB table name for AWS User Groups data",
            export_name="MeetupDashboardNewStack-DynamoDBTableName"
        )

        # Output SNS topic ARN for alarm notifications
        CfnOutput(
            self, "DynamoDBAlarmTopicArnNew",
            value=alarm_topic.topic_arn,
            description="SNS Topic ARN for DynamoDB alarm notifications",
            export_name="MeetupDashboardNewStack-DynamoDBAlarmTopicArn"
        )

        # Output Secrets Manager secret ARN for reference
        CfnOutput(
            self, "MeetupSecretArnNew",
            value=meetup_secret.secret_arn,
            description="Secrets Manager secret ARN for Meetup credentials",
            export_name="MeetupDashboardNewStack-MeetupSecretArn"
        )