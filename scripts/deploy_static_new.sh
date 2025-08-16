#!/bin/bash

# Enhanced shell script for quick deployments of the new meetup dashboard stack
# Usage: ./deploy_static_new.sh [AWS_PROFILE] [--verify] [--help]

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROFILE="default"
VERIFY=false
SUBDIRECTORY="meetup-dashboard-new"

# Function to display help
show_help() {
    echo "Usage: $0 [AWS_PROFILE] [OPTIONS]"
    echo ""
    echo "Quick deployment script for AWS User Group Dashboard New static assets"
    echo ""
    echo "Arguments:"
    echo "  AWS_PROFILE    AWS profile to use (default: default)"
    echo ""
    echo "Options:"
    echo "  --verify       Verify deployment after upload"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy using default profile"
    echo "  $0 gg-admin          # Deploy using gg-admin profile"
    echo "  $0 gg-admin --verify # Deploy and verify using gg-admin profile"
}

# Function to log messages with colors
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if AWS CLI is installed and configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Test AWS credentials
    if ! aws sts get-caller-identity $PROFILE_ARG &> /dev/null; then
        log_error "AWS credentials not configured or invalid for profile: $PROFILE"
        log_info "Please run: aws configure --profile $PROFILE"
        exit 1
    fi
    
    log_success "AWS CLI configured correctly for profile: $PROFILE"
}

# Function to check if local files exist
check_local_files() {
    local files=(
        "src/web/index.html"
        "src/web/styles.css"
        "src/web/script.js"
        "src/web/error.html"
        "src/web/favicon.svg"
    )
    
    local missing_files=()
    
    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        log_error "Missing local files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        exit 1
    fi
    
    log_success "All local files found"
}

# Function to get infrastructure details for new stack
get_infrastructure_details() {
    log_info "Retrieving infrastructure details for new stack..."
    
    # Try to get bucket name from CDK outputs first
    if [ -f "cdk-outputs-new.json" ]; then
        BUCKET=$(jq -r '.MeetupDashboardNewStack.S3BucketNameNew // empty' cdk-outputs-new.json 2>/dev/null)
        CLOUDFRONT_DOMAIN=$(jq -r '.MeetupDashboardNewStack.CloudFrontDomainNameNew // empty' cdk-outputs-new.json 2>/dev/null)
        CUSTOM_DOMAIN=$(jq -r '.MeetupDashboardNewStack.CustomDomainUrlNew // empty' cdk-outputs-new.json 2>/dev/null)
    fi
    
    # Fallback to CloudFormation if CDK outputs not available
    if [ -z "$BUCKET" ]; then
        log_info "CDK outputs not found, querying CloudFormation..."
        BUCKET=$(aws cloudformation describe-stacks \
            --stack-name MeetupDashboardNewStack \
            --query 'Stacks[0].Outputs[?OutputKey==`S3BucketNameNew`].OutputValue' \
            --output text $PROFILE_ARG 2>/dev/null || echo "")
        
        CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks \
            --stack-name MeetupDashboardNewStack \
            --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomainNameNew`].OutputValue' \
            --output text $PROFILE_ARG 2>/dev/null || echo "")
    fi
    
    if [ -z "$BUCKET" ]; then
        log_error "Could not find S3 bucket name from infrastructure"
        log_info "Please ensure the CDK stack is deployed: cdk deploy --app \"python app_new.py\""
        exit 1
    fi
    
    log_success "Infrastructure details retrieved:"
    echo "  S3 Bucket: $BUCKET"
    echo "  CloudFront Domain: ${CLOUDFRONT_DOMAIN:-Not found}"
    echo "  Custom Domain: ${CUSTOM_DOMAIN:-Not configured}"
}

# Function to upload files with proper content types and cache headers
upload_files() {
    log_info "Uploading files to s3://$BUCKET/$SUBDIRECTORY/..."
    
    local files=(
        "src/web/index.html:text/html:max-age=300"
        "src/web/styles.css:text/css:max-age=86400"
        "src/web/script.js:application/javascript:max-age=86400"
        "src/web/error.html:text/html:max-age=300"
        "src/web/favicon.svg:image/svg+xml:max-age=604800"
    )
    
    local upload_count=0
    local total_files=${#files[@]}
    
    for file_info in "${files[@]}"; do
        IFS=':' read -r file_path content_type cache_control <<< "$file_info"
        local filename=$(basename "$file_path")
        
        echo "  Uploading $filename..."
        
        if aws s3 cp "$file_path" "s3://$BUCKET/$SUBDIRECTORY/" \
            --content-type "$content_type" \
            --cache-control "$cache_control" \
            --metadata "uploaded-by=deploy-static-new-script,upload-timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            $PROFILE_ARG; then
            ((upload_count++))
            echo "    ✓ $filename uploaded successfully"
        else
            log_error "Failed to upload $filename"
            exit 1
        fi
    done
    
    log_success "All $upload_count/$total_files files uploaded successfully"
}

# Function to verify deployment
verify_deployment() {
    if [ "$VERIFY" = false ]; then
        return 0
    fi
    
    log_info "Verifying deployment..."
    
    # Check if files exist in S3
    local files=("index.html" "styles.css" "script.js" "error.html" "favicon.svg")
    local verification_failed=false
    
    for file in "${files[@]}"; do
        if aws s3api head-object --bucket "$BUCKET" --key "$SUBDIRECTORY/$file" $PROFILE_ARG &> /dev/null; then
            echo "  ✓ $file exists in S3"
        else
            echo "  ✗ $file not found in S3"
            verification_failed=true
        fi
    done
    
    if [ "$verification_failed" = true ]; then
        log_error "Deployment verification failed"
        exit 1
    fi
    
    log_success "Deployment verification passed"
}

# Function to display deployment URLs
show_deployment_urls() {
    log_success "Deployment completed successfully!"
    echo ""
    echo "🌐 Your website is available at:"
    
    if [ -n "$CLOUDFRONT_DOMAIN" ]; then
        echo "   CloudFront: https://$CLOUDFRONT_DOMAIN/$SUBDIRECTORY/"
    fi
    
    if [ -n "$CUSTOM_DOMAIN" ] && [ "$CUSTOM_DOMAIN" != "null" ] && [ "$CUSTOM_DOMAIN" != "Not configured" ]; then
        echo "   Custom Domain: $CUSTOM_DOMAIN"
    fi
    
    echo ""
    log_info "Note: CloudFront may take a few minutes to serve updated content due to caching"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verify)
            VERIFY=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        --*)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            if [ -z "$PROFILE_SET" ]; then
                PROFILE="$1"
                PROFILE_SET=true
            else
                log_error "Too many arguments"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Set up AWS profile argument
PROFILE_ARG=""
if [ "$PROFILE" != "default" ]; then
    PROFILE_ARG="--profile $PROFILE"
fi

# Main execution
main() {
    echo "=== AWS User Group Dashboard New - Quick Deployment ==="
    echo ""
    
    log_info "Starting deployment with profile: $PROFILE"
    log_info "Target subdirectory: $SUBDIRECTORY"
    log_info "Verification: $([ "$VERIFY" = true ] && echo "enabled" || echo "disabled")"
    echo ""
    
    # Pre-flight checks
    check_aws_cli
    check_local_files
    get_infrastructure_details
    
    # Deploy files
    upload_files
    
    # Verify deployment if requested
    verify_deployment
    
    # Show success message and URLs
    show_deployment_urls
}

# Run main function
main