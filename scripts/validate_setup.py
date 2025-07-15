#!/usr/bin/env python3
"""
Setup Validation Script
=======================

Validates that the centralized version management and code quality setup
is working correctly for the arris-modem-status library.

Usage:
    python scripts/validate_setup.py

This script checks:
- Version consistency across files
- PEP 8 whitespace compliance
- Build system configuration
- Dependencies and imports

Author: Charles Marshall
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any


class SetupValidator:
    """Validates the complete project setup."""

    def __init__(self):
        """Initialize the setup validator."""
        self.project_root = Path(__file__).parent.parent
        self.results: Dict[str, Any] = {
            'version_management': {},
            'whitespace_compliance': {},
            'build_system': {},
            'dependencies': {},
            'imports': {}
        }
        self.all_checks_passed = True

    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating arris-modem-status setup...")
        print("=" * 60)

        # Check version management
        self._check_version_management()

        # Check whitespace compliance
        self._check_whitespace_compliance()

        # Check build system
        self._check_build_system()

        # Check dependencies
        self._check_dependencies()

        # Check imports
        self._check_imports()

        # Print summary
        self._print_summary()

        return self.all_checks_passed

    def _check_version_management(self) -> None:
        """Check version management setup."""
        print("\n📋 Checking version management...")

        try:
            # Check if we can import and get version
            sys.path.insert(0, str(self.project_root))
            import arris_modem_status
            version = arris_modem_status.__version__

            self.results['version_management']['version_accessible'] = True
            self.results['version_management']['current_version'] = version
            print(f"   ✅ Version accessible: {version}")

            # Check version format
            parts = version.split('.')
            if len(parts) == 3 and all(part.isdigit() for part in parts):
                self.results['version_management']['valid_format'] = True
                print(f"   ✅ Valid semantic version format")
            else:
                self.results['version_management']['valid_format'] = False
                print(f"   ❌ Invalid version format: {version}")
                self.all_checks_passed = False

            # Check if version script works
            try:
                result = subprocess.run([
                    sys.executable, "scripts/manage_version.py", "--current"
                ], cwd=self.project_root, capture_output=True, text=True)

                if result.returncode == 0:
                    script_version = result.stdout.strip().split(": ")[-1]
                    if script_version == version:
                        self.results['version_management']['script_working'] = True
                        print(f"   ✅ Version management script working")
                    else:
                        self.results['version_management']['script_working'] = False
                        print(f"   ❌ Version mismatch: script={script_version}, import={version}")
                        self.all_checks_passed = False
                else:
                    self.results['version_management']['script_working'] = False
                    print(f"   ❌ Version script failed: {result.stderr}")
                    self.all_checks_passed = False

            except Exception as e:
                self.results['version_management']['script_working'] = False
                print(f"   ❌ Version script error: {e}")
                self.all_checks_passed = False

        except Exception as e:
            self.results['version_management']['version_accessible'] = False
            print(f"   ❌ Cannot import version: {e}")
            self.all_checks_passed = False

    def _check_whitespace_compliance(self) -> None:
        """Check PEP 8 whitespace compliance."""
        print("\n🧹 Checking whitespace compliance...")

        python_files = list(self.project_root.rglob("*.py"))
        issues_found = []

        for file_path in python_files:
            # Skip virtual environments and build directories
            if any(part in str(file_path) for part in ['.venv', 'venv', 'build', 'dist', '.git']):
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                lines = content.splitlines()

                for line_num, line in enumerate(lines, 1):
                    # Check for trailing whitespace
                    if line.rstrip() != line:
                        issues_found.append(f"{file_path}:{line_num} - trailing whitespace")

                    # Check for spaces on blank lines
                    if line.strip() == "" and line != "":
                        issues_found.append(f"{file_path}:{line_num} - spaces on blank line")

            except Exception as e:
                issues_found.append(f"{file_path} - read error: {e}")

        if issues_found:
            self.results['whitespace_compliance']['compliant'] = False
            self.results['whitespace_compliance']['issues'] = issues_found[:10]  # Limit output
            print(f"   ❌ Found {len(issues_found)} whitespace issues")
            if len(issues_found) <= 5:
                for issue in issues_found:
                    print(f"      • {issue}")
            else:
                for issue in issues_found[:3]:
                    print(f"      • {issue}")
                print(f"      ... and {len(issues_found) - 3} more")
            print("   💡 Run: make clean-whitespace")
            self.all_checks_passed = False
        else:
            self.results['whitespace_compliance']['compliant'] = True
            print("   ✅ All Python files are whitespace compliant")

    def _check_build_system(self) -> None:
        """Check build system configuration."""
        print("\n🏗️  Checking build system...")

        # Check pyproject.toml
        pyproject_file = self.project_root / "pyproject.toml"
        if pyproject_file.exists():
            self.results['build_system']['pyproject_exists'] = True
            print("   ✅ pyproject.toml exists")

            try:
                import tomllib
                content = tomllib.loads(pyproject_file.read_text())

                # Check for dynamic version
                if content.get('project', {}).get('dynamic') == ['version']:
                    self.results['build_system']['dynamic_version'] = True
                    print("   ✅ Dynamic version configuration found")
                else:
                    self.results['build_system']['dynamic_version'] = False
                    print("   ❌ Dynamic version not configured")
                    self.all_checks_passed = False

                # Check setuptools configuration
                setuptools_config = content.get('tool', {}).get('setuptools', {}).get('dynamic', {})
                if 'version' in setuptools_config:
                    self.results['build_system']['setuptools_dynamic'] = True
                    print("   ✅ Setuptools dynamic version configured")
                else:
                    self.results['build_system']['setuptools_dynamic'] = False
                    print("   ❌ Setuptools dynamic version not configured")
                    self.all_checks_passed = False

            except Exception as e:
                self.results['build_system']['pyproject_valid'] = False
                print(f"   ❌ pyproject.toml parsing error: {e}")
                self.all_checks_passed = False

        else:
            self.results['build_system']['pyproject_exists'] = False
            print("   ❌ pyproject.toml missing")
            self.all_checks_passed = False

    def _check_dependencies(self) -> None:
        """Check dependency management."""
        print("\n📦 Checking dependencies...")

        try:
            # Try to import main dependencies
            import requests
            import urllib3
            self.results['dependencies']['core_deps'] = True
            print("   ✅ Core dependencies importable")

            # Check versions
            print(f"   📊 requests: {requests.__version__}")
            print(f"   📊 urllib3: {urllib3.__version__}")

        except ImportError as e:
            self.results['dependencies']['core_deps'] = False
            print(f"   ❌ Core dependency missing: {e}")
            self.all_checks_passed = False

    def _check_imports(self) -> None:
        """Check that the package imports correctly."""
        print("\n🐍 Checking package imports...")

        try:
            sys.path.insert(0, str(self.project_root))

            # Test main imports
            import arris_modem_status
            from arris_modem_status import ArrisStatusClient, ChannelInfo

            self.results['imports']['main_package'] = True
            print("   ✅ Main package imports successfully")

            # Test version utilities
            try:
                from arris_modem_status._version import get_version, get_version_info
                version = get_version()
                version_info = get_version_info()
                self.results['imports']['version_utils'] = True
                print(f"   ✅ Version utilities working: {version}")
                print(f"   📊 Version info: {version_info}")
            except Exception as e:
                self.results['imports']['version_utils'] = False
                print(f"   ❌ Version utilities error: {e}")
                self.all_checks_passed = False

        except Exception as e:
            self.results['imports']['main_package'] = False
            print(f"   ❌ Package import error: {e}")
            self.all_checks_passed = False

    def _print_summary(self) -> None:
        """Print validation summary."""
        print("\n" + "=" * 60)
        if self.all_checks_passed:
            print("🎉 ALL VALIDATION CHECKS PASSED!")
            print("✅ Your setup is ready for development and production")
        else:
            print("⚠️  SOME VALIDATION CHECKS FAILED")
            print("❌ Please fix the issues above before proceeding")

        print("\n📊 Quick Commands:")
        print("   make version          # Show current version")
        print("   make version-info     # Show detailed version info")
        print("   make clean-whitespace # Fix whitespace issues")
        print("   make format           # Format code")
        print("   make lint             # Run linting")
        print("   make test             # Run tests")


def main():
    """Main entry point."""
    try:
        # Check if tomllib is available (Python 3.11+)
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
                import sys
                sys.modules['tomllib'] = tomllib
            except ImportError:
                print("⚠️  Warning: tomllib/tomli not available. Install with: pip install tomli")

        validator = SetupValidator()
        success = validator.run_all_checks()

        return 0 if success else 1

    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
