from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    RemovalPolicy,
)
from constructs import Construct


class SpaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 bucket for static website hosting
        self.website_bucket = s3.Bucket(
            self, "WebsiteBucket",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=True,  # Required for S3StaticWebsiteOrigin
            block_public_access=s3.BlockPublicAccess.BLOCK_ACLS,
            removal_policy=RemovalPolicy.DESTROY,  # For development/testing
            auto_delete_objects=True  # Clean up objects when stack is deleted
        )

        # Create S3 origin using static website hosting
        s3_origin = origins.S3StaticWebsiteOrigin(self.website_bucket)

        # Create CloudFront distribution with S3 origin
        self.distribution = cloudfront.Distribution(
            self, "WebsiteDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
            ),
            additional_behaviors={
                # Cache behavior for HTML files - shorter TTL for content updates
                "*.html": cloudfront.BehaviorOptions(
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
                # Cache behavior for CSS/JS files - longer TTL for performance
                "*.css": cloudfront.BehaviorOptions(
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
                "*.js": cloudfront.BehaviorOptions(
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
            default_root_object="index.html",
            comment="SPA CloudFront Distribution",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                )
            ]
        )

        # Grant CloudFront access to S3 bucket using Origin Access Control
        # This is automatically handled by S3BucketOrigin with OAC

        # Output the CloudFront domain name for testing
        CfnOutput(
            self, "CloudFrontDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront Distribution Domain Name",
            export_name="SpaStack-CloudFrontDomainName"
        )

        # Output the S3 bucket name for reference
        CfnOutput(
            self, "S3BucketName",
            value=self.website_bucket.bucket_name,
            description="S3 Bucket Name for Static Website",
            export_name="SpaStack-S3BucketName"
        )

        # Output the S3 website URL for reference
        CfnOutput(
            self, "S3WebsiteURL",
            value=self.website_bucket.bucket_website_url,
            description="S3 Static Website URL",
            export_name="SpaStack-S3WebsiteURL"
        )