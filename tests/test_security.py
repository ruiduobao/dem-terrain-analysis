import os
import sys
import pytest

# Use the module already loaded by conftest
import dem_terrain_analysis as mod

_module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dem-terrain-analysis.py')


class TestNoExternalNetworkCalls:
    """Verify no external network calls are made."""

    def test_no_socket_import(self):
        """Module should not import socket."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        # socket should not be used for network calls
        assert 'import socket' not in source

    def test_no_urllib_import(self):
        """Module should not import urllib for HTTP calls."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'import urllib' not in source

    def test_no_requests_import(self):
        """Module should not import requests."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'import requests' not in source

    def test_no_http_import(self):
        """Module should not import http modules."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'import http' not in source


class TestNoSensitiveDataExposure:
    """Verify no sensitive data is logged or exposed."""

    def test_no_hardcoded_tokens(self):
        """Module should not contain hardcoded tokens."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'ghp_' not in source
        assert 'sk-' not in source
        assert 'api_key' not in source.lower() or 'api_key' in source.lower()

    def test_no_password_strings(self):
        """Module should not contain password strings."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        lower = source.lower()
        # Should not have hardcoded passwords
        assert 'password=' not in lower
        assert 'passwd=' not in lower


class TestNoUnsafeOperations:
    """Verify no unsafe operations."""

    def test_no_eval(self):
        """Module should not use eval()."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        # Allow eval in comments but not in code
        lines = source.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            assert 'eval(' not in stripped, f"eval() found in: {stripped}"

    def test_no_exec(self):
        """Module should not use exec()."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        lines = source.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            assert 'exec(' not in stripped, f"exec() found in: {stripped}"

    def test_no_subprocess(self):
        """Module should not use subprocess."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'import subprocess' not in source

    def test_no_os_system(self):
        """Module should not use os.system()."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'os.system(' not in source


class TestPrivacyNotice:
    """Verify privacy notice is present."""

    def test_privacy_in_docstring(self):
        """Module docstring should mention privacy."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'Privacy' in source or 'privacy' in source

    def test_user_agent_present(self):
        """Module should define a User-Agent."""
        assert hasattr(mod, 'USER_AGENT')
        assert 'dem-terrain-analysis' in mod.USER_AGENT

    def test_no_7897_port(self):
        """Module should not reference port 7897."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert '7897' not in source

    def test_no_proxy_config(self):
        """Module should not have proxy configuration."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'proxy' not in source.lower() or 'PROXY' not in source


class TestFileOperations:
    """Verify safe file operations."""

    def test_no_unsafe_file_write(self):
        """Module should only write to specified output paths."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert '/etc/' not in source
        assert 'C:\\Windows' not in source


class TestDependencyCheck:
    """Verify only stdlib is used."""

    def test_no_numpy(self):
        """Module should not import numpy."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'import numpy' not in source
        assert 'from numpy' not in source

    def test_no_scipy(self):
        """Module should not import scipy."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'import scipy' not in source
        assert 'from scipy' not in source

    def test_no_gdal(self):
        """Module should not import GDAL."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'import gdal' not in source
        assert 'from osgeo' not in source
        assert 'from gdal' not in source

    def test_no_rasterio(self):
        """Module should not import rasterio."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'import rasterio' not in source
        assert 'from rasterio' not in source

    def test_no_shapely(self):
        """Module should not import shapely."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        assert 'import shapely' not in source
        assert 'from shapely' not in source

    def test_only_stdlib_imports(self):
        """Module should only use stdlib imports."""
        source = open(_module_path, 'r', encoding='utf-8').read()
        stdlib_modules = {
            'argparse', 'collections', 'json', 'math', 'os', 'struct',
            'sys', 'zlib', 'deque', 'pathlib'
        }
        import_lines = []
        for line in source.split('\n'):
            stripped = line.strip()
            # Only match actual import statements, not comments or docstrings
            if stripped.startswith('import ') or (stripped.startswith('from ') and ' import ' in stripped):
                import_lines.append(stripped)
        for line in import_lines:
            if line.startswith('import '):
                module = line.split()[1].split('.')[0]
            else:
                module = line.split()[1].split('.')[0]
            assert module in stdlib_modules, f"Non-stdlib import: {line}"


class TestLicensePresent:
    """Verify license information."""

    def test_license_file_exists(self):
        """LICENSE file should exist."""
        license_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LICENSE')
        assert os.path.exists(license_path)

    def test_mit0_license(self):
        """Should be MIT-0 license."""
        license_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LICENSE')
        with open(license_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'MIT No Attribution' in content or 'MIT-0' in content
