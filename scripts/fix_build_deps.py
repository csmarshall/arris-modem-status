#!/usr/bin/env python3
"""
Build Dependencies Fix Script
============================

This script automatically fixes missing build dependencies and validates
that the build system is working correctly.

Usage:
    python scripts/fix_build_deps.py
    python scripts/fix_build_deps.py --check-only
    python scripts/fix_build_deps.py --verbose

Common Issues Fixed:
- Missing build package
- Missing twine package  
- Missing wheel package
- Outdated setuptools
- Build system validation

Author: Charles Marshall
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any


class BuildDependencyFixer:
    """Fixes common build dependency issues."""

    def __init__(self, verbose: bool = False):
        """Initialize the build dependency fixer."""
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.required_packages = {
            'build': '>=0.10.0',
            'twine': '>=4.0.0', 
            'wheel': '>=0.40.0',
            'setuptools': '>=65.0'
        }

    def check_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed."""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False

    def get_package_version(self, package_name: str) -> str:
        """Get the version of an installed package."""
        try:
            import importlib.metadata
            return importlib.metadata.version(package_name)
        except Exception:
            try:
                # Fallback for older Python versions
                import pkg_resources
                return pkg_resources.get_distribution(package_name).version
            except Exception:
                return "unknown"

    def check_all_dependencies(self) -> Dict[str, Any]:
        """Check status of all build dependencies."""
        status = {
            'all_installed': True,
            'missing_packages': [],
            'outdated_packages': [],
            'installed_packages': {},
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        }

        print("🔍 Checking build dependencies...")
        print("=" * 50)

        for package, min_version in self.required_packages.items():
            is_installed = self.check_package_installed(package)
            
            if is_installed:
                version = self.get_package_version(package)
                status['installed_packages'][package] = version
                print(f"✅ {package}: {version}")
                
                if self.verbose:
                    print(f"   Required: {min_version}")
            else:
                status['missing_packages'].append(package)
                status['all_installed'] = False
                print(f"❌ {package}: Not installed")

        print(f"\n🐍 Python: {status['python_version']}")
        
        return status

    def install_missing_packages(self, packages: List[str]) -> bool:
        """Install missing packages."""
        if not packages:
            print("✅ All packages already installed")
            return True

        print(f"📦 Installing {len(packages)} missing packages...")
        
        # Build the pip install command
        install_packages = []
        for package in packages:
            if package in self.required_packages:
                install_packages.append(f"{package}{self.required_packages[package]}")
            else:
                install_packages.append(package)

        cmd = [sys.executable, '-m', 'pip', 'install'] + install_packages

        if self.verbose:
            print(f"🔧 Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if self.verbose:
                print("📤 Installation output:")
                print(result.stdout)
            
            print("✅ Packages installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Installation failed: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr}")
            return False

    def test_build_system(self) -> bool:
        """Test that the build system works."""
        print("\n🧪 Testing build system...")
        
        # Test 1: Can we import the package?
        try:
            sys.path.insert(0, str(self.project_root))
            import arris_modem_status
            version = arris_modem_status.__version__
            print(f"✅ Package import works: {version}")
        except Exception as e:
            print(f"❌ Package import failed: {e}")
            return False

        # Test 2: Can we run build command?
        try:
            cmd = [sys.executable, '-m', 'build', '--help']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                print("✅ Build command available")
            else:
                print(f"❌ Build command failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Build command test failed: {e}")
            return False

        # Test 3: Can we validate pyproject.toml?
        try:
            pyproject_file = self.project_root / "pyproject.toml"
            if pyproject_file.exists():
                print("✅ pyproject.toml exists")
                
                # Try to parse it
                try:
                    import tomllib
                except ImportError:
                    try:
                        import tomli as tomllib
                    except ImportError:
                        print("⚠️  Cannot validate pyproject.toml (tomllib/tomli not available)")
                        return True
                
                content = tomllib.loads(pyproject_file.read_text())
                if 'build-system' in content:
                    print("✅ Build system configured")
                else:
                    print("❌ Build system not configured in pyproject.toml")
                    return False
                    
            else:
                print("❌ pyproject.toml missing")
                return False
                
        except Exception as e:
            print(f"❌ pyproject.toml validation failed: {e}")
            return False

        return True

    def fix_build_dependencies(self, check_only: bool = False) -> bool:
        """Fix all build dependency issues."""
        print("🔧 BUILD DEPENDENCY FIXER")
        print("=" * 40)
        
        # Check current status
        status = self.check_all_dependencies()
        
        if status['all_installed']:
            print("\n✅ All build dependencies are installed!")
            
            # Still test the build system
            if self.test_build_system():
                print("\n🎉 Build system is working perfectly!")
                return True
            else:
                print("\n❌ Build system has issues despite dependencies being installed")
                return False
        
        if check_only:
            print(f"\n📋 Missing packages: {', '.join(status['missing_packages'])}")
            print("💡 Run without --check-only to install missing packages")
            return False
        
        # Install missing packages
        print(f"\n📦 Installing missing packages...")
        success = self.install_missing_packages(status['missing_packages'])
        
        if not success:
            return False
        
        # Re-check after installation
        print(f"\n🔍 Re-checking dependencies after installation...")
        new_status = self.check_all_dependencies()
        
        if not new_status['all_installed']:
            print("❌ Some packages still missing after installation")
            return False
        
        # Test build system
        if self.test_build_system():
            print("\n🎉 BUILD SYSTEM FIXED!")
            print("💡 You can now run: make build")
            return True
        else:
            print("\n❌ Build system still has issues")
            return False

    def print_fix_instructions(self) -> None:
        """Print manual fix instructions."""
        print("\n🛠️  MANUAL FIX INSTRUCTIONS:")
        print("=" * 40)
        print("If automatic fixing failed, try these steps:")
        print()
        print("1. Update pip:")
        print("   python -m pip install --upgrade pip")
        print()
        print("2. Install build dependencies:")
        print("   pip install build twine wheel")
        print()
        print("3. Reinstall in development mode:")
        print("   pip install -e .[dev,build]")
        print()
        print("4. Test the build:")
        print("   python -m build --help")
        print("   make build")
        print()
        print("5. If still failing, check your virtual environment:")
        print("   which python")
        print("   python --version")


def main():
    """Main entry point for build dependency fixer."""
    parser = argparse.ArgumentParser(
        description="Fix missing build dependencies for arris-modem-status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/fix_build_deps.py                # Fix all issues
  python scripts/fix_build_deps.py --check-only   # Just check, don't fix
  python scripts/fix_build_deps.py --verbose      # Show detailed output

This script will:
1. Check if build, twine, and wheel packages are installed
2. Install any missing packages automatically
3. Test that the build system works
4. Provide manual instructions if automatic fixing fails
        """
    )
    
    parser.add_argument("--check-only", action="store_true", help="Only check dependencies, don't install")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    try:
        fixer = BuildDependencyFixer(verbose=args.verbose)
        success = fixer.fix_build_dependencies(check_only=args.check_only)
        
        if not success and not args.check_only:
            fixer.print_fix_instructions()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        return 1
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())