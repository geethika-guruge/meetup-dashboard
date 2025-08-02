# Project Structure & Organization

## Directory Layout

```
meetup-dashboard/
├── src/                          # Source code
│   ├── web/                      # Frontend web assets
│   │   ├── index.html           # Main HTML file
│   │   ├── styles.css           # Responsive CSS styles
│   │   ├── script.js            # Frontend JavaScript
│   │   ├── error.html           # Error page
│   │   └── favicon.svg          # Site favicon
│   └── lambda/                   # Lambda function code
│       ├── lambda_function.py    # Main Meetup API function
│       └── group_details_function.py # Group details function
├── infrastructure/               # CDK infrastructure code
│   ├── __init__.py              # Python package marker
│   └── meetup_dashboard_stack.py # CDK stack definition
├── scripts/                      # Deployment and utility scripts
│   ├── deploy_assets.py         # Python asset deployment
│   ├── deploy_static.sh         # Shell asset deployment
│   └── update_secret.sh         # Secret management script
├── app.py                       # CDK app entry point
├── requirements.txt             # Python dependencies
├── cdk.json                     # CDK configuration
└── cdk-outputs.json            # CDK deployment outputs
```

## Naming Conventions

### Files
- **Python files**: Use `snake_case` (e.g., `lambda_function.py`, `meetup_dashboard_stack.py`)
- **Web assets**: Use `kebab-case` for HTML/CSS, `camelCase` for JavaScript functions
- **CDK classes**: Use `PascalCase` (e.g., `MeetupDashboardStack`)

### Directories
- Use lowercase with descriptive names
- Group related functionality together
- Separate concerns clearly (web, lambda, infrastructure)

## Code Organization Principles

### Separation of Concerns
- **`src/web/`**: All frontend assets (HTML, CSS, JS)
- **`src/lambda/`**: All Lambda function code
- **`infrastructure/`**: CDK infrastructure definitions only
- **`scripts/`**: Deployment and utility scripts

### Lambda Functions
- Each Lambda function has its own Python file
- Handler function named `lambda_handler`
- Environment variables accessed via `os.environ`
- Logging configured at module level
- Error handling with proper HTTP status codes

### Frontend Structure
- Single-page application with vanilla JavaScript
- No external frameworks or libraries
- Responsive CSS with mobile-first approach
- API calls use modern fetch API with async/await

### Infrastructure as Code
- Single CDK stack in `meetup_dashboard_stack.py`
- All resources defined in one place
- Outputs for important resource identifiers
- Proper IAM permissions with least privilege
- Resource tagging for management

## File Responsibilities

### Core Files
- **`app.py`**: CDK application entry point, instantiates stack
- **`infrastructure/meetup_dashboard_stack.py`**: Defines all AWS resources
- **`src/lambda/lambda_function.py`**: Main API for Meetup analytics
- **`src/lambda/group_details_function.py`**: Detailed group information API

### Web Assets
- **`src/web/index.html`**: Main dashboard page
- **`src/web/styles.css`**: All CSS styles with responsive design
- **`src/web/script.js`**: JavaScript for API integration and UI interactions
- **`src/web/error.html`**: CloudFront error page

### Deployment Scripts
- **`scripts/deploy_assets.py`**: Production-ready asset deployment with verification
- **`scripts/deploy_static.sh`**: Quick development asset deployment
- **`scripts/update_secret.sh`**: Interactive credential management

## Architecture Patterns

### Serverless Design
- Event-driven Lambda functions
- API Gateway for HTTP endpoints
- S3 for static hosting
- CloudFront for global distribution

### Security Patterns
- Secrets Manager for credential storage
- IAM roles with minimal permissions
- CORS configuration for API access
- HTTPS enforcement via CloudFront

### Deployment Patterns
- Infrastructure as Code with CDK
- Separate deployment of infrastructure and assets
- Environment-specific configurations
- Automated resource cleanup