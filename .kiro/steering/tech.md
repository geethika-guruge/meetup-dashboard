# Technology Stack & Build System

## Core Technologies

### Frontend
- **HTML5, CSS3, JavaScript (ES6+)**: Vanilla web technologies, no frameworks
- **Responsive Design**: Mobile-first CSS with media queries
- **Modern JavaScript**: Async/await, fetch API, DOM manipulation

### Backend
- **AWS Lambda**: Python 3.9 runtime for serverless functions
- **API Gateway**: REST API with CORS support
- **Secrets Manager**: Secure credential storage for Meetup API

### Infrastructure
- **AWS CDK**: Python-based Infrastructure as Code
- **CloudFront**: Global CDN with custom cache policies
- **S3**: Static website hosting with public read access
- **IAM**: Least-privilege access policies

### External APIs
- **Meetup.com GraphQL API**: Real-time user group data

## Dependencies

### Python (requirements.txt)
- `aws-cdk-lib>=2.100.0`: AWS CDK framework
- `constructs>=10.0.0`: CDK constructs library
- `boto3>=1.26.0`: AWS SDK for Python
- `requests>=2.31.0`: HTTP library for API calls
- `pytest>=7.0.0`: Testing framework
- `responses>=0.23.0`: HTTP request mocking for tests

## Common Commands

### Development Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Infrastructure Deployment
```bash
# Deploy CDK stack
cdk deploy --profile your-aws-profile

# Synthesize CloudFormation template (dry run)
cdk synth

# Destroy stack
cdk destroy --profile your-aws-profile
```

### Asset Deployment
```bash
# Recommended: Python script with verification
python scripts/deploy_assets.py

# Alternative: Shell script for quick deployments
./scripts/deploy_static.sh your-aws-profile
```

### Secrets Management
```bash
# Update Meetup API credentials
./scripts/update_secret.sh your-aws-profile
```

### Testing
```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src
```

## Build Conventions
- Use Python virtual environments for dependency isolation
- CDK outputs are stored in `cdk-outputs.json` for reference
- All AWS resources are tagged with `DoNotNuke: True`
- Lambda functions have 30-second timeout
- API Gateway has CORS enabled for all origins