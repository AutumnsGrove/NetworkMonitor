"""Tests for browser extension files."""

import json
import os
import pytest


def test_extension_directory_exists():
    """Test that extension directory exists."""
    assert os.path.exists("extension"), "extension/ directory should exist"


def test_manifest_exists():
    """Test that manifest.json exists and is valid."""
    manifest_path = "extension/manifest.json"
    assert os.path.exists(manifest_path), "manifest.json should exist"

    # Test JSON validity
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Test required fields
    assert "manifest_version" in manifest
    assert manifest["manifest_version"] == 2
    assert "name" in manifest
    assert "version" in manifest
    assert "permissions" in manifest
    assert "background" in manifest


def test_manifest_permissions():
    """Test that manifest has correct permissions."""
    manifest_path = "extension/manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    permissions = manifest["permissions"]
    assert "tabs" in permissions
    assert "http://localhost/*" in permissions or any("localhost" in p for p in permissions)


def test_manifest_background_script():
    """Test that manifest references background.js."""
    manifest_path = "extension/manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    assert "background" in manifest
    assert "scripts" in manifest["background"]
    assert "background.js" in manifest["background"]["scripts"]


def test_background_script_exists():
    """Test that background.js exists."""
    background_path = "extension/background.js"
    assert os.path.exists(background_path), "background.js should exist"

    # Test file contains key functions
    with open(background_path) as f:
        content = f.read()

    assert "extractDomain" in content
    assert "reportDomain" in content
    assert "API_ENDPOINT" in content


def test_background_script_api_endpoint():
    """Test that background.js has correct API endpoint."""
    background_path = "extension/background.js"
    with open(background_path) as f:
        content = f.read()

    # Should reference localhost:7500 and correct endpoint
    assert "localhost:7500" in content
    assert "/api/browser/active-tab" in content


def test_background_script_functions():
    """Test that background.js contains required functions."""
    background_path = "extension/background.js"
    with open(background_path) as f:
        content = f.read()

    required_functions = [
        "extractDomain",
        "extractParentDomain",
        "reportDomain",
        "startReporting",
        "stopReporting",
        "handleTabActivated",
        "handleTabUpdated",
        "initialize"
    ]

    for func in required_functions:
        assert func in content, f"Function '{func}' should exist in background.js"


def test_icons_directory_exists():
    """Test that icons directory exists."""
    icons_dir = "extension/icons"
    assert os.path.exists(icons_dir), "icons/ directory should exist"


def test_icons_readme_exists():
    """Test that icons README exists."""
    readme_path = "extension/icons/README.md"
    assert os.path.exists(readme_path), "extension/icons/README.md should exist"


def test_extension_readme_exists():
    """Test that extension README exists."""
    readme_path = "extension/README.md"
    assert os.path.exists(readme_path), "extension/README.md should exist"


def test_extension_readme_content():
    """Test that extension README has required sections."""
    readme_path = "extension/README.md"
    with open(readme_path) as f:
        content = f.read()

    required_sections = [
        "Installation",
        "Configuration",
        "Testing",
        "Troubleshooting",
        "Privacy & Security"
    ]

    for section in required_sections:
        assert section in content, f"Section '{section}' should exist in README"


def test_manifest_browser_settings():
    """Test that manifest has Firefox/Zen browser settings."""
    manifest_path = "extension/manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Should have browser_specific_settings for Firefox/Zen
    assert "browser_specific_settings" in manifest or "applications" in manifest


# Additional tests can be added for actual extension functionality
# Note: Full extension testing requires browser automation (Selenium/Playwright)
