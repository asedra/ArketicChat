#!/bin/bash

# ATTILA AI Enhanced Function Management System - Setup Script
# This script sets up the complete development environment

set -e  # Exit on any error

echo "🚀 ATTILA AI Enhanced Function Management System Setup"
echo "======================================================"
echo ""

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

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python found: $PYTHON_VERSION"
        
        # Check if Python version is 3.11+
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
            print_success "Python version is compatible (3.11+)"
        else
            print_error "Python 3.11+ is required. Current version: $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi
    
    # Check pip
    if command_exists pip3 || command_exists pip; then
        print_success "pip found"
    else
        print_error "pip not found. Please install pip"
        exit 1
    fi
    
    # Check Node.js
    if command_exists node; then
        NODE_VERSION=$(node --version)
        print_success "Node.js found: $NODE_VERSION"
        
        # Check if Node version is 18+
        if node -e "process.exit(process.version.slice(1).split('.')[0] >= 18 ? 0 : 1)"; then
            print_success "Node.js version is compatible (18+)"
        else
            print_error "Node.js 18+ is required. Current version: $NODE_VERSION"
            exit 1
        fi
    else
        print_error "Node.js not found. Please install Node.js 18+"
        exit 1
    fi
    
    # Check npm
    if command_exists npm; then
        NPM_VERSION=$(npm --version)
        print_success "npm found: $NPM_VERSION"
    else
        print_error "npm not found. Please install npm"
        exit 1
    fi
    
    echo ""
}

# Setup backend
setup_backend() {
    print_status "Setting up backend..."
    
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    print_success "Python dependencies installed"
    
    # Setup environment file
    if [ ! -f ".env" ]; then
        print_status "Creating environment file..."
        cp .env.example .env
        print_warning "Please edit .env file and add your OpenAI API key"
        print_warning "OPENAI_API_KEY=your_openai_api_key_here"
    else
        print_success "Environment file already exists"
    fi
    
    # Initialize database
    print_status "Initializing database..."
    python -c "
import asyncio
from app.core.database import init_db

async def main():
    await init_db()
    print('Database initialized successfully')

if __name__ == '__main__':
    asyncio.run(main())
" || print_warning "Database initialization skipped (may already be initialized)"
    
    cd ..
    print_success "Backend setup complete"
    echo ""
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    print_success "Node.js dependencies installed"
    
    # Build project (optional, for production)
    if [ "$1" == "production" ]; then
        print_status "Building frontend for production..."
        npm run build
        print_success "Frontend built for production"
    fi
    
    print_success "Frontend setup complete"
    echo ""
}

# Create startup scripts
create_startup_scripts() {
    print_status "Creating startup scripts..."
    
    # Backend start script
    cat > start_backend.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting ATTILA AI Backend..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
EOF
    chmod +x start_backend.sh
    
    # Frontend start script
    cat > start_frontend.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting ATTILA AI Frontend..."
npm run dev -- --host 0.0.0.0 --port 5173
EOF
    chmod +x start_frontend.sh
    
    # Combined start script
    cat > start_all.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting ATTILA AI Complete System..."
echo "Starting backend and frontend in parallel..."

# Start backend in background
./start_backend.sh &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend in background
./start_frontend.sh &
FRONTEND_PID=$!

echo ""
echo "✅ ATTILA AI is starting up!"
echo "📍 Frontend: http://localhost:5173"
echo "📍 Backend API: http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
EOF
    chmod +x start_all.sh
    
    print_success "Startup scripts created"
    echo ""
}

# Create development helpers
create_dev_helpers() {
    print_status "Creating development helpers..."
    
    # Database reset script
    cat > reset_database.sh << 'EOF'
#!/bin/bash
echo "🗄️ Resetting ATTILA AI Database..."
cd backend
source venv/bin/activate
rm -f attila_ai.db
python -c "
import asyncio
from app.core.database import init_db

async def main():
    await init_db()
    print('✅ Database reset and reinitialized')

if __name__ == '__main__':
    asyncio.run(main())
"
EOF
    chmod +x reset_database.sh
    
    # Test API script
    cat > test_api.sh << 'EOF'
#!/bin/bash
echo "🧪 Testing ATTILA AI API..."
echo "Testing health endpoint..."
curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ Backend not running or unhealthy"
echo ""
echo "Testing functions endpoint..."
curl -s http://localhost:8000/functions/ | python3 -m json.tool || echo "❌ Functions endpoint not available"
EOF
    chmod +x test_api.sh
    
    print_success "Development helpers created"
    echo ""
}

# Display final instructions
show_final_instructions() {
    echo "🎉 ATTILA AI Setup Complete!"
    echo "=========================="
    echo ""
    echo "📋 Next Steps:"
    echo "1. Edit backend/.env and add your OpenAI API key:"
    echo "   OPENAI_API_KEY=your_openai_api_key_here"
    echo ""
    echo "2. Start the system:"
    echo "   ./start_all.sh     # Start both backend and frontend"
    echo "   OR"
    echo "   ./start_backend.sh  # Start only backend"
    echo "   ./start_frontend.sh # Start only frontend"
    echo ""
    echo "3. Access the application:"
    echo "   🌐 Frontend: http://localhost:5173"
    echo "   🔧 Backend API: http://localhost:8000"
    echo "   📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "🛠️ Development Tools:"
    echo "   ./reset_database.sh # Reset database"
    echo "   ./test_api.sh       # Test API endpoints"
    echo ""
    echo "📖 Documentation:"
    echo "   - README.md: Project overview"
    echo "   - docs/: Detailed documentation"
    echo "   - PHASE_4_COMPLETION_REPORT.md: Complete implementation details"
    echo ""
    echo "🆘 Need Help?"
    echo "   - Check the documentation in the docs/ folder"
    echo "   - Ensure your OpenAI API key is set correctly"
    echo "   - Make sure ports 8000 and 5173 are available"
    echo ""
}

# Main setup process
main() {
    print_status "ATTILA AI Enhanced Function Management System"
    print_status "Automated Setup Process Starting..."
    echo ""
    
    # Parse arguments
    PRODUCTION_MODE=""
    if [ "$1" == "--production" ]; then
        PRODUCTION_MODE="production"
        print_status "Running in production mode"
    fi
    
    # Run setup steps
    check_prerequisites
    setup_backend
    setup_frontend $PRODUCTION_MODE
    create_startup_scripts
    create_dev_helpers
    show_final_instructions
    
    print_success "🎉 Setup completed successfully!"
    print_status "You can now start the system with: ./start_all.sh"
}

# Run main function with all arguments
main "$@"