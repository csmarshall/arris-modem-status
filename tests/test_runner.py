"""Test Runner Script for Arris Modem Status Client."""

import argparse
import subprocess
import sys
from pathlib import Path


class ArrisTestRunner:
    """Test runner for categorized testing."""

    def __init__(self):
        """Initialize test runner."""
        self.project_root = Path(__file__).parent.parent
        self.test_categories = {
            "connection": "test_connection_handling.py",
            "scoping": "test_variable_scoping.py",
            "http": "test_http_compatibility.py",
            "all": "tests/",
        }

    def run_tests(self, category=None, verbose=False, coverage=False):
        """Run tests with specified options."""
        cmd = ["python", "-m", "pytest"]

        # Add test file path
        if category and category in self.test_categories:
            if category == "all":
                test_path = "tests/"
            else:
                test_path = f"tests/{self.test_categories[category]}"
            cmd.append(test_path)
        else:
            cmd.append("tests/")

        # Add options
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        if coverage:
            cmd.extend(["--cov=arris_modem_status", "--cov-report=term-missing"])

        cmd.extend(["--tb=short", "-ra"])

        print(f"Running: {' '.join(cmd)}")
        print("=" * 60)

        try:
            result = subprocess.run(cmd, cwd=self.project_root, check=False)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return False

    def list_categories(self):
        """List available test categories."""
        print("📋 Available test categories:")
        print("=" * 40)

        descriptions = {
            "connection": "Connection handling, quick checks, fast failure",
            "scoping": "Variable scoping fixes in error paths",
            "http": "HTTP compatibility and urllib3 parsing fixes",
            "all": "All test categories",
        }

        for category, _test_file in self.test_categories.items():
            desc = descriptions.get(category, "")
            print(f"  {category:12} - {desc}")


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Arris Modem Status Client Test Runner")

    parser.add_argument(
        "--category",
        "-c",
        choices=list(ArrisTestRunner().test_categories.keys()),
        help="Run specific test category",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--list-categories", action="store_true")

    args = parser.parse_args()

    runner = ArrisTestRunner()

    if args.list_categories:
        runner.list_categories()
        return 0

    try:
        success = runner.run_tests(
            category=args.category,
            verbose=args.verbose,
            coverage=args.coverage,
        )
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
