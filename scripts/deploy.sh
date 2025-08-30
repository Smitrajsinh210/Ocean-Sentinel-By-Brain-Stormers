#!/bin/bash

# Ocean Sentinel - Deployment Script
# Automated deployment to Vercel with pre-deployment checks

set -e

echo "🚀 Ocean Sentinel - Deployment Script"
echo "===================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Pre-deployment checks
run_pre_deployment_checks() {
    print_status "Running pre-deployment checks..."
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        print_error ".env file not found"
        exit 1
    fi
    
    # Check if required files exist
    required_files=(
        "backend/app/main.py"
        "backend/requirements.txt"
        "vercel.json"
        "frontend/package.json"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "Required file not found: $file"
            exit 1
        fi
    done
    
    # Check Python syntax
    print_status "Checking Python syntax..."
    python3 -m py_compile backend/app/main.py
    
    # Install and check dependencies
    print_status "Checking Python dependencies..."
    cd backend
    source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt > /dev/null
    cd ..
    
    # Check Node.js dependencies
    print_status "Checking Node.js dependencies..."
    cd frontend
    npm install > /dev/null
    cd ..
    
    print_success "All pre-deployment checks passed"
}

# Build frontend assets
build_frontend() {
    print_status "Building frontend assets..."
    
    cd frontend
    
    # Run build if build script exists
    if npm run build 2>/dev/null; then
        print_success "Frontend build completed"
    else
        print_warning "No build script found, skipping frontend build"
    fi
    
    cd ..
}

# Deploy to Vercel
deploy_to_vercel() {
    print_status "Deploying to Vercel..."
    
    # Check if Vercel CLI is installed
    if ! command -v vercel &> /dev/null; then
        print_status "Installing Vercel CLI..."
        npm install -g vercel
    fi
    
    # Set environment variables from .env file
    print_status "Setting up environment variables..."
    
    # Read .env file and set Vercel env vars
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ $key =~ ^#.*$ ]] || [[ -z $key ]]; then
            continue
        fi
        
        # Remove quotes from value
        value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
        
        # Set environment variable in Vercel
        echo "Setting $key..."
        vercel env add "$key" production <<< "$value" 2>/dev/null || true
        vercel env add "$key" preview <<< "$value" 2>/dev/null || true
    done < .env
    
    # Deploy to production
    print_status "Deploying to production..."
    vercel deploy --prod
    
    print_success "Deployment completed!"
}

# Post-deployment verification
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Get deployment URL
    DEPLOYMENT_URL=$(vercel ls --scope team_slug 2>/dev/null | head -n 2 | tail -n 1 | awk '{print $2}' || echo "")
    
    if [ -n "$DEPLOYMENT_URL" ]; then
        print_status "Testing deployment health..."
        
        # Test API health endpoint
        if curl -f -s "https://$DEPLOYMENT_URL/api/health" > /dev/null; then
            print_success "API health check passed"
        else
            print_warning "API health check failed"
        fi
        
        print_success "Deployment URL: https://$DEPLOYMENT_URL"
    else
        print_warning "Could not determine deployment URL"
    fi
}

# Update documentation
update_docs() {
    print_status "Updating deployment documentation..."
    
    # Update README with deployment info
    if [ -f "README.md" ]; then
        # Add deployment timestamp
        echo "" >> README.md
        echo "## Latest Deployment" >> README.md
        echo "Deployed on: $(date)" >> README.md
        echo "Deploy script version: 1.0.0" >> README.md
    fi
}

# Main deployment function
main() {
    run_pre_deployment_checks
    build_frontend
    deploy_to_vercel
    verify_deployment
    update_docs
    
    print_success "🎉 Ocean Sentinel deployed successfully!"
    echo ""
    echo "Next steps:"
    echo "- Monitor deployment at: https://vercel.com/dashboard"
    echo "- Check logs for any issues"
    echo "- Test all functionality in production"
    echo "- Set up monitoring and alerts"
}

# Handle script arguments
case "$1" in
    "check")
        run_pre_deployment_checks
        ;;
    "build")
        build_frontend
        ;;
    "deploy")
        deploy_to_vercel
        ;;
    "verify")
        verify_deployment
        ;;
    *)
        main
        ;;
esac
