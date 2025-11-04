#!/usr/bin/env python3
"""
Environment validation script for the misinformation heatmap application.
Checks system requirements, dependencies, and configuration.
"""

import argparse
import importlib
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validates the development environment setup."""
    
    def __init__(self, mode: str = "local"):
        self.mode = mode
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def check_python_version(self) -> bool:
        """Check Python version requirements."""
        logger.info("Checking Python version...")
        
        version = sys.version_info
        required_major, required_minor = 3, 8
        
        if version.major < required_major or (version.major == required_major and version.minor < required_minor):
            self.errors.append(
                f"Python {required_major}.{required_minor}+ required, found {version.major}.{version.minor}.{version.micro}"
            )
            return False
            
        logger.info(f"Python version: {version.major}.{version.minor}.{version.micro} ✓")
        return True
        
    def check_system_requirements(self) -> bool:
        """Check system-level requirements."""
        logger.info("Checking system requirements...")
        
        # Check available memory
        try:
            if platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if 'MemTotal:' in line:
                            total_mem = int(line.split()[1]) // 1024  # Convert to MB
                            break
            elif platform.system() == "Darwin":  # macOS
                result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
                total_mem = int(result.stdout.split()[1]) // (1024 * 1024)  # Convert to MB
            elif platform.system() == "Windows":
                import psutil
                total_mem = psutil.virtual_memory().total // (1024 * 1024)  # Convert to MB
            else:
                total_mem = 4096  # Assume 4GB if unknown
                
            if total_mem < 2048:  # 2GB minimum
                self.warnings.append(f"Low memory detected: {total_mem}MB (recommended: 4GB+)")
            else:
                logger.info(f"Available memory: {total_mem}MB ✓")
                
        except Exception as e:
            self.warnings.append(f"Could not check memory: {e}")
            
        # Check disk space
        try:
            disk_usage = os.statvfs('.')
            free_space = (disk_usage.f_frsize * disk_usage.f_bavail) // (1024 * 1024)  # MB
            
            if free_space < 1024:  # 1GB minimum
                self.warnings.append(f"Low disk space: {free_space}MB (recommended: 2GB+)")
            else:
                logger.info(f"Available disk space: {free_space}MB ✓")
                
        except Exception as e:
            self.warnings.append(f"Could not check disk space: {e}")
            
        return True
        
    def check_python_packages(self) -> bool:
        """Check required Python packages."""
        logger.info("Checking Python packages...")
        
        required_packages = [
            'fastapi',
            'uvicorn',
            'pydantic',
            'sqlalchemy',
            'transformers',
            'torch',
            'numpy',
            'pandas',
            'requests',
            'python-dotenv'
        ]
        
        if self.mode == "cloud":
            required_packages.extend([
                'google-cloud-pubsub',
                'google-cloud-bigquery',
                'google-cloud-storage',
                'ibm-watson'
            ])
            
        missing_packages = []
        
        for package in required_packages:
            try:
                importlib.import_module(package.replace('-', '_'))
                logger.debug(f"Package {package} ✓")
            except ImportError:
                missing_packages.append(package)
                
        if missing_packages:
            self.errors.append(f"Missing Python packages: {', '.join(missing_packages)}")
            return False
            
        logger.info("All required Python packages found ✓")
        return True
        
    def check_external_tools(self) -> bool:
        """Check external tools and utilities."""
        logger.info("Checking external tools...")
        
        tools = {
            'curl': 'curl --version',
            'git': 'git --version'
        }
        
        if self.mode == "cloud":
            tools['gcloud'] = 'gcloud version'
            
        missing_tools = []
        
        for tool, command in tools.items():
            try:
                result = subprocess.run(
                    command.split(),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.debug(f"Tool {tool} ✓")
                else:
                    missing_tools.append(tool)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                missing_tools.append(tool)
                
        if missing_tools:
            if 'gcloud' in missing_tools and self.mode == "cloud":
                self.errors.append("gcloud CLI required for cloud mode")
            else:
                self.warnings.append(f"Optional tools not found: {', '.join(missing_tools)}")
                
        return True
        
    def check_environment_variables(self) -> bool:
        """Check required environment variables."""
        logger.info("Checking environment variables...")
        
        required_vars = []
        optional_vars = [
            'DEBUG',
            'LOG_LEVEL',
            'API_HOST',
            'API_PORT'
        ]
        
        if self.mode == "cloud":
            required_vars.extend([
                'GOOGLE_CLOUD_PROJECT',
                'GOOGLE_APPLICATION_CREDENTIALS'
            ])
            optional_vars.extend([
                'WATSON_DISCOVERY_API_KEY',
                'WATSON_DISCOVERY_URL'
            ])
            
        missing_required = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
                
        if missing_required:
            self.errors.append(f"Missing required environment variables: {', '.join(missing_required)}")
            return False
            
        # Check optional variables
        missing_optional = [var for var in optional_vars if not os.getenv(var)]
        if missing_optional:
            self.warnings.append(f"Optional environment variables not set: {', '.join(missing_optional)}")
            
        logger.info("Environment variables check completed ✓")
        return True
        
    def check_file_structure(self) -> bool:
        """Check required file and directory structure."""
        logger.info("Checking file structure...")
        
        required_files = [
            'backend/api.py',
            'backend/config.py',
            'backend/database.py',
            'backend/requirements.txt',
            'frontend/index.html',
            'frontend/js/app.js',
            'frontend/styles.css'
        ]
        
        required_dirs = [
            'backend',
            'frontend',
            'data',
            'scripts'
        ]
        
        missing_files = []
        missing_dirs = []
        
        # Check files
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
                
        # Check directories
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)
                
        if missing_files:
            self.errors.append(f"Missing required files: {', '.join(missing_files)}")
            
        if missing_dirs:
            self.errors.append(f"Missing required directories: {', '.join(missing_dirs)}")
            
        if not missing_files and not missing_dirs:
            logger.info("File structure check completed ✓")
            return True
            
        return False
        
    def check_network_connectivity(self) -> bool:
        """Check network connectivity for external services."""
        logger.info("Checking network connectivity...")
        
        test_urls = [
            'https://www.google.com',
            'https://huggingface.co'
        ]
        
        if self.mode == "cloud":
            test_urls.extend([
                'https://cloud.google.com',
                'https://api.us-south.discovery.watson.cloud.ibm.com'
            ])
            
        failed_connections = []
        
        for url in test_urls:
            try:
                result = subprocess.run(
                    ['curl', '-s', '--connect-timeout', '5', url],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode != 0:
                    failed_connections.append(url)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                failed_connections.append(url)
                
        if failed_connections:
            self.warnings.append(f"Network connectivity issues: {', '.join(failed_connections)}")
            
        logger.info("Network connectivity check completed")
        return True
        
    def validate_all(self) -> bool:
        """Run all validation checks."""
        logger.info(f"Starting environment validation for {self.mode} mode...")
        
        checks = [
            self.check_python_version,
            self.check_system_requirements,
            self.check_file_structure,
            self.check_python_packages,
            self.check_external_tools,
            self.check_environment_variables,
            self.check_network_connectivity
        ]
        
        success = True
        
        for check in checks:
            try:
                if not check():
                    success = False
            except Exception as e:
                self.errors.append(f"Validation check failed: {e}")
                success = False
                
        return success
        
    def print_results(self) -> None:
        """Print validation results."""
        print("\n" + "="*60)
        print("ENVIRONMENT VALIDATION RESULTS")
        print("="*60)
        
        if not self.errors and not self.warnings:
            print("✅ All checks passed! Environment is ready.")
        else:
            if self.errors:
                print(f"\n❌ ERRORS ({len(self.errors)}):")
                for i, error in enumerate(self.errors, 1):
                    print(f"  {i}. {error}")
                    
            if self.warnings:
                print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
                for i, warning in enumerate(self.warnings, 1):
                    print(f"  {i}. {warning}")
                    
        print("\n" + "="*60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Validate environment for misinformation heatmap application"
    )
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="Deployment mode to validate"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    validator = EnvironmentValidator(mode=args.mode)
    success = validator.validate_all()
    validator.print_results()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()