# Custom Domain Setup Guide

This guide will help you set up your meetup dashboard to be served at `https://projects.geethika.dev/meetup-dashboard`.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Domain `geethika.dev` registered with a domain registrar
- Python 3.8+ with pip
- AWS CDK CLI installed

## Step 1: Set Up Route 53 Hosted Zone

First, you need to create a hosted zone for your domain in Route 53:

```bash
# Run the Route 53 setup script
python scripts/setup_route53.py
```

This script will:
- Check if a hosted zone exists for `geethika.dev`
- Create one if it doesn't exist
- Display the name servers you need to configure with your domain registrar
- Save the configuration to `route53-config.json`

## Step 2: Update Domain Registrar

Take the name servers from Step 1 and update your domain registrar's DNS settings:

1. Log into your domain registrar's control panel
2. Find the DNS or Name Server settings for `geethika.dev`
3. Replace the existing name servers with the ones provided by Route 53
4. Save the changes

**Note:** DNS propagation can take up to 48 hours, but usually completes within a few hours.

## Step 3: Verify DNS Propagation

Check if DNS has propagated:

```bash
# Check name servers
dig NS geethika.dev

# Check if the domain resolves
dig geethika.dev
```

## Step 4: Deploy the Updated CDK Stack

Deploy your infrastructure with the custom domain configuration:

```bash
# Deploy the CDK stack
cdk deploy --profile your-aws-profile

# This will create:
# - SSL certificate for projects.geethika.dev
# - CloudFront distribution with custom domain
# - Route 53 A record pointing to CloudFront
```

**Note:** The SSL certificate validation may take several minutes as it requires DNS validation.

## Step 5: Upload Static Assets

Upload your web assets to the S3 bucket with the subdirectory structure:

```bash
# Option 1: Python script (recommended for production)
python scripts/deploy_assets.py

# Option 2: Shell script (quick deployment)
./scripts/deploy_static.sh your-aws-profile
```

## Step 6: Verify Deployment

After deployment, your site should be accessible at:

- **Custom Domain**: `https://projects.geethika.dev/meetup-dashboard`
- **CloudFront**: `https://[cloudfront-domain]/meetup-dashboard/`
- **S3 Website**: `http://[bucket-website-url]/meetup-dashboard/`

## Architecture Changes

The updated architecture includes:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Route 53      │────│   CloudFront     │────│   S3 Bucket     │
│   (DNS)         │    │   Distribution   │    │   (Website)     │
│                 │    │   + SSL Cert     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
projects.geethika.dev    Custom Domain           /meetup-dashboard/
                         + HTTPS                  ├── index.html
                                                 ├── styles.css
                                                 ├── script.js
                                                 ├── error.html
                                                 └── favicon.svg
```

## Key Changes Made

### 1. CDK Stack Updates (`infrastructure/meetup_dashboard_stack.py`)
- Added ACM certificate for `projects.geethika.dev`
- Configured CloudFront distribution with custom domain
- Added Route 53 A record pointing to CloudFront
- DNS validation for SSL certificate

### 2. Deployment Scripts Updates
- **`scripts/deploy_assets.py`**: Updated to upload files to `meetup-dashboard/` subdirectory
- **`scripts/deploy_static.sh`**: Updated for subdirectory structure
- **`scripts/setup_route53.py`**: New script to manage Route 53 hosted zone

### 3. File Structure in S3
Files are now uploaded to the `meetup-dashboard/` prefix:
- `meetup-dashboard/index.html`
- `meetup-dashboard/styles.css`
- `meetup-dashboard/script.js`
- `meetup-dashboard/error.html`
- `meetup-dashboard/favicon.svg`

## Troubleshooting

### SSL Certificate Issues
- Ensure DNS has propagated before deploying
- Certificate validation requires the Route 53 hosted zone to be active
- Check CloudFormation events for certificate validation status

### DNS Issues
- Use `dig NS geethika.dev` to verify name servers
- Use `dig projects.geethika.dev` to verify the A record
- DNS propagation can take up to 48 hours

### CloudFront Caching
- CloudFront may cache old content for up to 24 hours
- Use CloudFront invalidation if you need immediate updates
- The deployment script sets appropriate cache headers

### Access Issues
- Verify S3 bucket policy allows CloudFront access
- Check CloudFront origin access control settings
- Ensure files are uploaded to the correct subdirectory

## Cost Considerations

Additional costs for custom domain setup:
- **Route 53 Hosted Zone**: $0.50/month
- **ACM Certificate**: Free for CloudFront distributions
- **Route 53 DNS Queries**: $0.40 per million queries

## Security Features

- **HTTPS Enforced**: All traffic redirected to HTTPS
- **SSL Certificate**: Automatically managed by ACM
- **Origin Access Control**: S3 bucket only accessible via CloudFront
- **Secrets Management**: API credentials stored securely in Secrets Manager

## Next Steps

1. Monitor the deployment in CloudFormation console
2. Test the custom domain once DNS propagates
3. Set up monitoring and alerts for your domain
4. Consider setting up additional subdomains for other projects

---

**Your meetup dashboard will be available at: `https://projects.geethika.dev/meetup-dashboard`**
