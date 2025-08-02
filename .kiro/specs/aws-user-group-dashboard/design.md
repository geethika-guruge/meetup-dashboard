# Design Document

## Overview

The AWS User Group Dashboard is a serverless web application built on AWS infrastructure that provides real-time analytics and insights for AWS user groups worldwide. The application follows a modern three-tier architecture with a React-like frontend (vanilla JavaScript), serverless backend (AWS Lambda), and external API integration (Meetup.com GraphQL API). The design emphasizes performance, security, scalability, and user experience while maintaining cost-effectiveness through serverless technologies.

## Architecture

### High-Level Architecture

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

### Technology Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript (ES6+)
- **CDN**: AWS CloudFront for global content delivery
- **Storage**: AWS S3 for static website hosting
- **API Layer**: AWS API Gateway (REST API)
- **Compute**: AWS Lambda (Python 3.9)
- **Security**: AWS Secrets Manager for credential storage
- **Infrastructure**: AWS CDK (Python) for Infrastructure as Code
- **External API**: Meetup.com GraphQL API

### Design Principles

1. **Serverless-First**: Utilize AWS serverless services for automatic scaling and cost optimization
2. **Security by Design**: Implement least-privilege access and secure credential management
3. **Performance Optimization**: Leverage CDN caching and efficient API design
4. **Responsive Design**: Mobile-first approach with progressive enhancement
5. **Graceful Degradation**: Fallback mechanisms for API failures and missing credentials
6. **Accessibility**: WCAG 2.1 AA compliance with semantic HTML and proper ARIA labels

## Components and Interfaces

### Frontend Components

#### 1. Dashboard Container (`aws-container`)
- **Purpose**: Main application wrapper providing layout structure
- **Responsibilities**: 
  - Manages overall page layout (header, main, footer)
  - Provides consistent spacing and responsive behavior
  - Handles global CSS custom properties

#### 2. Header Component (`aws-header`)
- **Purpose**: Application branding and navigation
- **Responsibilities**:
  - Displays AWS User Group Dashboard title and logo
  - Provides consistent branding across the application
  - Responsive design for mobile devices

#### 3. Analytics Card (`analytics-card`)
- **Purpose**: Displays high-level metrics and data fetching controls
- **Responsibilities**:
  - Houses the "Load Data" button for triggering API calls
  - Displays total countries, groups, and members in a grid layout
  - Manages loading states and error handling for analytics data

#### 4. Groups Table Component (`groups-card`)
- **Purpose**: Interactive table displaying detailed group information
- **Responsibilities**:
  - Renders sortable table with group details
  - Handles row expansion for detailed group information
  - Manages individual group detail API calls
  - Provides responsive table design for mobile devices

#### 5. Group Details Component (Dynamic)
- **Purpose**: Expandable section showing detailed group information
- **Responsibilities**:
  - Displays past events with dates, titles, and RSVP counts
  - Handles loading states for individual group data
  - Provides error handling for failed group detail requests

### Backend Components

#### 1. Main Lambda Function (`lambda_function.py`)
- **Purpose**: Primary API endpoint for fetching Meetup analytics and group data
- **Responsibilities**:
  - Retrieves credentials from AWS Secrets Manager
  - Constructs and executes GraphQL queries to Meetup API
  - Processes and transforms API responses
  - Implements fallback to mock data when credentials are unavailable
  - Handles CORS preflight requests

#### 2. Group Details Lambda Function (`group_details_function.py`)
- **Purpose**: Specialized endpoint for fetching detailed group information
- **Responsibilities**:
  - Fetches individual group event history
  - Processes event data including RSVP counts and dates
  - Provides detailed error handling for group-specific requests
  - Implements efficient GraphQL queries for event data

#### 3. Infrastructure Stack (`meetup_dashboard_stack.py`)
- **Purpose**: AWS CDK stack defining all infrastructure resources
- **Responsibilities**:
  - Creates and configures S3 bucket with proper policies
  - Sets up CloudFront distribution with optimized caching
  - Defines Lambda functions with appropriate permissions
  - Configures API Gateway with CORS support
  - Manages Secrets Manager for credential storage
  - Outputs deployment information for reference

### API Interfaces

