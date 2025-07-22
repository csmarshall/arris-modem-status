#!/bin/bash
# Arris Modem Status - Custom Environment Setup
# ============================================
# Complete setup script for isolated development environment

set -e  # Exit on any error

echo "🚀 ARRIS MODEM STATUS - CUSTOM ENVIRONMENT SETUP"
echo "================================================"

PROJECT_NAME="arris-modem-status"
ENV_NAME="arris_modem_venv"
PYTHON_VERSION="3.9"  # Minimum supported version

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

# Check if we're in the project directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

print_status "Setting up custom Python environment for Arris Modem Status"

# Step 1: Check Python version
print_status "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    print_error "Python not found. Please install Python 3.8+ first."
    exit 1
fi

CURRENT_PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
print_status "Found Python version: $CURRENT_PYTHON_VERSION"

# Step 2: Remove existing environment if it exists
if [ -d "$ENV_NAME" ]; then
    print_warning "Existing environment '$ENV_NAME' found. Removing..."
    rm -rf "$ENV_NAME"
fi

# Step 3: Create virtual environment
print_status "Creating virtual environment: $ENV_NAME"
$PYTHON_CMD -m venv "$ENV_NAME"

# Step 4: Determine activation script path (cross-platform)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash, MSYS2, etc.)
    ACTIVATE_SCRIPT="$ENV_NAME/Scripts/activate"
    PYTHON_PATH="$ENV_NAME/Scripts/python"
    PIP_PATH="$ENV_NAME/Scripts/pip"
else
    # macOS/Linux
    ACTIVATE_SCRIPT="$ENV_NAME/bin/activate"
    PYTHON_PATH="$ENV_NAME/bin/python"
    PIP_PATH="$ENV_NAME/bin/pip"
fi

# Step 5: Activate environment and install dependencies
print_status "Activating environment and installing dependencies..."
source "$ACTIVATE_SCRIPT"

# Upgrade pip first
print_status "Upgrading pip..."
"$PIP_PATH" install --upgrade pip setuptools wheel

# Install the project in development mode with all dependencies
print_status "Installing arris-modem-status with development dependencies..."
"$PIP_PATH" install -e .[dev]

# Step 6: Install Playwright browsers
print_status "Installing Playwright browsers..."
"$PYTHON_PATH" -m playwright install chromium

# Step 7: Generate requirements files
print_status "Generating requirements files..."
"$PIP_PATH" freeze > requirements-dev.txt

# Create minimal requirements for production
cat > requirements.txt << EOF
# Core dependencies for arris-modem-status
aiohttp>=3.8.0
urllib3>=1.26.0
EOF

# Step 8: Create activation helper scripts
print_status "Creating activation helper scripts..."

# Create activation script for easy access
cat > activate_env.sh << 'EOF'
#!/bin/bash
# Activate the Arris Modem Status development environment
source arris_modem_venv/bin/activate
echo "🚀 Arris Modem Status development environment activated!"
echo "📦 Available commands:"
echo "   python -m arris_modem_status.cli --password 'YOUR_PASSWORD'"
echo "   python working_capture_test.py --password 'YOUR_PASSWORD'"
echo "   python arris_playwright_monitor.py --password 'YOUR_PASSWORD'"
echo ""
echo "💡 To deactivate: deactivate"
EOF

# Windows version
cat > activate_env.bat << 'EOF'
@echo off
call arris_modem_venv\Scripts\activate.bat
echo 🚀 Arris Modem Status development environment activated!
echo 📦 Available commands:
echo    python -m arris_modem_status.cli --password "YOUR_PASSWORD"
echo    python working_capture_test.py --password "YOUR_PASSWORD"
echo    python arris_playwright_monitor.py --password "YOUR_PASSWORD"
echo.
echo 💡 To deactivate: deactivate
EOF

chmod +x activate_env.sh

# Step 9: Create test script
cat > test_installation.py << 'EOF'
#!/usr/bin/env python3
"""
Test script to verify the Arris Modem Status installation
"""
import sys
import importlib.util

def test_import(module_name, description):
    """Test if a module can be imported"""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"❌ {description}: Module '{module_name}' not found")
            return False

        module = importlib.import_module(module_name)
        print(f"✅ {description}: OK")
        return True
    except ImportError as e:
        print(f"❌ {description}: Import error - {e}")
        return False

