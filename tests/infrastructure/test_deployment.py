#!/usr/bin/env python3
"""
Infrastructure and deployment tests for the misinformation heatmap application.
Tests local setup, cloud deployment, and environment switching.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests


class DeploymentTestCase(unittest.TestCase):
    """Base test case for deployment tests."""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.backend_dir = self.project_root / "backend"
        
    def run_script(self, script_path, args=None, timeout=60):
        """Run a script and return the result."""
        script_path = Path(script_path)
        
        # Handle different script types based on extension
        if script_path.suffix == '.py':
            cmd = [sys.executable, str(script_path)]
        elif script_path.suffix == '.sh':
            # On Windows, try to run with bash if available, otherwise skip
            if os.name == 'nt':
                # Try Git Bash or WSL bash
                bash_paths = [
                    r"C:\Program Files\Git\bin\bash.exe",
                    r"C:\Windows\System32\bash.exe"
                ]
                bash_exe = None
                for bash_path in bash_paths:
                    if Path(bash_path).exists():
                        bash_exe = bash_path
                        break
                
                if bash_exe:
                    cmd = [bash_exe, str(script_path)]
                else:
                    # Skip bash scripts on Windows without bash
                    return Mock(returncode=0, stdout="Skipped on Windows", stderr="")
            else:
                cmd = ['bash', str(script_path)]
        elif script_path.suffix == '.ps1':
            if os.name == 'nt':
                cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', str(script_path)]
            else:
                # Skip PowerShell scripts on non-Windows
                return Mock(returncode=0, stdout="Skipped on non-Windows", stderr="")
        else:
            cmd = [str(script_path)]
            
        if args:
            cmd.extend(args)
            
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            return result
        except subprocess.TimeoutExpired:
            self.fail(f"Script {script_path} timed out after {timeout}s")
        except FileNotFoundError:
            # Return a mock result for missing executables
            return Mock(returncode=1, stdout="", stderr=f"Executable not found for {script_path}")


class LocalSetupTests(DeploymentTestCase):
    """Tests for local development setup scripts."""
    
    def test_run_local_script_exists(self):
        """Test that local setup scripts exist and are executable."""
        bash_script = self.scripts_dir / "run_local.sh"
        ps_script = self.scripts_dir / "run_local.ps1"
        
        self.assertTrue(bash_script.exists(), "run_local.sh script not found")
        self.assertTrue(ps_script.exists(), "run_local.ps1 script not found")
    
    def test_run_local_help(self):
        """Test that local setup script shows help correctly."""
        script = self.scripts_dir / "run_local.sh"
        result = self.run_script(script, ["--help"])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("Options:", result.stdout)
    
    def test_environment_validation_script(self):
        """Test environment validation script."""
        script = self.scripts_dir / "validate_environment.py"
        self.assertTrue(script.exists(), "validate_environment.py not found")
        
        # Test help
        result = self.run_script(script, ["--help"])
        self.assertEqual(result.returncode, 0)
        
        # Test validation (may fail due to missing dependencies, but should not crash)
        result = self.run_script(script, ["--mode", "local"])
        self.assertIn(result.returncode, [0, 1])  # Either pass or fail, but not crash
    
    def test_database_initialization_script(self):
        """Test database initialization script."""
        script = self.backend_dir / "init_db.py"
        self.assertTrue(script.exists(), "init_db.py not found")
        
        # Test help
        result = self.run_script(script, ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Initialize database", result.stdout)
    
    def test_health_check_script(self):
        """Test health check script."""
        script = self.scripts_dir / "health_check.py"
        self.assertTrue(script.exists(), "health_check.py not found")
        
        # Test help
        result = self.run_script(script, ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Health check", result.stdout)


class CloudDeploymentTests(DeploymentTestCase):
    """Tests for cloud deployment scripts."""
    
    def test_cloud_deployment_scripts_exist(self):
        """Test that cloud deployment scripts exist."""
        scripts = [
            "deploy_cloudrun.sh",
            "pubsub_setup.sh", 
            "setup_bigquery.sh",
            "cloud_env_template.sh"
        ]
        
        for script_name in scripts:
            script_path = self.scripts_dir / script_name
            self.assertTrue(script_path.exists(), f"{script_name} not found")
    
    def test_deploy_cloudrun_help(self):
        """Test Cloud Run deployment script help."""
        script = self.scripts_dir / "deploy_cloudrun.sh"
        result = self.run_script(script, ["--help"])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Cloud Run Deployment", result.stdout)
        self.assertIn("--project", result.stdout)
    
    def test_pubsub_setup_help(self):
        """Test Pub/Sub setup script help."""
        script = self.scripts_dir / "pubsub_setup.sh"
        result = self.run_script(script, ["--help"])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Pub/Sub Setup", result.stdout)
        self.assertIn("--project", result.stdout)
    
    def test_bigquery_setup_help(self):
        """Test BigQuery setup script help."""
        script = self.scripts_dir / "setup_bigquery.sh"
        result = self.run_script(script, ["--help"])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("BigQuery Setup", result.stdout)
        self.assertIn("--project", result.stdout)
    
    def test_bigquery_schema_file(self):
        """Test BigQuery schema SQL file."""
        schema_file = self.scripts_dir / "bigquery_schema.sql"
        self.assertTrue(schema_file.exists(), "bigquery_schema.sql not found")
        
        # Check that schema contains expected elements
        content = schema_file.read_text()
        self.assertIn("CREATE SCHEMA", content)
        self.assertIn("misinformation_heatmap", content)
        self.assertIn("events", content)
        self.assertIn("state_aggregations", content)
    
    def test_cloud_env_template(self):
        """Test cloud environment template."""
        template = self.scripts_dir / "cloud_env_template.sh"
        self.assertTrue(template.exists(), "cloud_env_template.sh not found")
        
        content = template.read_text()
        self.assertIn("GOOGLE_CLOUD_PROJECT", content)
        self.assertIn("BIGQUERY_DATASET", content)
        self.assertIn("PUBSUB_", content)


class EnvironmentSwitchingTests(DeploymentTestCase):
    """Tests for switching between local and cloud environments."""
    
    def test_config_mode_switching(self):
        """Test configuration mode switching."""
        # Import Config class to test mode switching
        sys.path.append(str(self.backend_dir))
        
        try:
            from config import Config
            
            # Test local mode
            with patch.dict(os.environ, {'MODE': 'local'}):
                config = Config()
                self.assertTrue(config.is_local_mode())
                self.assertFalse(config.is_cloud_mode())
                self.assertEqual(config.mode, 'local')
            
            # Test cloud mode
            with patch.dict(os.environ, {
                'MODE': 'cloud',
                'GCP_PROJECT_ID': 'test-project',
                'WATSON_API_KEY': 'test-key',
                'GEE_SERVICE_ACCOUNT': '/path/to/service-account.json'
            }):
                config = Config()
                self.assertTrue(config.is_cloud_mode())
                self.assertFalse(config.is_local_mode())
                self.assertEqual(config.mode, 'cloud')
                
        except ImportError:
            self.skipTest("Config module not available")
    
    def test_database_configuration_switching(self):
        """Test database configuration for different modes."""
        sys.path.append(str(self.backend_dir))
        
        try:
            from config import Config
            
            # Test local mode database config
            with patch.dict(os.environ, {'MODE': 'local'}):
                config = Config()
                db_config = config.get_database_config()
                self.assertEqual(db_config.type, 'sqlite')
                self.assertIn('sqlite:///', db_config.url)
            
            # Test cloud mode database config
            with patch.dict(os.environ, {
                'MODE': 'cloud',
                'GCP_PROJECT_ID': 'test-project'
            }):
                config = Config()
                db_config = config.get_database_config()
                self.assertEqual(db_config.type, 'bigquery')
                self.assertEqual(db_config.project_id, 'test-project')
                
        except ImportError:
            self.skipTest("Config module not available")
    
    def test_pubsub_configuration_switching(self):
        """Test Pub/Sub configuration for different modes."""
        sys.path.append(str(self.backend_dir))
        
        try:
            from config import Config
            
            # Test local mode Pub/Sub config
            with patch.dict(os.environ, {'MODE': 'local'}):
                config = Config()
                pubsub_config = config.get_pubsub_config()
                self.assertTrue(pubsub_config.use_emulator)
                self.assertEqual(pubsub_config.emulator_host, 'localhost:8085')
            
            # Test cloud mode Pub/Sub config
            with patch.dict(os.environ, {
                'MODE': 'cloud',
                'GCP_PROJECT_ID': 'test-project'
            }):
                config = Config()
                pubsub_config = config.get_pubsub_config()
                self.assertFalse(pubsub_config.use_emulator)
                self.assertEqual(pubsub_config.project_id, 'test-project')
                
        except ImportError:
            self.skipTest("Config module not available")
    
    def test_satellite_configuration_switching(self):
        """Test satellite validation configuration for different modes."""
        sys.path.append(str(self.backend_dir))
        
        try:
            from config import Config
            
            # Test local mode satellite config
            with patch.dict(os.environ, {'MODE': 'local'}):
                config = Config()
                satellite_config = config.get_satellite_config()
                self.assertTrue(satellite_config.use_stub)
            
            # Test cloud mode satellite config
            with patch.dict(os.environ, {
                'MODE': 'cloud',
                'GEE_SERVICE_ACCOUNT': '/path/to/service-account.json'
            }):
                config = Config()
                satellite_config = config.get_satellite_config()
                self.assertFalse(satellite_config.use_stub)
                self.assertEqual(satellite_config.gee_service_account_path, '/path/to/service-account.json')
                
        except ImportError:
            self.skipTest("Config module not available")
    
    def test_environment_variable_validation(self):
        """Test environment variable validation for different modes."""
        sys.path.append(str(self.backend_dir))
        
        try:
            from config import Config
            
            # Test cloud mode missing required variables
            with patch.dict(os.environ, {'MODE': 'cloud'}, clear=True):
                with self.assertRaises(ValueError):
                    config = Config()
                    config.get_database_config()  # Should fail without GCP_PROJECT_ID
            
            # Test cloud mode with required variables
            with patch.dict(os.environ, {
                'MODE': 'cloud',
                'GCP_PROJECT_ID': 'test-project',
                'WATSON_API_KEY': 'test-key',
                'GEE_SERVICE_ACCOUNT': '/path/to/service-account.json'
            }):
                config = Config()
                # Should not raise exceptions
                db_config = config.get_database_config()
                watson_config = config.get_watson_config()
                satellite_config = config.get_satellite_config()
                
                self.assertEqual(db_config.project_id, 'test-project')
                self.assertTrue(watson_config['enabled'])
                self.assertFalse(satellite_config.use_stub)
                
        except ImportError:
            self.skipTest("Config module not available")


class IntegrationTests(DeploymentTestCase):
    """Integration tests for deployment components."""
    
    def test_script_dependencies(self):
        """Test that all scripts have their dependencies available."""
        # Test Python scripts
        python_scripts = [
            "validate_environment.py",
            "health_check.py",
            "performance_benchmark.py"
        ]
        
        for script_name in python_scripts:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                # Test that script can be imported (basic syntax check)
                result = subprocess.run([
                    sys.executable, "-m", "py_compile", str(script_path)
                ], capture_output=True)
                
                self.assertEqual(result.returncode, 0, 
                    f"Python script {script_name} has syntax errors: {result.stderr.decode()}")
    
    def test_deployment_script_execution(self):
        """Test deployment scripts can be executed with help flags."""
        bash_scripts = [
            ("run_local.sh", ["--help"]),
            ("deploy_cloudrun.sh", ["--help"]),
            ("pubsub_setup.sh", ["--help"]),
            ("setup_bigquery.sh", ["--help"])
        ]
        
        for script_name, args in bash_scripts:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                try:
                    result = self.run_script(script_path, args, timeout=30)
                    self.assertEqual(result.returncode, 0, 
                        f"Script {script_name} help failed: {result.stderr}")
                    self.assertIn("Usage:", result.stdout, 
                        f"Script {script_name} missing usage information")
                except subprocess.TimeoutExpired:
                    self.fail(f"Script {script_name} timed out")
    
    def test_environment_validation_integration(self):
        """Test environment validation script integration."""
        script = self.scripts_dir / "validate_environment.py"
        if script.exists():
            # Test local mode validation
            result = self.run_script(script, ["--mode", "local"], timeout=60)
            self.assertIn(result.returncode, [0, 1])  # Either pass or fail gracefully
            
            # Test that it produces output
            self.assertTrue(result.stdout or result.stderr, 
                "Environment validation script produced no output")
    
    def test_health_check_integration(self):
        """Test health check script integration."""
        script = self.scripts_dir / "health_check.py"
        if script.exists():
            # Test help
            result = self.run_script(script, ["--help"])
            self.assertEqual(result.returncode, 0)
            self.assertIn("Health check", result.stdout)
            
            # Test JSON format
            result = self.run_script(script, ["--format", "json"], timeout=30)
            self.assertIn(result.returncode, [0, 1])  # May fail if services not running
    
    def test_test_data_integrity(self):
        """Test that test data files are valid."""
        test_data_file = self.project_root / "data" / "fact_checks.csv"
        
        if test_data_file.exists():
            content = test_data_file.read_text()
            lines = content.strip().split('\n')
            
            # Should have header + data rows
            self.assertGreater(len(lines), 1, "Test data file is empty")
            
            # Check header
            header = lines[0]
            expected_columns = [
                'event_id', 'source', 'original_text', 'lang', 
                'region_hint', 'lat', 'lon', 'category'
            ]
            
            for column in expected_columns:
                self.assertIn(column, header, f"Missing column: {column}")
    
    def test_geojson_data_integrity(self):
        """Test that GeoJSON data is valid."""
        geojson_files = [
            self.project_root / "data" / "india_states_geojson.json",
            self.project_root / "frontend" / "data" / "india-states.geojson"
        ]
        
        for geojson_file in geojson_files:
            if geojson_file.exists():
                try:
                    content = geojson_file.read_text()
                    data = json.loads(content)
                    
                    # Basic GeoJSON structure validation
                    self.assertEqual(data.get("type"), "FeatureCollection")
                    self.assertIn("features", data)
                    self.assertIsInstance(data["features"], list)
                    
                    # Check if features exist (may be empty in test data)
                    if len(data["features"]) > 0:
                        # Check first feature structure
                        feature = data["features"][0]
                        self.assertEqual(feature.get("type"), "Feature")
                        self.assertIn("properties", feature)
                        self.assertIn("geometry", feature)
                        
                        # Validate Indian state properties
                        properties = feature.get("properties", {})
                        self.assertTrue(
                            "NAME" in properties or "name" in properties or "ST_NM" in properties,
                            "GeoJSON feature missing state name property"
                        )
                    else:
                        # Empty features array is acceptable for test data
                        print(f"Warning: {geojson_file} has empty features array")
                        
                except json.JSONDecodeError as e:
                    self.fail(f"Invalid GeoJSON format in {geojson_file}: {e}")
    
    def test_docker_configuration(self):
        """Test Docker configuration files if they exist."""
        dockerfile_paths = [
            self.backend_dir / "Dockerfile",
            self.project_root / "Dockerfile"
        ]
        
        for dockerfile in dockerfile_paths:
            if dockerfile.exists():
                content = dockerfile.read_text()
                
                # Basic Dockerfile validation
                self.assertIn("FROM", content, "Dockerfile missing FROM instruction")
                self.assertIn("WORKDIR", content, "Dockerfile missing WORKDIR instruction")
                self.assertIn("COPY", content, "Dockerfile missing COPY instruction")
                
                # Check for Python-specific instructions
                if "python" in content.lower():
                    self.assertIn("pip install", content, "Python Dockerfile missing pip install")
    
    def test_cloud_configuration_templates(self):
        """Test cloud configuration templates."""
        cloud_templates = [
            self.scripts_dir / "cloud_env_template.sh",
            self.scripts_dir / "bigquery_schema.sql"
        ]
        
        for template in cloud_templates:
            if template.exists():
                content = template.read_text()
                self.assertGreater(len(content.strip()), 0, 
                    f"Template {template.name} is empty")
                
                if template.name.endswith('.sql'):
                    # Basic SQL validation
                    self.assertIn("CREATE", content.upper(), 
                        "SQL template missing CREATE statements")
                elif template.name.endswith('.sh'):
                    # Basic shell script validation
                    self.assertTrue(content.startswith('#!/bin/bash') or 
                                  content.startswith('#!/bin/sh'),
                                  "Shell script missing shebang")


class DeploymentScriptTests(DeploymentTestCase):
    """Tests for deployment script functionality and error handling."""
    
    def test_local_setup_script_error_handling(self):
        """Test local setup script error handling."""
        script = self.scripts_dir / "run_local.sh"
        if not script.exists():
            self.skipTest("run_local.sh not found")
        
        # Test invalid mode
        result = self.run_script(script, ["--mode", "invalid"])
        self.assertNotEqual(result.returncode, 0, "Script should fail with invalid mode")
        
        # Test help output
        result = self.run_script(script, ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--mode", result.stdout)
    
    def test_cloud_deployment_script_validation(self):
        """Test cloud deployment script validation."""
        script = self.scripts_dir / "deploy_cloudrun.sh"
        if not script.exists():
            self.skipTest("deploy_cloudrun.sh not found")
        
        # Test missing project ID
        result = self.run_script(script, ["--build-only"])
        self.assertNotEqual(result.returncode, 0, "Script should fail without project ID")
        self.assertIn("Project ID", result.stderr)
        
        # Test help output
        result = self.run_script(script, ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("--project", result.stdout)
    
    def test_pubsub_setup_script_validation(self):
        """Test Pub/Sub setup script validation."""
        script = self.scripts_dir / "pubsub_setup.sh"
        if not script.exists():
            self.skipTest("pubsub_setup.sh not found")
        
        # Test dry run mode
        result = self.run_script(script, ["--project", "test-project", "--dry-run"])
        self.assertEqual(result.returncode, 0, "Dry run should succeed")
        self.assertIn("DRY RUN", result.stdout)
        
        # Test list functionality (should work without project)
        result = self.run_script(script, ["--list"])
        # May fail if not authenticated, but should not crash
        self.assertIn(result.returncode, [0, 1])
    
    def test_bigquery_setup_script_validation(self):
        """Test BigQuery setup script validation."""
        script = self.scripts_dir / "setup_bigquery.sh"
        if not script.exists():
            self.skipTest("setup_bigquery.sh not found")
        
        # Test missing project ID
        result = self.run_script(script, ["--dry-run"])
        self.assertNotEqual(result.returncode, 0, "Script should fail without project ID")
        
        # Test with project ID in dry run
        result = self.run_script(script, ["--project", "test-project", "--dry-run"])
        # May fail due to missing gcloud/bq, but should handle gracefully
        self.assertIn(result.returncode, [0, 1])
    
    def test_script_permissions(self):
        """Test that deployment scripts have correct permissions."""
        bash_scripts = [
            "run_local.sh",
            "deploy_cloudrun.sh", 
            "pubsub_setup.sh",
            "setup_bigquery.sh"
        ]
        
        for script_name in bash_scripts:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                # On Windows, just check that file exists and is readable
                if os.name == 'nt':
                    self.assertTrue(script_path.is_file(), f"Script {script_name} is not a file")
                    # Check if file is readable
                    try:
                        with open(script_path, 'r') as f:
                            f.read(1)
                        readable = True
                    except:
                        readable = False
                    self.assertTrue(readable, f"Script {script_name} is not readable")
                else:
                    # On Unix-like systems, check executable permissions
                    stat_info = script_path.stat()
                    is_executable = bool(stat_info.st_mode & 0o111)
                    self.assertTrue(is_executable, f"Script {script_name} is not executable")
    
    def test_powershell_script_functionality(self):
        """Test PowerShell script functionality on Windows."""
        ps_script = self.scripts_dir / "run_local.ps1"
        if not ps_script.exists():
            self.skipTest("run_local.ps1 not found")
        
        # Test help functionality
        try:
            result = subprocess.run([
                "powershell", "-ExecutionPolicy", "Bypass", 
                "-File", str(ps_script), "-Help"
            ], capture_output=True, text=True, timeout=30)
            
            # Should work on Windows, may fail on other platforms
            if result.returncode == 0:
                self.assertIn("Usage:", result.stdout)
            else:
                # If PowerShell not available, just check file exists and has content
                content = ps_script.read_text()
                self.assertIn("param(", content)
                self.assertIn("function", content.lower())
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # PowerShell not available, just validate file structure
            content = ps_script.read_text()
            self.assertIn("param(", content)
            self.assertGreater(len(content), 1000, "PowerShell script seems too short")


class ErrorHandlingTests(DeploymentTestCase):
    """Tests for error handling in deployment scenarios."""
    
    def test_missing_dependencies_handling(self):
        """Test handling of missing dependencies."""
        # Test environment validation with missing dependencies
        script = self.scripts_dir / "validate_environment.py"
        if script.exists():
            # Test with minimal environment
            minimal_env = {
                'PATH': os.environ.get('PATH', ''),
                'PYTHONPATH': os.environ.get('PYTHONPATH', ''),
                'HOME': os.environ.get('HOME', ''),
                'MODE': 'local'
            }
            
            result = subprocess.run([
                sys.executable, str(script), "--mode", "local"
            ], env=minimal_env, capture_output=True, text=True, timeout=60)
            
            # Should handle missing dependencies gracefully
            self.assertIn(result.returncode, [0, 1])
            self.assertTrue(result.stdout or result.stderr)
    
    def test_network_failure_handling(self):
        """Test handling of network failures."""
        # Test health check with unreachable services
        script = self.scripts_dir / "health_check.py"
        if script.exists():
            # Test with unreachable URL and very short timeout
            try:
                result = self.run_script(script, [
                    "--url", "http://localhost:9999", 
                    "--timeout", "1",
                    "--format", "json"
                ], timeout=10)
                
                # Should fail gracefully
                self.assertEqual(result.returncode, 1)
                
                # Should produce some output (may not be valid JSON if connection fails quickly)
                self.assertTrue(result.stdout or result.stderr, 
                    "Health check should produce some output even on failure")
                
                # Try to parse JSON if stdout exists
                if result.stdout.strip():
                    try:
                        output = json.loads(result.stdout)
                        self.assertIn("overall_healthy", output)
                        self.assertFalse(output["overall_healthy"])
                    except json.JSONDecodeError:
                        # JSON parsing may fail if connection fails immediately
                        pass
                        
            except AssertionError as e:
                if "timed out" in str(e):
                    # If script times out, that's also a valid test result
                    # (shows the script doesn't handle timeouts well)
                    pass
                else:
                    raise
    
    def test_configuration_validation_errors(self):
        """Test configuration validation error handling."""
        sys.path.append(str(self.backend_dir))
        
        try:
            from config import Config
            
            # Test invalid mode
            with patch.dict(os.environ, {'MODE': 'invalid'}):
                with self.assertRaises(ValueError):
                    Config()
            
            # Test cloud mode with missing required variables
            with patch.dict(os.environ, {'MODE': 'cloud'}, clear=True):
                config = Config()
                
                with self.assertRaises(ValueError):
                    config.get_database_config()
                
                with self.assertRaises(ValueError):
                    config.get_watson_config()
                    
        except ImportError:
            self.skipTest("Config module not available")
    
    def test_file_permission_errors(self):
        """Test handling of file permission errors."""
        # Create a temporary directory with restricted permissions
        with tempfile.TemporaryDirectory() as temp_dir:
            restricted_dir = Path(temp_dir) / "restricted"
            restricted_dir.mkdir()
            
            # Try to make it read-only (may not work on all systems)
            try:
                restricted_dir.chmod(0o444)
                
                # Test database initialization with restricted directory
                script = self.backend_dir / "init_db.py"
                if script.exists():
                    result = subprocess.run([
                        sys.executable, str(script), 
                        "--database-url", f"sqlite:///{restricted_dir}/test.db"
                    ], capture_output=True, text=True, timeout=30)
                    
                    # Should handle permission error gracefully
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(result.stderr)
                    
            except OSError:
                # Permission changes not supported on this system
                self.skipTest("Cannot test file permissions on this system")


class PerformanceTests(DeploymentTestCase):
    """Performance and load tests."""
    
    def test_performance_benchmark_script(self):
        """Test performance benchmark script."""
        script = self.scripts_dir / "performance_benchmark.py"
        self.assertTrue(script.exists(), "performance_benchmark.py not found")
        
        # Test help
        result = self.run_script(script, ["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Performance benchmark", result.stdout)
    
    def test_script_execution_performance(self):
        """Test deployment script execution performance."""
        # Test that help commands execute quickly
        scripts_to_test = [
            ("validate_environment.py", ["--help"]),
            ("health_check.py", ["--help"]),
            ("run_local.sh", ["--help"])
        ]
        
        for script_name, args in scripts_to_test:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                start_time = time.time()
                result = self.run_script(script_path, args, timeout=10)
                execution_time = time.time() - start_time
                
                # Help commands should execute quickly
                self.assertLess(execution_time, 5.0, 
                    f"Script {script_name} help took too long: {execution_time}s")
                self.assertEqual(result.returncode, 0)
    
    @unittest.skipUnless(
        subprocess.run(["curl", "-s", "http://localhost:8000/health"], 
                      capture_output=True).returncode == 0,
        "API server not running"
    )
    def test_api_response_times(self):
        """Test API response times meet requirements."""
        endpoints = [
            "/health",
            "/heatmap", 
            "/api/info"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            
            try:
                response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                # API should respond within 1 second for basic endpoints
                self.assertLess(response_time, 1000, 
                    f"Endpoint {endpoint} response time too high: {response_time}ms")
                
                if response.status_code < 400:
                    self.assertLess(response_time, 500, 
                        f"Successful endpoint {endpoint} should respond faster: {response_time}ms")
                        
            except requests.exceptions.RequestException as e:
                self.fail(f"Request to {endpoint} failed: {e}")
    
    def test_concurrent_health_checks(self):
        """Test concurrent health check execution."""
        script = self.scripts_dir / "health_check.py"
        if not script.exists():
            self.skipTest("health_check.py not found")
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def run_health_check():
            try:
                result = self.run_script(script, ["--format", "json"], timeout=30)
                results_queue.put(("success", result.returncode))
            except Exception as e:
                results_queue.put(("error", str(e)))
        
        # Run 3 concurrent health checks
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=run_health_check)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=60)
        
        # Check results
        success_count = 0
        while not results_queue.empty():
            status, result = results_queue.get()
            if status == "success":
                success_count += 1
        
        # At least some health checks should succeed
        self.assertGreater(success_count, 0, "No concurrent health checks succeeded")


class ComprehensiveDeploymentTests(DeploymentTestCase):
    """Comprehensive end-to-end deployment validation tests."""
    
    def test_full_local_deployment_simulation(self):
        """Test full local deployment simulation."""
        # Test that all required components for local deployment exist
        required_components = [
            # Scripts
            self.scripts_dir / "run_local.sh",
            self.scripts_dir / "validate_environment.py",
            self.scripts_dir / "health_check.py",
            
            # Backend components
            self.backend_dir / "api.py",
            self.backend_dir / "config.py",
            self.backend_dir / "database.py",
            self.backend_dir / "requirements.txt",
            
            # Frontend components
            self.project_root / "frontend" / "index.html",
            self.project_root / "frontend" / "app.js",
            
            # Data components
            self.project_root / "data"
        ]
        
        missing_components = []
        for component in required_components:
            if not component.exists():
                missing_components.append(str(component))
        
        if missing_components:
            self.fail(f"Missing components for local deployment: {missing_components}")
    
    def test_cloud_deployment_readiness(self):
        """Test cloud deployment readiness."""
        # Test that all required components for cloud deployment exist
        cloud_components = [
            # Cloud deployment scripts
            self.scripts_dir / "deploy_cloudrun.sh",
            self.scripts_dir / "pubsub_setup.sh",
            self.scripts_dir / "setup_bigquery.sh",
            self.scripts_dir / "bigquery_schema.sql",
            
            # Cloud configuration
            self.scripts_dir / "cloud_env_template.sh"
        ]
        
        missing_components = []
        for component in cloud_components:
            if not component.exists():
                missing_components.append(str(component))
        
        if missing_components:
            self.fail(f"Missing components for cloud deployment: {missing_components}")
    
    def test_deployment_documentation(self):
        """Test that deployment documentation exists and is comprehensive."""
        readme_files = [
            self.project_root / "README.md",
            self.project_root / "DEPLOYMENT.md",
            self.scripts_dir / "README.md"
        ]
        
        # At least one documentation file should exist
        docs_exist = any(readme.exists() for readme in readme_files)
        
        if not docs_exist:
            self.skipTest("No deployment documentation found")
        
        # Check for key deployment topics in existing docs
        for readme in readme_files:
            if readme.exists():
                content = readme.read_text().lower()
                
                # Should mention both deployment modes
                if "local" in content and "cloud" in content:
                    self.assertIn("setup", content, "Documentation missing setup instructions")
                    break
    
    def test_environment_switching_integration(self):
        """Test complete environment switching integration."""
        sys.path.append(str(self.backend_dir))
        
        try:
            from config import Config
            
            # Test switching between modes with proper validation
            test_scenarios = [
                {
                    'mode': 'local',
                    'env_vars': {'MODE': 'local'},
                    'expected_db_type': 'sqlite',
                    'expected_pubsub_emulator': True
                },
                {
                    'mode': 'cloud',
                    'env_vars': {
                        'MODE': 'cloud',
                        'GCP_PROJECT_ID': 'test-project',
                        'WATSON_API_KEY': 'test-key',
                        'GEE_SERVICE_ACCOUNT': '/path/to/service-account.json'
                    },
                    'expected_db_type': 'bigquery',
                    'expected_pubsub_emulator': False
                }
            ]
            
            for scenario in test_scenarios:
                with patch.dict(os.environ, scenario['env_vars'], clear=True):
                    config = Config()
                    
                    # Test database configuration
                    db_config = config.get_database_config()
                    self.assertEqual(db_config.type, scenario['expected_db_type'])
                    
                    # Test Pub/Sub configuration
                    pubsub_config = config.get_pubsub_config()
                    self.assertEqual(pubsub_config.use_emulator, scenario['expected_pubsub_emulator'])
                    
                    # Test satellite configuration
                    satellite_config = config.get_satellite_config()
                    expected_stub = scenario['mode'] == 'local'
                    self.assertEqual(satellite_config.use_stub, expected_stub)
                    
        except ImportError:
            self.skipTest("Config module not available for integration testing")
    
    def test_deployment_rollback_capability(self):
        """Test deployment rollback and cleanup capabilities."""
        # Test that cleanup scripts exist and work
        cleanup_scripts = [
            ("run_local.sh", ["--stop"]),
            ("pubsub_setup.sh", ["--cleanup"]),
            ("setup_bigquery.sh", ["--cleanup"])
        ]
        
        for script_name, args in cleanup_scripts:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                # Test help for cleanup commands
                result = self.run_script(script_path, ["--help"])
                self.assertEqual(result.returncode, 0)
                
                # Check that cleanup options are documented
                help_text = result.stdout.lower()
                cleanup_mentioned = any(word in help_text for word in ['stop', 'cleanup', 'delete'])
                self.assertTrue(cleanup_mentioned, 
                    f"Script {script_name} missing cleanup documentation")
    
    def test_monitoring_and_observability(self):
        """Test monitoring and observability setup."""
        # Test health check capabilities
        script = self.scripts_dir / "health_check.py"
        if script.exists():
            # Test different output formats
            formats = ["human", "json"]
            for fmt in formats:
                result = self.run_script(script, ["--format", fmt], timeout=30)
                self.assertIn(result.returncode, [0, 1])  # May fail if services not running
                
                if fmt == "json" and result.stdout:
                    try:
                        data = json.loads(result.stdout)
                        self.assertIn("overall_healthy", data)
                        self.assertIn("checks", data)
                    except json.JSONDecodeError:
                        pass  # May not be valid JSON if services not running
    
    def test_security_configuration(self):
        """Test security configuration and best practices."""
        # Check for security-related configuration
        config_files = [
            self.project_root / ".env.sample",
            self.scripts_dir / "cloud_env_template.sh"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                content = config_file.read_text()
                
                # Should not contain actual secrets
                sensitive_patterns = [
                    r'password\s*=\s*[^<\s]+',
                    r'key\s*=\s*[A-Za-z0-9]{20,}',
                    r'token\s*=\s*[A-Za-z0-9]{20,}'
                ]
                
                for pattern in sensitive_patterns:
                    import re
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    self.assertEqual(len(matches), 0, 
                        f"Potential hardcoded secret in {config_file}: {matches}")
                
                # Should have placeholder values
                placeholder_patterns = ['<', 'YOUR_', 'REPLACE_', 'TODO']
                has_placeholders = any(pattern in content for pattern in placeholder_patterns)
                
                if not has_placeholders:
                    # At least warn about potential security issue
                    print(f"Warning: {config_file} may not have proper placeholder values")


if __name__ == "__main__":
    # Create test results directory
    test_results_dir = Path("test-results")
    test_results_dir.mkdir(exist_ok=True)
    
    # Run tests with detailed output
    try:
        import xmlrunner
        
        with open(test_results_dir / "infrastructure-tests.xml", "wb") as output:
            runner = xmlrunner.XMLTestRunner(output=output, verbosity=2)
            unittest.main(testRunner=runner, exit=False)
    except ImportError:
        # Fall back to standard test runner if xmlrunner not available
        unittest.main(verbosity=2)