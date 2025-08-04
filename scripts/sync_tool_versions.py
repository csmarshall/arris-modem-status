#!/usr/bin/env python3
"""
Synchronize Tool Versions Across Configurations
==============================================

This script ensures all tool versions are synchronized across:
- pyproject.toml
- .pre-commit-config.yaml
- GitHub Actions workflows
- Makefile (if pinned versions)
"""

import re
from pathlib import Path
import tomllib
import tomli_w
import yaml


class ToolVersionSync:
    """Synchronize tool versions across all configuration files."""

    # Single source of truth for tool versions
    TOOL_VERSIONS = {
        "ruff": "0.8.4",
        "black": "25.1.0",
        "mypy": "1.14.1",
        "pytest": "8.3.5",
        "pytest-cov": "6.0.0",
        "coverage": "7.6.10",
        "bandit": "1.8.0",
        "pip-audit": "2.8.0",
        "interrogate": "1.7.0",
        "vulture": "2.14",
        "pre-commit": "4.0.2",
    }

    def __init__(self, project_root: Path = Path.cwd()):
        self.project_root = project_root
        self.updates_made = []

    def sync_all(self):
        """Synchronize all configuration files."""
        print("🔄 Synchronizing tool versions...")
        print("=" * 50)

        self._sync_pyproject_toml()
        self._sync_precommit_config()
        self._sync_github_actions()

        if self.updates_made:
            print("\n✅ Synchronization complete!")
            print("\nUpdates made:")
            for update in self.updates_made:
                print(f"  • {update}")
        else:
            print("\n✅ All tool versions are already synchronized!")

    def _sync_pyproject_toml(self):
        """Update tool versions in pyproject.toml."""
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            return

        print("\n📄 Checking pyproject.toml...")

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        updated = False

        # Update dev dependencies
        if "project" in data and "optional-dependencies" in data["project"]:
            dev_deps = data["project"]["optional-dependencies"].get("dev", [])
            new_deps = []

            for dep in dev_deps:
                dep_updated = False
                for tool, version in self.TOOL_VERSIONS.items():
                    if dep.startswith(f"{tool}==") or dep.startswith(f"{tool}>="):
                        new_dep = f"{tool}=={version}"
                        if dep != new_dep:
                            new_deps.append(new_dep)
                            dep_updated = True
                            updated = True
                            print(f"  Updated {tool}: {dep} → {new_dep}")
                        else:
                            new_deps.append(dep)
                        break
                if not dep_updated:
                    new_deps.append(dep)

            if updated:
                data["project"]["optional-dependencies"]["dev"] = new_deps
                with open(pyproject_path, "wb") as f:
                    tomli_w.dump(data, f)
                self.updates_made.append("pyproject.toml")

    def _sync_precommit_config(self):
        """Update tool versions in pre-commit config."""
        config_path = self.project_root / ".pre-commit-config.yaml"
        if not config_path.exists():
            return

        print("\n📄 Checking .pre-commit-config.yaml...")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        updated = False

        for repo in data.get("repos", []):
            # Ruff
            if "ruff-pre-commit" in repo.get("repo", ""):
                new_rev = f"v{self.TOOL_VERSIONS['ruff']}"
                if repo["rev"] != new_rev:
                    print(f"  Updated ruff: {repo['rev']} → {new_rev}")
                    repo["rev"] = new_rev
                    updated = True

            # Black
            elif "psf/black" in repo.get("repo", ""):
                new_rev = self.TOOL_VERSIONS["black"]
                if repo["rev"] != new_rev:
                    print(f"  Updated black: {repo['rev']} → {new_rev}")
                    repo["rev"] = new_rev
                    updated = True

            # mypy
            elif "mirrors-mypy" in repo.get("repo", ""):
                new_rev = f"v{self.TOOL_VERSIONS['mypy']}"
                if repo["rev"] != new_rev:
                    print(f"  Updated mypy: {repo['rev']} → {new_rev}")
                    repo["rev"] = new_rev
                    updated = True

            # bandit
            elif "PyCQA/bandit" in repo.get("repo", ""):
                new_rev = self.TOOL_VERSIONS["bandit"]
                if repo["rev"] != new_rev:
                    print(f"  Updated bandit: {repo['rev']} → {new_rev}")
                    repo["rev"] = new_rev
                    updated = True

            # interrogate
            elif "econchick/interrogate" in repo.get("repo", ""):
                new_rev = self.TOOL_VERSIONS["interrogate"]
                if repo["rev"] != new_rev:
                    print(f"  Updated interrogate: {repo['rev']} → {new_rev}")
                    repo["rev"] = new_rev
                    updated = True

        if updated:
            with open(config_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            self.updates_made.append(".pre-commit-config.yaml")

    def _sync_github_actions(self):
        """Update tool versions in GitHub Actions if they're pinned."""
        workflow_path = self.project_root / ".github/workflows/quality-check.yml"
        if not workflow_path.exists():
            return

        print("\n📄 Checking GitHub Actions workflow...")

        # For now, we don't pin versions in GHA since we install from pyproject.toml
        # But we could add version checks here if needed
        print("  Tool versions are managed via pyproject.toml")


if __name__ == "__main__":
    syncer = ToolVersionSync()
    syncer.sync_all()
