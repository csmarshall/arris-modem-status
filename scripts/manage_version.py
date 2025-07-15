#!/usr/bin/env python3
"""
Version Management Script
=========================

Central script for managing semantic versions across the arris-modem-status library.
This script ensures version consistency and follows PEP 440 versioning standards.

Usage:
    python scripts/manage_version.py --current               # Show current version
    python scripts/manage_version.py --bump patch            # Bump patch version (1.3.0 -> 1.3.1)
    python scripts/manage_version.py --bump minor            # Bump minor version (1.3.0 -> 1.4.0)
    python scripts/manage_version.py --bump major            # Bump major version (1.3.0 -> 2.0.0)
    python scripts/manage_version.py --set 1.3.1             # Set specific version
    python scripts/manage_version.py --validate              # Validate version consistency
    python scripts/manage_version.py --clean                 # Clean up whitespace issues

Author: Charles Marshall
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional


class VersionManager:
    """Manages semantic versioning for the arris-modem-status library."""

    def __init__(self, project_root: Path = None):
        """Initialize version manager with project root directory."""
        self.project_root = project_root or Path(__file__).parent.parent
        self.init_file = self.project_root / "arris_modem_status" / "__init__.py"

    def get_current_version(self) -> str:
        """Get the current version from __init__.py."""
        if not self.init_file.exists():
            raise FileNotFoundError(f"Cannot find {self.init_file}")

        content = self.init_file.read_text(encoding='utf-8')
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)

        if not match:
            raise ValueError("Version not found in __init__.py")

        return match.group(1)

    def set_version(self, new_version: str) -> None:
        """Set new version in __init__.py."""
        if not self._is_valid_version(new_version):
            raise ValueError(f"Invalid version format: {new_version}")

        content = self.init_file.read_text(encoding='utf-8')
        new_content = re.sub(
            r'(__version__\s*=\s*["\'])([^"\']+)(["\'])',
            rf'\g<1>{new_version}\g<3>',
            content
        )

        self.init_file.write_text(new_content, encoding='utf-8')
        print(f"✅ Updated version to {new_version} in {self.init_file}")

    def bump_version(self, bump_type: str) -> str:
        """Bump version according to semantic versioning rules."""
        current = self.get_current_version()
        major, minor, patch = self._parse_version(current)

        if bump_type == "major":
            new_version = f"{major + 1}.0.0"
        elif bump_type == "minor":
            new_version = f"{major}.{minor + 1}.0"
        elif bump_type == "patch":
            new_version = f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")

        self.set_version(new_version)
        return new_version

    def validate_consistency(self) -> List[str]:
        """Validate version consistency across all files."""
        issues = []
        current_version = self.get_current_version()

        # Check files that should reference the version
        files_to_check = [
            (self.project_root / "README.md", f"v{current_version}"),
            (self.project_root / "CHANGELOG.md", current_version),
        ]

        for file_path, expected_pattern in files_to_check:
            if file_path.exists():
                content = file_path.read_text(encoding='utf-8')
                if expected_pattern not in content:
                    issues.append(f"Version {expected_pattern} not found in {file_path}")

        return issues

    def clean_whitespace(self) -> List[str]:
        """Clean up whitespace issues in Python files."""
        cleaned_files = []
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            if self._clean_file_whitespace(file_path):
                cleaned_files.append(str(file_path))

        return cleaned_files

    def _clean_file_whitespace(self, file_path: Path) -> bool:
        """Clean whitespace issues in a single file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()

            cleaned_lines = []
            changes_made = False

            for line in lines:
                # Remove trailing whitespace
                cleaned_line = line.rstrip()
                if cleaned_line != line:
                    changes_made = True

                cleaned_lines.append(cleaned_line)

            if changes_made:
                # Join with newlines and ensure file ends with newline
                new_content = '\n'.join(cleaned_lines)
                if not new_content.endswith('\n'):
                    new_content += '\n'

                file_path.write_text(new_content, encoding='utf-8')
                return True

        except Exception as e:
            print(f"⚠️ Error cleaning {file_path}: {e}")

        return False

    def _is_valid_version(self, version: str) -> bool:
        """Check if version follows semantic versioning pattern."""
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))

    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse version string into major, minor, patch components."""
        if not self._is_valid_version(version):
            raise ValueError(f"Invalid version format: {version}")

        parts = version.split('.')
        return int(parts[0]), int(parts[1]), int(parts[2])

    def get_version_info(self) -> dict:
        """Get comprehensive version information."""
        current = self.get_current_version()
        major, minor, patch = self._parse_version(current)

        return {
            'current_version': current,
            'major': major,
            'minor': minor,
            'patch': patch,
            'next_patch': f"{major}.{minor}.{patch + 1}",
            'next_minor': f"{major}.{minor + 1}.0",
            'next_major': f"{major + 1}.0.0",
            'file_location': str(self.init_file)
        }


def main():
    """Main entry point for version management script."""
    parser = argparse.ArgumentParser(
        description="Manage semantic versions for arris-modem-status library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/manage_version.py --current
  python scripts/manage_version.py --bump patch
  python scripts/manage_version.py --set 1.3.1
  python scripts/manage_version.py --validate
  python scripts/manage_version.py --clean

Version Bumping Rules:
  patch: 1.3.0 -> 1.3.1 (bug fixes)
  minor: 1.3.0 -> 1.4.0 (new features, backward compatible)
  major: 1.3.0 -> 2.0.0 (breaking changes)
        """
    )

    parser.add_argument("--current", action="store_true", help="Show current version")
    parser.add_argument("--bump", choices=["major", "minor", "patch"], help="Bump version")
    parser.add_argument("--set", metavar="VERSION", help="Set specific version")
    parser.add_argument("--validate", action="store_true", help="Validate version consistency")
    parser.add_argument("--clean", action="store_true", help="Clean up whitespace issues")
    parser.add_argument("--info", action="store_true", help="Show detailed version information")

    args = parser.parse_args()

    try:
        manager = VersionManager()

        if args.current:
            version = manager.get_current_version()
            print(f"Current version: {version}")

        elif args.info:
            info = manager.get_version_info()
            print("📊 Version Information:")
            print(f"   Current: {info['current_version']}")
            print(f"   Components: {info['major']}.{info['minor']}.{info['patch']}")
            print(f"   Next patch: {info['next_patch']}")
            print(f"   Next minor: {info['next_minor']}")
            print(f"   Next major: {info['next_major']}")
            print(f"   Location: {info['file_location']}")

        elif args.bump:
            old_version = manager.get_current_version()
            new_version = manager.bump_version(args.bump)
            print(f"🚀 Bumped {args.bump} version: {old_version} -> {new_version}")

        elif args.set:
            old_version = manager.get_current_version()
            manager.set_version(args.set)
            print(f"🎯 Set version: {old_version} -> {args.set}")

        elif args.validate:
            print("🔍 Validating version consistency...")
            issues = manager.validate_consistency()
            if issues:
                print("❌ Version consistency issues found:")
                for issue in issues:
                    print(f"   • {issue}")
                return 1
            else:
                print("✅ Version consistency validated successfully")

        elif args.clean:
            print("🧹 Cleaning whitespace issues...")
            cleaned_files = manager.clean_whitespace()
            if cleaned_files:
                print(f"✅ Cleaned {len(cleaned_files)} files:")
                for file_path in cleaned_files:
                    print(f"   • {file_path}")
            else:
                print("✅ No whitespace issues found")

        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
