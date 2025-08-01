# Project Structure

This project follows AWS CDK best practices for organizing serverless web applications.

## Directory Structure

```
meetup-dashboard/
├── src/                          # Source code
│   ├── web/                      # Frontend web assets
│   │   ├── index.html           # Main HTML file
│   │   ├── styles.css           # CSS styles
│   │   ├── script.js            # JavaScript code
│   │   ├── error.html           # Error page
│   │   └── favicon.svg          # Site icon
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
├── cdk-outputs.json            # CDK deployment outputs
├── README.md                    # Project documentation
└── PROJECT_STRUCTURE.md        # This file
```

## Design Principles

### Separation of Concerns
- **src/web/**: Contains all frontend assets (HTML, CSS, JS)
- **src/lambda/**: Contains all Lambda function code
- **infrastructure/**: Contains CDK infrastructure definitions
- **scripts/**: Contains deployment and utility scripts

### Naming Conventions
- **Files**: Use snake_case for Python files, kebab-case for web assets
- **Directories**: Use lowercase with descriptive names
- **CDK Stack**: Named `MeetupDashboardStack` following PascalCase convention

### Best Practices Applied
1. **Logical Grouping**: Related files are grouped in appropriate directories
2. **Clear Separation**: Infrastructure, application code, and deployment scripts are separated
3. **Consistent Naming**: File and directory names follow established conventions
4. **Scalability**: Structure supports adding new Lambda functions or web assets easily
5. **Maintainability**: Clear organization makes the project easy to understand and modify

## File Descriptions

### Core Application Files
- `app.py`: CDK application entry point that instantiates the stack
- `infrastructure/meetup_dashboard_stack.py`: Defines all AWS resources (S3, CloudFront, Lambda, API Gateway)

### Frontend Assets (`src/web/`)
- `index.html`: Main dashboard page with responsive design
- `styles.css`: CSS styles with mobile-first responsive design
- `script.js`: JavaScript for API calls and dynamic content
- `error.html`: Error page for CloudFront error responses
- `favicon.svg`: Site icon in SVG format

### Backend Code (`src/lambda/`)
- `lambda_function.py`: Main Lambda function for Meetup API integration
- `group_details_function.py`: Lambda function for detailed group information

### Deployment Scripts (`scripts/`)
- `deploy_assets.py`: Python script for uploading web assets to S3
- `deploy_static.sh`: Shell script alternative for asset deployment
- `update_secret.sh`: Interactive script for updating Meetup API credentials

## Migration from Previous Structure

The project was reorganized from a flat structure to this hierarchical structure to:
1. Improve maintainability and readability
2. Follow AWS CDK best practices
3. Separate concerns more clearly
4. Make the project more scalable for future enhancements