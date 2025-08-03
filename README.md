# AWS User Group Dashboard

A modern web application deployed on AWS using CloudFront, S3, Lambda, and API Gateway, featuring real-time Meetup data integration and responsive design.

## 📋 Overview

This project demonstrates a complete AWS serverless web application featuring:

- **Real-time Meetup Integration**: Fetches live data from Meetup.com API via AWS Lambda
- **Interactive Dashboard**: Displays user group analytics and detailed group information
- **Responsive Design**: Mobile-first approach with modern CSS
- **AWS Serverless Architecture**: CloudFront + S3 + Lambda + API Gateway
- **Infrastructure as Code**: AWS CDK for reproducible deployments

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudFront    │────│   S3 Bucket      │────│   Static Files  │
│   Distribution  │    │   (Website)      │    │   (HTML/CSS/JS) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │────│   Lambda         │────│   Meetup API    │
│   (REST API)    │    │   Functions      │    │   (GraphQL)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│   Secrets       │
│   Manager       │
└─────────────────┘
```

## 📊 Features

### Meetup Integration
- **Live Data**: Real-time fetching from Meetup.com GraphQL API
- **Group Analytics**: Total countries, groups, and members
- **Group Details**: Individual group information with event history
- **Event Data**: Past events with RSVP counts and details

### Responsive Design
- **Mobile**: Single column layout with touch-friendly interactions
- **Tablet**: Optimized layout for medium screens
- **Desktop**: Full-featured layout with expandable group details
- **Accessibility**: High contrast support and semantic HTML

### Performance & Security
- **CDK Infrastructure**: Automated deployment and configuration
- **Secrets Management**: Secure API credential storage
- **CORS Support**: Proper cross-origin resource sharing
- **Error Handling**: Graceful fallbacks and user feedback

## 🛠️ Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Backend**: AWS Lambda (Python 3.9)
- **Infrastructure**: AWS CDK (Python)
- **Services**: CloudFront, S3, API Gateway, Lambda, Secrets Manager
- **API**: Meetup.com GraphQL API

## 📁 Project Structure

```
meetup-dashboard/
├── src/                            # Source code
│   ├── web/                        # Frontend web assets
│   │   ├── index.html             # Main HTML file
│   │   ├── styles.css             # Responsive CSS styles
│   │   ├── script.js              # Frontend JavaScript
│   │   ├── error.html             # Error page
│   │   └── favicon.svg            # Site favicon
│   └── lambda/                     # Lambda function code
│       ├── lambda_function.py      # Main Lambda function
│       └── group_details_function.py # Group details Lambda
├── infrastructure/                 # CDK infrastructure code
│   └── meetup_dashboard_stack.py   # AWS CDK stack definition
├── scripts/                        # Deployment scripts
│   ├── deploy_assets.py           # Asset deployment script
│   ├── deploy_static.sh           # Shell deployment script
│   └── update_secret.sh           # Secret management script
├── app.py                         # CDK app entry point
├── requirements.txt               # Python dependencies
├── cdk.json                       # CDK configuration
├── cdk-outputs.json              # CDK deployment outputs
├── PROJECT_STRUCTURE.md          # Project structure documentation
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with appropriate credentials
- Python 3.8+ with pip
- Node.js (for AWS CDK)
- AWS CDK CLI installed
- Domain registered (for custom domain setup)

### Deployment Steps

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd meetup-dashboard
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up custom domain (optional but recommended)**
   ```bash
   # Set up Route 53 hosted zone for geethika.dev
   python scripts/setup_route53.py
   
   # Follow the instructions to update your domain registrar's name servers
   # Wait for DNS propagation (up to 48 hours)
   ```
   
   For detailed custom domain setup instructions, see [CUSTOM_DOMAIN_SETUP.md](CUSTOM_DOMAIN_SETUP.md).

3. **Deploy infrastructure**
   ```bash
   cdk deploy --profile your-aws-profile
   ```

4. **Upload static assets**
   ```bash
   # Recommended: Python script with verification (production)
   python scripts/deploy_assets.py
   
   # Alternative: Shell script for quick deployments (development)
   ./scripts/deploy_static.sh your-aws-profile
   ```
   
   **Script Comparison:**
   - **deploy_assets.py**: Full verification, proper content-types, cache headers, accessibility testing
   - **deploy_static.sh**: Lightweight, fast, minimal dependencies

5. **Configure Meetup credentials** (optional)
   ```bash
   # Interactive script to update credentials
   ./scripts/update_secret.sh your-aws-profile
   ```
   - Secret name: `meetup-dashboard/credentials`
   - Required fields: `MEETUP_CLIENT_ID`, `MEETUP_CLIENT_SECRET`, `MEETUP_ACCESS_TOKEN`, `MEETUP_PRO_URLNAME`

6. **Access your application**
   - **Custom Domain**: `https://projects.geethika.dev/meetup-dashboard` (if configured)
   - **CloudFront**: Check `cdk-outputs.json` for the CloudFront URL + `/meetup-dashboard/`
   - **S3 Website**: Direct S3 website URL + `/meetup-dashboard/`

## 🔧 Configuration

### Deployment Scripts

Two deployment options are available for uploading static assets:

#### deploy_assets.py (Recommended)
- **Use case**: Production deployments and thorough testing
- **Features**:
  - Comprehensive verification (S3 and CloudFront accessibility)
  - Proper content-type detection and cache headers
  - Detailed error handling and logging
  - Temporary public access management for testing
  - HTTP status verification
- **Dependencies**: Python with boto3 and requests

#### deploy_static.sh
- **Use case**: Quick deployments during development
- **Features**:
  - Simple and lightweight
  - Fast execution
  - AWS profile support
- **Dependencies**: AWS CLI only

### AWS Resources Created
- **S3 Bucket**: Static website hosting with public read access
- **CloudFront Distribution**: Global CDN with optimized caching
- **Lambda Functions**: Two functions for Meetup API integration
- **API Gateway**: REST API for Lambda function access
- **Secrets Manager**: Secure storage for Meetup API credentials

### Cache Behaviors
- **HTML files**: 5-minute cache for content updates
- **CSS/JS files**: 1-day cache for performance
- **Images**: 7-day cache for optimal performance

## 🧪 API Endpoints

- **POST /meetup**: Fetch overall Meetup analytics and group list
- **POST /group-details**: Get detailed information for a specific group

Both endpoints support CORS and return JSON responses.

## 🔒 Security Features

- **HTTPS Enforcement**: All traffic redirected to HTTPS
- **Secrets Management**: API credentials stored securely
- **CORS Configuration**: Proper cross-origin access control
- **IAM Roles**: Least-privilege access for Lambda functions

## 📈 Performance

- **Global CDN**: Sub-second response times worldwide
- **Optimized Caching**: Different TTLs for different content types
- **Serverless Architecture**: Automatic scaling and high availability
- **Lightweight Frontend**: Minimal JavaScript, no external frameworks

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- AWS CDK team for the infrastructure-as-code framework
- Meetup.com for providing the GraphQL API
- The open-source community for inspiration and best practices

---

**Built with ❤️ using AWS CDK and modern web technologies**