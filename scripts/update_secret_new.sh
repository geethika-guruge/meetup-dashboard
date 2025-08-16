#!/bin/bash

# Enhanced script for updating Secrets Manager credentials for the new stack
# Usage: ./update_secret_new.sh [AWS_PROFILE] [OPTIONS]

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROFILE="default"
SECRET_ID="meetup-dashboard-new/credentials"
SHOW_CURRENT=false
VALIDATE_CREDENTIALS=false

# Function to display help
show_help() {
    echo "Usage: $0 [AWS_PROFILE] [OPTIONS]"
    echo ""
    echo "Interactive script to update Meetup API credentials in AWS Secrets Manager for new stack"
    echo ""
    echo "Arguments:"
    echo "  AWS_PROFILE    AWS profile to use (default: default)"
    echo ""
    echo "Options:"
    echo "  --show-current Show current credentials (masked)"
    echo "  --validate     Validate credentials after update"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Update using default profile"
    echo "  $0 gg-admin                 # Update using gg-admin profile"
    echo "  $0 gg-admin --show-current  # Show current values before update"
    echo "  $0 gg-admin --validate      # Validate credentials after update"
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

# Function to check if secret exists
check_secret_exists() {
    if aws secretsmanager describe-secret --secret-id "$SECRET_ID" $PROFILE_ARG &> /dev/null; then
        log_success "Secret '$SECRET_ID' found"
        return 0
    else
        log_warning "Secret '$SECRET_ID' not found"
        return 1
    fi
}

# Function to show current credentials (masked)
show_current_credentials() {
    if [ "$SHOW_CURRENT" = false ]; then
        return 0
    fi
    
    log_info "Retrieving current credentials..."
    
    if ! check_secret_exists; then
        log_warning "Cannot show current credentials - secret does not exist"
        return 0
    fi
    
    local secret_value
    secret_value=$(aws secretsmanager get-secret-value --secret-id "$SECRET_ID" --query 'SecretString' --output text $PROFILE_ARG 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$secret_value" ]; then
        echo ""
        echo "Current credentials (masked):"
        
        # Parse JSON and show masked values
        local client_id=$(echo "$secret_value" | jq -r '.MEETUP_CLIENT_ID // "Not set"')
        local pro_urlname=$(echo "$secret_value" | jq -r '.MEETUP_PRO_URLNAME // "Not set"')
        local access_token=$(echo "$secret_value" | jq -r '.MEETUP_ACCESS_TOKEN // "Not set"')
        local client_secret=$(echo "$secret_value" | jq -r '.MEETUP_CLIENT_SECRET // "Not set"')
        
        echo "  MEETUP_CLIENT_ID: ${client_id:0:8}***"
        echo "  MEETUP_PRO_URLNAME: $pro_urlname"
        echo "  MEETUP_ACCESS_TOKEN: ${access_token:0:8}***"
        echo "  MEETUP_CLIENT_SECRET: ${client_secret:0:8}***"
        echo ""
    else
        log_warning "Could not retrieve current credentials"
    fi
}

# Function to validate input
validate_input() {
    local field_name="$1"
    local field_value="$2"
    local required="$3"
    
    if [ "$required" = true ] && [ -z "$field_value" ]; then
        log_error "$field_name is required"
        return 1
    fi
    
    # Additional validation based on field type
    case "$field_name" in
        "MEETUP_PRO_URLNAME")
            if [ -n "$field_value" ] && [[ ! "$field_value" =~ ^[a-zA-Z0-9_-]+$ ]]; then
                log_error "PRO_URLNAME should only contain letters, numbers, hyphens, and underscores"
                return 1
            fi
            ;;
        "MEETUP_ACCESS_TOKEN")
            if [ -n "$field_value" ] && [ ${#field_value} -lt 10 ]; then
                log_warning "Access token seems too short (less than 10 characters)"
            fi
            ;;
    esac
    
    return 0
}

# Function to collect credentials interactively
collect_credentials() {
    log_info "Please enter the Meetup API credentials for the new stack:"
    echo ""
    
    # Get current values if secret exists
    local current_client_id=""
    local current_pro_urlname=""
    
    if check_secret_exists; then
        local secret_value
        secret_value=$(aws secretsmanager get-secret-value --secret-id "$SECRET_ID" --query 'SecretString' --output text $PROFILE_ARG 2>/dev/null)
        
        if [ $? -eq 0 ] && [ -n "$secret_value" ]; then
            current_client_id=$(echo "$secret_value" | jq -r '.MEETUP_CLIENT_ID // ""')
            current_pro_urlname=$(echo "$secret_value" | jq -r '.MEETUP_PRO_URLNAME // ""')
        fi
    fi
    
    # Collect CLIENT_ID
    local default_client_id="${current_client_id:-Meetup-Dashboard-New}"
    read -p "Enter MEETUP_CLIENT_ID (default: $default_client_id): " CLIENT_ID
    CLIENT_ID=${CLIENT_ID:-"$default_client_id"}
    
    if ! validate_input "MEETUP_CLIENT_ID" "$CLIENT_ID" true; then
        exit 1
    fi
    
    # Collect PRO_URLNAME
    local pro_prompt="Enter MEETUP_PRO_URLNAME"
    if [ -n "$current_pro_urlname" ]; then
        pro_prompt="$pro_prompt (current: $current_pro_urlname, press Enter to keep)"
    fi
    read -p "$pro_prompt: " PRO_URLNAME
    
    if [ -z "$PRO_URLNAME" ] && [ -n "$current_pro_urlname" ]; then
        PRO_URLNAME="$current_pro_urlname"
    fi
    
    if ! validate_input "MEETUP_PRO_URLNAME" "$PRO_URLNAME" true; then
        exit 1
    fi
    
    # Collect ACCESS_TOKEN
    read -s -p "Enter MEETUP_ACCESS_TOKEN: " ACCESS_TOKEN
    echo
    
    if ! validate_input "MEETUP_ACCESS_TOKEN" "$ACCESS_TOKEN" true; then
        exit 1
    fi
    
    # Collect CLIENT_SECRET
    read -s -p "Enter MEETUP_CLIENT_SECRET: " CLIENT_SECRET
    echo
    
    if ! validate_input "MEETUP_CLIENT_SECRET" "$CLIENT_SECRET" true; then
        exit 1
    fi
    
    echo ""
    log_success "All credentials collected successfully"
}

# Function to update secret
update_secret() {
    log_info "Updating secret in AWS Secrets Manager..."
    
    # Create JSON payload
    local secret_json
    secret_json=$(jq -n \
        --arg client_id "$CLIENT_ID" \
        --arg client_secret "$CLIENT_SECRET" \
        --arg access_token "$ACCESS_TOKEN" \
        --arg pro_urlname "$PRO_URLNAME" \
        '{
            MEETUP_CLIENT_ID: $client_id,
            MEETUP_CLIENT_SECRET: $client_secret,
            MEETUP_ACCESS_TOKEN: $access_token,
            MEETUP_PRO_URLNAME: $pro_urlname
        }')
    
    # Update or create secret
    if check_secret_exists; then
        # Update existing secret
        if aws secretsmanager update-secret \
            --secret-id "$SECRET_ID" \
            --secret-string "$secret_json" \
            $PROFILE_ARG > /dev/null 2>&1; then
            log_success "Secret updated successfully!"
        else
            log_error "Failed to update secret"
            exit 1
        fi
    else
        # Create new secret
        log_info "Secret does not exist, creating new secret..."
        if aws secretsmanager create-secret \
            --name "$SECRET_ID" \
            --description "Meetup API credentials for AWS User Group Dashboard New" \
            --secret-string "$secret_json" \
            $PROFILE_ARG > /dev/null 2>&1; then
            log_success "Secret created successfully!"
        else
            log_error "Failed to create secret"
            exit 1
        fi
    fi
}

# Function to validate credentials (basic check)
validate_credentials() {
    if [ "$VALIDATE_CREDENTIALS" = false ]; then
        return 0
    fi
    
    log_info "Validating credentials..."
    
    # Basic validation - check if we can retrieve the secret
    local retrieved_secret
    retrieved_secret=$(aws secretsmanager get-secret-value --secret-id "$SECRET_ID" --query 'SecretString' --output text $PROFILE_ARG 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$retrieved_secret" ]; then
        # Parse and verify all fields are present
        local fields=("MEETUP_CLIENT_ID" "MEETUP_CLIENT_SECRET" "MEETUP_ACCESS_TOKEN" "MEETUP_PRO_URLNAME")
        local validation_passed=true
        
        for field in "${fields[@]}"; do
            local value=$(echo "$retrieved_secret" | jq -r ".$field // \"\"")
            if [ -z "$value" ]; then
                log_error "Field $field is missing or empty in stored secret"
                validation_passed=false
            fi
        done
        
        if [ "$validation_passed" = true ]; then
            log_success "Credential validation passed"
        else
            log_error "Credential validation failed"
            exit 1
        fi
    else
        log_error "Could not retrieve secret for validation"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --show-current)
            SHOW_CURRENT=true
            shift
            ;;
        --validate)
            VALIDATE_CREDENTIALS=true
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
    echo "=== AWS User Group Dashboard New - Secrets Manager Update ==="
    echo ""
    
    log_info "Updating credentials using profile: $PROFILE"
    log_info "Secret ID: $SECRET_ID"
    echo ""
    
    # Pre-flight checks
    check_aws_cli
    
    # Show current credentials if requested
    show_current_credentials
    
    # Collect new credentials
    collect_credentials
    
    # Confirm before updating
    echo ""
    read -p "Do you want to update the secret with these credentials? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled by user"
        exit 0
    fi
    
    # Update secret
    update_secret
    
    # Validate credentials if requested
    validate_credentials
    
    echo ""
    log_success "Meetup API credentials updated successfully for new stack!"
    log_info "The Lambda functions will use these credentials on their next execution"
}

# Check for required dependencies
if ! command -v jq &> /dev/null; then
    log_error "jq is required but not installed. Please install jq first."
    log_info "On macOS: brew install jq"
    log_info "On Ubuntu/Debian: sudo apt-get install jq"
    exit 1
fi

# Run main function
main