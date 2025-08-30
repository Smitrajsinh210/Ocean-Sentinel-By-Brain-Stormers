#!/bin/bash

# Ocean Sentinel - Complete Setup Script
# This script sets up the entire Ocean Sentinel application

set -e  # Exit on any error

echo "🌊 Ocean Sentinel - Complete Setup Script"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check for Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed"
        exit 1
    fi
    
    # Check for npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed"
        exit 1
    fi
    
    # Check for git
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed"
        exit 1
    fi
    
    print_success "All dependencies are installed"
}

# Create project directory structure
create_directory_structure() {
    print_status "Creating directory structure..."
    
    # Create main directories
    mkdir -p backend/app/{models,routes,services,utils}
    mkdir -p frontend/{bubble_integration/{js,css},assets}
    mkdir -p database
    mkdir -p scripts
    mkdir -p docs
    mkdir -p tests/{backend,frontend}
    mkdir -p models/tensorflowjs
    
    print_success "Directory structure created"
}

# Setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    cd backend
    
    # Create virtual environment
    python3 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found. You'll need to install dependencies manually."
    fi
    
    cd ..
}

# Setup Node.js dependencies
setup_node_env() {
    print_status "Setting up Node.js environment..."
    
    cd frontend
    
    if [ -f "package.json" ]; then
        npm install
        print_success "Node.js dependencies installed"
    else
        print_warning "package.json not found. You'll need to install dependencies manually."
    fi
    
    cd ..
}

# Create environment file
create_env_file() {
    print_status "Creating environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Environment file created from template"
            print_warning "Please edit .env file with your actual API keys and configuration"
        else
            print_warning ".env.example not found. You'll need to create .env manually."
        fi
    else
        print_warning ".env file already exists"
    fi
}

# Setup database
setup_database() {
    print_status "Setting up database..."
    
    if [ -f "database/schema.sql" ]; then
        print_success "Database schema found"
        print_warning "Please run the schema.sql file in your Supabase project"
        print_warning "Also run database/seed_data.sql for sample data"
    else
        print_warning "Database schema not found"
    fi
}

# Setup Git repository
setup_git() {
    print_status "Setting up Git repository..."
    
    if [ ! -d ".git" ]; then
        git init
        
        # Create .gitignore if it doesn't exist
        if [ ! -f ".gitignore" ]; then
            cat > .gitignore << EOF
# Environment variables
.env
.env.local
.env.production

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
venv/
env/

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.yarn-integrity

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs
*.log

# Temporary files
*.tmp
*.temp

# Build outputs
dist/
build/

# Cache
.cache/
.parcel-cache/

# Coverage reports
coverage/
.nyc_output

# Vercel
.vercel
EOF
        fi
        
        git add .
        git commit -m "Initial commit: Ocean Sentinel project setup"
        
        print_success "Git repository initialized"
    else
        print_warning "Git repository already exists"
    fi
}

# Install Vercel CLI (optional)
install_vercel_cli() {
    print_status "Installing Vercel CLI..."
    
    if command -v vercel &> /dev/null; then
        print_warning "Vercel CLI already installed"
    else
        npm install -g vercel
        print_success "Vercel CLI installed"
    fi
}

# Run setup checks
run_setup_checks() {
    print_status "Running setup validation checks..."
    
    # Check Python imports
    cd backend
    source venv/bin/activate
    python -c "import fastapi, uvicorn, supabase; print('✅ Core Python packages working')" || print_error "Python package imports failed"
    cd ..
    
    # Check Node.js setup
    cd frontend
    if [ -f "package.json" ]; then
        node -e "console.log('✅ Node.js environment working')"
    fi
    cd ..
    
    print_success "Setup validation completed"
}

# Display next steps
show_next_steps() {
    print_success "Ocean Sentinel setup completed!"
    echo ""
    echo "🚀 Next Steps:"
    echo "=============="
    echo ""
    echo "1. Configure Environment Variables:"
    echo "   - Edit .env file with your API keys"
    echo "   - Get API keys from:"
    echo "     * Supabase: https://app.supabase.com"
    echo "     * OpenWeatherMap: https://openweathermap.org/api"
    echo "     * Google AI Studio: https://makersuite.google.com"
    echo "     * Starton: https://app.starton.io"
    echo "     * Pusher: https://pusher.com"
    echo "     * Twilio: https://twilio.com"
    echo ""
    echo "2. Setup Database:"
    echo "   - Create Supabase project"
    echo "   - Run database/schema.sql in Supabase SQL editor"
    echo "   - Run database/seed_data.sql for sample data"
    echo ""
    echo "3. Deploy Smart Contract:"
    echo "   - Create Starton account"
    echo "   - Deploy data logging smart contract"
    echo "   - Update CONTRACT_ADDRESS in .env"
    echo ""
    echo "4. Test the application:"
    echo "   - Backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo "   - Frontend: cd frontend && npm run dev"
    echo ""
    echo "5. Deploy to production:"
    echo "   - vercel deploy"
    echo ""
    echo "📚 Documentation: Check docs/ folder for detailed guides"
    echo "🐛 Issues: Report at https://github.com/your-org/ocean-sentinel/issues"
    echo ""
    echo "Happy coding! 🌊"
}

# Main execution
main() {
    check_dependencies
    create_directory_structure
    setup_python_env
    setup_node_env
    create_env_file
    setup_database
    setup_git
    install_vercel_cli
    run_setup_checks
    show_next_steps
}

# Run main function
main