def main():
    print("🧪 TESTING ARRIS MODEM STATUS INSTALLATION")
    print("=" * 50)

    success_count = 0
    total_tests = 0

    # Core dependencies
    tests = [
        ("aiohttp", "Async HTTP client"),
        ("urllib3", "HTTP library"),
        ("arris_modem_status", "Main Arris library"),
        ("arris_modem_status.cli", "CLI module"),
        ("arris_modem_status.arris_status_client", "Status client"),
    ]

    # Optional dependencies
    optional_tests = [
        ("playwright", "Playwright (for monitoring)"),
        ("selenium", "Selenium (for debugging)"),
        ("bs4", "BeautifulSoup (for parsing)"),
    ]

    print("📦 Core Dependencies:")
    for module, desc in tests:
        if test_import(module, desc):
            success_count += 1
        total_tests += 1

    print(f"\n📦 Optional Dependencies:")
    for module, desc in optional_tests:
        if test_import(module, desc):
            success_count += 1
        total_tests += 1

    print(f"\n📊 RESULTS: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("🎉 All tests passed! Installation is complete.")
        print("\n🚀 Next steps:")
        print("   1. Run: python working_capture_test.py --password 'YOUR_PASSWORD'")
        print("   2. Run: python arris_playwright_monitor.py --password 'YOUR_PASSWORD'")
        print("   3. Test CLI: python -m arris_modem_status.cli --password 'YOUR_PASSWORD'")
        return True
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

# Step 10: Create project info script
cat > project_info.py << 'EOF'
#!/usr/bin/env python3
"""Show current project environment information"""
import sys
import os
import platform
from pathlib import Path

def main():
    print("📊 ARRIS MODEM STATUS - ENVIRONMENT INFO")
    print("=" * 50)

    # Python info
    print(f"🐍 Python Version: {sys.version}")
    print(f"📂 Python Executable: {sys.executable}")
    print(f"🏠 Virtual Environment: {os.environ.get('VIRTUAL_ENV', 'Not detected')}")

    # System info
    print(f"💻 Platform: {platform.platform()}")
    print(f"🏛️  Architecture: {platform.architecture()[0]}")

    # Project info
    cwd = Path.cwd()
    print(f"📁 Current Directory: {cwd}")
    print(f"📦 Project Files:")

    important_files = [
        "pyproject.toml",
        "README.md",
        "arris_modem_status/",
        "working_capture_test.py",
        "arris_playwright_monitor.py",
        "requirements.txt",
        "requirements-dev.txt"
    ]

    for file in important_files:
        path = cwd / file
        if path.exists():
            if path.is_dir():
                print(f"   ✅ {file} (directory)")
            else:
                size = path.stat().st_size
                print(f"   ✅ {file} ({size} bytes)")
        else:
            print(f"   ❌ {file} (missing)")

    # Virtual environment check
    if 'VIRTUAL_ENV' in os.environ:
        venv_path = Path(os.environ['VIRTUAL_ENV'])
        print(f"\n🌐 Virtual Environment Details:")
        print(f"   Path: {venv_path}")
        print(f"   Python: {venv_path / 'bin' / 'python' if os.name != 'nt' else venv_path / 'Scripts' / 'python.exe'}")

    # Import test
    try:
        import arris_modem_status
        print(f"\n✅ Arris Modem Status library is importable!")
    except ImportError as e:
        print(f"\n❌ Cannot import arris_modem_status: {e}")

if __name__ == "__main__":
    main()
EOF

print_success "Environment setup complete!"
print_status "Environment location: $(pwd)/$ENV_NAME"

# Step 11: Test the installation
print_status "Testing installation..."
"$PYTHON_PATH" test_installation.py

print_success "🎉 SETUP COMPLETE!"
print_status "To activate your environment:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "   Windows: activate_env.bat"
else
    echo "   macOS/Linux: source activate_env.sh"
fi

print_status "Or manually:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "   Windows: $ENV_NAME\\Scripts\\activate.bat"
else
    echo "   macOS/Linux: source $ENV_NAME/bin/activate"
fi

print_status "To test your setup:"
echo "   python working_capture_test.py --password 'YOUR_PASSWORD'"
echo "   python arris_playwright_monitor.py --password 'YOUR_PASSWORD'"

deactivate 2>/dev/null || true  # Deactivate if we were in a venv
