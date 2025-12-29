#!/usr/bin/env python3
"""Deployment script for streamlit-notebook.

Automates the release process:
1. Bumps the patch version in pyproject.toml
2. Commits and pushes to GitHub
3. Cleans build artifacts
4. Builds distribution packages
5. Uploads to PyPI

Usage:
    python deploy.py
"""

import subprocess
import sys
import shutil
from pathlib import Path

# Try to import tomllib (Python 3.11+) or fallback to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomli package is required for Python < 3.11")
        print("Install with: pip install tomli")
        sys.exit(1)


def run_command(cmd, check=True, capture_output=False):
    """Run a shell command and handle errors."""
    print(f"Running: {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        check=check,
        capture_output=capture_output,
        text=True
    )
    if capture_output:
        return result.stdout.strip()
    return result


def get_current_version():
    """Extract current version from pyproject.toml using TOML parser."""
    pyproject_path = Path("pyproject.toml")

    with open(pyproject_path, 'rb') as f:
        data = tomllib.load(f)

    version = data.get('project', {}).get('version')
    if not version:
        print("Error: Could not find version in pyproject.toml")
        sys.exit(1)

    return version


def bump_patch_version(version):
    """Increment the patch version number."""
    parts = version.split('.')
    if len(parts) != 3:
        print(f"Error: Invalid version format: {version}")
        sys.exit(1)

    major, minor, patch = parts
    new_patch = int(patch) + 1
    return f"{major}.{minor}.{new_patch}"


def update_version_in_file(new_version):
    """Update the version in pyproject.toml using line-by-line replacement."""
    pyproject_path = Path("pyproject.toml")
    lines = pyproject_path.read_text(encoding="utf-8").splitlines(keepends=True)

    # Track if we're in the [project] section
    in_project_section = False
    version_updated = False

    new_lines = []
    for line in lines:
        # Check if we're entering the [project] section
        if line.strip() == '[project]':
            in_project_section = True
            new_lines.append(line)
            continue

        # Check if we're leaving the [project] section (entering a new section)
        if line.strip().startswith('[') and line.strip() != '[project]':
            in_project_section = False

        # Only replace version if we're in the [project] section
        if in_project_section and line.strip().startswith('version'):
            new_lines.append(f'version = "{new_version}"\n')
            version_updated = True
        else:
            new_lines.append(line)

    if not version_updated:
        print("Error: Could not find version field in [project] section")
        sys.exit(1)

    pyproject_path.write_text(''.join(new_lines), encoding="utf-8")
    print(f"Updated pyproject.toml to version {new_version}")


def commit_and_push(version):
    """Commit version bump and push to GitHub."""
    run_command("git add pyproject.toml")
    run_command(f'git commit -m "Bumped to v{version}"')
    run_command("git push")
    print(f"Committed and pushed version {version} to GitHub")


def clean_build_artifacts():
    """Remove build, dist, and egg-info directories."""
    dirs_to_remove = ["build", "dist", "streamlit_notebook.egg-info"]

    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"Removing {dir_name}/")
            shutil.rmtree(dir_path)

    print("Build artifacts cleaned")


def build_package():
    """Build the distribution packages."""
    run_command("python3 -m build")
    print("Package built successfully")


def upload_to_pypi():
    """Upload the package to PyPI using twine."""
    run_command("twine upload dist/*")
    print("Package uploaded to PyPI")


def main():
    """Main deployment workflow."""
    print("=" * 60)
    print("streamlit-notebook Deployment Script")
    print("=" * 60)
    print()

    # Check if we're in a git repository
    try:
        run_command("git status", capture_output=True)
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository")
        sys.exit(1)

    # Check for uncommitted changes (excluding pyproject.toml)
    status = run_command("git status --porcelain", capture_output=True)
    if status:
        # Filter out pyproject.toml
        lines = [line for line in status.split('\n') if line and 'pyproject.toml' not in line]
        if lines:
            print("Error: You have uncommitted changes:")
            print(status)
            print("\nPlease commit or stash your changes before deploying.")
            sys.exit(1)

    # Get current version and bump it
    current_version = get_current_version()
    new_version = bump_patch_version(current_version)

    print(f"Current version: {current_version}")
    print(f"New version:     {new_version}")
    print()

    # Confirm deployment
    response = input(f"Deploy version {new_version}? [y/N]: ").strip().lower()
    if response != 'y':
        print("Deployment cancelled.")
        sys.exit(0)

    print()
    print("Starting deployment...")
    print()

    try:
        # Step 1: Bump version
        print("Step 1/5: Bumping version...")
        update_version_in_file(new_version)
        print()

        # Step 2: Commit and push
        print("Step 2/5: Committing and pushing to GitHub...")
        commit_and_push(new_version)
        print()

        # Step 3: Clean build artifacts
        print("Step 3/5: Cleaning build artifacts...")
        clean_build_artifacts()
        print()

        # Step 4: Build package
        print("Step 4/5: Building package...")
        build_package()
        print()

        # Step 5: Upload to PyPI
        print("Step 5/5: Uploading to PyPI...")
        upload_to_pypi()
        print()

        print("=" * 60)
        print(f"✅ Successfully deployed version {new_version}!")
        print("=" * 60)
        print()
        print("Package is now available on PyPI:")
        print(f"  pip install streamlit-notebook=={new_version}")
        print()

    except subprocess.CalledProcessError as e:
        print()
        print("=" * 60)
        print("❌ Deployment failed!")
        print("=" * 60)
        print(f"\nError: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print("\nDeployment interrupted by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()