#### 1. Meetup Analytics Endpoint
- **Method**: POST
- **Path**: `/meetup`
- **Request Body**: `{}`
- **Response Format**:
```json
{
  "success": true,
  "data": {
    "totalCountries": number,
    "totalGroups": number,
    "totalMembers": number,
    "groups": [
      {
        "id": string,
        "name": string,
        "country": string,
        "foundedDate": string,
        "stats": { "memberCounts": { "all": number } },
        "eventsLast12Months": number,
        "avgRsvpsLast12Months": number
      }
    ]
  }
}
```

#### 2. Group Details Endpoint
- **Method**: POST
- **Path**: `/group-details`
- **Request Body**: `{ "groupId": string }`
- **Response Format**:
```json
{
  "success": true,
  "data": {
    "groupId": string,
    "totalPastEvents": number,
    "events": [
      {
        "title": string,
        "dateTime": string,
        "rsvps": { "totalCount": number },
        "eventHosts": [{ "name": string }]
      }
    ]
  }
}
```

## Data Models

### Group Model
```typescript
interface Group {
  id: string;
  name: string;
  country: string;
  foundedDate: string;
  stats: {
    memberCounts: {
      all: number;
    };
  };
  eventsLast12Months: number;
  avgRsvpsLast12Months: number;
}
```

### Event Model
```typescript
interface Event {
  title: string;
  dateTime: string;
  rsvps: {
    totalCount: number;
  };
  eventHosts: Array<{
    name: string;
  }>;
}
```

### Analytics Model
```typescript
interface Analytics {
  totalCountries: number;
  totalGroups: number;
  totalMembers: number;
  groups: Group[];
}
```

### API Response Model
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  note?: string; // For mock data notifications
}
```

## Error Handling

### Frontend Error Handling

1. **Network Errors**: Display user-friendly messages for connection issues
2. **API Errors**: Show specific error messages returned from Lambda functions
3. **Loading States**: Provide visual feedback during API calls
4. **Graceful Degradation**: Continue functioning when non-critical features fail

### Backend Error Handling

1. **Credential Management**: Fallback to mock data when credentials are unavailable
2. **API Rate Limiting**: Implement retry logic with exponential backoff
3. **GraphQL Errors**: Parse and handle GraphQL-specific error responses
4. **Timeout Handling**: Set appropriate timeouts for external API calls
5. **Logging**: Comprehensive logging for debugging and monitoring

### Error Response Format
```json
{
  "success": false,
  "error": "User-friendly error message",
  "details": "Technical details for debugging (optional)"
}
```

## Testing Strategy

### Frontend Testing

1. **Unit Testing**: Test individual JavaScript functions and components
2. **Integration Testing**: Test API integration and data flow
3. **Responsive Testing**: Verify layout across different screen sizes
4. **Accessibility Testing**: Validate WCAG compliance and screen reader compatibility
5. **Cross-Browser Testing**: Ensure compatibility across modern browsers

### Backend Testing

1. **Unit Testing**: Test individual Lambda functions with mock data
2. **Integration Testing**: Test API Gateway and Lambda integration
3. **Mock API Testing**: Verify fallback behavior when credentials are unavailable
4. **Error Scenario Testing**: Test various failure modes and error handling
5. **Performance Testing**: Validate response times and memory usage

### Infrastructure Testing

1. **CDK Testing**: Validate CloudFormation template generation
2. **Deployment Testing**: Verify successful deployment across environments
3. **Security Testing**: Validate IAM permissions and access controls
4. **Monitoring Testing**: Ensure proper logging and alerting configuration

### End-to-End Testing

1. **User Journey Testing**: Test complete user workflows from data loading to group details
2. **Performance Testing**: Validate page load times and API response times
3. **Security Testing**: Verify HTTPS enforcement and CORS configuration
4. **Disaster Recovery Testing**: Test application behavior during AWS service outages

## Security Considerations

### Authentication and Authorization
- OAuth2 integration with Meetup.com API
- AWS IAM roles with least-privilege access
- Secrets Manager for secure credential storage

### Data Protection
- HTTPS enforcement through CloudFront
- Secure API communication with proper headers
- No sensitive data stored in frontend code

### Infrastructure Security
- S3 bucket policies restricting access
- Lambda function environment variable encryption
- API Gateway throttling and request validation

### Monitoring and Auditing
- CloudWatch logging for all Lambda functions
- API Gateway access logging
- CloudTrail for infrastructure changes