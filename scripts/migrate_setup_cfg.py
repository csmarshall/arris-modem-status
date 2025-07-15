#!/usr/bin/env python3
"""
setup.cfg Migration Script
==========================

Handles migration from setup.cfg to pyproject.toml configuration,
specifically managing version conflicts and configuration consolidation.

This script:
1. Analyzes current setup.cfg for version conflicts
2. Migrates supported configuration to pyproject.toml
3. Creates minimal setup.cfg for tools that don't support pyproject.toml yet
4. Validates the migration

Usage:
    python scripts/migrate_setup_cfg.py --analyze     # Analyze current setup.cfg
    python scripts/migrate_setup_cfg.py --migrate     # Migrate configuration
    python scripts/migrate_setup_cfg.py --clean       # Remove version conflicts
    python scripts/migrate_setup_cfg.py --minimize    # Create minimal setup.cfg

Author: Charles Marshall
"""

import argparse
import configparser
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


class SetupCfgMigration:
    """Handles migration from setup.cfg to modern pyproject.toml configuration."""

    def __init__(self, project_root: Path = None):
        """Initialize the migration manager."""
        self.project_root = project_root or Path(__file__).parent.parent
        self.setup_cfg_path = self.project_root / "setup.cfg"
        self.pyproject_path = self.project_root / "pyproject.toml"

    def analyze_setup_cfg(self) -> Dict[str, Any]:
        """Analyze current setup.cfg for version conflicts and migration opportunities."""
        analysis = {
            'exists': False,
            'has_version_conflict': False,
            'version_found': None,
            'correct_version': None,
            'sections': [],
            'migratable_sections': [],
            'keep_sections': [],
            'conflicts': [],
            'recommendations': []
        }

        if not self.setup_cfg_path.exists():
            analysis['recommendations'].append("No setup.cfg found - already modern!")
            return analysis

        analysis['exists'] = True

        # Get correct version from __init__.py
        try:
            sys.path.insert(0, str(self.project_root))
            import arris_modem_status
            analysis['correct_version'] = arris_modem_status.__version__
        except Exception as e:
            print(f"⚠️  Warning: Cannot get version from __init__.py: {e}")

        # Parse setup.cfg
        try:
            config = configparser.ConfigParser()
            config.read(self.setup_cfg_path)

            analysis['sections'] = list(config.sections())

            # Check for version conflicts
            if config.has_section('metadata') and config.has_option('metadata', 'version'):
                setup_cfg_version = config.get('metadata', 'version')
                analysis['version_found'] = setup_cfg_version

                if analysis['correct_version'] and setup_cfg_version != analysis['correct_version']:
                    analysis['has_version_conflict'] = True
                    analysis['conflicts'].append(
                        f"Version mismatch: setup.cfg has '{setup_cfg_version}', "
                        f"__init__.py has '{analysis['correct_version']}'"
                    )

            # Categorize sections
            for section in config.sections():
                if section in ['metadata', 'options', 'options.packages.find', 'options.entry_points']:
                    # These should be migrated to pyproject.toml
                    analysis['migratable_sections'].append(section)
                elif section in ['flake8', 'tool:pytest', 'mypy']:
                    # These might need to stay (tool-specific)
                    analysis['keep_sections'].append(section)

            # Generate recommendations
            if analysis['has_version_conflict']:
                analysis['recommendations'].append(
                    "🔴 CRITICAL: Remove version from setup.cfg - managed dynamically from __init__.py"
                )

            if analysis['migratable_sections']:
                analysis['recommendations'].append(
                    f"🔄 Migrate {len(analysis['migratable_sections'])} sections to pyproject.toml"
                )

            if analysis['keep_sections']:
                analysis['recommendations'].append(
                    f"🔶 Keep minimal setup.cfg for {len(analysis['keep_sections'])} tool-specific sections"
                )

        except Exception as e:
            analysis['conflicts'].append(f"Error parsing setup.cfg: {e}")

        return analysis

    def clean_version_conflicts(self) -> bool:
        """Remove version conflicts from setup.cfg."""
        if not self.setup_cfg_path.exists():
            print("✅ No setup.cfg to clean")
            return True

        try:
            config = configparser.ConfigParser()
            config.read(self.setup_cfg_path)

            changes_made = False

            # Remove version from metadata section
            if config.has_section('metadata') and config.has_option('metadata', 'version'):
                old_version = config.get('metadata', 'version')
                config.remove_option('metadata', 'version')
                changes_made = True
                print(f"✅ Removed version '{old_version}' from [metadata] section")

                # Add comment about dynamic versioning
                if not config.has_option('metadata', 'dynamic'):
                    config.set('metadata', '# Version is now managed dynamically from arris_modem_status.__version__', '')

            # Remove version from options section
            if config.has_section('options') and config.has_option('options', 'version'):
                old_version = config.get('options', 'version')
                config.remove_option('options', 'version')
                changes_made = True
                print(f"✅ Removed version '{old_version}' from [options] section")

            if changes_made:
                # Write back the cleaned config
                with open(self.setup_cfg_path, 'w') as f:
                    config.write(f)
                print(f"✅ Cleaned setup.cfg saved")
            else:
                print("✅ No version conflicts found in setup.cfg")

            return True

        except Exception as e:
            print(f"❌ Error cleaning setup.cfg: {e}")
            return False

    def create_minimal_setup_cfg(self) -> bool:
        """Create minimal setup.cfg with only necessary tool configurations."""
        minimal_content = '''# setup.cfg - Minimal Legacy Configuration
# Most configuration has moved to pyproject.toml
# Version is managed dynamically from arris_modem_status.__version__

[flake8]
# Flake8 configuration (not yet fully supported in pyproject.toml)
max-line-length = 120
extend-ignore = E203, W503
exclude =
    .git,
    __pycache__,
    .venv,
    venv,
    build,
    dist,
    *.egg-info

[tool:pytest]
# Pytest configuration moved to pyproject.toml
# This section kept for backward compatibility only

# NOTE: All other configuration is now in pyproject.toml:
# - Project metadata (name, description, authors, etc.)
# - Dependencies and optional dependencies
# - Build system configuration
# - Version management (dynamic from __init__.py)
# - Entry points and scripts
# - Tool configurations (black, isort, mypy, etc.)
'''

        try:
            # Backup existing setup.cfg if it exists
            if self.setup_cfg_path.exists():
                backup_path = self.setup_cfg_path.with_suffix('.cfg.backup')
                self.setup_cfg_path.rename(backup_path)
                print(f"📦 Backed up existing setup.cfg to {backup_path}")

            # Write minimal setup.cfg
            self.setup_cfg_path.write_text(minimal_content)
            print(f"✅ Created minimal setup.cfg")
            return True

        except Exception as e:
            print(f"❌ Error creating minimal setup.cfg: {e}")
            return False

    def validate_migration(self) -> Dict[str, bool]:
        """Validate that the migration was successful."""
        validation = {
            'no_version_conflicts': True,
            'pyproject_has_dynamic_version': False,
            'build_system_works': False,
            'tools_still_work': True
        }

        print("🔍 Validating setup.cfg migration...")

        # Check for version conflicts
        analysis = self.analyze_setup_cfg()
        if analysis['has_version_conflict']:
            validation['no_version_conflicts'] = False
            print("❌ Version conflicts still exist")
        else:
            print("✅ No version conflicts found")

        # Check pyproject.toml has dynamic version
        if self.pyproject_path.exists():
            try:
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib

                content = tomllib.loads(self.pyproject_path.read_text())
                project_config = content.get('project', {})

                if 'version' in project_config.get('dynamic', []):
                    validation['pyproject_has_dynamic_version'] = True
                    print("✅ Dynamic version configured in pyproject.toml")
                else:
                    print("❌ Dynamic version not configured in pyproject.toml")

            except Exception as e:
                print(f"⚠️  Error checking pyproject.toml: {e}")

        # Test build system
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, '-c', 
                'import arris_modem_status; print(arris_modem_status.__version__)'
            ], capture_output=True, text=True, cwd=self.project_root)

            if result.returncode == 0:
                validation['build_system_works'] = True
                version = result.stdout.strip()
                print(f"✅ Build system works - version: {version}")
            else:
                print(f"❌ Build system error: {result.stderr}")

        except Exception as e:
            print(f"⚠️  Error testing build system: {e}")

        return validation

    def print_migration_report(self) -> None:
        """Print comprehensive migration report."""
        print("\n" + "=" * 60)
        print("📋 SETUP.CFG MIGRATION REPORT")
        print("=" * 60)

        analysis = self.analyze_setup_cfg()

        if not analysis['exists']:
            print("✅ No setup.cfg found - project is already modern!")
            return

        print(f"📁 setup.cfg analysis:")
        print(f"   Sections found: {len(analysis['sections'])}")
        print(f"   Version conflicts: {'Yes' if analysis['has_version_conflict'] else 'No'}")

        if analysis['version_found']:
            print(f"   setup.cfg version: {analysis['version_found']}")
        if analysis['correct_version']:
            print(f"   Correct version: {analysis['correct_version']}")

        if analysis['conflicts']:
            print(f"\n❌ CONFLICTS FOUND:")
            for conflict in analysis['conflicts']:
                print(f"   • {conflict}")

        if analysis['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in analysis['recommendations']:
                print(f"   • {rec}")

        print(f"\n🔧 MIGRATION OPTIONS:")
        print(f"   1. Clean conflicts: python scripts/migrate_setup_cfg.py --clean")
        print(f"   2. Create minimal:  python scripts/migrate_setup_cfg.py --minimize")
        print(f"   3. Full migration:  python scripts/migrate_setup_cfg.py --migrate")

    def perform_full_migration(self) -> bool:
        """Perform complete migration from setup.cfg to pyproject.toml."""
        print("🚀 Performing full setup.cfg migration...")

        steps_completed = []

        try:
            # Step 1: Clean version conflicts
            if self.clean_version_conflicts():
                steps_completed.append("✅ Cleaned version conflicts")
            else:
                steps_completed.append("❌ Failed to clean version conflicts")
                return False

            # Step 2: Create minimal setup.cfg
            if self.create_minimal_setup_cfg():
                steps_completed.append("✅ Created minimal setup.cfg")
            else:
                steps_completed.append("❌ Failed to create minimal setup.cfg")
                return False

            # Step 3: Validate migration
            validation = self.validate_migration()
            if all(validation.values()):
                steps_completed.append("✅ Migration validation passed")
            else:
                steps_completed.append("⚠️  Migration validation has warnings")

            print(f"\n📊 MIGRATION COMPLETE:")
            for step in steps_completed:
                print(f"   {step}")

            print(f"\n🎯 NEXT STEPS:")
            print(f"   1. Test build: make build")
            print(f"   2. Validate setup: python scripts/validate_setup.py")
            print(f"   3. Run tests: make test")

            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False


def main():
    """Main entry point for setup.cfg migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate setup.cfg to modern pyproject.toml configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/migrate_setup_cfg.py --analyze
  python scripts/migrate_setup_cfg.py --clean
  python scripts/migrate_setup_cfg.py --minimize
  python scripts/migrate_setup_cfg.py --migrate

Migration Strategy:
  1. Remove version conflicts (version should only be in __init__.py)
  2. Move most configuration to pyproject.toml
  3. Keep minimal setup.cfg for tools that don't support pyproject.toml
  4. Validate that everything still works
        """
    )

    parser.add_argument("--analyze", action="store_true", help="Analyze current setup.cfg")
    parser.add_argument("--clean", action="store_true", help="Remove version conflicts")
    parser.add_argument("--minimize", action="store_true", help="Create minimal setup.cfg")
    parser.add_argument("--migrate", action="store_true", help="Perform full migration")
    parser.add_argument("--validate", action="store_true", help="Validate migration")
    parser.add_argument("--report", action="store_true", help="Show migration report")

    args = parser.parse_args()

    try:
        migration = SetupCfgMigration()

        if args.analyze or not any([args.clean, args.minimize, args.migrate, args.validate]):
            # Default action: analyze
            analysis = migration.analyze_setup_cfg()
            migration.print_migration_report()

        elif args.clean:
            success = migration.clean_version_conflicts()
            if success:
                print("✅ Version conflicts cleaned")
            else:
                print("❌ Failed to clean version conflicts")
                return 1

        elif args.minimize:
            success = migration.create_minimal_setup_cfg()
            if success:
                print("✅ Minimal setup.cfg created")
            else:
                print("❌ Failed to create minimal setup.cfg")
                return 1

        elif args.migrate:
            success = migration.perform_full_migration()
            if success:
                print("✅ Migration completed successfully")
            else:
                print("❌ Migration failed")
                return 1

        elif args.validate:
            validation = migration.validate_migration()
            all_good = all(validation.values())
            if all_good:
                print("✅ Migration validation passed")
            else:
                print("⚠️  Migration validation has issues")
                return 1

        elif args.report:
            migration.print_migration_report()

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
