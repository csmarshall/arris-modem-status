#!/usr/bin/env python3
"""
Legacy File Cleanup Script
==========================

This script helps identify and optionally remove legacy Python packaging files
that are no longer needed with modern pyproject.toml-based packaging.

Usage:
    python scripts/cleanup_legacy.py --check      # Check what can be removed
    python scripts/cleanup_legacy.py --remove     # Actually remove legacy files
    python scripts/cleanup_legacy.py --backup     # Backup before removing

Author: Charles Marshall
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Any


class LegacyFileCleanup:
    """Manages cleanup of legacy Python packaging files."""

    def __init__(self, project_root: Path = None):
        """Initialize the cleanup manager."""
        self.project_root = project_root or Path(__file__).parent.parent
        self.legacy_files = {
            'setup.py': {
                'reason': 'Replaced by pyproject.toml',
                'safe_to_remove': True,
                'backup_recommended': True
            },
            'setup.cfg': {
                'reason': 'Mostly replaced by pyproject.toml (keep minimal version for flake8)',
                'safe_to_remove': False,  # We keep a minimal version
                'backup_recommended': True
            },
            'MANIFEST.in': {
                'reason': 'Can be replaced by pyproject.toml package discovery',
                'safe_to_remove': True,
                'backup_recommended': True
            },
            'requirements.txt': {
                'reason': 'Dependencies now in pyproject.toml',
                'safe_to_remove': False,  # Might be used for development
                'backup_recommended': True
            },
            'requirements-dev.txt': {
                'reason': 'Dev dependencies now in pyproject.toml [project.optional-dependencies]',
                'safe_to_remove': True,
                'backup_recommended': True
            }
        }

    def check_legacy_files(self) -> Dict[str, Any]:
        """Check which legacy files exist and their removal status."""
        results = {
            'found_files': [],
            'can_remove_safely': [],
            'should_keep': [],
            'recommendations': []
        }

        print("🔍 Checking for legacy packaging files...")
        print("=" * 60)

        for filename, info in self.legacy_files.items():
            file_path = self.project_root / filename

            if file_path.exists():
                file_info = {
                    'filename': filename,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'reason': info['reason'],
                    'safe_to_remove': info['safe_to_remove'],
                    'backup_recommended': info['backup_recommended']
                }

                results['found_files'].append(file_info)

                if info['safe_to_remove']:
                    results['can_remove_safely'].append(filename)
                    print(f"✅ {filename} - Can be safely removed")
                    print(f"   📋 Reason: {info['reason']}")
                else:
                    results['should_keep'].append(filename)
                    print(f"🔶 {filename} - Should keep (modified)")
                    print(f"   📋 Reason: {info['reason']}")

                print(f"   📊 Size: {file_path.stat().st_size} bytes")
                print()

        # Generate recommendations
        if results['can_remove_safely']:
            results['recommendations'].append(
                f"Remove {len(results['can_remove_safely'])} legacy files: {', '.join(results['can_remove_safely'])}"
            )

        if results['should_keep']:
            results['recommendations'].append(
                f"Keep {len(results['should_keep'])} files (but verify): {', '.join(results['should_keep'])}"
            )

        return results

    def backup_files(self, files_to_backup: List[str]) -> str:
        """Create backup of files before removal."""
        backup_dir = self.project_root / "backup_legacy_files"
        backup_dir.mkdir(exist_ok=True)

        print(f"📦 Creating backup in {backup_dir}...")

        for filename in files_to_backup:
            file_path = self.project_root / filename
            if file_path.exists():
                backup_path = backup_dir / filename
                shutil.copy2(file_path, backup_path)
                print(f"   ✅ Backed up: {filename}")

        return str(backup_dir)

    def remove_legacy_files(self, dry_run: bool = True) -> List[str]:
        """Remove legacy files (with dry run option)."""
        removed_files = []

        if dry_run:
            print("🧪 DRY RUN - No files will actually be removed")
        else:
            print("🗑️  REMOVING LEGACY FILES")
        print("=" * 60)

        for filename, info in self.legacy_files.items():
            file_path = self.project_root / filename

            if file_path.exists() and info['safe_to_remove']:
                if dry_run:
                    print(f"🔸 Would remove: {filename}")
                    print(f"   📋 Reason: {info['reason']}")
                else:
                    file_path.unlink()
                    removed_files.append(filename)
                    print(f"✅ Removed: {filename}")
                    print(f"   📋 Reason: {info['reason']}")
                print()

        return removed_files

    def validate_modern_setup(self) -> Dict[str, bool]:
        """Validate that modern packaging setup is complete."""
        print("✅ Validating modern packaging setup...")

        validations = {
            'pyproject_toml_exists': (self.project_root / "pyproject.toml").exists(),
            'dynamic_version_configured': False,
            'build_system_configured': False,
            'dependencies_configured': False
        }

        pyproject_file = self.project_root / "pyproject.toml"
        if pyproject_file.exists():
            try:
                # Try to import tomllib (Python 3.11+) or tomli
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib

                content = tomllib.loads(pyproject_file.read_text())

                # Check dynamic version
                project_config = content.get('project', {})
                if 'version' in project_config.get('dynamic', []):
                    validations['dynamic_version_configured'] = True

                # Check build system
                build_system = content.get('build-system', {})
                if build_system.get('build-backend') and build_system.get('requires'):
                    validations['build_system_configured'] = True

                # Check dependencies
                if project_config.get('dependencies'):
                    validations['dependencies_configured'] = True

            except Exception as e:
                print(f"⚠️  Error parsing pyproject.toml: {e}")

        # Print validation results
        for check, passed in validations.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check.replace('_', ' ').title()}")

        return validations

    def generate_migration_report(self) -> str:
        """Generate a comprehensive migration report."""
        report = []
        report.append("# Legacy to Modern Packaging Migration Report")
        report.append("=" * 50)
        report.append("")

        # Check legacy files
        legacy_results = self.check_legacy_files()

        if legacy_results['found_files']:
            report.append("## Legacy Files Found")
            for file_info in legacy_results['found_files']:
                status = "✅ Can Remove" if file_info['safe_to_remove'] else "🔶 Keep Modified"
                report.append(f"- **{file_info['filename']}** - {status}")
                report.append(f"  - Reason: {file_info['reason']}")
                report.append(f"  - Size: {file_info['size']} bytes")
                report.append("")
        else:
            report.append("## No Legacy Files Found")
            report.append("✅ Your project is already using modern packaging!")
            report.append("")

        # Validate modern setup
        validations = self.validate_modern_setup()
        report.append("## Modern Packaging Validation")

        all_good = all(validations.values())
        if all_good:
            report.append("✅ **All modern packaging requirements met!**")
        else:
            report.append("⚠️  **Some modern packaging requirements missing:**")
            for check, passed in validations.items():
                status = "✅" if passed else "❌"
                report.append(f"- {status} {check.replace('_', ' ').title()}")

        report.append("")

        # Recommendations
        if legacy_results['recommendations']:
            report.append("## Recommendations")
            for rec in legacy_results['recommendations']:
                report.append(f"- {rec}")
            report.append("")

        # Next steps
        report.append("## Next Steps")
        if legacy_results['can_remove_safely']:
            report.append("1. **Backup legacy files**: `python scripts/cleanup_legacy.py --backup`")
            report.append("2. **Remove legacy files**: `python scripts/cleanup_legacy.py --remove`")
            report.append("3. **Test build system**: `make build`")
            report.append("4. **Validate setup**: `python scripts/validate_setup.py`")
        else:
            report.append("1. **Your setup is already modern!**")
            report.append("2. **Validate everything**: `python scripts/validate_setup.py`")
            report.append("3. **Test build system**: `make build`")

        return "\n".join(report)


def main():
    """Main entry point for legacy cleanup script."""
    parser = argparse.ArgumentParser(
        description="Clean up legacy Python packaging files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/cleanup_legacy.py --check
  python scripts/cleanup_legacy.py --backup
  python scripts/cleanup_legacy.py --remove
  python scripts/cleanup_legacy.py --report > migration_report.md

Modern packaging uses pyproject.toml instead of setup.py and setup.cfg.
This script helps identify and remove legacy files safely.
        """
    )

    parser.add_argument("--check", action="store_true", help="Check which legacy files exist")
    parser.add_argument("--backup", action="store_true", help="Backup legacy files before removal")
    parser.add_argument("--remove", action="store_true", help="Remove legacy files (use with --backup)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without doing it")
    parser.add_argument("--report", action="store_true", help="Generate migration report")
    parser.add_argument("--validate", action="store_true", help="Validate modern packaging setup")

    args = parser.parse_args()

    try:
        cleanup = LegacyFileCleanup()

        if args.check or not any([args.backup, args.remove, args.report, args.validate]):
            # Default action: check
            results = cleanup.check_legacy_files()

            if results['found_files']:
                print(f"\n📊 SUMMARY:")
                print(f"   Found {len(results['found_files'])} legacy files")
                print(f"   Can safely remove: {len(results['can_remove_safely'])}")
                print(f"   Should keep: {len(results['should_keep'])}")

                if results['can_remove_safely']:
                    print(f"\n💡 Next steps:")
                    print(f"   python scripts/cleanup_legacy.py --backup")
                    print(f"   python scripts/cleanup_legacy.py --remove")
            else:
                print("✅ No legacy files found - your setup is already modern!")

        elif args.validate:
            cleanup.validate_modern_setup()

        elif args.report:
            report = cleanup.generate_migration_report()
            print(report)

        elif args.backup:
            results = cleanup.check_legacy_files()
            if results['can_remove_safely']:
                backup_dir = cleanup.backup_files(results['can_remove_safely'])
                print(f"✅ Backup created in: {backup_dir}")
            else:
                print("ℹ️  No files need backing up")

        elif args.remove:
            if args.dry_run:
                removed = cleanup.remove_legacy_files(dry_run=True)
            else:
                # Ask for confirmation
                print("⚠️  This will permanently remove legacy files!")
                response = input("Are you sure? (y/N): ")
                if response.lower() == 'y':
                    removed = cleanup.remove_legacy_files(dry_run=False)
                    print(f"✅ Removed {len(removed)} legacy files")
                    print("💡 Run 'make build' to test the modern build system")
                else:
                    print("🚫 Operation cancelled")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
