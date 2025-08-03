# Origin Access Control (OAC) Implementation

## Overview

This document describes the implementation of AWS CloudFront Origin Access Control (OAC) for the Meetup Dashboard, replacing the previous S3 static website hosting approach with a more secure solution.

## Security Benefits

### Before OAC Implementation
- S3 bucket was publicly accessible
- Anyone could access files directly via S3 URLs
- Less secure architecture

### After OAC Implementation
- ✅ S3 bucket is private (no public access)
- ✅ Files only accessible through CloudFront
- ✅ Source ARN condition prevents unauthorized access
- ✅ Follows AWS security best practices

## Technical Implementation

### 1. Origin Access Control Resource
```typescript
// Created explicit OAC resource using L1 construct
oac = cloudfront.CfnOriginAccessControl(
    self, "OriginAccessControl",
    origin_access_control_config={
        name: "MeetupDashboard-OAC",
        origin_access_control_origin_type: "s3",
        signing_behavior: "always",
        signing_protocol: "sigv4",
        description: "Origin Access Control for Meetup Dashboard S3 bucket"
    }
)
```

### 2. CloudFront Distribution Configuration
```typescript
// Used escape hatch to configure OAC in CloudFront
cfn_distribution.add_property_override(
    "DistributionConfig.Origins.0.OriginAccessControlId",
    oac.attr_id
)
```

### 3. S3 Bucket Policy
```json
{
    "Effect": "Allow",
    "Principal": {
        "Service": "cloudfront.amazonaws.com"
    },
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::bucket-name/*",
    "Condition": {
        "StringEquals": {
            "AWS:SourceArn": "arn:aws:cloudfront::ACCOUNT:distribution/DISTRIBUTION_ID"
        }
    }
}
```

### 4. S3 Bucket Configuration
- Removed `website_index_document` and `website_error_document`
- Set `public_read_access=False`
- Set `block_public_access=s3.BlockPublicAccess.BLOCK_ALL`

## Verification Results

### ✅ Working URLs
- **Custom Domain**: `https://projects.geethika.dev/` → HTTP 200
- **CloudFront**: `https://d2t9i2ckx0b7v4.cloudfront.net/` → HTTP 200

### ✅ Security Verification
- **Direct S3 Access**: `https://bucket.s3.region.amazonaws.com/file` → HTTP 403 (Forbidden)
- **OAC ID**: `EGPGZOW81AMXU` (properly configured)

### ✅ Content Delivery
- **HTML Files**: Served with `text/html`, 5-minute cache
- **CSS Files**: Served with `text/css`, 1-day cache  
- **JS Files**: Served with `application/javascript`, 1-day cache
- **Images**: Served with proper MIME types, 7-day cache

## Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Route 53      │────│   CloudFront     │────│   S3 Bucket     │
│   (DNS)         │    │   Distribution   │    │   (Private)     │
│                 │    │   + OAC          │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
projects.geethika.dev    OAC ID: EGPGZOW81AMXU    Block Public Access
Custom Domain + HTTPS    Source ARN Condition     403 on Direct Access
```

## Key Configuration Details

### OAC Configuration
- **OAC ID**: `EGPGZOW81AMXU`
- **Signing Behavior**: `always`
- **Signing Protocol**: `sigv4`
- **Origin Type**: `s3`

### CloudFront Distribution
- **Distribution ID**: `E3RTPE1MJD9EQ1`
- **Domain**: `d2t9i2ckx0b7v4.cloudfront.net`
- **Custom Domain**: `projects.geethika.dev`
- **Origin Path**: `/meetup-dashboard`

### S3 Bucket
- **Name**: `meetupdashboardstack-websitebucket75c24d94-e2hwexf0odzm`
- **Region**: `ap-southeast-2`
- **Public Access**: Blocked
- **Website Hosting**: Disabled (using OAC instead)

## Troubleshooting

### Common Issues and Solutions

1. **403 Errors After OAC Implementation**
   - Verify OAC ID is set in CloudFront distribution
   - Check S3 bucket policy includes CloudFront service principal
   - Ensure source ARN condition matches distribution ARN

2. **Files Not Loading**
   - Check origin path configuration (`/meetup-dashboard`)
   - Verify files exist in correct S3 subdirectory
   - Create CloudFront invalidation if needed

3. **Cache Issues**
   - Use CloudFront invalidation: `aws cloudfront create-invalidation --distribution-id E3RTPE1MJD9EQ1 --paths "/*"`
   - Check cache headers are properly set

## Monitoring and Maintenance

### CloudWatch Metrics to Monitor
- CloudFront 4xx/5xx error rates
- Origin response times
- Cache hit ratios

### Regular Maintenance
- Monitor S3 bucket access logs
- Review CloudFront access logs
- Update cache policies as needed

## Cost Impact

### Cost Savings
- Reduced S3 data transfer costs (traffic goes through CloudFront)
- Better cache efficiency

### Additional Costs
- Minimal increase due to OAC (no additional charges)
- CloudFront costs remain the same

## Compliance and Security

### Security Standards Met
- ✅ AWS Well-Architected Security Pillar
- ✅ Principle of least privilege
- ✅ Defense in depth
- ✅ No public S3 bucket access

### Compliance Benefits
- Improved security posture
- Audit trail through CloudTrail
- Centralized access control

---

**Implementation Date**: August 3, 2025  
**Status**: ✅ Successfully Implemented  
**Security Level**: Enhanced with OAC
