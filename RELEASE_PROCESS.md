# Release Process for arris-modem-status

## Quick Release (Recommended)

For most releases, use the automated workflow:

```bash
# Ensure code is ready
make dev-check              # Must pass 100% (includes security checks)

# Automated patch release (1.0.0 → 1.0.1)
make release-patch

# Automated minor release (1.0.0 → 1.1.0)
make release-minor
```

**What happens automatically:**
1. ✅ Runs full validation (`dev-check` - format, lint, type-check, test, security)
2. ✅ Bumps version and updates files
3. ✅ Creates git commit and tag
4. ✅ Pushes to GitHub (triggers CI/CD)
5. ✅ GitHub Actions builds and publishes to PyPI
6. ✅ Creates GitHub release with artifacts

**Monitor progress:** https://github.com/csmarshall/arris-modem-status/actions

## Manual Release Process

For more control or when automation fails:

### Phase 1: Pre-Release Validation
```bash
git checkout main && git pull origin main
make dev-check              # Complete validation (includes security scans)
git status                  # Ensure clean working directory
```

### Phase 2: Test Release (Recommended)
```bash
make build                  # Build packages
make release-test           # Upload to TestPyPI

# Verify test installation
pip install -i https://test.pypi.org/simple/ arris-modem-status
arris-modem-status --help   # Should work
```

### Phase 3: Version Management
```bash
# Choose appropriate version bump:
make version-patch          # Bug fixes (1.0.0 → 1.0.1)
make version-minor          # New features (1.0.0 → 1.1.0)
make version-major          # Breaking changes (1.0.0 → 2.0.0)

# Verify version update
make version               # Should show new version
```

### Phase 4: Production Release
```bash
# Option A: Trigger automated release
git push origin main --tags

# Option B: Manual release
make release               # Direct upload to PyPI (prompts for confirmation)
```

### Phase 5: Post-Release Validation
```bash
# Verify PyPI publication (wait ~5 minutes for propagation)
pip install arris-modem-status    # Should install new version
arris-modem-status --help         # Should work
python -c "import arris_modem_status; print(arris_modem_status.__version__)"

# Check GitHub release was created
# Visit: https://github.com/csmarshall/arris-modem-status/releases
```

## Initial Release Preparation

For the first PyPI release (1.0.0), you may want to clean git history:

### Git History Cleanup (Optional)
```bash
# 1. Backup all development history
git branch dev-pre-1.0.0
git push origin dev-pre-1.0.0

# 2. Create clean main branch
git checkout --orphan temp-clean
git add .
git commit -m "Initial commit - Complete arris-modem-status implementation"
git branch -D main
git branch -m main

# 3. Force push clean history
git push origin main --force

# Result: Clean public history, development history preserved in dev-pre-1.0.0
```

## Version Guidelines

### Patch Releases (X.Y.Z+1)
- Bug fixes
- Documentation updates
- Minor performance improvements
- No API changes

### Minor Releases (X.Y+1.0)
- New features
- New command-line options
- Backward-compatible API changes
- Dependency updates

### Major Releases (X+1.0.0)
- Breaking API changes
- Removed deprecated features
- Major architectural changes
- Python version requirement changes

## Emergency Procedures

### If Automated Release Fails
```bash
# Check GitHub Actions logs first
# Then manually release:
make clean && make build && make release
```

### If Bad Release Published
```bash
# You cannot delete from PyPI, but can yank versions
# Go to: https://pypi.org/manage/project/arris-modem-status/releases/

# Release hotfix immediately:
make version-patch
# Fix issues in code
make dev-check
make release-patch
```

### Rollback Process
1. **Cannot delete** from PyPI (by design)
2. **Yank the release** on PyPI web interface (makes it unavailable for new installs)
3. **Release immediate hotfix** with fix
4. **Communicate** the issue and resolution

## Release Checklist

Copy this for each release:

### Pre-Release ✅
- [ ] All tests passing: `make dev-check`
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if major changes)
- [ ] Working directory clean: `git status`

### Test Release ✅
- [ ] TestPyPI upload successful: `make release-test`
- [ ] Package installs from TestPyPI
- [ ] CLI functionality verified: `arris-modem-status --help`
- [ ] Import test passes

### Production Release ✅
- [ ] Version bumped appropriately
- [ ] Automated release triggered OR manual release completed
- [ ] GitHub Actions completed successfully (if automated)
- [ ] PyPI page shows new version
- [ ] Fresh installation verified

## Configuration Requirements

### One-Time Setup
1. **PyPI API Token:** Added to GitHub repository secrets as `PYPI_API_TOKEN`
2. **Development Environment:** `make setup-dev`
3. **Pre-commit Hooks:** Installed via `setup-dev`

### Required Files
- [x] `pyproject.toml` - Package configuration
- [x] `.bumpversion.toml` - Version management
- [x] `.github/workflows/release.yaml` - Automated PyPI publishing
- [x] `Makefile` - Development commands

## Available Make Commands

**Essential commands:**
```bash
make help           # Show all commands
make setup-dev      # One-time development setup
make dev-check      # Complete validation (format, lint, type-check, test, security)
make test           # Run tests with coverage
make build          # Build packages for PyPI
make clean          # Clean build artifacts

# Version management
make version        # Show current version
make version-patch  # Bump patch version
make version-minor  # Bump minor version
make version-major  # Bump major version

# Release workflow
make release-test   # Upload to TestPyPI
make release        # Upload to PyPI (manual)
make release-patch  # Automated patch release
make release-minor  # Automated minor release

# Development utilities
make info           # Show project status
make pre-commit     # Run pre-commit hooks manually
```

## Success Indicators

Your release is successful when:

1. ✅ **GitHub Actions complete** (green checkmarks)
2. ✅ **PyPI shows new version:** https://pypi.org/project/arris-modem-status/
3. ✅ **GitHub release created:** https://github.com/csmarshall/arris-modem-status/releases
4. ✅ **Package installs cleanly:** `pip install arris-modem-status`
5. ✅ **CLI works:** `arris-modem-status --help`
6. ✅ **No import errors:** `python -c "import arris_modem_status"`

## Development Cycle

**Daily development:**
```
Code Changes → make dev-check → git commit → git push
```

**Release cycle:**
```
make dev-check → make release-patch → Monitor GitHub Actions → Verify PyPI
```

**Typical release time:** 2-3 minutes of manual work + 5-10 minutes of automated processing.

## Troubleshooting

### Common Issues

**"Version already exists on PyPI"**
```bash
make version-patch  # Bump again and retry
```

**"Authentication failed"**
- Check `PYPI_API_TOKEN` in GitHub repository secrets
- Regenerate PyPI API token if expired

**"Build artifacts missing"**
```bash
make clean && make build
ls -la dist/  # Should see .whl and .tar.gz files
```

**"GitHub Actions failing"**
- Check logs at: https://github.com/csmarshall/arris-modem-status/actions
- Common fixes: update secrets, fix code issues, retry release

**"make dev-check fails"**
```bash
# Run individual steps to identify issue:
make format         # Fix formatting
make lint          # Check linting
make typecheck     # Check types
make test          # Run tests
make security      # Security scans
```

### Support
- **GitHub Issues:** https://github.com/csmarshall/arris-modem-status/issues
- **PyPI Project:** https://pypi.org/project/arris-modem-status/
- **Documentation:** README.md

---

*This process is designed for reliability and speed. The automated workflow handles 95% of releases with minimal manual intervention.*
